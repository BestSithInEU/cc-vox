"""Kokoro TTS backend — CPU-based, OpenAI-compatible API on Docker :32612."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .voices import to_kokoro

KOKORO_PORT = int(os.environ.get("KOKORO_PORT", "32612"))
KOKORO_URL = f"http://localhost:{KOKORO_PORT}"


class KokoroBackend:
    name = "kokoro"
    priority = 20

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{KOKORO_URL}/v1/models", method="GET")
            resp = urllib.request.urlopen(req, timeout=1.0)
            return 200 <= resp.status < 300
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def ensure_running(self) -> bool:
        return self.is_available()

    def generate(self, text: str, voice: str, speed: float) -> bytes:
        voice = to_kokoro(voice)
        payload: dict[str, object] = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "wav",
        }
        if speed != 1.0:
            payload["speed"] = speed

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{KOKORO_URL}/v1/audio/speech",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.read()
