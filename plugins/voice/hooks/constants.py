"""Voice plugin constants — single source of truth for magic values."""

from __future__ import annotations

import os

# Marker used to extract spoken summaries from Claude responses
VOICE_MARKER = "\U0001f4e2"  # 📢

# Config value bounds
SPEED_MIN, SPEED_MAX = 0.5, 2.0
VOLUME_MIN, VOLUME_MAX = 0.0, 2.0
SENTENCES_MIN, SENTENCES_MAX = 1, 10

# Truncation limits
MAX_SUMMARY_WORDS = 500
MAX_CONTEXT_CHARS = 3000
MAX_MESSAGE_CHARS = 2000


def sentence_label(n: int) -> str:
    """Return '1 sentence' or 'N sentences'."""
    return "1 sentence" if n == 1 else f"{n} sentences"


def env_port(var: str, default: int) -> int:
    """Read a port number from an environment variable."""
    return int(os.environ.get(var, str(default)))
