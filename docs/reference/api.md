# Python API Reference

## `tts` Package

### `tts.select_backend(backend_pref, fallback)`

Select the best available TTS backend.

```python
from tts import select_backend

backend = select_backend("auto", fallback=True)
if backend:
    audio = backend.generate("Hello world", "af_heart", 1.0)
```

**Parameters:**

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `backend_pref` | `str` | `"auto"` or a specific backend name |
| `fallback` | `bool` | Fall through to auto if forced backend is down |

**Returns:** `TTSBackend | None` — a backend instance, or `None` if nothing is reachable.

---

### `tts.available_backend_names()`

Return all valid backend names including `"auto"`.

```python
from tts import available_backend_names

print(available_backend_names())
# ('auto', 'kokoro', 'fish-speech', 'pocket-tts')
```

**Returns:** `tuple[str, ...]`

---

## `tts._protocol.TTSBackend`

The Protocol that all backends implement.

```python
from tts._protocol import TTSBackend

class MyBackend:
    name: str = "my-backend"
    priority: int = 25

    def is_available(self) -> bool: ...
    def ensure_running(self) -> bool: ...
    def generate(self, text: str, voice: str, speed: float) -> bytes: ...
```

| Attribute/Method | Type | Description |
|:-----------------|:-----|:------------|
| `name` | `str` | Backend identifier (e.g., `"kokoro"`) |
| `priority` | `int` | Auto-selection order (lower = first) |
| `is_available()` | `-> bool` | Check if service is reachable |
| `ensure_running()` | `-> bool` | Start service if possible, then check |
| `generate(text, voice, speed)` | `-> bytes` | Generate WAV audio |

---

## `tts.voices`

### `VOICE_CATALOG`

Complete voice catalog — single source of truth.

```python
from tts.voices import VOICE_CATALOG

for name, info in VOICE_CATALOG.items():
    print(f"{name}: {info}")
# af_heart: {'alias': 'alba', 'gender': 'F', 'accent': 'American'}
# ...
```

**Type:** `dict[str, dict[str, str]]`

---

### `tts.voices.to_kokoro(voice)`

Normalize any voice identifier to its canonical Kokoro form.

```python
from tts.voices import to_kokoro

to_kokoro("alba")      # "af_heart"
to_kokoro("af_bella")  # "af_bella"
to_kokoro("unknown")   # "af_heart" (default)
```

**Parameters:** `voice: str` — Kokoro name, pocket-tts alias, or anything.
**Returns:** `str` — canonical Kokoro voice name.

---

### `tts.voices.to_alias(voice)`

Convert a voice identifier to its pocket-tts alias.

```python
from tts.voices import to_alias

to_alias("af_heart")  # "alba"
to_alias("alba")      # "alba"
to_alias("bm_george") # "bm_george" (no alias)
```

**Parameters:** `voice: str`
**Returns:** `str` — pocket-tts alias, or Kokoro name if no alias exists.

---

## `tts._playback`

### `play_audio(audio_data)`

Play WAV audio data using the best available player.

```python
from tts._playback import play_audio

play_audio(wav_bytes)
```

**Player priority:** `ffplay` (streaming) -> `afplay` (macOS) -> `aplay` (Linux) -> `paplay` (PulseAudio)

---

### `PlaybackLock`

File-based mutex to prevent overlapping audio.

```python
from tts._playback import PlaybackLock

# Context manager
with PlaybackLock(max_wait=30):
    play_audio(audio)

# Manual acquire/release
lock = PlaybackLock()
if lock.acquire():
    try:
        play_audio(audio)
    finally:
        lock.release()
```

---

## `tts._session_state.SessionState`

Manages `/tmp` sentinel files for stop-hook integration.

```python
from tts._session_state import SessionState

session = SessionState("abc123")
# Creates /tmp/voice-abc123-running

session.mark_done()    # Creates -done, removes -running
session.mark_failed()  # Creates -failed, removes -running
session.cleanup()      # Removes -running
```

---

## `voice_common`

### `get_voice_config()`

Read voice config from `~/.claude/cc-vox.toml`.

```python
from voice_common import get_voice_config

config = get_voice_config()
print(config.voice, config.backend, config.speed)
```

**Returns:** `VoiceConfig` dataclass.

---

### `update_voice_config(**kwargs)`

Read current config, apply updates, write back.

```python
from voice_common import update_voice_config

config = update_voice_config(voice="af_bella", speed=1.3)
```

**Returns:** `VoiceConfig` — the updated config.

---

### `VoiceConfig`

```python
@dataclass
class VoiceConfig:
    enabled: bool = True
    voice: str = "af_heart"
    backend: str = "auto"
    speed: float = 1.0
    max_sentences: int = 2
    fallback: bool = True
    prompt: str = ""
    just_disabled: bool = False
```

---

## `session`

### `find_session_file(session_id)`

Locate a Claude Code session JSONL file.

```python
from session import find_session_file

path = find_session_file("abc123")  # Path or None
```

---

### `get_last_assistant_message(session_file)`

Extract the last assistant message with race-condition retry logic.

```python
from session import get_last_assistant_message

text = get_last_assistant_message(path, max_retries=10, retry_delay=0.5)
```

---

### `extract_voice_marker(text)`

Extract the `📢` voice summary from a message.

```python
from session import extract_voice_marker

marker = extract_voice_marker("Some text\n📢 Done refactoring!\n")
# "Done refactoring!"
```

---

## `summarize`

### `summarize_with_claude(conversation, custom_prompt)`

Use headless Claude to generate a 1-2 sentence spoken summary.

```python
from summarize import summarize_with_claude

summary = summarize_with_claude(
    [("user", "fix the bug"), ("assistant", "I fixed the null pointer...")],
    custom_prompt="be brief",
)
```

**Returns:** `str | None`
