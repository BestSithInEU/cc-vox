# Environment Variables

All environment variables are optional. They override config file values where applicable.

## Backend Selection

| Variable | Default | Description |
|:---------|:-------:|:------------|
| `TTS_BACKEND` | — | Override backend preference. Values: `auto`, `kokoro`, `fish-speech`, `pocket-tts`, `chatterbox`, `qwen3-tts` |

```bash
TTS_BACKEND=kokoro claude
```

## Port Configuration

| Variable | Default | Used By | Description |
|:---------|:-------:|:--------|:------------|
| `KOKORO_PORT` | `32612` | Kokoro backend | Docker container port for Kokoro API |
| `FISH_SPEECH_PORT` | `32611` | Fish Speech backend | Docker container port for Fish Speech API |
| `CHATTERBOX_PORT` | `32613` | Chatterbox backend | Docker container port for Chatterbox API |
| `QWEN3_TTS_PORT` | `32614` | Qwen3-TTS backend | Docker container port for Qwen3-TTS API |
| `TTS_PORT` | `8000` | pocket-tts backend | Server port for pocket-tts |

```bash
# Run Kokoro on a non-default port
docker run -d --name kokoro -p 9000:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
KOKORO_PORT=9000 claude
```

## GPU Configuration

| Variable | Default | Description |
|:---------|:-------:|:------------|
| `GPU_THRESHOLD` | `80` | GPU utilization percentage above which Fish Speech is skipped in auto mode |

```bash
# Allow Fish Speech even when GPU is 90% utilized
GPU_THRESHOLD=95 claude
```

## Claude Code Variables

These are set by Claude Code itself and used by the hook scripts:

| Variable | Description |
|:---------|:------------|
| `CLAUDE_PLUGIN_ROOT` | Root directory of the installed plugin |
| `CLAUDE_CONFIG_DIR` | Claude Code config directory (default `~/.claude`) |

## Temporary Files

cc-vox creates temporary files for inter-process coordination:

| Path | Purpose |
|:-----|:--------|
| `/tmp/voice-playback.lock` | Playback mutex (prevents overlapping audio) |
| `/tmp/voice-{session_id}-running` | TTS is in progress |
| `/tmp/voice-{session_id}-done` | TTS completed successfully |
| `/tmp/voice-{session_id}-failed` | TTS failed |
| `/tmp/pocket-tts-server.log` | pocket-tts auto-start log |
