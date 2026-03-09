"""stop-backends - Stop all running TTS backend services."""

from __future__ import annotations

import sys
from pathlib import Path

# ── Resolve imports from hooks/ ──────────────────────────────────────────────

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from tts import stop_all_backends


def main() -> int:
    print("Stopping TTS backends...", file=sys.stderr)
    stop_all_backends()
    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
