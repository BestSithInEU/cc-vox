"""Tests for the TTSBackend ABC, DockerBackend, and OpenAICompatibleBackend."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from tts._base import DockerBackend, TTSBackend
from tts._errors import TTSConnectionError, TTSGenerationError
from tts._openai_compat import OpenAICompatibleBackend


# ---------------------------------------------------------------------------
# __init_subclass__ enforcement
# ---------------------------------------------------------------------------

class TestInitSubclassEnforcement:
    def test_missing_name_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must define class attribute 'name'"):
            class Bad(TTSBackend):  # noqa: B903
                priority = 1
                port = 8000
                health_path = "/health"
                def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                    return b""

    def test_missing_priority_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must define class attribute 'priority'"):
            class Bad(TTSBackend):  # noqa: B903
                name = "test"
                port = 8000
                health_path = "/health"
                def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                    return b""

    def test_missing_port_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must define class attribute 'port'"):
            class Bad(TTSBackend):  # noqa: B903
                name = "test"
                priority = 1
                health_path = "/health"
                def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                    return b""

    def test_missing_health_path_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must define class attribute 'health_path'"):
            class Bad(TTSBackend):  # noqa: B903
                name = "test"
                priority = 1
                port = 8000
                def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                    return b""

    def test_valid_subclass_succeeds(self) -> None:
        class Good(TTSBackend):
            name = "test"
            priority = 1
            port = 8000
            health_path = "/health"
            def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                return b""

        inst = Good()
        assert inst.name == "test"
        assert inst.base_url == "http://localhost:8000"


# ---------------------------------------------------------------------------
# Shared is_available()
# ---------------------------------------------------------------------------

class TestIsAvailable:
    @patch("urllib.request.urlopen")
    def test_healthy_returns_true(self, mock_urlopen: MagicMock) -> None:
        resp = MagicMock()
        resp.status = 200
        mock_urlopen.return_value = resp

        class Stub(TTSBackend):
            name = "stub"
            priority = 1
            port = 9999
            health_path = "/up"
            def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                return b""

        assert Stub().is_available() is True

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused"))
    def test_url_error_returns_false(self, mock_urlopen: MagicMock) -> None:
        class Stub(TTSBackend):
            name = "stub"
            priority = 1
            port = 9999
            health_path = "/up"
            def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                return b""

        assert Stub().is_available() is False


# ---------------------------------------------------------------------------
# generate() error wrapping
# ---------------------------------------------------------------------------

class TestGenerateErrorWrapping:
    def _make_backend(self, side_effect: Exception) -> TTSBackend:
        class Stub(TTSBackend):
            name = "stub"
            priority = 1
            port = 9999
            health_path = "/up"
            def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                raise side_effect

        return Stub()

    def test_url_error_becomes_connection_error(self) -> None:
        backend = self._make_backend(urllib.error.URLError("refused"))
        with pytest.raises(TTSConnectionError):
            backend.generate("hello", "voice", 1.0)

    def test_os_error_becomes_connection_error(self) -> None:
        backend = self._make_backend(OSError("network down"))
        with pytest.raises(TTSConnectionError):
            backend.generate("hello", "voice", 1.0)

    def test_generic_exception_becomes_generation_error(self) -> None:
        backend = self._make_backend(ValueError("bad data"))
        with pytest.raises(TTSGenerationError):
            backend.generate("hello", "voice", 1.0)

    def test_tts_generation_error_passes_through(self) -> None:
        backend = self._make_backend(TTSGenerationError("no audio"))
        with pytest.raises(TTSGenerationError, match="no audio"):
            backend.generate("hello", "voice", 1.0)

    def test_successful_generate_returns_bytes(self) -> None:
        class Stub(TTSBackend):
            name = "stub"
            priority = 1
            port = 9999
            health_path = "/up"
            def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                return b"audio-data"

        assert Stub().generate("hello", "voice", 1.0) == b"audio-data"


# ---------------------------------------------------------------------------
# DockerBackend.stop()
# ---------------------------------------------------------------------------

class TestDockerBackendStop:
    @patch("tts._base.docker_stop_by_port")
    def test_calls_docker_stop_with_port(self, mock_stop: MagicMock) -> None:
        class Stub(DockerBackend):
            name = "stub"
            priority = 1
            port = 12345
            health_path = "/up"
            def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
                return b""

        Stub().stop()
        mock_stop.assert_called_once_with(12345)


# ---------------------------------------------------------------------------
# OpenAICompatibleBackend._generate_impl()
# ---------------------------------------------------------------------------

class TestOpenAICompatibleBackend:
    @patch("urllib.request.urlopen")
    def test_payload_construction(self, mock_urlopen: MagicMock) -> None:
        resp = MagicMock()
        resp.read.return_value = b"audio"
        mock_urlopen.return_value = resp

        class Stub(OpenAICompatibleBackend):
            name = "stub"
            priority = 1
            port = 9999
            health_path = "/up"
            model = "test-model"
            supports_speed = True

        Stub().generate("hello", "voice", 1.5)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert payload["model"] == "test-model"
        assert payload["input"] == "hello"
        assert payload["voice"] == "voice"
        assert payload["speed"] == 1.5
        assert payload["response_format"] == "wav"

    @patch("urllib.request.urlopen")
    def test_speed_1_omitted_when_supported(self, mock_urlopen: MagicMock) -> None:
        resp = MagicMock()
        resp.read.return_value = b"audio"
        mock_urlopen.return_value = resp

        class Stub(OpenAICompatibleBackend):
            name = "stub"
            priority = 1
            port = 9999
            health_path = "/up"
            model = "test-model"
            supports_speed = True

        Stub().generate("hello", "voice", 1.0)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert "speed" not in payload

    @patch("urllib.request.urlopen")
    def test_speed_ignored_when_not_supported(self, mock_urlopen: MagicMock) -> None:
        resp = MagicMock()
        resp.read.return_value = b"audio"
        mock_urlopen.return_value = resp

        class Stub(OpenAICompatibleBackend):
            name = "stub"
            priority = 1
            port = 9999
            health_path = "/up"
            model = "test-model"

        Stub().generate("hello", "voice", 1.5)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert "speed" not in payload
