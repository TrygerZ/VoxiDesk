"""Transcription history management stored in history.json."""

import copy
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from threading import Lock

# Path to project root folder
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class History:
    """Persistent transcription history manager."""

    def __init__(self, path: str | Path | None = None):
        """
        Initialize History.

        Args:
            path: Path to history.json file. If None, defaults
                  to project root folder.
        """
        if path is None:
            path = ROOT_DIR / "history.json"
        self._path = Path(path)
        self._lock = Lock()
        self._entries: list[dict] = []
        self.load()

    @property
    def path(self) -> Path:
        """Path to history.json file."""
        return self._path

    def load(self) -> list[dict]:
        """Load history from JSON file with type validation and error differentiation."""
        with self._lock:
            if not self._path.exists():
                self._entries = []
                return self._entries

            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Type validation: must be list
                self._entries = data if isinstance(data, list) else []
                # Truncate after load to prevent memory issues
                if len(self._entries) > self.MAX_HISTORY:
                    self._entries = self._entries[: self.MAX_HISTORY]
            except json.JSONDecodeError as e:
                logging.error("History file corrupted at %s: %s", self._path, e)
                self._backup_corrupted()
                self._entries = []
            except PermissionError as e:
                logging.error("Permission denied reading history at %s: %s", self._path, e)
                self._entries = []
                # Do NOT overwrite file — fall back to in-memory empty list
            except OSError as e:
                logging.error("OS error reading history at %s: %s", self._path, e)
                self._entries = []

            # Sort newest first
            self._entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return self._entries

    def _backup_corrupted(self):
        """Backup a corrupted history file before resetting (caller MUST hold self._lock)."""
        if self._path.exists() and self._path.stat().st_size > 0:
            try:
                self._rotate_backup()
            except OSError as e:
                logging.warning("Failed to backup corrupted history: %s", e)

    def _rotate_backup(self):
        """Rotate backup files with timestamp, keeping versioned copies."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = self._path.with_suffix(f".json.bak.{timestamp}")
        try:
            shutil.copy2(self._path, backup_path)
        except OSError as e:
            logging.warning("Failed to create backup at %s: %s", backup_path, e)

    def _save_internal(self):
        """Write entries to disk atomically (caller MUST hold self._lock)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        try:
            # Backup existing file before overwriting
            if self._path.exists():
                self._rotate_backup()

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self._path)
        except OSError as e:
            logging.error("Failed to save history to %s: %s", self._path, e)
            # Clean up temp file if it exists
            if tmp_path.exists():
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def save(self):
        """Save history to JSON file."""
        with self._lock:
            self._save_internal()

    MAX_HISTORY = 1000

    def add_entry(self, entry: dict):
        """
        Add a new entry to the history.

        Args:
            entry: Dict with keys:
                - timestamp (str): Transcription timestamp
                - file_name (str): File name
                - file_size (int): File size in bytes
                - model (str): Model name
                - language (str): Language code
                - task (str): Transcription task
                - device (str): Device used
                - duration_audio (float): Audio duration in seconds
                - duration_process (float): Process duration in seconds
                - output_files (dict): Dict format -> path
                - text_preview (str): Result text preview
        """
        # Validate entry has required fields
        if not isinstance(entry, dict) or "timestamp" not in entry or "file_name" not in entry:
            logging.warning("Invalid history entry rejected: missing required fields (timestamp, file_name)")
            return False

        with self._lock:
            self._entries.insert(0, entry)  # Insert at beginning (newest first)
            # Limit history
            if len(self._entries) > self.MAX_HISTORY:
                self._entries = self._entries[:self.MAX_HISTORY]
            self._save_internal()
        return True

    def get_all(self) -> list[dict]:
        """Return all history entries as deep copies to prevent external mutation."""
        with self._lock:
            return copy.deepcopy(self._entries)

    def get_recent(self, n: int = 10) -> list[dict]:
        """Return the most recent n entries as deep copies."""
        with self._lock:
            return copy.deepcopy(self._entries[:n])

    def clear(self):
        """Clear all history."""
        with self._lock:
            self._entries = []
            self._save_internal()

    def count(self) -> int:
        """Return the number of history entries."""
        return len(self._entries)
