"""
Session file I/O — find and parse Claude Code JSONL session files.

Extracted from stop_hook.py to keep hook logic minimal.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path


def find_session_file(session_id: str) -> Path | None:
    """Find session file by ID in ~/.claude/projects/*/"""
    if not session_id:
        return None

    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    projects_dir = claude_home / "projects"

    if not projects_dir.exists():
        return None

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        exact_path = project_dir / f"{session_id}.jsonl"
        if exact_path.exists():
            return exact_path

        for jsonl_file in project_dir.glob(f"*{session_id}*.jsonl"):
            return jsonl_file

    return None


def count_sentences(text: str) -> int:
    """Count sentences in text (split on . ! ?)."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return len([s for s in sentences if s])


def trim_to_sentences(text: str, max_sentences: int) -> str:
    """Trim text to max_sentences, adding ellipsis if truncated."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in sentences if s]
    if len(sentences) <= max_sentences:
        return text.strip()
    return " ".join(sentences[:max_sentences])


def is_short_response_sentences(text: str, max_sentences: int) -> bool:
    """Check if response is short enough to speak directly (sentence-based)."""
    return count_sentences(text) <= max_sentences


def extract_voice_marker(text: str) -> str | None:
    """Extract voice summary from 📢 marker if present."""
    pattern = r'^[ \t]*📢[ \t]*(.+?)[ \t]*$'
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        summary = match.group(1).strip()
        summary = re.sub(r'^\[|\]$', '', summary)
        return summary if summary else None
    return None


def extract_message_text(data: dict) -> str | None:
    """Extract text content from a message data dict."""
    message = data.get("message", {})
    content = message.get("content", "")

    if isinstance(content, str):
        return content.strip()
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return "\n".join(text_parts).strip()
    return None


def _read_session_messages(session_file: Path) -> tuple[int, int, str | None]:
    """Read session file and extract message ordering info.

    Returns:
        Tuple of (last_user_line, last_assistant_text_line, last_assistant_text)
    """
    last_user_line = -1
    last_assistant_text_line = -1
    last_assistant_text = None

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    msg_type = data.get("type")

                    if msg_type == "user":
                        last_user_line = line_num

                    elif msg_type == "assistant":
                        text = extract_message_text(data)
                        if text:
                            last_assistant_text_line = line_num
                            last_assistant_text = text

                except json.JSONDecodeError:
                    continue
    except OSError:
        pass

    return last_user_line, last_assistant_text_line, last_assistant_text


def get_last_assistant_message(
    session_file: Path,
    max_retries: int = 10,
    retry_delay: float = 0.5,
) -> str | None:
    """Get the last assistant message text, with retry for race conditions.

    The stop hook can fire before the assistant message is written to the session
    file. This checks if the last assistant message with text comes AFTER the
    last user message (by line order). If not, it retries.
    """
    for attempt in range(max_retries):
        last_user_line, last_asst_line, last_asst_text = _read_session_messages(
            session_file
        )

        if last_asst_text and last_asst_line > last_user_line >= 0:
            return last_asst_text

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    return None


def get_recent_conversation(
    session_file: Path,
    num_turns: int = 5,
    max_assistant_words: int = 500,
) -> list[tuple[str, str]]:
    """Extract recent conversation turns from session file.

    Returns list of (role, text) tuples, most recent last.
    """
    messages: list[tuple[str, str]] = []

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    msg_type = data.get("type")

                    if msg_type not in ("user", "assistant"):
                        continue

                    text = extract_message_text(data)
                    if not text:
                        continue

                    # Skip tool results
                    if msg_type == "user":
                        content = data.get("message", {}).get("content", [])
                        if isinstance(content, list) and content:
                            if isinstance(content[0], dict):
                                if content[0].get("type") == "tool_result":
                                    continue

                    if msg_type == "assistant":
                        words = text.split()
                        if len(words) > max_assistant_words:
                            text = " ".join(words[:max_assistant_words]) + "..."

                    messages.append((msg_type, text))

                except json.JSONDecodeError:
                    continue

    except OSError:
        pass

    return messages[-(num_turns * 2):]
