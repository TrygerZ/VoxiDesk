"""Transcription history panel."""

import customtkinter as ctk

from app.ui import theme
from app.data.history import History
from app.ui.dialogs import show_info


def _fmt_duration(value) -> str:
    """Safely format a duration value, returning '-' on failure."""
    try:
        return f"{float(value):.1f}s"
    except (TypeError, ValueError):
        return "-"


class HistoryPanel(ctk.CTkFrame):
    """Panel that displays the transcription history list."""

    def __init__(self, master, history: History | None = None, **kwargs):
        """
        Initialize HistoryPanel.

        Args:
            master: Parent widget
            history: History instance. If None, creates a new one.
        """
        super().__init__(master, **kwargs)

        self.history = history or History()

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        """Build UI components."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=theme.PAD_X, pady=(theme.PAD_Y, theme.PAD_Y // 2))

        self.label_title = ctk.CTkLabel(
            header_frame,
            text="History",
            font=theme.FONT_HEADER,
            text_color=theme.TEXT,
        )
        self.label_title.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self._refresh,
            width=80,
            height=30,
            font=theme.FONT_CAPTION,
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_refresh.pack(side="right", padx=(6, 0))

        self.btn_clear = ctk.CTkButton(
            header_frame,
            text="Delete all",
            command=self._clear_history,
            width=100,
            height=30,
            font=theme.FONT_CAPTION,
            fg_color="transparent",
            hover_color=theme.SURFACE_HI,
            text_color=theme.DANGER,
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_clear.pack(side="right", padx=(6, 0))

        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", padx=theme.PAD_X, pady=(6, theme.PAD_Y), expand=True)

        self.detail_frame = ctk.CTkFrame(self)
        self.detail_frame.pack(fill="x", padx=theme.PAD_X, pady=(0, theme.PAD_Y))

        self.detail_label = ctk.CTkLabel(
            self.detail_frame,
            text="Click a history item to view details",
            font=theme.FONT_CAPTION,
            text_color=theme.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=800,
        )
        self.detail_label.pack(fill="x", padx=theme.PAD_Y, pady=6)

        self.count_label = ctk.CTkLabel(
            self,
            text="",
            font=theme.FONT_CAPTION,
            text_color=theme.TEXT_MUTED,
        )
        self.count_label.pack(pady=(0, theme.PAD_Y))

    def _refresh(self):
        """Reload and display history."""
        entries = self.history.get_all()

        for widget in self.table_frame.winfo_children():
            widget.destroy()

        if not entries:
            empty_label = ctk.CTkLabel(
                self.table_frame,
                text="No transcription history yet.",
                font=theme.FONT_BODY,
                text_color=theme.TEXT_MUTED,
            )
            empty_label.pack(pady=50)
            self.count_label.configure(text="0 items")
            return

        header_row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        header_row.pack(fill="x", pady=(6, 2))

        headers = ["No", "Time", "File", "Model", "Duration", "Status"]
        widths = [40, 160, 250, 70, 80, 80]
        for i, (hdr, w) in enumerate(zip(headers, widths)):
            lbl = ctk.CTkLabel(
                header_row,
                text=hdr,
                font=theme.font(11, "bold"),
                text_color=theme.TEXT_MUTED,
                width=w,
                anchor="w",
            )
            lbl.pack(side="left", padx=(6, 0))

        separator = ctk.CTkFrame(self.table_frame, height=1, fg_color=theme.BORDER)
        separator.pack(fill="x", padx=6)

        for idx, entry in enumerate(entries, start=1):
            row_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)

            row_frame.bind("<Button-1>", lambda e, eid=idx - 1: self._show_detail(eid))
            data = [
                (str(idx), 40),
                (entry.get("timestamp", "-"), 160),
                (entry.get("file_name", "-"), 250),
                (entry.get("model", "-"), 70),
                (_fmt_duration(entry.get('duration_process', 0)), 80),
                ("Done", 80),
            ]
            for text, w in data:
                lbl = ctk.CTkLabel(
                    row_frame,
                    text=text,
                    font=theme.FONT_CAPTION,
                    text_color=theme.TEXT,
                    width=w,
                    anchor="w",
                )
                lbl.pack(side="left", padx=(6, 0))
                lbl.bind("<Button-1>", lambda e, eid=idx - 1: self._show_detail(eid))

        self.count_label.configure(text=f"{len(entries)} items")

    def _show_detail(self, index: int):
        """Display history entry details."""
        entries = self.history.get_all()
        if index < 0 or index >= len(entries):
            return

        entry = entries[index]
        lines = [
            f"File: {entry.get('file_name', '-')}",
            f"Time: {entry.get('timestamp', '-')}",
            f"Model: {entry.get('model', '-')}  |  "
            f"Language: {entry.get('language', '-')}  |  "
            f"Device: {entry.get('device', '-')}",
            f"Audio: {_fmt_duration(entry.get('duration_audio', 0))}  |  "
            f"Process: {_fmt_duration(entry.get('duration_process', 0))}",
        ]

        output_files = entry.get("output_files", {})
        if output_files:
            fmt_paths = [f"  {fmt.upper()}: {path}" for fmt, path in output_files.items()]
            lines.append("Saved files:")
            lines.extend(fmt_paths)

        preview = entry.get("text_preview", "")
        if preview:
            max_preview = 300
            if len(preview) > max_preview:
                preview = preview[:max_preview] + "…"
            lines.append(f"\nPreview:\n{preview}")

        self.detail_label.configure(text="\n".join(lines))

    def _clear_history(self):
        """Delete all history with confirmation."""
        dialog = ctk.CTkInputDialog(
            text="Type 'DELETE' to confirm clearing all history:",
            title="Clear All History",
        )
        # Make dialog modal
        toplevel = self.winfo_toplevel()
        dialog.transient(toplevel)
        dialog.grab_set()
        result = dialog.get_input()

        if result and result.strip().upper() == "DELETE":
            self.history.clear()
            self._refresh()
            show_info("History Cleared", "All transcription history has been deleted.",
                      master=self.winfo_toplevel())
        elif result:
            show_info("Invalid Input", "Type 'DELETE' to confirm deletion.",
                      master=self.winfo_toplevel())
