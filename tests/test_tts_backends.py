"""Tests for individual TTS backend classes."""

from __future__ import annotations

import json
import signal
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from tts.chatterbox import ChatterboxBackend, CHATTERBOX_PORT
from tts.fish_speech import FishSpeechBackend, FISH_SPEECH_PORT, _get_gpu_util
from tts.kokoro import KokoroBackend, KOKORO_PORT
from tts.pocket_tts import PocketTTSBackend, TTS_PORT, _find_pid_by_port
from tts.qwen3_tts import Qwen3TTSBackend, QWEN3_TTS_PORT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_urlopen_ok(status: int = 200) -> MagicMock:
    """Return a mock suitable for urllib.request.urlopen with given status."""
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ===========================================================================
# is_available — all backends (shared from ABC, but verify each endpoint)
# ===========================================================================

class TestIsAvailableAllBackends:
    """HTTP-up → True, URLError → False for every backend."""

    @pytest.mark.parametrize("cls", [
        FishSpeechBackend,
        KokoroBackend,
        PocketTTSBackend,
        ChatterboxBackend,
        Qwen3TTSBackend,
    ])
    @patch("urllib.request.urlopen")
    def test_http_ok_returns_true(self, mock_urlopen: MagicMock, cls: type) -> None:
        mock_urlopen.return_value = _mock_urlopen_ok(200)

        # Fish Speech also checks GPU — make it pass
        if cls is FishSpeechBackend:
            with patch("tts.fish_speech._get_gpu_util", return_value=0):
                assert cls().is_available() is True
        else:
            assert cls().is_available() is True

    @pytest.mark.parametrize("cls", [
        FishSpeechBackend,
        KokoroBackend,
        PocketTTSBackend,
        ChatterboxBackend,
        Qwen3TTSBackend,
    ])
    @patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    )
    def test_url_error_returns_false(self, mock_urlopen: MagicMock, cls: type) -> None:
        assert cls().is_available() is False


# ===========================================================================
# Fish Speech
# ===========================================================================

class TestFishSpeechGetGpuUtil:
    @patch("tts.fish_speech.subprocess.run")
    def test_normal_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="45\n", returncode=0)
        assert _get_gpu_util() == 45

    @patch("tts.fish_speech.subprocess.run", side_effect=OSError("no nvidia-smi"))
    def test_oserror_returns_100(self, mock_run: MagicMock) -> None:
        assert _get_gpu_util() == 100

    @patch("tts.fish_speech.subprocess.run")
    def test_bad_output_returns_100(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="not-a-number\n", returncode=0)
        assert _get_gpu_util() == 100


class TestFishSpeechIsAvailable:
    @patch("urllib.request.urlopen")
    @patch("tts.fish_speech._get_gpu_util", return_value=79)
    def test_gpu_below_threshold_available(
        self, mock_gpu: MagicMock, mock_urlopen: MagicMock,
    ) -> None:
        mock_urlopen.return_value = _mock_urlopen_ok(200)
        assert FishSpeechBackend().is_available() is True

    @patch("urllib.request.urlopen")
    @patch("tts.fish_speech._get_gpu_util", return_value=80)
    def test_gpu_at_threshold_unavailable(
        self, mock_gpu: MagicMock, mock_urlopen: MagicMock,
    ) -> None:
        mock_urlopen.return_value = _mock_urlopen_ok(200)
        assert FishSpeechBackend().is_available() is False


class TestFishSpeechStop:
    @patch("tts._base.docker_stop_by_port")
    def test_calls_docker_stop_with_correct_port(
        self, mock_stop: MagicMock,
    ) -> None:
        FishSpeechBackend().stop()
        mock_stop.assert_called_once_with(FISH_SPEECH_PORT)


# ===========================================================================
# Kokoro
# ===========================================================================

class TestKokoroGenerate:
    @patch("urllib.request.urlopen")
    def test_speed_1_omitted_from_payload(self, mock_urlopen: MagicMock) -> None:
        resp = MagicMock()
        resp.read.return_value = b"audio-data"
        mock_urlopen.return_value = resp

        KokoroBackend().generate("hello", "af_heart", speed=1.0)

        # Inspect the body sent to urlopen
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert "speed" not in payload

    @patch("urllib.request.urlopen")
    def test_speed_nondefault_included_in_payload(
        self, mock_urlopen: MagicMock,
    ) -> None:
        resp = MagicMock()
        resp.read.return_value = b"audio-data"
        mock_urlopen.return_value = resp

        KokoroBackend().generate("hello", "af_heart", speed=1.5)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert payload["speed"] == 1.5


class TestKokoroStop:
    @patch("tts._base.docker_stop_by_port")
    def test_calls_docker_stop_with_correct_port(
        self, mock_stop: MagicMock,
    ) -> None:
        KokoroBackend().stop()
        mock_stop.assert_called_once_with(KOKORO_PORT)


# ===========================================================================
# Qwen3 TTS
# ===========================================================================

class TestQwen3TTSGenerate:
    @patch("urllib.request.urlopen")
    def test_empty_voice_falls_back_to_p276(
        self, mock_urlopen: MagicMock,
    ) -> None:
        resp = MagicMock()
        resp.read.return_value = b"audio-data"
        mock_urlopen.return_value = resp

        Qwen3TTSBackend().generate("hello", voice="", speed=1.0)

        req = mock_urlopen.call_args[0][0]
        assert "voice=p276" in req.full_url


class TestQwen3TTSStop:
    @patch("tts._base.docker_stop_by_port")
    def test_calls_docker_stop_with_correct_port(
        self, mock_stop: MagicMock,
    ) -> None:
        Qwen3TTSBackend().stop()
        mock_stop.assert_called_once_with(QWEN3_TTS_PORT)


# ===========================================================================
# Chatterbox
# ===========================================================================

class TestChatterboxStop:
    @patch("tts._base.docker_stop_by_port")
    def test_calls_docker_stop_with_correct_port(
        self, mock_stop: MagicMock,
    ) -> None:
        ChatterboxBackend().stop()
        mock_stop.assert_called_once_with(CHATTERBOX_PORT)


# ===========================================================================
# pocket-tts
# ===========================================================================

class TestFindPidByPort:
    @patch("tts.pocket_tts.sys.platform", "linux")
    @patch("tts.pocket_tts.subprocess.run")
    def test_finds_pid_in_ss_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout=(
                "State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process\n"
                'LISTEN 0       128     127.0.0.1:8000      0.0.0.0:*          '
                'users:(("python3",pid=12345,fd=7))\n'
            ),
        )
        assert _find_pid_by_port(8000) == 12345

    @patch("tts.pocket_tts.sys.platform", "win32")
    @patch("tts.pocket_tts.subprocess.run")
    def test_finds_pid_in_netstat_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout=(
                "  TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    12345\n"
            ),
        )
        assert _find_pid_by_port(8000) == 12345

    @patch("tts.pocket_tts.sys.platform", "darwin")
    @patch("tts.pocket_tts.subprocess.run")
    def test_finds_pid_in_lsof_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="12345\n")
        assert _find_pid_by_port(8000) == 12345

    @patch("tts.pocket_tts.sys.platform", "linux")
    @patch("tts.pocket_tts.subprocess.run")
    def test_no_match_returns_none(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process\n",
        )
        assert _find_pid_by_port(8000) is None

    @patch("tts.pocket_tts.subprocess.run", side_effect=OSError("no ss"))
    def test_oserror_returns_none(self, mock_run: MagicMock) -> None:
        assert _find_pid_by_port(8000) is None


class TestPocketTTSStop:
    @patch("tts.pocket_tts.os.kill")
    @patch("tts.pocket_tts._find_pid_by_port", return_value=12345)
    def test_kills_process_when_pid_found(
        self, mock_find: MagicMock, mock_kill: MagicMock,
    ) -> None:
        # First call is SIGTERM, second is signal-0 check which should show process exited
        mock_kill.side_effect = [None, ProcessLookupError]
        PocketTTSBackend().stop()
        assert mock_kill.call_args_list[0] == ((12345, signal.SIGTERM),)
        assert mock_kill.call_args_list[1] == ((12345, 0),)

    @patch("tts.pocket_tts.os.kill")
    @patch("tts.pocket_tts._find_pid_by_port", return_value=None)
    def test_no_kill_when_no_pid(
        self, mock_find: MagicMock, mock_kill: MagicMock,
    ) -> None:
        PocketTTSBackend().stop()
        mock_kill.assert_not_called()


class TestPocketTTSEnsureRunning:
    @patch.object(PocketTTSBackend, "_start")
    @patch.object(PocketTTSBackend, "is_available", return_value=True)
    def test_already_available_skips_start(
        self, mock_avail: MagicMock, mock_start: MagicMock,
    ) -> None:
        result = PocketTTSBackend().ensure_running()
        assert result is True
        mock_start.assert_not_called()

    @patch.object(PocketTTSBackend, "_start", return_value=True)
    @patch.object(PocketTTSBackend, "is_available", return_value=False)
    def test_unavailable_calls_start(
        self, mock_avail: MagicMock, mock_start: MagicMock,
    ) -> None:
        result = PocketTTSBackend().ensure_running()
        assert result is True
        mock_start.assert_called_once()
