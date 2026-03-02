"""Audio playback and cross-process playback locking."""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
import time


def play_audio(audio_data: bytes) -> None:
    """Play WAV audio data. Prefers ffplay (streaming), falls back to file-based."""
    if shutil.which("ffplay"):
        proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
             "-probesize", "32", "-analyzeduration", "0", "-i", "pipe:0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=audio_data)
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_data)
        tmp_path = f.name

    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", tmp_path], check=True)
        elif shutil.which("aplay"):
            subprocess.run(["aplay", "-q", tmp_path], check=True)
        elif shutil.which("paplay"):
            subprocess.run(["paplay", tmp_path], check=True)
        else:
            print(
                "Error: No audio player found "
                "(tried ffplay, afplay, aplay, paplay)",
                file=sys.stderr,
            )
    finally:
        os.unlink(tmp_path)


LOCK_FILE = "/tmp/voice-playback.lock"


class PlaybackLock:
    """File-based mutex using fcntl.flock to prevent overlapping voices."""

    def __init__(self, max_wait: int = 30):
        self.max_wait = max_wait
        self._fd: int | None = None

    def __enter__(self) -> PlaybackLock:
        if not self.acquire():
            raise TimeoutError(
                f"Timeout waiting for audio lock after {self.max_wait}s"
            )
        return self

    def __exit__(self, *_: object) -> None:
        self.release()

    def acquire(self) -> bool:
        self._fd = os.open(LOCK_FILE, os.O_CREAT | os.O_WRONLY)
        deadline = time.monotonic() + self.max_wait
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                os.ftruncate(self._fd, 0)
                os.write(self._fd, str(os.getpid()).encode())
                return True
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(self._fd)
                    self._fd = None
                    return False
                time.sleep(0.2)

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
