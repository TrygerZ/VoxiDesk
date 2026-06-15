"""Utility functions for audio/video files."""

import logging
import math
import subprocess
from pathlib import Path

from app.core.ffmpeg_checker import get_ffprobe_path

logger = logging.getLogger(__name__)

# Maximum allowed file size: 500 MB
MAX_FILE_SIZE = 500 * 1024 * 1024


def validate_file_size(file_path: str | Path) -> bool:
    """
    Check if file size is within the allowed limit.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if file size is within limit, False otherwise.
    """
    try:
        size = Path(file_path).stat().st_size
        if size > MAX_FILE_SIZE:
            logger.warning(
                "File exceeds maximum size (%d MB): %s (%d bytes)",
                MAX_FILE_SIZE // (1024 * 1024), file_path, size,
            )
            return False
        return True
    except OSError as e:
        logger.error("Cannot stat file for size check: %s — %s", file_path, e)
        return False


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
        logger.debug("ffprobe not found, cannot detect duration")
        return 0.0

    # SEC-001: Resolve to absolute path to prevent argument injection.
    # A file named "-v.mp3" could be interpreted as a flag by ffprobe.
    resolved = Path(file_path).resolve()
    if not resolved.exists():
        logger.warning("File does not exist for duration check: %s", resolved)
        return 0.0

    try:
        proc = subprocess.run(
            [
                ffprobe_path, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                "--",
                str(resolved),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            logger.debug(
                "ffprobe returned non-zero exit code %d for: %s",
                proc.returncode, resolved,
            )
            return 0.0
        raw = proc.stdout.strip()
        if raw:
            value = float(raw)
            # Guard against NaN / Inf
            if math.isnan(value) or math.isinf(value):
                logger.warning("ffprobe returned non-finite duration for %s: %s", resolved, raw)
                return 0.0
            return value
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe timed out for: %s", resolved)
    except ValueError:
        logger.warning("ffprobe returned non-numeric duration for %s: %s", resolved, proc.stdout.strip() if 'proc' in dir() else "N/A")
    except OSError as e:
        logger.error("ffprobe execution failed for %s: %s", resolved, e)
    return 0.0


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to hours:minutes:seconds format.

    Args:
        seconds: Duration in seconds.

    Returns:
        String format "HH:MM:SS" or "MM:SS" if less than 1 hour.
    """
    # Guard against NaN / Inf
    if not isinstance(seconds, (int, float)) or math.isnan(seconds) or math.isinf(seconds):
        return "00:00"
    if seconds <= 0:
        return "00:00"

    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"
