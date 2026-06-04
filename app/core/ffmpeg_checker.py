"""Detect and validate FFmpeg availability on the system."""

import os
import shutil
import subprocess
from pathlib import Path


def _get_base_dir() -> Path:
    """Get project root directory."""
    return Path(__file__).resolve().parent.parent.parent


def check_ffmpeg() -> dict:
    """
    Detect FFmpeg from bundled folder or system PATH.

    Returns:
        dict with keys:
            - available (bool): Whether FFmpeg is available
            - path (str | None): Path to ffmpeg.exe
            - version (str | None): FFmpeg version
            - source (str): 'bundled' | 'system' | 'not_found'
    """
    result = {
        "available": False,
        "path": None,
        "version": None,
        "source": "not_found",
    }

    # 1. Check bundled FFmpeg in project folder
    bundled_path = _get_base_dir() / "ffmpeg" / "bin"
    bundled_ffmpeg = bundled_path / "ffmpeg.exe"

    if bundled_ffmpeg.exists():
        # Add bundled path to PATH so Whisper can find it
        bundled_str = str(bundled_path)
        if bundled_str not in os.environ.get("PATH", ""):
            current_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{bundled_str};{current_path}"

        result["path"] = str(bundled_ffmpeg)
        result["source"] = "bundled"
        result["available"] = True
        result["version"] = _get_ffmpeg_version(str(bundled_ffmpeg))
        return result

    # 2. Check in system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        result["path"] = system_ffmpeg
        result["source"] = "system"
        result["available"] = True
        result["version"] = _get_ffmpeg_version(system_ffmpeg)
        return result

    return result


def get_ffprobe_path() -> str | None:
    """
    Get path to ffprobe.exe (bundled or system).

    Returns:
        str path to ffprobe.exe, or None if not found.
    """
    # Check bundled first
    bundled_path = _get_base_dir() / "ffmpeg" / "bin"
    bundled_ffprobe = bundled_path / "ffprobe.exe"
    if bundled_ffprobe.exists():
        return str(bundled_ffprobe)

    # Fallback to system PATH
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe

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
