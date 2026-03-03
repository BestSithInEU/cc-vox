#!/usr/bin/env python3
"""
Stop hook - extract or generate voice summary.

Flow:
1. Look for 📢 marker in the last assistant message (instant, no API call)
2. If not found and response is short, speak it directly
3. Fall back to headless Claude to generate a summary (slower)
4. Last resort: truncate last message
5. Speak the summary via the say script
"""

import json
import subprocess
import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from session import (
    extract_voice_marker,
    find_session_file,
    get_last_assistant_message,
    get_recent_conversation,
    is_short_response_sentences,
    trim_to_sentences,
)
from summarize import summarize_with_claude
from voice_common import get_voice_config

PLUGIN_ROOT = Path(__file__).parent.parent


def speak_summary(
    session_id: str,
    summary: str,
    voice: str,
    speed: float = 1.0,
) -> None:
    """Call the say script to speak the summary (runs in background)."""
    say_script = PLUGIN_ROOT / "scripts" / "say"

    cmd = [
        str(say_script),
        "--session", session_id,
        "--voice", voice,
    ]
    if speed != 1.0:
        cmd += ["--speed", str(speed)]
    cmd.append(summary)

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"decision": "approve"}))
        return

    session_id = data.get("session_id", "")

    config = get_voice_config()
    if not config.enabled:
        print(json.dumps({"decision": "approve"}))
        return

    if not session_id:
        print(json.dumps({"decision": "approve"}))
        return

    session_file = find_session_file(session_id)
    if not session_file:
        print(json.dumps({"decision": "approve"}))
        return

    summary = None
    used_headless = False

    last_assistant_msg = get_last_assistant_message(session_file)

    flexible_limit = config.max_sentences + 1

    # Strategy 1: Try to extract 📢 marker (instant!)
    if last_assistant_msg:
        marker_summary = extract_voice_marker(last_assistant_msg)
        if marker_summary:
            summary = trim_to_sentences(marker_summary, flexible_limit)

    # Strategy 2: If no marker but response is short, speak directly
    if not summary and last_assistant_msg:
        if is_short_response_sentences(last_assistant_msg, config.max_sentences):
            summary = last_assistant_msg

    # Strategy 3: Fall back to headless Claude summarization (slower)
    if not summary and last_assistant_msg:
        conversation = get_recent_conversation(session_file)
        if conversation:
            summary = summarize_with_claude(
                conversation, config.prompt, config.max_sentences,
            )
            if summary:
                summary = trim_to_sentences(summary, flexible_limit)
                used_headless = True

    # Strategy 4: Last resort - truncate last message
    if not summary and last_assistant_msg:
        summary = trim_to_sentences(last_assistant_msg, config.max_sentences)

    if not summary:
        print(json.dumps({"decision": "approve"}))
        return

    speak_summary(session_id, summary, config.voice, config.speed)

    if used_headless:
        print(json.dumps({
            "decision": "approve",
            "systemMessage": f"🔊 {summary}"
        }))
    else:
        print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
