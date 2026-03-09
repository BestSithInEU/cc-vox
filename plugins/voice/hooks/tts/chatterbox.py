"""Chatterbox TTS backend — GPU-based, OpenAI-compatible API on Docker :32613."""

from __future__ import annotations

import base64
from pathlib import Path

from constants import env_port
from ._openai_compat import OpenAICompatibleBackend

CHATTERBOX_PORT = env_port("CHATTERBOX_PORT", 32613)


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

        # Voice cloning: include reference audio if configured
        from voice_common import get_voice_config
        config = get_voice_config()
        if config.clone_audio:
            ref_path = Path(config.clone_audio)
            if ref_path.exists():
                audio_bytes = ref_path.read_bytes()
                payload["reference_audio"] = base64.b64encode(audio_bytes).decode()
                from ._debug import log
                log(f"chatterbox: using clone reference {ref_path.name}")

        return payload
