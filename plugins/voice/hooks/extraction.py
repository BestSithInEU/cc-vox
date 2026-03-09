"""Text extraction strategies for the stop hook."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sanitize import sanitize_text
from session import (
    extract_voice_marker,
    get_recent_conversation,
    is_short_response_sentences,
    trim_to_sentences,
)
from summarize import summarize_with_claude
from tts._debug import log
from voice_common import VoiceConfig


@dataclass
class ExtractionResult:
    """Result of a text extraction attempt."""

    text: str
    used_headless: bool = False


def _try_marker(msg: str, config: VoiceConfig) -> ExtractionResult | None:
    """Strategy 1: Extract text from voice marker (instant)."""
    marker_text = extract_voice_marker(msg)
    if marker_text:
        trimmed = trim_to_sentences(marker_text, config.max_sentences + 1)
        log(f"extraction: marker found, {len(trimmed)} chars")
        return ExtractionResult(text=trimmed)
    return None


def _try_short(msg: str, config: VoiceConfig) -> ExtractionResult | None:
    """Strategy 2: Use response directly if short enough."""
    if is_short_response_sentences(msg, config.max_sentences):
        log(f"extraction: short response, speaking directly")
        return ExtractionResult(text=msg)
    return None


def _try_headless(
    msg: str, config: VoiceConfig, session_file: Path,
) -> ExtractionResult | None:
    """Strategy 3: Summarize via headless Claude (slower)."""
    conversation = get_recent_conversation(session_file)
    if conversation:
        summary = summarize_with_claude(
            conversation, config.prompt, config.max_sentences,
        )
        if summary:
            trimmed = trim_to_sentences(summary, config.max_sentences + 1)
            log(f"extraction: headless summary, {len(trimmed)} chars")
            return ExtractionResult(text=trimmed, used_headless=True)
    log("extraction: headless summarization failed or no conversation")
    return None


def _try_truncate(msg: str, config: VoiceConfig) -> ExtractionResult | None:
    """Strategy 4: Last resort — truncate to sentence limit."""
    trimmed = trim_to_sentences(msg, config.max_sentences)
    if trimmed:
        log(f"extraction: truncated to {config.max_sentences} sentences")
        return ExtractionResult(text=trimmed)
    return None


_STRATEGIES = [_try_marker, _try_short]
_STRATEGIES_WITH_SESSION = [_try_headless]
_STRATEGIES_FALLBACK = [_try_truncate]


def extract_speakable_text(
    assistant_msg: str,
    config: VoiceConfig,
    session_file: Path,
) -> ExtractionResult | None:
    """Run extraction strategies in order, return first success."""
    result: ExtractionResult | None = None

    for strategy in _STRATEGIES:
        result = strategy(assistant_msg, config)
        if result is not None:
            break

    if result is None:
        for strategy in _STRATEGIES_WITH_SESSION:
            result = strategy(assistant_msg, config, session_file)
            if result is not None:
                break

    if result is None:
        for strategy in _STRATEGIES_FALLBACK:
            result = strategy(assistant_msg, config)
            if result is not None:
                break

    if result is None:
        return None

    # Sanitize TTS-unfriendly tokens (paths, UUIDs, hashes, URLs)
    result.text = sanitize_text(result.text)
    return result
