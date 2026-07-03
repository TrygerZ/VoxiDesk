"""Drag-and-drop widget for selecting audio/video files (multi-file)."""

import logging
import os
import threading
from pathlib import Path

import re
import customtkinter as ctk
from tkinter import filedialog, StringVar

from app.ui import theme
from app.core.file_utils import get_audio_duration, format_duration, MAX_FILE_SIZE

logger = logging.getLogger(__name__)

# Supported file formats
SUPPORTED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".mp4", ".mkv",
    ".avi", ".mov", ".flac", ".ogg", ".webm",
    ".aac", ".wma",
}

SUPPORTED_DESCRIPTION = (
    "Audio/Video: mp3, wav, m4a, mp4, mkv, avi, mov, flac, ogg, webm, aac, wma"
)

# Magic bytes for common audio/video formats
AUDIO_MAGIC = {
    b'\xff\xfb': 'mp3',       # MP3 frame sync
    b'\xff\xf3': 'mp3',       # MP3 frame sync
    b'\xff\xf2': 'mp3',       # MP3 frame sync
    b'\x49\x44\x33': 'mp3',   # ID3 tag (MP3)
    b'\x52\x49\x46\x46': 'wav',  # RIFF/WAV
    b'\x66\x4c\x61\x43': 'flac',  # FLAC
    b'\x4f\x67\x67\x53': 'ogg',   # Ogg
    b'\x1a\x45\xdf\xa3': 'mkv/webm',  # Matroska/WebM
}

# ftyp box pattern for MP4/M4A/MOV (bytes 4-8 are 'ftyp')
_FTYP_MAGIC = b'ftyp'


def is_valid_media_file(path: Path) -> bool:
    """
    Check magic bytes to validate file is actually audio/video.

    Args:
        path: Path to the file to validate.

    Returns:
        True if the file header matches a known audio/video format.
    """
    try:
        with open(path, 'rb') as f:
            header = f.read(16)
        if len(header) < 4:
            return False

        # Check standard magic bytes
        for magic, _fmt in AUDIO_MAGIC.items():
            if header.startswith(magic):
                return True

        # Check ftyp box (MP4, M4A, MOV, etc.) — 'ftyp' at offset 4
        if len(header) >= 8 and header[4:8] == _FTYP_MAGIC:
            return True

        return False
    except OSError:
        return False


def format_file_size(size_bytes: int) -> str:
    """Format file size to KB/MB/GB."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileDropWidget(ctk.CTkFrame):
    """Widget for drag-and-drop or browsing audio/video files (multi-file)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.selected_files: list[Path] = []
        self._on_file_change_callback = None

        self._build_ui()

        # Bind drag-and-drop via tkinterdnd2
        self._setup_drag_drop()

    def _build_ui(self):
        """Build UI components."""
        # Instruction label
        self.label_title = ctk.CTkLabel(
            self,
            text="Source files",
            font=theme.FONT_HEADER,
            text_color=theme.TEXT,
            anchor="w",
        )
        self.label_title.pack(fill="x", padx=theme.PAD_X, pady=(theme.PAD_Y, theme.PAD_Y // 2))

        # Drop area
        self.drop_frame = ctk.CTkFrame(
            self,
            fg_color=theme.SURFACE_HI,
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=theme.RADIUS_CARD,
            height=110,
        )
        self.drop_frame.pack(fill="x", padx=theme.PAD_X, pady=(0, theme.PAD_Y // 2))
        self.drop_frame.pack_propagate(False)

        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="Drag & drop audio or video here\nor click to browse",
            font=theme.FONT_BODY,
            text_color=theme.TEXT_MUTED,
        )
        self.drop_label.pack(expand=True, fill="both")

        # Bind click to browse
        self.drop_frame.bind("<Button-1>", lambda e: self._browse_files())
        self.drop_label.bind("<Button-1>", lambda e: self._browse_files())

        # Selected files list
        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="x", padx=20, pady=(0, 5))

        self.file_list_container = ctk.CTkScrollableFrame(
            self.list_frame, height=120
        )
        self.file_list_container.pack(fill="x")
        # NOTE: do not call pack_propagate(False) — it causes the inner CTkScrollableFrame to collapse to 1x1 px, hiding children.

        # Action buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_browse = ctk.CTkButton(
            self.btn_frame,
            text="Browse files",
            command=self._browse_files,
            width=110,
            height=34,
            font=theme.FONT_BODY,
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_browse.pack(side="left", padx=(0, 8))

        self.btn_clear = ctk.CTkButton(
            self.btn_frame,
            text="Clear all",
            command=self.clear_files,
            width=100,
            height=34,
            font=theme.FONT_BODY,
            state="disabled",
            fg_color="transparent",
            hover_color=theme.SURFACE_HI,
            text_color=theme.DANGER,
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_clear.pack(side="left")

        # File count label
        self.count_label = ctk.CTkLabel(
            self,
            text="",
            font=theme.FONT_CAPTION,
            text_color=theme.TEXT_MUTED,
        )
        self.count_label.pack(pady=(0, theme.PAD_Y // 2))

    def _setup_drag_drop(self):
        """Set up drag-and-drop using tkinterdnd2."""
        try:
            self.drop_frame.drop_target_register("*")
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_label.drop_target_register("*")
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)

            self.drop_frame.dnd_bind(
                "<<DragEnter>>", lambda e: self._on_drag_enter()
            )
            self.drop_frame.dnd_bind(
                "<<DragLeave>>", lambda e: self._on_drag_leave()
            )
            self.drop_label.dnd_bind(
                "<<DragEnter>>", lambda e: self._on_drag_enter()
            )
            self.drop_label.dnd_bind(
                "<<DragLeave>>", lambda e: self._on_drag_leave()
            )
        except Exception:
            pass  # tkinterdnd2 not available

    def _on_drag_enter(self):
        """Visual feedback when drag enters the area."""
        if self.winfo_exists():
            self.drop_frame.configure(border_color=theme.ACCENT, fg_color=theme.ACCENT_SOFT)

    def _on_drag_leave(self):
        """Visual feedback when drag leaves the area."""
        if self.winfo_exists():
            self.drop_frame.configure(border_color=theme.BORDER, fg_color=theme.SURFACE_HI)

    def _on_drop(self, event):
        """Handler when files are dropped (multi-file support)."""
        self._on_drag_leave()
        raw = event.data.strip()

        # Handle braced format: {path1} {path2} (Windows)
        paths = re.findall(r'\{([^}]+)\}', raw)
        if not paths:
            # Fallback: split by whitespace/newline, filter valid paths
            potential = re.split(r'[\s\n\r]+', raw)
            paths = [p.strip().strip('{}') for p in potential if p.strip()]

        for file_path_str in paths:
            p = Path(file_path_str.strip())
            if p.exists() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.add_file(p)

    def _browse_files(self):
        """Open file browse dialog (multi-select)."""
        self._on_drag_leave()  # Reset visual drop
        ext_pattern = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        file_paths = filedialog.askopenfilenames(
            title="Select audio/video files",
            filetypes=[
                ("Audio/Video Files", ext_pattern),
                ("All Files", "*.*"),
            ],
        )
        if file_paths:
            for fp in file_paths:
                self.add_file(Path(fp))

    def add_file(self, path: Path):
        """
        Validate and add a file to the list.

        Args:
            path: Path to the file to add.
        """
        # Validate extension
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            from app.ui.dialogs import show_error
            show_error(
                "Unsupported Format",
                f"File format '{path.suffix}' is not supported.\n\n{SUPPORTED_DESCRIPTION}",
                master=self.winfo_toplevel(),
            )
            return

        # Validate file exists
        if not path.exists():
            from app.ui.dialogs import show_error
            show_error("File Not Found", f"File not found:\n{path}", master=self.winfo_toplevel())
            return

        # SEC-009: Validate file size (max 500 MB)
        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = 0
        if file_size > MAX_FILE_SIZE:
            from app.ui.dialogs import show_error
            max_mb = MAX_FILE_SIZE // (1024 * 1024)
            show_error(
                "File Too Large",
                f"File exceeds the maximum allowed size ({max_mb} MB).\n\n"
                f"File size: {format_file_size(file_size)}",
                master=self.winfo_toplevel(),
            )
            logger.warning("Rejected oversized file: %s (%d bytes)", path, file_size)
            return

        # SEC-006: Validate magic bytes (skip for very small files < 16 bytes)
        if file_size >= 16 and not is_valid_media_file(path):
            from app.ui.dialogs import show_error
            show_error(
                "Invalid File",
                f"File does not appear to be a valid audio/video file.\n\n"
                f"The file extension is '{path.suffix}' but the file content "
                f"does not match any supported format.",
                master=self.winfo_toplevel(),
            )
            logger.warning("Rejected file with invalid magic bytes: %s", path)
            return

        # Check duplicates (case-insensitive on Windows via resolved paths)
        resolved = path.resolve()
        if resolved in {p.resolve() for p in self.selected_files}:
            return  # Silently ignore duplicates

        # Add file
        self.selected_files.append(path)
        self._update_file_list()
        self._notify_change()

    def remove_file(self, index: int):
        """
        Remove a file from the list by index.

        Args:
            index: Index of the file to remove.
        """
        if 0 <= index < len(self.selected_files):
            self.selected_files.pop(index)
            self._update_file_list()
            self._notify_change()

    def clear_files(self):
        """Clear all files from the list."""
        self.selected_files.clear()
        self._update_file_list()
        self._notify_change()

    def get_files(self) -> list[Path]:
        """Return the list of selected files."""
        return list(self.selected_files)

    def get_file_count(self) -> int:
        """Return the number of selected files."""
        return len(self.selected_files)

    def set_on_file_change(self, callback):
        """Set callback for when files change."""
        self._on_file_change_callback = callback

    def _update_file_list(self):
        """Update the file list display with async duration probing."""
        # Remove all child widgets
        for widget in self.file_list_container.winfo_children():
            widget.destroy()

        if not self.selected_files:
            self.btn_clear.configure(state="disabled")
            self.drop_label.configure(
                text="Drag & drop audio or video here\nor click to browse",
                text_color=theme.TEXT_MUTED,
            )
            self.count_label.configure(text="")
            return

        # File count header
        count = len(self.selected_files)
        self.count_label.configure(text=f"{count} file(s) selected")

        self.btn_clear.configure(state="normal")
        self.drop_label.configure(
            text="Add more files (drag or browse)",
            text_color=theme.ACCENT,
        )

        # Display each file with async duration probing
        for i, file_path in enumerate(self.selected_files):
            row = ctk.CTkFrame(self.file_list_container, fg_color="transparent")
            row.pack(fill="x", pady=1, padx=2)

            try:
                size_bytes = file_path.stat().st_size
                size_str = format_file_size(size_bytes)
            except (OSError, FileNotFoundError):
                size_str = "??? (file not found)"

            # Show placeholder duration, probe async
            file_info = f"{i + 1}.  {file_path.name}  ·  {size_str}  ·  …"
            lbl = ctk.CTkLabel(
                row,
                text=file_info,
                font=theme.FONT_CAPTION,
                text_color=theme.TEXT,
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True)

            btn_remove = ctk.CTkButton(
                row,
                text="✕",
                width=26,
                height=24,
                font=theme.font(11),
                fg_color="transparent",
                hover_color=theme.SURFACE_HI,
                text_color=theme.TEXT_MUTED,
                corner_radius=theme.RADIUS_BTN,
                command=lambda idx=i: self.remove_file(idx),
            )
            btn_remove.pack(side="right", padx=(6, 0))

            # Start async duration probe
            threading.Thread(
                target=self._probe_duration,
                args=(file_path, lbl, i, size_str),
                daemon=True,
            ).start()

        # Force refresh scrollable frame
        self.file_list_container.update_idletasks()
        # Scroll to top
        try:
            self.file_list_container._parent_canvas.yview_moveto(0)
        except AttributeError:
            pass

    def _probe_duration(self, file_path: Path, label, index: int, size_str: str):
        """Probe audio duration in background thread and update label."""
        try:
            duration = get_audio_duration(str(file_path))
            dur_str = f"  ·  {format_duration(duration)}" if duration > 0 else ""
        except Exception:
            dur_str = ""
        # Update UI on main thread
        try:
            self.after(0, lambda: self._update_duration_label(
                label, index, file_path, size_str, dur_str
            ))
        except Exception:
            pass  # Widget may have been destroyed

    def _update_duration_label(self, label, index, file_path, size_str, dur_str):
        """Update a file row label with the probed duration (main thread)."""
        if not self.winfo_exists():
            return
        try:
            new_text = f"{index + 1}.  {file_path.name}  ·  {size_str}{dur_str}"
            label.configure(text=new_text)
        except Exception:
            pass  # Widget may have been destroyed

    def _notify_change(self):
        """Notify callback that the file list changed."""
        if self._on_file_change_callback:
            files = self.get_files()
            self._on_file_change_callback(files)
