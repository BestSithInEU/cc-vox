---
allowed-tools: Bash
---

Setup or remove the cc-vox statusline.

**Commands:**
- `/statusline:setup-statusline` — Install the statusline into `~/.claude/settings.json`
- `/statusline:setup-statusline uninstall` — Remove the statusline setting

**Auto-setup:**
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/statusline:setup-statusline"
```

**Uninstall:**
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/statusline:setup-statusline" --uninstall
```

**Manual setup:**

Add to `~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run python /path/to/cc-vox/plugins/statusline/statusline.py"
  }
}
```

Replace `/path/to/cc-vox` with the absolute path to your cc-vox clone.

**Behavior:**
- When no argument: Run the setup script to install the statusline.
- When `uninstall`: Run the setup script with `--uninstall` to remove the statusline setting.
