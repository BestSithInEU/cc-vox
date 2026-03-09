"""Audio response history — save and replay TTS clips."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ._debug import log

HISTORY_DIR = Path.home() / ".claude" / "voice-history"
MAX_HISTORY = 50


def _ensure_dir() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def save_clip(
    audio_data: bytes, text: str, backend: str, voice: str = "",
) -> Path:
    """Save audio clip with metadata sidecar. Returns clip path."""
    _ensure_dir()

    ts = time.strftime("%Y-%m-%d_%H%M%S")
    wav_path = HISTORY_DIR / f"{ts}.wav"
    meta_path = HISTORY_DIR / f"{ts}.json"

    wav_path.write_bytes(audio_data)
    meta_path.write_text(
        json.dumps({
            "text": text,
            "backend": backend,
            "voice": voice,
            "timestamp": time.time(),
        }),
        encoding="utf-8",
    )

    log(f"Saved clip: {wav_path.name} ({len(audio_data)} bytes)")
    cleanup_old_clips()
    return wav_path


def list_clips(limit: int = 10) -> list[dict]:
    """List recent clips with metadata, newest first."""
    if not HISTORY_DIR.exists():
        return []

    clips = []
    for meta_path in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
        if len(clips) >= limit:
            break
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            wav_path = meta_path.with_suffix(".wav")
            if wav_path.exists():
                meta["file"] = str(wav_path)
                meta["name"] = wav_path.stem
                clips.append(meta)
        except (OSError, json.JSONDecodeError):
            continue

    return clips


def get_clip(index: int = 0) -> tuple[bytes, dict] | None:
    """Get audio data and metadata by index (0 = most recent)."""
    clips = list_clips(limit=index + 1)
    if index >= len(clips):
        return None

    clip = clips[index]
    try:
        audio = Path(clip["file"]).read_bytes()
        return audio, clip
    except OSError:
        return None


def cleanup_old_clips() -> None:
    """Remove clips beyond MAX_HISTORY (oldest first)."""
    if not HISTORY_DIR.exists():
        return

    wav_files = sorted(HISTORY_DIR.glob("*.wav"))
    if len(wav_files) <= MAX_HISTORY:
        return

    for wav_path in wav_files[:-MAX_HISTORY]:
        try:
            wav_path.unlink(missing_ok=True)
            wav_path.with_suffix(".json").unlink(missing_ok=True)
        except OSError:
            pass
