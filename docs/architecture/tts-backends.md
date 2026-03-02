# TTS Backend Architecture

The TTS system follows a plugin architecture with a Protocol-based contract. Each backend is a self-contained module with its own detection, startup, and audio generation logic.

## The Protocol

Every backend implements the `TTSBackend` Protocol defined in `hooks/tts/_protocol.py`:

```python
@runtime_checkable
class TTSBackend(Protocol):
    name: str       # "kokoro", "fish-speech", "chatterbox", "qwen3-tts", "pocket-tts"
    priority: int   # lower = tried first in auto mode

    def is_available(self) -> bool: ...
    def ensure_running(self) -> bool: ...
    def generate(self, text: str, voice: str, speed: float) -> bytes: ...
```

| Method | Purpose |
|:-------|:--------|
| `is_available()` | Check if the service is reachable right now |
| `ensure_running()` | Start the service if possible, then check availability |
| `generate()` | Produce WAV audio bytes from text |

**Conventions:**

- `voice` is always passed in canonical Kokoro form — backends map internally
- `speed` may be ignored by backends that don't support it
- `generate()` returns raw WAV bytes
- GPU checks are internal to the backend (not in generic selection logic)

## The Registry

`hooks/tts/__init__.py` maintains the backend registry:

```python
def _registry() -> dict[str, type[TTSBackend]]:
    from .chatterbox import ChatterboxBackend
    from .fish_speech import FishSpeechBackend
    from .kokoro import KokoroBackend
    from .pocket_tts import PocketTTSBackend
    from .qwen3_tts import Qwen3TTSBackend

    return {
        "kokoro": KokoroBackend,
        "fish-speech": FishSpeechBackend,
        "pocket-tts": PocketTTSBackend,
        "chatterbox": ChatterboxBackend,
        "qwen3-tts": Qwen3TTSBackend,
    }
```

### `select_backend(backend_pref, fallback)`

1. If `backend_pref` is a specific backend name, try it
2. If unavailable and `fallback=True`, fall through to auto
3. In auto mode, sort all backends by `priority` (ascending) and return the first that `ensure_running()` returns `True`
4. Returns `None` if nothing is reachable

## Backend Implementations

### KokoroBackend (`kokoro.py`)

| Property | Value |
|:---------|:------|
| Priority | 20 |
| API | OpenAI-compatible `/v1/audio/speech` |
| Health check | `GET /v1/models` |
| Voice support | Full catalog via `to_kokoro()` |
| Speed support | Yes (payload field) |

### FishSpeechBackend (`fish_speech.py`)

| Property | Value |
|:---------|:------|
| Priority | 10 |
| API | Gradio SSE (`/gradio_api/call/partial`) |
| Health check | `GET /config` + GPU utilization < threshold |
| Voice support | Ignored (uses own model) |
| Speed support | Ignored |

The `is_available()` method checks both service reachability **and** GPU utilization via `nvidia-smi`.

### ChatterboxBackend (`chatterbox.py`)

| Property | Value |
|:---------|:------|
| Priority | 12 |
| API | OpenAI-compatible `/v1/audio/speech` |
| Health check | `GET /voices` |
| Voice support | Ignored (uses voice cloning with default voice) |
| Speed support | Ignored |

Chatterbox uses a voice cloning model — it always sends `"voice": "default"` regardless of the configured voice name.

### Qwen3TTSBackend (`qwen3_tts.py`)

| Property | Value |
|:---------|:------|
| Priority | 14 |
| API | FastAPI REST `GET /base_tts/` |
| Health check | `GET /openapi.json` |
| Voice support | Ignored (uses default English voice) |
| Speed support | Yes (query parameter) |

Qwen3-TTS uses the default English voice from the model and passes the `speed` parameter via query string.

### PocketTTSBackend (`pocket_tts.py`)

| Property | Value |
|:---------|:------|
| Priority | 30 |
| API | Multipart form-data `/tts` |
| Health check | `GET /health` |
| Voice support | Aliased via `to_alias()` |
| Speed support | Ignored |
| Auto-start | Yes — spawns `uvx pocket-tts serve` |

`ensure_running()` calls `_start()` which launches the server via `uvx` and polls `/health` for up to 60 seconds.

## Playback System

### `play_audio(audio_data: bytes)`

Audio player priority:

1. `ffplay` — streaming via stdin pipe (preferred, lowest latency)
2. `afplay` — macOS native player (temp file)
3. `aplay` — ALSA player on Linux (temp file)
4. `paplay` — PulseAudio player on Linux (temp file)

### `PlaybackLock`

File-based mutex at `/tmp/voice-playback.lock` using `fcntl.flock`:

- Prevents overlapping audio from concurrent responses
- 30-second acquire timeout
- Supports context manager (`with PlaybackLock(): ...`)
- Writes PID for diagnostics

### `SessionState`

Sentinel files in `/tmp/` for stop-hook integration:

| File | Meaning |
|:-----|:--------|
| `/tmp/voice-{id}-running` | TTS is generating/playing |
| `/tmp/voice-{id}-done` | TTS completed successfully |
| `/tmp/voice-{id}-failed` | TTS failed |
