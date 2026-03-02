# Installation

## Prerequisites

- **Claude Code** (CLI) installed and working
- **Python 3.11+** (for hook scripts)
- **Audio output** — speakers, headphones, or system audio

No external Python packages are required. cc-vox uses only the standard library.

## Install the Plugin

=== "Marketplace (recommended)"

    ```bash
    claude plugin marketplace add BestSithInEU/cc-vox
    claude plugin install voice
    ```

=== "From source"

    ```bash
    git clone https://github.com/BestSithInEU/cc-vox.git
    cd cc-vox
    claude --plugin-dir .
    ```

=== "Local development"

    ```bash
    claude --plugin-dir ~/Documents/Projects/cc-vox
    ```

## Pick a Backend

You need at least one TTS backend running. cc-vox supports three, in priority order:

| Backend | Type | Setup | Quality |
|:--------|:-----|:------|:--------|
| Fish Speech | GPU (Docker) | `docker run` + NVIDIA GPU | Best |
| **Kokoro** :material-star: | CPU (Docker) | `docker run` | Great |
| pocket-tts | CPU (uvx) | **Zero setup** — auto-starts | Good |

### Option A: Zero Setup (pocket-tts)

No action needed. pocket-tts auto-starts via `uvx` when cc-vox first tries to speak. The [pocket-tts model](https://huggingface.co/kyutai/pocket-tts) downloads automatically on first use.

!!! tip
    If you have `uv` installed, pocket-tts will download and start automatically on first use. You can pre-download the model with `hf download kyutai/pocket-tts`.

### Option B: Kokoro (Recommended)

```bash
docker run -d --name kokoro \
  -p 32612:8880 \
  ghcr.io/remsky/kokoro-fastapi-cpu:latest
```

!!! tip
    Kokoro offers the best balance of quality and simplicity. One command, CPU-only, great results.

### Option C: Fish Speech (Best Quality)

```bash
# Download the model
hf download fishaudio/openaudio-s1-mini --local-dir checkpoints/openaudio-s1-mini

# Start the container
docker run -d --name fish-speech \
  --gpus all \
  -p 32611:7860 \
  -v ./checkpoints:/app/checkpoints \
  fishaudio/fish-speech:latest
```

!!! important
    Requires an NVIDIA GPU with Docker GPU support configured. The [openaudio-s1-mini](https://huggingface.co/fishaudio/openaudio-s1-mini) model is licensed CC-BY-NC-SA-4.0.

## Verify

```bash
# Start Claude Code
claude

# In the session, type anything — you should hear audio after the response
# Or test the TTS script directly:
./scripts/say "Hello from cc-vox"
```

## Next Steps

- [Configure voice, speed, and backend](configuration.md)
- [Explore available voices](../usage/voices.md)
- [Learn how the pipeline works](../usage/how-it-works.md)
