"""Parse stdin JSON into a structured data object."""

import json
import sys
import io
from dataclasses import dataclass, field


@dataclass
class StdinData:
    context_window: dict = field(default_factory=dict)
    cost: dict = field(default_factory=dict)
    model: dict = field(default_factory=dict)
    five_hour: dict = field(default_factory=dict)
    mcp: dict = field(default_factory=dict)
    cwd: str = ""
    transcript_path: str = ""
    raw: dict = field(default_factory=dict)

    # Derived convenience fields
    used_pct: float = 0
    ctx_size: int = 200_000
    total_in: int = 0
    total_out: int = 0
    session_cost: float = 0
    model_name: str = "Claude"
    ctx_tokens: int = 0


def parse_stdin():
    """Read JSON from stdin and return a StdinData instance."""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    data = json.load(sys.stdin)

    ctx = data.get("context_window", {})
    cost = data.get("cost", {})
    model = data.get("model", {})

    used_pct = ctx.get("used_percentage", 0) or 0
    ctx_size = ctx.get("context_window_size", 200_000) or 200_000

    return StdinData(
        context_window=ctx,
        cost=cost,
        model=model,
        five_hour=data.get("five_hour", {}),
        mcp=data.get("mcp", {}),
        cwd=data.get("cwd", ""),
        transcript_path=data.get("transcript_path", ""),
        raw=data,
        used_pct=used_pct,
        ctx_size=ctx_size,
        total_in=ctx.get("total_input_tokens", 0),
        total_out=ctx.get("total_output_tokens", 0),
        session_cost=cost.get("total_cost_usd", 0),
        model_name=model.get("display_name", "Claude"),
        ctx_tokens=int(ctx_size * used_pct / 100),
    )
