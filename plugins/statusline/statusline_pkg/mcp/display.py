"""MCP display: name formatting, categorization, line building."""

from ..theme import (
    RST, BOLD, OVERLAY0, SURFACE2, SUBTEXT0,
    LAVENDER, PINK, SKY, rgb,
)
from .types import MCPEntry


def mcp_short(name, source):
    """Clean up MCP name for display."""
    if name.startswith("plugin:") or name.startswith("plugin_"):
        parts = name.replace("_", ":").split(":")
        return parts[-1] if len(parts) >= 3 else parts[-1]
    if name.startswith("claude.ai "):
        return name[10:]
    if name.startswith("claude_ai_"):
        return name[10:].replace("_", " ")
    return name


def _categorize(entries):
    """Split entries into cloud, plugin, and other lists."""
    cloud = []
    plugins = []
    others = []
    for e in entries:
        if e.source == "cloud" or "claude" in e.name.lower():
            cloud.append(e)
        elif e.source == "plugin" or e.name.startswith("plugin"):
            plugins.append(e)
        else:
            others.append(e)
    return cloud, plugins, others


def build_mcp_line(mcp_entries, docker_servers, docker_entry, accent):
    """Build the MCP status line string."""
    other_entries = [e for e in mcp_entries if not (e.name == "MCP_DOCKER" and docker_servers)]
    cloud, plugins, others = _categorize(other_entries)

    count = len(mcp_entries) + len(docker_servers)
    parts = []
    sep_char = f"{SURFACE2},{RST} "

    if cloud:
        names = sep_char.join(f"{LAVENDER}{mcp_short(e.name, e.source)}{RST}" for e in cloud)
        parts.append(names)

    if plugins:
        names = sep_char.join(f"{PINK}{mcp_short(e.name, e.source)}{RST}" for e in plugins)
        parts.append(names)

    if others:
        names = sep_char.join(f"{SUBTEXT0}{mcp_short(e.name, e.source)}{RST}" for e in others)
        parts.append(names)

    if docker_entry and docker_servers:
        parts.append(f"{SKY}Docker{RST}{OVERLAY0}({len(docker_servers)}){RST}")

    sep = f"  {SURFACE2}\u2502{RST}  "
    return f" {accent} {OVERLAY0}mcp{RST} {OVERLAY0}{count}{RST}  {sep.join(parts)}"
