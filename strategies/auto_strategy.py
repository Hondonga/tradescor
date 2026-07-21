"""Automatic strategy selection using already-loaded market data."""

from __future__ import annotations

import pandas as pd

from strategies import breakout_retest, ict_2022, supply_demand, universal_structure
from strategies.base import EMPTY_LEVELS


STRATEGY_NAME = "Auto"


def analyze(
    candles: pd.DataFrame,
    shared_analysis: dict[str, object],
    *,
    symbol: str,
    timeframe: str,
    top_down_analysis: dict[str, object] | None = None,
    context_candles: dict[str, pd.DataFrame] | None = None,
    macro_context: dict[str, object] | None = None,
    multi_timeframe_context: dict[str, pd.DataFrame] | None = None,
    top_down_context: dict[str, object] | None = None,
    analysis_timestamp: object | None = None,
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Choose one clean model without making additional data requests."""
    ict_result, ict_legacy = ict_2022.analyze(
        candles,
        shared_analysis,
        symbol=symbol,
        timeframe=timeframe,
        top_down_analysis=top_down_analysis,
        context_candles=context_candles,
        macro_context=macro_context,
        top_down_context=top_down_context,
        analysis_timestamp=analysis_timestamp,
    )
    if _ict_context_is_clean(ict_result):
        return _selected(
            ict_result,
            key="ict_2022",
            label="ICT Precision",
            reason="Liquidity sweep, fair value gap, and active kill-zone context align.",
        ), ict_legacy

    supply_result, _legacy = supply_demand.analyze(
        candles,
        shared_analysis,
        symbol=symbol,
        timeframe=timeframe,
        macro_context=macro_context,
        multi_timeframe_context=multi_timeframe_context,
        top_down_context=top_down_context,
        analysis_timestamp=analysis_timestamp,
    )
    if _supply_demand_context_is_clean(supply_result):
        return _selected(
            supply_result,
            key="supply_demand",
            label="Supply & Demand",
            reason="A valid nearby supply or demand zone has a clean reaction context.",
        ), None

    breakout_result, _legacy = breakout_retest.analyze(
        candles,
        shared_analysis,
        symbol=symbol,
        timeframe=timeframe,
        macro_context=macro_context,
        multi_timeframe_context=multi_timeframe_context,
        top_down_context=top_down_context,
        analysis_timestamp=analysis_timestamp,
    )
    if _breakout_context_is_clean(breakout_result):
        return _selected(
            breakout_result,
            key="breakout_retest",
            label="Breakout & Retest",
            reason="Price has broken a defined range and returned to test the broken level.",
        ), None

    structure_result, _legacy = universal_structure.analyze(
        candles,
        shared_analysis,
        macro_context=macro_context,
        multi_timeframe_context=multi_timeframe_context,
        top_down_context=top_down_context,
        analysis_timestamp=analysis_timestamp,
    )
    return _structure_context(structure_result), None


def _ict_context_is_clean(result: dict[str, object]) -> bool:
    checklist = result.get("ict_checklist") or {}
    return all(
        checklist.get(key) == "pass"
        for key in ("kill_zone", "liquidity_swept", "fvg")
    ) and str(result.get("state")) not in {"NO_TRADE", "INVALIDATED"}


def _supply_demand_context_is_clean(result: dict[str, object]) -> bool:
    details = result.get("supply_demand_details") or {}
    quality = details.get("zone_quality") or {}
    return bool(quality.get("valid")) and str(result.get("state")) not in {
        "NO_TRADE",
        "INVALIDATED",
        "WAITING_FOR_PRICE_TO_ENTER_ZONE",
    }


def _breakout_context_is_clean(result: dict[str, object]) -> bool:
    details = result.get("breakout_retest_details") or {}
    return bool(details.get("breakout")) and bool(details.get("retest")) and not bool(
        details.get("failed_breakout")
    )


def _selected(
    result: dict[str, object],
    *,
    key: str,
    label: str,
    reason: str,
) -> dict[str, object]:
    result.update(
        {
            "strategy_name": label,
            "requested_strategy": "auto",
            "selected_strategy": label,
            "selected_strategy_key": key,
            "strategy_reason": reason,
            "auto_strategy": True,
        }
    )
    return result


def _structure_context(result: dict[str, object]) -> dict[str, object]:
    overlays = dict(result.get("overlays") or {})
    for key in ("entry_zone", "stop_loss", "tp1", "tp2", "trade_levels"):
        overlays[key] = None
    overlays["levels_mode"] = "hidden"
    bias = str(result.get("bias", "Neutral"))
    result.update(
        {
            "strategy_name": "Structure Context",
            "requested_strategy": "auto",
            "selected_strategy": "Structure Context",
            "selected_strategy_key": "universal_structure",
            "strategy_reason": "No clean specialist strategy model is active, so TradeScor is showing structure context only.",
            "auto_strategy": True,
            "state": "TREND_DETECTED" if bias in {"Bullish", "Bearish"} else "NO_TRADE",
            "trade_decision": "PENDING",
            "levels_mode": "hidden",
            "levels": EMPTY_LEVELS.copy(),
            "overlays": overlays,
            "objective_plan": {
                "decision": "PENDING",
                "reason": "No clean strategy model detected.",
                "targets": [],
            },
            "next_action": "Wait for a clean strategy model to form before considering a trade.",
            "next_trigger": "Wait for a clean strategy model to form before considering a trade.",
        }
    )
    return result
