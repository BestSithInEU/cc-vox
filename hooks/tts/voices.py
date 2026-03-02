"""
Single source of truth for all voice data.

Every voice mapping, alias resolution, and catalog query lives here.
"""

from __future__ import annotations

VOICE_CATALOG: dict[str, dict[str, str]] = {
    "af_heart":   {"alias": "alba",    "gender": "F", "accent": "American"},
    "af_bella":   {"alias": "azure",   "gender": "F", "accent": "American"},
    "af_nicole":  {"alias": "fantine", "gender": "F", "accent": "American"},
    "af_sarah":   {"alias": "cosette", "gender": "F", "accent": "American"},
    "af_sky":     {"alias": "eponine", "gender": "F", "accent": "American"},
    "am_adam":    {"alias": "marius",  "gender": "M", "accent": "American"},
    "am_michael": {"alias": "jean",    "gender": "M", "accent": "American"},
    "bf_emma":    {"alias": "azelma",  "gender": "F", "accent": "British"},
    "bm_george":  {                    "gender": "M", "accent": "British"},
}

DEFAULT_VOICE = "af_heart"

# Computed lookup tables
ALIAS_TO_KOKORO: dict[str, str] = {
    v["alias"]: k for k, v in VOICE_CATALOG.items() if "alias" in v
}
KOKORO_TO_ALIAS: dict[str, str] = {v: k for k, v in ALIAS_TO_KOKORO.items()}


def to_kokoro(voice: str) -> str:
    """Normalize any voice identifier to its canonical Kokoro form."""
    if voice in ALIAS_TO_KOKORO:
        return ALIAS_TO_KOKORO[voice]
    if voice in VOICE_CATALOG:
        return voice
    return DEFAULT_VOICE


def to_alias(voice: str) -> str:
    """Convert a Kokoro voice name to its pocket-tts alias (passthrough if none)."""
    kokoro = to_kokoro(voice)
    return KOKORO_TO_ALIAS.get(kokoro, kokoro)


def voice_comments() -> list[str]:
    """Generate TOML comment lines for the voice catalog."""
    lines = ["# ── Available Voices ──────────────────────────────"]
    for kokoro_name, info in VOICE_CATALOG.items():
        default = " (default)" if kokoro_name == DEFAULT_VOICE else ""
        alias_part = f"   alias: {info['alias']}" if "alias" in info else ""
        lines.append(
            f"# {kokoro_name}{default:<10s} {info['gender']}  "
            f"{info['accent']}{alias_part}"
        )
    return lines
