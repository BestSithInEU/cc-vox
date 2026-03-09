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

_cached_registry: dict[str, type[TTSBackend]] | None = None


def _registry() -> dict[str, type[TTSBackend]]:
    global _cached_registry  # noqa: PLW0603
    if _cached_registry is not None:
        return _cached_registry

    from .chatterbox import ChatterboxBackend
    from .fish_speech import FishSpeechBackend
    from .kokoro import KokoroBackend
    from .pocket_tts import PocketTTSBackend
    from .qwen3_tts import Qwen3TTSBackend

    _cached_registry = {
        "kokoro": KokoroBackend,
        "fish-speech": FishSpeechBackend,
        "pocket-tts": PocketTTSBackend,
        "chatterbox": ChatterboxBackend,
        "qwen3-tts": Qwen3TTSBackend,
    }
    return _cached_registry


def create_backend(name: str) -> TTSBackend:
    """Instantiate a backend by name. Raises KeyError for unknown names."""
    registry = _registry()
    if name not in registry:
        raise KeyError(f"Unknown backend: {name!r}")
    return registry[name]()


def available_backend_names() -> tuple[str, ...]:
    """Return all valid backend names including 'auto'."""
    return ("auto", *_registry().keys())


def select_backend(
    backend_pref: str, fallback: bool, session_id: str = "",
) -> TTSBackend | None:
    """Pick the best available TTS backend.

    *backend_pref*: "auto" or a specific backend name (env override respected).
    *fallback*: when True, fall through to auto if the forced backend is down.
    *session_id*: optional session ID for per-session caching.
    Returns None if nothing is reachable.
    """
    from . import _debug
    from ._cache import get_cached_backend, set_cached_backend

    pref = os.environ.get("TTS_BACKEND", backend_pref)
    registry = _registry()

    # Try session cache first (auto mode only)
    if pref == "auto" and session_id:
        cached = get_cached_backend(session_id)
        if cached and cached in registry:
            inst = registry[cached]()
            if inst.ensure_running():
                _debug.log(f"Using cached backend: {inst.name}")
                return inst
            _debug.log(f"Cached backend {cached!r} no longer available")

    if pref != "auto" and pref in registry:
        inst = registry[pref]()
        if inst.ensure_running():
            _debug.log(f"Selected preferred backend: {inst.name}")
            if session_id:
                set_cached_backend(session_id, inst.name)
            return inst
        _debug.log(f"Preferred backend {pref!r} unavailable")
        if fallback:
            result = _auto_select(registry)
            if result and session_id:
                set_cached_backend(session_id, result.name)
            return result
        return None

    result = _auto_select(registry)
    if result and session_id:
        set_cached_backend(session_id, result.name)
    return result


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
    session_id: str = "",
) -> tuple[bytes, str] | None:
    """Try generate() on selected backend; on failure, try others by priority.

    Returns (audio_bytes, backend_name) or None.
    """
    from . import _debug
    from ._cache import get_cached_backend, set_cached_backend
    from ._lang import backends_for_language, detect_language

    pref = os.environ.get("TTS_BACKEND", backend_pref)
    registry = _registry()
    tried: set[str] = set()

    # Detect language and try language-preferred backends first (auto mode only)
    lang = detect_language(text)
    lang_backends = backends_for_language(lang)
    if pref == "auto" and lang_backends:
        _debug.log(f"Detected language: {lang}, preferred backends: {lang_backends}")
        for name in lang_backends:
            if name in registry:
                inst = registry[name]()
                if inst.ensure_running():
                    try:
                        _debug.log(f"Trying language-preferred backend: {inst.name}")
                        result = inst.generate(text, voice, speed), inst.name
                        if session_id:
                            set_cached_backend(session_id, inst.name)
                        return result
                    except TTSError as exc:
                        _debug.log(f"Language backend {inst.name} failed: {exc}")
                        tried.add(name)

    # Try session-cached backend first (auto mode only)
    if pref == "auto" and session_id:
        cached = get_cached_backend(session_id)
        if cached and cached in registry:
            inst = registry[cached]()
            if inst.ensure_running():
                try:
                    _debug.log(f"Generating with cached backend: {inst.name}")
                    return inst.generate(text, voice, speed), inst.name
                except TTSError as exc:
                    _debug.log(f"Cached {inst.name} failed: {exc}")
                    tried.add(cached)

    # Try preferred backend first
    if pref != "auto" and pref in registry:
        inst = registry[pref]()
        if inst.ensure_running():
            try:
                _debug.log(f"Generating with preferred backend: {inst.name}")
                result = inst.generate(text, voice, speed), inst.name
                if session_id:
                    set_cached_backend(session_id, inst.name)
                return result
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
                result = inst.generate(text, voice, speed), inst.name
                if session_id:
                    set_cached_backend(session_id, inst.name)
                return result
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
