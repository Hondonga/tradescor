"""Strategy registry."""

from __future__ import annotations

import pandas as pd

from strategies import breakout_retest, ict_2022, supply_demand, universal_structure
from strategies import auto_strategy


STRATEGY_LABELS = {
    "auto": "Auto",
    "universal_structure": "Structure Context",
    "ict_2022": "ICT Precision",
    "supply_demand": "Supply & Demand",
    "breakout_retest": "Breakout & Retest",
    "boom_crash_spike_state": "Boom/Crash Spike-State",
    "derived_range_reaction": "Derived Range Reaction",
    "derived_regime_switch": "Derived Regime Switch",
    "jump_dex_post_event": "Jump/DEX Post-Event Structure",
    "step_structure_research": "Step Index Structure Research",
    "volatility_smc": "Volatility SMC",
    "volatility_structure_pullback": "Volatility Structure Pullback",
    "jump_smc": "Jump SMC",
    "step_smc": "Step SMC",
}


def normalize_strategy_key(value: object) -> str:
    key = str(value or "auto").strip().lower()
    return key if key in STRATEGY_LABELS else "auto"


def analyze_strategy(
    strategy_key: str,
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
    """Run only the selected strategy."""
    selected = normalize_strategy_key(strategy_key)

    if selected == "auto":
        return auto_strategy.analyze(
            candles,
            shared_analysis,
            symbol=symbol,
            timeframe=timeframe,
            top_down_analysis=top_down_analysis,
            context_candles=context_candles,
            macro_context=macro_context,
            multi_timeframe_context=multi_timeframe_context,
            top_down_context=top_down_context,
            analysis_timestamp=analysis_timestamp,
        )

    if selected == "ict_2022":
        return ict_2022.analyze(
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
    if selected == "supply_demand":
        return supply_demand.analyze(
            candles,
            shared_analysis,
            symbol=symbol,
            timeframe=timeframe,
            macro_context=macro_context,
            multi_timeframe_context=multi_timeframe_context,
            top_down_context=top_down_context,
            analysis_timestamp=analysis_timestamp,
        )
    if selected == "breakout_retest":
        return breakout_retest.analyze(
            candles,
            shared_analysis,
            symbol=symbol,
            timeframe=timeframe,
            macro_context=macro_context,
            multi_timeframe_context=multi_timeframe_context,
            top_down_context=top_down_context,
            analysis_timestamp=analysis_timestamp,
        )

    return universal_structure.analyze(
        candles,
        shared_analysis,
        macro_context=macro_context,
        multi_timeframe_context=multi_timeframe_context,
        top_down_context=top_down_context,
        analysis_timestamp=analysis_timestamp,
    )
