"""OAuth usage fetching with file cache."""

import json
import pathlib
from .cache import read_json_cache, write_json_cache

_CACHE_PATH = pathlib.Path.home() / ".claude" / "usage-tracking" / "oauth_usage.json"


def fetch_oauth_usage():
    """Fetch usage from OAuth API, using 5-minute cache. Returns dict."""
    cached = read_json_cache(_CACHE_PATH)
    if cached:
        return cached

    try:
        import urllib.request
        cred_path = pathlib.Path.home() / ".claude" / ".credentials.json"
        creds = json.loads(cred_path.read_text(encoding="utf-8"))
        token = creds["claudeAiOauth"]["accessToken"]
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "anthropic-beta": "oauth-2025-04-20",
            },
        )
        resp = urllib.request.urlopen(req, timeout=5)
        usage = json.loads(resp.read())
        write_json_cache(_CACHE_PATH, usage)
        return usage
    except Exception:
        return {}
