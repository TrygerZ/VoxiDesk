"""Wrapper for faster-whisper (CTranslate2)."""

import threading

from faster_whisper import WhisperModel


class Transcriber:
    """Wrapper for faster-whisper model."""

    def __init__(self, model_name: str = "small", device: str | None = None):
        self.model_name = model_name
        self.device = device
        self.model = None

    def load_model(self):
        """Load faster-whisper model into memory."""
        compute_type = "float16"
        if self.device and self.device.startswith("cpu"):
            compute_type = "int8"

        self.model = WhisperModel(
            self.model_name,
            device=self.device or "cuda",
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
                on_segment(seg_dict)

        return {
            "text": " ".join(full_text_parts).strip(),
            "segments": formatted_segments,
            "language": info.language or "",
            "duration": info.duration or 0,
        }

    def unload_model(self):
        """Unload model from memory."""
        if self.model is not None:
            del self.model
            self.model = None
