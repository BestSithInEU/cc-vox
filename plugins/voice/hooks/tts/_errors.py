"""TTS error hierarchy."""

from __future__ import annotations


class TTSError(Exception):
    """Base exception for all TTS backend errors."""


class TTSConnectionError(TTSError):
    """Backend service is unreachable or returned a connection error."""


class TTSGenerationError(TTSError):
    """Audio generation failed after reaching the backend."""


class TTSBackendUnavailable(TTSError):
    """No backend could be started or reached."""
