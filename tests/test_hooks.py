"""Tests for hook entry points — UserPromptSubmit, PostToolUse, Stop."""

from __future__ import annotations

import io
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from voice_common import VoiceConfig


# ── Helpers ───────────────────────────────────────────────────────────


def _run_hook(module_name: str, input_data: dict, config: VoiceConfig) -> dict:
    """Run a hook's main() with mocked stdin/stdout and config.

    Returns the parsed JSON output from stdout.
    """
    stdin = io.StringIO(json.dumps(input_data))
    stdout = io.StringIO()

    with (
        patch.dict(sys.modules, {}),  # force fresh import each time
        patch("hook_framework.sys.stdin", stdin),
        patch("hook_framework.sys.stdout", stdout),
        patch("hook_framework.get_voice_config", return_value=config),
    ):
        mod = __import__(module_name)
        mod.main()

    output = stdout.getvalue().strip()
    return json.loads(output) if output else {}


# ── UserPromptSubmit hook ─────────────────────────────────────────────


class TestUserPromptSubmitHook:
    def test_disabled_approves(self) -> None:
        config = VoiceConfig(enabled=False)
        result = _run_hook("user_prompt_submit_hook", {"prompt": "hello"}, config)
        assert result == {"decision": "approve"}

    def test_just_disabled_outputs_disabled_text(self) -> None:
        config = VoiceConfig(enabled=False, just_disabled=True)
        with patch("user_prompt_submit_hook.clear_just_disabled_flag") as mock_clear:
            stdin = io.StringIO(json.dumps({"prompt": "hello"}))
            stdout = io.StringIO()
            with (
                patch("hook_framework.sys.stdin", stdin),
                patch("hook_framework.sys.stdout", stdout),
                patch("hook_framework.get_voice_config", return_value=config),
            ):
                import user_prompt_submit_hook
                user_prompt_submit_hook.main()

            mock_clear.assert_called_once()

        output = json.loads(stdout.getvalue().strip())
        hso = output.get("hookSpecificOutput", {})
        assert "DISABLED" in hso.get("additionalContext", "")

    def test_enabled_outputs_voice_reminder(self) -> None:
        config = VoiceConfig(enabled=True, max_sentences=2)
        result = _run_hook("user_prompt_submit_hook", {"prompt": "hello"}, config)
        hso = result.get("hookSpecificOutput", {})
        context = hso.get("additionalContext", "")
        assert "\U0001f4e2" in context  # 📢 character

    def test_enabled_reminder_contains_sentence_count(self) -> None:
        config = VoiceConfig(enabled=True, max_sentences=3)
        result = _run_hook("user_prompt_submit_hook", {"prompt": "hi"}, config)
        hso = result.get("hookSpecificOutput", {})
        context = hso.get("additionalContext", "")
        assert "3 sentences" in context


# ── PostToolUse hook ──────────────────────────────────────────────────


class TestPostToolUseHook:
    def test_disabled_approves(self) -> None:
        config = VoiceConfig(enabled=False)
        result = _run_hook("post_tool_use_hook", {"tool": "Read"}, config)
        assert result == {"decision": "approve"}

    def test_enabled_outputs_short_reminder(self) -> None:
        config = VoiceConfig(enabled=True, max_sentences=2)
        result = _run_hook("post_tool_use_hook", {"tool": "Read"}, config)
        hso = result.get("hookSpecificOutput", {})
        context = hso.get("additionalContext", "")
        assert "\U0001f4e2" in context  # 📢 character
        assert "Voice feedback" in context or "voice" in context.lower()

    def test_enabled_reminder_contains_sentence_limit(self) -> None:
        config = VoiceConfig(enabled=True, max_sentences=4)
        result = _run_hook("post_tool_use_hook", {"tool": "Bash"}, config)
        hso = result.get("hookSpecificOutput", {})
        context = hso.get("additionalContext", "")
        assert "4 sentences" in context


# ── Stop hook ─────────────────────────────────────────────────────────


class TestStopHookDisabled:
    def test_disabled_approves(self) -> None:
        config = VoiceConfig(enabled=False)
        result = _run_hook("stop_hook", {"session_id": "abc"}, config)
        assert result == {"decision": "approve"}

    def test_no_session_id_approves(self) -> None:
        config = VoiceConfig(enabled=True)
        result = _run_hook("stop_hook", {}, config)
        assert result == {"decision": "approve"}

    def test_empty_session_id_approves(self) -> None:
        config = VoiceConfig(enabled=True)
        result = _run_hook("stop_hook", {"session_id": ""}, config)
        assert result == {"decision": "approve"}


class TestStopHookStrategy1Marker:
    """Strategy 1: marker found in last assistant message.

    Uses real extract_voice_marker and trim_to_sentences (no mocking)
    so the actual parsing logic is exercised.
    """

    def test_marker_found_calls_speak(self) -> None:
        config = VoiceConfig(enabled=True, voice="af_heart", speed=1.0, max_sentences=2)
        marker_text = "Here is code.\n\n\U0001f4e2 [I updated the config file.]"
        input_data = {"session_id": "test-session-123"}

        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()

        with (
            patch("hook_framework.sys.stdin", stdin),
            patch("hook_framework.sys.stdout", stdout),
            patch("hook_framework.get_voice_config", return_value=config),
            patch("stop_hook.find_session_file", return_value="/fake/session.jsonl"),
            patch("stop_hook.get_last_assistant_message", return_value=marker_text),
            patch("stop_hook.speak") as mock_speak,
        ):
            import stop_hook
            stop_hook.main()

        mock_speak.assert_called_once()
        args = mock_speak.call_args[0]
        assert args[0] == "test-session-123"
        assert args[1] == "I updated the config file."
        assert args[2] == "af_heart"
        assert args[3] == 1.0


class TestStopHookStrategy2Short:
    """Strategy 2: short response without marker — speak directly.

    Uses real extract_voice_marker and is_short_response_sentences (no mocking)
    so the actual threshold check is exercised.
    """

    def test_short_response_speaks_directly(self) -> None:
        config = VoiceConfig(enabled=True, voice="af_heart", speed=1.0, max_sentences=2)
        short_text = "Done."
        input_data = {"session_id": "test-session-456"}

        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()

        with (
            patch("hook_framework.sys.stdin", stdin),
            patch("hook_framework.sys.stdout", stdout),
            patch("hook_framework.get_voice_config", return_value=config),
            patch("stop_hook.find_session_file", return_value="/fake/session.jsonl"),
            patch("stop_hook.get_last_assistant_message", return_value=short_text),
            patch("stop_hook.speak") as mock_speak,
        ):
            import stop_hook
            stop_hook.main()

        mock_speak.assert_called_once_with(
            "test-session-456",
            "Done.",
            "af_heart",
            1.0,
            1.0,
            False,
        )


class TestStopHookStrategy3Summarize:
    """Strategy 3: headless Claude summarization fallback."""

    def test_summarize_fallback_calls_speak(self) -> None:
        config = VoiceConfig(enabled=True, voice="af_heart", speed=1.0, max_sentences=2)
        long_text = "I made a lot of changes. " * 20
        input_data = {"session_id": "test-session-789"}

        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()

        with (
            patch("hook_framework.sys.stdin", stdin),
            patch("hook_framework.sys.stdout", stdout),
            patch("hook_framework.get_voice_config", return_value=config),
            patch("stop_hook.find_session_file", return_value="/fake/session.jsonl"),
            patch("stop_hook.get_last_assistant_message", return_value=long_text),
            patch("extraction.extract_voice_marker", return_value=None),
            patch("extraction.is_short_response_sentences", return_value=False),
            patch("extraction.get_recent_conversation", return_value=[("user", "go"), ("assistant", long_text)]),
            patch("extraction.summarize_with_claude", return_value="Made many changes."),
            patch("extraction.trim_to_sentences", return_value="Made many changes."),
            patch("stop_hook.speak") as mock_speak,
        ):
            import stop_hook
            stop_hook.main()

        mock_speak.assert_called_once()
        # The summary text should be passed through
        assert mock_speak.call_args[0][1] == "Made many changes."

    def test_summarize_fallback_outputs_system_message(self) -> None:
        config = VoiceConfig(enabled=True, voice="af_heart", speed=1.0, max_sentences=2)
        long_text = "I made a lot of changes. " * 20
        input_data = {"session_id": "test-session-sm"}

        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()

        with (
            patch("hook_framework.sys.stdin", stdin),
            patch("hook_framework.sys.stdout", stdout),
            patch("hook_framework.get_voice_config", return_value=config),
            patch("stop_hook.find_session_file", return_value="/fake/session.jsonl"),
            patch("stop_hook.get_last_assistant_message", return_value=long_text),
            patch("extraction.extract_voice_marker", return_value=None),
            patch("extraction.is_short_response_sentences", return_value=False),
            patch("extraction.get_recent_conversation", return_value=[("user", "go"), ("assistant", long_text)]),
            patch("extraction.summarize_with_claude", return_value="Made many changes."),
            patch("extraction.trim_to_sentences", return_value="Made many changes."),
            patch("stop_hook.speak"),
        ):
            import stop_hook
            stop_hook.main()

        output = json.loads(stdout.getvalue().strip())
        # Headless path outputs a systemMessage with the summary
        assert "systemMessage" in output
        assert "Made many changes." in output["systemMessage"]


class TestStopHookStrategy4Truncation:
    """Strategy 4: last resort — truncate last message when summarization fails."""

    def test_truncation_fallback_calls_speak(self) -> None:
        config = VoiceConfig(enabled=True, voice="af_heart", speed=1.0, max_sentences=2)
        long_text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        input_data = {"session_id": "test-session-trunc"}

        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()

        with (
            patch("hook_framework.sys.stdin", stdin),
            patch("hook_framework.sys.stdout", stdout),
            patch("hook_framework.get_voice_config", return_value=config),
            patch("stop_hook.find_session_file", return_value="/fake/session.jsonl"),
            patch("stop_hook.get_last_assistant_message", return_value=long_text),
            patch("extraction.get_recent_conversation", return_value=[]),
            patch("extraction.summarize_with_claude", return_value=None),
            patch("stop_hook.speak") as mock_speak,
        ):
            import stop_hook
            stop_hook.main()

        mock_speak.assert_called_once()
        spoken_text = mock_speak.call_args[0][1]
        # Should be truncated to max_sentences (2) by trim_to_sentences
        assert "First sentence." in spoken_text
        assert "Second sentence." in spoken_text


class TestStopHookNoSessionFile:
    """No session file found — should approve without speaking."""

    def test_no_session_file_approves(self) -> None:
        config = VoiceConfig(enabled=True)
        input_data = {"session_id": "nonexistent"}

        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()

        with (
            patch("hook_framework.sys.stdin", stdin),
            patch("hook_framework.sys.stdout", stdout),
            patch("hook_framework.get_voice_config", return_value=config),
            patch("stop_hook.find_session_file", return_value=None),
        ):
            import stop_hook
            stop_hook.main()

        output = json.loads(stdout.getvalue().strip())
        assert output == {"decision": "approve"}


# ── speak (from speaker module) ─────────────────────────────────────


class TestSpeak:
    """Test speak command construction."""

    def test_basic_command(self) -> None:
        with patch("speaker.subprocess.Popen") as mock_popen:
            import speaker
            speaker.speak("sess-1", "Hello world", "af_heart")

        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "--session" in cmd
        assert "sess-1" in cmd
        assert "--voice" in cmd
        assert "af_heart" in cmd
        assert "Hello world" in cmd

    def test_speed_omitted_when_default(self) -> None:
        with patch("speaker.subprocess.Popen") as mock_popen:
            import speaker
            speaker.speak("sess-1", "text", "af_heart", speed=1.0)

        cmd = mock_popen.call_args[0][0]
        assert "--speed" not in cmd

    def test_speed_included_when_not_default(self) -> None:
        with patch("speaker.subprocess.Popen") as mock_popen:
            import speaker
            speaker.speak("sess-1", "text", "af_heart", speed=1.5)

        cmd = mock_popen.call_args[0][0]
        assert "--speed" in cmd
        speed_idx = cmd.index("--speed")
        assert cmd[speed_idx + 1] == "1.5"

    def test_oserror_swallowed(self) -> None:
        with patch("speaker.subprocess.Popen", side_effect=OSError):
            import speaker
            # Should not raise
            speaker.speak("sess-1", "text", "af_heart")
