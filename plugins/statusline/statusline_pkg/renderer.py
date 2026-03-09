"""Output composition: builds the 5-line statusline display."""

from .theme import (
    RST, BOLD, DOT, PIPE,
    MAUVE, BLUE, TEAL, YELLOW, RED, GREEN, PEACH, TEXT,
    OVERLAY0, SUBTEXT0, SURFACE2,
    rgb, fmt_tok, fmt_cost, cost_color, palette_rgb,
)
from .bars import get_bar
from .config import BAR_W


def _model_color(model_name):
    mn = model_name.lower()
    if "opus" in mn:
        return MAUVE
    if "sonnet" in mn:
        return BLUE
    if "haiku" in mn:
        return TEAL
    return TEXT


def _accent(used_pct):
    """Dynamic accent color based on context pressure."""
    if used_pct < 50:
        c = palette_rgb("accent_healthy")
    elif used_pct < 80:
        c = palette_rgb("accent_warm")
    else:
        c = palette_rgb("accent_hot")
    return f"{rgb(*c)}\u2590{RST}"


def render_identity(git, stdin_data, now_istanbul, accent):
    """Line 1: cwd, branch, status, commits, model, session cost, time."""
    branch_part = f" {MAUVE}{git.branch}{RST}" if git.branch else ""
    status_dot = f"{GREEN}\u25cf{RST}" if git.is_clean else f"{PEACH}\u25cf{RST}"
    model_c = _model_color(stdin_data.model_name)

    return (
        f" {accent} {BLUE}{git.display_cwd}{RST}{branch_part}"
        f" {status_dot}"
        f"{DOT}{OVERLAY0}commits{RST} {TEXT}{BOLD}{git.commits_today}{RST}"
        f"{DOT}{model_c}{stdin_data.model_name}{RST}"
        f"{DOT}{YELLOW}{BOLD}{fmt_cost(stdin_data.session_cost)}{RST}"
        f"{DOT}{OVERLAY0}{now_istanbul:%H:%M}{RST}"
    )


def render_costs(costs, accent):
    """Line 2: cost dashboard — day, 7d, 30d, repo, live."""
    cc = cost_color
    return (
        f" {accent} {OVERLAY0}day{RST} {cc(costs.day)}{BOLD}{fmt_cost(costs.day)}{RST}"
        f"{DOT}{OVERLAY0}7d{RST} {cc(costs.week)}{fmt_cost(costs.week)}{RST}"
        f"{DOT}{OVERLAY0}30d{RST} {cc(costs.month)}{fmt_cost(costs.month)}{RST}"
        f"{DOT}{OVERLAY0}repo{RST} {cc(costs.repo)}{fmt_cost(costs.repo)}{RST}"
        f"{PIPE}{OVERLAY0}live{RST} {PEACH}{fmt_cost(costs.live)}{RST}"
    )


def render_context(stdin_data, accent):
    """Line 3: context window bar and token counts."""
    ctx_bar, ctx_c = get_bar("context", stdin_data.used_pct, BAR_W)
    return (
        f" {accent} {OVERLAY0}ctx {RST} {ctx_bar}"
        f" {ctx_c}{BOLD}{stdin_data.used_pct}%{RST}"
        f"{DOT}{TEXT}{BOLD}{fmt_tok(stdin_data.ctx_tokens)}{RST} {OVERLAY0}tokens{RST}"
        f"{DOT}{SUBTEXT0}{fmt_tok(stdin_data.total_in)}{OVERLAY0}\u2191{RST}"
        f" {SUBTEXT0}{fmt_tok(stdin_data.total_out)}{OVERLAY0}\u2193{RST}"
    )


def render_windows(win5, week, accent):
    """Line 4: 5-hour + weekly usage bars."""
    win_bar, win_c = get_bar("window", win5.pct, BAR_W)
    wk_bar, wk_c = get_bar("weekly", week.pct, BAR_W)

    # 5hr utilization display
    if win5.utilization is not None:
        u5 = int(win5.utilization)
        u5c = GREEN if u5 < 50 else (YELLOW if u5 < 80 else RED)
        u5_str = f" {u5c}{BOLD}{u5}%{RST}"
    else:
        time_left = f"{win5.remaining_h}h{win5.remaining_m}m" if win5.remaining_h > 0 else f"{win5.remaining_m}m"
        u5_str = f" {win_c}{BOLD}{time_left}{RST}"

    # Week utilization display
    wk_str = f" {wk_c}{BOLD}{week.pct}%{RST}" if week.utilization is not None else ""

    r5_str = f" {OVERLAY0}rst{RST} {GREEN}{win5.reset_str}{RST}" if win5.reset_str else ""
    rw_str = f" {OVERLAY0}rst{RST} {GREEN}{week.reset_display}{RST}" if week.reset_display else ""

    return (
        f" {accent} {OVERLAY0}5hr {RST} {win_bar}{u5_str}{r5_str}"
        f"{PIPE}{OVERLAY0}week{RST} {wk_bar}{wk_str}{rw_str}"
    )


def _render_voice(accent):
    """Optional voice line: show TTS backend and voice if active."""
    try:
        import json
        import tempfile
        import time
        from pathlib import Path

        state_file = Path(tempfile.gettempdir()) / "cc-vox-state.json"
        raw = state_file.read_text(encoding="utf-8")
        state = json.loads(raw)
        if time.time() - state.get("ts", 0) > 300:  # 5 min TTL
            return None
        backend = state.get("backend", "?")
        voice = state.get("voice", "?")
        status = state.get("status", "ok")
        status_c = GREEN if status == "ok" else RED
        return (
            f" {accent} {OVERLAY0}voice{RST}"
            f" {status_c}\u25cf{RST}"
            f" {TEXT}{backend}{RST}"
            f"{DOT}{SUBTEXT0}{voice}{RST}"
        )
    except (OSError, ValueError, KeyError):
        return None


def compose_output(stdin_data, git, costs, win5, week, now_istanbul, mcp_entries, docker_servers):
    """Compose all output lines and return as a single string."""
    accent = _accent(stdin_data.used_pct)

    lines = [
        render_identity(git, stdin_data, now_istanbul, accent),
        render_costs(costs, accent),
        render_context(stdin_data, accent),
        render_windows(win5, week, accent),
    ]

    # MCP line
    if mcp_entries or docker_servers:
        from .mcp.display import build_mcp_line
        docker_entry = next((e for e in mcp_entries if e.name == "MCP_DOCKER" and docker_servers), None)
        lines.append(build_mcp_line(mcp_entries, docker_servers, docker_entry, accent))

    # Voice line (only shown when TTS state is fresh)
    voice_line = _render_voice(accent)
    if voice_line:
        lines.append(voice_line)

    return "\n".join(lines)
