# Slash Commands

cc-vox provides the `/voice:speak` slash command for runtime control of voice feedback. All changes persist to `~/.claude/cc-vox.toml`.

## Command Reference

### Enable / Disable

| Command | Description |
|:--------|:------------|
| `/voice:speak` | Enable voice feedback with current settings |
| `/voice:speak stop` | Disable voice feedback |

### Voice

| Command | Description |
|:--------|:------------|
| `/voice:speak <voice>` | Set voice and enable feedback |
| `/voice:speak af_bella` | Example: switch to af_bella |
| `/voice:speak alba` | Example: pocket-tts alias also works |

See the full [voice catalog](voices.md) for all available voices.

### Backend

| Command | Description |
|:--------|:------------|
| `/voice:speak backend auto` | Auto-detect best backend (default) |
| `/voice:speak backend kokoro` | Force Kokoro |
| `/voice:speak backend fish-speech` | Force Fish Speech |
| `/voice:speak backend pocket-tts` | Force pocket-tts |

### Tuning

| Command | Description |
|:--------|:------------|
| `/voice:speak speed <value>` | Set speech speed, 0.5--2.0 (Kokoro only) |
| `/voice:speak max_sentences <value>` | Set max summary sentences, 1--10 |
| `/voice:speak fallback on` | Enable backend fallback |
| `/voice:speak fallback off` | Disable backend fallback |

### Personality

| Command | Description |
|:--------|:------------|
| `/voice:speak prompt <text>` | Set custom voice personality |
| `/voice:speak prompt` | Clear custom prompt |

## Examples

```
# Quick enable with default voice
/voice:speak

# Switch to a male British voice
/voice:speak bm_george

# Make it faster and more casual
/voice:speak speed 1.4
/voice:speak prompt be chill and casual

# Force Kokoro backend with longer summaries
/voice:speak backend kokoro
/voice:speak max_sentences 4

# Disable voice
/voice:speak stop
```
