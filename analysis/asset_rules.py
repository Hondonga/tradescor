"""Asset-specific price, session, and context rules."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def asset_rules(symbol: str, asset_class: str) -> dict[str, object]:
    """Return deterministic trading conventions for a supported asset."""
    kind = str(asset_class or "forex").lower()
    normalized = str(symbol or "").upper().replace(" ", "")
    if kind == "derived_index":
        from analysis.derived_index_rules import derived_index_rules
        return derived_index_rules(symbol)
    if kind == "forex":
        jpy = normalized.endswith("JPY") or normalized.endswith("/JPY")
        tick, precision = (0.001, 3) if jpy else (0.00001, 5)
        return {"asset_class": kind, "tick_size": tick, "precision": precision, "movement_unit": "pip", "pip_size": 0.01 if jpy else 0.0001, "market_schedule": "weekday_forex", "exchange_timezone": "UTC", "dxy_applicable": True}
    if kind == "crypto":
        return {"asset_class": kind, "tick_size": 0.01, "precision": 2, "movement_unit": "point", "pip_size": None, "market_schedule": "24_7", "exchange_timezone": "UTC", "dxy_applicable": False}
    if kind == "index":
        exchange = "America/New_York" if normalized in {"NDX", "DJI", "SPX", "RUT", "NASDAQ100", "S&P500"} else "UTC"
        return {"asset_class": kind, "tick_size": 0.1, "precision": 1, "movement_unit": "point", "pip_size": None, "market_schedule": "exchange_cash", "exchange_timezone": exchange, "dxy_applicable": False}
    if kind == "equity":
        return {"asset_class": kind, "tick_size": 0.01, "precision": 2, "movement_unit": "point", "pip_size": None, "market_schedule": "exchange_extended", "exchange_timezone": "America/New_York", "dxy_applicable": False}
    return {"asset_class": kind, "tick_size": 0.01, "precision": 2, "movement_unit": "point", "pip_size": None, "market_schedule": "instrument_specific", "exchange_timezone": "UTC", "dxy_applicable": False}


def normalize_price(value: object, rules: dict[str, object], *, rounding: str = "nearest") -> float | None:
    """Normalize a real level without fabricating a missing value."""
    try:
        number = Decimal(str(value))
        tick = Decimal(str(rules["tick_size"]))
    except (TypeError, ValueError, KeyError):
        return None
    mode = ROUND_FLOOR if rounding == "down" else ROUND_CEILING if rounding == "up" else ROUND_HALF_UP
    units = (number / tick).to_integral_value(rounding=mode)
    return round(float(units * tick), int(rules.get("precision", 8)))
