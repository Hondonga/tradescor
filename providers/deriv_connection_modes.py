"""Strict separation between public chart data and future account transport."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os


class DerivConnectionMode(str, Enum):
    DERIV_PUBLIC_MARKET_DATA = "DERIV_PUBLIC_MARKET_DATA"
    DERIV_AUTHENTICATED_TRADING = "DERIV_AUTHENTICATED_TRADING"


@dataclass(frozen=True)
class DerivConnectionProfile:
    mode: DerivConnectionMode
    endpoint: str | None
    authentication_required: bool
    purpose: str
    enabled: bool


DERIV_PUBLIC_MARKET_DATA = DerivConnectionProfile(
    mode=DerivConnectionMode.DERIV_PUBLIC_MARKET_DATA,
    endpoint=os.getenv("DERIV_PUBLIC_WS_URL","wss://ws.binaryws.com/websockets/v3"),
    authentication_required=False,
    purpose="symbols, historical candles, live ticks and chart analysis",
    enabled=True,
)

DERIV_AUTHENTICATED_TRADING = DerivConnectionProfile(
    mode=DerivConnectionMode.DERIV_AUTHENTICATED_TRADING,
    endpoint=None,
    authentication_required=True,
    purpose="future account access and demo/real order execution",
    enabled=False,
)


PUBLIC_MARKET_DATA_REQUESTS = frozenset({
    "active_symbols", "ticks_history", "ticks", "forget", "ping", "time"
})

def public_market_data_connect_url()->str:
    """Legacy gateway app identification; this is not account authentication."""
    app_id=str(os.getenv("DERIV_PUBLIC_APP_ID","1089")).strip()
    separator="&" if "?" in str(DERIV_PUBLIC_MARKET_DATA.endpoint) else "?"
    return f"{DERIV_PUBLIC_MARKET_DATA.endpoint}{separator}app_id={app_id}" if app_id else str(DERIV_PUBLIC_MARKET_DATA.endpoint)


def require_public_market_data_request(payload: dict[str, object]) -> None:
    """Reject account/trading messages at the public chart-data boundary."""
    operations = {str(key) for key in payload if key not in {"req_id", "subscribe", "granularity", "style", "count", "end", "product_type"}}
    if not operations.intersection(PUBLIC_MARKET_DATA_REQUESTS):
        raise ValueError("Authenticated account or trading requests are not allowed on the public market-data connection.")
    forbidden = operations - PUBLIC_MARKET_DATA_REQUESTS
    if forbidden:
        raise ValueError(f"Unsupported public market-data request: {', '.join(sorted(forbidden))}.")
