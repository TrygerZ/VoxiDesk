"""Main application class for VoxiDesk."""

import os
import sys

# Add parent folder to sys.path so app.* imports work
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import customtkinter as ctk

from app.ui.main_window import MainWindow
from app.data.settings import AppSettings


class App:
    """Main VoxiDesk application."""

    def __init__(self):
        """Initialize application."""
        self.settings = AppSettings()
        theme = self.settings.get("theme", "System")

        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("VoxiDesk v3.0")

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
