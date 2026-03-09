"""Git repository info: branch, status, commits."""

import os
import pathlib
from dataclasses import dataclass


@dataclass
class GitInfo:
    branch: str = ""
    is_clean: bool = True
    commits_today: str = "0"
    display_cwd: str = ""


def _run_git(args, cwd, default=""):
    """Run a git command and return stdout or default."""
    import subprocess
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=3,
            cwd=cwd if os.path.isdir(cwd) else None,
        )
        return r.stdout.strip() if r.returncode == 0 else default
    except Exception:
        return default


def _shorten_cwd(cwd):
    """Shorten cwd for display: ~/project/sub."""
    home = str(pathlib.Path.home())
    display = cwd.replace("\\", "/")
    home_unix = home.replace("\\", "/")
    if display.startswith(home_unix):
        display = "~" + display[len(home_unix):]
    parts = display.split("/")
    if len(parts) > 3:
        display = "~/" + "/".join(parts[-2:])
    return display


def get_git_info(cwd):
    """Gather git info for the given working directory."""
    branch = _run_git(["symbolic-ref", "--short", "HEAD"], cwd)
    if not branch:
        short_hash = _run_git(["rev-parse", "--short", "HEAD"], cwd)
        if short_hash:
            branch = f":{short_hash}"

    dirty = _run_git(["status", "--porcelain"], cwd)
    commits_raw = _run_git(["log", "--since=today 00:00", "--oneline"], cwd)
    commits_today = str(len(commits_raw.splitlines())) if commits_raw else "0"

    return GitInfo(
        branch=branch,
        is_clean=not dirty,
        commits_today=commits_today,
        display_cwd=_shorten_cwd(cwd),
    )
