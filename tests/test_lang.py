"""Tests for language detection and backend routing."""

from __future__ import annotations

from tts._lang import backends_for_language, detect_language


class TestDetectLanguage:
    def test_english(self) -> None:
        assert detect_language("Hello world, this is a test.") == "en"

    def test_chinese(self) -> None:
        assert detect_language("你好世界，这是一个测试。") == "zh"

    def test_japanese(self) -> None:
        assert detect_language("こんにちは世界、これはテストです。") == "ja"

    def test_korean(self) -> None:
        assert detect_language("안녕하세요 세계, 이것은 테스트입니다.") == "ko"

    def test_russian(self) -> None:
        assert detect_language("Привет мир, это тест.") == "ru"

    def test_mixed_english_chinese(self) -> None:
        # Mostly English with a few Chinese chars → English
        text = "The function returns 值 from the database."
        assert detect_language(text) == "en"

    def test_mostly_chinese(self) -> None:
        # Mostly Chinese
        text = "这个函数从数据库返回值 and some English."
        assert detect_language(text) == "zh"

    def test_empty_string(self) -> None:
        assert detect_language("") == "en"

    def test_whitespace_only(self) -> None:
        assert detect_language("   ") == "en"

    def test_numbers_and_punctuation(self) -> None:
        assert detect_language("123, 456!") == "en"


class TestBackendsForLanguage:
    def test_chinese_prefers_qwen3(self) -> None:
        backends = backends_for_language("zh")
        assert "qwen3-tts" in backends

    def test_english_returns_empty(self) -> None:
        # Empty means "all backends" (no filtering)
        assert backends_for_language("en") == []

    def test_unknown_language_returns_empty(self) -> None:
        assert backends_for_language("xx") == []

    def test_japanese_prefers_qwen3(self) -> None:
        assert "qwen3-tts" in backends_for_language("ja")
