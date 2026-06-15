"""Wrapper for faster-whisper (CTranslate2)."""

import logging
import threading
import gc

logger = logging.getLogger(__name__)


class Transcriber:
    """Wrapper for faster-whisper model."""

    def __init__(self, model_name: str = "small", device: str | None = None):
        self.model_name = model_name
        self.device = device
        self.model = None
        self._lock = threading.Lock()

    def load_model(self):
        """Load faster-whisper model into memory (thread-safe)."""
        with self._lock:
            from faster_whisper import WhisperModel
            compute_type = "float16"
            if self.device and self.device.startswith("cpu"):
                compute_type = "int8"

            device = self.device or "cpu"
            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
            )

    def transcribe(
        self,
        file_path: str,
        language: str | None = "id",
        task: str = "transcribe",
        log_progress: bool = False,
        on_segment: callable = None,
        cancel_flag: threading.Event = None,
    ):
        """
        Transcribe audio/video file.

        Args:
            file_path: Path to audio/video file
            language: ISO-639-1 language code (None for auto-detect)
            task: 'transcribe' or 'translate'
            log_progress: Enable tqdm progress bar
            on_segment: Callback invoked for each processed segment
            cancel_flag: Event flag to cancel mid-transcription

        Returns:
            dict with transcription result format:
            { "text": str, "segments": [...], "language": str, "duration": float }
        """
        with self._lock:
            if self.model is None:
                raise RuntimeError("Model not loaded. Call load_model() first.")

            segments_generator, info = self.model.transcribe(
                file_path,
                language=language,
                task=task,
                beam_size=5,
                vad_filter=True,
                word_timestamps=True,
                log_progress=log_progress,
            )

            # Iterate generator manually — each segment processed in real-time
            formatted_segments = []
            full_text_parts = []

            for segment in segments_generator:
                if cancel_flag and cancel_flag.is_set():
                    break
                seg_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text or "",
                    "words": [],
                }
                if segment.words:
                    seg_dict["words"] = [
                        {"word": w.word, "start": w.start, "end": w.end}
                        for w in segment.words
                    ]
                formatted_segments.append(seg_dict)
                full_text_parts.append(segment.text or "")

                if on_segment:
                    try:
                        on_segment(seg_dict)
                    except Exception as e:
                        logger.error("Segment callback error: %s", e)
                        # Continue processing — don't let callback failure break transcription

            return {
                "text": " ".join(full_text_parts).strip(),
                "segments": formatted_segments,
                "language": info.language or "",
                "duration": info.duration or 0,
            }

    def unload_model(self):
        """Unload model from memory (thread-safe)."""
        with self._lock:
            if self.model is not None:
                del self.model
                self.model = None

                # Force garbage collection to free C++ bindings and CUDA memory
                gc.collect()

                # Try to clear CUDA cache if torch is available
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
