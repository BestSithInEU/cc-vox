"""Session state sentinel files for stop-hook integration."""

from __future__ import annotations

import os
from pathlib import Path


class SessionState:
    """Manages /tmp session state files so the stop hook knows TTS status."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.active = bool(session_id)
        if self.active:
            self.running = f"/tmp/voice-{session_id}-running"
            self.done = f"/tmp/voice-{session_id}-done"
            self.failed = f"/tmp/voice-{session_id}-failed"
            Path(self.running).write_text(str(os.getpid()))

    def mark_done(self) -> None:
        if self.active:
            Path(self.done).touch()
            Path(self.running).unlink(missing_ok=True)

    def mark_failed(self) -> None:
        if self.active:
            Path(self.failed).touch()
            Path(self.running).unlink(missing_ok=True)

    def cleanup(self) -> None:
        if self.active:
            Path(self.running).unlink(missing_ok=True)
