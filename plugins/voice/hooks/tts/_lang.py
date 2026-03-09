"""Language detection and backend routing.

Uses Unicode character range heuristics (stdlib only, no ML).
"""

from __future__ import annotations


# ── Language detection ──────────────────────────────────────────────

def _char_ratio(text: str, test: callable) -> float:
    """Fraction of non-whitespace chars matching test."""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    return sum(1 for c in chars if test(c)) / len(chars)


def _is_cjk(c: str) -> bool:
    cp = ord(c)
    return (
        0x4E00 <= cp <= 0x9FFF      # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF   # CJK Extension A
        or 0x20000 <= cp <= 0x2A6DF # CJK Extension B
        or 0xF900 <= cp <= 0xFAFF   # CJK Compatibility Ideographs
    )


def _is_hiragana_katakana(c: str) -> bool:
    cp = ord(c)
    return (
        0x3040 <= cp <= 0x309F  # Hiragana
        or 0x30A0 <= cp <= 0x30FF  # Katakana
    )


def _is_hangul(c: str) -> bool:
    cp = ord(c)
    return (
        0xAC00 <= cp <= 0xD7AF  # Hangul Syllables
        or 0x1100 <= cp <= 0x11FF  # Hangul Jamo
    )


def _is_cyrillic(c: str) -> bool:
    cp = ord(c)
    return 0x0400 <= cp <= 0x04FF


def detect_language(text: str) -> str:
    """Detect language from text using Unicode character range heuristics.

    Returns ISO 639-1 code: en, zh, ja, ko, ru.
    """
    # Threshold: if >15% of chars are in a script, classify as that language
    threshold = 0.15

    jp_ratio = _char_ratio(text, _is_hiragana_katakana)
    if jp_ratio > threshold:
        return "ja"

    ko_ratio = _char_ratio(text, _is_hangul)
    if ko_ratio > threshold:
        return "ko"

    cjk_ratio = _char_ratio(text, _is_cjk)
    if cjk_ratio > threshold:
        return "zh"

    cy_ratio = _char_ratio(text, _is_cyrillic)
    if cy_ratio > threshold:
        return "ru"

    return "en"


# ── Backend routing ─────────────────────────────────────────────────

# Maps language to preferred backends (in priority order).
# Backends not listed here are assumed to support English only.
_LANGUAGE_BACKENDS: dict[str, list[str]] = {
    "zh": ["qwen3-tts"],
    "ja": ["qwen3-tts"],
    "ko": ["qwen3-tts"],
    "ru": ["qwen3-tts"],
    "en": [],  # empty = all backends (default behavior)
}


def backends_for_language(lang: str) -> list[str]:
    """Return preferred backend names for the given language.

    Returns an empty list for English (meaning: use all backends).
    """
    return _LANGUAGE_BACKENDS.get(lang, [])
