"""Fish Speech TTS backend — GPU-based, Gradio API on Docker :32611."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

FISH_SPEECH_PORT = int(os.environ.get("FISH_SPEECH_PORT", "32611"))
FISH_SPEECH_URL = f"http://localhost:{FISH_SPEECH_PORT}"
GPU_THRESHOLD = int(os.environ.get("GPU_THRESHOLD", "80"))


def _get_gpu_util() -> int:
    """Return GPU utilization %, or 100 if unavailable."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip().split("\n")[0].strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 100


class FishSpeechBackend:
    name = "fish-speech"
    priority = 10

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{FISH_SPEECH_URL}/config", method="GET",
            )
            resp = urllib.request.urlopen(req, timeout=1.0)
            if not (200 <= resp.status < 300):
                return False
        except (urllib.error.URLError, OSError, ValueError):
            return False
        return _get_gpu_util() < GPU_THRESHOLD

    def ensure_running(self) -> bool:
        return self.is_available()

    def generate(self, text: str, voice: str, speed: float) -> bytes:  # noqa: ARG002
        # Fish Speech ignores voice/speed — uses its own model
        payload = json.dumps({
            "data": [text, "", None, "", 0, 300, 0.8, 1.1, 0.8, 0, "on"],
        }).encode()
        req = urllib.request.Request(
            f"{FISH_SPEECH_URL}/gradio_api/call/partial",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        event_id = json.loads(resp.read())["event_id"]

        # Poll SSE stream for result
        resp = urllib.request.urlopen(
            f"{FISH_SPEECH_URL}/gradio_api/call/partial/{event_id}",
            timeout=60,
        )
        for line in resp:
            line = line.decode().strip()
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if isinstance(data, list) and data[0] and "url" in data[0]:
                    audio = urllib.request.urlopen(
                        data[0]["url"], timeout=30,
                    ).read()
                    return audio

        raise RuntimeError("Fish Speech returned no audio")
