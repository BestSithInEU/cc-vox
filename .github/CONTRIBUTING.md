# Contributing to cc-vox

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/cc-vox.git
cd cc-vox
claude --plugin-dir .
```

No virtual environment or `pip install` needed — cc-vox uses only the Python standard library.

## Making Changes

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
3. **Make your changes** — follow existing code patterns
4. **Test** with at least one TTS backend running:
   ```bash
   ./scripts/say --voice af_heart "Testing my changes"
   ```
5. **Commit** using the [commit message convention](#commit-messages)
6. **Push** and open a Pull Request

## Commit Messages

We use a conventional format. Configure the template:

```bash
git config commit.template .gitmessage
```

Format: `<type>: <subject>`

| Type | Use for |
|:-----|:--------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Restructure without behavior change |
| `docs` | Documentation only |
| `style` | Formatting, whitespace |
| `test` | Adding or fixing tests |
| `chore` | Build, CI, dependencies |
| `perf` | Performance improvement |

Examples:
```
feat: add ElevenLabs TTS backend
fix: handle missing nvidia-smi gracefully
docs: add troubleshooting section for WSL
refactor: extract playback lock to separate module
```

## Code Style

- **Python 3.11+** — use modern syntax (`X | Y` unions, etc.)
- **Type hints** on all public function signatures
- **Docstrings** on all public functions and classes
- **No external dependencies** — stdlib only
- One responsibility per module, keep files focused

## Adding a TTS Backend

This is the most common contribution. See the
[Adding a Backend](https://BestSithInEU.github.io/cc-vox/development/adding-backends/)
guide for step-by-step instructions. TL;DR:

1. Create `hooks/tts/my_backend.py` implementing `TTSBackend`
2. Add one line to `_registry()` in `hooks/tts/__init__.py`

## Documentation

Docs use [Zensical](https://zensical.org/).

```bash
# Preview locally
zensical serve

# Build (strict mode catches broken links)
zensical build --strict
```

Source lives in `docs/`, config in `zensical.toml`.

## Questions?

Open an issue or start a discussion — happy to help!
