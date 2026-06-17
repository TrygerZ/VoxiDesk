"""Utility functions for audio/video files."""

import logging
import math
import subprocess
import tempfile
from pathlib import Path

from app.core.ffmpeg_checker import get_ffprobe_path, get_ffmpeg_bin_dir

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


def repair_audio_file(file_path: str | Path) -> Path | None:
    """
    Re-encode an audio file using ffmpeg to fix corrupt frames that cause
    PyAV (used by faster-whisper) to stop decoding prematurely.

    This is needed because faster-whisper 1.x uses PyAV internally for audio
    decoding, and PyAV is less tolerant of corrupt/partial frames than the
    ffmpeg CLI. Files with minor corruption may decode fine in ffprobe but
    yield only a fraction of the expected audio when processed by PyAV.

    Args:
        file_path: Path to the audio file to repair.

    Returns:
        Path to the repaired temporary file, or None if repair fails.
        The caller is responsible for cleaning up the temp file.
    """
    import os
    from app.core.ffmpeg_checker import check_ffmpeg

    ffmpeg_info = check_ffmpeg()
    if not ffmpeg_info["available"]:
        logger.warning("FFmpeg not available, cannot repair audio file")
        return None

    resolved = Path(file_path).resolve()
    if not resolved.exists():
        logger.warning("File does not exist for repair: %s", resolved)
        return None

    # Create a temporary output file with .wav extension
    # WAV is uncompressed, so PyAV will have no issues decoding it
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="voxidesk_repair_")
        os.close(tmp_fd)
    except OSError as e:
        logger.error("Cannot create temp file for audio repair: %s", e)
        return None

    tmp_path = Path(tmp_path)

    try:
        cmd = [
            ffmpeg_info["path"],
            "-y",                      # Overwrite output
            "-i", str(resolved),       # Input file
            "-vn",                     # No video
            "-acodec", "pcm_s16le",    # PCM 16-bit (safe, universal)
            "-ar", "16000",            # Resample to 16kHz (Whisper standard)
            "-ac", "1",                # Mono
            "-af", "aresample=resampler=soxr",  # High-quality resampling
            str(tmp_path),
        ]

        logger.info("Repairing audio file: %s → %s", resolved.name, tmp_path)
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max for very long files
        )

        if proc.returncode != 0:
            logger.warning(
                "Audio repair failed (return code %d) for %s: %s",
                proc.returncode, resolved, proc.stderr[:500],
            )
            tmp_path.unlink(missing_ok=True)
            return None

        if not tmp_path.exists() or tmp_path.stat().st_size == 0:
            logger.warning("Audio repair produced empty output for %s", resolved)
            tmp_path.unlink(missing_ok=True)
            return None

        logger.info(
            "Audio repair successful: %s (%d bytes)",
            resolved.name, tmp_path.stat().st_size,
        )
        return tmp_path

    except subprocess.TimeoutExpired:
        logger.warning("Audio repair timed out for %s", resolved)
        tmp_path.unlink(missing_ok=True)
        return None
    except OSError as e:
        logger.error("Audio repair failed with OSError for %s: %s", resolved, e)
        tmp_path.unlink(missing_ok=True)
        return None
