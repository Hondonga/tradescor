"""Controlled multi-timeframe candle loading with per-timeframe caching."""

from __future__ import annotations

import time

import pandas as pd

from data_feed import get_candles
from providers.provider_router import get_provider


TIMEFRAME_INTERVALS = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H2": "2h",
    "H4": "4h",
    "D1": "1day",
}

FULL_TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H2", "H4", "D1"]
BALANCED_TIMEFRAMES = ["M5", "M15", "H1", "H4", "D1"]
ORDER = {timeframe: index for index, timeframe in enumerate(FULL_TIMEFRAMES)}

CACHE_SECONDS = {
    "M1": 60,
    "M5": 60,
    "M15": 180,
    "M30": 180,
    "H1": 600,
    "H2": 600,
    "H4": 1800,
    "D1": 1800,
}

_CONTEXT_CACHE: dict[tuple[str, str, int], tuple[float, pd.DataFrame]] = {}


def normalize_context_depth(value: object) -> str:
    """Return a supported context depth."""
    depth = str(value or "balanced").strip().lower()
    return depth if depth in {"light", "balanced", "full"} else "balanced"


def get_multi_timeframe_context(
    symbol: str,
    selected_timeframe: str,
    bars: int,
    depth: str = "balanced",
    selected_candles: pd.DataFrame | None = None,
    provider: str = "twelve_data",
    asset_class: str | None = None,
) -> dict[str, object]:
    """Load selected symbol across context timeframes after an explicit request."""
    selected = selected_timeframe.upper()
    selected_candles = _normalize_candles(selected_candles) if selected_candles is not None else None
    context: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    cache_status: dict[str, str] = {}

    timeframes=_context_timeframes(selected, depth)
    derived_m1=bool(provider=="deriv" and asset_class=="derived_index")
    if derived_m1 and "M1" not in timeframes:timeframes=["M1",*timeframes]
    for timeframe in timeframes:
        if derived_m1 and timeframe in {"M5","M15","H1"}:continue
        try:
            if timeframe == selected and selected_candles is not None and not selected_candles.empty:
                candles = selected_candles.copy()
                cache_status[timeframe] = "fresh"
            else:
                candles, status = _load_cached(symbol, timeframe, bars, provider, asset_class)
                cache_status[timeframe] = status

            context[timeframe] = _normalize_candles(candles)
        except RuntimeError as error:
            errors[timeframe] = str(error)
        except Exception as error:
            errors[timeframe] = f"Could not load {timeframe}: {error}"

    if derived_m1 and "M1" in context:
        for timeframe in ("M5","M15","H1"):
            context[timeframe]=_resample_completed(context["M1"],timeframe);cache_status[timeframe]="derived_from_m1"
        if selected in context:selected_candles=context[selected]

    if selected not in context:
        if selected_candles is not None and not selected_candles.empty:
            context[selected] = selected_candles.copy()
            cache_status[selected] = "fresh"
        elif selected in errors:
            raise RuntimeError(errors[selected])
        else:
            raise RuntimeError(f"Could not load selected timeframe {selected}.")

    return {
        "selected": {
            "timeframe": selected,
            "candles": context[selected],
        },
        "context": context,
        "errors": errors,
        "cache": cache_status,
        "depth": normalize_context_depth(depth),
    }


def context_timeframes(selected_timeframe: str, depth: str = "balanced") -> list[str]:
    """Expose timeframe selection for UI/debug use."""
    return _context_timeframes(selected_timeframe.upper(), depth)


def _context_timeframes(selected: str, depth: str) -> list[str]:
    depth = normalize_context_depth(depth)

    if depth == "full":
        frames = FULL_TIMEFRAMES.copy()
    elif depth == "balanced":
        frames = BALANCED_TIMEFRAMES.copy()
    else:
        frames = _light_timeframes(selected)

    if selected not in frames:
        frames.append(selected)

    return sorted(set(frames), key=lambda item: ORDER.get(item, 999))


def _light_timeframes(selected: str) -> list[str]:
    if selected not in ORDER:
        return [selected]

    index = ORDER[selected]
    frames = [selected]

    if index > 0:
        frames.append(FULL_TIMEFRAMES[index - 1])
    if index < len(FULL_TIMEFRAMES) - 1:
        frames.append(FULL_TIMEFRAMES[index + 1])

    return frames


def _load_cached(symbol: str, timeframe: str, bars: int, provider: str="twelve_data", asset_class: str|None=None) -> tuple[pd.DataFrame, str]:
    cache_key = (provider, symbol, timeframe, int(bars))
    cached_at, cached_candles = _CONTEXT_CACHE.get(cache_key, (0, pd.DataFrame()))
    now = time.time()
    ttl = CACHE_SECONDS.get(timeframe, 180)

    if not cached_candles.empty and now - cached_at < ttl:
        return cached_candles.copy(), "cached"

    if provider == "deriv" or asset_class == "derived_index":
        candles = get_provider(provider=provider,asset_class=asset_class).fetch_candles(symbol,timeframe,_bars_for_timeframe(timeframe,bars))
    else:
        interval = TIMEFRAME_INTERVALS[timeframe]
        candles = get_candles(symbol=symbol, timeframe=interval, bars=_bars_for_timeframe(timeframe, bars))
    candles = _normalize_candles(candles)
    if candles.empty and not cached_candles.empty:
        stale=cached_candles.copy();stale.attrs["stale_data"]=True
        return stale,"stale"
    if candles.empty:
        raise RuntimeError(f"No completed {timeframe} candles were returned for {symbol}.")
    _CONTEXT_CACHE[cache_key] = (now, candles.copy())
    return candles, "fresh"


def _bars_for_timeframe(timeframe: str, selected_bars: int) -> int:
    if timeframe == "M1":
        return min(max(selected_bars*60,1200),5000)
    if timeframe == "D1":
        return min(max(selected_bars, 120), 240)
    if timeframe == "H4":
        return min(max(selected_bars, 160), 320)
    if timeframe in {"H1", "H2"}:
        return min(max(selected_bars, 180), 400)
    return min(max(selected_bars, 120), 500)


def _resample_completed(rows:pd.DataFrame,timeframe:str)->pd.DataFrame:
    rule={"M5":"5min","M15":"15min","H1":"1h"}[timeframe];source=rows.copy();source["time"]=pd.to_datetime(source.time,utc=True)
    result=source.set_index("time").resample(rule,label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index()
    latest=pd.Timestamp(source.iloc[-1].time);period=pd.Timedelta(rule);result=result[result.time+period<=latest+pd.Timedelta(minutes=1)]
    return result.reset_index(drop=True)


def _normalize_candles(candles: pd.DataFrame) -> pd.DataFrame:
    clean = candles.copy()
    if clean.empty:
        return clean

    clean["time"] = pd.to_datetime(clean["time"], errors="coerce")
    for column in ["open", "high", "low", "close"]:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    clean = clean.dropna(subset=["time", "open", "high", "low", "close"])
    clean = clean.sort_values("time").drop_duplicates(subset=["time"], keep="last")
    return clean[["time", "open", "high", "low", "close"]].reset_index(drop=True)
