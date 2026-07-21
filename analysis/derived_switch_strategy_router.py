"""Pure routing rules: exactly one existing strategy may own the decision."""
def route_switch_strategy(family,regime,*,has_locked_range=False,directional_structure="neutral",stable=True,transition_active=False):
    eligible=[]; selected=None; allowed=[]; reason=""; rejected=[]
    if transition_active or not stable: reason="Waiting for completed-candle regime confirmation."
    elif family=="VOLATILITY_SWITCH":
        if regime in {"LOW_STABLE","NORMAL_STABLE"}: selected="derived_range_reaction"; reason="Stable low/normal volatility permits boundary reaction evaluation."; allowed=["buy","sell"]
        elif regime in {"COMPRESSION","RISING_VOLATILITY"} and (has_locked_range or regime=="COMPRESSION"): selected="derived_range_break_retest"; reason="A locked compression/rising-volatility range permits breakout and retest evaluation."; allowed=["buy","sell"]
        elif regime=="HIGH_STABLE" and directional_structure in {"bullish","bearish"}: selected="volatility_structure_pullback"; reason="Directional structure remained stable after volatility expansion."; allowed=["buy" if directional_structure=="bullish" else "sell"]
        else: reason=f"{regime} has no eligible switch strategy."
    elif family=="DRIFT_SWITCH":
        if regime=="BULLISH_DRIFT": selected="volatility_structure_pullback"; allowed=["buy"]; reason="Confirmed bullish drift permits buy-side pullback evaluation."
        elif regime=="BEARISH_DRIFT": selected="volatility_structure_pullback"; allowed=["sell"]; reason="Confirmed bearish drift permits sell-side pullback evaluation."
        elif regime=="SIDEWAYS_DRIFT": selected="derived_range_reaction"; allowed=["buy","sell"]; reason="Confirmed sideways drift permits boundary reaction evaluation."
        else: reason="Drift transition is not actionable."
    all_names=["derived_range_reaction","derived_range_break_retest","volatility_structure_pullback"]
    eligible=[selected] if selected else []; rejected=[{"strategy":name,"reason":"Not selected by the confirmed regime."} for name in all_names if name!=selected]
    return {"eligible_strategies":eligible,"delegated_strategy":selected,"rejected_strategies":rejected,"selection_reason":reason,"selection_confidence":.9 if selected else .0,"allowed_directions":allowed}
