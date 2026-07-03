"""Panel for displaying transcription results."""

import customtkinter as ctk

from app.ui import theme


class PreviewPanel(ctk.CTkFrame):
    """Panel for displaying transcription results."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._text_content = ""
        self._raw_segments = []
        self._timestamp_mode = False
        self._search_matches: list[str] = []
        self._search_current = -1

        self._build_ui()

    def _build_ui(self):
        """Build UI components."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=theme.PAD_X, pady=(theme.PAD_Y, theme.PAD_Y // 2))

        self.label_title = ctk.CTkLabel(
            header_frame,
            text="Result",
            font=theme.FONT_HEADER,
            text_color=theme.TEXT,
        )
        self.label_title.pack(side="left")

        # --- Search bar ---
        self.search_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.search_frame.pack(side="right", padx=(6, 0))

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search…",
            width=140,
            height=30,
            font=theme.FONT_CAPTION,
            corner_radius=theme.RADIUS_BTN,
        )
        self.search_entry.pack(side="left", padx=(0, 4))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())
        self.search_entry.bind("<Return>", lambda e: self._on_search_next())

        self.btn_search_prev = ctk.CTkButton(
            self.search_frame,
            text="▲",
            command=self._on_search_prev,
            width=28,
            height=30,
            font=theme.font(10),
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_search_prev.pack(side="left", padx=(0, 2))

        self.btn_search_next = ctk.CTkButton(
            self.search_frame,
            text="▼",
            command=self._on_search_next,
            width=28,
            height=30,
            font=theme.font(10),
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_search_next.pack(side="left", padx=(0, 2))

        self.label_match_count = ctk.CTkLabel(
            self.search_frame,
            text="",
            font=theme.FONT_CAPTION,
            text_color=theme.TEXT_MUTED,
            anchor="w",
        )
        self.label_match_count.pack(side="left", padx=(4, 0))

        # --- Timestamp toggle ---
        self.btn_toggle_ts = ctk.CTkButton(
            header_frame,
            text="Timestamps",
            command=self._toggle_timestamp_mode,
            width=110,
            height=30,
            font=theme.FONT_CAPTION,
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_toggle_ts.pack(side="right", padx=(6, 0))

        # --- Copy button ---
        self.btn_copy = ctk.CTkButton(
            header_frame,
            text="Copy all",
            command=self._copy_all,
            width=90,
            height=30,
            font=theme.FONT_CAPTION,
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_copy.pack(side="right", padx=(0, 6))

        # Text preview
        self.preview_text = ctk.CTkTextbox(
            self,
            font=theme.FONT_BODY,
            state="disabled",
            wrap="word",
            corner_radius=theme.RADIUS_BTN,
        )
        self.preview_text.pack(fill="both", padx=theme.PAD_X, pady=(0, theme.PAD_Y), expand=True)

        # Configure search highlight tag
        self.preview_text.tag_config(
            "search_highlight",
            background=theme.HIGHLIGHT_BG,
            foreground=theme.HIGHLIGHT_FG,
        )
        self.preview_text.tag_config(
            "search_current",
            background=theme.HIGHLIGHT_CURRENT_BG,
            foreground=theme.HIGHLIGHT_CURRENT_FG,
        )

        # Placeholder
        self._show_placeholder()

    def _show_placeholder(self):
        """Show placeholder text."""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        self.preview_text.insert(
            "0.0",
            "Transcription result will appear here…\n\n"
            "1. Select audio or video file(s)\n"
            "2. Adjust settings if needed\n"
            "3. Click the Transcribe button\n"
            "4. Wait for the process to complete",
        )
        self.preview_text.configure(state="disabled")

    def show_result(self, text: str, segments: list | None = None):
        """Display transcription result."""
        self._text_content = text
        self._raw_segments = segments or []
        self._timestamp_mode = False
        self.btn_toggle_ts.configure(text="Timestamps")
        self._display_text(text)

    def _display_text(self, text: str):
        """Display text in the preview widget."""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        self.preview_text.insert("0.0", text)
        self.preview_text.configure(state="disabled")
        # Re-run search if active
        if self.search_entry.get().strip():
            self._on_search()

    def clear(self):
        """Clear the preview."""
        self._text_content = ""
        self._raw_segments = []
        self._timestamp_mode = False
        self._search_matches = []
        self._search_current = -1
        self.label_match_count.configure(text="")
        self.search_entry.delete(0, "end")
        self._show_placeholder()

    def _get_all_text(self) -> str:
        """Get all meaningful text from the preview (excluding placeholder)."""
        text = self.preview_text.get("0.0", "end").strip()
        if text and text != self._get_placeholder_text():
            return text
        return ""

    def _copy_all(self):
        """Copy all text to clipboard."""
        text = self._get_all_text()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
        self.btn_copy.configure(text="Copied!")
        self.after(1500, lambda: self.btn_copy.configure(text="Copy all"))

    def _get_placeholder_text(self) -> str:
        """Get placeholder text for comparison."""
        return (
            "Transcription result will appear here…\n\n"
            "1. Select audio or video file(s)\n"
            "2. Adjust settings if needed\n"
            "3. Click the Transcribe button\n"
            "4. Wait for the process to complete"
        )

    def _on_search(self):
        """Search and highlight text in preview."""
        query = self.search_entry.get().strip()
        self.preview_text.tag_remove("search_highlight", "0.0", "end")
        self.preview_text.tag_remove("search_current", "0.0", "end")
        self._search_matches = []
        self._search_current = -1
        self.label_match_count.configure(text="")

        if not query or not self._text_content:
            return

        # Find all matches
        content = self.preview_text.get("0.0", "end")
        start_idx = "0.0"
        while True:
            pos = self.preview_text.search(query, start_idx, "end", nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(query)}c"
            self._search_matches.append(pos)
            self.preview_text.tag_add("search_highlight", pos, end_pos)
            start_idx = end_pos

        if self._search_matches:
            self._search_current = 0
            self._highlight_current()
            self.label_match_count.configure(
                text=f"{len(self._search_matches)} matches"
            )
        else:
            self.label_match_count.configure(text="No results")

    def _on_search_next(self):
        """Go to next search match."""
        if not self._search_matches:
            return
        self._search_current = (self._search_current + 1) % len(self._search_matches)
        self._highlight_current()

    def _on_search_prev(self):
        """Go to previous search match."""
        if not self._search_matches:
            return
        self._search_current = (self._search_current - 1) % len(self._search_matches)
        self._highlight_current()

    def _highlight_current(self):
        """Highlight current match and scroll to it."""
        self.preview_text.tag_remove("search_current", "0.0", "end")
        if self._search_current < 0 or self._search_current >= len(self._search_matches):
            return
        pos = self._search_matches[self._search_current]
        query = self.search_entry.get().strip()
        end_pos = f"{pos}+{len(query)}c"
        self.preview_text.tag_add("search_current", pos, end_pos)
        self.preview_text.see(pos)
        # Update match counter
        self.label_match_count.configure(
            text=f"{self._search_current + 1}/{len(self._search_matches)}"
        )

    def _format_ts_hms(self, seconds: float) -> str:
        """Format seconds to [HH:MM:SS]."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"

    def _format_with_timestamps(self) -> str:
        """Format text with per-word timestamps."""
        lines = []
        for seg in self._raw_segments:
            words = seg.get("words", [])
            if words:
                for word_info in words:
                    word = word_info.get("word", "").strip()
                    if not word:
                        continue
                    start = self._format_ts_hms(word_info.get("start", 0))
                    end = self._format_ts_hms(word_info.get("end", 0))
                    lines.append(f"{start} -> {end} {word}")
            else:
                # Fallback: segment-level timestamp
                start = self._format_ts_hms(seg.get("start", 0))
                end = self._format_ts_hms(seg.get("end", 0))
                text = seg.get("text", "").strip()
                if text:
                    lines.append(f"{start} -> {end} {text}")
            lines.append("")  # Blank line between segments
        return "\n".join(lines)

    def _toggle_timestamp_mode(self):
        """Toggle between full text and timestamp display."""
        self._timestamp_mode = not self._timestamp_mode
        if self._timestamp_mode:
            self.btn_toggle_ts.configure(text="Full text")
            formatted = self._format_with_timestamps()
        else:
            self.btn_toggle_ts.configure(text="Timestamps")
            formatted = self._text_content

        self._display_text(formatted)