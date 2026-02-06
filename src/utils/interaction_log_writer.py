"""Append-only writer for raw interaction logs."""

from __future__ import annotations

from pathlib import Path


class InteractionLogWriter:
    """Append raw interaction lines to a session log file."""

    def __init__(self, log_path: str | Path) -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append_line(self, line: str) -> None:
        if not line.endswith("\n"):
            line = line + "\n"
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)
