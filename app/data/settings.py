"""Application settings management stored in settings.json."""

import copy
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from threading import Lock

# Default settings
DEFAULT_SETTINGS = {
    "theme": "System",
    "default_model": "small",
    "default_language": "id",
    "default_task": "transcribe",
    "default_device": "auto",
    "default_formats": ["txt", "srt", "vtt", "pdf"],
    "window_width": 900,
    "window_height": 700,
}

# Path to project root folder
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = ROOT_DIR / "backups"
MAX_BACKUPS = 5


class AppSettings:
    """Persistent application settings manager."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path | None = None):
        """
        Initialize AppSettings.

        Args:
            path: Path to settings.json file. If None, defaults
                  to project root folder.
        """
        if path is None:
            path = ROOT_DIR / "settings.json"
        self._path = Path(path)
        self._lock = Lock()
        self._settings: dict = {}
        self.load()

    @property
    def path(self) -> Path:
        """Path to settings.json file."""
        return self._path

    def load(self) -> dict:
        """Load settings from JSON file with type validation and error differentiation."""
        with self._lock:
            if not self._path.exists():
                self._settings = dict(DEFAULT_SETTINGS)
                self._settings["__version__"] = self.SCHEMA_VERSION
                self._save_internal()
                return self._settings

            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Type validation: must be dict
                self._settings = data if isinstance(data, dict) else dict(DEFAULT_SETTINGS)
                # Ensure schema version is present
                if "__version__" not in self._settings:
                    self._settings["__version__"] = self.SCHEMA_VERSION
            except json.JSONDecodeError as e:
                logging.error("Settings file corrupted at %s: %s", self._path, e)
                self._backup_corrupted()
                self._settings = dict(DEFAULT_SETTINGS)
                self._settings["__version__"] = self.SCHEMA_VERSION
                self._save_internal()
            except PermissionError as e:
                logging.error("Permission denied reading settings at %s: %s", self._path, e)
                self._settings = dict(DEFAULT_SETTINGS)
                self._settings["__version__"] = self.SCHEMA_VERSION
                # Do NOT overwrite file — fall back to in-memory defaults
            except OSError as e:
                logging.error("OS error reading settings at %s: %s", self._path, e)
                self._settings = dict(DEFAULT_SETTINGS)
                self._settings["__version__"] = self.SCHEMA_VERSION
        return self._settings

    def _backup_corrupted(self):
        """Backup a corrupted settings file before resetting (caller MUST hold self._lock)."""
        if self._path.exists() and self._path.stat().st_size > 0:
            try:
                self._rotate_backup()
            except OSError as e:
                logging.warning("Failed to backup corrupted settings: %s", e)

    def _rotate_backup(self):
        """Rotate backup files with timestamp, keeping versioned copies."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / f"{self._path.stem}.bak.{timestamp}{self._path.suffix}"
        try:
            shutil.copy2(self._path, backup_path)
            self._cleanup_old_backups()
        except OSError as e:
            logging.warning("Failed to create backup at %s: %s", backup_path, e)

    def _cleanup_old_backups(self):
        """Remove oldest backup files beyond MAX_BACKUPS limit."""
        try:
            pattern = f"{self._path.stem}.bak.*{self._path.suffix}"
            backups = sorted(BACKUP_DIR.glob(pattern))
            while len(backups) > MAX_BACKUPS:
                oldest = backups.pop(0)
                oldest.unlink()
        except OSError as e:
            logging.warning("Failed to clean up old backups: %s", e)

    def _save_internal(self):
        """Write settings to disk atomically (caller MUST hold self._lock)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        try:
            # Backup existing file before overwriting
            if self._path.exists():
                self._rotate_backup()

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self._path)
        except OSError as e:
            logging.error("Failed to save settings to %s: %s", self._path, e)
            # Clean up temp file if it exists
            if tmp_path.exists():
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def save(self):
        """Save settings to JSON file."""
        with self._lock:
            self._save_internal()

    def get(self, key: str, default=None):
        """Get a setting value."""
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value and save to file."""
        with self._lock:
            self._settings[key] = value
            self._save_internal()

    def update(self, data: dict):
        """Update multiple settings at once."""
        with self._lock:
            self._settings.update(data)
            self._save_internal()

    def get_all(self) -> dict:
        """Return all settings as a deep copy to prevent external mutation."""
        with self._lock:
            return copy.deepcopy(self._settings)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        with self._lock:
            self._settings = dict(DEFAULT_SETTINGS)
            self._settings["__version__"] = self.SCHEMA_VERSION
            self._save_internal()
