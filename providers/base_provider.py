"""Common market-data provider contract and normalized candle helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class MarketDataProvider(ABC):
    """Backend-only provider interface used by charts and analysis."""

    name = "unknown"

    @abstractmethod
    def list_symbols(self) -> list[dict[str, object]]: ...

    @abstractmethod
    def fetch_candles(self, symbol: str, timeframe: str, count: int): ...

    @abstractmethod
    def subscribe_ticks(self, symbol: str, callback: Callable[[dict[str, object]], None]) -> str: ...

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None: ...

    @abstractmethod
    def get_server_time(self) -> int: ...

    @abstractmethod
    def close(self) -> None: ...


def normalized_candle(*, epoch: int, open_: float, high: float, low: float, close: float,
                      complete: bool, provider: str, symbol: str, timeframe: str = "") -> dict[str, object]:
    return {"time": int(epoch), "open": float(open_), "high": float(high), "low": float(low),
            "close": float(close), "complete": bool(complete), "provider": provider, "symbol": symbol, "timeframe":timeframe}
