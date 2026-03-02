"""Chatterbox TTS backend — GPU-based, OpenAI-compatible API on Docker :32613."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

CHATTERBOX_PORT = int(os.environ.get("CHATTERBOX_PORT", "32613"))
CHATTERBOX_URL = f"http://localhost:{CHATTERBOX_PORT}"


class ChatterboxBackend:
    name = "chatterbox"
    priority = 12

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{CHATTERBOX_URL}/voices", method="GET")
            resp = urllib.request.urlopen(req, timeout=2.0)
            return 200 <= resp.status < 300
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def ensure_running(self) -> bool:
        return self.is_available()

    def generate(self, text: str, voice: str, speed: float) -> bytes:  # noqa: ARG002
        # Chatterbox uses voice cloning, not the Kokoro voice catalog
        payload = json.dumps({
            "input": text,
            "voice": "default",
            "response_format": "wav",
        }).encode()
        req = urllib.request.Request(
            f"{CHATTERBOX_URL}/v1/audio/speech",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.read()
