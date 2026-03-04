"""Tests for summarize — headless Claude summarization fallback."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from summarize import summarize_with_claude


# ── Empty / no-assistant cases ────────────────────────────────────────


class TestSummarizeEarlyReturns:
    def test_empty_conversation_returns_none(self) -> None:
        result = summarize_with_claude([])
        assert result is None

    def test_no_assistant_message_returns_none(self) -> None:
        conversation = [("user", "Hello")]
        result = summarize_with_claude(conversation)
        assert result is None

    @patch("summarize.subprocess.run")
    def test_empty_list_no_subprocess_call(self, mock_run: MagicMock) -> None:
        summarize_with_claude([])
        mock_run.assert_not_called()

    @patch("summarize.subprocess.run")
    def test_no_assistant_no_subprocess_call(self, mock_run: MagicMock) -> None:
        summarize_with_claude([("user", "Hi")])
        mock_run.assert_not_called()


# ── Successful responses ──────────────────────────────────────────────


class TestSummarizeSuccess:
    @patch("summarize.subprocess.run")
    def test_dict_response(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "Fixed the bug."}),
        )
        result = summarize_with_claude([("user", "fix it"), ("assistant", "I fixed the bug in main.py")])
        assert result == "Fixed the bug."

    @patch("summarize.subprocess.run")
    def test_list_response(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"type": "text", "text": "Done."}]),
        )
        result = summarize_with_claude([("user", "do it"), ("assistant", "I did it.")])
        assert result == "Done."

    @patch("summarize.subprocess.run")
    def test_list_response_multiple_blocks(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"type": "text", "text": "Part one."},
                {"type": "text", "text": "Part two."},
            ]),
        )
        result = summarize_with_claude([("user", "go"), ("assistant", "went")])
        assert result == "Part one. Part two."

    @patch("summarize.subprocess.run")
    def test_empty_result_returns_none(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": ""}),
        )
        result = summarize_with_claude([("user", "x"), ("assistant", "y")])
        assert result is None


# ── Error handling ────────────────────────────────────────────────────


class TestSummarizeErrors:
    @patch("summarize.subprocess.run")
    def test_timeout_returns_none(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        result = summarize_with_claude([("user", "hi"), ("assistant", "hello")])
        assert result is None

    @patch("summarize.subprocess.run")
    def test_nonzero_returncode_returns_none(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = summarize_with_claude([("user", "hi"), ("assistant", "hello")])
        assert result is None

    @patch("summarize.subprocess.run")
    def test_invalid_json_returns_none(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="not json{{{")
        result = summarize_with_claude([("user", "hi"), ("assistant", "hello")])
        assert result is None

    @patch("summarize.subprocess.run")
    def test_os_error_returns_none(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("claude not found")
        result = summarize_with_claude([("user", "hi"), ("assistant", "hello")])
        assert result is None


# ── Prompt construction ───────────────────────────────────────────────


class TestSummarizePromptConstruction:
    @patch("summarize.subprocess.run")
    def test_prompt_contains_assistant_message(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        assistant_text = "I refactored the database layer."
        summarize_with_claude([("user", "refactor db"), ("assistant", assistant_text)])

        args, _kwargs = mock_run.call_args
        prompt_arg = args[0][-1]  # last positional arg is the prompt string
        assert assistant_text in prompt_arg

    @patch("summarize.subprocess.run")
    def test_prompt_contains_custom_prompt(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        custom = "Respond in pirate speak"
        summarize_with_claude(
            [("user", "ahoy"), ("assistant", "matey")],
            custom_prompt=custom,
        )

        args, _kwargs = mock_run.call_args
        prompt_arg = args[0][-1]
        assert custom in prompt_arg

    @patch("summarize.subprocess.run")
    def test_prompt_without_custom_prompt(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        summarize_with_claude([("user", "go"), ("assistant", "done")])

        args, _kwargs = mock_run.call_args
        prompt_arg = args[0][-1]
        assert "Additional instruction:" not in prompt_arg

    @patch("summarize.subprocess.run")
    def test_prompt_respects_max_sentences(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        summarize_with_claude(
            [("user", "hi"), ("assistant", "hello")],
            max_sentences=5,
        )

        args, _kwargs = mock_run.call_args
        prompt_arg = args[0][-1]
        assert "5 sentences" in prompt_arg
