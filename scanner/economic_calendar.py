"""Local economic calendar and high-impact news restriction helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")
RESTRICTION_MINUTES = 15


def analyze_economic_news(
    symbol: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return high-impact news status from a local JSON calendar file."""
    current = now.astimezone(NEW_YORK) if now else datetime.now(NEW_YORK)
    currencies = _symbol_currencies(symbol)
    events = _load_events()
    relevant_events = [
        event for event in events if event["currency"] in currencies and event["impact"] == "High"
    ]
    upcoming = [_event_payload(event, current) for event in relevant_events if event["time"] >= current - timedelta(minutes=RESTRICTION_MINUTES)]
    upcoming = sorted(upcoming, key=lambda event: event["release_timestamp"])[:6]
    restricted_event = next((event for event in upcoming if event["restriction_active"]), None)

    if restricted_event:
        status = "Restricted"
        warning = f"Avoid new entries around {restricted_event['currency']} high-impact news: {restricted_event['title']}."
    elif upcoming:
        status = "Clear"
        warning = "No high-impact news restriction is active."
    else:
        status = "No configured events"
        warning = "News filter unavailable — no live calendar configured."

    return {
        "enabled": bool(events),
        "status": status,
        "restriction_active": restricted_event is not None,
        "restriction_window_minutes": RESTRICTION_MINUTES,
        "warning": warning,
        "upcoming_events": upcoming,
        "currencies": sorted(currencies),
        "evaluated_at": current.isoformat(),
    }


def get_news_status(timestamp: object, symbol: str) -> dict[str, object]:
    """Evaluate local news restrictions at an explicit analysis timestamp."""
    if isinstance(timestamp, datetime):
        current = timestamp
    elif hasattr(timestamp, "to_pydatetime"):
        current = timestamp.to_pydatetime()
    else:
        current = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=NEW_YORK)
    return analyze_economic_news(symbol, now=current)


def _load_events() -> list[dict[str, object]]:
    path = Path(os.getenv("ECONOMIC_CALENDAR_FILE", "data/economic_calendar.json"))

    if not path.exists():
        return []

    try:
        raw_events = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []

    events = []
    for event in raw_events:
        parsed = _parse_event(event)
        if parsed:
            events.append(parsed)

    return events


def _parse_event(event: dict[str, object]) -> dict[str, object] | None:
    title = str(event.get("title", "")).strip()
    currency = str(event.get("currency", "")).strip().upper()
    impact = str(event.get("impact", "")).strip().title()
    time_text = str(event.get("time", "")).strip()

    if not title or not currency or not time_text:
        return None

    try:
        timestamp = datetime.fromisoformat(time_text)
    except ValueError:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=NEW_YORK)
    else:
        timestamp = timestamp.astimezone(NEW_YORK)

    return {
        "title": title,
        "currency": currency,
        "impact": impact,
        "time": timestamp,
    }


def _event_payload(event: dict[str, object], current: datetime) -> dict[str, object]:
    release_time = event["time"]
    delta = release_time - current
    restriction_start = release_time - timedelta(minutes=RESTRICTION_MINUTES)
    restriction_end = release_time + timedelta(minutes=RESTRICTION_MINUTES)

    return {
        "title": event["title"],
        "currency": event["currency"],
        "impact": event["impact"],
        "release_time": release_time.strftime("%Y-%m-%d %H:%M:%S"),
        "release_timestamp": int(release_time.timestamp()),
        "time_until_release": _format_delta(delta),
        "restriction_window": f"{restriction_start.strftime('%H:%M')} - {restriction_end.strftime('%H:%M')} NY",
        "restriction_active": restriction_start <= current <= restriction_end,
    }


def _symbol_currencies(symbol: str) -> set[str]:
    parts = [part.strip().upper() for part in symbol.split("/") if part.strip()]

    if not parts:
        return set()

    currencies = set(parts)

    if symbol.upper().endswith("/USD"):
        currencies.add("USD")

    return currencies


def _format_delta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    prefix = "" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _seconds = divmod(remainder, 60)

    if hours:
        return f"{prefix}{hours}h {minutes}m"

    return f"{prefix}{minutes}m"
