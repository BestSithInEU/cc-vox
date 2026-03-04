"""Chatterbox TTS backend — GPU-based, OpenAI-compatible API on Docker :32613."""

from __future__ import annotations

import os

from ._openai_compat import OpenAICompatibleBackend

CHATTERBOX_PORT = int(os.environ.get("CHATTERBOX_PORT", "32613"))


class ChatterboxBackend(OpenAICompatibleBackend):
    name = "chatterbox"
    priority = 12
    port = CHATTERBOX_PORT
    health_path = "/voices"
    model = "chatterbox"

    def _build_payload(self, text: str, voice: str, speed: float) -> dict:
        # Chatterbox uses voice cloning, not the Kokoro voice catalog
        payload = super()._build_payload(text, "default", speed)
        payload.pop("model", None)
        return payload
