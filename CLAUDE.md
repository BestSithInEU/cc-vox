# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cc-vox is a Claude Code plugin marketplace shipping two plugins:

1. **voice** — Speaks a short summary aloud after every Claude response using swappable TTS backends.
2. **statusline** — Catppuccin-themed statusline showing costs, context window, usage windows, git info, and MCP servers.

**Python 3.11+, stdlib only, no pip install.** This is a Claude Code plugin marketplace, not a Python package.

## Repository Layout

```
cc-vox/
├── .claude-plugin/
│   └── marketplace.json        # lists both plugins
├── plugins/
│   ├── voice/                  # TTS voice feedback plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── hooks/              # 3 Claude Code hooks + TTS system
│   │   ├── scripts/            # say, stop-backends
│   │   └── commands/           # /speak slash command
│   └── statusline/             # statusline plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── statusline.py       # entry point
│       ├── statusline_pkg/     # rendering pipeline
│       ├── scripts/            # setup-statusline
│       └── commands/           # /setup-statusline slash command
├── tests/                      # pytest suite (voice plugin)
├── docs/                       # documentation site
└── assets/                     # SVG diagrams and logos
```

## Development Commands

```bash
# Run Claude Code with the full marketplace loaded
claude --plugin-dir .

# Run a single plugin
claude --plugin-dir ./plugins/voice
claude --plugin-dir ./plugins/statusline

# Test the TTS pipeline directly
uv run python plugins/voice/scripts/say.py --voice af_heart "Hello world"

# Force a specific backend
TTS_BACKEND=kokoro uv run python plugins/voice/scripts/say.py "Testing Kokoro"

# Setup statusline
bash plugins/statusline/scripts/setup-statusline

# Run tests
uv run --with pytest pytest -v

# Preview docs locally
zensical serve

# Build docs (strict mode catches broken links)
zensical build --strict
```

## Architecture

### Voice Plugin (`plugins/voice/`)

#### Hook Pipeline (3 hooks, registered in `plugins/voice/hooks/hooks.json`)

1. **UserPromptSubmit** (`hooks/user_prompt_submit_hook.py`) — Injects a system message telling Claude to end responses with a `📢 [spoken summary]` marker.
2. **PostToolUse** (`hooks/post_tool_use_hook.py`) — Re-injects a brief reminder during long tool-call chains to keep the instruction in context.
3. **Stop** (`hooks/stop_hook.py`) — Extracts speakable text via a 4-strategy cascade (📢 marker → short response → headless Claude summary → truncation), then launches `scripts/say` as a background subprocess.

#### TTS System (`plugins/voice/hooks/tts/`)

- `_protocol.py` — `TTSBackend` Protocol: `name`, `priority`, `is_available()`, `ensure_running()`, `generate(text, voice, speed) -> bytes`
- `__init__.py` — Registry + `select_backend()`. Auto-selection tries backends by priority (lower = first).
- Three backends: **Fish Speech** (priority=10, GPU, Docker `:32611`), **Kokoro** (priority=20, CPU, Docker `:32612`), **pocket-tts** (priority=30, CPU, auto-starts via `uvx`).
- `voices.py` — Single source of truth for voice name mapping (Kokoro canonical ↔ pocket-tts alias).
- `_playback.py` — Audio playback (ffplay > afplay > aplay > paplay). Uses `fcntl.flock` on `/tmp/voice-playback.lock`.
- `_session_state.py` — Sentinel files at `/tmp/voice-{session_id}-{running,done,failed}`.

#### Configuration

TOML config at `~/.claude/cc-vox.toml` with sections: `[core]`, `[tuning]`, `[style]`, `[internal]`. Read/written by `plugins/voice/hooks/voice_common.py` which holds the `VoiceConfig` dataclass.

#### Adding a TTS Backend

1. Create `plugins/voice/hooks/tts/my_backend.py` implementing `TTSBackend`
2. Add one import + entry to `_registry()` in `plugins/voice/hooks/tts/__init__.py`

### Statusline Plugin (`plugins/statusline/`)

Python-based statusline rendering pipeline:
- `statusline.py` — Entry point, run via `uv run python statusline.py`
- `statusline_pkg/__main__.py` — Orchestrator: parse stdin → OAuth → windows → costs → git → MCP → render
- `statusline_pkg/renderer.py` — 5-line output (identity, costs, context, windows, MCP)
- `statusline_pkg/theme.py` — Catppuccin color palette with dynamic accent colors

Setup: `bash plugins/statusline/scripts/setup-statusline` writes the `statusLine` setting to `~/.claude/settings.json`.

## Conventions

- **Commits**: Conventional format — `<type>: <subject>` (feat, fix, refactor, docs, style, test, chore, perf). Imperative mood, no trailing period. Template: `.gitmessage`
- **Code style**: Type hints on all public signatures. Docstrings on public functions/classes. `from __future__ import annotations` at top of every file. Private modules prefixed with underscore.
- **Dependencies**: Stdlib only. No external Python packages.
- **Branches**: Feature branches from `main`, named `feat/my-feature`.

## Key Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `TTS_BACKEND` | `auto` | Override backend selection |
| `KOKORO_PORT` | `32612` | Kokoro Docker port |
| `FISH_SPEECH_PORT` | `32611` | Fish Speech Docker port |
| `TTS_PORT` | `8000` | pocket-tts port |
| `GPU_THRESHOLD` | `80` | GPU % above which Fish Speech is skipped |
