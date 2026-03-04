"""Shared fixtures for cc-vox test suite."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture()
def tmp_config(tmp_path: Path):
    """Redirect VoiceConfig to a temp file so tests don't touch real config."""
    config_path = tmp_path / "cc-vox.toml"
    with (
        patch("voice_common.DEFAULT_CONFIG_PATH", config_path),
        patch("voice_common.OLD_CONFIG_PATH", tmp_path / "voice.local.md"),
    ):
        yield config_path


@pytest.fixture()
def tmp_old_config(tmp_path: Path):
    """Write a legacy voice.local.md for migration tests."""
    old_path = tmp_path / "voice.local.md"
    old_path.write_text(
        "---\n"
        "enabled: true\n"
        'voice: af_bella\n'
        'prompt: "be concise"\n'
        "---\n"
    )
    config_path = tmp_path / "cc-vox.toml"
    with (
        patch("voice_common.DEFAULT_CONFIG_PATH", config_path),
        patch("voice_common.OLD_CONFIG_PATH", old_path),
    ):
        yield config_path


@pytest.fixture()
def mock_session_file(tmp_path: Path):
    """Factory that writes JSONL lines to a temp file and returns the path."""
    def _make(messages: list[dict]) -> Path:
        path = tmp_path / "session.jsonl"
        with open(path, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")
        return path
    return _make
