"""Live candle data loading with the Twelve Data API."""

from __future__ import annotations

import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

from providers.twelvedata import INTRADAY_INTERVALS, normalize_time_series_payload


TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"
DEFAULT_SYMBOL = "EUR/USD"
DEFAULT_INTERVAL = "5min"
DEFAULT_BARS = 300
CACHE_SECONDS = 60
_CANDLE_CACHE: dict[tuple[str, str, int], tuple[float, pd.DataFrame]] = {}


def get_candles(
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_INTERVAL,
    bars: int = DEFAULT_BARS,
) -> pd.DataFrame:
    """Load OHLC candles from Twelve Data.

    Twelve Data calls the chart timeframe an "interval", for example:
    1min, 5min, 15min, 1h, 4h, or 1day.
    """
    load_dotenv()
    api_key = os.getenv("TWELVE_DATA_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "Missing TWELVE_DATA_API_KEY. Copy .env.example to .env and add your API key."
        )

    cache_key = (symbol, timeframe, bars)
    cached_at, cached_candles = _CANDLE_CACHE.get(cache_key, (0, pd.DataFrame()))

    if time.time() - cached_at < CACHE_SECONDS and not cached_candles.empty:
        return cached_candles.copy()

    params = {
        "symbol": symbol,
        "interval": timeframe,
        "outputsize": bars,
        "apikey": api_key,
    }
    requested_timezone = "UTC" if timeframe in INTRADAY_INTERVALS else None
    if requested_timezone:
        params["timezone"] = requested_timezone

    try:
        response = requests.get(TWELVE_DATA_URL, params=params, timeout=15)
    except requests.RequestException as error:
        raise RuntimeError(
            "Could not connect to Twelve Data. Check your internet connection and try again."
        ) from error

    if response.status_code >= 400:
        if response.status_code == 429:
            raise RuntimeError(
                "Twelve Data rate limit reached. Wait before refreshing or increase the refresh interval."
            )

        message = _get_error_message(response)
        raise RuntimeError(
            f"Twelve Data HTTP error {response.status_code}: {message}"
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Twelve Data returned a response that was not JSON.") from error

    if payload.get("status") == "error":
        message = payload.get("message", "Unknown Twelve Data API error.")
        if "rate" in message.lower() or "limit" in message.lower():
            raise RuntimeError(
                "Twelve Data rate limit reached. Wait before refreshing or increase the refresh interval."
            )
        raise RuntimeError(f"Twelve Data API error: {message}")

    if not payload.get("values"):
        raise RuntimeError(
            f"Twelve Data returned no candle values for {symbol} on {timeframe}."
        )

    candles, _time_metadata = normalize_time_series_payload(
        payload,
        interval=timeframe,
        requested_timezone=requested_timezone,
    )

    if candles.empty:
        raise RuntimeError(
            f"Twelve Data returned candle values for {symbol}, but none were usable."
        )
    if not _time_metadata.get("validation_passed"):
        raise RuntimeError(f"Twelve Data candle validation failed for {symbol} {timeframe}: duplicates={_time_metadata.get('duplicate_timestamps')}, malformed={_time_metadata.get('malformed_rows')}, invalid_ohlc={_time_metadata.get('invalid_ohlc')}.")

    _CANDLE_CACHE[cache_key] = (time.time(), candles.copy())

    return candles


def _get_error_message(response: requests.Response) -> str:
    """Return a safe API error message without exposing the API key."""
    try:
        payload = response.json()
    except ValueError:
        return response.reason or "Request failed."

    return payload.get("message") or payload.get("code") or "Request failed."
