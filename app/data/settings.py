"""Application settings management stored in settings.json."""

import json
from pathlib import Path
from threading import Lock

# Default settings
DEFAULT_SETTINGS = {
    "theme": "System",
    "default_model": "small",
    "default_language": "id",
    "default_task": "transcribe",
    "default_device": "auto",
    "default_formats": ["txt", "srt", "vtt"],
    "default_output_dir": "",
    "window_width": 900,
    "window_height": 700,
}

# Path to project root folder
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class AppSettings:
    """Persistent application settings manager."""

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
        """Load settings from JSON file."""
        with self._lock:
            try:
                if self._path.exists():
                    with open(self._path, "r", encoding="utf-8") as f:
                        self._settings = json.load(f)
                else:
                    self._settings = dict(DEFAULT_SETTINGS)
                    self.save()
            except (json.JSONDecodeError, OSError):
                self._settings = dict(DEFAULT_SETTINGS)
                self.save()
        return self._settings

    def save(self):
        """Save settings to JSON file."""
        try:
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # Failed to save, ignore

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value and save to file."""
        self._settings[key] = value
        self.save()

    def update(self, data: dict):
        """Update multiple settings at once."""
        self._settings.update(data)
        self.save()

    def get_all(self) -> dict:
        """Return all settings."""
        return dict(self._settings)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._settings = dict(DEFAULT_SETTINGS)
        self.save()
