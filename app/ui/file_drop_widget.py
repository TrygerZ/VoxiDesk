"""Drag-and-drop widget for selecting audio/video files (multi-file)."""

import os
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, StringVar

from app.core.file_utils import get_audio_duration, format_duration

# Supported file formats
SUPPORTED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".mp4", ".mkv",
    ".avi", ".mov", ".flac", ".ogg", ".webm",
    ".aac", ".wma",
}

SUPPORTED_DESCRIPTION = (
    "Audio/Video: mp3, wav, m4a, mp4, mkv, avi, mov, flac, ogg, webm, aac, wma"
)


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
            text="📁 Select Audio / Video Files",
            font=("Segoe UI", 14, "bold"),
        )
        self.label_title.pack(pady=(10, 5))

        # Drop area
        self.drop_frame = ctk.CTkFrame(
            self,
            border_width=2,
            border_color="#555555",
            corner_radius=10,
            height=100,
        )
        self.drop_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.drop_frame.pack_propagate(False)

        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="📥 Drag & drop files here\nor click to browse",
            font=("Segoe UI", 14),
            text_color="#888888",
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
            text="📂 Browse Files",
            command=self._browse_files,
            width=100,
        )
        self.btn_browse.pack(side="left", padx=(0, 5))

        self.btn_clear = ctk.CTkButton(
            self.btn_frame,
            text="🗑 Clear All",
            command=self.clear_files,
            width=100,
            state="disabled",
            fg_color="#8B0000",
            hover_color="#A52A2A",
        )
        self.btn_clear.pack(side="left")

        # File count label
        self.count_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 11),
            text_color="#888888",
        )
        self.count_label.pack(pady=(0, 5))

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
        self.drop_frame.configure(border_color="#3B8ED0")

    def _on_drag_leave(self):
        """Visual feedback when drag leaves the area."""
        self.drop_frame.configure(border_color="#555555")

    def _on_drop(self, event):
        """Handler when files are dropped (multi-file support)."""
        self._on_drag_leave()
        raw = event.data.strip()
        # Handle multiple files format: {path1} {path2}
        import re
        paths = re.findall(r'\{([^}]+)\}', raw)
        if not paths:
            paths = [raw.strip().strip('{}')]

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

        # Check duplicates
        if path in self.selected_files:
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
        """Update the file list display."""
        # Remove all child widgets
        for widget in self.file_list_container.winfo_children():
            widget.destroy()

        if not self.selected_files:
            self.btn_clear.configure(state="disabled")
            self.drop_label.configure(
                text="📥 Drag & drop files here\nor click to browse",
                text_color="#888888",
            )
            self.count_label.configure(text="")
            return

        # File count header
        count = len(self.selected_files)
        self.count_label.configure(text=f"📄 {count} file(s) selected")

        self.btn_clear.configure(state="normal")
        self.drop_label.configure(
            text="✅ Add more files (drag or browse)",
            text_color="#4CAF50",
        )

        # Display each file
        for i, file_path in enumerate(self.selected_files):
            row = ctk.CTkFrame(self.file_list_container, fg_color="transparent")
            row.pack(fill="x", pady=1, padx=2)

            try:
                size_bytes = file_path.stat().st_size
                size_str = format_file_size(size_bytes)
            except (OSError, FileNotFoundError):
                size_str = "??? (file not found)"

            # Detect audio duration
            duration = get_audio_duration(str(file_path))
            dur_str = f" — ⏱ {format_duration(duration)}" if duration > 0 else ""

            file_info = f"{i + 1}. {file_path.name} ({size_str}){dur_str}"
            lbl = ctk.CTkLabel(
                row,
                text=file_info,
                font=("Segoe UI", 11),
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True)

            btn_remove = ctk.CTkButton(
                row,
                text="✕",
                width=28,
                height=22,
                font=("Segoe UI", 10),
                fg_color="#8B0000",
                hover_color="#A52A2A",
                command=lambda idx=i: self.remove_file(idx),
            )
            btn_remove.pack(side="right", padx=(5, 0))

        # Force refresh scrollable frame
        self.file_list_container.update_idletasks()
        # Scroll to top
        try:
            self.file_list_container._parent_canvas.yview_moveto(0)
        except AttributeError:
            pass

    def _notify_change(self):
        """Notify callback that the file list changed."""
        if self._on_file_change_callback:
            files = self.get_files()
            self._on_file_change_callback(files)
