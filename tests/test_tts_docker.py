"""Tests for the shared Docker helper: docker_stop_by_port."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, call, patch

from tts._docker import docker_stop_by_port


class TestDockerStopByPort:
    @patch("tts._docker.subprocess.run")
    def test_no_containers_found(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        docker_stop_by_port(32612)

        # docker ps was called, but docker stop should NOT be called
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][:2] == ["docker", "ps"]

    @patch("tts._docker.subprocess.run")
    def test_one_container_found(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="abc123\n", returncode=0)
        docker_stop_by_port(32612)

        assert mock_run.call_count == 2
        # Second call should be docker stop with the container ID
        stop_call = mock_run.call_args_list[1]
        assert stop_call[0][0] == ["docker", "stop", "abc123"]

    @patch("tts._docker.subprocess.run")
    def test_multiple_containers(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="abc123\ndef456\nghi789\n", returncode=0,
        )
        docker_stop_by_port(32612)

        # 1 ps call + 3 stop calls
        assert mock_run.call_count == 4
        stop_calls = mock_run.call_args_list[1:]
        assert stop_calls[0][0][0] == ["docker", "stop", "abc123"]
        assert stop_calls[1][0][0] == ["docker", "stop", "def456"]
        assert stop_calls[2][0][0] == ["docker", "stop", "ghi789"]

    @patch("tts._docker.subprocess.run", side_effect=OSError("docker not found"))
    def test_oserror_silent_noop(self, mock_run: MagicMock) -> None:
        # Should not raise
        docker_stop_by_port(32612)

    @patch(
        "tts._docker.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=5),
    )
    def test_timeout_expired_silent_noop(self, mock_run: MagicMock) -> None:
        # Should not raise
        docker_stop_by_port(32612)

    @patch("tts._docker.subprocess.run")
    def test_nonzero_returncode_no_stop(self, mock_run: MagicMock) -> None:
        # Even with garbage in stdout, non-zero returncode should prevent stop
        mock_run.return_value = MagicMock(
            stdout="some-error-text\n", returncode=1,
        )
        docker_stop_by_port(32612)

        # Only the ps call; no stop should be attempted
        mock_run.assert_called_once()
