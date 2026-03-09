"""Auto-configure statusline on SessionStart. Idempotent: skips if already set."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    plugin_root = Path(__file__).resolve().parent.parent
    settings_path = Path.home() / ".claude" / "settings.json"
    statusline_cmd = f"uv run python {plugin_root / 'statusline.py'}"

    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        data = json.loads(settings_path.read_text())
    else:
        data = {}

    if "statusLine" in data:
        return

    data["statusLine"] = {"type": "command", "command": statusline_cmd}
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Statusline auto-configured in {settings_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
