#!/usr/bin/env python3
"""
UserPromptSubmit hook - inject voice summary reminder into each turn.

This hook adds a system message reminding Claude to end responses with a
voice-friendly summary marker (📢), making extraction easy and avoiding
the need for a headless Claude call to generate summaries.
"""

import json
import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from voice_common import (
    get_voice_config,
    build_full_reminder,
    clear_just_disabled_flag,
)


def main():
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"decision": "approve"}))
        return

    config = get_voice_config()

    # If just disabled, inject a "don't add summaries" message and clear the flag
    if config.just_disabled:
        clear_just_disabled_flag()
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    "Voice feedback has been DISABLED. "
                    "Do NOT add 📢 spoken summaries to your responses."
                )
            }
        }))
        return

    if not config.enabled:
        print(json.dumps({"decision": "approve"}))
        return

    reminder = build_full_reminder(config.max_words, config.prompt)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder
        }
    }))


if __name__ == "__main__":
    main()
