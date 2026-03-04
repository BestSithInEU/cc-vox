# Changelog

## [Unreleased]

Refactored TTS backends to use ABC inheritance hierarchy (`TTSBackend` → `DockerBackend` → `OpenAICompatibleBackend`), eliminating duplicated health checks, Docker stop logic, and OpenAI-compatible payload construction
Added `_errors.py` with `TTSError`, `TTSConnectionError`, and `TTSGenerationError` exception hierarchy for structured error handling
Added `create_backend(name)` factory function to the TTS registry
Added `__init_subclass__` enforcement on `TTSBackend` ABC — subclasses missing required class attributes (`name`, `priority`, `port`, `health_path`) raise `TypeError` at class definition time
Added `/speak stop` now also stops running TTS backend services (Docker containers and pocket-tts process) to free resources
Added `stop()` method to the TTS backend protocol, allowing each backend to clean up its own service
Added `scripts/stop-backends` CLI tool for stopping all running TTS backends
Added `generate_with_fallback()` — automatic retry with next-priority backend when `generate()` fails, replacing the manual select-then-generate flow in `scripts/say`
Added `volume` config option (0.0–2.0) with per-player support: ffplay `-volume`, afplay `-v`, paplay `--volume`
Added `debug` config option and `--debug` CLI flag — prints `[cc-vox]` diagnostics to stderr for backend selection, generate timing, and player choice
Added stale lock detection in `PlaybackLock` — recovers from dead-process locks instead of waiting 30s
Added `cleanup_stale_sessions()` to remove `/tmp/voice-*` sentinel files older than 1 hour
Added pocket-tts race guard in `_start()` — checks if a process is already listening before spawning
Added pocket-tts graceful stop — waits up to 3s for process to exit after SIGTERM
Added deterministic backend ordering with secondary sort by name when priorities are equal
Added actionable error message when no TTS service is available
Fixed file descriptor leak in pocket-tts `_start()` — log file now uses a context manager
Fixed Fish Speech `generate()` missing bounds check on SSE response data before index access
Fixed bare `RuntimeError` in Fish Speech replaced with `TTSGenerationError`
Fixed all backends now wrap `generate()` errors into `TTSConnectionError` or `TTSGenerationError` via the ABC template method
Fixed `/speak backend <name>` silently falling back to "auto" when given an invalid backend name instead of showing an error

## [0.1.1] - 2026-03-03

Fixed Claude CLI JSON output parser to handle the new list response format (array of content blocks) in addition to the original dict format
Added `max_sentences` config option (1-10) replacing the old `max_words` setting, giving more intuitive control over spoken summary length
Fixed config file auto-rewriting on schema changes so renamed keys like `max_words` get replaced with the current schema automatically

## [0.1.0] - 2026-03-02

Initial release — multi-backend TTS plugin for Claude Code

Added 5 swappable TTS backends: Qwen3-TTS (GPU), Fish Speech (GPU), Chatterbox (GPU), Kokoro (CPU), and pocket-tts (CPU, auto-starts via uvx)
Added automatic backend selection with priority-based routing and GPU utilization awareness
Added 3-hook pipeline: UserPromptSubmit injects voice instructions, PostToolUse re-injects reminders during long tool chains, Stop extracts and speaks summaries
Added `/speak` slash command for enabling, disabling, and configuring voice feedback
Added TOML-based configuration at `~/.claude/cc-vox.toml` with migration from legacy format
Added voice name mapping between Kokoro canonical names and pocket-tts aliases
Added session state tracking with sentinel files and playback locking to prevent audio overlap
Added GPU-aware routing that skips Fish Speech when GPU utilization exceeds threshold
