"""Trade record dataclass for the backtesting engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class TradeRecord:
    """Represents one simulated trade produced by the backtesting engine."""

    strategy: str
    symbol: str
    timeframe: str
    direction: str          # "Bullish" or "Bearish"
    entry_time: int         # Unix timestamp when trade was filled
    entry: float            # Fill price
    stop_loss: float
    tp1: float
    tp2: Optional[float]
    exit_time: int          # Unix timestamp when trade closed
    exit_price: float
    result: str             # "SL", "TP1", "TP2", "OPEN_AT_END"
    rr_result: float        # Positive for win, -1.0 for SL, fractional for partial
    duration_candles: int   # How many candles the trade lasted
    reason: str             # Brief strategy context at signal time

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def is_win(self) -> bool:
        return self.result in {"TP1", "TP2"}

    @property
    def is_loss(self) -> bool:
        return self.result == "SL"
