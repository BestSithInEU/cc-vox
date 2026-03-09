"""Session state sentinel files for stop-hook integration."""

from __future__ import annotations

import os
import time
from pathlib import Path

STALE_AGE_SECS = 3600  # 1 hour


def cleanup_stale_sessions() -> None:
    """Remove /tmp/voice-*-{running,done,failed} files older than 1 hour."""
    now = time.time()
    tmp = Path("/tmp")
    for pattern in ("voice-*-running", "voice-*-done", "voice-*-failed"):
        for path in tmp.glob(pattern):
            try:
                if now - path.stat().st_mtime > STALE_AGE_SECS:
                    path.unlink(missing_ok=True)
            except OSError:
                pass


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
