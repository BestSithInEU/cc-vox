"""MCP data types."""

from dataclasses import dataclass, field
from typing import NamedTuple


class MCPEntry(NamedTuple):
    name: str
    status: str  # "on", "off", "cfg"
    source: str  # "global", "project", "plugin", "cloud", "runtime"


@dataclass
class MCPContext:
    """Context needed by MCP source detectors."""
    cwd: str = ""
    runtime_servers: list = field(default_factory=list)
    config_entries: dict = field(default_factory=dict)  # name -> source
    docker_servers: list = field(default_factory=list)
    docker_reachable: bool = False
