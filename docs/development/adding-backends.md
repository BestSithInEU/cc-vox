# Adding a New TTS Backend

cc-vox is designed so that adding a new backend requires **one new file** and **one registry line**. No existing code needs modification.

## Step 1: Create the Backend File

Create `hooks/tts/my_backend.py`:

```python
"""My Custom TTS backend — description of what it is."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .voices import to_kokoro  # if your backend uses Kokoro voice names

MY_PORT = int(os.environ.get("MY_BACKEND_PORT", "9999"))
MY_URL = f"http://localhost:{MY_PORT}"


class MyBackend:
    name = "my-backend"
    priority = 25  # between kokoro (20) and pocket-tts (30)

    def is_available(self) -> bool:
        """Check if the service is reachable."""
        try:
            req = urllib.request.Request(f"{MY_URL}/health", method="GET")
            resp = urllib.request.urlopen(req, timeout=1.0)
            return 200 <= resp.status < 300
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def ensure_running(self) -> bool:
        """Start the service if possible, then check availability.

        If your backend can't auto-start, just return is_available().
        """
        return self.is_available()

    def generate(self, text: str, voice: str, speed: float) -> bytes:
        """Generate WAV audio from text.

        Args:
            text: The text to speak
            voice: Voice name in canonical Kokoro form (e.g., "af_heart")
            speed: Speech speed (1.0 = normal). Ignore if unsupported.

        Returns:
            Raw WAV audio bytes.
        """
        voice = to_kokoro(voice)
        payload = json.dumps({"text": text, "voice": voice}).encode()
        req = urllib.request.Request(
            f"{MY_URL}/synthesize",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.read()
```

### Key Points

- **`name`**: Must be a unique, lowercase, hyphenated identifier
- **`priority`**: Lower values are tried first in auto mode. Current priorities: Fish Speech=10, Kokoro=20, pocket-tts=30
- **`is_available()`**: Should be fast (<1s timeout). Return `False` on any error
- **`ensure_running()`**: For auto-startable backends, start the service then poll for readiness
- **`generate()`**: Must return raw WAV bytes. The `voice` argument is always in Kokoro form — map internally if needed

## Step 2: Register the Backend

Edit `hooks/tts/__init__.py` — add one import and one dict entry:

```python
def _registry() -> dict[str, type[TTSBackend]]:
    from .fish_speech import FishSpeechBackend
    from .kokoro import KokoroBackend
    from .my_backend import MyBackend          # (1)!
    from .pocket_tts import PocketTTSBackend

    return {
        "kokoro": KokoroBackend,
        "fish-speech": FishSpeechBackend,
        "my-backend": MyBackend,               # (2)!
        "pocket-tts": PocketTTSBackend,
    }
```

1. Import your backend class
2. Add a registry entry — the key is the name used in config and slash commands

## Step 3: Done

That's it. Your backend is now:

- :material-check: Available in auto mode (sorted by priority)
- :material-check: Selectable via `/voice:speak backend my-backend`
- :material-check: Selectable via config `backend = "my-backend"`
- :material-check: Selectable via env `TTS_BACKEND=my-backend`
- :material-check: Listed in `available_backend_names()`
- :material-check: Validated in config parsing

## Checklist

- [ ] Backend file implements `name`, `priority`, `is_available()`, `ensure_running()`, `generate()`
- [ ] `generate()` returns raw WAV bytes
- [ ] `is_available()` has a short timeout (1s)
- [ ] Port is configurable via environment variable
- [ ] Registry entry added in `__init__.py`
- [ ] Tested with `./scripts/say --voice af_heart "test"` after forcing your backend
