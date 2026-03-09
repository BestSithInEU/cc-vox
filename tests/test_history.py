"""Tests for audio response history."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tts._history import (
    MAX_HISTORY,
    cleanup_old_clips,
    get_clip,
    list_clips,
    save_clip,
)


@pytest.fixture(autouse=True)
def tmp_history(tmp_path: Path):
    """Redirect history dir to temp."""
    history_dir = tmp_path / "voice-history"
    with patch("tts._history.HISTORY_DIR", history_dir):
        yield history_dir


class TestSaveClip:
    def test_saves_wav_and_json(self, tmp_history: Path) -> None:
        path = save_clip(b"audio-data", "Hello world", "kokoro", "af_heart")
        assert path.exists()
        assert path.suffix == ".wav"
        assert path.read_bytes() == b"audio-data"

        meta_path = path.with_suffix(".json")
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["text"] == "Hello world"
        assert meta["backend"] == "kokoro"
        assert meta["voice"] == "af_heart"
        assert "timestamp" in meta

    def test_creates_dir_if_missing(self, tmp_history: Path) -> None:
        assert not tmp_history.exists()
        save_clip(b"data", "test", "kokoro")
        assert tmp_history.exists()


class TestListClips:
    def test_empty_history(self) -> None:
        assert list_clips() == []

    def test_lists_newest_first(self, tmp_history: Path) -> None:
        tmp_history.mkdir(parents=True)
        for i, name in enumerate(["2024-01-01_000001", "2024-01-01_000002"]):
            (tmp_history / f"{name}.wav").write_bytes(b"audio")
            (tmp_history / f"{name}.json").write_text(
                json.dumps({"text": f"clip {i}", "backend": "kokoro"})
            )

        clips = list_clips(limit=10)
        assert len(clips) == 2
        assert clips[0]["text"] == "clip 1"  # newest first

    def test_respects_limit(self, tmp_history: Path) -> None:
        tmp_history.mkdir(parents=True)
        for i in range(5):
            name = f"2024-01-01_00000{i}"
            (tmp_history / f"{name}.wav").write_bytes(b"audio")
            (tmp_history / f"{name}.json").write_text(
                json.dumps({"text": f"clip {i}", "backend": "kokoro"})
            )

        clips = list_clips(limit=2)
        assert len(clips) == 2


class TestGetClip:
    def test_get_most_recent(self, tmp_history: Path) -> None:
        save_clip(b"audio-data", "Hello", "kokoro")
        result = get_clip(0)
        assert result is not None
        audio, meta = result
        assert audio == b"audio-data"
        assert meta["text"] == "Hello"

    def test_get_out_of_range(self) -> None:
        assert get_clip(99) is None


class TestCleanupOldClips:
    def test_removes_excess_clips(self, tmp_history: Path) -> None:
        tmp_history.mkdir(parents=True)
        for i in range(MAX_HISTORY + 5):
            name = f"2024-01-01_{i:06d}"
            (tmp_history / f"{name}.wav").write_bytes(b"audio")
            (tmp_history / f"{name}.json").write_text(
                json.dumps({"text": f"clip {i}", "backend": "kokoro"})
            )

        cleanup_old_clips()

        wav_count = len(list(tmp_history.glob("*.wav")))
        assert wav_count == MAX_HISTORY
