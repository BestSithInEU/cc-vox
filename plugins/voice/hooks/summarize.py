"""
Headless Claude summarization fallback.

Calls `claude -p` to generate a 1-2 sentence spoken summary when no
📢 marker was embedded by the model.
"""

from __future__ import annotations

import json
import subprocess


def summarize_with_claude(
    conversation: list[tuple[str, str]],
    custom_prompt: str = "",
    max_sentences: int = 2,
) -> str | None:
    """Use headless Claude to generate a 1-sentence summary."""
    if not conversation:
        return None

    last_assistant_msg = None
    past_conv: list[tuple[str, str]] = []

    for i in range(len(conversation) - 1, -1, -1):
        role, text = conversation[i]
        if role == "assistant":
            last_assistant_msg = text
            past_conv = conversation[:i]
            break

    if not last_assistant_msg:
        return None

    past_lines = []
    for role, text in past_conv:
        if len(text) > 500:
            text = text[:500] + "..."
        past_lines.append(f"[{role}]: {text}")

    past_text = "\n\n".join(past_lines) if past_lines else "(no prior context)"

    if len(past_text) > 3000:
        past_text = past_text[-3000:]
    if len(last_assistant_msg) > 2000:
        last_assistant_msg = last_assistant_msg[:2000] + "..."

    base_instruction = (
        "You are the assistant who just wrote that message. Give a brief SPOKEN "
        "voice update to the user. Match the user's tone - if they're casual or "
        "use colorful language, mirror that. IMPORTANT: Keep it to "
        f"{max_sentences} sentence{'s' if max_sentences != 1 else ''} max, "
        "and NEVER longer than the original message. Since this will be "
        "spoken aloud, avoid file paths, UUIDs, hashes, or technical identifiers "
        "- use natural language instead (e.g., 'the config file' not "
        "'/Users/foo/bar/config.json'). What would you say?"
    )

    if custom_prompt:
        base_instruction += f"\n\nAdditional instruction: {custom_prompt}"

    prompt = f"""PAST CONVERSATION (for tone context):
{past_text}

---

YOUR LAST MESSAGE:
{last_assistant_msg}

---

{base_instruction}"""

    try:
        result = subprocess.run(
            [
                "claude", "-p",
                "--output-format", "json",
                "--no-session-persistence",
                "--setting-sources", "",
                prompt,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                summary = data.get("result", "").strip()
            elif isinstance(data, list):
                # Content block array: [{"type": "text", "text": "..."}]
                parts = [
                    block.get("text", "")
                    for block in data
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                summary = " ".join(parts).strip()
            else:
                summary = str(data).strip()
            return summary if summary else None

    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    return None
