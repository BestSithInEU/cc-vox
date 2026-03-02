"""
TTS backend registry and selection.

Adding a new backend:
  1. Create hooks/tts/my_backend.py implementing TTSBackend
  2. Add one import + entry to _registry() below
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._protocol import TTSBackend


def _registry() -> dict[str, type[TTSBackend]]:
    from .chatterbox import ChatterboxBackend
    from .fish_speech import FishSpeechBackend
    from .kokoro import KokoroBackend
    from .pocket_tts import PocketTTSBackend
    from .qwen3_tts import Qwen3TTSBackend

    return {
        "kokoro": KokoroBackend,
        "fish-speech": FishSpeechBackend,
        "pocket-tts": PocketTTSBackend,
        "chatterbox": ChatterboxBackend,
        "qwen3-tts": Qwen3TTSBackend,
    }


def available_backend_names() -> tuple[str, ...]:
    """Return all valid backend names including 'auto'."""
    return ("auto", *_registry().keys())


def select_backend(backend_pref: str, fallback: bool) -> TTSBackend | None:
    """Pick the best available TTS backend.

    *backend_pref*: "auto" or a specific backend name (env override respected).
    *fallback*: when True, fall through to auto if the forced backend is down.
    Returns None if nothing is reachable.
    """
    pref = os.environ.get("TTS_BACKEND", backend_pref)
    registry = _registry()

    if pref != "auto" and pref in registry:
        inst = registry[pref]()
        if inst.ensure_running():
            return inst
        if fallback:
            return _auto_select(registry)
        return None

    return _auto_select(registry)


def _auto_select(registry: dict[str, type[TTSBackend]]) -> TTSBackend | None:
    """Try backends in priority order, return first that starts."""
    by_priority = sorted(registry.values(), key=lambda cls: cls.priority)
    for cls in by_priority:
        inst = cls()
        if inst.ensure_running():
            return inst
    return None
