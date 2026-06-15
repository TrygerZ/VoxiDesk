"""Detect and validate FFmpeg availability on the system."""

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Platform-aware executable extension
_EXE_EXT = ".exe" if os.name == "nt" else ""


def _get_base_dir() -> Path:
    """Get project root directory."""
    return Path(__file__).resolve().parent.parent.parent


def get_ffmpeg_bin_dir() -> Path | None:
    """
    Get the absolute path to the bundled FFmpeg bin directory, if it exists.

    Returns:
        Path to the bundled ffmpeg bin directory, or None if not found.
    """
    bundled_path = _get_base_dir() / "ffmpeg" / "bin"
    ffmpeg_bin = bundled_path / f"ffmpeg{_EXE_EXT}"
    if ffmpeg_bin.exists():
        return bundled_path
    return None


def check_ffmpeg() -> dict:
    """
    Detect FFmpeg from bundled folder or system PATH.

    Returns:
        dict with keys:
            - available (bool): Whether FFmpeg is available
            - path (str | None): Absolute path to ffmpeg binary
            - version (str | None): FFmpeg version
            - source (str): 'bundled' | 'system' | 'not_found'
    """
    result = {
        "available": False,
        "path": None,
        "version": None,
        "source": "not_found",
    }

    # 1. Check system PATH first (preferred over bundled)
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        result["path"] = system_ffmpeg
        result["source"] = "system"
        result["available"] = True
        result["version"] = _get_ffmpeg_version(system_ffmpeg)
        logger.info("Found system FFmpeg: %s", system_ffmpeg)
        return result

    # 2. Check bundled FFmpeg as fallback
    bundled_path = _get_base_dir() / "ffmpeg" / "bin"
    bundled_ffmpeg = bundled_path / f"ffmpeg{_EXE_EXT}"

    if bundled_ffmpeg.exists():
        # SEC-005: Do NOT mutate global os.environ["PATH"].
        # Return the absolute path; callers must use it directly in subprocess.
        abs_path = str(bundled_ffmpeg.resolve())
        result["path"] = abs_path
        result["source"] = "bundled"
        result["available"] = True
        result["version"] = _get_ffmpeg_version(abs_path)
        logger.info("Found bundled FFmpeg (fallback): %s", abs_path)
        return result

    logger.warning("FFmpeg not found (neither system PATH nor bundled)")
    return result


def get_ffprobe_path() -> str | None:
    """
    Get absolute path to ffprobe binary (bundled or system).

    Returns:
        str absolute path to ffprobe, or None if not found.
    """
    # Check system PATH first (preferred over bundled)
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return str(Path(system_ffprobe).resolve())

    # Fallback to bundled — use platform-aware extension
    bundled_path = _get_base_dir() / "ffmpeg" / "bin"
    bundled_ffprobe = bundled_path / f"ffprobe{_EXE_EXT}"
    if bundled_ffprobe.exists():
        return str(bundled_ffprobe.resolve())

    return None


def _get_ffmpeg_version(ffmpeg_path: str) -> str | None:
    """Get FFmpeg version from --version output."""
    try:
        proc = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        first_line = proc.stdout.split("\n")[0].strip()
        return first_line
    except Exception:
        return None
