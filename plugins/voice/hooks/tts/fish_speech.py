"""Fish Speech TTS backend — GPU-based, Gradio API on Docker :32611."""

from __future__ import annotations

import json
import subprocess
import urllib.request

from constants import env_port
from ._base import DockerBackend
from ._errors import TTSGenerationError

FISH_SPEECH_PORT = env_port("FISH_SPEECH_PORT", 32611)
GPU_THRESHOLD = env_port("GPU_THRESHOLD", 80)


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


class FishSpeechBackend(DockerBackend):
    name = "fish-speech"
    priority = 10
    port = FISH_SPEECH_PORT
    health_path = "/config"
    health_timeout = 1.0

    def is_available(self) -> bool:
        if not super().is_available():
            return False
        return _get_gpu_util() < GPU_THRESHOLD

    def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
        # Fish Speech ignores voice/speed — uses its own model
        payload = json.dumps({
            "data": [text, "", None, "", 0, 300, 0.8, 1.1, 0.8, 0, "on"],
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/gradio_api/call/partial",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        event_id = json.loads(resp.read())["event_id"]

        # Poll SSE stream for result
        resp = urllib.request.urlopen(
            f"{self.base_url}/gradio_api/call/partial/{event_id}",
            timeout=self.generate_timeout,
        )
        for line in resp:
            line = line.decode().strip()
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if isinstance(data, list) and len(data) > 0 and data[0] and "url" in data[0]:
                    audio = urllib.request.urlopen(
                        data[0]["url"], timeout=30,
                    ).read()
                    return audio

        raise TTSGenerationError("Fish Speech returned no audio")
