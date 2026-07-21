from validation.smc_reachability import build_reachability,aggregate_blockers
def decision(family="VOLATILITY",state="NO_CONTEXT",source=False,ready=False):
    setup={"state":"TRADE_READY" if ready else state,"direction":"buy" if state!="NO_CONTEXT" else "","bos":{"direction":"bullish"} if source else None,"entry_array":{"low":1,"high":2} if state in {"WAITING_FOR_RETRACE","TRADE_READY"} else {}};return {"family":family,"smc_contract":{"setup":setup,"structure":{"external_structure":"bullish" if source else "range","last_bos":{"direction":"bullish"} if source else None},"gate_funnel":{"first_blocking_gate":"external_structure" if not source else "entry_array"},"evaluated_candidates":[]}}
def test_zero_trade_classification_distinguishes_absence_and_deadlock():
    absent=build_reachability([decision()]);assert all(x["zero_trade_classification"]=="SOURCE_BEHAVIOR_ABSENT" for x in absent)
    detected=build_reachability([decision(source=True,state="DIRECTIONAL_CONTEXT")])
    by_type={row["setup_type"]:row for row in detected}
    assert by_type["volatility_structure_pullback"]["zero_trade_classification"]=="TARGET_UNAVAILABLE"
    # A BOS is source behaviour for a structure pullback, but is not a sweep for
    # either reversal model. Those models must remain classified as absent.
    assert by_type["volatility_liquidity_reversal"]["zero_trade_classification"]=="SOURCE_BEHAVIOR_ABSENT"
    assert by_type["volatility_range_reaction"]["zero_trade_classification"]=="SOURCE_BEHAVIOR_ABSENT"
def test_blocker_aggregation_is_deterministic():
    rows=build_reachability([decision(),decision()]);assert aggregate_blockers(rows)==aggregate_blockers(list(reversed(rows)))
