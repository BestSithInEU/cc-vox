---
allowed-tools: Bash, Read, Write, Edit
arguments: voice
---

Enable, disable, or configure voice feedback.

**Commands:**
- `/speak` - Enable voice feedback with current voice
- `/speak <voice>` - Set voice and enable feedback
- `/speak stop` - Disable voice feedback
- `/speak prompt <text>` - Set custom instruction for voice summaries
- `/speak prompt` - Clear custom prompt
- `/speak backend <name>` - Switch TTS backend (auto, kokoro, fish-speech, pocket-tts, chatterbox, qwen3-tts)
- `/speak speed <value>` - Set speech speed (0.5-2.0, kokoro only)
- `/speak max_words <value>` - Set max spoken summary length (5-100)
- `/speak fallback on|off` - Toggle backend fallback behavior

**Config file:** `~/.claude/cc-vox.toml`

```toml
[core]
enabled = true
voice = "af_heart"
backend = "auto"

[tuning]
speed = 1.0
max_words = 25
fallback = true

[style]
prompt = "be upbeat and encouraging"
```

**Backends:**
- `auto` (default) - Tries Fish Speech → Chatterbox → Qwen3-TTS → Kokoro → pocket-tts
- `kokoro` - Force Kokoro (Docker CPU, port 32612)
- `fish-speech` - Force Fish Speech (Docker GPU, port 32611)
- `chatterbox` - Force Chatterbox (Docker GPU, port 32613)
- `qwen3-tts` - Force Qwen3-TTS (Docker GPU, port 32614)
- `pocket-tts` - Force pocket-tts (uvx, port 8000, auto-starts if needed)

**Kokoro voices (Docker):**
- Female: `af_heart` (default), `af_bella`, `af_nicole`, `af_sarah`, `af_sky`
- Male: `am_adam`, `am_michael`
- British: `bf_emma`, `bm_george`

**pocket-tts voices (mapped to Kokoro):**
- `alba` → af_heart, `azure` → af_bella, `marius` → am_adam
- `jean` → am_michael, `fantine` → af_nicole, `cosette` → af_sarah
- `eponine` → af_sky, `azelma` → bf_emma

**Behavior:**
- When no argument: Set `enabled = true` and tell user:
  "Voice feedback enabled. Use `/speak stop` to disable, or `/speak <name>` to change voice."
- When voice name given: Set `voice = "<name>"` and `enabled = true`, tell user:
  "Voice set to <name> and enabled. Use `/speak stop` to disable."
- When `stop`: Set `enabled = false` AND set `just_disabled = true` in `[internal]` section (voice unchanged), tell user:
  "Voice feedback disabled. Use `/speak` to re-enable."
- When `prompt <text>`: Set `prompt = "<text>"` in `[style]`, tell user:
  "Custom prompt set: <text>"
- When `prompt` (no text): Set `prompt = ""` in `[style]`, tell user:
  "Custom prompt cleared."
- When `backend <name>`: Set `backend = "<name>"` in `[core]`, tell user:
  "TTS backend set to <name>."
- When `speed <value>`: Set `speed = <value>` in `[tuning]` (clamped 0.5-2.0), tell user:
  "Speech speed set to <value>."
- When `max_words <value>`: Set `max_words = <value>` in `[tuning]` (clamped 5-100), tell user:
  "Max spoken words set to <value>."
- When `fallback on`: Set `fallback = true` in `[tuning]`, tell user:
  "Backend fallback enabled."
- When `fallback off`: Set `fallback = false` in `[tuning]`, tell user:
  "Backend fallback disabled."

To update the config, import and call `update_voice_config()` from `hooks/voice_common.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "hooks"))
from voice_common import update_voice_config
update_voice_config(enabled=True, voice="af_bella")
```

Create the config file if it doesn't exist (default voice: af_heart, backend: auto).
