"""Worker thread for running transcription in the background."""

import logging
import os
import sys
import threading
import time
import traceback
import gc
from pathlib import Path
from queue import Queue

from app.core.transcriber import Transcriber
from app.core.export import export_results
from app.core.file_utils import get_audio_duration, repair_audio_file
from app.core.ffmpeg_checker import get_ffmpeg_bin_dir

logger = logging.getLogger(__name__)


class TranscriptionWorker(threading.Thread):
    """Worker thread that runs transcription in the background."""

    def __init__(
        self,
        file_path: str,
        config: dict,
        progress_queue: Queue,
        result_queue: Queue,
    ):
        super().__init__()
        self.daemon = False  # Non-daemon: ensures proper cleanup on exit
        self.file_path = file_path
        self.config = config
        self.progress_queue = progress_queue
        self.result_queue = result_queue
        self._cancel_flag = threading.Event()

    def cancel(self):
        """Mark worker for cancellation."""
        self._cancel_flag.set()

    def run(self):
        """Run transcription in the background thread.
        
        Lifecycle:
        - Always cleans up model in finally block
        - Sends 'cancelled' via result_queue if cancel was requested
        - Always sends 'worker_done' as final signal to indicate full cleanup
        """
        transcriber = None
        try:
            # Ensure bundled FFmpeg is discoverable by faster_whisper.
            # faster_whisper calls ffmpeg internally via subprocess, so we
            # prepend the bundled bin dir to PATH for this process.
            bundled_bin = get_ffmpeg_bin_dir()
            if bundled_bin:
                bundled_str = str(bundled_bin)
                current_path = os.environ.get("PATH", "")
                if bundled_str not in current_path:
                    os.environ["PATH"] = f"{bundled_str}{os.pathsep}{current_path}"
                    logger.debug("Prepended bundled FFmpeg to PATH: %s", bundled_str)

            # Send model loading status
            self.progress_queue.put(
                ("status", f"Loading model '{self.config['model']}'...")
            )

            # Create transcriber
            transcriber = Transcriber(
                model_name=self.config["model"],
                device=self.config.get("device"),
            )

            # Check cancel before loading model
            if self._cancel_flag.is_set():
                return

            transcriber.load_model()

            # Check cancel after loading model
            if self._cancel_flag.is_set():
                return

            in_path = Path(self.file_path)
            self.progress_queue.put(
                ("status", f"Processing: {in_path.name}")
            )
            self.progress_queue.put(("progress", 0, 100, "Starting transcription..."))

            audio_dur = get_audio_duration(self.file_path)
            # Shared state between segment callback
            prog_state = {
                "tok_s": 0.0,
                "last_pct": -1,
                "start_time": time.time()
            }

            # Callback to calculate progress and tok/s in real-time from each segment
            total_chars = 0
            t_seg_start = time.time()

            def on_segment(seg):
                nonlocal total_chars, t_seg_start
                total_chars += len(seg["text"])
                elapsed = time.time() - t_seg_start
                if elapsed > 1:
                    # Whisper BPE: ~4.5 chars per token (multilingual)
                    prog_state["tok_s"] = total_chars / elapsed / 4.5

                if audio_dur > 0:
                    pct = min(int((seg["end"] / audio_dur) * 100), 99)
                    if pct != prog_state["last_pct"]:
                        prog_state["last_pct"] = pct
                        msg = f"Transcription {pct}%"
                        if prog_state["tok_s"] > 0:
                            msg += f" — {prog_state['tok_s']:.0f} tok/s"
                        
                        elapsed_total = time.time() - prog_state["start_time"]
                        if elapsed_total > 3 and pct > 3 and pct < 95:
                            eta = elapsed_total * (100 / pct - 1)
                            msg += f" — ~{eta:.0f}s"
                        self.progress_queue.put(("progress", pct, 100, msg))
                else:
                    # Fallback if audio_dur is 0
                    msg = f"Transcribing... processed {seg['end']:.1f}s"
                    if prog_state["tok_s"] > 0:
                        msg += f" — {prog_state['tok_s']:.0f} tok/s"
                    self.progress_queue.put(("progress", 0, 0, msg))

            lang_cfg = self.config.get("language", "id")
            if lang_cfg == "auto":
                lang_cfg = None

            result = transcriber.transcribe(
                file_path=self.file_path,
                language=lang_cfg,
                task=self.config.get("task", "transcribe"),
                log_progress=False,
                on_segment=on_segment,
                cancel_flag=self._cancel_flag,
            )

            if self._cancel_flag.is_set():
                self.progress_queue.put(("status", "Transcription cancelled"))
                return

            # === Auto-repair: detect empty result from corrupt audio ===
            # faster-whisper 1.x uses PyAV internally, which is less tolerant
            # of corrupt MP3 frames than the ffmpeg CLI. If a file has minor
            # corruption, PyAV may only decode the first few milliseconds,
            # resulting in 0 segments despite the file being hours long.
            result_text = result.get("text", "").strip()
            if not result_text and audio_dur > 30 and not self._cancel_flag.is_set():
                logger.warning(
                    "Empty transcription for '%s' (ffprobe duration: %.1fs). "
                    "Attempting audio repair via ffmpeg re-encode...",
                    in_path.name, audio_dur,
                )
                self.progress_queue.put((
                    "status",
                    "⚠️ Audio decode issue detected. Re-encoding file...",
                ))

                repaired = repair_audio_file(self.file_path)
                if repaired is not None:
                    self.progress_queue.put((
                        "status",
                        "🔄 Retrying transcription with repaired audio...",
                    ))
                    try:
                        result = transcriber.transcribe(
                            file_path=str(repaired),
                            language=lang_cfg,
                            task=self.config.get("task", "transcribe"),
                            log_progress=False,
                            on_segment=on_segment,
                            cancel_flag=self._cancel_flag,
                        )
                        result_text = result.get("text", "").strip()
                        if result_text:
                            self.progress_queue.put((
                                "status", "✅ Repair successful! File re-encoded cleanly."
                            ))
                        else:
                            self.progress_queue.put((
                                "status",
                                "⚠️ Repair done, but transcription still empty. "
                                "The audio may be silent or contain no speech.",
                            ))
                    finally:
                        repaired.unlink(missing_ok=True)
                else:
                    self.progress_queue.put((
                        "status",
                        "⚠️ Audio repair failed. The file may be corrupt. "
                        "Output will be empty.",
                    ))

            self.progress_queue.put(("status", "Saving transcription results..."))

            # Export results — SEC-002: sanitize output path to prevent traversal
            output_dir = Path(self.config.get("output_dir", in_path.parent)).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

            # Sanitize stem: remove path traversal and dangerous characters
            safe_stem = in_path.stem.replace("..", "").replace("/", "").replace("\\", "")
            if not safe_stem:
                safe_stem = "transcription"
            base_path = output_dir / safe_stem

            # Validate: resolved base_path must remain inside output_dir
            if not str(base_path.resolve()).startswith(str(output_dir)):
                raise ValueError(f"Output path traversal detected: {base_path}")

            formats = list(self.config.get("formats", ["txt", "srt", "vtt"]))

            if "pdf" in formats:
                lang = result.get("language", "").lower()
                # Only block languages truly unsupported by DejaVuSans (CJK, Arabic, Thai, etc.)
                unsupported_pdf_fonts = ["ja", "zh", "ko", "ar", "th", "he", "hi", "ur", "fa"]
                if lang in unsupported_pdf_fonts:
                    self.progress_queue.put(
                        ("status", f"⚠️ Warning: PDF export skipped for {lang.upper()} (font not supported).")
                    )
                    formats.remove("pdf")

            try:
                saved_files = export_results(result, base_path, formats)
            except Exception as e:
                # If export fails (e.g. PDF font issue), retry without PDF
                logger.warning("Export failed, retrying without PDF: %s", e)
                formats_without_pdf = [f for f in formats if f != "pdf"]
                if formats_without_pdf:
                    saved_files = export_results(result, base_path, formats_without_pdf)
                    self.progress_queue.put(
                        ("status", "⚠️ PDF export failed, saved other formats.")
                    )
                else:
                    raise

            if self._cancel_flag.is_set():
                self.progress_queue.put(("status", "Transcription cancelled during export"))
                return

            if "pdf" in formats and "pdf" not in saved_files:
                self.progress_queue.put(
                    ("status", "⚠️ Warning: PDF export failed (check logs).")
                )

            self.progress_queue.put(("progress", 100, 100, "✅ Done!"))
            self.progress_queue.put(("status", "✅ Transcription complete!"))

            # Send result
            self.result_queue.put((
                "result",
                {
                    "text": result.get("text", "").strip(),
                    "segments": result.get("segments", []),
                    "saved_files": saved_files,
                    "language": result.get("language", ""),
                    "duration": result.get("duration", 0),
                },
            ))

        except Exception as e:
            # SEC-007: Log full traceback internally, send only generic message to UI
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(
                "Transcription error for %s: %s\n%s",
                self.file_path, error_msg, traceback.format_exc(),
            )

            generic_msg = "An error occurred during transcription. Please check your input file and try again."
            self.progress_queue.put(
                ("status", f"Error: {generic_msg}")
            )
            # Send only generic message — no traceback or internal paths
            self.result_queue.put(
                ("error", {"message": generic_msg})
            )
        finally:
            # === Guaranteed cleanup & lifecycle signals ===
            # Always unload model and free CUDA/CPU memory
            if transcriber is not None:
                transcriber.unload_model()
            gc.collect()

            # If cancel was requested, send cancelled signal
            if self._cancel_flag.is_set():
                self.result_queue.put(("cancelled", None))

            # Always signal that worker is fully done (cleanup complete)
            self.result_queue.put(("worker_done", None))
