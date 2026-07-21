"""Trade simulator — state machine for one pending/active trade at a time.

Enforces no look-ahead: price checks only use the candle currently being
evaluated, never future data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .trade_log import TradeRecord


MAX_PENDING_CANDLES = 20  # cancel entry if price never entered zone


@dataclass
class _PendingTrade:
    signal_candle_idx: int
    strategy_name: str
    symbol: str
    timeframe: str
    direction: str
    entry_zone_top: float
    entry_zone_bottom: float
    entry_mid: float
    stop_loss: float
    tp1: float
    tp2: Optional[float]
    reason: str
    entry_time: int = 0
    entry_price: float = 0.0


class TradeSimulator:
    """Manages one trade at a time for a single strategy."""

    def __init__(self, strategy_name: str) -> None:
        self.strategy_name = strategy_name
        self.state = "WATCHING"   # WATCHING | PENDING_ENTRY | ACTIVE
        self._trade: Optional[_PendingTrade] = None
        self._pending_since = 0

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def open_pending(
        self,
        *,
        signal_candle_idx: int,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        direction: str,
        entry_zone: object,
        stop_loss: float,
        tp1: float,
        tp2: Optional[float],
        reason: str,
    ) -> None:
        """Record a pending trade waiting for price to enter the entry zone."""
        top, bottom = _parse_entry_zone(entry_zone, stop_loss, tp1, direction)
        entry_mid = (top + bottom) / 2.0

        self._trade = _PendingTrade(
            signal_candle_idx=signal_candle_idx,
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            entry_zone_top=top,
            entry_zone_bottom=bottom,
            entry_mid=entry_mid,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            reason=reason,
        )
        self.state = "PENDING_ENTRY"
        self._pending_since = signal_candle_idx

    def check_pending_entry(
        self,
        candle: pd.Series,
        candle_idx: int,
    ) -> Optional[str]:
        """Check whether the trade filled or was cancelled.

        Returns "FILLED" when the trade becomes active, None otherwise.
        The caller should check self.state afterward.
        """
        trade = self._trade
        if trade is None:
            self.state = "WATCHING"
            return None

        # Expire if too many candles have passed without a fill
        if candle_idx - self._pending_since > MAX_PENDING_CANDLES:
            self.state = "WATCHING"
            self._trade = None
            return "EXPIRED"  # signals engine to increment missed_entries

        high = float(candle["high"])
        low = float(candle["low"])

        # If invalidation is breached before entry, cancel
        if trade.direction == "Bullish" and low <= trade.stop_loss:
            self.state = "WATCHING"
            self._trade = None
            return None
        if trade.direction == "Bearish" and high >= trade.stop_loss:
            self.state = "WATCHING"
            self._trade = None
            return None

        # Check if price entered the entry zone on this candle
        zone_touched = low <= trade.entry_zone_top and high >= trade.entry_zone_bottom
        if zone_touched:
            fill_price = max(min(trade.entry_mid, high), low)
            trade.entry_price = fill_price
            trade.entry_time = _candle_time(candle)
            self.state = "ACTIVE"
            return "FILLED"

        return None

    def check_active_trade(
        self,
        candle: pd.Series,
        candle_idx: int,
    ) -> Optional[TradeRecord]:
        """Check whether SL or TP is hit on this candle.

        Returns a completed TradeRecord when the trade closes, else None.
        """
        trade = self._trade
        if trade is None:
            self.state = "WATCHING"
            return None

        high = float(candle["high"])
        low = float(candle["low"])
        exit_time = _candle_time(candle)
        bullish = trade.direction == "Bullish"

        # Evaluate hits
        tp2_hit = (
            trade.tp2 is not None
            and ((bullish and high >= trade.tp2) or (not bullish and low <= trade.tp2))
        )
        tp1_hit = (bullish and high >= trade.tp1) or (not bullish and low <= trade.tp1)
        sl_hit = (bullish and low <= trade.stop_loss) or (not bullish and high >= trade.stop_loss)

        if sl_hit and tp1_hit:
            # Both hit same candle — use whichever side opened first.
            # Conservative: record SL (worst case).
            record = self._close(trade, "SL", trade.stop_loss, exit_time, candle_idx)
        elif tp2_hit:
            record = self._close(trade, "TP2", trade.tp2, exit_time, candle_idx)  # type: ignore[arg-type]
        elif tp1_hit:
            record = self._close(trade, "TP1", trade.tp1, exit_time, candle_idx)
        elif sl_hit:
            record = self._close(trade, "SL", trade.stop_loss, exit_time, candle_idx)
        else:
            return None

        self.state = "WATCHING"
        self._trade = None
        return record

    def force_close(
        self,
        candle: pd.Series,
        candle_idx: int,
    ) -> Optional[TradeRecord]:
        """Close any open trade at end of data (marked OPEN_AT_END)."""
        trade = self._trade
        if trade is None or self.state == "WATCHING":
            return None

        if self.state == "PENDING_ENTRY":
            self.state = "WATCHING"
            self._trade = None
            return None  # never filled — not a trade

        close_price = float(candle["close"])
        exit_time = _candle_time(candle)
        record = self._close(trade, "OPEN_AT_END", close_price, exit_time, candle_idx)
        self.state = "WATCHING"
        self._trade = None
        return record

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _close(
        self,
        trade: _PendingTrade,
        result: str,
        exit_price: float,
        exit_time: int,
        exit_idx: int,
    ) -> TradeRecord:
        entry = trade.entry_price if trade.entry_price else trade.entry_mid
        risk = abs(entry - trade.stop_loss)

        if result == "SL":
            pnl_r = -1.0
        elif result in {"TP1", "TP2"}:
            pnl_r = abs(exit_price - entry) / risk if risk > 0 else 0.0
        else:
            # OPEN_AT_END — compute unrealised P&L in R
            direction_sign = 1.0 if trade.direction == "Bullish" else -1.0
            pnl_r = direction_sign * (exit_price - entry) / risk if risk > 0 else 0.0

        duration = max(0, exit_idx - trade.signal_candle_idx)

        return TradeRecord(
            strategy=trade.strategy_name,
            symbol=trade.symbol,
            timeframe=trade.timeframe,
            direction=trade.direction,
            entry_time=trade.entry_time,
            entry=round(entry, 6),
            stop_loss=round(trade.stop_loss, 6),
            tp1=round(trade.tp1, 6),
            tp2=round(trade.tp2, 6) if trade.tp2 is not None else None,
            exit_time=exit_time,
            exit_price=round(exit_price, 6),
            result=result,
            rr_result=round(pnl_r, 3),
            duration_candles=duration,
            reason=trade.reason,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_entry_zone(
    entry_zone: object,
    stop_loss: float,
    tp1: float,
    direction: str,
) -> tuple[float, float]:
    """Return (top, bottom) from whatever shape the strategy provides."""
    if isinstance(entry_zone, dict):
        top = float(entry_zone.get("top") or entry_zone.get("high") or 0)
        bottom = float(entry_zone.get("bottom") or entry_zone.get("low") or 0)
        if top and bottom:
            if top < bottom:
                top, bottom = bottom, top
            return top, bottom

    # Scalar fallback: treat as a midpoint and widen slightly
    try:
        mid = float(entry_zone)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        # Last resort: split entry between SL and TP
        mid = (stop_loss + tp1) / 2.0

    spread = abs(mid - stop_loss) * 0.05  # 5% of risk as zone width
    return mid + spread, mid - spread


def _candle_time(candle: pd.Series) -> int:
    """Convert a candle's time field to a Unix timestamp integer."""
    try:
        ts = pd.Timestamp(candle["time"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return int(ts.timestamp())
    except Exception:
        return 0
