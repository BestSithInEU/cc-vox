"""Client-side text sanitization for TTS input.

Strips file paths, UUIDs, SHA hashes, URLs, and other machine-readable
tokens that Claude sometimes includes in spoken summaries. Acts as a
safety net when the prompt-based instructions are not followed.
"""

from __future__ import annotations

import re

# ── Patterns (compiled once) ────────────────────────────────────────

# Unix paths with at least 2 segments: /foo/bar/baz.py
_UNIX_PATH = re.compile(r'/(?:[a-zA-Z0-9._\-]+/){2,}[a-zA-Z0-9._\-]+')

# Windows paths: C:\Users\foo\bar.py
_WIN_PATH = re.compile(r'[A-Z]:\\(?:[^\\\/:*?"<>|\r\n]+\\){1,}[^\\\/:*?"<>|\r\n]+')

# UUIDs: 8-4-4-4-12 hex
_UUID = re.compile(
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
)

# SHA hashes: 7-40 lowercase hex chars as a word boundary
_SHA = re.compile(r'\b[0-9a-f]{7,40}\b')

# Long hex values: 0x followed by 8+ hex digits
_HEX = re.compile(r'\b0x[0-9a-fA-F]{8,}\b')

# URLs
_URL = re.compile(r'https?://\S+')

# Backtick-wrapped code spans
_BACKTICK = re.compile(r'`([^`]{1,80})`')
_BACKTICK_LONG = re.compile(r'`[^`]{81,}`')

# Consecutive whitespace collapse
_MULTI_SPACE = re.compile(r'  +')


def _replace_backtick_short(m: re.Match) -> str:
    """Keep short backtick content, just strip the backticks."""
    return m.group(1)


def sanitize_text(text: str) -> str:
    """Remove or replace TTS-unfriendly patterns with natural language."""
    result = text

    # Order matters: URLs before paths (URLs contain path-like segments)
    result = _URL.sub("a link", result)
    result = _WIN_PATH.sub("a file", result)
    result = _UNIX_PATH.sub("a file", result)
    result = _UUID.sub("an identifier", result)
    result = _HEX.sub("a hex value", result)
    result = _SHA.sub("a hash", result)
    result = _BACKTICK_LONG.sub("some code", result)
    result = _BACKTICK.sub(_replace_backtick_short, result)
    result = _MULTI_SPACE.sub(" ", result)

    return result.strip()
