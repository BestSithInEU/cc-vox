# Contributing

Contributions are welcome! Here's how to get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/cc-vox.git
cd cc-vox

# Run Claude Code with the local plugin
claude --plugin-dir .
```

No virtual environment or `pip install` needed — cc-vox has zero external dependencies.

## Testing

### Manual Testing

```bash
# Test the say script directly
./scripts/say --voice af_heart "Hello, testing voice output"

# Force a specific backend
TTS_BACKEND=kokoro ./scripts/say "Testing Kokoro"

# Test with custom speed
./scripts/say --voice af_heart --speed 1.3 "Testing faster speech"

# Test backend selection
cd hooks
python3 -c "from tts import select_backend; b = select_backend('auto', True); print(b.name if b else 'none')"

# Test voice resolution
python3 -c "from tts.voices import to_kokoro, to_alias; print(to_kokoro('alba'), to_alias('af_heart'))"
```

### Verify Imports

```bash
cd hooks

# Protocol
python3 -c "from tts._protocol import TTSBackend; print('OK')"

# Voices
python3 -c "from tts.voices import VOICE_CATALOG; print(f'{len(VOICE_CATALOG)} voices')"

# Registry
python3 -c "from tts import available_backend_names; print(available_backend_names())"

# Session module
python3 -c "from session import find_session_file; print('OK')"

# Summarize module
python3 -c "from summarize import summarize_with_claude; print('OK')"
```

### End-to-End Test

1. Start at least one TTS backend (or let pocket-tts auto-start)
2. Run `claude --plugin-dir ~/path/to/cc-vox`
3. Send a message and verify:
    - Voice reminder appears in Claude's system context
    - Claude includes a `📢` summary
    - Audio plays after the response

## Code Style

- **Python 3.11+** — use modern syntax (`X | Y` unions, `match`, etc.)
- **Type hints** on all public function signatures
- **Docstrings** on all public functions and classes
- **No external dependencies** — stdlib only
- Keep files focused — one responsibility per module
- Follow existing patterns in the codebase

## Submitting Changes

1. **Fork** the repository
2. **Create a feature branch** (`git checkout -b feature/my-feature`)
3. **Make your changes** — follow the existing code style
4. **Test** with at least one TTS backend running
5. **Submit a PR** with a clear description

!!! tip "Adding a new backend?"
    See the dedicated [Adding a Backend](adding-backends.md) guide for step-by-step instructions.
