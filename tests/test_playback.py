"""Tests for tts._playback — audio playback and cross-process locking."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from tts._playback import PlaybackLock, _is_lock_stale, play_audio


# ── play_audio ────────────────────────────────────────────────────────


class TestPlayAudioFfplay:
    """ffplay available: streams via Popen with stdin pipe."""

    @patch("tts._playback.subprocess.Popen")
    @patch("tts._playback.shutil.which", return_value="ffplay")
    def test_uses_popen_with_stdin_pipe(
        self, mock_which: MagicMock, mock_popen: MagicMock
    ) -> None:
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        play_audio(b"fake-wav-data")

        mock_popen.assert_called_once()
        popen_kwargs = mock_popen.call_args
        assert popen_kwargs[1]["stdin"] == subprocess.PIPE
        mock_proc.communicate.assert_called_once_with(input=b"fake-wav-data")

    @patch("tts._playback.subprocess.Popen")
    @patch("tts._playback.shutil.which", return_value="ffplay")
    def test_ffplay_command_flags(
        self, mock_which: MagicMock, mock_popen: MagicMock
    ) -> None:
        mock_popen.return_value = MagicMock()

        play_audio(b"data")

        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "ffplay"
        assert "-nodisp" in cmd
        assert "-autoexit" in cmd


class TestPlayAudioLinuxFallback:
    """ffplay unavailable, linux platform, aplay available."""

    @patch("tts._playback.os.unlink")
    @patch("tts._playback.subprocess.run")
    @patch("tts._playback.sys.platform", "linux")
    @patch("tts._playback.shutil.which")
    def test_uses_aplay_on_linux(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
        mock_unlink: MagicMock,
    ) -> None:
        def which_side_effect(name: str) -> str | None:
            if name == "ffplay":
                return None
            if name == "aplay":
                return "/usr/bin/aplay"
            return None

        mock_which.side_effect = which_side_effect

        play_audio(b"fake-wav-data")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "aplay"
        assert "-q" in cmd
        # Temp file path is after the -q flag
        assert cmd[2].endswith(".wav")


class TestPlayAudioNoPlayer:
    """No audio player found at all."""

    @patch("tts._playback.shutil.which", return_value=None)
    @patch("tts._playback.sys.platform", "linux")
    def test_prints_error_to_stderr(
        self, mock_which: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        play_audio(b"data")

        captured = capsys.readouterr()
        assert "No audio player found" in captured.err


# ── PlaybackLock ──────────────────────────────────────────────────────


@pytest.fixture()
def tmp_lock_file(tmp_path):
    """Patch LOCK_FILE to a temp path so tests don't touch the real lock."""
    lock_path = str(tmp_path / "test-playback.lock")
    with patch("tts._playback.LOCK_FILE", lock_path):
        yield lock_path


class TestPlaybackLockAcquire:
    def test_acquire_succeeds(self, tmp_lock_file: str) -> None:
        lock = PlaybackLock(max_wait=2)
        assert lock.acquire() is True
        lock.release()

    def test_release_after_acquire_no_error(self, tmp_lock_file: str) -> None:
        lock = PlaybackLock(max_wait=2)
        lock.acquire()
        lock.release()  # should not raise

    def test_release_without_acquire_no_error(self, tmp_lock_file: str) -> None:
        lock = PlaybackLock(max_wait=2)
        lock.release()  # _fd is None, should be a no-op


class TestPlaybackLockContextManager:
    def test_context_manager_acquires_and_releases(
        self, tmp_lock_file: str
    ) -> None:
        with PlaybackLock(max_wait=2) as lock:
            assert lock._fd is not None
        # After exit, fd should be None
        assert lock._fd is None

    def test_context_manager_raises_on_timeout(
        self, tmp_lock_file: str
    ) -> None:
        with patch("tts._playback.fcntl.flock", side_effect=BlockingIOError):
            with pytest.raises(TimeoutError, match="Timeout waiting for audio lock"):
                with PlaybackLock(max_wait=0.1):
                    pass  # pragma: no cover


class TestPlaybackLockBlocked:
    @patch("tts._playback.fcntl.flock", side_effect=BlockingIOError)
    @patch("tts._playback._is_lock_stale", return_value=False)
    def test_acquire_returns_false_on_timeout(
        self, mock_stale: MagicMock, mock_flock: MagicMock, tmp_lock_file: str
    ) -> None:
        lock = PlaybackLock(max_wait=0.1)
        assert lock.acquire() is False
        assert lock._fd is None


# ── Stale lock detection ─────────────────────────────────────────────


class TestIsLockStale:
    def test_dead_pid_is_stale(self, tmp_lock_file: str) -> None:
        # Write a PID that doesn't exist (use a very high number)
        with open(tmp_lock_file, "w") as f:
            f.write("999999999")
        assert _is_lock_stale() is True

    def test_own_pid_is_not_stale(self, tmp_lock_file: str) -> None:
        with open(tmp_lock_file, "w") as f:
            f.write(str(os.getpid()))
        assert _is_lock_stale() is False

    def test_missing_file_is_not_stale(self, tmp_lock_file: str) -> None:
        # Lock file doesn't exist yet
        assert _is_lock_stale() is False

    def test_invalid_pid_is_stale(self, tmp_lock_file: str) -> None:
        with open(tmp_lock_file, "w") as f:
            f.write("not-a-number")
        assert _is_lock_stale() is True


class TestStaleLockRecovery:
    def test_recovers_from_stale_lock(self, tmp_lock_file: str) -> None:
        # Write a dead PID to the lock file and hold the flock
        with open(tmp_lock_file, "w") as f:
            f.write("999999999")

        # A new lock should succeed (stale detection will unlink + retry)
        lock = PlaybackLock(max_wait=2)
        assert lock.acquire() is True
        lock.release()


# ── Volume control ───────────────────────────────────────────────────


class TestPlayAudioVolume:
    @patch("tts._playback.subprocess.Popen")
    @patch("tts._playback.shutil.which", return_value="ffplay")
    def test_ffplay_volume_flag(
        self, mock_which: MagicMock, mock_popen: MagicMock,
    ) -> None:
        mock_popen.return_value = MagicMock()

        play_audio(b"data", volume=0.5)

        cmd = mock_popen.call_args[0][0]
        assert "-volume" in cmd
        vol_idx = cmd.index("-volume")
        assert cmd[vol_idx + 1] == "50"

    @patch("tts._playback.subprocess.Popen")
    @patch("tts._playback.shutil.which", return_value="ffplay")
    def test_ffplay_no_volume_flag_at_default(
        self, mock_which: MagicMock, mock_popen: MagicMock,
    ) -> None:
        mock_popen.return_value = MagicMock()

        play_audio(b"data", volume=1.0)

        cmd = mock_popen.call_args[0][0]
        assert "-volume" not in cmd
