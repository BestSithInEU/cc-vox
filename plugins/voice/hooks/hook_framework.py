"""Minimal hook framework — shared boilerplate for all Claude Code hooks."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Callable

from voice_common import VoiceConfig, get_voice_config


@dataclass
class HookResult:
    """What a hook handler returns."""

    decision: str = "approve"
    hook_event_name: str | None = None
    additional_context: str | None = None
    system_message: str | None = None

    def to_json(self) -> str:
        if self.hook_event_name and self.additional_context is not None:
            payload: dict = {
                "hookSpecificOutput": {
                    "hookEventName": self.hook_event_name,
                    "additionalContext": self.additional_context,
                }
            }
            return json.dumps(payload)

        result: dict = {"decision": self.decision}
        if self.system_message:
            result["systemMessage"] = self.system_message
        return json.dumps(result)


APPROVE = HookResult()


def run_hook(
    handler: Callable[[dict, VoiceConfig], HookResult],
    *,
    require_enabled: bool = True,
) -> None:
    """Parse stdin, load config, call handler, print JSON result.

    If *require_enabled* is True (default), returns approve when voice is
    disabled without calling the handler.
    """
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(APPROVE.to_json())
        return

    config = get_voice_config()

    # Enable debug logging for the whole hook pipeline
    if config.debug:
        from tts._debug import enable
        enable()

    if require_enabled and not config.enabled:
        print(APPROVE.to_json())
        return

    result = handler(data, config)
    print(result.to_json())
