#!/usr/bin/env python3
"""
UserPromptSubmit hook - inject voice summary reminder into each turn.

This hook adds a system message reminding Claude to end responses with a
voice-friendly summary marker, making extraction easy and avoiding
the need for a headless Claude call to generate summaries.
"""

import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from hook_framework import APPROVE, HookResult, run_hook
from tts._playback import kill_current_playback
from voice_common import (
    VoiceConfig,
    build_full_reminder,
    clear_just_disabled_flag,
)


def handle(data: dict, config: VoiceConfig) -> HookResult:
    # Kill any ongoing playback when user sends a new prompt
    kill_current_playback()

    # If just disabled, inject a "don't add summaries" message and clear the flag
    if config.just_disabled:
        clear_just_disabled_flag()
        return HookResult(
            hook_event_name="UserPromptSubmit",
            additional_context=(
                "Voice feedback has been DISABLED. "
                "Do NOT add \U0001f4e2 spoken summaries to your responses."
            ),
        )

    if not config.enabled:
        return APPROVE

    return HookResult(
        hook_event_name="UserPromptSubmit",
        additional_context=build_full_reminder(config.max_sentences, config.prompt),
    )


def main():
    run_hook(handle, require_enabled=False)


if __name__ == "__main__":
    main()
