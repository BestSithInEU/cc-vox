"""MCP registry: orchestrates detection from all sources, deduplicates."""

from .types import MCPEntry, MCPContext
from .sources import ALL_SOURCES


def _mcp_norm(name):
    """Normalize MCP name for deduplication."""
    return name.replace("_", " ").replace(":", " ").replace(".", " ").lower()


def detect_all_mcp(cwd, mcp_data):
    """Detect all MCP servers from all sources.
    Returns (entries: list[MCPEntry], docker_servers: list[str])."""
    runtime_servers = mcp_data.get("servers", [])
    ctx = MCPContext(cwd=cwd, runtime_servers=runtime_servers)

    # Run all source detectors (they populate ctx.config_entries as side effect)
    for source in ALL_SOURCES:
        source.detect(ctx)

    # Build unified list with status from runtime
    entries = []
    if runtime_servers:
        runtime_norms = set()
        for s in runtime_servers:
            name = s.get("name", "?")
            status = "on" if s.get("status") == "connected" else "off"
            source = ctx.config_entries.get(name, "runtime")
            entries.append(MCPEntry(name, status, source))
            runtime_norms.add(_mcp_norm(name))
        # Add config entries not covered by runtime
        for name, source in ctx.config_entries.items():
            if _mcp_norm(name) not in runtime_norms:
                entries.append(MCPEntry(name, "cfg", source))
    else:
        for name, source in ctx.config_entries.items():
            entries.append(MCPEntry(name, "cfg", source))

    return entries, ctx.docker_servers
