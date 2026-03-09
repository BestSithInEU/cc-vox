---
allowed-tools: Bash, Read, Write, Edit
arguments: voice
---

Enable, disable, or configure voice feedback.

**Commands:**
- `/voice:speak` - Enable voice feedback with current voice
- `/voice:speak <voice>` - Set voice and enable feedback
- `/voice:speak stop` - Disable voice feedback
- `/voice:speak status` - Show current config and active backend health
- `/voice:speak backends` - Show detailed health table for all TTS backends
- `/voice:speak preview` - Speak a sample sentence with current voice
- `/voice:speak preview <text>` - Speak custom text as a preview
- `/voice:speak prompt <text>` - Set custom instruction for voice summaries
- `/voice:speak prompt` - Clear custom prompt
- `/voice:speak backend <name>` - Switch TTS backend (auto, kokoro, fish-speech, pocket-tts, chatterbox, qwen3-tts)
- `/voice:speak speed <value>` - Set speech speed (0.5-2.0, kokoro only)
- `/voice:speak max_sentences <value>` - Set max sentences in spoken summary (1-10)
- `/voice:speak fallback on|off` - Toggle backend fallback behavior
- `/voice:speak clone <path>` - Set reference audio file for Chatterbox voice cloning
- `/voice:speak clone` - Clear voice cloning reference
- `/voice:speak history` - Show recent voice clips
- `/voice:speak replay [N]` - Replay the Nth most recent voice clip (default: latest)
- `/voice:speak save on|off` - Toggle saving voice clips to history
- `/voice:speak conversational on|off` - Toggle periodic voice updates during tool chains
- `/voice:speak interval <seconds>` - Set conversational update interval (default: 30)
- `/voice:speak debug on|off` - Toggle debug logging to stderr

**Config file:** `~/.claude/cc-vox.toml`

```toml
[core]
enabled = true
voice = "af_heart"
backend = "auto"

[tuning]
speed = 1.0
max_sentences = 2
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
- When `status`: Run `bash uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/status.py"` and show the output to the user.
- When `backends`: Run `bash uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" --detailed` and show the output to the user.
- When `preview`: Run `bash uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/say.py" "Hello! This is how your voice sounds right now."` in the background.
- When `preview <text>`: Run `bash uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/say.py" "<text>"` in the background.
- When no argument: Set `enabled = true` and tell user:
  "Voice feedback enabled. Use `/voice:speak stop` to disable, or `/voice:speak <name>` to change voice."
- When voice name given: Set `voice = "<name>"` and `enabled = true`, tell user:
  "Voice set to <name> and enabled. Use `/voice:speak stop` to disable."
- When `stop`:
  1. Set `enabled = false` AND set `just_disabled = true` in `[internal]` section (voice unchanged)
  2. Run `uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/stop_backends.py"` via Bash to stop any running TTS services
  3. Tell user: "Voice feedback disabled and TTS backends stopped. Use `/voice:speak` to re-enable."
- When `prompt <text>`: Set `prompt = "<text>"` in `[style]`, tell user:
  "Custom prompt set: <text>"
- When `prompt` (no text): Set `prompt = ""` in `[style]`, tell user:
  "Custom prompt cleared."
- When `backend <name>`: Validate that `<name>` is one of: auto, kokoro, fish-speech, pocket-tts, chatterbox, qwen3-tts.
  If invalid, tell user: "Unknown backend '<name>'. Valid options: auto, kokoro, fish-speech, pocket-tts, chatterbox, qwen3-tts"
  If valid, set `backend = "<name>"` in `[core]`, tell user: "TTS backend set to <name>."
- When `speed <value>`: Set `speed = <value>` in `[tuning]` (clamped 0.5-2.0), tell user:
  "Speech speed set to <value>."
- When `max_sentences <value>`: Set `max_sentences = <value>` in `[tuning]` (clamped 1-10), tell user:
  "Max sentences set to <value>."
- When `fallback on`: Set `fallback = true` in `[tuning]`, tell user:
  "Backend fallback enabled."
- When `fallback off`: Set `fallback = false` in `[tuning]`, tell user:
  "Backend fallback disabled."
- When `clone <path>`: Resolve to absolute path, validate the file exists and is .wav/.mp3/.ogg.
  If invalid: "File not found or unsupported format (use .wav, .mp3, or .ogg)"
  If valid: Set `clone_audio = "<abspath>"` in `[style]`, tell user:
  "Voice cloning reference set to <filename>. Will be used with Chatterbox backend."
- When `clone` (no path): Set `clone_audio = ""` in `[style]`, tell user:
  "Voice cloning reference cleared."
- When `history`: Run `bash uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/replay.py" --list` and show the output.
- When `replay` or `replay <N>`: Run `bash uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/replay.py" <N>` (default 0).
- When `save on`: Set `save_history = true` in `[features]`, tell user:
  "Voice history saving enabled."
- When `save off`: Set `save_history = false` in `[features]`, tell user:
  "Voice history saving disabled."
- When `conversational on`: Set `conversational = true` in `[features]`, tell user:
  "Conversational mode enabled. Claude will speak periodic updates during tool chains."
- When `conversational off`: Set `conversational = false` in `[features]`, tell user:
  "Conversational mode disabled."
- When `interval <seconds>`: Set `update_interval = <seconds>` in `[features]` (clamped 5-300), tell user:
  "Conversational update interval set to <seconds>s."
- When `debug on`: Set `debug = true` in `[core]`, tell user:
  "Debug logging enabled. [cc-vox] diagnostics will appear in stderr."
- When `debug off`: Set `debug = false` in `[core]`, tell user:
  "Debug logging disabled."

To update the config, import and call `update_voice_config()` from `hooks/voice_common.py`.
It returns `(config, warnings)` — always show any warnings to the user:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "hooks"))
from voice_common import update_voice_config
config, warnings = update_voice_config(enabled=True, voice="af_bella")
# If warnings is non-empty, tell the user about each clamped/corrected value
```

Create the config file if it doesn't exist (default voice: af_heart, backend: auto).
