"""Audio playback and cross-process playback locking."""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
import time


def play_audio(audio_data: bytes, volume: float = 1.0) -> None:
    """Play WAV audio data. Prefers ffplay (streaming), falls back to file-based."""
    from ._debug import log

    if shutil.which("ffplay"):
        log(f"Playing audio via ffplay ({len(audio_data)} bytes, volume={volume})")
        cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
               "-probesize", "32", "-analyzeduration", "0"]
        if volume != 1.0:
            cmd += ["-volume", str(int(volume * 100))]
        cmd += ["-i", "pipe:0"]
        proc = subprocess.Popen(
            cmd,
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
            log(f"Playing audio via afplay (volume={volume})")
            cmd = ["afplay"]
            if volume != 1.0:
                cmd += ["-v", str(volume)]
            cmd.append(tmp_path)
            subprocess.run(cmd, check=True)
        elif shutil.which("aplay"):
            log("Playing audio via aplay")
            subprocess.run(["aplay", "-q", tmp_path], check=True)
        elif shutil.which("paplay"):
            log(f"Playing audio via paplay (volume={volume})")
            cmd = ["paplay"]
            if volume != 1.0:
                cmd += ["--volume", str(int(volume * 65536))]
            cmd.append(tmp_path)
            subprocess.run(cmd, check=True)
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
        stale_checked = False
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                os.ftruncate(self._fd, 0)
                os.write(self._fd, str(os.getpid()).encode())
                return True
            except BlockingIOError:
                if not stale_checked and _is_lock_stale():
                    stale_checked = True
                    # Stale lock from a dead process — remove and retry once
                    os.close(self._fd)
                    try:
                        os.unlink(LOCK_FILE)
                    except OSError:
                        pass
                    self._fd = os.open(LOCK_FILE, os.O_CREAT | os.O_WRONLY)
                    continue
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


def _is_lock_stale() -> bool:
    """Check if the lock file is held by a dead process."""
    try:
        fd = os.open(LOCK_FILE, os.O_RDONLY)
        try:
            raw = os.read(fd, 32)
            pid = int(raw.decode().strip())
            os.kill(pid, 0)  # signal 0 = just check if alive
            return False  # process exists
        except (ValueError, ProcessLookupError):
            return True  # PID invalid or process dead
        except PermissionError:
            return False  # process exists but owned by different user
        finally:
            os.close(fd)
    except OSError:
        return False
