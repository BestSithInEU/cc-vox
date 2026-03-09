"""Per-session backend cache to avoid repeated probing.

Stores the last successful backend name per session in a JSON temp file
with a TTL to prevent stale entries from persisting.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

CACHE_FILE = Path(tempfile.gettempdir()) / "cc-vox-backend-cache.json"
CACHE_TTL = 300  # 5 minutes


def _read_cache() -> dict:
    """Read the cache file, returning empty dict on any error."""
    try:
        raw = CACHE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return {}


def _write_cache(data: dict) -> None:
    """Write cache atomically."""
    tmp = CACHE_FILE.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(str(tmp), str(CACHE_FILE))
    except OSError:
        pass


def get_cached_backend(session_id: str) -> str | None:
    """Return cached backend name if fresh, else None."""
    if not session_id:
        return None
    cache = _read_cache()
    entry = cache.get(session_id)
    if not isinstance(entry, dict):
        return None
    ts = entry.get("ts", 0)
    if time.time() - ts > CACHE_TTL:
        return None
    name = entry.get("backend")
    return name if isinstance(name, str) else None


def set_cached_backend(session_id: str, backend_name: str) -> None:
    """Cache the successful backend for this session."""
    if not session_id:
        return
    cache = _read_cache()
    # Prune stale entries while we're at it
    now = time.time()
    cache = {
        k: v for k, v in cache.items()
        if isinstance(v, dict) and now - v.get("ts", 0) < CACHE_TTL
    }
    cache[session_id] = {"backend": backend_name, "ts": now}
    _write_cache(cache)


def invalidate_cache(session_id: str | None = None) -> None:
    """Clear cache for a session, or all sessions if None."""
    if session_id is None:
        try:
            CACHE_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        return

    cache = _read_cache()
    if session_id in cache:
        del cache[session_id]
        _write_cache(cache)
