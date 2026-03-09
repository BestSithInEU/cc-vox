#!/usr/bin/env python3
"""
PostToolUse hook - inject brief voice reminder after tool calls.

This keeps the voice summary instruction fresh in Claude's context
after long chains of tool calls, where it might otherwise forget
the initial UserPromptSubmit instructions.

When conversational mode is enabled, this hook also triggers periodic
voice updates during long tool chains ("still reading files...").
"""

import sys
import tempfile
import time
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from hook_framework import HookResult, run_hook
from voice_common import VoiceConfig, build_short_reminder

# Tool name → spoken phrase mapping
_TOOL_PHRASES: dict[str, str] = {
    "Read": "still reading files",
    "Bash": "running commands",
    "Edit": "editing code",
    "Write": "writing files",
    "Grep": "searching the codebase",
    "Glob": "looking for files",
    "Agent": "working with a sub-agent",
}

_DEFAULT_PHRASE = "still working"


def _last_spoke_path(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"voice-{session_id}-last-spoke"


def _should_speak(session_id: str, interval: int) -> bool:
    """Check if enough time has passed since last conversational update."""
    if not session_id:
        return False
    path = _last_spoke_path(session_id)
    try:
        ts = float(path.read_text(encoding="utf-8").strip())
        return (time.time() - ts) >= interval
    except (OSError, ValueError):
        return True  # first time or corrupt file


def _mark_spoke(session_id: str) -> None:
    path = _last_spoke_path(session_id)
    try:
        path.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def handle(data: dict, config: VoiceConfig) -> HookResult:
    # Conversational mode: periodic voice updates during long tool chains
    if config.conversational:
        session_id = data.get("session_id", "")
        if session_id and _should_speak(session_id, config.update_interval):
            tool_name = data.get("tool_name", "")
            phrase = _TOOL_PHRASES.get(tool_name, _DEFAULT_PHRASE)
            _mark_spoke(session_id)

            from speaker import speak
            speak(session_id, f"{phrase}...", config.voice, config.speed, config.volume)

    return HookResult(
        hook_event_name="PostToolUse",
        additional_context=build_short_reminder(config.max_sentences),
    )


def main():
    run_hook(handle)


if __name__ == "__main__":
    main()
