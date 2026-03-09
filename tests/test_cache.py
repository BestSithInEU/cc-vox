"""Tests for per-session backend cache."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from tts._cache import (
    CACHE_TTL,
    get_cached_backend,
    invalidate_cache,
    set_cached_backend,
)


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path: Path):
    """Redirect cache file to temp dir."""
    cache_file = tmp_path / "cc-vox-backend-cache.json"
    with patch("tts._cache.CACHE_FILE", cache_file):
        yield cache_file


class TestSetAndGet:
    def test_set_then_get(self) -> None:
        set_cached_backend("sess-1", "kokoro")
        assert get_cached_backend("sess-1") == "kokoro"

    def test_get_missing_session(self) -> None:
        assert get_cached_backend("nonexistent") is None

    def test_get_empty_session_id(self) -> None:
        assert get_cached_backend("") is None

    def test_set_empty_session_id_noop(self) -> None:
        set_cached_backend("", "kokoro")
        assert get_cached_backend("") is None

    def test_overwrite(self) -> None:
        set_cached_backend("sess-1", "kokoro")
        set_cached_backend("sess-1", "fish-speech")
        assert get_cached_backend("sess-1") == "fish-speech"


class TestTTL:
    def test_expired_returns_none(self, tmp_cache: Path) -> None:
        # Write an entry with an old timestamp
        data = {"sess-old": {"backend": "kokoro", "ts": time.time() - CACHE_TTL - 10}}
        tmp_cache.write_text(json.dumps(data))
        assert get_cached_backend("sess-old") is None

    def test_fresh_entry_returned(self, tmp_cache: Path) -> None:
        data = {"sess-new": {"backend": "kokoro", "ts": time.time()}}
        tmp_cache.write_text(json.dumps(data))
        assert get_cached_backend("sess-new") == "kokoro"


class TestInvalidate:
    def test_invalidate_specific(self) -> None:
        set_cached_backend("sess-1", "kokoro")
        set_cached_backend("sess-2", "fish-speech")
        invalidate_cache("sess-1")
        assert get_cached_backend("sess-1") is None
        assert get_cached_backend("sess-2") == "fish-speech"

    def test_invalidate_all(self) -> None:
        set_cached_backend("sess-1", "kokoro")
        set_cached_backend("sess-2", "fish-speech")
        invalidate_cache()
        assert get_cached_backend("sess-1") is None
        assert get_cached_backend("sess-2") is None

    def test_invalidate_missing_noop(self) -> None:
        invalidate_cache("nonexistent")  # should not raise
        invalidate_cache()  # should not raise


class TestPruning:
    def test_stale_entries_pruned_on_set(self, tmp_cache: Path) -> None:
        old_ts = time.time() - CACHE_TTL - 10
        data = {"stale": {"backend": "kokoro", "ts": old_ts}}
        tmp_cache.write_text(json.dumps(data))

        set_cached_backend("fresh", "fish-speech")

        raw = json.loads(tmp_cache.read_text())
        assert "stale" not in raw
        assert "fresh" in raw
