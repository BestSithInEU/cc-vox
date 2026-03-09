"""Tests for client-side text sanitization."""

from __future__ import annotations

from sanitize import sanitize_text


class TestSanitizeUnixPaths:
    def test_strips_unix_path(self) -> None:
        text = "I updated /Users/foo/bar/config.json for you."
        assert "a file" in sanitize_text(text)
        assert "/Users/foo" not in sanitize_text(text)

    def test_strips_deep_path(self) -> None:
        text = "Check /home/user/projects/cc-vox/plugins/voice/hooks/tts/__init__.py"
        result = sanitize_text(text)
        assert "a file" in result
        assert "__init__.py" not in result

    def test_preserves_short_path(self) -> None:
        # Single-segment paths like /tmp should be preserved
        text = "Saved to /tmp."
        assert sanitize_text(text) == "Saved to /tmp."


class TestSanitizeWindowsPaths:
    def test_strips_windows_path(self) -> None:
        text = r"I edited C:\Users\Batuhan\Desktop\projects\file.py"
        result = sanitize_text(text)
        assert "a file" in result
        assert "Batuhan" not in result


class TestSanitizeUUIDs:
    def test_strips_uuid(self) -> None:
        text = "The session ID is 550e8400-e29b-41d4-a716-446655440000."
        result = sanitize_text(text)
        assert "an identifier" in result
        assert "550e8400" not in result

    def test_strips_uppercase_uuid(self) -> None:
        text = "ID: 550E8400-E29B-41D4-A716-446655440000"
        result = sanitize_text(text)
        assert "an identifier" in result


class TestSanitizeSHA:
    def test_strips_short_sha(self) -> None:
        text = "Commit dfa24e2 added the fix."
        result = sanitize_text(text)
        assert "a hash" in result
        assert "dfa24e2" not in result

    def test_strips_full_sha(self) -> None:
        text = "SHA: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        result = sanitize_text(text)
        assert "a hash" in result

    def test_preserves_normal_words(self) -> None:
        # Normal words shouldn't match the SHA pattern
        text = "The backend is available."
        assert sanitize_text(text) == "The backend is available."


class TestSanitizeHex:
    def test_strips_hex_value(self) -> None:
        text = "Address 0x7FFF5FBFF8A0 in memory."
        result = sanitize_text(text)
        assert "a hex value" in result
        assert "0x7FFF" not in result


class TestSanitizeURLs:
    def test_strips_url(self) -> None:
        text = "Check https://github.com/anthropics/claude-code/issues for details."
        result = sanitize_text(text)
        assert "a link" in result
        assert "github.com" not in result

    def test_strips_http_url(self) -> None:
        text = "Visit http://localhost:8080/api/v1/health"
        result = sanitize_text(text)
        assert "a link" in result


class TestSanitizeBackticks:
    def test_strips_short_backtick(self) -> None:
        text = "Run `npm install` to set up."
        result = sanitize_text(text)
        assert "npm install" in result
        assert "`" not in result

    def test_replaces_long_backtick(self) -> None:
        long_code = "x" * 100
        text = f"I added `{long_code}` to the file."
        result = sanitize_text(text)
        assert "some code" in result
        assert long_code not in result


class TestSanitizeMixed:
    def test_mixed_content(self) -> None:
        text = (
            "I updated /Users/foo/src/bar/config.json with commit dfa24e2 "
            "and deployed to https://example.com/api."
        )
        result = sanitize_text(text)
        assert "/Users/foo" not in result
        assert "dfa24e2" not in result
        assert "example.com" not in result
        assert "a file" in result
        assert "a hash" in result
        assert "a link" in result

    def test_clean_text_unchanged(self) -> None:
        text = "Everything looks good. The tests are passing."
        assert sanitize_text(text) == text

    def test_empty_string(self) -> None:
        assert sanitize_text("") == ""

    def test_collapses_extra_spaces(self) -> None:
        text = "Hello   world"
        assert sanitize_text(text) == "Hello world"
