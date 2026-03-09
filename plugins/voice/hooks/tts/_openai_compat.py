"""OpenAI-compatible TTS backend base class."""

from __future__ import annotations

import abc
import json
import urllib.request
from collections.abc import Iterator

from ._base import DockerBackend


class OpenAICompatibleBackend(DockerBackend, abc.ABC):
    """Base for backends exposing an OpenAI-style /v1/audio/speech endpoint."""

    model: str
    speech_path: str = "/v1/audio/speech"
    supports_speed: bool = False
    supports_streaming: bool = True
    _stream_chunk_size: int = 8192

    def _build_payload(self, text: str, voice: str, speed: float) -> dict:
        """Build the JSON payload. Override to customize voice/model mapping."""
        payload: dict[str, object] = {
            "model": self.model,
            "input": text,
            "voice": voice,
            "response_format": "wav",
        }
        if self.supports_speed and speed != 1.0:
            payload["speed"] = speed
        return payload

    def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
        payload = self._build_payload(text, voice, speed)
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}{self.speech_path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=self.generate_timeout)
        return resp.read()

    def generate_streaming(
        self, text: str, voice: str, speed: float,
    ) -> Iterator[bytes]:
        """Yield audio chunks as they arrive from the backend."""
        from ._debug import log

        payload = self._build_payload(text, voice, speed)
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}{self.speech_path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        log(f"{self.name}: streaming {len(text)} chars")
        resp = urllib.request.urlopen(req, timeout=self.generate_timeout)
        while True:
            chunk = resp.read(self._stream_chunk_size)
            if not chunk:
                break
            yield chunk
