"""Launch the say script as a background subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tts._debug import log

PLUGIN_ROOT = Path(__file__).parent.parent
SAY_SCRIPT = PLUGIN_ROOT / "scripts" / "say.py"


def speak(
    session_id: str,
    text: str,
    voice: str,
    speed: float = 1.0,
    volume: float = 1.0,
    debug: bool = False,
) -> None:
    """Call the say script in the background. Swallows OSError."""
    cmd = [
        "uv", "run", "python", str(SAY_SCRIPT),
        "--session", session_id,
        "--voice", voice,
    ]
    if speed != 1.0:
        cmd += ["--speed", str(speed)]
    if volume != 1.0:
        cmd += ["--volume", str(volume)]
    if debug:
        cmd.append("--debug")
    cmd.append(text)

    try:
        log_file = Path("/tmp/cc-vox-say.log")
        with open(log_file, "a") as lf:
            lf.write(f"--- cmd: {' '.join(cmd)}\n")
        stderr_dest = open(log_file, "a") if debug else subprocess.DEVNULL
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=stderr_dest,
        )
    except OSError as exc:
        log(f"speak: failed to launch say script: {exc}")
