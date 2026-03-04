"""Tests for voice_common — config I/O, TOML round-trips, reminders."""

from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from voice_common import (
    VoiceConfig,
    _build_toml,
    _clamp,
    _migrate_old_config,
    build_full_reminder,
    build_short_reminder,
    clear_just_disabled_flag,
    get_voice_config,
    update_voice_config,
)


# ── _clamp ───────────────────────────────────────────────────────────


class TestClamp:
    def test_below_min(self) -> None:
        assert _clamp(-1.0, 0.0, 10.0) == 0.0

    def test_above_max(self) -> None:
        assert _clamp(15.0, 0.0, 10.0) == 10.0

    def test_in_range(self) -> None:
        assert _clamp(5.0, 0.0, 10.0) == 5.0

    def test_at_min_boundary(self) -> None:
        assert _clamp(0.0, 0.0, 10.0) == 0.0

    def test_at_max_boundary(self) -> None:
        assert _clamp(10.0, 0.0, 10.0) == 10.0


# ── build_full_reminder ──────────────────────────────────────────────


class TestBuildFullReminder:
    def test_singular_sentence(self) -> None:
        result = build_full_reminder(max_sentences=1)
        assert "1 sentence" in result
        assert "1 sentences" not in result

    def test_plural_sentences(self) -> None:
        result = build_full_reminder(max_sentences=2)
        assert "2 sentences" in result

    def test_with_custom_prompt(self) -> None:
        result = build_full_reminder(max_sentences=2, custom_prompt="speak slowly")
        assert "CUSTOM VOICE INSTRUCTION" in result
        assert "speak slowly" in result

    def test_without_custom_prompt(self) -> None:
        result = build_full_reminder(max_sentences=2)
        assert "CUSTOM VOICE INSTRUCTION" not in result

    def test_without_custom_prompt_empty_string(self) -> None:
        result = build_full_reminder(max_sentences=2, custom_prompt="")
        assert "CUSTOM VOICE INSTRUCTION" not in result


# ── build_short_reminder ─────────────────────────────────────────────


class TestBuildShortReminder:
    def test_singular(self) -> None:
        result = build_short_reminder(max_sentences=1)
        assert "1 sentence" in result
        assert "1 sentences" not in result

    def test_plural(self) -> None:
        result = build_short_reminder(max_sentences=3)
        assert "3 sentences" in result


# ── _build_toml round-trip ───────────────────────────────────────────


class TestBuildToml:
    def test_round_trip_defaults(self) -> None:
        config = VoiceConfig()
        toml_str = _build_toml(config)
        parsed = tomllib.loads(toml_str)

        assert parsed["core"]["enabled"] is True
        assert parsed["core"]["voice"] == "af_heart"
        assert parsed["core"]["backend"] == "auto"
        assert parsed["tuning"]["speed"] == 1.0
        assert parsed["tuning"]["max_sentences"] == 2
        assert parsed["tuning"]["fallback"] is True
        assert parsed["style"]["prompt"] == ""

    def test_round_trip_custom_values(self) -> None:
        config = VoiceConfig(
            enabled=False,
            voice="af_bella",
            backend="kokoro",
            speed=1.5,
            max_sentences=4,
            fallback=False,
            prompt="be dramatic",
        )
        toml_str = _build_toml(config)
        parsed = tomllib.loads(toml_str)

        assert parsed["core"]["enabled"] is False
        assert parsed["core"]["voice"] == "af_bella"
        assert parsed["core"]["backend"] == "kokoro"
        assert parsed["tuning"]["speed"] == 1.5
        assert parsed["tuning"]["max_sentences"] == 4
        assert parsed["tuning"]["fallback"] is False
        assert parsed["style"]["prompt"] == "be dramatic"

    def test_special_chars_in_prompt(self) -> None:
        config = VoiceConfig(prompt='say "hello" and use back\\slashes')
        toml_str = _build_toml(config)
        parsed = tomllib.loads(toml_str)
        assert parsed["style"]["prompt"] == 'say "hello" and use back\\slashes'

    def test_just_disabled_includes_internal(self) -> None:
        config = VoiceConfig(just_disabled=True)
        toml_str = _build_toml(config)
        parsed = tomllib.loads(toml_str)
        assert parsed["internal"]["just_disabled"] is True

    def test_no_internal_when_not_disabled(self) -> None:
        config = VoiceConfig(just_disabled=False)
        toml_str = _build_toml(config)
        parsed = tomllib.loads(toml_str)
        assert "internal" not in parsed


# ── get_voice_config ─────────────────────────────────────────────────


class TestGetVoiceConfig:
    def test_first_run_creates_default(self, tmp_config: Path) -> None:
        assert not tmp_config.exists()
        config = get_voice_config()
        assert tmp_config.exists()
        assert config.enabled is True
        assert config.voice == "af_heart"
        assert config.backend == "auto"

    def test_read_existing(self, tmp_config: Path) -> None:
        toml_content = (
            '[core]\n'
            'enabled = false\n'
            'voice = "af_bella"\n'
            'backend = "auto"\n'
            '\n'
            '[tuning]\n'
            'speed = 1.5\n'
            'max_sentences = 3\n'
            'fallback = false\n'
            '\n'
            '[style]\n'
            'prompt = "be concise"\n'
        )
        tmp_config.write_text(toml_content)
        config = get_voice_config()
        assert config.enabled is False
        assert config.voice == "af_bella"
        assert config.speed == 1.5
        assert config.max_sentences == 3
        assert config.fallback is False
        assert config.prompt == "be concise"

    def test_invalid_backend_falls_back(self, tmp_config: Path) -> None:
        toml_content = (
            '[core]\n'
            'enabled = true\n'
            'voice = "af_heart"\n'
            'backend = "nonexistent"\n'
            '\n'
            '[tuning]\n'
            'speed = 1.0\n'
            'max_sentences = 2\n'
            'fallback = true\n'
            '\n'
            '[style]\n'
            'prompt = ""\n'
        )
        tmp_config.write_text(toml_content)
        config = get_voice_config()
        assert config.backend == "auto"


# ── update_voice_config ──────────────────────────────────────────────


class TestUpdateVoiceConfig:
    def test_applies_changes(self, tmp_config: Path) -> None:
        # Create initial config
        get_voice_config()
        config = update_voice_config(voice="af_bella", max_sentences=4)
        assert config.voice == "af_bella"
        assert config.max_sentences == 4

    def test_clamps_speed_too_high(self, tmp_config: Path) -> None:
        get_voice_config()
        config = update_voice_config(speed=5.0)
        assert config.speed == 2.0

    def test_clamps_speed_too_low(self, tmp_config: Path) -> None:
        get_voice_config()
        config = update_voice_config(speed=0.1)
        assert config.speed == 0.5

    def test_rejects_invalid_backend(self, tmp_config: Path) -> None:
        get_voice_config()
        config = update_voice_config(backend="fake_backend")
        assert config.backend == "auto"

    def test_valid_speed_unchanged(self, tmp_config: Path) -> None:
        get_voice_config()
        config = update_voice_config(speed=1.3)
        assert config.speed == 1.3


# ── _migrate_old_config ──────────────────────────────────────────────


class TestMigrateOldConfig:
    def test_migrates_values(self, tmp_old_config: Path) -> None:
        config = get_voice_config()
        assert config.voice == "af_bella"
        assert config.prompt == "be concise"
        assert config.enabled is True
        # New TOML should exist, old file should be deleted
        assert tmp_old_config.exists()

    def test_new_config_written_after_migration(self, tmp_old_config: Path) -> None:
        get_voice_config()
        # New TOML config should exist with migrated values
        assert tmp_old_config.exists()
        raw = tmp_old_config.read_bytes()
        parsed = tomllib.loads(raw.decode())
        assert parsed["core"]["voice"] == "af_bella"

    def test_old_file_deleted_after_migration(self, tmp_path: Path) -> None:
        old_path = tmp_path / "voice.local.md"
        old_path.write_text("---\nvoice: af_bella\n---\n")
        config_path = tmp_path / "cc-vox.toml"
        with (
            patch("voice_common.DEFAULT_CONFIG_PATH", config_path),
            patch("voice_common.OLD_CONFIG_PATH", old_path),
        ):
            get_voice_config()
            assert not old_path.exists()


# ── clear_just_disabled_flag ─────────────────────────────────────────


class TestClearJustDisabledFlag:
    def test_clears_flag(self, tmp_config: Path) -> None:
        # First set the flag
        get_voice_config()
        update_voice_config(just_disabled=True)

        # Verify it's set
        config = get_voice_config()
        assert config.just_disabled is True

        # Clear it
        clear_just_disabled_flag()

        # Verify cleared
        config = get_voice_config()
        assert config.just_disabled is False

    def test_noop_when_no_config(self, tmp_config: Path) -> None:
        # Should not raise when config file doesn't exist
        assert not tmp_config.exists()
        clear_just_disabled_flag()  # Should be a no-op

    def test_noop_when_flag_not_set(self, tmp_config: Path) -> None:
        get_voice_config()
        # Flag is not set by default, clearing should be safe
        clear_just_disabled_flag()
        config = get_voice_config()
        assert config.just_disabled is False
