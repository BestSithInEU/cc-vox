"""TTSBackend protocol — the contract every backend implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSBackend(Protocol):
    name: str       # "kokoro", "fish-speech", "pocket-tts"
    priority: int   # lower = tried first in auto mode

    def is_available(self) -> bool:
        """Return True if the backend service is reachable right now."""
        ...

    def ensure_running(self) -> bool:
        """Start the service if possible, then return is_available().

        Backends without auto-start can just delegate to is_available().
        """
        ...

    def generate(self, text: str, voice: str, speed: float) -> bytes:
        """Generate WAV audio.

        *voice* is always in canonical Kokoro form — the backend maps internally.
        *speed* may be ignored by backends that don't support it.
        """
        ...
