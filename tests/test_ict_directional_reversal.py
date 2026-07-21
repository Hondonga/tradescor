from strategies.ict_2022_v2 import _candidate_contract, _relationship, _select_observation
from analysis.ict_consistency_validator import validate_ict_consistency


def _candidate(direction,score,valid=True,candidate_id=None,accepted=False):
    event={"valid":valid,"rejection_reason":None}; sweep={**event,"rejection_reason":"Accepted breakout is not an ICT sweep." if accepted else None}
    return {"candidate_id":candidate_id or f"ict-{direction}","direction":direction,"score":score,"liquidity_event":event,"liquidity":{"opposing_pool":{"liquidity_id":f"liq-{direction}"},"directional_target":None,"candidate_pools":[]},"sweep_event":sweep,"sweep":{"sweep_time":"2026-01-01T01:00:00+00:00"},"displacement_event":event,"displacement":{"start_time":"2026-01-01T01:15:00+00:00"},"mss_event":event,"mss":{"break_time":"2026-01-01T01:30:00+00:00"},"fvg_event":event,"entry_event":event,"entry_array":{"fvg_id":f"fvg-{direction}","low":100,"high":101},"interaction":{"state":"waiting"}}


def test_invalidated_sell_does_not_block_new_bullish_candidate():
    bearish=_candidate("sell",2,valid=False,candidate_id="old-sell",accepted=True); bullish=_candidate("buy",5,candidate_id="new-buy")
    selected=_select_observation(bullish,bearish,"sell")
    assert selected["candidate_id"]=="new-buy" and selected["direction"]=="buy"
    old=_candidate_contract(bearish,"aligned_continuation",None)
    assert old["state"]=="invalidated" and old["candidate_id"]!="new-buy"


def test_countertrend_candidate_is_labeled_while_htf_remains_bearish():
    bullish=_candidate("buy",5); top_down={"timeframes":{"H1":{"bias":"bearish"},"H4":{"bias":"bearish"}}}
    assert _relationship("buy","sell",bullish,top_down)=="countertrend_reversal_candidate"


def test_h1_and_h4_improvement_classifies_full_regime_reversal():
    bullish=_candidate("buy",5); top_down={"timeframes":{"H1":{"bias":"bullish"},"H4":{"bias":"neutral"}}}
    assert _relationship("buy","sell",bullish,top_down)=="full_regime_reversal"


def test_weak_opposite_observation_does_not_override_htf_direction():
    bullish=_candidate("buy",2,valid=False); bearish=_candidate("sell",1,valid=False)
    assert _select_observation(bullish,bearish,"sell")["direction"]=="sell"


def test_both_directional_diagnostics_have_independent_levels():
    bullish=_candidate_contract(_candidate("buy",5),"countertrend_reversal_candidate",None); bearish=_candidate_contract(_candidate("sell",2,valid=False,accepted=True),"aligned_continuation",None)
    assert bullish["candidate_id"]!=bearish["candidate_id"]
    assert bullish["entry"]["fvg_id"]=="fvg-buy" and bearish["entry"]["fvg_id"]=="fvg-sell"
    assert bearish["state"]=="invalidated"


def test_partial_v2_candidate_with_missing_event_timestamps_is_safe():
    ict={"strategy_version":"ict_2022_v2","sequence":{},"sequence_events":{},"setup":{"direction":"sell","sweep":{"sweep_time":"2026-01-01T01:00:00Z"},"mss":{"break_time":None},"displacement":{"start_time":None},"entry_array":{}},"execution":{"entry":None,"stop":None,"targets":[]},"quality":{"confidence":"low","trade_plan_valid":False},"user_output":{"status":"POTENTIAL SELL CONTEXT"}}
    assert validate_ict_consistency(ict)["valid"]
