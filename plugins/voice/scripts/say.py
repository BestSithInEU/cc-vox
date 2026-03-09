"""
say - Multi-backend TTS script for Claude Code voice plugin

Supports 5 backends with auto-detection and retry-with-fallback:
  1. Qwen3-TTS (GPU, Docker :32614) - highest priority
  2. Fish Speech (GPU, Docker :32611) - best quality if GPU is idle
  3. Chatterbox (GPU, Docker :32613) - voice cloning
  4. Kokoro (CPU, Docker :32612) - great quality, always-available
  5. pocket-tts (CPU, uvx :8000) - lightweight zero-setup fallback

Usage: say [--voice <voice>] [--session <id>] [--speed <n>] [--volume <n>] [--debug] <text>
"""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

# ── Resolve imports from hooks/ ──────────────────────────────────────────────

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from tts import generate_with_fallback, select_backend
from tts._debug import enable as enable_debug, log
from tts._history import save_clip
from tts._playback import PlaybackLock, play_audio, play_audio_streaming
from tts._session_state import SessionState, cleanup_stale_sessions
from tts._state_file import write_tts_state
from voice_common import get_voice_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-backend TTS for Claude Code voice plugin")
    parser.add_argument("--voice", default="", help="Voice name")
    parser.add_argument("--session", default="", help="Session ID for stop hook")
    parser.add_argument("--speed", type=float, default=0.0,
                        help="Speech speed 0.5-2.0 (kokoro only, 0=use config)")
    parser.add_argument("--volume", type=float, default=0.0,
                        help="Playback volume 0.0-2.0 (0=use config)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging to stderr")
    parser.add_argument("text", nargs="+", help="Text to speak")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = " ".join(args.text)

    if not text.strip():
        print("Error: No text provided", file=sys.stderr)
        return 1

    config = get_voice_config()
    if not config.enabled:
        return 0

    if args.debug or config.debug:
        enable_debug()

    voice = args.voice or config.voice
    speed = args.speed if args.speed > 0 else config.speed
    volume = args.volume if args.volume > 0 else config.volume

    log(f"Config: voice={voice}, speed={speed}, volume={volume}, "
        f"backend={config.backend}, fallback={config.fallback}")

    cleanup_stale_sessions()

    session = SessionState(args.session)
    lock = PlaybackLock()

    def on_signal(signum, frame):
        lock.release()
        session.cleanup()
        sys.exit(1)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    if not lock.acquire():
        print("Error: Timeout waiting for audio lock after 30s", file=sys.stderr)
        session.mark_failed()
        return 1

    try:
        # Try streaming path first for lower latency
        backend = select_backend(
            config.backend, config.fallback, session_id=args.session,
        )
        if backend is None:
            print(
                "Error: No TTS service available. "
                "Check Docker ('docker ps') or try 'TTS_BACKEND=pocket-tts'.",
                file=sys.stderr,
            )
            session.mark_failed()
            return 1

        print(f"TTS backend: {backend.name}", file=sys.stderr)
        write_tts_state(backend.name, voice)

        if backend.supports_streaming:
            log(f"Using streaming pipeline with {backend.name}")
            collected: list[bytes] = []

            def _saving_chunks():
                for chunk in backend.generate_streaming(text, voice, speed):
                    collected.append(chunk)
                    yield chunk

            play_audio_streaming(_saving_chunks(), volume)

            if config.save_history and collected:
                save_clip(b"".join(collected), text, backend.name, voice)
        else:
            result = generate_with_fallback(
                text, voice, speed, config.backend, config.fallback,
                session_id=args.session,
            )
            if result is None:
                print("Error: TTS generation failed.", file=sys.stderr)
                session.mark_failed()
                return 1

            audio, backend_name = result
            if not audio:
                print("Error: Generated audio is empty", file=sys.stderr)
                session.mark_failed()
                return 1

            play_audio(audio, volume)

            if config.save_history:
                save_clip(audio, text, backend_name, voice)

        session.mark_done()
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        session.mark_failed()
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
