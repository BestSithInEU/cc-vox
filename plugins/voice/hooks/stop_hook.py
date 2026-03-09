#!/usr/bin/env python3
"""
Stop hook - extract or generate voice summary.

Flow:
1. Look for voice marker in the last assistant message (instant, no API call)
2. If not found and response is short, speak it directly
3. Fall back to headless Claude to generate a summary (slower)
4. Last resort: truncate last message
5. Speak the summary via the say script
"""

import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Temporary file-based debug logging (stderr not visible in Claude debug)
_DEBUG_LOG = Path("/tmp/cc-vox-stop-hook.log")

def _flog(msg: str) -> None:
    with open(_DEBUG_LOG, "a") as f:
        f.write(f"{msg}\n")

from extraction import extract_speakable_text
from hook_framework import APPROVE, HookResult, run_hook
from session import find_session_file, get_last_assistant_message
from speaker import speak
from tts import select_backend
from tts._state_file import write_tts_state
from voice_common import VoiceConfig


def handle(data: dict, config: VoiceConfig) -> HookResult:
    session_id = data.get("session_id", "")
    _flog(f"stop: session_id={session_id!r}, config.enabled={config.enabled}, config.debug={config.debug}")
    _flog(f"stop: stdin keys={list(data.keys())}")

    if not session_id:
        _flog("stop: no session_id, skipping")
        return APPROVE

    # Prefer last_assistant_message from stdin (no file I/O, no race condition)
    last_msg = data.get("last_assistant_message", "")
    _flog(f"stop: stdin last_assistant_message={bool(last_msg)} ({len(last_msg)} chars)")

    session_file = find_session_file(session_id) if not last_msg else None

    if not last_msg and session_file:
        last_msg = get_last_assistant_message(session_file)
        _flog(f"stop: session file fallback={'found' if last_msg else 'empty'}")

    if not last_msg:
        _flog("stop: no message to speak, skipping")
        return APPROVE

    _flog(f"stop: last_msg preview: {last_msg[:120]!r}")

    # session_file still needed for headless summarization fallback
    if session_file is None:
        session_file = find_session_file(session_id)

    result = extract_speakable_text(last_msg, config, session_file or Path("/dev/null"))
    if not result:
        _flog("stop: extraction returned None, skipping")
        return APPROVE

    _flog(f"stop: extracted '{result.text[:80]}' (headless={result.used_headless})")

    # Pre-check backend availability (speak is fire-and-forget via Popen)
    backend = select_backend(config.backend, config.fallback)
    if backend is None:
        _flog("stop: no backend available")
        write_tts_state("none", config.voice, status="down")
        return HookResult(
            system_message=(
                "Voice feedback unavailable \u2014 no TTS backend is reachable. "
                "Run /voice:speak status for details."
            ),
        )

    _flog(f"stop: speaking via {backend.name}")
    speak(
        session_id, result.text, config.voice,
        config.speed, config.volume, config.debug,
    )

    if result.used_headless:
        return HookResult(system_message=f"\U0001f50a {result.text}")
    return APPROVE


def main():
    try:
        run_hook(handle)
    except Exception as exc:
        _flog(f"stop: CRASH: {exc}")
        import traceback
        _flog(traceback.format_exc())
        print('{"decision":"approve"}')


if __name__ == "__main__":
    main()
