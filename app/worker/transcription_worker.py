"""Worker thread for running transcription in the background."""

import re
import sys
import threading
import time
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
                self.result_queue.put(("cancelled", None))
                return

            transcriber.load_model()

            # Check cancel after loading model
            if self._cancel_flag.is_set():
                transcriber.unload_model()
                self.result_queue.put(("cancelled", None))
                return

            in_path = Path(self.file_path)
            self.progress_queue.put(
                ("status", f"Processing: {in_path.name}")
            )
            self.progress_queue.put(("progress", 0, 100, "Starting transcription..."))

            audio_dur = get_audio_duration(self.file_path)
            # Shared state antara tqdm capture dan on_segment callback
            prog_state = {"tok_s": 0.0}

            # === REAL-TIME PROGRESS FROM TQDM ===
            # faster-whisper uses tqdm internally (writes to stderr).
            # We intercept stderr to get real-time progress.

            class _TqdmCapture:
                """Capture tqdm output from stderr for real-time progress."""
                def __init__(self, q, audio_dur, prog_state):
                    self._q = q
                    self._buf = ""
                    self._last = -1
                    self._start = time.time()
                    self._audio_dur = audio_dur
                    self._prog = prog_state

                def write(self, s):
                    sys.__stderr__.write(s)  # pass through to original stderr
                    self._buf += s
                    # Ambil persentase terakhir dari buffer
                    matches = re.findall(r'(\d+)%', self._buf)
                    if matches:
                        pct = min(int(matches[-1]), 99)
                        if pct != self._last:
                            self._last = pct
                            elapsed = time.time() - self._start
                            # Calculate speed & ETA
                            msg = f"Transcription {pct}%"
                            if self._prog["tok_s"] > 0:
                                msg += f" — {self._prog['tok_s']:.0f} tok/s"
                            if elapsed > 3 and pct > 3 and pct < 95:
                                eta = elapsed * (100 / pct - 1)
                                msg += f" — ~{eta:.0f}s"
                            self._q.put(("progress", pct, 100, msg))
                    # Prevent buffer from growing indefinitely
                    if len(self._buf) > 16384:
                        self._buf = self._buf[-8192:]

                def flush(self):
                    sys.__stderr__.flush()

            original_stderr = sys.stderr
            sys.stderr = _TqdmCapture(self.progress_queue, audio_dur, prog_state)

            # Callback to calculate tok/s in real-time from each segment
            total_chars = 0
            t_seg_start = time.time()

            def on_segment(seg):
                nonlocal total_chars, t_seg_start
                total_chars += len(seg["text"])
                elapsed = time.time() - t_seg_start
                if elapsed > 1:
                    # Whisper BPE: ~4.5 chars per token (multilingual)
                    prog_state["tok_s"] = total_chars / elapsed / 4.5

            try:
                result = transcriber.transcribe(
                    file_path=self.file_path,
                    language=self.config.get("language", "id"),
                    task=self.config.get("task", "transcribe"),
                    log_progress=True,
                    on_segment=on_segment,
                    cancel_flag=self._cancel_flag,
                )
            finally:
                sys.stderr = original_stderr

            # === CHECK CANCEL BEFORE EXPORT ===
            if self._cancel_flag.is_set():
                self.progress_queue.put(("status", "Transcription cancelled"))
                transcriber.unload_model()
                self.result_queue.put(("cancelled", None))
                return

            # === EXPORT RESULTS ===
            self.progress_queue.put(("status", "Saving transcription results..."))

            # Export hasil
            output_dir = Path(self.config.get("output_dir", in_path.parent))
            output_dir.mkdir(parents=True, exist_ok=True)
            base_path = output_dir / in_path.stem
            formats = self.config.get("formats", ["txt", "srt", "vtt"])

            saved_files = export_results(result, base_path, formats)

            # === PROGRESS 100% ===
            self.progress_queue.put(("progress", 100, 100, "✅ Done!"))
            self.progress_queue.put(("status", "✅ Transcription complete!"))

            # Kirim hasil
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

        except Exception as e:
            transcriber.unload_model()
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            error_detail = traceback.format_exc()
            self.progress_queue.put(
                ("status", f"Error: {error_msg}")
            )
            self.result_queue.put(
                ("error", {"message": error_msg, "detail": error_detail})
            )
