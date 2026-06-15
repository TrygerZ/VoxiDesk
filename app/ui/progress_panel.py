"""Panel displaying progress bar and real-time logs."""

import customtkinter as ctk


class ProgressPanel(ctk.CTkFrame):
    """Panel displaying progress bar and real-time logs."""

    MAX_LOG_LINES = 500

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._is_indeterminate = False
        self._build_ui()

    def _build_ui(self):
        """Build UI components."""
        self.label_title = ctk.CTkLabel(
            self,
            text="Progress",
            font=("Segoe UI", 14, "bold"),
        )
        self.label_title.pack(pady=(10, 5))

        self.status_var = ctk.StringVar(value="Waiting for files...")
        self.label_status = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 12),
            anchor="w",
            wraplength=800,
        )
        self.label_status.pack(fill="x", padx=20, pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(self, height=15)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 5))
        self.progress_bar.set(0)

        self.log_text = ctk.CTkTextbox(
            self,
            height=120,
            font=("Consolas", 11),
            state="disabled",
            wrap="word",
        )
        self.log_text.pack(fill="both", padx=20, pady=(0, 10), expand=True)

    def update_progress(self, value: float):
        """Update progress bar (0.0 - 1.0)."""
        if self._is_indeterminate:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self._is_indeterminate = False
        self.progress_bar.set(value)

    def set_status(self, text: str):
        """Update status text."""
        self.status_var.set(text)

    def append_log(self, text: str):
        """Append text to log with line limit to prevent memory leak."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        # Trim to max lines
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > self.MAX_LOG_LINES:
            self.log_text.delete("1.0", f"{lines - self.MAX_LOG_LINES}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_indeterminate(self, enabled: bool = True):
        """Set progress bar to indeterminate mode (loading)."""
        if enabled:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
            self._is_indeterminate = True
        else:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)
            self._is_indeterminate = False

    def reset(self):
        """Reset all progress components."""
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self._is_indeterminate = False
        self.status_var.set("Waiting for files...")
        self.log_text.configure(state="normal")
        self.log_text.delete("0.0", "end")
        self.log_text.configure(state="disabled")
