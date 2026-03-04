"""
TTS backend registry and selection.

Adding a new backend:
  1. Create hooks/tts/my_backend.py inheriting from TTSBackend/DockerBackend/OpenAICompatibleBackend
  2. Add one import + entry to _registry() below
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import TTSBackend

from ._errors import TTSError


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


def create_backend(name: str) -> TTSBackend:
    """Instantiate a backend by name. Raises KeyError for unknown names."""
    registry = _registry()
    if name not in registry:
        raise KeyError(f"Unknown backend: {name!r}")
    return registry[name]()


def available_backend_names() -> tuple[str, ...]:
    """Return all valid backend names including 'auto'."""
    return ("auto", *_registry().keys())


def select_backend(backend_pref: str, fallback: bool) -> TTSBackend | None:
    """Pick the best available TTS backend.

    *backend_pref*: "auto" or a specific backend name (env override respected).
    *fallback*: when True, fall through to auto if the forced backend is down.
    Returns None if nothing is reachable.
    """
    from . import _debug

    pref = os.environ.get("TTS_BACKEND", backend_pref)
    registry = _registry()

    if pref != "auto" and pref in registry:
        inst = registry[pref]()
        if inst.ensure_running():
            _debug.log(f"Selected preferred backend: {inst.name}")
            return inst
        _debug.log(f"Preferred backend {pref!r} unavailable")
        if fallback:
            return _auto_select(registry)
        return None

    return _auto_select(registry)


def _auto_select(registry: dict[str, type[TTSBackend]]) -> TTSBackend | None:
    """Try backends in priority order, return first that starts."""
    from . import _debug

    by_priority = sorted(registry.values(), key=lambda cls: (cls.priority, cls.name))
    for cls in by_priority:
        inst = cls()
        if inst.ensure_running():
            _debug.log(f"Auto-selected backend: {inst.name}")
            return inst
        _debug.log(f"Skipped {inst.name} (unavailable)")
    return None


def generate_with_fallback(
    text: str, voice: str, speed: float,
    backend_pref: str, fallback: bool,
) -> tuple[bytes, str] | None:
    """Try generate() on selected backend; on failure, try others by priority.

    Returns (audio_bytes, backend_name) or None.
    """
    from . import _debug

    pref = os.environ.get("TTS_BACKEND", backend_pref)
    registry = _registry()
    tried: set[str] = set()

    # Try preferred backend first
    if pref != "auto" and pref in registry:
        inst = registry[pref]()
        if inst.ensure_running():
            try:
                _debug.log(f"Generating with preferred backend: {inst.name}")
                return inst.generate(text, voice, speed), inst.name
            except TTSError as exc:
                _debug.log(f"{inst.name} failed: {exc}")
                tried.add(pref)
                if not fallback:
                    return None

    # Try remaining backends by priority
    by_priority = sorted(registry.values(), key=lambda cls: (cls.priority, cls.name))
    for cls in by_priority:
        inst = cls()
        if inst.name in tried:
            continue
        if inst.ensure_running():
            try:
                _debug.log(f"Trying fallback backend: {inst.name}")
                return inst.generate(text, voice, speed), inst.name
            except TTSError as exc:
                _debug.log(f"{inst.name} failed: {exc}")
                tried.add(inst.name)
                continue
    return None


def stop_all_backends() -> None:
    """Stop every registered TTS backend service."""
    for name, cls in _registry().items():
        try:
            cls().stop()
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to stop {name}: {exc}", file=sys.stderr)
