# FAQ & Troubleshooting

## Troubleshooting

### No audio output

1. Check that voice is enabled:
   ```
   /voice:speak
   ```

2. Verify your TTS backend is running:
   ```bash
   # Kokoro
   curl -s http://localhost:32612/v1/models && echo " OK" || echo "Not running"

   # Fish Speech
   curl -s http://localhost:32611/config && echo " OK" || echo "Not running"

   # pocket-tts
   curl -s http://localhost:8000/health && echo " OK" || echo "Not running"
   ```

3. Check system audio output device

4. Try forcing a backend:
   ```
   /voice:speak backend pocket-tts
   ```

5. Test the say script directly:
   ```bash
   ./scripts/say "Testing audio output"
   ```

---

### Docker container won't start

```bash
# Check if port is already in use
lsof -i :32612  # Kokoro
lsof -i :32611  # Fish Speech

# Check Docker logs
docker logs kokoro
docker logs fish-speech

# Restart
docker restart kokoro
```

---

### Fish Speech is being skipped

cc-vox checks GPU utilization before using Fish Speech. If your GPU is busy (default >80%), it falls back to Kokoro or pocket-tts.

```bash
# Check current GPU usage
nvidia-smi

# Raise the threshold
export GPU_THRESHOLD=95
```

---

### Voice sounds wrong or uses wrong backend

```bash
# Force a specific backend
/voice:speak backend kokoro

# Check which backend is being used
TTS_BACKEND=kokoro ./scripts/say "Testing Kokoro directly"
```

---

### pocket-tts won't auto-start

pocket-tts requires `uv` (or `uvx`) to be installed:

```bash
# Check if uv is available
which uvx

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Check pocket-tts startup log
cat /tmp/pocket-tts-server.log
```

---

## FAQ

??? question "Does it work offline?"

    Yes — if you run Kokoro or Fish Speech locally via Docker, everything stays on your machine. pocket-tts also runs locally via `uvx`. The only network call is to the local TTS service.

    The headless Claude summarization fallback (Strategy 3) does require an active Claude API connection, but Strategies 1, 2, and 4 are fully local.

??? question "Can I add custom voices?"

    The voice list is currently fixed to the 9 voices that map cleanly across backends. Custom voice support depends on the backend — Fish Speech supports voice cloning natively.

    To add voices to the catalog, edit `hooks/tts/voices.py` and add entries to `VOICE_CATALOG`.

??? question "Does it slow down Claude?"

    No. TTS runs asynchronously after Claude finishes responding. The only overhead is a small system prompt injection (~50 tokens) to remind Claude to include a voice summary.

??? question "Can I use it with other AI coding tools?"

    cc-vox is built specifically for Claude Code's hook system. The `scripts/say` script can be used standalone for any TTS needs, but the automatic hook integration is Claude Code-specific.

??? question "How do I uninstall?"

    ```bash
    claude plugin uninstall voice

    # Optionally remove Docker containers
    docker rm -f kokoro fish-speech

    # Optionally remove config
    rm ~/.claude/cc-vox.toml
    ```

??? question "Can I run multiple backends simultaneously?"

    Yes! In `auto` mode, cc-vox probes all backends and picks the best one each time. You can run Kokoro and Fish Speech simultaneously — cc-vox will prefer Fish Speech when GPU is idle and fall back to Kokoro when it's busy.
