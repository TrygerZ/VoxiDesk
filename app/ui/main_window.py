"""Main application window for VoxiDesk."""

import time
import threading
import gc
import logging
from pathlib import Path
from queue import Queue, Empty
from datetime import datetime

import customtkinter as ctk

from app.ui.file_drop_widget import FileDropWidget
from app.ui.settings_panel import SettingsPanel
from app.ui.progress_panel import ProgressPanel
from app.ui.preview_panel import PreviewPanel
from app.ui.history_panel import HistoryPanel
from app.ui.dialogs import show_error, show_info, show_about
from app.core.ffmpeg_checker import check_ffmpeg
from app.core.file_utils import get_audio_duration
from app.data.history import History
from app.data.settings import AppSettings


class MainWindow(ctk.CTkFrame):
    """Main window that manages all panels and logic."""

    def __init__(self, master, settings: AppSettings | None = None, **kwargs):
        """
        Initialize MainWindow.

        Args:
            master: Parent widget
            settings: AppSettings instance for persistence
        """
        super().__init__(master, **kwargs)

        self.pack(fill="both", expand=True)

        # Settings & History
        self.app_settings = settings or AppSettings()
        self.history = History()

        # Queue for worker -> UI communication
        self.progress_queue: Queue = Queue()
        self.result_queue: Queue = Queue()

        # Worker state
        self.worker = None  # TranscriptionWorker (imported lazily)
        self.is_processing = False
        self.is_cancelling = False

        # Batch processing state
        self.batch_files: list[Path] = []
        self.batch_index: int = 0
        self.batch_total: int = 0
        self.batch_config: dict = {}
        self.batch_start_time: float = 0.0
        self.file_start_time: float = 0.0
        self._last_logged_pct: int = -1
        self.batch_results: list[dict] = []

        # Check FFmpeg at startup
        self.ffmpeg_status = check_ffmpeg()

        # Build UI
        self._build_ui()

        # Load settings from file
        self._load_settings()

        # Start polling queues
        self._poll_queues()

    def _build_ui(self):
        """Build UI components with Transcribe and History tabs."""
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.top_bar.pack(fill="x", padx=10, pady=(5, 0))

        self.label_app_title = ctk.CTkLabel(
            self.top_bar,
            text="🎙️ VoxiDesk",
            font=("Segoe UI", 14, "bold"),
        )
        self.label_app_title.pack(side="left")

        self.btn_theme = ctk.CTkButton(
            self.top_bar,
            text="🌙 Dark",
            command=self._toggle_theme,
            width=80,
            height=28,
            font=("Segoe UI", 11),
        )
        self.btn_theme.pack(side="right", padx=(5, 0))
        self._update_theme_button()

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_transcribe = self.tab_view.add("🎤 Transcribe")
        self._build_transcribe_tab()

        self.tab_history = self.tab_view.add("📜 History")
        self.history_panel = HistoryPanel(self.tab_history, history=self.history)
        self.history_panel.pack(fill="both", expand=True)

    def _build_transcribe_tab(self):
        """Build UI components in the Transcribe tab."""
        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_transcribe)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.file_drop = FileDropWidget(self.scroll_frame)
        self.file_drop.pack(fill="x", pady=(0, 10))
        self.file_drop.set_on_file_change(self._on_file_changed)

        self.settings_panel = SettingsPanel(self.scroll_frame)
        self.settings_panel.pack(fill="x", pady=(0, 10))

        self.action_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_transcribe = ctk.CTkButton(
            self.action_frame,
            text="▶ Transcribe!",
            command=self._start_transcription,
            height=40,
            font=("Segoe UI", 14, "bold"),
            state="disabled",
        )
        self.btn_transcribe.pack(side="left", padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(
            self.action_frame,
            text="⏹ Cancel",
            command=self._cancel_transcription,
            height=40,
            width=100,
            font=("Segoe UI", 12),
            fg_color="#8B0000",
            hover_color="#A52A2A",
            state="disabled",
        )
        self.btn_cancel.pack(side="left", padx=(0, 10))

        self.btn_about = ctk.CTkButton(
            self.action_frame,
            text="ℹ️ About",
            command=self._show_about,
            width=100,
            height=40,
            font=("Segoe UI", 12),
        )
        self.btn_about.pack(side="left", padx=(0, 10))

        self.progress_panel = ProgressPanel(self.scroll_frame)
        self.progress_panel.pack(fill="x", pady=(0, 10))

        self.preview_panel = PreviewPanel(self.scroll_frame)
        self.preview_panel.pack(fill="both", pady=(0, 10), expand=True)

        # Warning if FFmpeg is not found
        if not self.ffmpeg_status["available"]:
            self._show_ffmpeg_warning()


    def _toggle_theme(self):
        """Toggle between Dark and Light mode."""
        current = ctk.get_appearance_mode()
        new_mode = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self._update_theme_button()
        self.app_settings.set("theme", new_mode)

    def _update_theme_button(self):
        """Update theme button text based on active mode."""
        current = ctk.get_appearance_mode()
        if current == "Dark":
            self.btn_theme.configure(text="☀️ Light")
        else:
            self.btn_theme.configure(text="🌙 Dark")

    def _show_ffmpeg_warning(self):
        """Show warning if FFmpeg is not found."""
        warning_label = ctk.CTkLabel(
            self.scroll_frame,
            text="⚠️ FFmpeg not found. Transcription cannot run. "
                 "Make sure FFmpeg is installed or the bundled FFmpeg is available.",
            font=("Segoe UI", 12),
            text_color="#FF9800",
            wraplength=800,
        )
        warning_label.pack(padx=20, pady=(0, 10))

    def _load_settings(self):
        """Load settings from file and apply to UI."""
        settings = self.app_settings.get_all()

        # Theme already set in App.__init__(), just update button text
        self._update_theme_button()

        self.settings_panel.load_from_settings(settings)

    def _save_settings(self):
        """Save settings from UI to file."""
        settings = self.settings_panel.get_settings_dict()
        settings["theme"] = ctk.get_appearance_mode()
        
        # Only save window dimensions if it's not minimized and has a valid size
        toplevel = self.winfo_toplevel()
        if toplevel.state() != "iconic":
            w = self.winfo_width()
            h = self.winfo_height()
            if w > 100 and h > 100:
                settings["window_width"] = w
                settings["window_height"] = h
                
        self.app_settings.update(settings)

    def _on_file_changed(self, files: list[Path]):
        """Callback when the file list changes."""
        if files and not self.is_processing:
            count = len(files)
            label = "file" if count == 1 else "files"
            self.btn_transcribe.configure(
                state="normal",
                text=f"▶ Transcribe ({count} {label})"
            )
        elif not files:
            self.btn_transcribe.configure(state="disabled", text="▶ Transcribe!")

    def get_selected_files(self) -> list[Path]:
        """Return the list of files from the widget."""
        return self.file_drop.get_files()



    def _start_transcription(self):
        """Start batch transcription process."""
        files = self.get_selected_files()
        if not files:
            show_error("No Files", "Please select audio/video files first.")
            return

        if not self.ffmpeg_status["available"]:
            show_error(
                "FFmpeg Not Found",
                "FFmpeg was not found on the system.\n\n"
                "Ensure the ffmpeg/bin/ folder exists in the VoxiDesk directory "
                "or FFmpeg is installed on your system.",
            )
            return

        config = self.settings_panel.get_config()
        if not config["formats"]:
            show_error(
                "No Output Format",
                "Please select at least one output format (TXT, SRT, or VTT).",
            )
            return

        # Choose output folder (use parent of first file as default)
        from tkinter import filedialog
        output_dir = filedialog.askdirectory(
            title="Select output folder",
            initialdir=str(files[0].parent),
        )
        if not output_dir:
            return  # User cancel

        # Verify writability
        try:
            test_path = Path(output_dir)
            test_path.mkdir(parents=True, exist_ok=True)
            test_file = test_path / ".voxidesk_test_write"
            test_file.touch()
            test_file.unlink()
        except OSError as e:
            show_error(
                "Folder Access Error",
                f"Cannot write to the selected folder:\n{output_dir}\n\nError: {e}\n\nPlease select a different folder."
            )
            return

        config["output_dir"] = output_dir

        # Reset UI
        self.progress_panel.reset()
        self.preview_panel.clear()
        
        self.progress_panel.set_status("Preparing batch...")
        self.progress_panel.append_log(
            f"📁 {len(files)} file(s) to process"
        )
        self.progress_panel.append_log(
            f"📐 Model: {config['model']} | Lang: {config['language']} "
            f"| Device: {config['device']}"
        )
        self.progress_panel.append_log(f"📂 Output: {output_dir}")

        # Set batch state
        self.batch_files = list(files)
        self.batch_index = 0
        self.batch_total = len(files)
        self.batch_config = config
        self.batch_results = []
        self.batch_start_time = time.time()

        # Disable buttons
        self.btn_transcribe.configure(state="disabled", text="⏳ Batch...")
        self.btn_cancel.configure(state="normal")
        self.is_processing = True

        # Process first file
        self._process_next_file()

    def _process_next_file(self):
        """Process the next file in batch."""
        self._last_logged_pct = -1
        if self.batch_index >= self.batch_total:
            # All done
            self._on_batch_complete()
            return

        file_path = self.batch_files[self.batch_index]
        config = dict(self.batch_config)

        # Update status
        current = self.batch_index + 1
        total = self.batch_total
        self.progress_panel.append_log("")
        self.progress_panel.append_log(
            f"{'='*50}"
        )
        self.progress_panel.set_status(
            f"📄 File {current}/{total}: {file_path.name}"
        )
        self.progress_panel.append_log(
            f"📄 File {current}/{total}: {file_path.name}"
        )

        # Clear queues
        while not self.progress_queue.empty():
            try:
                self.progress_queue.get_nowait()
            except Empty:
                break
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except Empty:
                break

        # Start worker for this file
        self.file_start_time = time.time()
        from app.worker.transcription_worker import TranscriptionWorker
        self.worker = TranscriptionWorker(
            file_path=str(file_path),
            config=config,
            progress_queue=self.progress_queue,
            result_queue=self.result_queue,
        )
        self.worker.start()

    def _cancel_transcription(self):
        """Cancel transcription with confirmation."""
        if not self.is_processing or not self.worker:
            return

        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Confirm")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 150) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="Are you sure you want to cancel?",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            dialog,
            text="The ongoing process will be stopped.",
            font=("Segoe UI", 12),
            text_color="#888888",
        ).pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=(0, 15))

        def do_cancel():
            if dialog.winfo_exists():
                dialog.destroy()
            if self.worker and not self.is_cancelling:
                self.is_cancelling = True
                self.btn_cancel.configure(state="disabled")
                self.progress_panel.set_status("Cancelling...")
                
                worker_ref = self.worker
                def cancel_thread():
                    worker_ref.cancel()
                    # Block until the worker thread actually exits to prevent orphaned threads
                    # holding onto CUDA VRAM. Since cancel_flag is set, it will exit soon.
                    worker_ref.join(timeout=3.0)
                    gc.collect()
                    if self.worker is worker_ref:
                        self.result_queue.put(("cancelled", None))
                    
                threading.Thread(target=cancel_thread, daemon=True).start()

        ctk.CTkButton(
            btn_frame, text="Yes, Cancel", command=do_cancel,
            width=100, fg_color="#8B0000", hover_color="#A52A2A",
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Continue", command=lambda: dialog.winfo_exists() and dialog.destroy(),
            width=100,
        ).pack(side="left", padx=5)

    def _on_progress(self, current: int, total: int, text: str):
        """Handler for progress updates from worker."""
        if total > 0:
            pct = current / total
            self.progress_panel.update_progress(pct)
        if text and text.strip():
            self.progress_panel.set_status(text.strip())
            # Log only every 5% change to prevent spam
            if total > 0:
                new_pct = int((current / total) * 100)
                if getattr(self, "_last_logged_pct", -1) < 0 or (new_pct - getattr(self, "_last_logged_pct", -1)) >= 5:
                    self.progress_panel.append_log(f"  {text.strip()}")
                    self._last_logged_pct = new_pct
            else:
                # If total is 0, don't spam the log, just log once or rely on set_status
                if getattr(self, "_last_logged_pct", -1) != -2:
                    self.progress_panel.append_log(f"  {text.strip()}")
                    self._last_logged_pct = -2

    def _on_complete(self, result: dict):
        """Handler when one file is done transcribing."""
        if not self.is_processing:
            return

        elapsed = time.time() - self.file_start_time
        self.progress_panel.set_indeterminate(False)
        self.progress_panel.update_progress(1.0)
        self.progress_panel.set_status(
            f"✅ File done! ({elapsed:.1f} sec)"
        )
        self.progress_panel.append_log(
            f"✅ Completed in {elapsed:.1f} sec"
        )

        # Display result (preview)
        text = result.get("text", "")
        segments = result.get("segments", [])
        self.preview_panel.show_result(text, segments)

        # Saved files info
        saved_files = result.get("saved_files", {})
        if saved_files:
            self.progress_panel.append_log("📁 Saved files:")
            for fmt, path in saved_files.items():
                self.progress_panel.append_log(f"   • {fmt.upper()}: {path}")

        # Calculate statistics
        segments = result.get("segments", [])
        audio_duration = result.get("duration", 0)
        language = result.get("language", "")
        word_count = len(text.split())
        file_path = self.batch_files[self.batch_index]

        self.progress_panel.append_log(
                f"📊 Stats: {word_count} words, "
                f"{len(segments)} segments, "
                f"duration {audio_duration:.1f}s, "
                f"language {language}"
        )

        self._save_history_entry(
            file_path=file_path,
            result=result,
            process_duration=elapsed,
            saved_files=saved_files,
        )

        # Save batch result
        self.batch_results.append(result)

        # Continue to next file
        if not self.is_cancelling:
            self.batch_index += 1
            self._process_next_file()

    def _on_batch_complete(self):
        """Handler when all files are processed."""
        total_elapsed = time.time() - self.batch_start_time
        self.progress_panel.set_status(
            f"✅ Batch complete! ({self.batch_total} files, {total_elapsed:.1f} sec)"
        )
        self.progress_panel.append_log("")
        self.progress_panel.append_log(
            f"{'='*50}"
        )
        self.progress_panel.append_log(
            f"✅ Batch complete! {self.batch_total} files processed "
            f"in {total_elapsed:.1f} sec"
        )

        # Calculate totals
        total_words = sum(
            len(r.get("text", "").split()) for r in self.batch_results
        )
        self.progress_panel.append_log(
            f"📊 Total: {total_words} words from {self.batch_total} files"
        )

        show_info(
            "Batch Complete",
            f"All {self.batch_total} files have been processed.\n"
            f"Total time: {total_elapsed:.1f} sec.\n"
            f"Results saved to the selected folder.",
        )

        # Refresh history panel
        self.history_panel._refresh()

        # Reset UI
        self._reset_ui()

    def _on_error(self, error: dict):
        """Handler when an error occurs."""
        if self.is_cancelling:
            return

        self.progress_panel.set_indeterminate(False)
        self.progress_panel.update_progress(0)
        self.progress_panel.set_status("❌ Error")

        show_error(
            "Transcription Error",
            error.get("message", "An unknown error occurred"),
            error.get("detail"),
        )

        # Ask whether to continue to next file
        if self.batch_index < self.batch_total - 1:
            from app.ui.dialogs import show_confirm
            proceed = show_confirm(
                "Continue Batch?",
                "File failed to process. Continue to next file?",
                master=self.winfo_toplevel()
            )
            if proceed:
                self.batch_index += 1
                self._process_next_file()
            else:
                self._reset_ui()
        else:
            self._reset_ui()

    def _on_cancelled(self):
        """Handler when transcription is cancelled."""
        self.is_cancelling = False
        self.progress_panel.set_indeterminate(False)
        self.progress_panel.update_progress(0)
        self.progress_panel.set_status("⏹ Cancelled")
        self.progress_panel.append_log("⏹ Transcription cancelled by user.")

        # Record results completed before cancellation
        if self.batch_results:
            self.progress_panel.append_log(
                f"ℹ️ {len(self.batch_results)}/{self.batch_total} files "
                f"were processed before cancellation."
            )

        self._reset_ui()

    def _save_history_entry(
        self,
        file_path: Path,
        result: dict,
        process_duration: float,
        saved_files: dict,
    ):
        """Save transcription result to history."""
        try:
            text = result.get("text", "").strip()
            audio_duration = result.get("duration", 0)
            config = self.batch_config

            try:
                file_size = file_path.stat().st_size
            except OSError:
                file_size = 0

            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_name": file_path.name,
                "file_size": file_size,
                "model": config.get("model", ""),
                "language": config.get("language", ""),
                "task": config.get("task", ""),
                "device": config.get("device", ""),
                "duration_audio": audio_duration,
                "duration_process": process_duration,
                "output_files": {
                    fmt: str(path) for fmt, path in saved_files.items()
                },
                "text_preview": text[:300] if text else "",
            }
            self.history.add_entry(entry)
        except Exception as e:
            import logging
            logging.error(f"Failed to save history entry: {e}")
            try:
                self.progress_panel.append_log(f"⚠️ Warning: Failed to save history ({e})")
                from app.ui.dialogs import show_error
                show_error(
                    "History Save Error",
                    f"Failed to save transcription history:\n{e}",
                    master=self.winfo_toplevel()
                )
            except Exception:
                pass

    def _reset_ui(self):
        """Reset UI to initial state."""
        self.is_processing = False
        self.is_cancelling = False
        self.worker = None
        self.batch_files = []
        self.batch_index = 0
        self.batch_results = []

        files = self.get_selected_files()
        if files:
            count = len(files)
            self.btn_transcribe.configure(
                state="normal",
                text=f"▶ Transcribe ({count} files)",
            )
        else:
            self.btn_transcribe.configure(
                state="disabled",
                text="▶ Transcribe!",
            )
        self.btn_cancel.configure(state="disabled")

    def _poll_queues(self):
        """Check queues for updates from worker (called via after)."""
        # Only poll actively when processing to reduce overhead
        if not self.is_processing:
            self.after(200, self._poll_queues)
            return

        try:
            progress_updates = []
            try:
                while True:
                    msg = self.progress_queue.get_nowait()
                    if msg[0] == "progress":
                        _, current, total, text = msg
                        if total > 0:
                            progress_updates.append((current, total, text))
                    elif msg[0] == "status":
                        _, text = msg
                        self.progress_panel.set_status(text)
                        self.progress_panel.append_log(f"ℹ️ {text}")
                    else:
                        print(f"[VoxiDesk] Unknown progress message: {msg}")
                        continue
            except Empty:
                pass

            # ⬇️ Call _on_progress OUTSIDE the try/except Empty block
            for cur, tot, txt in progress_updates:
                self._on_progress(cur, tot, txt)

            try:
                msg = self.result_queue.get_nowait()
                if msg[0] == "result":
                    self._on_complete(msg[1])
                elif msg[0] == "error":
                    self._on_error(msg[1])
                elif msg[0] == "cancelled":
                    self._on_cancelled()
            except Empty:
                pass
        except Exception as e:
            print(f"[VoxiDesk] Queue error: {e}")

        self.after(200, self._poll_queues)

    def _show_about(self):
        """Show about dialog."""
        show_about(master=self.winfo_toplevel())

    def on_close(self):
        """Clean up on window close."""
        if self.worker and self.is_processing:
            self.worker.cancel()
            self.worker.join(timeout=2.0)

        # Save settings
        self._save_settings()

