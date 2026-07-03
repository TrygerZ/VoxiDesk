"""Main application window for VoxiDesk."""

import time
import threading
import gc
import logging
from pathlib import Path
from queue import Queue, Empty
from datetime import datetime

import customtkinter as ctk

from app.ui import theme
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

        # Worker lifecycle state flags
        self._pending_error: dict | None = None  # Deferred error for worker_done handler
        self._error_continue = False   # User chose to continue batch after error
        self._error_stop = False       # User chose to stop batch after error

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

        # Debounce timer for auto-save
        self._save_timer = None

        # Build UI
        self._build_ui()

        # Load settings from file
        self._load_settings()

        # Connect auto-save callback
        self.settings_panel.set_on_change(self._on_settings_changed)

        # Start polling queues
        self._poll_queues()

    def _build_ui(self):
        """Build UI components with Transcribe and History tabs."""
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent", height=36)
        self.top_bar.pack(fill="x", padx=theme.PAD_X, pady=(theme.PAD_Y, 0))

        # Wordmark: a thin orange accent tick sets the brand color without emoji.
        self.title_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.title_frame.pack(side="left")

        self.accent_tick = ctk.CTkFrame(
            self.title_frame,
            fg_color=theme.ACCENT,
            width=4,
            height=20,
            corner_radius=2,
        )
        self.accent_tick.pack(side="left", padx=(0, 10))

        self.label_app_title = ctk.CTkLabel(
            self.title_frame,
            text="VoxiDesk",
            font=theme.font(16, "bold"),
            text_color=theme.TEXT,
        )
        self.label_app_title.pack(side="left")

        self.label_app_tagline = ctk.CTkLabel(
            self.top_bar,
            text="Audio & video transcription",
            font=theme.FONT_CAPTION,
            text_color=theme.TEXT_MUTED,
        )
        self.label_app_tagline.pack(side="right", padx=(0, 4))

        self.tab_view = ctk.CTkTabview(
            self,
            fg_color=theme.SURFACE,
            segmented_button_selected_color=theme.ACCENT,
            segmented_button_selected_hover_color=theme.ACCENT_HOVER,
        )
        self.tab_view.pack(fill="both", expand=True, padx=theme.PAD_X, pady=theme.PAD_Y)

        self.tab_transcribe = self.tab_view.add("Transcribe")
        self._build_transcribe_tab()

        self.tab_history = self.tab_view.add("History")
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
        self.action_frame.pack(fill="x", padx=theme.PAD_X, pady=(0, theme.GAP))

        self.btn_transcribe = ctk.CTkButton(
            self.action_frame,
            text="Transcribe",
            command=self._start_transcription,
            height=44,
            font=theme.font(14, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT_ON_ACCENT,
            corner_radius=theme.RADIUS_BTN,
            state="disabled",
        )
        self.btn_transcribe.pack(side="left", padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(
            self.action_frame,
            text="Cancel",
            command=self._cancel_transcription,
            height=44,
            width=100,
            font=theme.FONT_BODY,
            fg_color="transparent",
            hover_color=theme.SURFACE_HI,
            text_color=theme.DANGER,
            border_width=1,
            border_color=theme.DANGER,
            corner_radius=theme.RADIUS_BTN,
            state="disabled",
        )
        self.btn_cancel.pack(side="left", padx=(0, 10))

        self.btn_about = ctk.CTkButton(
            self.action_frame,
            text="About",
            command=self._show_about,
            width=100,
            height=44,
            font=theme.FONT_BODY,
            fg_color="transparent",
            hover_color=theme.SURFACE_HI,
            text_color=theme.TEXT_MUTED,
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=theme.RADIUS_BTN,
        )
        self.btn_about.pack(side="left", padx=(0, 10))

        self.progress_panel = ProgressPanel(self.scroll_frame)
        self.progress_panel.pack(fill="x", pady=(0, 10))

        self.preview_panel = PreviewPanel(self.scroll_frame)
        self.preview_panel.pack(fill="both", pady=(0, 10), expand=True)

        # Warning if FFmpeg is not found
        if not self.ffmpeg_status["available"]:
            self._show_ffmpeg_warning()


    def _show_ffmpeg_warning(self):
        """Show warning if FFmpeg is not found."""
        warning_label = ctk.CTkLabel(
            self.scroll_frame,
            text="FFmpeg not found. Transcription cannot run. "
                 "Make sure FFmpeg is installed or the bundled FFmpeg is available.",
            font=theme.FONT_BODY,
            text_color=theme.WARNING,
            wraplength=800,
        )
        warning_label.pack(padx=theme.PAD_X, pady=(0, theme.GAP))

    def _load_settings(self):
        """Load settings from file and apply to UI."""
        settings = self.app_settings.get_all()

        # Appearance is fixed to Dark in App.__init__() (dark-only design),
        # so there is no theme control to sync here.
        self.settings_panel.load_from_settings(settings)

    def _save_settings(self):
        """Save settings from UI to file."""
        settings = self.settings_panel.get_settings_dict()
        settings["theme"] = ctk.get_appearance_mode()
        
        # Only save window dimensions if it's not minimized and has a valid size
        toplevel = self.winfo_toplevel()
        if toplevel.state() != "iconic":
            w = toplevel.winfo_width()
            h = toplevel.winfo_height()
            if w > 100 and h > 100:
                settings["window_width"] = w
                settings["window_height"] = h
                
        self.app_settings.update(settings)

    def _on_settings_changed(self):
        """Debounced auto-save: waits 500ms idle before saving."""
        if self._save_timer is not None:
            self.after_cancel(self._save_timer)
        self._save_timer = self.after(500, self._save_settings)

    def _on_file_changed(self, files: list[Path]):
        """Callback when the file list changes."""
        if files and not self.is_processing:
            count = len(files)
            label = "file" if count == 1 else "files"
            self.btn_transcribe.configure(
                state="normal",
                text=f"Transcribe ({count} {label})"
            )
        elif not files:
            self.btn_transcribe.configure(state="disabled", text="Transcribe")

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
        self.btn_transcribe.configure(state="disabled", text="Processing…")
        self.btn_cancel.configure(state="normal")
        self.is_processing = True

        # Process first file
        self._process_next_file()

    def _process_next_file(self):
        """Process the next file in batch."""
        # Safety: ensure previous worker is fully joined before starting new one
        if self.worker is not None:
            if self.worker.is_alive():
                self.worker.join(timeout=10.0)
                if self.worker.is_alive():
                    logging.warning("[VoxiDesk] Previous worker still alive after 10s join")
            self.worker = None

        # Reset deferred error state
        self._pending_error = None
        self._error_continue = False
        self._error_stop = False

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
        dialog.geometry("360x170")
        dialog.resizable(False, False)
        dialog.configure(fg_color=theme.BG_BASE)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 360) // 2
        y = self.winfo_y() + (self.winfo_height() - 170) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="Cancel transcription?",
            font=theme.FONT_TITLE,
            text_color=theme.TEXT,
        ).pack(pady=(24, 6))

        ctk.CTkLabel(
            dialog,
            text="The ongoing process will be stopped.",
            font=theme.FONT_BODY,
            text_color=theme.TEXT_MUTED,
        ).pack(pady=(0, 18))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=(0, 18))

        def do_cancel():
            if dialog.winfo_exists():
                dialog.destroy()
            if self.worker and not self.is_cancelling:
                self.is_cancelling = True
                self.btn_cancel.configure(state="disabled")
                self.progress_panel.set_status("Cancelling…")
                # Worker itself will detect cancel_flag, cleanup, and send
                # 'cancelled' + 'worker_done' signals via result_queue
                self.worker.cancel()

        ctk.CTkButton(
            btn_frame, text="Yes, cancel", command=do_cancel,
            width=110, height=36,
            fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER,
            text_color=theme.TEXT, corner_radius=theme.RADIUS_BTN,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame, text="Keep going",
            command=lambda: dialog.winfo_exists() and dialog.destroy(),
            width=110, height=36,
            fg_color="transparent", hover_color=theme.SURFACE_HI,
            text_color=theme.TEXT_MUTED, border_width=1, border_color=theme.BORDER,
            corner_radius=theme.RADIUS_BTN,
        ).pack(side="left", padx=6)

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

        # Ignore result if cancellation is in progress
        if self.is_cancelling:
            logging.info("[VoxiDesk] Ignoring result — cancellation in progress")
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

        # Advance to next file — actual start is deferred to 'worker_done' signal
        # to ensure the old worker has fully cleaned up (CUDA memory freed)
        if not self.is_cancelling:
            self.batch_index += 1

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
        """Handler when an error occurs.
        
        During cancellation: logs the error but skips the dialog.
        Normal flow: defers the error dialog to _handle_worker_done so the
        worker thread is fully cleaned up before user interaction.
        """
        if self.is_cancelling:
            # Log error during cancel — don't show dialog, don't skip silently
            logging.warning(
                f"[VoxiDesk] Error during cancel: {error.get('message', '')}"
            )
            self.progress_panel.append_log(
                f"⚠️ Error (during cancel): {error.get('message', '')}"
            )
            return

        # Store error for deferred handling in _handle_worker_done
        self._pending_error = error

    def _on_cancelled(self):
        """Handler when 'cancelled' signal received from worker.
        
        Phase 1 of cancel: update status/log only.
        Phase 2 (UI reset) happens in _handle_worker_done after worker exits.
        """
        self.progress_panel.set_indeterminate(False)
        self.progress_panel.update_progress(0)
        self.progress_panel.set_status("Cancelling…")
        self.progress_panel.append_log("Transcription cancelled by user.")

    def _handle_worker_done(self):
        """Handle 'worker_done' signal — worker thread has fully cleaned up.
        
        This is the single point where we decide what happens after a worker exits:
        - If cancelling: finalize cancel (reset UI)
        - If pending error: show deferred error dialog
        - If batch complete: finalize batch
        - Otherwise: start next file
        """
        # Join worker to ensure thread is fully reaped
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=10.0)
            if self.worker.is_alive():
                logging.warning("[VoxiDesk] Worker still alive after 10s join in worker_done")
        self.worker = None
        gc.collect()

        # --- Cancel flow: finalize ---
        if self.is_cancelling:
            if self.batch_results:
                self.progress_panel.append_log(
                    f"ℹ️ {len(self.batch_results)}/{self.batch_total} files "
                    f"were processed before cancellation."
                )
            self.progress_panel.set_status("Cancelled")
            self.is_cancelling = False
            self._reset_ui()
            return

        # --- Error flow: show deferred dialog ---
        if self._pending_error is not None:
            error = self._pending_error
            self._pending_error = None

            self.progress_panel.set_indeterminate(False)
            self.progress_panel.update_progress(0)
            self.progress_panel.set_status("❌ Error")

            # SEC-007: No detail parameter — traceback is in log only
            show_error(
                "Transcription Error",
                error.get("message", "An unknown error occurred"),
                master=self.winfo_toplevel(),
            )

            # Ask whether to continue to next file
            if self.batch_index < self.batch_total:
                from app.ui.dialogs import show_confirm
                proceed = show_confirm(
                    "Continue Batch?",
                    "File failed to process. Continue to next file?",
                    master=self.winfo_toplevel()
                )
                if proceed:
                    self._process_next_file()
                else:
                    self._reset_ui()
            else:
                self._reset_ui()
            return

        # --- Normal flow: next file or batch complete ---
        if self.batch_index >= self.batch_total:
            self._on_batch_complete()
        else:
            self._process_next_file()

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
                # SEC-007: Don't expose internal error details in UI
                logging.error("History save failed: %s", e)
                from app.ui.dialogs import show_error
                show_error(
                    "History Save Error",
                    "Failed to save transcription history. Details logged.",
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
                text=f"Transcribe ({count} files)",
            )
        else:
            self.btn_transcribe.configure(
                state="disabled",
                text="Transcribe",
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

            # Process ALL result messages in order — important because
            # 'worker_done' must come after 'result'/'cancelled'/'error'
            try:
                while True:
                    msg = self.result_queue.get_nowait()
                    if msg[0] == "result":
                        self._on_complete(msg[1])
                    elif msg[0] == "error":
                        self._on_error(msg[1])
                    elif msg[0] == "cancelled":
                        self._on_cancelled()
                    elif msg[0] == "worker_done":
                        self._handle_worker_done()
                    else:
                        logging.warning(f"[VoxiDesk] Unknown result message: {msg}")
            except Empty:
                pass
        except Exception as e:
            logging.exception("Queue polling error")
            try:
                self.progress_panel.append_log(f"⚠️ Internal error: {e}")
            except Exception:
                pass

        self.after(200, self._poll_queues)

    def _show_about(self):
        """Show about dialog."""
        show_about(master=self.winfo_toplevel())

    def on_close(self):
        """Clean up on window close.
        
        Ensures worker thread is fully joined before exit to prevent
        CUDA memory leaks and orphaned threads.
        """
        if self.worker is not None and self.worker.is_alive():
            self.worker.cancel()
            # Non-daemon worker needs time to unload model and free CUDA memory
            self.worker.join(timeout=30.0)
            if self.worker.is_alive():
                logging.warning(
                    "[VoxiDesk] Worker thread did not exit within 30s on close"
                )
            self.worker = None
            gc.collect()

        # Save settings
        self._save_settings()

