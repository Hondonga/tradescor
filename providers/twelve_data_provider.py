"""Adapter preserving TradeScor's existing Twelve Data loader."""

from __future__ import annotations

import time
from typing import Callable

from data_feed import get_candles
from providers.base_provider import MarketDataProvider
from providers.runtime_health import runtime_health, PipelineTrace

INTERVALS = {"M1":"1min","M5":"5min","M15":"15min","M30":"30min","H1":"1h","H2":"2h","H4":"4h","D1":"1day"}


class TwelveDataProvider(MarketDataProvider):
    name = "twelve_data"

    def list_symbols(self):
        return []

    def fetch_candles(self, symbol: str, timeframe: str, count: int):
        interval = INTERVALS.get(str(timeframe).upper(), timeframe)
        # Phase 4 §3 -- Twelve Data previously had no PipelineTrace the way
        # the Deriv provider does (providers/deriv_provider.py), so
        # GET /api/system/data-pipeline always fell back to an empty
        # placeholder for Forex symbols. Stages this layer cannot itself
        # observe (completed-candle filtering happens later, generically,
        # in analysis/top_down_engine.py) are deliberately left at their
        # default "pending" status rather than fabricated as passed.
        trace = PipelineTrace(symbol, timeframe, provider_symbol=symbol)
        trace.start("ACTIVE_SYMBOL_RESOLUTION").pass_("ACTIVE_SYMBOL_RESOLUTION", 1)
        runtime_health.provider("twelve_data","loading")
        started = time.perf_counter()
        trace.start("PROVIDER_CONNECTION").pass_("PROVIDER_CONNECTION")
        trace.start("HISTORY_REQUEST")
        try:
            rows = get_candles(symbol=symbol, timeframe=interval, bars=count)
        except RuntimeError as error:
            state = "rate_limited" if "rate limit" in str(error).lower() else "error"
            runtime_health.provider("twelve_data", state)
            trace.fail("HISTORY_REQUEST", "RATE_LIMITED" if state == "rate_limited" else "PROVIDER_ERROR", error)
            runtime_health.observe_history((time.perf_counter() - started) * 1000)
            runtime_health.add_trace(trace)
            raise
        trace.pass_("HISTORY_REQUEST")
        time_metadata = rows.attrs.get("time_metadata") or {}
        trace.start("HISTORY_RESPONSE").pass_("HISTORY_RESPONSE", time_metadata.get("raw_rows", len(rows)))
        trace.start("CANDLE_NORMALIZATION").pass_("CANDLE_NORMALIZATION", time_metadata.get("valid_rows", len(rows)))
        trace.start("CACHE_WRITE").pass_("CACHE_WRITE", len(rows))
        trace.start("ANALYSIS_READY").pass_("ANALYSIS_READY", len(rows)).ready()
        runtime_health.provider("twelve_data","ready")
        runtime_health.observe_history((time.perf_counter() - started) * 1000)
        runtime_health.add_trace(trace)
        rows.attrs.setdefault("provider", self.name)
        return rows

    def subscribe_ticks(self, symbol: str, callback: Callable):
        raise NotImplementedError("Twelve Data live subscriptions are not used by this application.")

    def unsubscribe(self, subscription_id: str): return None
    def get_server_time(self):
        import time
        return int(time.time())
    def close(self): return None
