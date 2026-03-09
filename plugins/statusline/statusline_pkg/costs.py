"""JSONL cost scanning and project directory resolution."""

import json
import os
import pathlib
from dataclasses import dataclass
from .config import PRICING, DEFAULT_PRICING


@dataclass
class CostData:
    session: float = 0
    day: float = 0
    week: float = 0
    month: float = 0
    repo: float = 0
    live: float = 0


def calc_entry_cost(usage, model_id):
    """Calculate cost for a single usage entry."""
    p = PRICING.get(model_id, DEFAULT_PRICING)
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    cw = usage.get("cache_creation_input_tokens", 0)
    cr = usage.get("cache_read_input_tokens", 0)
    return (inp * p[0] + out * p[1] + cw * p[2] + cr * p[3]) / 1_000_000


def scan_jsonl_costs(project_dirs, boundaries):
    """Scan JSONL files in project dirs and sum costs per boundary."""
    costs = {k: 0.0 for k in boundaries}
    costs["repo"] = 0.0
    for pdir in project_dirs:
        if not pdir.is_dir():
            continue
        for jsonl in pdir.rglob("*.jsonl"):
            try:
                for line in open(jsonl, encoding="utf-8", errors="ignore"):
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("type") != "assistant":
                        continue
                    msg = entry.get("message", {})
                    usage = msg.get("usage")
                    if not usage:
                        continue
                    model_id = msg.get("model", "")
                    if model_id == "<synthetic>":
                        continue
                    ts = entry.get("timestamp", "")
                    c = calc_entry_cost(usage, model_id)
                    costs["repo"] += c
                    for name, cutoff in boundaries.items():
                        if ts >= cutoff:
                            costs[name] += c
            except Exception:
                continue
    return costs


def _encode_cwd(cwd):
    """Encode a cwd path for matching against project directory names."""
    encoded = cwd.replace("\\", "-").replace("/", "-").replace(":", "").lstrip("-")
    if cwd.startswith("/"):
        alt = cwd.lstrip("/").replace("/", "-")
    else:
        alt = encoded
    return encoded, alt


def resolve_project_dirs(cwd):
    """Resolve current and all project directories."""
    projects_root = pathlib.Path.home() / ".claude" / "projects"
    encoded, alt = _encode_cwd(cwd)

    current_dirs = []
    all_dirs = []
    if projects_root.is_dir():
        for d in projects_root.iterdir():
            if d.is_dir():
                all_dirs.append(d)
                if d.name == encoded or d.name == alt:
                    current_dirs.append(d)

    return current_dirs, all_dirs


def compute_all_costs(cwd, boundaries, session_cost=0):
    """Compute all cost data: day, week, month, repo, live."""
    current_dirs, all_dirs = resolve_project_dirs(cwd)
    repo_dirs = current_dirs if current_dirs else all_dirs[:1]

    cost_data = scan_jsonl_costs(all_dirs, boundaries)
    repo_cost_data = scan_jsonl_costs(repo_dirs, {"_": "1970-01-01T00:00:00+00:00"})

    return CostData(
        session=session_cost,
        day=cost_data.get("day", 0),
        week=cost_data.get("7day", 0),
        month=cost_data.get("30day", 0),
        repo=repo_cost_data["repo"],
        live=cost_data.get("live", 0),
    )
