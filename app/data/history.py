"""Transcription history management stored in history.json."""

import json
from pathlib import Path
from threading import Lock

# Path to project root folder (3 levels up from history.py)
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
        """Load history from JSON file."""
        with self._lock:
            try:
                if self._path.exists():
                    with open(self._path, "r", encoding="utf-8") as f:
                        self._entries = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._entries = []
        # Sort newest first
        self._entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return self._entries

    def save(self):
        """Save history to JSON file."""
        try:
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(self._entries, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

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
        self._entries.insert(0, entry)  # Insert at beginning (newest first)
        # Limit history
        if len(self._entries) > self.MAX_HISTORY:
            self._entries = self._entries[:self.MAX_HISTORY]
        self.save()

    def get_all(self) -> list[dict]:
        """Return all history entries."""
        return list(self._entries)

    def get_recent(self, n: int = 10) -> list[dict]:
        """Return the most recent n entries."""
        return list(self._entries[:n])

    def clear(self):
        """Clear all history."""
        self._entries = []
        self.save()

    def count(self) -> int:
        """Return the number of history entries."""
        return len(self._entries)
