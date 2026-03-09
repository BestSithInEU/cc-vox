"""Entry point: reads stdin JSON, orchestrates modules, prints output."""

import os

from .data_input import parse_stdin
from .time_utils import get_times, compute_boundaries
from .oauth import fetch_oauth_usage
from .windows import compute_five_hour, compute_seven_day
from .costs import compute_all_costs
from .git_info import get_git_info
from .mcp import detect_all_mcp
from .renderer import compose_output


def main():
    # 1. Parse stdin
    data = parse_stdin()
    cwd = data.cwd or os.getcwd()

    # 2. Time
    utc_now, now_istanbul = get_times()

    # 3. OAuth usage (cached)
    oauth_usage = fetch_oauth_usage()
    five_hour = data.five_hour
    if oauth_usage.get("five_hour"):
        five_hour = oauth_usage["five_hour"]
    seven_day = oauth_usage.get("seven_day", {})

    # 4. Usage windows
    win5 = compute_five_hour(five_hour, utc_now, data.transcript_path)
    week = compute_seven_day(seven_day)

    # 5. Cost scanning
    boundaries = compute_boundaries(now_istanbul, win5.window_start_ts)
    costs = compute_all_costs(cwd, boundaries, data.session_cost)

    # 6. Git info
    git = get_git_info(cwd)

    # 7. MCP detection
    mcp_entries, docker_servers = detect_all_mcp(cwd, data.mcp)

    # 8. Render and print
    output = compose_output(data, git, costs, win5, week, now_istanbul, mcp_entries, docker_servers)
    print(output)


if __name__ == "__main__":
    main()
