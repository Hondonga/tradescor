"""ICT session intelligence based on New York time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class SessionDefinition:
    name: str
    start: time
    end: time
    entry_allowed: bool
    phase: str
    expected_behavior: str


SESSIONS = [
    SessionDefinition(
        name="Asian Session",
        start=time(20, 0),
        end=time(0, 0),
        entry_allowed=False,
        phase="Range Formation",
        expected_behavior="Identify Asia range high, range low, and resting liquidity pools.",
    ),
    SessionDefinition(
        name="London Kill Zone",
        start=time(2, 0),
        end=time(5, 0),
        entry_allowed=True,
        phase="Manipulation",
        expected_behavior="Looking for manipulation, liquidity sweep, and CHOCH.",
    ),
    SessionDefinition(
        name="New York Kill Zone",
        start=time(7, 0),
        end=time(10, 0),
        entry_allowed=True,
        phase="Distribution",
        expected_behavior="Looking for continuation, distribution, and entry confirmation.",
    ),
    SessionDefinition(
        name="London Close",
        start=time(10, 0),
        end=time(12, 0),
        entry_allowed=False,
        phase="Profit Taking",
        expected_behavior="Looking for continuation and profit-taking behavior.",
    ),
]

KILL_ZONE_NAMES = {"London Kill Zone", "New York Kill Zone"}

OUTSIDE_SESSION = SessionDefinition(
    name="Outside Trading Hours",
    start=time(0, 0),
    end=time(0, 0),
    entry_allowed=False,
    phase="Context Only",
    expected_behavior="Continue updating market context. New valid entries are blocked by the session filter.",
)


def get_session_context(
    now: datetime | None = None,
    entry_filter_enabled: bool = True,
) -> dict[str, object]:
    """Return current ICT session context using America/New_York time."""
    current = _analysis_time(now)
    active_definition, start_dt, end_dt = _active_session(current)

    if active_definition is None:
        session = OUTSIDE_SESSION
        next_session, next_start = _next_session_start(current)
        active = False
        status = "INACTIVE"
        remaining = next_start - current
        progress = 0
        start_text = "--"
        end_text = "--"
        next_start_text = next_start.strftime("%I:%M %p %Z").lstrip("0")
    else:
        session = active_definition
        next_session, next_start = _next_session_start(end_dt)
        active = True
        status = "ACTIVE"
        remaining = end_dt - current
        progress = _progress_percent(current, start_dt, end_dt)
        start_text = start_dt.strftime("%H:%M:%S")
        end_text = end_dt.strftime("%H:%M:%S")
        next_start_text = next_start.strftime("%I:%M %p %Z").lstrip("0")

    entry_allowed = bool(session.entry_allowed if entry_filter_enabled else True)
    kill_zone_active = bool(active and session.name in KILL_ZONE_NAMES)
    market_open = _is_forex_market_open(current)

    if active_definition is None:
        next_transition_name = next_session.name
        next_transition_time = next_start
    else:
        next_transition_name = "Outside Trading Hours"
        next_transition_time = end_dt

    transition_delta = next_transition_time - current
    transition_text = next_transition_time.strftime("%I:%M %p %Z").lstrip("0")

    return {
        "name": session.name,
        "session": session.name,
        "status": status,
        "active": active,
        "entry_allowed": entry_allowed,
        "entry_filter_enabled": entry_filter_enabled,
        "kill_zone_active": kill_zone_active,
        "kill_zone_status": "ACTIVE" if kill_zone_active else "INACTIVE",
        "market_open": market_open,
        "market_status": "OPEN" if market_open else "CLOSED",
        "time_remaining": _format_hms(remaining),
        "time_remaining_label": _format_label(remaining),
        "next_session": next_session.name,
        "phase": session.phase,
        "expected_behavior": session.expected_behavior,
        "current_time": current.strftime("%H:%M:%S"),
        "current_time_label": current.strftime("%I:%M:%S %p %Z").lstrip("0"),
        "timezone": "America/New_York",
        "timezone_abbreviation": current.tzname() or "ET",
        "progress": progress,
        "session_start": start_text,
        "session_end": end_text,
        "next_session_time": next_start.isoformat(),
        "next_session_label": f"{next_session.name} at {next_start_text}",
        "next_transition": next_transition_name,
        "next_transition_time": next_transition_time.isoformat(),
        "next_transition_label": f"{next_transition_name} at {transition_text}",
        "time_until_next_session": _format_hms(transition_delta),
        "time_until_next_session_label": _format_label(transition_delta),
        "timeline": _session_timeline(current),
        "evaluated_at": current.isoformat(),
    }


def _is_forex_market_open(current: datetime) -> bool:
    """Return the standard retail forex week status in New York time."""
    weekday = current.weekday()
    current_time = current.time()

    if weekday == 5:
        return False
    if weekday == 6:
        return current_time >= time(17, 0)
    if weekday == 4:
        return current_time < time(17, 0)
    return True


def get_session_status(
    timestamp: object,
    entry_filter_enabled: bool = True,
    asset_type: str = "forex",
    symbol: str = "",
) -> dict[str, object]:
    """Evaluate an asset-aware market and liquidity context."""
    context = get_session_context(
        now=_coerce_datetime(timestamp),
        entry_filter_enabled=entry_filter_enabled,
    )
    normalized = str(asset_type or "forex").lower()
    if normalized == "crypto":
        current = _coerce_datetime(timestamp).astimezone(NEW_YORK)
        liquidity = _crypto_liquidity_window(current)
        context.update(
            {
                "name": liquidity,
                "session": liquidity,
                "liquidity_window": liquidity,
                "market_open": True,
                "market_status": "OPEN_24_7",
                "market_status_label": "24/7 Open",
                "entry_allowed": True,
                "entry_filter_enabled": False,
                "phase": "Liquidity Context",
                "expected_behavior": "Use the liquidity window as context; crypto remains continuously tradable.",
            }
        )
    elif normalized in {"index", "equity"}:
        current = _coerce_datetime(timestamp).astimezone(NEW_YORK)
        weekday_open = current.weekday() < 5
        cash_open = weekday_open and time(9, 30) <= current.time() < time(16, 0)
        context.update(
            {
                "market_open": cash_open,
                "market_status": "OPEN" if cash_open else "CLOSED",
                "market_status_label": "Cash Market Open" if cash_open else "Cash Market Closed",
                "entry_allowed": bool(cash_open and context.get("entry_allowed")),
                "instrument": symbol or None,
                "schedule_type": "exchange_cash" if normalized == "index" else "exchange_extended_hours",
                "exchange_timezone": "America/New_York",
                "session_segment": "regular" if cash_open else "premarket" if weekday_open and time(4, 0) <= current.time() < time(9, 30) else "after_hours" if weekday_open and time(16, 0) <= current.time() < time(20, 0) else "closed",
            }
        )
    elif normalized == "commodity":
        current = _coerce_datetime(timestamp).astimezone(NEW_YORK)
        market_open = _is_forex_market_open(current)
        context.update(
            {
                "market_open": market_open,
                "market_status": "OPEN" if market_open else "CLOSED",
                "market_status_label": "Commodity Market Open" if market_open else "Commodity Market Closed",
                "entry_allowed": bool(market_open and context.get("entry_allowed")),
            }
        )
    elif normalized == "forex":
        # Phase 4 §4/§5 fix: every other gated asset type (index/equity/
        # commodity, above) explicitly ANDs market_open into entry_allowed;
        # forex was the one branch that never did, so entry_allowed could
        # read True purely because the wall-clock time-of-day matched a
        # kill-zone window even while the weekend/Friday-close closure made
        # market_open False -- i.e. the market could appear tradable while
        # actually closed. Session logic still only ever narrows
        # entry_allowed, never creates it -- this does not add a new
        # reason to allow entry, only a missing reason to block it.
        context["entry_allowed"] = bool(context.get("market_open") and context.get("entry_allowed"))
        context["market_status_label"] = "Open" if context.get("market_open") else "Closed"
    else:
        context["market_status_label"] = "Open" if context.get("market_open") else "Closed"
    context["asset_type"] = normalized
    return context


def _crypto_liquidity_window(current: datetime) -> str:
    hour = current.hour
    if 19 <= hour or hour < 2:
        return "Asian Liquidity"
    if 2 <= hour < 7:
        return "London Liquidity"
    if 7 <= hour < 17:
        return "New York Liquidity"
    return "Weekend Liquidity" if current.weekday() >= 5 else "Off-Peak Liquidity"


def _analysis_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(NEW_YORK)
    return _coerce_datetime(value).astimezone(NEW_YORK)


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif hasattr(value, "to_pydatetime"):
        result = value.to_pydatetime()
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


def _active_session(
    current: datetime,
) -> tuple[SessionDefinition | None, datetime | None, datetime | None]:
    for session in SESSIONS:
        start_dt, end_dt = _window_for(current, session)
        if start_dt <= current < end_dt:
            return session, start_dt, end_dt

    return None, None, None


def _window_for(
    current: datetime,
    session: SessionDefinition,
) -> tuple[datetime, datetime]:
    start_dt = current.replace(
        hour=session.start.hour,
        minute=session.start.minute,
        second=0,
        microsecond=0,
    )
    end_dt = current.replace(
        hour=session.end.hour,
        minute=session.end.minute,
        second=0,
        microsecond=0,
    )

    if session.end <= session.start:
        if current.time() < session.end:
            start_dt -= timedelta(days=1)
        else:
            end_dt += timedelta(days=1)

    return start_dt, end_dt


def _next_session_start(current: datetime) -> tuple[SessionDefinition, datetime]:
    upcoming = []

    for session in SESSIONS:
        start_dt = current.replace(
            hour=session.start.hour,
            minute=session.start.minute,
            second=0,
            microsecond=0,
        )

        if start_dt <= current:
            start_dt += timedelta(days=1)

        upcoming.append((start_dt, session))

    start_dt, session = min(upcoming, key=lambda item: item[0])
    return session, start_dt


def _session_timeline(current: datetime) -> list[dict[str, object]]:
    rows = []
    active_session, _active_start, _active_end = _active_session(current)

    for session in SESSIONS:
        start_dt, end_dt = _window_for(current, session)

        if end_dt <= current:
            state = "completed"
        elif active_session and session.name == active_session.name:
            state = "current"
        else:
            state = "upcoming"

        rows.append(
            {
                "name": session.name,
                "start": start_dt.strftime("%H:%M"),
                "end": end_dt.strftime("%H:%M"),
                "state": state,
            }
        )

    return rows


def _progress_percent(current: datetime, start: datetime, end: datetime) -> int:
    total_seconds = max(int((end - start).total_seconds()), 1)
    elapsed_seconds = max(int((current - start).total_seconds()), 0)
    return min(round((elapsed_seconds / total_seconds) * 100), 100)


def _format_hms(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_label(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"
