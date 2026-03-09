"""TTS state file for cross-plugin coordination.

Writes current TTS state to a temp file that the statusline plugin
can read to display voice information.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

STATE_FILE = Path(tempfile.gettempdir()) / "cc-vox-state.json"
STATE_TTL = 300  # 5 minutes


def write_tts_state(
    backend: str, voice: str, status: str = "ok",
) -> None:
    """Write current TTS state for statusline consumption."""
    data = {
        "backend": backend,
        "voice": voice,
        "status": status,
        "ts": time.time(),
    }
    tmp = STATE_FILE.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(str(tmp), str(STATE_FILE))
    except OSError:
        pass


def read_tts_state() -> dict | None:
    """Read TTS state. Returns None if stale (>5 min) or missing."""
    try:
        raw = STATE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if time.time() - data.get("ts", 0) > STATE_TTL:
            return None
        return data
    except (OSError, json.JSONDecodeError, ValueError):
        return None
