"""Detect available devices for running Whisper models."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def _check_nvidia_smi() -> list[str]:
    """Detect NVIDIA GPU via nvidia-smi (without torch CUDA)."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return [line.strip() for line in proc.stdout.strip().split("\n") if line.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return []


def _get_cuda_device_count() -> int:
    """Safely get CUDA device count from CTranslate2."""
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count()
    except Exception:
        return 0


def get_available_devices() -> list[dict]:
    """
    Detect all available devices for inference.

    Returns:
        list[dict] with keys:
            - name (str): Device name
            - type (str): 'cpu' or 'cuda'
            - available (bool): Whether device is available
            - description (str): Additional description
    """
    devices = []

    # CPU always available
    devices.append({
        "name": "CPU",
        "type": "cpu",
        "available": True,
        "description": "All computers (slowest)",
    })

    # Check CUDA via CTranslate2 (no PyTorch needed)
    cuda_count = _get_cuda_device_count()
    if cuda_count > 0:
        nvidia_gpus = _check_nvidia_smi()
        for i in range(cuda_count):
            if i >= len(nvidia_gpus):
                logger.warning(
                    "CUDA device %d not found in nvidia-smi output "
                    "(cuda_count=%d, nvidia-smi GPUs=%d)",
                    i, cuda_count, len(nvidia_gpus),
                )
            gpu_name = nvidia_gpus[i] if i < len(nvidia_gpus) else f"GPU {i}"
            devices.append({
                "name": f"CUDA ({gpu_name})",
                "type": "cuda",
                "available": True,
                "description": f"GPU NVIDIA ({gpu_name})",
            })
    else:
        # Check if NVIDIA GPU exists but CUDA runtime is not available
        nvidia_gpus = _check_nvidia_smi()
        if nvidia_gpus:
            gpu_list = ", ".join(nvidia_gpus)
            devices.append({
                "name": f"⚠️ NVIDIA ({gpu_list})",
                "type": "cuda",
                "available": False,
                "description": (
                    f"GPU {gpu_list} detected, but CUDA is not available.\n"
                    "Install NVIDIA CUDA Toolkit or use CPU mode."
                ),
            })
        else:
            devices.append({
                "name": "CUDA",
                "type": "cuda",
                "available": False,
                "description": "GPU NVIDIA (not available)",
            })

    return devices


def get_default_device() -> str:
    """
    Auto-select default device.
    Priority: CUDA > CPU
    """
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def get_cuda_status() -> dict:
    """
    Get detailed CUDA status.

    Returns:
        dict with keys:
            - available (bool)
            - version (str | None)
            - device_count (int)
            - device_name (str | None)
            - nvidia_gpus (list[str]): GPUs from nvidia-smi
            - install_hint (str | None)
    """
    cuda_count = _get_cuda_device_count()
    nvidia_gpus = _check_nvidia_smi()

    status = {
        "available": cuda_count > 0,
        "version": None,
        "device_count": cuda_count,
        "device_name": nvidia_gpus[0] if nvidia_gpus else None,
        "nvidia_gpus": nvidia_gpus,
        "install_hint": None,
    }

    if cuda_count == 0 and nvidia_gpus:
        status["install_hint"] = (
            f"GPU {', '.join(nvidia_gpus)} detected, but CUDA is not available.\n"
            "Install NVIDIA CUDA Toolkit or use CPU mode."
        )

    return status
