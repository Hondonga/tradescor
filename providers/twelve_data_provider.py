"""Adapter preserving TradeScor's existing Twelve Data loader."""

from __future__ import annotations

from typing import Callable

from data_feed import get_candles
from providers.base_provider import MarketDataProvider
from providers.runtime_health import runtime_health

INTERVALS = {"M1":"1min","M5":"5min","M15":"15min","M30":"30min","H1":"1h","H2":"2h","H4":"4h","D1":"1day"}


class TwelveDataProvider(MarketDataProvider):
    name = "twelve_data"

    def list_symbols(self):
        return []

    def fetch_candles(self, symbol: str, timeframe: str, count: int):
        interval = INTERVALS.get(str(timeframe).upper(), timeframe)
        runtime_health.provider("twelve_data","loading")
        try:rows = get_candles(symbol=symbol, timeframe=interval, bars=count)
        except RuntimeError as error:
            runtime_health.provider("twelve_data","rate_limited" if "rate limit" in str(error).lower() else "error");raise
        runtime_health.provider("twelve_data","ready")
        rows.attrs.setdefault("provider", self.name)
        return rows

    def subscribe_ticks(self, symbol: str, callback: Callable):
        raise NotImplementedError("Twelve Data live subscriptions are not used by this application.")

    def unsubscribe(self, subscription_id: str): return None
    def get_server_time(self):
        import time
        return int(time.time())
    def close(self): return None
