"""Tests for TTS state file (cross-plugin coordination)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from tts._state_file import STATE_TTL, read_tts_state, write_tts_state


@pytest.fixture(autouse=True)
def tmp_state(tmp_path: Path):
    """Redirect state file to temp."""
    state_file = tmp_path / "cc-vox-state.json"
    with patch("tts._state_file.STATE_FILE", state_file):
        yield state_file


class TestWriteAndRead:
    def test_write_then_read(self) -> None:
        write_tts_state("kokoro", "af_heart")
        state = read_tts_state()
        assert state is not None
        assert state["backend"] == "kokoro"
        assert state["voice"] == "af_heart"
        assert state["status"] == "ok"

    def test_write_with_status(self) -> None:
        write_tts_state("none", "af_heart", status="down")
        state = read_tts_state()
        assert state is not None
        assert state["status"] == "down"

    def test_read_missing_returns_none(self) -> None:
        assert read_tts_state() is None


class TestStaleness:
    def test_stale_returns_none(self, tmp_state: Path) -> None:
        data = {
            "backend": "kokoro",
            "voice": "af_heart",
            "status": "ok",
            "ts": time.time() - STATE_TTL - 10,
        }
        tmp_state.write_text(json.dumps(data))
        assert read_tts_state() is None

    def test_fresh_returns_data(self, tmp_state: Path) -> None:
        data = {
            "backend": "kokoro",
            "voice": "af_heart",
            "status": "ok",
            "ts": time.time(),
        }
        tmp_state.write_text(json.dumps(data))
        state = read_tts_state()
        assert state is not None
        assert state["backend"] == "kokoro"


class TestCorruptFile:
    def test_invalid_json_returns_none(self, tmp_state: Path) -> None:
        tmp_state.write_text("not json")
        assert read_tts_state() is None

    def test_empty_file_returns_none(self, tmp_state: Path) -> None:
        tmp_state.write_text("")
        assert read_tts_state() is None
