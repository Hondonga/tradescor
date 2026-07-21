"""ICT kill zone and session helpers."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")

KILL_ZONES = [
    ("Asian Session", time(20, 0), time(0, 0), False),
    ("London Kill Zone", time(2, 0), time(5, 0), True),
    ("New York Kill Zone", time(7, 0), time(10, 0), True),
    ("London Close", time(10, 0), time(12, 0), False),
]


def analyze_kill_zone(now: datetime | None = None) -> dict[str, object]:
    """Return current session context using New York time."""
    current = now.astimezone(NEW_YORK) if now else datetime.now(NEW_YORK)
    session = "Outside Session"
    entry_allowed = False

    for name, start, end, allowed in KILL_ZONES:
        if _inside_window(current, start, end):
            session = name
            entry_allowed = allowed
            break

    next_name, next_start = _next_zone_start(current)
    remaining = next_start - current

    return {
        "timezone": "America/New_York",
        "current_time": current.strftime("%H:%M:%S"),
        "current_session": session,
        "next_kill_zone": next_name,
        "time_remaining": _format_remaining(remaining),
        "entry_allowed": entry_allowed,
    }


def _inside_window(current: datetime, start: time, end: time) -> bool:
    start_dt = current.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
    end_dt = current.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)

    if end <= start:
        return current >= start_dt or current < end_dt

    return start_dt <= current < end_dt


def _next_zone_start(current: datetime) -> tuple[str, datetime]:
    upcoming = []

    for name, start, _end, _allowed in KILL_ZONES:
        candidate = current.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
        if candidate <= current:
            candidate += timedelta(days=1)
        upcoming.append((candidate, name))

    candidate, name = min(upcoming, key=lambda item: item[0])
    return name, candidate


def _format_remaining(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m"
