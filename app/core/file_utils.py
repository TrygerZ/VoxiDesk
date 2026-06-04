"""Utility functions for audio/video files."""

import subprocess
from pathlib import Path

from app.core.ffmpeg_checker import get_ffprobe_path


def get_audio_duration(file_path: str | Path) -> float:
    """
    Detect audio/video file duration using ffprobe.

    Args:
        file_path: Path to audio/video file.

    Returns:
        Duration in seconds (float). 0.0 if detection fails.
    """
    ffprobe_path = get_ffprobe_path()
    if not ffprobe_path:
        return 0.0

    file_path = str(file_path)
    try:
        proc = subprocess.run(
            [
                ffprobe_path, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return float(proc.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, OSError):
        pass
    return 0.0


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to hours:minutes:seconds format.

    Args:
        seconds: Duration in seconds.

    Returns:
        String format "HH:MM:SS" or "MM:SS" if less than 1 hour.
    """
    if seconds <= 0:
        return "00:00"

    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"
