"""pocket-tts backend — lightweight CPU fallback via uvx on :8000."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
import urllib.request

from ._base import TTSBackend
from .voices import to_alias

TTS_PORT = int(os.environ.get("TTS_PORT", "8000"))


def _find_pid_by_port(port: int) -> int | None:
    """Find the PID of the process listening on *port*, or None."""
    try:
        result = subprocess.run(
            ["ss", "-tlnp", "sport", "=", f":{port}"],
            capture_output=True, text=True, timeout=5,
        )
        match = re.search(r"pid=(\d+)", result.stdout)
        return int(match.group(1)) if match else None
    except (OSError, subprocess.TimeoutExpired):
        return None


class PocketTTSBackend(TTSBackend):
    name = "pocket-tts"
    priority = 30
    port = TTS_PORT
    health_path = "/health"
    health_timeout = 1.0

    def ensure_running(self) -> bool:
        if self.is_available():
            return True
        return self._start()

    def _start(self) -> bool:
        """Auto-start pocket-tts via uvx."""
        # Race guard: another process may already be starting
        if _find_pid_by_port(TTS_PORT) is not None:
            # Something is listening — wait for it to become healthy
            for _ in range(30):
                if self.is_available():
                    return True
                time.sleep(1)
            return False

        print("Starting pocket-tts server...", file=sys.stderr)
        try:
            with open("/tmp/pocket-tts-server.log", "w") as log_fd:
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

    def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
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
            f"{self.base_url}/tts",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=self.generate_timeout)
        return resp.read()

    def stop(self) -> None:
        pid = _find_pid_by_port(TTS_PORT)
        if pid is not None:
            print(f"Stopping pocket-tts (pid {pid})...", file=sys.stderr)
            os.kill(pid, signal.SIGTERM)
            # Wait up to 3s for the process to exit
            for _ in range(15):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.2)
                except ProcessLookupError:
                    return  # process exited
