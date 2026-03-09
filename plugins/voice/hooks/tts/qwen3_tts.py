"""Qwen3-TTS backend — GPU-based, FastAPI REST on Docker :32614."""

from __future__ import annotations

import urllib.parse
import urllib.request

from constants import env_port
from ._base import DockerBackend

QWEN3_TTS_PORT = env_port("QWEN3_TTS_PORT", 32614)


class Qwen3TTSBackend(DockerBackend):
    name = "qwen3-tts"
    priority = 8
    port = QWEN3_TTS_PORT
    health_path = "/openapi.json"

    def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
        params = urllib.parse.urlencode({
            "text": text,
            "voice": voice or "p276",
            "speed": speed,
        })
        req = urllib.request.Request(
            f"{self.base_url}/synthesize_speech/?{params}", method="GET",
        )
        resp = urllib.request.urlopen(req, timeout=self.generate_timeout)
        return resp.read()
