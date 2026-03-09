"""Tests for extraction strategies."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from extraction import (
    ExtractionResult,
    _try_headless,
    _try_marker,
    _try_short,
    _try_truncate,
    extract_speakable_text,
)
from voice_common import VoiceConfig


# ── Strategy 1: Marker ───────────────────────────────────────────────


class TestTryMarker:
    def test_extracts_marker_text(self) -> None:
        msg = "Here is code.\n\n\U0001f4e2 [I updated the config.]"
        config = VoiceConfig(max_sentences=2)
        result = _try_marker(msg, config)
        assert result is not None
        assert result.text == "I updated the config."
        assert result.used_headless is False

    def test_returns_none_without_marker(self) -> None:
        msg = "Just some regular text."
        config = VoiceConfig(max_sentences=2)
        assert _try_marker(msg, config) is None


# ── Strategy 2: Short Response ───────────────────────────────────────


class TestTryShort:
    def test_short_response_returned(self) -> None:
        msg = "Done."
        config = VoiceConfig(max_sentences=2)
        result = _try_short(msg, config)
        assert result is not None
        assert result.text == "Done."

    def test_long_response_returns_none(self) -> None:
        msg = "First. Second. Third. Fourth."
        config = VoiceConfig(max_sentences=2)
        assert _try_short(msg, config) is None


# ── Strategy 3: Headless ─────────────────────────────────────────────


class TestTryHeadless:
    def test_returns_summary_when_available(self) -> None:
        config = VoiceConfig(max_sentences=2)
        with (
            patch("extraction.get_recent_conversation", return_value=[("user", "hi"), ("assistant", "long text")]),
            patch("extraction.summarize_with_claude", return_value="Summary."),
        ):
            result = _try_headless("long text", config, Path("/fake"))
        assert result is not None
        assert result.text == "Summary."
        assert result.used_headless is True

    def test_returns_none_when_summarize_fails(self) -> None:
        config = VoiceConfig(max_sentences=2)
        with (
            patch("extraction.get_recent_conversation", return_value=[("user", "hi")]),
            patch("extraction.summarize_with_claude", return_value=None),
        ):
            result = _try_headless("long text", config, Path("/fake"))
        assert result is None


# ── Strategy 4: Truncation ───────────────────────────────────────────


class TestTryTruncate:
    def test_truncates_to_limit(self) -> None:
        msg = "First sentence. Second sentence. Third sentence. Fourth sentence."
        config = VoiceConfig(max_sentences=2)
        result = _try_truncate(msg, config)
        assert result is not None
        assert "First sentence." in result.text
        assert "Second sentence." in result.text

    def test_returns_none_for_empty(self) -> None:
        config = VoiceConfig(max_sentences=2)
        assert _try_truncate("", config) is None


# ── Pipeline ─────────────────────────────────────────────────────────


class TestExtractSpeakableText:
    def test_prefers_marker_over_short(self) -> None:
        msg = "\U0001f4e2 Marker text."
        config = VoiceConfig(max_sentences=2)
        result = extract_speakable_text(msg, config, Path("/fake"))
        assert result is not None
        assert result.text == "Marker text."
        assert result.used_headless is False

    def test_falls_through_to_truncation(self) -> None:
        msg = "A. B. C. D. E."
        config = VoiceConfig(max_sentences=2)
        with (
            patch("extraction.get_recent_conversation", return_value=[]),
            patch("extraction.summarize_with_claude", return_value=None),
        ):
            result = extract_speakable_text(msg, config, Path("/fake"))
        assert result is not None
        assert "A." in result.text
