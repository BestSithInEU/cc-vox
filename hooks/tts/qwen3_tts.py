"""Qwen3-TTS backend — GPU-based, FastAPI REST on Docker :32614."""

from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request

QWEN3_TTS_PORT = int(os.environ.get("QWEN3_TTS_PORT", "32614"))
QWEN3_TTS_URL = f"http://localhost:{QWEN3_TTS_PORT}"


class Qwen3TTSBackend:
    name = "qwen3-tts"
    priority = 8

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{QWEN3_TTS_URL}/openapi.json", method="GET",
            )
            resp = urllib.request.urlopen(req, timeout=2.0)
            return 200 <= resp.status < 300
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def ensure_running(self) -> bool:
        return self.is_available()

    def generate(self, text: str, voice: str, speed: float) -> bytes:
        # Use /synthesize_speech/ with explicit voice (base_tts uses
        # a non-existent "default_en" voice internally)
        params = urllib.parse.urlencode({
            "text": text,
            "voice": voice or "p276",
            "speed": speed,
        })
        req = urllib.request.Request(
            f"{QWEN3_TTS_URL}/synthesize_speech/?{params}", method="GET",
        )
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.read()
