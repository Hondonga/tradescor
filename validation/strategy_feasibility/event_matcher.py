"""Event = one causally-generated setup, normalized for paired evaluation.

A strategy plugs into the harness by supplying a setup generator:

    generate(symbol, candles_df) -> list[Event]

Each Event fixes everything the controls share (the entry bar, price, ATR,
timing, grouping labels). Only the *direction* differs between controls, so any
performance difference is attributable to direction rather than to a different
event set. This is the pairing that the JDBR test lacked in its first pass.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Event:
    symbol: str
    event_id: str            # stable id for the originating structural event
    entry_index: int         # bar index in the symbol's candle frame
    entry_price: float
    atr: float               # ATR at entry, for symmetric geometry / risk normalization
    native_direction: int    # +1 (long) / -1 (short) = the strategy's own directional call
    day: str                 # calendar day of entry (a grouping unit)
    period: str = ""         # independent chronological block label (a grouping unit)
    structural_episode: str = ""  # id shared by setups from the same structural context
    meta: dict = None

    def __post_init__(self):
        if self.native_direction not in (-1, 1):
            raise ValueError("native_direction must be +1 or -1")
        if self.atr <= 0:
            raise ValueError("atr must be positive")
        if self.meta is None:
            self.meta = {}
        if not self.period:
            self.period = self.day  # default independent block = day


def normalize_events(events: list[Event]) -> list[Event]:
    """Deduplicate by (symbol, event_id) keeping the earliest entry per event.

    Repeated setups after one jump share an event_id, so collapsing them here
    prevents one event contributing many correlated trades.
    """
    seen = {}
    for ev in sorted(events, key=lambda e: (e.symbol, e.event_id, e.entry_index)):
        key = (ev.symbol, ev.event_id)
        if key not in seen:
            seen[key] = ev
    return list(seen.values())
