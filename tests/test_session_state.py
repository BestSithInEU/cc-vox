"""Tests for tts._session_state — sentinel file management."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from tts._session_state import SessionState


def _unique_id() -> str:
    """Generate a unique session ID to avoid collisions between tests."""
    return f"pytest-{uuid.uuid4().hex[:12]}"


@pytest.fixture()
def session_id():
    """Provide a unique session ID and clean up all sentinel files after the test."""
    sid = _unique_id()
    yield sid
    # Cleanup all possible sentinel files
    for suffix in ("running", "done", "failed"):
        Path(f"/tmp/voice-{sid}-{suffix}").unlink(missing_ok=True)


# ── Inactive state (empty session_id) ────────────────────────────────


class TestInactiveSessionState:
    def test_empty_session_id_inactive(self) -> None:
        state = SessionState("")
        assert state.active is False

    def test_empty_session_id_no_files_created(self) -> None:
        state = SessionState("")
        # No running/done/failed attributes should exist
        assert not hasattr(state, "running")

    def test_mark_done_noop(self) -> None:
        state = SessionState("")
        state.mark_done()  # should not raise

    def test_mark_failed_noop(self) -> None:
        state = SessionState("")
        state.mark_failed()  # should not raise

    def test_cleanup_noop(self) -> None:
        state = SessionState("")
        state.cleanup()  # should not raise


# ── Active state ──────────────────────────────────────────────────────


class TestActiveSessionState:
    def test_active_flag(self, session_id: str) -> None:
        state = SessionState(session_id)
        assert state.active is True

    def test_creates_running_file(self, session_id: str) -> None:
        state = SessionState(session_id)
        running_path = Path(state.running)
        assert running_path.exists()

    def test_running_file_contains_pid(self, session_id: str) -> None:
        state = SessionState(session_id)
        content = Path(state.running).read_text()
        assert content == str(os.getpid())


# ── mark_done ─────────────────────────────────────────────────────────


class TestMarkDone:
    def test_creates_done_file(self, session_id: str) -> None:
        state = SessionState(session_id)
        state.mark_done()
        assert Path(state.done).exists()

    def test_removes_running_file(self, session_id: str) -> None:
        state = SessionState(session_id)
        state.mark_done()
        assert not Path(state.running).exists()


# ── mark_failed ───────────────────────────────────────────────────────


class TestMarkFailed:
    def test_creates_failed_file(self, session_id: str) -> None:
        state = SessionState(session_id)
        state.mark_failed()
        assert Path(state.failed).exists()

    def test_removes_running_file(self, session_id: str) -> None:
        state = SessionState(session_id)
        state.mark_failed()
        assert not Path(state.running).exists()


# ── cleanup ───────────────────────────────────────────────────────────


class TestCleanup:
    def test_removes_running_file(self, session_id: str) -> None:
        state = SessionState(session_id)
        assert Path(state.running).exists()
        state.cleanup()
        assert not Path(state.running).exists()

    def test_cleanup_idempotent(self, session_id: str) -> None:
        state = SessionState(session_id)
        state.cleanup()
        state.cleanup()  # second call should not raise
