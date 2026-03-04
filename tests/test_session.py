"""Tests for session — sentence counting, markers, JSONL parsing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from session import (
    _read_session_messages,
    count_sentences,
    extract_message_text,
    extract_voice_marker,
    find_session_file,
    get_last_assistant_message,
    get_recent_conversation,
    is_short_response_sentences,
    trim_to_sentences,
)


# ── count_sentences ──────────────────────────────────────────────────


class TestCountSentences:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("Hello.", 1),
            ("Hello. World.", 2),
            ("Hello! World? Done.", 3),
            ("", 0),
            ("No punctuation", 1),
        ],
    )
    def test_counts(self, text: str, expected: int) -> None:
        assert count_sentences(text) == expected

    def test_whitespace_only(self) -> None:
        assert count_sentences("   ") == 0

    def test_multiple_spaces_between_sentences(self) -> None:
        assert count_sentences("First.   Second.") == 2


# ── trim_to_sentences ────────────────────────────────────────────────


class TestTrimToSentences:
    def test_trim_to_n(self) -> None:
        text = "One. Two. Three."
        assert trim_to_sentences(text, 2) == "One. Two."

    def test_already_fits(self) -> None:
        text = "One. Two."
        assert trim_to_sentences(text, 5) == "One. Two."

    def test_single_sentence(self) -> None:
        text = "Hello world."
        assert trim_to_sentences(text, 1) == "Hello world."

    def test_trim_to_one(self) -> None:
        text = "First. Second. Third."
        assert trim_to_sentences(text, 1) == "First."


# ── is_short_response_sentences ──────────────────────────────────────


class TestIsShortResponseSentences:
    def test_at_limit(self) -> None:
        assert is_short_response_sentences("One. Two.", 2) is True

    def test_above_limit(self) -> None:
        assert is_short_response_sentences("One. Two. Three.", 2) is False

    def test_below_limit(self) -> None:
        assert is_short_response_sentences("One.", 2) is True

    def test_empty_is_short(self) -> None:
        assert is_short_response_sentences("", 2) is True


# ── extract_voice_marker ─────────────────────────────────────────────


class TestExtractVoiceMarker:
    def test_bracketed(self) -> None:
        text = "Done!\n\U0001f4e2 [Fixed the bug]"
        assert extract_voice_marker(text) == "Fixed the bug"

    def test_unbracketed(self) -> None:
        text = "Done!\n\U0001f4e2 I fixed it."
        assert extract_voice_marker(text) == "I fixed it."

    def test_no_marker(self) -> None:
        assert extract_voice_marker("Just text") is None

    def test_leading_whitespace(self) -> None:
        text = "text\n  \U0001f4e2 [summary]"
        assert extract_voice_marker(text) == "summary"

    def test_marker_mid_text(self) -> None:
        text = "Line one.\n\U0001f4e2 [middle marker]\nLine three."
        assert extract_voice_marker(text) == "middle marker"

    def test_empty_brackets(self) -> None:
        text = "text\n\U0001f4e2 []"
        assert extract_voice_marker(text) is None


# ── extract_message_text ─────────────────────────────────────────────


class TestExtractMessageText:
    def test_string_content(self) -> None:
        data = {"message": {"content": "Hello world"}}
        assert extract_message_text(data) == "Hello world"

    def test_list_content_text_blocks(self) -> None:
        data = {
            "message": {
                "content": [
                    {"type": "text", "text": "First part."},
                    {"type": "tool_use", "name": "grep"},
                    {"type": "text", "text": "Second part."},
                ]
            }
        }
        assert extract_message_text(data) == "First part.\nSecond part."

    def test_missing_message_key(self) -> None:
        assert extract_message_text({}) is None

    def test_missing_content_key(self) -> None:
        data = {"message": {}}
        assert extract_message_text(data) is None

    def test_content_is_none(self) -> None:
        data = {"message": {"content": None}}
        assert extract_message_text(data) is None

    def test_empty_string_content_returns_none(self) -> None:
        data = {"message": {"content": ""}}
        assert extract_message_text(data) is None

    def test_whitespace_only_content_returns_none(self) -> None:
        data = {"message": {"content": "   "}}
        assert extract_message_text(data) is None

    def test_empty_list_content_returns_none(self) -> None:
        data = {"message": {"content": []}}
        assert extract_message_text(data) is None

    def test_string_content_whitespace_stripped(self) -> None:
        data = {"message": {"content": "  padded  "}}
        assert extract_message_text(data) == "padded"


# ── _read_session_messages ───────────────────────────────────────────


class TestReadSessionMessages:
    def test_basic_user_assistant(self, mock_session_file) -> None:
        path = mock_session_file(
            [
                {"type": "user", "message": {"content": "Hello"}},
                {"type": "assistant", "message": {"content": "Hi there"}},
            ]
        )
        last_user, last_asst, last_text = _read_session_messages(path)
        assert last_user == 0
        assert last_asst == 1
        assert last_text == "Hi there"

    def test_multiple_turns(self, mock_session_file) -> None:
        path = mock_session_file(
            [
                {"type": "user", "message": {"content": "First"}},
                {"type": "assistant", "message": {"content": "Reply 1"}},
                {"type": "user", "message": {"content": "Second"}},
                {"type": "assistant", "message": {"content": "Reply 2"}},
            ]
        )
        last_user, last_asst, last_text = _read_session_messages(path)
        assert last_user == 2
        assert last_asst == 3
        assert last_text == "Reply 2"

    def test_empty_file(self, mock_session_file) -> None:
        path = mock_session_file([])
        last_user, last_asst, last_text = _read_session_messages(path)
        assert last_user == -1
        assert last_asst == -1
        assert last_text is None

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / "does_not_exist.jsonl"
        last_user, last_asst, last_text = _read_session_messages(path)
        assert last_user == -1
        assert last_asst == -1
        assert last_text is None


# ── get_recent_conversation ──────────────────────────────────────────


class TestGetRecentConversation:
    def test_truncates_long_assistant(self, mock_session_file) -> None:
        long_text = " ".join(["word"] * 600)
        path = mock_session_file(
            [
                {"type": "user", "message": {"content": "Tell me a story"}},
                {"type": "assistant", "message": {"content": long_text}},
            ]
        )
        turns = get_recent_conversation(path, max_assistant_words=500)
        assert len(turns) == 2
        role, text = turns[1]
        assert role == "assistant"
        assert text.endswith("...")
        assert len(text.split()) <= 501  # 500 words + "..."

    def test_skips_tool_result_messages(self, mock_session_file) -> None:
        path = mock_session_file(
            [
                {"type": "user", "message": {"content": "Do something"}},
                {"type": "assistant", "message": {"content": "Using tool..."}},
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {"type": "tool_result", "content": "output"}
                        ]
                    },
                },
                {"type": "assistant", "message": {"content": "Done!"}},
            ]
        )
        turns = get_recent_conversation(path)
        # The tool_result user message should be skipped
        roles = [role for role, _ in turns]
        # Should have: user, assistant, assistant (tool_result skipped)
        assert roles == ["user", "assistant", "assistant"]

    def test_returns_last_n_turns(self, mock_session_file) -> None:
        messages = []
        for i in range(10):
            messages.append(
                {"type": "user", "message": {"content": f"User msg {i}"}}
            )
            messages.append(
                {"type": "assistant", "message": {"content": f"Asst msg {i}"}}
            )
        path = mock_session_file(messages)
        turns = get_recent_conversation(path, num_turns=2)
        # num_turns=2 means last 4 messages (2 user + 2 assistant)
        assert len(turns) == 4
        assert turns[-1] == ("assistant", "Asst msg 9")

    def test_empty_session(self, mock_session_file) -> None:
        path = mock_session_file([])
        assert get_recent_conversation(path) == []


# ── get_last_assistant_message ──────────────────────────────────────


class TestGetLastAssistantMessage:
    def test_returns_last_assistant_text(self, mock_session_file) -> None:
        path = mock_session_file([
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": "Hi there"}},
        ])
        result = get_last_assistant_message(path, max_retries=1)
        assert result == "Hi there"

    def test_returns_none_when_no_assistant_after_user(
        self, mock_session_file,
    ) -> None:
        path = mock_session_file([
            {"type": "assistant", "message": {"content": "Old message"}},
            {"type": "user", "message": {"content": "New question"}},
        ])
        # Assistant message is before user, so ordering check fails
        result = get_last_assistant_message(path, max_retries=1, retry_delay=0)
        assert result is None

    def test_returns_none_for_empty_file(self, mock_session_file) -> None:
        path = mock_session_file([])
        result = get_last_assistant_message(path, max_retries=1, retry_delay=0)
        assert result is None

    def test_retry_succeeds_on_later_attempt(
        self, mock_session_file, tmp_path: Path,
    ) -> None:
        """Simulate race condition: file initially has no assistant reply,
        then gets one on the second read."""
        path = tmp_path / "session.jsonl"

        # Initial state: only user message
        initial = [{"type": "user", "message": {"content": "Hello"}}]
        path.write_text("\n".join(json.dumps(m) for m in initial) + "\n")

        call_count = 0
        original_read = _read_session_messages

        def patched_read(session_file):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_read(session_file)
            # On second call, append assistant message
            with open(session_file, "a") as f:
                f.write(json.dumps({
                    "type": "assistant",
                    "message": {"content": "Reply!"},
                }) + "\n")
            return original_read(session_file)

        with patch("session._read_session_messages", side_effect=patched_read):
            result = get_last_assistant_message(path, max_retries=3, retry_delay=0)

        assert result == "Reply!"


# ── find_session_file ───────────────────────────────────────────────


class TestFindSessionFile:
    def test_returns_none_for_empty_session_id(self) -> None:
        assert find_session_file("") is None

    def test_finds_exact_match(self, tmp_path: Path, monkeypatch) -> None:
        claude_home = tmp_path / ".claude"
        projects = claude_home / "projects" / "myproject"
        projects.mkdir(parents=True)
        session = projects / "abc123.jsonl"
        session.write_text("{}\n")

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_home))
        assert find_session_file("abc123") == session

    def test_finds_partial_match(self, tmp_path: Path, monkeypatch) -> None:
        claude_home = tmp_path / ".claude"
        projects = claude_home / "projects" / "myproject"
        projects.mkdir(parents=True)
        session = projects / "prefix-abc123-suffix.jsonl"
        session.write_text("{}\n")

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_home))
        assert find_session_file("abc123") == session

    def test_returns_none_when_not_found(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        claude_home = tmp_path / ".claude"
        projects = claude_home / "projects" / "myproject"
        projects.mkdir(parents=True)

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_home))
        assert find_session_file("nonexistent") is None

    def test_returns_none_when_no_projects_dir(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        claude_home = tmp_path / ".claude"
        claude_home.mkdir()
        # No projects/ directory

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_home))
        assert find_session_file("abc123") is None
