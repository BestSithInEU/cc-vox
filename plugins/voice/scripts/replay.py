"""
replay - Replay a recent voice clip from history.

Usage: replay [N]  (default 0 = most recent)
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Resolve imports from hooks/ ──────────────────────────────────────────────
HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from tts._history import get_clip, list_clips
from tts._playback import play_audio
from voice_common import get_voice_config


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        clips = list_clips(limit=10)
        if not clips:
            print("No voice history found.", file=sys.stderr)
            return 0
        print(f"{'#':<4} {'Time':<20} {'Backend':<14} {'Text'}")
        print("-" * 70)
        for i, clip in enumerate(clips):
            text_preview = clip.get("text", "")[:40]
            if len(clip.get("text", "")) > 40:
                text_preview += "..."
            print(f"{i:<4} {clip.get('name', '?'):<20} {clip.get('backend', '?'):<14} {text_preview}")
        return 0

    index = 0
    if len(sys.argv) > 1:
        try:
            index = int(sys.argv[1])
        except ValueError:
            print(f"Usage: replay [N]  (0 = most recent)", file=sys.stderr)
            return 1

    result = get_clip(index)
    if result is None:
        print(f"No clip at index {index}. Use 'replay --list' to see history.", file=sys.stderr)
        return 1

    audio, meta = result
    config = get_voice_config()
    print(f"Replaying: {meta.get('text', '?')[:60]}", file=sys.stderr)
    play_audio(audio, config.volume)
    return 0


if __name__ == "__main__":
    sys.exit(main())
