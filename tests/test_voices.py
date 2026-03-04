"""Tests for tts.voices — alias resolution, catalog integrity, comments."""

from __future__ import annotations

import pytest

from tts.voices import (
    ALIAS_TO_KOKORO,
    DEFAULT_VOICE,
    KOKORO_TO_ALIAS,
    VOICE_CATALOG,
    to_alias,
    to_kokoro,
    voice_comments,
)


# ── to_kokoro ────────────────────────────────────────────────────────


class TestToKokoro:
    @pytest.mark.parametrize(
        "alias, expected",
        [
            ("alba", "af_heart"),
            ("azure", "af_bella"),
            ("fantine", "af_nicole"),
            ("cosette", "af_sarah"),
            ("eponine", "af_sky"),
            ("marius", "am_adam"),
            ("jean", "am_michael"),
            ("azelma", "bf_emma"),
        ],
    )
    def test_alias_to_kokoro(self, alias: str, expected: str) -> None:
        assert to_kokoro(alias) == expected

    @pytest.mark.parametrize(
        "kokoro_name",
        list(VOICE_CATALOG.keys()),
    )
    def test_kokoro_passthrough(self, kokoro_name: str) -> None:
        assert to_kokoro(kokoro_name) == kokoro_name

    def test_unknown_returns_default(self) -> None:
        assert to_kokoro("nonexistent_voice") == DEFAULT_VOICE

    def test_empty_string_returns_default(self) -> None:
        assert to_kokoro("") == DEFAULT_VOICE


# ── to_alias ─────────────────────────────────────────────────────────


class TestToAlias:
    def test_kokoro_to_alias(self) -> None:
        assert to_alias("af_heart") == "alba"

    def test_no_alias_passthrough(self) -> None:
        # bm_george has no alias in VOICE_CATALOG
        assert to_alias("bm_george") == "bm_george"

    def test_alias_input_returns_alias(self) -> None:
        # Passing "alba" should resolve to kokoro first, then back to alias
        assert to_alias("alba") == "alba"

    @pytest.mark.parametrize(
        "kokoro_name, expected_alias",
        [
            ("af_bella", "azure"),
            ("af_nicole", "fantine"),
            ("am_adam", "marius"),
            ("bf_emma", "azelma"),
        ],
    )
    def test_all_aliased_voices(self, kokoro_name: str, expected_alias: str) -> None:
        assert to_alias(kokoro_name) == expected_alias


# ── VOICE_CATALOG integrity ──────────────────────────────────────────


class TestVoiceCatalog:
    def test_every_entry_has_gender(self) -> None:
        for name, info in VOICE_CATALOG.items():
            assert "gender" in info, f"{name} missing 'gender'"

    def test_every_entry_has_accent(self) -> None:
        for name, info in VOICE_CATALOG.items():
            assert "accent" in info, f"{name} missing 'accent'"

    def test_all_aliases_are_unique(self) -> None:
        aliases = [
            info["alias"]
            for info in VOICE_CATALOG.values()
            if "alias" in info
        ]
        assert len(aliases) == len(set(aliases)), "Duplicate aliases found"

    def test_default_voice_in_catalog(self) -> None:
        assert DEFAULT_VOICE in VOICE_CATALOG


# ── ALIAS_TO_KOKORO / KOKORO_TO_ALIAS symmetry ──────────────────────


class TestLookupSymmetry:
    def test_alias_to_kokoro_and_back(self) -> None:
        for alias, kokoro in ALIAS_TO_KOKORO.items():
            assert KOKORO_TO_ALIAS[kokoro] == alias

    def test_kokoro_to_alias_and_back(self) -> None:
        for kokoro, alias in KOKORO_TO_ALIAS.items():
            assert ALIAS_TO_KOKORO[alias] == kokoro

    def test_same_length(self) -> None:
        assert len(ALIAS_TO_KOKORO) == len(KOKORO_TO_ALIAS)


# ── voice_comments ───────────────────────────────────────────────────


class TestVoiceComments:
    def test_returns_list_of_strings(self) -> None:
        result = voice_comments()
        assert isinstance(result, list)
        assert all(isinstance(line, str) for line in result)

    def test_all_catalog_voices_mentioned(self) -> None:
        lines = "\n".join(voice_comments())
        for kokoro_name in VOICE_CATALOG:
            assert kokoro_name in lines, f"{kokoro_name} not in voice_comments output"

    def test_default_voice_marked(self) -> None:
        lines = "\n".join(voice_comments())
        assert "(default)" in lines

    def test_default_marker_on_correct_voice(self) -> None:
        for line in voice_comments():
            if "(default)" in line:
                assert DEFAULT_VOICE in line
                break
        else:
            pytest.fail("No line with (default) marker found")
