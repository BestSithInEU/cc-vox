"""Debug logging for cc-vox TTS pipeline."""

from __future__ import annotations

import sys
import time

_enabled = False


def enable() -> None:
    """Enable debug logging to stderr."""
    global _enabled  # noqa: PLW0603
    _enabled = True


def is_enabled() -> bool:
    """Return whether debug logging is active."""
    return _enabled


def log(msg: str) -> None:
    """Print a debug message to stderr if debug mode is on."""
    if _enabled:
        print(f"[cc-vox] {msg}", file=sys.stderr)


class Timer:
    """Context manager that logs elapsed time for an operation."""

    def __init__(self, label: str) -> None:
        self.label = label
        self._start = 0.0

    def __enter__(self) -> Timer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *_: object) -> None:
        elapsed = time.monotonic() - self._start
        log(f"{self.label}: {elapsed:.2f}s")
