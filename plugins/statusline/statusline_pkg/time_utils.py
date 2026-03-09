"""Time utilities: Istanbul timezone, boundaries, reset formatting."""

import datetime
from .config import ISTANBUL_TZ


def get_times():
    """Return (utc_now, now_istanbul) tuple."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    now_istanbul = utc_now.astimezone(ISTANBUL_TZ)
    return utc_now, now_istanbul


def format_reset_time(dt, tz=None):
    """Format a datetime as '3:05pm' style 12-hour string."""
    if tz:
        dt = dt.astimezone(tz)
    h = dt.hour % 12 or 12
    ap = "am" if dt.hour < 12 else "pm"
    return f"{h}:{dt.minute:02d}{ap}"


def compute_boundaries(now_istanbul, window_start_ts=None):
    """Compute ISO timestamp boundaries for cost scanning."""
    today_midnight = now_istanbul.replace(hour=0, minute=0, second=0, microsecond=0)
    today_utc = today_midnight.astimezone(datetime.timezone.utc).isoformat()
    d7_utc = (today_midnight - datetime.timedelta(days=7)).astimezone(datetime.timezone.utc).isoformat()
    d30_utc = (today_midnight - datetime.timedelta(days=30)).astimezone(datetime.timezone.utc).isoformat()

    boundaries = {"day": today_utc, "7day": d7_utc, "30day": d30_utc}
    if window_start_ts:
        boundaries["live"] = datetime.datetime.fromtimestamp(
            window_start_ts, tz=datetime.timezone.utc
        ).isoformat()
    return boundaries
