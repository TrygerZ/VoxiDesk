"""Configuration panel for transcription settings."""

import customtkinter as ctk

from app.core.device_checker import get_available_devices, get_cuda_status

# Model info: (label, ram_estimation, speed, tooltip)
MODEL_OPTIONS = {
    "tiny": ("tiny", "~1 GB RAM", "Fastest, low accuracy",
             "Fast but less accurate. Good for quick checks."),
    "base": ("base", "~1 GB RAM", "Fast, decent accuracy",
             "Decent speed with reasonable accuracy."),
    "small": ("small", "~2 GB RAM", "Balanced (default)",
              "Balanced — recommended default."),
    "medium": ("medium", "~5 GB RAM", "Slow, high accuracy",
               "High accuracy, but needs ~5 GB RAM."),
    "large": ("large", "~10 GB RAM", "Slowest, best accuracy",
              "Best accuracy, but very slow & needs ~10 GB RAM."),
}

# Tooltip info for task
TASK_TOOLTIPS = {
    "transcribe": "Transcribe in the original audio language.",
    "translate": "Transcribe + translate to English.",
}

# Tooltip info for device
DEVICE_TOOLTIPS = {
    "auto": "Auto-select (CUDA if available, CPU otherwise).",
    "cpu": "Process on CPU (slow, but compatible).",
    "cuda": "Process on NVIDIA GPU (fast, requires CUDA)."
}

# Daftar bahasa yang didukung
LANGUAGE_OPTIONS = {
    "id": "Indonesia",
    "en": "English",
    "ja": "日本語 (Japanese)",
    "ar": "العربية (Arabic)",
    "zh": "中文 (Chinese)",
    "ms": "Melayu (Malay)",
    "th": "ไทย (Thai)",
    "vi": "Tiếng Việt",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
    "ru": "Русский",
    "ko": "한국어 (Korean)",
    "nl": "Nederlands",
    "it": "Italiano",
    "tr": "Türkçe",
    "hi": "हिन्दी (Hindi)",
}

# Task options
TASK_OPTIONS = [
    ("transcribe", "Transcribe — Original language"),
    ("translate", "Translate — To English"),
]


class SettingsPanel(ctk.CTkFrame):
    """Configuration panel for model, language, task, device, and output formats."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.devices = get_available_devices()
        self.cuda_status = get_cuda_status()

        # Variables
        self.model_var = ctk.StringVar(value="small")
        self.language_var = ctk.StringVar(value="id")
        self.task_var = ctk.StringVar(value="transcribe")
        self.device_var = ctk.StringVar(value="auto")
        self.format_txt_var = ctk.BooleanVar(value=True)
        self.format_srt_var = ctk.BooleanVar(value=True)
        self.format_vtt_var = ctk.BooleanVar(value=True)
        self.format_pdf_var = ctk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        """Build settings UI components."""
        # Title
        label_title = ctk.CTkLabel(
            self,
            text="⚙️ Transcription Settings",
            font=("Segoe UI", 14, "bold"),
        )
        label_title.pack(pady=(10, 5))

        # Grid settings
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=20, pady=5)

        # Row 0: Model
        ctk.CTkLabel(
            self.grid_frame, text="Model:", font=("Segoe UI", 12), anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)

        self.model_menu = ctk.CTkOptionMenu(
            self.grid_frame,
            values=list(MODEL_OPTIONS.keys()),
            variable=self.model_var,
            command=self._on_model_change,
            width=120,
        )
        self.model_menu.grid(row=0, column=1, sticky="w", pady=5)

        self.model_info = ctk.CTkLabel(
            self.grid_frame,
            text="Balanced — recommended default.",
            font=("Segoe UI", 11),
            text_color="#888888",
            anchor="w",
        )
        self.model_info.grid(row=0, column=2, sticky="w", padx=(10, 0), pady=5)

        # Row 1: Language
        ctk.CTkLabel(
            self.grid_frame, text="Language:", font=("Segoe UI", 12), anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)

        language_display = [
            f"{code} — {name}"
            for code, name in LANGUAGE_OPTIONS.items()
        ]
        self.language_menu = ctk.CTkOptionMenu(
            self.grid_frame,
            values=language_display,
            command=self._on_language_change,
            width=250,
        )
        self.language_menu.grid(row=1, column=1, columnspan=2, sticky="w", pady=5)

        # Set default — look for code "id" dynamically
        default_lang = next(
            (d for d in language_display if d.startswith("id")),
            language_display[0]
        )
        self.language_menu.set(default_lang)

        # Row 2: Task
        ctk.CTkLabel(
            self.grid_frame, text="Task:", font=("Segoe UI", 12), anchor="w"
        ).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)

        self.task_frame_inner = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        self.task_frame_inner.grid(row=2, column=1, columnspan=2, sticky="w", pady=5)

        for i, (value, label) in enumerate(TASK_OPTIONS):
            rb = ctk.CTkRadioButton(
                self.task_frame_inner,
                text=label,
                variable=self.task_var,
                value=value,
                font=("Segoe UI", 12),
                command=self._on_task_change,
            )
            rb.pack(side="left", padx=(0, 15))

        # Row 3: Task info (own row for tooltip)
        self.task_info = ctk.CTkLabel(
            self.grid_frame,
            text=TASK_TOOLTIPS.get("transcribe", ""),
            font=("Segoe UI", 11),
            text_color="#888888",
            anchor="w",
        )
        self.task_info.grid(row=3, column=1, sticky="w", padx=(0, 10), pady=5)

        # Row 4: Device
        ctk.CTkLabel(
            self.grid_frame, text="Device:", font=("Segoe UI", 12), anchor="w"
        ).grid(row=4, column=0, sticky="w", padx=(0, 10), pady=5)

        device_values = ["auto — Auto select"]
        seen_types = set()
        for dev in self.devices:
            if dev["available"] and dev["type"] not in seen_types:
                device_values.append(dev["type"])
                seen_types.add(dev["type"])
        self.device_menu = ctk.CTkOptionMenu(
            self.grid_frame,
            values=device_values,
            variable=self.device_var,
            command=self._on_device_change,
            width=200,
        )
        self.device_menu.grid(row=4, column=1, sticky="w", pady=5)

        # CUDA status
        if self.cuda_status["available"]:
            cuda_text = "✅ CUDA Available"
            cuda_color = "#4CAF50"
        elif self.cuda_status["nvidia_gpus"]:
            gpu_list = ", ".join(self.cuda_status["nvidia_gpus"])
            cuda_text = f"⚠️ {gpu_list} (install CUDA torch)"
            cuda_color = "#FF9800"
        else:
            cuda_text = "❌ CUDA Not Available"
            cuda_color = "#FF5252"

        self.cuda_label = ctk.CTkLabel(
            self.grid_frame,
            text=cuda_text,
            font=("Segoe UI", 11),
            text_color=cuda_color,
            anchor="w",
        )
        self.cuda_label.grid(row=4, column=2, sticky="w", padx=(10, 0), pady=5)

        # Row 5: Device info (own row for tooltip)
        device_info_text = (
            self.cuda_status.get("install_hint")
            if not self.cuda_status["available"] and self.cuda_status["nvidia_gpus"]
            else DEVICE_TOOLTIPS.get("auto", "")
        )
        self.device_info = ctk.CTkLabel(
            self.grid_frame,
            text=device_info_text,
            font=("Segoe UI", 11),
            text_color="#888888",
            anchor="w",
            wraplength=500,
            justify="left",
        )
        self.device_info.grid(row=5, column=1, columnspan=2, sticky="w", padx=(0, 10), pady=5)

        # Row 6: Output Format
        ctk.CTkLabel(
            self.grid_frame, text="Format:", font=("Segoe UI", 12), anchor="w"
        ).grid(row=6, column=0, sticky="w", padx=(0, 10), pady=5)

        self.format_frame_inner = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        self.format_frame_inner.grid(row=6, column=1, columnspan=2, sticky="w", pady=5)

        cb_txt = ctk.CTkCheckBox(
            self.format_frame_inner,
            text="TXT",
            variable=self.format_txt_var,
            font=("Segoe UI", 12),
        )
        cb_txt.pack(side="left", padx=(0, 10))

        cb_srt = ctk.CTkCheckBox(
            self.format_frame_inner,
            text="SRT (Subtitle)",
            variable=self.format_srt_var,
            font=("Segoe UI", 12),
        )
        cb_srt.pack(side="left", padx=(0, 10))

        cb_vtt = ctk.CTkCheckBox(
            self.format_frame_inner,
            text="VTT (Web)",
            variable=self.format_vtt_var,
            font=("Segoe UI", 12),
        )
        cb_vtt.pack(side="left", padx=(0, 10))

        cb_pdf = ctk.CTkCheckBox(
            self.format_frame_inner,
            text="PDF",
            variable=self.format_pdf_var,
            font=("Segoe UI", 12),
        )
        cb_pdf.pack(side="left", padx=(0, 10))

    def _on_model_change(self, choice: str):
        """Update model info when selection changes."""
        info = MODEL_OPTIONS.get(choice, {})
        tooltip = info[3] if len(info) >= 4 else ""
        self.model_info.configure(text=tooltip)

    def _on_language_change(self, choice: str):
        """Update language var when selection changes."""
        code = choice.split(" — ")[0].strip()
        self.language_var.set(code)

    def _on_task_change(self):
        """Update task tooltip when selection changes."""
        task = self.task_var.get()
        tooltip = TASK_TOOLTIPS.get(task, "")
        self.task_info.configure(text=tooltip)

    def _on_device_change(self, choice: str):
        """Update device var and tooltip when selection changes."""
        if choice.startswith("auto"):
            self.device_var.set("auto")
        elif "cuda" in choice.lower():
            self.device_var.set("cuda")
        else:
            self.device_var.set("cpu")

        # Update tooltip
        dev = self.device_var.get()
        tooltip = DEVICE_TOOLTIPS.get(dev, "")
        self.device_info.configure(text=tooltip)

    def load_from_settings(self, settings: dict):
        """Load values from settings dict into UI."""
        if "default_model" in settings:
            model = settings["default_model"]
            if model in MODEL_OPTIONS:
                self.model_var.set(model)
                self._on_model_change(model)

        if "default_language" in settings:
            lang = settings["default_language"]
            self.language_var.set(lang)
            # Find matching display text
            lang_display = next(
                (d for d in self.language_menu.cget("values")
                 if d.startswith(lang)),
                None
            )
            if lang_display:
                self.language_menu.set(lang_display)

        if "default_task" in settings:
            task = settings["default_task"]
            if task in dict(TASK_OPTIONS):
                self.task_var.set(task)
                self._on_task_change()

        if "default_device" in settings:
            dev = settings["default_device"]
            self.device_var.set(dev)
            # Find matching display
            for val in self.device_menu.cget("values"):
                if dev in val.lower():
                    self.device_menu.set(val)
                    break
            self._on_device_change(self.device_menu.get())

        if "default_formats" in settings:
            formats = settings["default_formats"]
            self.format_txt_var.set("txt" in formats)
            self.format_srt_var.set("srt" in formats)
            self.format_vtt_var.set("vtt" in formats)
            self.format_pdf_var.set("pdf" in formats)

    def get_settings_dict(self) -> dict:
        """Return settings as a dict for saving."""
        device = self.device_var.get()
        formats = []
        if self.format_txt_var.get():
            formats.append("txt")
        if self.format_srt_var.get():
            formats.append("srt")
        if self.format_vtt_var.get():
            formats.append("vtt")
        if self.format_pdf_var.get():
            formats.append("pdf")

        return {
            "default_model": self.model_var.get(),
            "default_language": self.language_var.get(),
            "default_task": self.task_var.get(),
            "default_device": device,
            "default_formats": formats,
        }

    def get_config(self) -> dict:
        """Return all settings as a config dict."""
        formats = []
        if self.format_txt_var.get():
            formats.append("txt")
        if self.format_srt_var.get():
            formats.append("srt")
        if self.format_vtt_var.get():
            formats.append("vtt")
        if self.format_pdf_var.get():
            formats.append("pdf")

        device = self.device_var.get()
        if device == "auto" or device.startswith("auto"):
            from app.core.device_checker import get_default_device
            device = get_default_device()

        return {
            "model": self.model_var.get(),
            "language": self.language_var.get(),
            "task": self.task_var.get(),
            "device": device,
            "formats": formats,
        }
