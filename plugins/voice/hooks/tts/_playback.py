"""Audio playback and cross-process playback locking."""

from __future__ import annotations

import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator

if sys.platform == "win32":
    import msvcrt

    def _lock_exclusive_nb(fd: int) -> None:
        """Non-blocking exclusive lock (Windows)."""
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _unlock(fd: int) -> None:
        """Unlock (Windows)."""
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def _lock_exclusive_nb(fd: int) -> None:
        """Non-blocking exclusive lock (Unix)."""
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(fd: int) -> None:
        """Unlock (Unix)."""
        fcntl.flock(fd, fcntl.LOCK_UN)


def _default_lock_path() -> str:
    """Return platform-appropriate lock file path."""
    if sys.platform == "win32":
        return os.path.join(tempfile.gettempdir(), "voice-playback.lock")
    return "/tmp/voice-playback.lock"


LOCK_FILE = _default_lock_path()


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
        elif sys.platform == "win32":
            if volume != 1.0:
                log("winsound does not support volume control, ignoring")
            log("Playing audio via winsound")
            import winsound
            winsound.PlaySound(tmp_path, winsound.SND_FILENAME)
        else:
            print(
                "Error: No audio player found "
                "(tried ffplay, afplay, aplay, paplay)",
                file=sys.stderr,
            )
    finally:
        os.unlink(tmp_path)


def play_audio_streaming(
    chunks: Iterator[bytes], volume: float = 1.0,
) -> None:
    """Pipe audio chunks to ffplay as they arrive.

    Falls back to buffering all chunks and calling play_audio() if ffplay
    is not available.
    """
    from ._debug import log

    if not shutil.which("ffplay"):
        # Fallback: buffer everything and use file-based playback
        log("Streaming fallback: ffplay not available, buffering")
        data = b"".join(chunks)
        play_audio(data, volume)
        return

    cmd = [
        "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
        "-probesize", "32", "-analyzeduration", "0",
    ]
    if volume != 1.0:
        cmd += ["-volume", str(int(volume * 100))]
    cmd += ["-i", "pipe:0"]

    log(f"Streaming audio via ffplay (volume={volume})")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for chunk in chunks:
            proc.stdin.write(chunk)
        proc.stdin.close()
        proc.wait()
    except (BrokenPipeError, OSError):
        pass
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        proc.wait()


class PlaybackLock:
    """File-based mutex to prevent overlapping voices.

    Uses fcntl.flock on Unix and msvcrt.locking on Windows.
    """

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
        self._fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)
        deadline = time.monotonic() + self.max_wait
        stale_checked = False
        while True:
            try:
                _lock_exclusive_nb(self._fd)
                os.lseek(self._fd, 0, os.SEEK_SET)
                os.ftruncate(self._fd, 0)
                os.write(self._fd, str(os.getpid()).encode())
                return True
            except (BlockingIOError, OSError):
                if not stale_checked and _is_lock_stale():
                    stale_checked = True
                    # Stale lock from a dead process — remove and retry once
                    os.close(self._fd)
                    try:
                        os.unlink(LOCK_FILE)
                    except OSError:
                        pass
                    self._fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)
                    continue
                if time.monotonic() >= deadline:
                    os.close(self._fd)
                    self._fd = None
                    return False
                time.sleep(0.2)

    def release(self) -> None:
        if self._fd is not None:
            try:
                _unlock(self._fd)
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None


def kill_current_playback() -> bool:
    """Kill the process currently holding the playback lock.

    Reads the PID from the lock file and sends SIGTERM (Unix) or
    taskkill (Windows). Returns True if a process was killed.
    """
    try:
        fd = os.open(LOCK_FILE, os.O_RDONLY)
        try:
            raw = os.read(fd, 32)
            pid = int(raw.decode().strip())
        except (ValueError, OSError):
            return False
        finally:
            os.close(fd)

        if pid == os.getpid():
            return False  # don't kill ourselves

        if sys.platform == "win32":
            import subprocess as _sp
            try:
                _sp.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except OSError:
                return False
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                return True
            except (ProcessLookupError, PermissionError, OSError):
                return False
    except OSError:
        return False


def _is_lock_stale() -> bool:
    """Check if the lock file is held by a dead process."""
    try:
        fd = os.open(LOCK_FILE, os.O_RDONLY)
        try:
            raw = os.read(fd, 32)
            pid = int(raw.decode().strip())
            os.kill(pid, 0)  # signal 0 = just check if alive
            return False  # process exists
        except PermissionError:
            return False  # process exists but owned by different user
        except (ValueError, ProcessLookupError, OSError):
            return True  # PID invalid or process dead
        finally:
            os.close(fd)
    except OSError:
        return False
