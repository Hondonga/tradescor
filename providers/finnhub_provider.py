"""Finnhub provider boundary for market-filter data.

This module keeps Finnhub credentials on the backend and normalizes provider
responses before the rest of TradeScor sees them.
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


FINNHUB_ECONOMIC_CALENDAR_URL = "https://finnhub.io/api/v1/calendar/economic"
CACHE_SECONDS = 30 * 60
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
_ECONOMIC_CACHE: dict[tuple[str, str], tuple[float, list[dict[str, object]]]] = {}


def is_available() -> bool:
    """Return True when Finnhub is enabled and an API key is configured."""
    _load_env()
    return _enabled() and bool(_api_key())


def get_economic_calendar(
    start_date: date | datetime | str,
    end_date: date | datetime | str,
) -> list[dict[str, object]]:
    """Return normalized Finnhub economic-calendar events for a date range."""
    _load_env()
    if not _enabled():
        raise RuntimeError("Finnhub provider is disabled.")
    token = _api_key()
    if not token:
        raise RuntimeError("Finnhub API key missing.")

    start = _date_text(start_date)
    end = _date_text(end_date)
    cache_key = (start, end)
    cached_at, cached_events = _ECONOMIC_CACHE.get(cache_key, (0, []))
    if time.time() - cached_at < CACHE_SECONDS:
        return [dict(event) for event in cached_events]

    try:
        response = requests.get(
            FINNHUB_ECONOMIC_CALENDAR_URL,
            params={"from": start, "to": end, "token": token},
            timeout=12,
        )
    except requests.RequestException as error:
        raise RuntimeError("Could not connect to Finnhub economic calendar.") from error

    if response.status_code == 429:
        raise RuntimeError("Finnhub rate limit reached.")
    if response.status_code == 401:
        raise RuntimeError("Finnhub API key was rejected.")
    if response.status_code == 403:
        raise RuntimeError("Finnhub calendar access is unavailable for this API key or plan.")
    if response.status_code >= 400:
        raise RuntimeError(f"Finnhub HTTP error {response.status_code}: {_safe_error_message(response)}")

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Finnhub returned a response that was not JSON.") from error

    raw_events = payload.get("economicCalendar", payload.get("events", []))
    if not isinstance(raw_events, list):
        raise RuntimeError("Finnhub economic calendar response was malformed.")

    events = [_normalize_event(event) for event in raw_events if isinstance(event, dict)]
    normalized = [event for event in events if event]
    _ECONOMIC_CACHE[cache_key] = (time.time(), [dict(event) for event in normalized])
    return normalized


def clear_cache() -> None:
    """Clear provider cache. Used by tests."""
    _ECONOMIC_CACHE.clear()


def _load_env() -> None:
    load_dotenv(_ENV_PATH)


def _enabled() -> bool:
    return os.getenv("FINNHUB_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _api_key() -> str:
    return os.getenv("FINNHUB_API_KEY", "").strip()


def _date_text(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _normalize_event(event: dict[str, Any]) -> dict[str, object] | None:
    event_name = _first_text(event, "event", "title", "name")
    country = _first_text(event, "country", "region")
    currency = _first_text(event, "currency").upper()
    if not currency:
        currency = _country_currency(country)
    impact = _normalize_impact(_first_text(event, "impact", "importance"))
    event_time = _parse_time(event.get("time") or event.get("datetime") or event.get("date"))

    if not event_name or not currency or not event_time:
        return None

    return {
        "event": event_name,
        "country": country or None,
        "currency": currency,
        "impact": impact,
        "time": event_time.isoformat().replace("+00:00", "Z"),
        "actual": _nullable(event.get("actual")),
        "forecast": _nullable(event.get("forecast", event.get("estimate"))),
        "previous": _nullable(event.get("previous")),
        "source": "Finnhub",
    }


def _first_text(event: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = event.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_impact(value: str) -> str:
    text = value.strip().lower()
    if text in {"3", "high", "h"}:
        return "high"
    if text in {"2", "medium", "med", "m"}:
        return "medium"
    if text in {"1", "low", "l"}:
        return "low"
    return "medium" if text else "low"


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
        try:
            parsed = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _country_currency(country: str) -> str:
    mapping = {
        "united states": "USD",
        "us": "USD",
        "usa": "USD",
        "euro area": "EUR",
        "european union": "EUR",
        "eurozone": "EUR",
        "germany": "EUR",
        "france": "EUR",
        "italy": "EUR",
        "spain": "EUR",
        "united kingdom": "GBP",
        "uk": "GBP",
        "japan": "JPY",
        "canada": "CAD",
        "australia": "AUD",
        "new zealand": "NZD",
        "switzerland": "CHF",
    }
    return mapping.get(country.strip().lower(), "")


def _nullable(value: object) -> object | None:
    if value in {"", "n/a", "N/A", "-"}:
        return None
    return value


def _safe_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.reason or "Request failed."
    return str(payload.get("error") or payload.get("message") or payload.get("code") or "Request failed.")
