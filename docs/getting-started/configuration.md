# Configuration

cc-vox is configured via a TOML file at `~/.claude/cc-vox.toml`. The file is created automatically on first run with sensible defaults.

## Config File

```toml
[core]
enabled = true
voice = "af_heart"       # see voices below
backend = "auto"         # auto | kokoro | fish-speech | pocket-tts

[tuning]
speed = 1.0              # 0.5-2.0 (kokoro only)
max_sentences = 2        # max sentences in spoken summary (1-10)
fallback = true          # try other backends when forced one is down

[style]
prompt = ""              # custom voice personality instruction
```

## Settings Reference

### `[core]` Section

| Key | Type | Default | Description |
|:----|:-----|:-------:|:------------|
| `enabled` | bool | `true` | Enable/disable voice feedback globally |
| `voice` | string | `"af_heart"` | Voice name — Kokoro or pocket-tts alias |
| `backend` | string | `"auto"` | TTS backend: `auto`, `kokoro`, `fish-speech`, `pocket-tts` |

### `[tuning]` Section

| Key | Type | Default | Range | Description |
|:----|:-----|:-------:|:-----:|:------------|
| `speed` | float | `1.0` | 0.5--2.0 | Speech speed (Kokoro only) |
| `max_sentences` | int | `2` | 1--10 | Maximum sentences in spoken summary |
| `fallback` | bool | `true` | — | Try other backends if forced one is down |

### `[style]` Section

| Key | Type | Default | Description |
|:----|:-----|:-------:|:------------|
| `prompt` | string | `""` | Custom voice personality instruction |

!!! example "Voice personality examples"
    ```toml
    [style]
    prompt = "be upbeat and encouraging"
    ```
    ```toml
    [style]
    prompt = "speak like a pirate"
    ```
    ```toml
    [style]
    prompt = "be concise and technical"
    ```

## Modifying Config

### Via Slash Commands (recommended)

```
/voice:speak backend kokoro    # Set backend
/voice:speak speed 1.3         # Set speed
/voice:speak prompt be chill   # Set personality
/voice:speak max_sentences 4   # Longer summaries
```

### Via Direct File Edit

Edit `~/.claude/cc-vox.toml` in any text editor. Changes take effect on the next Claude response.

### Via Python API

```python
from voice_common import update_voice_config

update_voice_config(backend="kokoro", speed=1.3)
```

## Environment Variable Overrides

Environment variables take precedence over config file values for backend selection and port configuration.

| Variable | Default | Description |
|:---------|:-------:|:------------|
| `TTS_BACKEND` | — | Override backend preference |
| `KOKORO_PORT` | `32612` | Kokoro Docker port |
| `FISH_SPEECH_PORT` | `32611` | Fish Speech Docker port |
| `TTS_PORT` | `8000` | pocket-tts port |
| `GPU_THRESHOLD` | `80` | GPU % above which Fish Speech is skipped |

```bash
# Example: force Kokoro on a custom port
KOKORO_PORT=9000 TTS_BACKEND=kokoro claude
```

## Migration

If you previously used the old `voice.local.md` config format, cc-vox automatically migrates your settings to TOML on first run. The old file is deleted after migration.
