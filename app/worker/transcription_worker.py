"""Worker thread for running transcription in the background."""

import sys
import threading
import time
import traceback
import gc
from pathlib import Path
from queue import Queue

from app.core.transcriber import Transcriber
from app.core.export import export_results
from app.core.file_utils import get_audio_duration


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
        self.daemon = True
        self.file_path = file_path
        self.config = config
        self.progress_queue = progress_queue
        self.result_queue = result_queue
        self._cancel_flag = threading.Event()

    def cancel(self):
        """Mark worker for cancellation."""
        self._cancel_flag.set()

    def run(self):
        """Run transcription in the background thread."""
        transcriber = None
        try:
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
                transcriber.unload_model()
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
                transcriber.unload_model()
                return

            self.progress_queue.put(("status", "Saving transcription results..."))

            # Export results
            output_dir = Path(self.config.get("output_dir", in_path.parent))
            output_dir.mkdir(parents=True, exist_ok=True)
            base_path = output_dir / in_path.stem
            formats = list(self.config.get("formats", ["txt", "srt", "vtt"]))

            if "pdf" in formats:
                lang = result.get("language", "").lower()
                unsupported_pdf_fonts = ["ja", "zh", "ko", "ar", "th", "he", "hi", "ur", "fa", "vi"]
                if lang in unsupported_pdf_fonts:
                    self.progress_queue.put(
                        ("status", f"⚠️ Warning: PDF export skipped for {lang.upper()} (font not supported).")
                    )
                    formats.remove("pdf")

            saved_files = export_results(result, base_path, formats)

            if self._cancel_flag.is_set():
                self.progress_queue.put(("status", "Transcription cancelled during export"))
                transcriber.unload_model()
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

            # Cleanup model
            transcriber.unload_model()
            gc.collect()

        except Exception as e:
            if transcriber is not None:
                transcriber.unload_model()
            error_msg = f"{type(e).__name__}: {str(e)}"
            error_detail = traceback.format_exc()
            self.progress_queue.put(
                ("status", f"Error: {error_msg}")
            )
            self.result_queue.put(
                ("error", {"message": error_msg, "detail": error_detail})
            )
