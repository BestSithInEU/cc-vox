#!/usr/bin/env python3
"""
Shared voice plugin utilities and constants.

Single source of truth for config parsing (TOML), VoiceConfig dataclass,
and voice reminder generation.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "cc-vox.toml"
OLD_CONFIG_PATH = Path.home() / ".claude" / "voice.local.md"

def _default_config_toml() -> str:
    """Generate the default config TOML with voice catalog from single source."""
    header = """\
[core]
enabled = true
voice = "af_heart"       # see voices below
backend = "auto"         # auto | kokoro | fish-speech | pocket-tts | chatterbox | qwen3-tts

[tuning]
speed = 1.0              # 0.5-2.0 (kokoro only)
max_words = 25           # max spoken summary length
fallback = true          # try other backends when forced one is down

[style]
prompt = ""
"""
    return header + "\n" + "\n".join(_voice_comment_lines()) + "\n"

try:
    from tts import available_backend_names
    from tts.voices import voice_comments
    VALID_BACKENDS = available_backend_names()
except ImportError:
    VALID_BACKENDS = ("auto", "kokoro", "fish-speech", "pocket-tts", "chatterbox", "qwen3-tts")
    voice_comments = None  # type: ignore[assignment]


def _voice_comment_lines() -> list[str]:
    """Generate voice catalog comment lines from VOICE_CATALOG or fallback."""
    if voice_comments is not None:
        return voice_comments()
    return [
        "# ── Available Voices ──────────────────────────────",
        "# af_heart (default)  F  American   alias: alba",
        "# af_bella            F  American   alias: azure",
        "# af_nicole           F  American   alias: fantine",
        "# af_sarah            F  American   alias: cosette",
        "# af_sky              F  American   alias: eponine",
        "# am_adam             M  American   alias: marius",
        "# am_michael          M  American   alias: jean",
        "# bf_emma             F  British    alias: azelma",
        "# bm_george           M  British",
    ]


@dataclass
class VoiceConfig:
    enabled: bool = True
    voice: str = "af_heart"
    backend: str = "auto"
    speed: float = 1.0
    max_words: int = 25
    fallback: bool = True
    prompt: str = ""
    just_disabled: bool = False


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _migrate_old_config() -> dict[str, object] | None:
    """Read values from old voice.local.md if it exists. Returns dict or None."""
    if not OLD_CONFIG_PATH.exists():
        return None

    content = OLD_CONFIG_PATH.read_text()
    values: dict[str, object] = {}

    lines = content.split("\n")
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter:
            if line.startswith("enabled:"):
                val = line.split(":", 1)[1].strip()
                values["enabled"] = val.lower() != "false"
            elif line.startswith("voice:"):
                values["voice"] = line.split(":", 1)[1].strip()
            elif line.startswith("prompt:"):
                val = line.split(":", 1)[1].strip()
                if (val.startswith('"') and val.endswith('"')) or \
                   (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                values["prompt"] = val
            elif line.startswith("just_disabled:"):
                val = line.split(":", 1)[1].strip()
                values["just_disabled"] = val.lower() == "true"
            elif line.startswith("backend:"):
                val = line.split(":", 1)[1].strip()
                if val in VALID_BACKENDS:
                    values["backend"] = val

    return values


def _write_toml(config: VoiceConfig) -> None:
    """Write config to cc-vox.toml, preserving the commented voice catalog."""
    lines = [
        "[core]",
        f'enabled = {"true" if config.enabled else "false"}',
        f'voice = "{config.voice}"       # see voices below',
        f'backend = "{config.backend}"'
        + ("         # auto | kokoro | fish-speech | pocket-tts | chatterbox | qwen3-tts"
           if config.backend == "auto" else ""),
        "",
        "[tuning]",
        f"speed = {config.speed}"
        + ("              # 0.5-2.0 (kokoro only)"
           if config.speed == 1.0 else ""),
        f"max_words = {config.max_words}"
        + ("           # max spoken summary length"
           if config.max_words == 25 else ""),
        f'fallback = {"true" if config.fallback else "false"}'
        + ("          # try other backends when forced one is down"
           if config.fallback else ""),
        "",
        "[style]",
        'prompt = "{}"'.format(config.prompt.replace("\\", "\\\\").replace('"', '\\"')),
    ]

    if config.just_disabled:
        lines += ["", "[internal]", "just_disabled = true"]

    lines += [""] + _voice_comment_lines() + [""]

    DEFAULT_CONFIG_PATH.write_text("\n".join(lines))


def get_voice_config() -> VoiceConfig:
    """Read voice config from ~/.claude/cc-vox.toml.

    - Creates default config if missing.
    - Migrates from old voice.local.md if it exists.
    - Validates and clamps values.
    """
    config = VoiceConfig()

    # Migration: if old config exists but new doesn't, migrate
    if not DEFAULT_CONFIG_PATH.exists():
        old_values = _migrate_old_config()
        if old_values:
            for key, val in old_values.items():
                if hasattr(config, key):
                    setattr(config, key, val)
            _write_toml(config)
            OLD_CONFIG_PATH.unlink(missing_ok=True)
            return config
        else:
            # First run: create default
            DEFAULT_CONFIG_PATH.write_text(_default_config_toml())
            return config

    # Parse TOML
    try:
        raw = DEFAULT_CONFIG_PATH.read_bytes()
        data = tomllib.loads(raw.decode())
    except (OSError, tomllib.TOMLDecodeError):
        return config

    core = data.get("core", {})
    tuning = data.get("tuning", {})
    style = data.get("style", {})
    internal = data.get("internal", {})

    if "enabled" in core:
        config.enabled = bool(core["enabled"])
    if "voice" in core:
        config.voice = str(core["voice"])
    if "backend" in core:
        val = str(core["backend"])
        if val in VALID_BACKENDS:
            config.backend = val

    if "speed" in tuning:
        config.speed = _clamp(float(tuning["speed"]), 0.5, 2.0)
    if "max_words" in tuning:
        config.max_words = int(_clamp(float(tuning["max_words"]), 5, 100))
    if "fallback" in tuning:
        config.fallback = bool(tuning["fallback"])

    if "prompt" in style:
        config.prompt = str(style["prompt"])

    if "just_disabled" in internal:
        config.just_disabled = bool(internal["just_disabled"])

    return config


def update_voice_config(**kwargs: object) -> VoiceConfig:
    """Read current config, apply updates, write back. Returns updated config."""
    config = get_voice_config()
    for key, val in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, val)
    # Validate after update
    config.speed = _clamp(config.speed, 0.5, 2.0)
    config.max_words = int(_clamp(float(config.max_words), 5, 100))
    if config.backend not in VALID_BACKENDS:
        config.backend = "auto"
    _write_toml(config)
    return config


def clear_just_disabled_flag() -> None:
    """Remove the just_disabled flag from config."""
    if not DEFAULT_CONFIG_PATH.exists():
        return

    try:
        raw = DEFAULT_CONFIG_PATH.read_bytes()
        data = tomllib.loads(raw.decode())
    except (OSError, tomllib.TOMLDecodeError):
        return

    if "internal" in data and "just_disabled" in data["internal"]:
        # Re-read config, clear flag, rewrite
        config = get_voice_config()
        config.just_disabled = False
        _write_toml(config)


def build_full_reminder(max_words: int = 25, custom_prompt: str = "") -> str:
    """Build the full voice reminder for UserPromptSubmit hook."""
    reminder = (
        "Voice feedback is enabled. At the end of your response:\n"
        f"- If ≤{max_words} words of natural speakable text, no summary needed\n"
        f"- If ≤{max_words} words but contains code/paths/technical output, "
        "ADD a 📢 summary\n"
        "- If longer, end with: 📢 [brief spoken summary]\n\n"
        "VOICE SUMMARY STYLE:\n"
        "- Match the user's tone - if they're casual or use colorful language, "
        "mirror that\n"
        "- Keep it brief and conversational, like you're speaking to them\n"
        "- NEVER include file paths, UUIDs, hashes, or technical identifiers - "
        "use natural language instead (e.g., 'the config file' not "
        "'/Users/foo/bar/config.json')"
    )

    if custom_prompt:
        reminder += (
            f"\n\nCUSTOM VOICE INSTRUCTION (overrides above instructions if they "
            f"contradict): {custom_prompt}"
        )

    return reminder


def build_short_reminder(max_words: int = 25) -> str:
    """Build a brief voice reminder for PostToolUse hook."""
    return (
        f"[Voice feedback: when done, end with 📢 summary (max {max_words} words) "
        f"if response is >{max_words} words or contains code/paths]"
    )
