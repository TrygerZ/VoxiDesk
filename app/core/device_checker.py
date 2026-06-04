"""Detect available devices for running Whisper models."""

import subprocess
import torch


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

    # Cek CUDA via torch
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        cuda_count = torch.cuda.device_count()
        for i in range(cuda_count):
            gpu_name = torch.cuda.get_device_name(i)
            devices.append({
                "name": f"CUDA ({gpu_name})",
                "type": "cuda",
                "available": True,
                "description": f"GPU NVIDIA ({gpu_name})",
            })
    else:
        # Check if NVIDIA GPU exists but torch CUDA is not installed
        nvidia_gpus = _check_nvidia_smi()
        if nvidia_gpus:
            gpu_list = ", ".join(nvidia_gpus)
            devices.append({
                "name": f"⚠️ NVIDIA ({gpu_list})",
                "type": "cuda",
                "available": False,
                "description": (
                    f"GPU {gpu_list} detected, but PyTorch CUDA is not installed.\n"
                    "Run: pip install torch --index-url https://download.pytorch.org/whl/cu124"
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
    if torch.cuda.is_available():
        return "cuda"
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
            - nvidia_gpus (list[str]): GPUs from nvidia-smi (even if torch CUDA is inactive)
            - install_hint (str | None): Install hint if GPU exists but torch CUDA doesn't
    """
    status = {
        "available": torch.cuda.is_available(),
        "version": None,
        "device_count": 0,
        "device_name": None,
        "nvidia_gpus": [],
        "install_hint": None,
    }

    if status["available"]:
        status["version"] = torch.version.cuda
        status["device_count"] = torch.cuda.device_count()
        status["device_name"] = torch.cuda.get_device_name(0)
    else:
        # Check if there's actually an NVIDIA GPU
        nvidia_gpus = _check_nvidia_smi()
        if nvidia_gpus:
            status["nvidia_gpus"] = nvidia_gpus
            status["install_hint"] = (
                f"GPU {', '.join(nvidia_gpus)} detected, but PyTorch CUDA is not installed.\n"
                "Run in terminal (venv active):\n"
                "  pip install torch --index-url https://download.pytorch.org/whl/cu124"
            )

    return status
