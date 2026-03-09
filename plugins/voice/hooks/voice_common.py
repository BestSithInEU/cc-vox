#!/usr/bin/env python3
"""
Shared voice plugin utilities and constants.

Single source of truth for config parsing (TOML), VoiceConfig dataclass,
and voice reminder generation.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from constants import (
    SENTENCES_MIN,
    SENTENCES_MAX,
    SPEED_MIN,
    SPEED_MAX,
    VOICE_MARKER,
    VOLUME_MIN,
    VOLUME_MAX,
    sentence_label,
)

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
volume = 1.0             # 0.0-2.0 playback volume
max_sentences = 2        # max sentences in spoken summary (1-10)
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
    volume: float = 1.0
    max_sentences: int = 2
    fallback: bool = True
    prompt: str = ""
    clone_audio: str = ""
    save_history: bool = False
    conversational: bool = False
    update_interval: int = 30
    debug: bool = False
    just_disabled: bool = False


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _validate_config(config: VoiceConfig) -> tuple[VoiceConfig, list[str]]:
    """Clamp and validate all config fields.

    Returns (config, warnings) where warnings lists any clamped fields.
    """
    warnings: list[str] = []

    clamped = _clamp(config.speed, SPEED_MIN, SPEED_MAX)
    if clamped != config.speed:
        warnings.append(
            f"speed clamped from {config.speed} to {clamped} "
            f"(range: {SPEED_MIN}\u2013{SPEED_MAX})"
        )
    config.speed = clamped

    clamped_vol = _clamp(config.volume, VOLUME_MIN, VOLUME_MAX)
    if clamped_vol != config.volume:
        warnings.append(
            f"volume clamped from {config.volume} to {clamped_vol} "
            f"(range: {VOLUME_MIN}\u2013{VOLUME_MAX})"
        )
    config.volume = clamped_vol

    clamped_sent = int(_clamp(float(config.max_sentences), SENTENCES_MIN, SENTENCES_MAX))
    if clamped_sent != config.max_sentences:
        warnings.append(
            f"max_sentences clamped from {config.max_sentences} to {clamped_sent} "
            f"(range: {SENTENCES_MIN}\u2013{SENTENCES_MAX})"
        )
    config.max_sentences = clamped_sent

    if config.backend not in VALID_BACKENDS:
        warnings.append(
            f"unknown backend {config.backend!r} reset to 'auto'"
        )
        config.backend = "auto"

    return config, warnings


def _migrate_old_config() -> dict[str, object] | None:
    """Read values from old voice.local.md if it exists. Returns dict or None."""
    if not OLD_CONFIG_PATH.exists():
        return None

    content = OLD_CONFIG_PATH.read_text(encoding="utf-8")
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


def _build_toml(config: VoiceConfig) -> str:
    """Build TOML string from config."""
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
        f"volume = {config.volume}"
        + ("             # 0.0-2.0 playback volume"
           if config.volume == 1.0 else ""),
        f"max_sentences = {config.max_sentences}"
        + ("        # max sentences in spoken summary (1-10)"
           if config.max_sentences == 2 else ""),
        f'fallback = {"true" if config.fallback else "false"}'
        + ("          # try other backends when forced one is down"
           if config.fallback else ""),
        "",
        "[style]",
        'prompt = "{}"'.format(config.prompt.replace("\\", "\\\\").replace('"', '\\"')),
    ]

    if config.clone_audio:
        lines.append(
            'clone_audio = "{}"'.format(
                config.clone_audio.replace("\\", "\\\\").replace('"', '\\"')
            )
        )

    # Features section (non-default values only)
    feature_lines: list[str] = []
    if config.save_history:
        feature_lines.append("save_history = true")
    if config.conversational:
        feature_lines.append("conversational = true")
    if config.update_interval != 30:
        feature_lines.append(f"update_interval = {config.update_interval}")
    if feature_lines:
        lines += ["", "[features]", *feature_lines]

    internal_lines: list[str] = []
    if config.just_disabled:
        internal_lines.append("just_disabled = true")
    if config.debug:
        internal_lines.append("debug = true")
    if internal_lines:
        lines += ["", "[internal]", *internal_lines]

    lines += [""] + _voice_comment_lines() + [""]

    return "\n".join(lines)


def _write_toml(config: VoiceConfig) -> None:
    """Write config to cc-vox.toml atomically if content changed."""
    content = _build_toml(config)
    try:
        if DEFAULT_CONFIG_PATH.read_text(encoding="utf-8") == content:
            return
    except OSError:
        pass
    tmp = DEFAULT_CONFIG_PATH.with_suffix(".toml.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(DEFAULT_CONFIG_PATH))


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
            DEFAULT_CONFIG_PATH.write_text(_default_config_toml(), encoding="utf-8")
            return config

    # Parse TOML
    try:
        raw = DEFAULT_CONFIG_PATH.read_bytes()
        data = tomllib.loads(raw.decode())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        from tts._debug import log
        log(f"config parse: {type(exc).__name__}: {exc}")
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
        config.backend = str(core["backend"])

    if "speed" in tuning:
        config.speed = float(tuning["speed"])
    if "volume" in tuning:
        config.volume = float(tuning["volume"])
    if "max_sentences" in tuning:
        config.max_sentences = int(tuning["max_sentences"])
    if "fallback" in tuning:
        config.fallback = bool(tuning["fallback"])

    if "prompt" in style:
        config.prompt = str(style["prompt"])
    if "clone_audio" in style:
        config.clone_audio = str(style["clone_audio"])

    features = data.get("features", {})
    if "save_history" in features:
        config.save_history = bool(features["save_history"])
    if "conversational" in features:
        config.conversational = bool(features["conversational"])
    if "update_interval" in features:
        config.update_interval = int(features["update_interval"])

    if "just_disabled" in internal:
        config.just_disabled = bool(internal["just_disabled"])
    if "debug" in internal:
        config.debug = bool(internal["debug"])

    _validate_config(config)  # discard warnings for file reads

    # Always rewrite to keep config in sync with current schema
    _write_toml(config)

    return config


def update_voice_config(**kwargs: object) -> tuple[VoiceConfig, list[str]]:
    """Read current config, apply updates, write back.

    Returns (config, warnings) where warnings lists any clamped fields.
    """
    config = get_voice_config()
    old_backend = config.backend
    for key, val in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, val)
    config, warnings = _validate_config(config)
    _write_toml(config)

    # Invalidate backend cache when backend preference changes
    if config.backend != old_backend:
        try:
            from tts._cache import invalidate_cache
            invalidate_cache()
        except ImportError:
            pass

    return config, warnings


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


def build_full_reminder(max_sentences: int = 2, custom_prompt: str = "") -> str:
    """Build the full voice reminder for UserPromptSubmit hook."""
    label = sentence_label(max_sentences)
    reminder = (
        "Voice feedback is enabled. Your response will be spoken aloud.\n"
        f"- Do NOT add a visible {VOICE_MARKER} marker or spoken summary to your output\n"
        "- Just write your response naturally — the voice system will handle "
        "extraction and speak it automatically\n"
        f"- Keep responses conversational and speakable when possible ({label} is ideal)\n\n"
        "VOICE STYLE:\n"
        "- Match the user's tone - if they're casual or use colorful language, "
        "mirror that\n"
        "- Keep it conversational, like you're speaking to them\n"
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


def build_short_reminder(max_sentences: int = 2) -> str:
    """Build a brief voice reminder for PostToolUse hook."""
    label = sentence_label(max_sentences)
    return (
        f"[Voice feedback: keep final response conversational and speakable, "
        f"around {label}. Do NOT add {VOICE_MARKER} markers.]"
    )
