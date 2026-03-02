"""pocket-tts backend — lightweight CPU fallback via uvx on :8000."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .voices import to_alias

TTS_PORT = int(os.environ.get("TTS_PORT", "8000"))
POCKET_TTS_URL = f"http://localhost:{TTS_PORT}"


class PocketTTSBackend:
    name = "pocket-tts"
    priority = 30

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{POCKET_TTS_URL}/health", method="GET",
            )
            resp = urllib.request.urlopen(req, timeout=1.0)
            return 200 <= resp.status < 300
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def ensure_running(self) -> bool:
        if self.is_available():
            return True
        return self._start()

    def _start(self) -> bool:
        """Auto-start pocket-tts via uvx."""
        print("Starting pocket-tts server...", file=sys.stderr)
        try:
            log_fd = open("/tmp/pocket-tts-server.log", "w")
            subprocess.Popen(
                ["uvx", "pocket-tts", "serve", "--host", "localhost",
                 "--port", str(TTS_PORT)],
                stdout=log_fd,
                stderr=subprocess.STDOUT,
            )
        except OSError:
            return False

        for _ in range(60):
            if self.is_available():
                print("pocket-tts started!", file=sys.stderr)
                return True
            time.sleep(1)

        print("Error: pocket-tts failed to start within 60s", file=sys.stderr)
        return False

    def generate(self, text: str, voice: str, speed: float) -> bytes:  # noqa: ARG002
        # pocket-tts ignores speed, uses alias names
        alias = to_alias(voice)
        boundary = "----PocketTTSBoundary"
        parts = []

        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="text"\r\n\r\n'
            f"{text}\r\n"
        )
        if alias:
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="voice_url"\r\n\r\n'
                f"{alias}\r\n"
            )
        parts.append(f"--{boundary}--\r\n")

        body = "".join(parts).encode()
        req = urllib.request.Request(
            f"{POCKET_TTS_URL}/tts",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.read()
