"""
status - Show voice plugin configuration and backend health.

Usage: status [--detailed]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# ── Resolve imports from hooks/ ──────────────────────────────────────────────
HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from tts import _registry
from voice_common import get_voice_config


def probe_backends() -> list[dict[str, str | int]]:
    """Probe all registered backends and measure response time."""
    results = []
    registry = _registry()
    by_priority = sorted(registry.values(), key=lambda cls: (cls.priority, cls.name))

    for cls in by_priority:
        inst = cls()
        t0 = time.monotonic()
        available = inst.is_available()
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        results.append({
            "name": inst.name,
            "status": "UP" if available else "DOWN",
            "port": inst.port,
            "priority": inst.priority,
            "response_ms": elapsed_ms if available else 0,
        })

    return results


def format_status(detailed: bool = False) -> str:
    """Format config summary and optionally a backend table."""
    config = get_voice_config()
    probes = probe_backends()

    lines = [
        "Voice Plugin Status",
        "=" * 40,
        f"  enabled:        {config.enabled}",
        f"  voice:          {config.voice}",
        f"  backend:        {config.backend}",
        f"  speed:          {config.speed}",
        f"  volume:         {config.volume}",
        f"  max_sentences:  {config.max_sentences}",
        f"  fallback:       {config.fallback}",
    ]
    if config.prompt:
        lines.append(f'  prompt:         "{config.prompt}"')

    # Active backend summary
    active = [p for p in probes if p["status"] == "UP"]
    if active:
        best = active[0]
        lines.append(f"\n  Active backend: {best['name']} (port {best['port']}, {best['response_ms']}ms)")
    else:
        lines.append("\n  Active backend: NONE (all backends down)")

    if detailed:
        lines.append("")
        lines.append(format_backend_table(probes))

    return "\n".join(lines)


def format_backend_table(probes: list[dict]) -> str:
    """Format a table of all backend statuses."""
    header = f"{'Backend':<16} {'Status':<8} {'Port':<8} {'Response':<10} {'Priority'}"
    sep = "-" * len(header)
    rows = [header, sep]

    for p in probes:
        resp = f"{p['response_ms']}ms" if p["status"] == "UP" else "--"
        rows.append(
            f"{p['name']:<16} {p['status']:<8} {p['port']:<8} {resp:<10} {p['priority']}"
        )

    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Voice plugin status")
    parser.add_argument(
        "--detailed", action="store_true",
        help="Show full backend health table",
    )
    args = parser.parse_args()

    print(format_status(detailed=args.detailed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
