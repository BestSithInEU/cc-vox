"""Tests for the TTS backend registry and selection logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tts import (
    _registry,
    available_backend_names,
    create_backend,
    generate_with_fallback,
    select_backend,
    stop_all_backends,
)
from tts._errors import TTSError, TTSGenerationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_backend_cls(name: str, priority: int, available: bool) -> type:
    """Create a mock backend class with controllable ensure_running()."""
    cls = MagicMock()
    cls.priority = priority
    instance = MagicMock()
    instance.name = name
    instance.priority = priority
    instance.ensure_running.return_value = available
    cls.return_value = instance
    return cls


def _mock_registry(specs: list[tuple[str, int, bool]]) -> dict[str, type]:
    """Build a fake registry from (name, priority, available) tuples."""
    return {name: _make_backend_cls(name, pri, avail) for name, pri, avail in specs}


# ---------------------------------------------------------------------------
# available_backend_names
# ---------------------------------------------------------------------------

class TestAvailableBackendNames:
    def test_returns_tuple(self) -> None:
        result = available_backend_names()
        assert isinstance(result, tuple)

    def test_auto_is_first(self) -> None:
        result = available_backend_names()
        assert result[0] == "auto"

    def test_contains_all_backend_names(self) -> None:
        result = available_backend_names()
        expected = {"auto", "kokoro", "fish-speech", "pocket-tts", "chatterbox", "qwen3-tts"}
        assert set(result) == expected


# ---------------------------------------------------------------------------
# _registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_returns_dict_with_correct_keys(self) -> None:
        reg = _registry()
        assert isinstance(reg, dict)
        expected_keys = {"kokoro", "fish-speech", "pocket-tts", "chatterbox", "qwen3-tts"}
        assert set(reg.keys()) == expected_keys


# ---------------------------------------------------------------------------
# select_backend
# ---------------------------------------------------------------------------

class TestSelectBackend:
    def test_specific_backend_available_no_fallback(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
        ])
        with patch("tts._registry", return_value=reg):
            result = select_backend("kokoro", fallback=False)
        assert result is not None
        assert result.name == "kokoro"

    def test_specific_backend_unavailable_no_fallback_returns_none(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, False),
            ("fish-speech", 10, True),
        ])
        with patch("tts._registry", return_value=reg):
            result = select_backend("kokoro", fallback=False)
        assert result is None

    def test_specific_backend_unavailable_with_fallback_auto_selects(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, False),
            ("fish-speech", 10, True),
        ])
        with patch("tts._registry", return_value=reg):
            result = select_backend("kokoro", fallback=True)
        assert result is not None
        # fish-speech has lower priority (10 < 20) so it should be chosen
        assert result.name == "fish-speech"

    def test_auto_mode_selects_by_priority(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
            ("pocket-tts", 30, True),
        ])
        with patch("tts._registry", return_value=reg):
            result = select_backend("auto", fallback=False)
        assert result is not None
        assert result.name == "fish-speech"

    def test_auto_mode_skips_unavailable(self) -> None:
        reg = _mock_registry([
            ("fish-speech", 10, False),
            ("kokoro", 20, True),
            ("pocket-tts", 30, True),
        ])
        with patch("tts._registry", return_value=reg):
            result = select_backend("auto", fallback=False)
        assert result is not None
        assert result.name == "kokoro"

    def test_all_unavailable_returns_none(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, False),
            ("fish-speech", 10, False),
            ("pocket-tts", 30, False),
        ])
        with patch("tts._registry", return_value=reg):
            result = select_backend("auto", fallback=False)
        assert result is None

    def test_env_var_overrides_pref(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TTS_BACKEND", "pocket-tts")
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
            ("pocket-tts", 30, True),
        ])
        with patch("tts._registry", return_value=reg):
            result = select_backend("kokoro", fallback=False)
        assert result is not None
        # env override should pick pocket-tts even though we asked for kokoro
        assert result.name == "pocket-tts"


# ---------------------------------------------------------------------------
# stop_all_backends
# ---------------------------------------------------------------------------

class TestStopAllBackends:
    def test_calls_stop_on_each_backend(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
        ])
        with patch("tts._registry", return_value=reg):
            stop_all_backends()

        for cls in reg.values():
            cls.return_value.stop.assert_called_once()

    def test_swallows_exceptions(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
            ("pocket-tts", 30, True),
        ])
        # Make the first backend raise on stop()
        first_key = next(iter(reg))
        reg[first_key].return_value.stop.side_effect = RuntimeError("boom")

        with patch("tts._registry", return_value=reg):
            # Should not raise
            stop_all_backends()

        # All backends should still have had stop() called
        for cls in reg.values():
            cls.return_value.stop.assert_called_once()


# ---------------------------------------------------------------------------
# create_backend
# ---------------------------------------------------------------------------

class TestCreateBackend:
    def test_known_backend_returns_instance(self) -> None:
        backend = create_backend("kokoro")
        assert backend.name == "kokoro"

    def test_unknown_backend_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown backend"):
            create_backend("nonexistent")


# ---------------------------------------------------------------------------
# generate_with_fallback
# ---------------------------------------------------------------------------

class TestGenerateWithFallback:
    def test_preferred_backend_succeeds(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
        ])
        reg["kokoro"].return_value.generate.return_value = b"audio"
        with patch("tts._registry", return_value=reg):
            result = generate_with_fallback("hi", "voice", 1.0, "kokoro", fallback=True)
        assert result is not None
        audio, name = result
        assert audio == b"audio"
        assert name == "kokoro"

    def test_fallback_on_generate_failure(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
        ])
        reg["kokoro"].return_value.generate.side_effect = TTSGenerationError("fail")
        reg["fish-speech"].return_value.generate.return_value = b"fallback-audio"
        with patch("tts._registry", return_value=reg):
            result = generate_with_fallback("hi", "voice", 1.0, "kokoro", fallback=True)
        assert result is not None
        audio, name = result
        assert audio == b"fallback-audio"
        assert name == "fish-speech"

    def test_no_fallback_returns_none(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
        ])
        reg["kokoro"].return_value.generate.side_effect = TTSGenerationError("fail")
        with patch("tts._registry", return_value=reg):
            result = generate_with_fallback("hi", "voice", 1.0, "kokoro", fallback=False)
        assert result is None

    def test_all_fail_returns_none(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
        ])
        reg["kokoro"].return_value.generate.side_effect = TTSGenerationError("fail")
        reg["fish-speech"].return_value.generate.side_effect = TTSGenerationError("fail")
        with patch("tts._registry", return_value=reg):
            result = generate_with_fallback("hi", "voice", 1.0, "auto", fallback=True)
        assert result is None

    def test_auto_mode_tries_by_priority(self) -> None:
        reg = _mock_registry([
            ("kokoro", 20, True),
            ("fish-speech", 10, True),
        ])
        reg["fish-speech"].return_value.generate.return_value = b"fish-audio"
        with patch("tts._registry", return_value=reg):
            result = generate_with_fallback("hi", "voice", 1.0, "auto", fallback=True)
        assert result is not None
        _, name = result
        assert name == "fish-speech"
