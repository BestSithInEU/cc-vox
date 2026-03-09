"""5-hour and 7-day usage window calculations."""

import json
import datetime
import pathlib
from dataclasses import dataclass
from .config import ISTANBUL_TZ
from .time_utils import format_reset_time


@dataclass
class WindowState:
    pct: int = 0
    remaining_h: int = 0
    remaining_m: int = 0
    remaining_s: int = 0
    reset_str: str = ""
    window_start_ts: float = 0
    utilization: object = None  # None means not from API


@dataclass
class WeekState:
    pct: int = 0
    utilization: object = None
    reset_display: str = ""


def compute_five_hour(five_hour, utc_now, transcript_path=""):
    """Compute 5-hour window state from API data or local fallback."""
    resets_at_str = five_hour.get("resets_at", "")
    utilization = five_hour.get("utilization")

    state = WindowState(utilization=utilization)

    if resets_at_str:
        try:
            reset_dt = datetime.datetime.fromisoformat(resets_at_str.replace("Z", "+00:00"))
            diff = reset_dt - utc_now
            state.remaining_s = max(0, int(diff.total_seconds()))
            state.remaining_h = state.remaining_s // 3600
            state.remaining_m = (state.remaining_s % 3600) // 60
            state.reset_str = format_reset_time(reset_dt, ISTANBUL_TZ)
            state.window_start_ts = (reset_dt - datetime.timedelta(hours=5)).timestamp()
        except Exception:
            pass
    else:
        _fallback_five_hour(state, utc_now, transcript_path)

    if utilization is not None:
        state.pct = min(100, int(utilization))
    elif state.remaining_s > 0:
        elapsed_s = 5 * 3600 - state.remaining_s
        state.pct = min(100, int(elapsed_s / (5 * 3600) * 100))

    return state


def _fallback_five_hour(state, utc_now, transcript_path):
    """Fallback: track 5-hour window locally via file."""
    tracking_dir = pathlib.Path.home() / ".claude" / "usage-tracking"
    tracking_dir.mkdir(exist_ok=True)
    now_ts = utc_now.timestamp()

    session_start_ts = now_ts
    if transcript_path:
        try:
            tp = pathlib.Path(transcript_path)
            if tp.exists():
                try:
                    session_start_ts = tp.stat().st_birthtime
                except AttributeError:
                    session_start_ts = tp.stat().st_ctime
        except Exception:
            pass

    window_file = tracking_dir / "5h_window.json"
    window_start_ts = session_start_ts
    try:
        wd = json.loads(window_file.read_text())
        saved = float(wd.get("start", 0))
        if 0 < now_ts - saved < 5 * 3600:
            window_start_ts = min(saved, session_start_ts)
    except Exception:
        pass

    window_file.write_text(json.dumps({"start": str(window_start_ts)}))
    elapsed = now_ts - window_start_ts
    state.remaining_s = max(0, int(5 * 3600 - elapsed))
    state.remaining_h = state.remaining_s // 3600
    state.remaining_m = (state.remaining_s % 3600) // 60
    state.window_start_ts = window_start_ts

    reset_utc = datetime.datetime.fromtimestamp(
        window_start_ts, tz=datetime.timezone.utc
    ) + datetime.timedelta(hours=5)
    state.reset_str = format_reset_time(reset_utc, ISTANBUL_TZ)


def compute_seven_day(seven_day):
    """Compute 7-day window state from API data."""
    state = WeekState(utilization=seven_day.get("utilization"))

    if state.utilization is not None:
        state.pct = min(100, int(state.utilization))

    resets_str = seven_day.get("resets_at", "")
    if resets_str:
        try:
            reset_dt = datetime.datetime.fromisoformat(resets_str.replace("Z", "+00:00"))
            reset_ist = reset_dt.astimezone(ISTANBUL_TZ)
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            wday = day_names[reset_ist.weekday()]
            wh = reset_ist.hour % 12 or 12
            wap = "am" if reset_ist.hour < 12 else "pm"
            state.reset_display = f"{wday} {wh}{wap}"
        except Exception:
            pass

    return state
