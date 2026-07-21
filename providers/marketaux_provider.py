"""Marketaux provider boundary for financial news risk data.

Credentials stay on the backend. The rest of TradeScor receives normalized
article records instead of raw provider responses.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


MARKETAUX_NEWS_URL = "https://api.marketaux.com/v1/news/all"
CACHE_SECONDS = 10 * 60
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
_NEWS_CACHE: dict[tuple[str, str, str, int], tuple[float, list[dict[str, object]]]] = {}


def is_available() -> bool:
    """Return True when Marketaux is enabled and an API token is configured."""
    _load_env()
    return _enabled() and bool(_api_token())


def get_finance_news(
    *,
    symbol: str,
    published_after: datetime,
    published_before: datetime,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Return normalized recent finance-news articles for a symbol/search query."""
    _load_env()
    if not _enabled():
        raise RuntimeError("Marketaux provider is disabled.")
    token = _api_token()
    if not token:
        raise RuntimeError("Marketaux API token missing.")

    query = _search_query(symbol)
    after = _marketaux_datetime(published_after)
    before = _marketaux_datetime(published_before)
    safe_limit = max(1, min(int(limit), 10))
    cache_key = (query, after, before, safe_limit)
    cached_at, cached_articles = _NEWS_CACHE.get(cache_key, (0, []))
    if time.time() - cached_at < CACHE_SECONDS:
        return [dict(article) for article in cached_articles]

    try:
        response = requests.get(
            MARKETAUX_NEWS_URL,
            params={
                "api_token": token,
                "search": query,
                "language": "en",
                "group_similar": "true",
                "must_have_entities": "false",
                "published_after": after,
                "published_before": before,
                "limit": safe_limit,
            },
            timeout=12,
        )
    except requests.RequestException as error:
        raise RuntimeError("Could not connect to Marketaux news.") from error

    if response.status_code == 429:
        raise RuntimeError("Marketaux rate limit reached.")
    if response.status_code in {401, 403}:
        raise RuntimeError("Marketaux API token was rejected or does not have access.")
    if response.status_code >= 400:
        raise RuntimeError(f"Marketaux HTTP error {response.status_code}: {_safe_error_message(response)}")

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Marketaux returned a response that was not JSON.") from error

    raw_articles = payload.get("data", [])
    if not isinstance(raw_articles, list):
        raise RuntimeError("Marketaux news response was malformed.")

    articles = [_normalize_article(article) for article in raw_articles if isinstance(article, dict)]
    normalized = [article for article in articles if article]
    _NEWS_CACHE[cache_key] = (time.time(), [dict(article) for article in normalized])
    return normalized


def clear_cache() -> None:
    """Clear provider cache. Used by tests."""
    _NEWS_CACHE.clear()


def _load_env() -> None:
    load_dotenv(_ENV_PATH)


def _enabled() -> bool:
    return os.getenv("MARKETAUX_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _api_token() -> str:
    return os.getenv("MARKETAUX_API_KEY", "").strip()


def _search_query(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper()
    if "/" in normalized:
        base, quote = [part for part in normalized.split("/", 1)]
        asset_type = "cryptocurrency" if base in {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"} else "forex"
        return f'"{normalized}" "{base} {quote}" {base} {quote} {asset_type}'
    return normalized or "financial markets"


def _marketaux_datetime(value: datetime) -> str:
    current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _normalize_article(article: dict[str, Any]) -> dict[str, object] | None:
    title = _text(article.get("title"))
    published_at = _parse_time(article.get("published_at"))
    if not title or not published_at:
        return None

    entities = article.get("entities") if isinstance(article.get("entities"), list) else []
    sentiment_scores = [
        float(entity["sentiment_score"])
        for entity in entities
        if isinstance(entity, dict) and _is_number(entity.get("sentiment_score"))
    ]
    sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
    symbols = [
        str(entity.get("symbol", "")).strip().upper()
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("symbol", "")).strip()
    ]

    return {
        "event": title,
        "title": title,
        "description": _text(article.get("description") or article.get("snippet")),
        "source": "Marketaux",
        "publisher": _text(article.get("source")),
        "url": _text(article.get("url")),
        "time": published_at.isoformat().replace("+00:00", "Z"),
        "published_at": published_at.isoformat().replace("+00:00", "Z"),
        "sentiment_score": sentiment,
        "symbols": sorted(set(symbols)),
        "impact": _impact_from_sentiment(sentiment),
    }


def _impact_from_sentiment(value: float | None) -> str:
    if value is None:
        return "low"
    magnitude = abs(value)
    if magnitude >= 0.65:
        return "high"
    if magnitude >= 0.35:
        return "medium"
    return "low"


def _parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _text(value: object) -> str:
    return str(value or "").strip()


def _is_number(value: object) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _safe_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.reason or "Request failed."
    return str(payload.get("error") or payload.get("message") or payload.get("code") or "Request failed.")
