"""Kokoro TTS backend — CPU-based, OpenAI-compatible API on Docker :32612."""

from __future__ import annotations

from constants import env_port
from ._openai_compat import OpenAICompatibleBackend
from .voices import to_kokoro

KOKORO_PORT = env_port("KOKORO_PORT", 32612)


class KokoroBackend(OpenAICompatibleBackend):
    name = "kokoro"
    priority = 20
    port = KOKORO_PORT
    health_path = "/v1/models"
    health_timeout = 1.0
    model = "kokoro"
    supports_speed = True

    def _build_payload(self, text: str, voice: str, speed: float) -> dict:
        return super()._build_payload(text, to_kokoro(voice), speed)
