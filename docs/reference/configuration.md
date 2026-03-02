# Configuration Reference

## Config File Location

```
~/.claude/cc-vox.toml
```

Created automatically on first run. Editable with any text editor or via [slash commands](../usage/slash-commands.md).

## Full Default Config

```toml
[core]
enabled = true
voice = "af_heart"       # see voices below
backend = "auto"         # auto | kokoro | fish-speech | pocket-tts | chatterbox | qwen3-tts

[tuning]
speed = 1.0              # 0.5-2.0 (kokoro only)
max_words = 25           # max spoken summary length
fallback = true          # try other backends when forced one is down

[style]
prompt = ""

# ── Available Voices ──────────────────────────────
# af_heart (default)  F  American   alias: alba
# af_bella            F  American   alias: azure
# af_nicole           F  American   alias: fantine
# af_sarah            F  American   alias: cosette
# af_sky              F  American   alias: eponine
# am_adam             M  American   alias: marius
# am_michael          M  American   alias: jean
# bf_emma             F  British    alias: azelma
# bm_george           M  British
```

## Settings

### `[core]`

#### `enabled`

:   **Type:** `bool` | **Default:** `true`

    Enable or disable voice feedback globally. When disabled, all hooks become no-ops and the `say` script exits immediately.

    ```toml
    enabled = false
    ```

#### `voice`

:   **Type:** `string` | **Default:** `"af_heart"`

    Voice name for TTS. Accepts both Kokoro names (e.g., `af_bella`) and pocket-tts aliases (e.g., `azure`). See [Voices](../usage/voices.md) for the full catalog.

    ```toml
    voice = "am_adam"
    ```

#### `backend`

:   **Type:** `string` | **Default:** `"auto"`
    **Valid values:** `auto`, `kokoro`, `fish-speech`, `pocket-tts`, `chatterbox`, `qwen3-tts`

    TTS backend preference. In `auto` mode, cc-vox tries backends in priority order (Fish Speech -> Chatterbox -> Qwen3-TTS -> Kokoro -> pocket-tts).

    ```toml
    backend = "kokoro"
    ```

### `[tuning]`

#### `speed`

:   **Type:** `float` | **Default:** `1.0` | **Range:** `0.5` -- `2.0`

    Speech speed multiplier. Only supported by the Kokoro backend; other backends ignore this value. Clamped to the valid range on read.

    ```toml
    speed = 1.3
    ```

#### `max_words`

:   **Type:** `int` | **Default:** `25` | **Range:** `5` -- `100`

    Maximum words in the spoken summary. Affects both the `📢` marker reminder and the truncation fallback.

    ```toml
    max_words = 40
    ```

#### `fallback`

:   **Type:** `bool` | **Default:** `true`

    When a forced backend is unavailable, fall through to auto-detection. If `false`, TTS fails silently when the forced backend is down.

    ```toml
    fallback = false
    ```

### `[style]`

#### `prompt`

:   **Type:** `string` | **Default:** `""`

    Custom instruction for voice summary personality. Injected into the system prompt and the headless Claude fallback.

    ```toml
    prompt = "be upbeat and encouraging"
    ```

### `[internal]`

#### `just_disabled`

:   **Type:** `bool` | **Default:** `false`

    Internal flag set when the user runs `/voice:speak stop`. Consumed once by the UserPromptSubmit hook to inject a "voice disabled" message, then cleared. Not intended for manual editing.
