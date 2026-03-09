# Changelog

## [Unreleased]

### Marketplace

Restructured repository from flat layout to marketplace with two independent plugins (`plugins/voice/`, `plugins/statusline/`)
Added `marketplace.json` listing both voice and statusline plugins
Added support for `claude --plugin-dir ./plugins/voice` and `claude --plugin-dir ./plugins/statusline` for individual plugin loading

### Statusline Plugin (new)

Added Catppuccin-themed statusline with costs, context window, usage windows, git info, and MCP server display
Added `statusline.py` entry point run via `uv run python statusline.py`
Added rendering pipeline: `data_input` → `oauth` → `windows` → `costs` → `git_info` → `mcp` → `renderer`
Added dynamic accent colors and 5-line output (identity, costs, context, windows, MCP)
Added voice status integration showing active TTS backend and current voice (e.g. `voice ● pocket-tts · af_heart`)
Added SessionStart hook (`hooks/auto_setup.py`) for idempotent auto-configuration of `statusLine` in `~/.claude/settings.json`
Added `/setup-statusline` slash command with install and uninstall support
Added `uv run --no-project` in hook command to avoid inheriting the host project's virtualenv

### Voice Plugin

#### Architecture

Refactored TTS backends to use ABC inheritance hierarchy (`TTSBackend` → `DockerBackend` → `OpenAICompatibleBackend`), eliminating duplicated health checks, Docker stop logic, and OpenAI-compatible payload construction
Added `hook_framework.py` — minimal hook framework with `HookResult` dataclass and `run_hook()`, eliminating boilerplate across all three hooks
Added `constants.py` — single source of truth for magic values (marker emoji, config bounds, truncation limits)
Added `extraction.py` — 4-strategy text extraction cascade (📢 marker → short response → headless Claude summary → truncation)
Added `sanitize.py` — client-side TTS text cleanup (strips paths, UUIDs, SHAs, URLs, backtick-wrapped code)
Added `speaker.py` — background subprocess launcher for say script
Converted `scripts/say` and `scripts/stop-backends` from bash to Python (`say.py`, `stop_backends.py`)

#### TTS System

Added `_errors.py` with `TTSError`, `TTSConnectionError`, and `TTSGenerationError` exception hierarchy
Added `create_backend(name)` factory function to the TTS registry
Added `__init_subclass__` enforcement on `TTSBackend` ABC — subclasses missing required class attributes raise `TypeError` at class definition time
Added `generate_with_fallback()` — automatic retry with next-priority backend when generation fails
Added `_cache.py` — per-session backend caching with 5-minute TTL to avoid repeated probing
Added `_lang.py` — language detection via Unicode character range heuristics (CJK, Japanese, Korean, Russian) with backend routing to Qwen3-TTS for non-English text
Added `_state_file.py` — cross-plugin coordination state at `/tmp/cc-vox-state.json` for statusline consumption
Added `_history.py` — voice clip history with WAV + JSON sidecar storage at `~/.claude/voice-history/`, supports listing, replay, and auto-cleanup (50 clip max)
Added deterministic backend ordering with secondary sort by name when priorities are equal
Added actionable error message when no TTS service is available

#### Playback

Complete rewrite of `_playback.py` with cross-platform support (Unix fcntl, Windows msvcrt)
Added `play_audio_streaming()` — pipes chunks to ffplay for low-latency streaming, falls back to buffering
Added stale lock detection in `PlaybackLock` — recovers from dead-process locks instead of waiting 30s
Added `volume` config option (0.0–2.0) with per-player support: ffplay `-volume`, afplay `-v`, paplay `--volume`
Added winsound fallback for Windows

#### New Features

Added `debug` config option and `--debug` CLI flag — prints `[cc-vox]` diagnostics to stderr
Added conversational mode — periodic voice updates during tool chains with configurable interval (5–300s)
Added voice cloning support via `/speak clone <path>` for Chatterbox backend (.wav/.mp3/.ogg)
Added voice clip history with `/speak history`, `/speak replay [N]`, and `/speak save on|off`
Added `/speak stop` now also stops running TTS backend services (Docker containers and pocket-tts process)
Added `scripts/status.py` — probes all backends, shows config summary and response times
Added `scripts/replay.py` — lists and replays recent voice clips
Added `scripts/stop_backends.py` — stops all running TTS backend services
Added `cleanup_stale_sessions()` to remove `/tmp/voice-*` sentinel files older than 1 hour
Added `/voice:speak debug on|off` command to toggle debug logging

#### Stop Hook

Changed stop hook to read `last_assistant_message` from stdin instead of session file I/O, eliminating race conditions
Removed visible `📢` marker from Claude's output — voice system now extracts text directly from the response
Changed voice prompt to present `max_sentences` as an ideal target length, not just a cap
Added file-based debug logging at `/tmp/cc-vox-stop-hook.log` for diagnosing hook failures

#### Statusline MCP Detection

Fixed `GlobalConfigSource` missing `~/.claude/.mcp.json` — Docker MCP servers were not detected when cache expired

#### Command Namespacing

Changed all `/speak` references to `/voice:speak` to match Claude Code plugin namespacing
Changed `/setup-statusline` to `/statusline:setup-statusline`

#### Backend Fixes

Added pocket-tts race guard in `_start()` — checks if process already listening before spawning
Added pocket-tts graceful stop — waits up to 3s for process to exit after SIGTERM
Fixed file descriptor leak in pocket-tts `_start()` — log file now uses context manager
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
