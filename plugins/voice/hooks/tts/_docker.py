"""Shared Docker helpers for TTS backends."""

from __future__ import annotations

import subprocess
import sys


def docker_stop_by_port(port: int) -> None:
    """Stop all Docker containers publishing the given port.

    Silently handles missing Docker binary, no matching containers,
    and command timeouts.
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"publish={port}",
             "--format", "{{.ID}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return
        container_ids = result.stdout.strip().split("\n")
        container_ids = [cid for cid in container_ids if cid]

        if not container_ids:
            return

        for cid in container_ids:
            print(f"Stopping container {cid} (port {port})...",
                  file=sys.stderr)
            subprocess.run(
                ["docker", "stop", cid],
                capture_output=True, timeout=30,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        from ._debug import log
        log(f"docker stop port {port}: {type(exc).__name__}: {exc}")
