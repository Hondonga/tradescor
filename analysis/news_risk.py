"""Market news-risk filter powered by live financial news and local events."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from providers import marketaux_provider


BLOCK_WINDOW_MINUTES = 30
WARNING_WINDOW_MINUTES = 120
LOCAL_CALENDAR_PATH = Path(__file__).resolve().parent.parent / "data" / "economic_calendar.json"


def analyze_news_risk(
    *,
    symbol: str,
    now: datetime,
    enabled: bool = True,
    provider_enabled: bool = True,
) -> dict[str, object]:
    """Return the highest-priority news risk for a symbol at a point in time."""
    current = _to_utc(now)
    if not enabled:
        return _unavailable("News risk filter is turned off.", source="Marketaux", blocks_entry=False, evaluated_at=current)
    if not provider_enabled:
        return _unavailable("Marketaux provider is disabled.", source="Marketaux", blocks_entry=False, evaluated_at=current)

    currencies = symbol_currencies(symbol)
    start = current - timedelta(minutes=WARNING_WINDOW_MINUTES)

    try:
        events = marketaux_provider.get_finance_news(
            symbol=symbol,
            published_after=start,
            published_before=current,
            limit=10,
        )
    except RuntimeError as error:
        local_result = _analyze_local_calendar(symbol=symbol, current=current)
        if local_result:
            return local_result
        return _unavailable(_provider_error_message(str(error)), blocks_entry=False, evaluated_at=current)

    if not events:
        return {
            "available": True,
            "source": "Marketaux",
            "risk_level": "low",
            "blocks_entry": False,
            "event": None,
            "currency": None,
            "impact": None,
            "event_time": None,
            "minutes_until": None,
            "message": "No recent Marketaux financial news found for this market in the last 120 minutes.",
            "currencies": sorted(currencies),
            "events_checked": 0,
            "upcoming_events": [],
            "status": "Low",
            "restriction_active": False,
            "warning": "No recent Marketaux financial news found for this market in the last 120 minutes.",
            "evaluated_at": current.isoformat().replace("+00:00", "Z"),
        }

    ranked = [_score_event(event, current) for event in events]
    ranked = [event for event in ranked if event]
    if not ranked:
        return _unavailable("Marketaux returned news, but none had usable publish times.", blocks_entry=False, evaluated_at=current)

    ranked.sort(key=lambda item: (item["rank"], abs(int(item["minutes_until"]))))
    selected = ranked[0]
    return _payload(selected, sorted(currencies), len(events), current)


def symbol_currencies(symbol: str) -> set[str]:
    """Return currencies affected by a pair-like symbol."""
    normalized = str(symbol or "").upper().replace(" ", "")
    parts = [part for part in normalized.split("/") if part]
    if len(parts) == 2 and all(len(part) == 3 for part in parts):
        return set(parts)
    if normalized.endswith("USD") or "/USD" in normalized:
        return {"USD"}
    return set()


def _score_event(event: dict[str, object], now: datetime) -> dict[str, object] | None:
    event_time = _parse_time(event.get("time"))
    if not event_time:
        return None
    minutes_until = int(round((event_time - now).total_seconds() / 60))
    abs_minutes = abs(minutes_until)
    impact = str(event.get("impact", "low")).lower()

    if impact == "high" and abs_minutes <= BLOCK_WINDOW_MINUTES:
        risk_level = "high"
        blocks = True
        rank = 0
    elif impact == "high" and 0 <= minutes_until <= WARNING_WINDOW_MINUTES:
        risk_level = "medium"
        blocks = False
        rank = 1
    elif impact == "high" and -WARNING_WINDOW_MINUTES <= minutes_until < 0:
        risk_level = "medium"
        blocks = False
        rank = 1
    elif impact == "medium" and abs_minutes <= BLOCK_WINDOW_MINUTES:
        risk_level = "medium"
        blocks = False
        rank = 2
    elif impact == "low":
        risk_level = "low"
        blocks = False
        rank = 4
    else:
        risk_level = "low"
        blocks = False
        rank = 5

    return {
        **event,
        "event_time_dt": event_time,
        "minutes_until": minutes_until,
        "risk_level": risk_level,
        "blocks_entry": blocks,
        "rank": rank,
    }


def _payload(
    event: dict[str, object],
    currencies: list[str],
    event_count: int,
    evaluated_at: datetime,
) -> dict[str, object]:
    name = str(event.get("event") or "Economic event")
    currency = str(event.get("currency") or "")
    impact = str(event.get("impact") or "low").lower()
    minutes_until = int(event["minutes_until"])
    risk_level = str(event["risk_level"])
    blocks = bool(event["blocks_entry"])
    timing = _timing_text(minutes_until)
    message = f"{impact.title()}-impact {currency} {name} {timing}."
    if str(event.get("source")) == "Marketaux":
        publisher = str(event.get("publisher") or "market news")
        sentiment = event.get("sentiment_score")
        sentiment_text = f" Sentiment {float(sentiment):+.2f}." if isinstance(sentiment, (int, float)) else ""
        message = f"{impact.title()}-impact Marketaux news from {publisher} {timing}: {name}.{sentiment_text}"
    if blocks:
        message = f"{message} Entry blocked."

    return {
        "available": True,
        "source": event.get("source", "Marketaux"),
        "risk_level": risk_level,
        "blocks_entry": blocks,
        "event": name,
        "currency": currency,
        "impact": impact,
        "event_time": str(event.get("time") or ""),
        "minutes_until": minutes_until,
        "message": message,
        "currencies": currencies,
        "sentiment_score": event.get("sentiment_score"),
        "publisher": event.get("publisher"),
        "url": event.get("url"),
        "events_checked": event_count,
        "status": risk_level.title(),
        "restriction_active": blocks,
        "warning": message,
        "upcoming_events": [_event_summary(event)],
        "evaluated_at": evaluated_at.isoformat().replace("+00:00", "Z"),
    }


def _event_summary(event: dict[str, object]) -> dict[str, object]:
    return {
        "title": event.get("event"),
        "event": event.get("event"),
        "currency": event.get("currency"),
        "impact": str(event.get("impact", "")).title(),
        "release_time": event.get("time"),
        "minutes_until": event.get("minutes_until"),
        "sentiment_score": event.get("sentiment_score"),
        "publisher": event.get("publisher"),
        "url": event.get("url"),
        "restriction_active": bool(event.get("blocks_entry")),
        "source": event.get("source", "Marketaux"),
    }


def _analyze_local_calendar(symbol: str, current: datetime) -> dict[str, object] | None:
    events = _load_local_events()
    if events is None:
        return None

    currencies = symbol_currencies(symbol)
    if not currencies:
        return _unavailable(
            "News risk unavailable — symbol currencies could not be detected.",
            source="Local calendar",
            blocks_entry=False,
            evaluated_at=current,
        )

    relevant = [
        event for event in events
        if str(event.get("currency", "")).upper() in currencies
    ]
    if not relevant:
        return {
            "available": True,
            "source": "Local calendar",
            "risk_level": "low",
            "blocks_entry": False,
            "event": None,
            "currency": None,
            "impact": None,
            "event_time": None,
            "minutes_until": None,
            "message": "No relevant high-impact local calendar events in the next 120 minutes.",
            "currencies": sorted(currencies),
            "events_checked": 0,
            "upcoming_events": [],
            "status": "Low",
            "restriction_active": False,
            "warning": "No relevant high-impact local calendar events in the next 120 minutes.",
            "evaluated_at": current.isoformat().replace("+00:00", "Z"),
        }

    ranked = [_score_event(event, current) for event in relevant]
    ranked = [event for event in ranked if event]
    if not ranked:
        return _unavailable(
            "Local calendar exists, but no events had usable times.",
            source="Local calendar",
            blocks_entry=False,
            evaluated_at=current,
        )
    ranked.sort(key=lambda item: (item["rank"], abs(int(item["minutes_until"]))))
    return _payload(ranked[0], sorted(currencies), len(relevant), current)


def _load_local_events() -> list[dict[str, object]] | None:
    if not LOCAL_CALENDAR_PATH.exists():
        return None

    try:
        raw_events = json.loads(LOCAL_CALENDAR_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return []

    events: list[dict[str, object]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        normalized = _normalize_local_event(event)
        if normalized:
            events.append(normalized)
    return events


def _normalize_local_event(event: dict[str, object]) -> dict[str, object] | None:
    name = str(event.get("event") or event.get("title") or event.get("name") or "").strip()
    currency = str(event.get("currency") or "").strip().upper()
    impact = str(event.get("impact") or event.get("importance") or "low").strip().lower()
    time_text = str(event.get("time") or event.get("datetime") or event.get("date") or "").strip()
    if not name or not currency or not time_text:
        return None
    parsed = _parse_time(time_text)
    if not parsed:
        return None
    return {
        "event": name,
        "currency": currency,
        "impact": _normalize_local_impact(impact),
        "time": parsed.isoformat().replace("+00:00", "Z"),
        "source": "Local calendar",
    }


def _normalize_local_impact(value: str) -> str:
    text = value.strip().lower()
    if text in {"3", "high", "h"}:
        return "high"
    if text in {"2", "medium", "med", "m"}:
        return "medium"
    if text in {"1", "low", "l"}:
        return "low"
    return "medium" if text else "low"


def _provider_error_message(message: str) -> str:
    text = message.strip()
    lowered = text.lower()
    if "api token missing" in lowered:
        return "Marketaux API token is missing."
    if "token was rejected" in lowered or "does not have access" in lowered:
        return "Marketaux API token was rejected or does not have access."
    if "rate limit" in lowered:
        return "Marketaux rate limit reached."
    return f"News filter unavailable — {text}"


def _timing_text(minutes_until: int) -> str:
    if minutes_until > 0:
        return f"in {minutes_until} minutes"
    if minutes_until < 0:
        return f"{abs(minutes_until)} minutes ago"
    return "now"


def _unavailable(
    message: str,
    *,
    source: str = "Marketaux",
    blocks_entry: bool = False,
    evaluated_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "available": False,
        "source": source,
        "risk_level": "unavailable",
        "blocks_entry": blocks_entry,
        "event": None,
        "currency": None,
        "impact": None,
        "event_time": None,
        "minutes_until": None,
        "message": message,
        "currencies": [],
        "sentiment_score": None,
        "publisher": None,
        "url": None,
        "events_checked": 0,
        "upcoming_events": [],
        "status": "Unavailable",
        "restriction_active": False,
        "warning": message,
        "evaluated_at": evaluated_at.isoformat().replace("+00:00", "Z") if evaluated_at else None,
    }


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_time(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return _to_utc(parsed)
