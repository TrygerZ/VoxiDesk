"""Main application class for VoxiDesk."""

import atexit
import os
import socket
import sys
import tempfile

# Add parent folder to sys.path so app.* imports work
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import customtkinter as ctk

from app.ui.main_window import MainWindow
from app.data.settings import AppSettings

VERSION = "3.0"

# Single-instance lock state (module-level to survive for app lifetime)
_lock_socket = None
_lock_file_path = os.path.join(tempfile.gettempdir(), "voxidesk.lock")


def _acquire_single_instance_lock():
    """Acquire a single-instance lock. Returns True if lock acquired."""
    global _lock_socket

    # Strategy 1: Try socket-based lock (automatically released on process death)
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        _lock_socket.bind(('127.0.0.1', 0))  # OS assigns a free port
        # Write port to lock file so other instances can check
        port = _lock_socket.getsockname()[1]
        with open(_lock_file_path, 'w') as f:
            f.write(f"{os.getpid()}\n{port}\n")
        _lock_socket.listen(1)
        atexit.register(_release_single_instance_lock)
        return True
    except OSError:
        pass

    # Strategy 2: Check if existing lock file points to a live process
    try:
        with open(_lock_file_path, 'r') as f:
            lines = f.readlines()
        if len(lines) >= 2:
            pid = int(lines[0].strip())
            # Check if process is still alive (Windows)
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
                if handle:
                    kernel32.CloseHandle(handle)
                    return False  # Process alive = another instance running
            except Exception:
                pass
    except (FileNotFoundError, ValueError, IndexError):
        pass

    # Stale lock file — overwrite
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        _lock_socket.bind(('127.0.0.1', 0))
        port = _lock_socket.getsockname()[1]
        with open(_lock_file_path, 'w') as f:
            f.write(f"{os.getpid()}\n{port}\n")
        _lock_socket.listen(1)
        atexit.register(_release_single_instance_lock)
        return True
    except OSError:
        return False


def _release_single_instance_lock():
    """Release the single-instance lock."""
    global _lock_socket
    try:
        if _lock_socket:
            _lock_socket.close()
            _lock_socket = None
    except Exception:
        pass
    try:
        os.unlink(_lock_file_path)
    except OSError:
        pass

class App:
    """Main VoxiDesk application."""

    def __init__(self):
        """Initialize application."""
        # Single instance check
        if not _acquire_single_instance_lock():
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                from tkinter import messagebox
                messagebox.showerror(
                    "VoxiDesk Already Running",
                    "VoxiDesk is already running.\n\n"
                    "Only one instance can be active at a time."
                )
                root.destroy()
            except Exception:
                print("VoxiDesk is already running.", file=sys.stderr)
            sys.exit(1)

        self.settings = AppSettings()
        theme = self.settings.get("theme", "System")

        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(f"VoxiDesk v{VERSION}")

        w_width = self.settings.get("window_width", 900)
        w_height = self.settings.get("window_height", 700)
        self.root.geometry(f"{w_width}x{w_height}")
        self.root.minsize(800, 600)

        self._set_icon()
        self.main_window = MainWindow(self.root, settings=self.settings)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self):
        """Set application icon if icon file exists."""
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        icon_path = os.path.join(base_dir, "assets", "icons", "app.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path)
            except Exception:
                pass

    def _on_close(self):
        """Handler when window is closed."""
        self.main_window.on_close()
        self.root.destroy()

    def run(self):
        """Run the application main loop."""
        self.root.mainloop()
