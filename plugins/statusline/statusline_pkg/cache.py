"""Shared JSON file cache utility."""

import json
import pathlib
import datetime


def read_json_cache(path, max_age=300):
    """Read a JSON cache file if it exists and is younger than max_age seconds.
    Returns the parsed dict or None."""
    try:
        p = pathlib.Path(path)
        if p.exists():
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            age = utc_now.timestamp() - p.stat().st_mtime
            if age < max_age:
                return json.loads(p.read_text())
    except Exception:
        pass
    return None


def write_json_cache(path, data):
    """Write data as JSON to a cache file, creating parent dirs."""
    try:
        p = pathlib.Path(path)
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(data))
    except Exception:
        pass
