"""MCP source detectors — ABC + concrete implementations (OCP)."""

import json
import pathlib
from abc import ABC, abstractmethod
from .types import MCPEntry, MCPContext


class MCPSource(ABC):
    """Abstract base for MCP server detection sources."""

    @abstractmethod
    def detect(self, ctx: MCPContext) -> list[MCPEntry]:
        ...


class GlobalConfigSource(MCPSource):
    """Detect MCP servers from global config files."""

    _PATHS = [
        pathlib.Path.home() / ".claude.json",
        pathlib.Path.home() / ".claude" / ".mcp.json",
        pathlib.Path.home() / ".claude" / "settings.json",
        pathlib.Path.home() / ".claude" / "settings.local.json",
    ]

    def detect(self, ctx: MCPContext) -> list[MCPEntry]:
        entries = []
        for config_path in self._PATHS:
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                for name in cfg.get("mcpServers", {}):
                    if name not in ctx.config_entries:
                        ctx.config_entries[name] = "global"
                        entries.append(MCPEntry(name, "cfg", "global"))
            except Exception:
                pass
        return entries


class ProjectConfigSource(MCPSource):
    """Detect MCP servers from project-level .mcp.json files."""

    def detect(self, ctx: MCPContext) -> list[MCPEntry]:
        entries = []
        cwd_path = pathlib.Path(ctx.cwd)
        for check_dir in [cwd_path] + list(cwd_path.parents)[:3]:
            for fname in (".mcp.json", "mcp.json"):
                try:
                    cfg = json.loads((check_dir / fname).read_text(encoding="utf-8"))
                    for name in cfg.get("mcpServers", {}):
                        if name not in ctx.config_entries:
                            ctx.config_entries[name] = "project"
                            entries.append(MCPEntry(name, "cfg", "project"))
                except Exception:
                    pass
        return entries


class PluginSource(MCPSource):
    """Detect MCP servers from enabled plugins."""

    def detect(self, ctx: MCPContext) -> list[MCPEntry]:
        entries = []
        try:
            settings_cfg = json.loads(
                (pathlib.Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8")
            )
            enabled_plugins = settings_cfg.get("enabledPlugins", {})
            plugin_cache_dir = pathlib.Path.home() / ".claude" / "plugins" / "cache"

            for plugin_id, enabled in enabled_plugins.items():
                if not enabled:
                    continue
                plugin_name = plugin_id.split("@")[0]
                for mcp_json in plugin_cache_dir.rglob(f"{plugin_name}/*/.mcp.json"):
                    try:
                        mcfg = json.loads(mcp_json.read_text(encoding="utf-8"))
                        servers = mcfg.get("mcpServers", {})
                        if servers:
                            srv_items = servers.keys()
                        else:
                            srv_items = [
                                k for k, v in mcfg.items()
                                if isinstance(v, dict) and "command" in v
                            ]
                        for srv_name in srv_items:
                            display = f"plugin:{plugin_name}:{srv_name}"
                            if display not in ctx.config_entries:
                                ctx.config_entries[display] = "plugin"
                                entries.append(MCPEntry(display, "cfg", "plugin"))
                    except Exception:
                        pass
                    break  # Only first match per plugin
        except Exception:
            pass
        return entries


class CloudSource(MCPSource):
    """Detect cloud MCPs (Gmail, Google Calendar) via OAuth credentials."""

    def detect(self, ctx: MCPContext) -> list[MCPEntry]:
        entries = []
        try:
            cred_path = pathlib.Path.home() / ".claude" / ".credentials.json"
            if cred_path.exists():
                creds = json.loads(cred_path.read_text(encoding="utf-8"))
                oauth = creds.get("claudeAiOauth", {})
                if oauth.get("accessToken") and "user:mcp_servers" in oauth.get("scopes", []):
                    for cm in ["Gmail", "Google Calendar"]:
                        key = f"claude.ai {cm}"
                        if key not in ctx.config_entries:
                            ctx.config_entries[key] = "cloud"
                            entries.append(MCPEntry(key, "cfg", "cloud"))
        except Exception:
            pass
        return entries


class DockerSource(MCPSource):
    """Detect Docker MCP gateway sub-servers (cached 5 min)."""

    def detect(self, ctx: MCPContext) -> list[MCPEntry]:
        from ..cache import read_json_cache, write_json_cache

        cache_path = pathlib.Path.home() / ".claude" / "usage-tracking" / "docker_mcp.json"
        cached = read_json_cache(cache_path)

        if cached:
            ctx.docker_servers = cached.get("servers", [])
            ctx.docker_reachable = cached.get("reachable", False)
            return []

        if "MCP_DOCKER" not in ctx.config_entries:
            return []

        try:
            import subprocess
            r = subprocess.run(
                ["docker", "mcp", "server", "list"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                ctx.docker_reachable = True
                skip_words = {"NAME", "Tip:", "---", "MCP"}
                for line in r.stdout.splitlines()[2:]:
                    parts = line.split()
                    if parts and parts[0] not in skip_words and not parts[0].startswith("-"):
                        ctx.docker_servers.append(parts[0])
                write_json_cache(cache_path, {
                    "servers": ctx.docker_servers, "reachable": True,
                })
        except Exception:
            pass
        return []


# ── Factory: all sources in detection order ──────────────────────────
ALL_SOURCES = [
    GlobalConfigSource(),
    ProjectConfigSource(),
    PluginSource(),
    CloudSource(),
    DockerSource(),
]
