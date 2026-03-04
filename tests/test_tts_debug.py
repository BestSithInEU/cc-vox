"""Tests for the tts._debug module."""

from __future__ import annotations

import time
from unittest.mock import patch

from tts._debug import Timer, enable, is_enabled, log

import tts._debug as _debug_mod


class TestDebugToggle:
    def setup_method(self) -> None:
        _debug_mod._enabled = False

    def teardown_method(self) -> None:
        _debug_mod._enabled = False

    def test_initially_disabled(self) -> None:
        assert is_enabled() is False

    def test_enable_sets_flag(self) -> None:
        enable()
        assert is_enabled() is True

    def test_log_silent_when_disabled(self, capsys) -> None:
        log("should not appear")
        assert capsys.readouterr().err == ""

    def test_log_prints_when_enabled(self, capsys) -> None:
        enable()
        log("hello debug")
        assert "[cc-vox] hello debug" in capsys.readouterr().err


class TestTimer:
    def setup_method(self) -> None:
        _debug_mod._enabled = False

    def teardown_method(self) -> None:
        _debug_mod._enabled = False

    def test_timer_logs_elapsed(self, capsys) -> None:
        enable()
        with Timer("test-op"):
            pass  # instant
        captured = capsys.readouterr().err
        assert "[cc-vox] test-op:" in captured
        assert "s" in captured

    def test_timer_silent_when_disabled(self, capsys) -> None:
        with Timer("test-op"):
            pass
        assert capsys.readouterr().err == ""
