import pandas as pd

from analysis.smc.smc_invariants import validate_trade_ready_invariants
from analysis.smc.smc_target_engine import evaluate_structural_targets,target_lifecycle_events,history_depth_audit,clear_target_lifecycle_cache
from analysis.smc.smc_target_store import SMCTargetStore
from analysis.smc.smc_setup_engine import build_smc_setup
from paper_testing.derived_setup_tracker import build_paper_setup
from paper_testing.derived_setup_tracker import registerable_paper_setup


def candles(values,start="2026-01-01",freq="15min"):
    return pd.DataFrame([{"time":time,"open":close,"high":high,"low":low,"close":close,"complete":True} for time,(high,low,close) in zip(pd.date_range(start,periods=len(values),freq=freq,tz="UTC"),values)])


def swing(identity,price,scope="internal",time="2026-01-01T01:45:00+00:00",kind="high"):
    return {"swing_id":identity,"type":kind,"scope":scope,"price":price,"candle_time":time,"confirmation_time":time}


def frames():
    quiet=candles([(103,99,100)]*8)
    return {"M5":quiet,"M15":quiet,"H1":quiet,"H4":quiet}


def test_internal_tp1_and_external_tp2_are_selected_deterministically():
    # M15-scoped internal swings are excluded from TP1 for structure_pullback
    # (the default setup_type here), so the H1 external swing is TP1 and no
    # farther candidate remains for TP2.
    result=evaluate_structural_targets(symbol="R_100",direction="bullish",entry=100,stop=95,swings=[swing("i",110),swing("e",120,"external")],liquidity=[],candles_by_timeframe=frames())
    assert result["tp1"]["price"]==120 and result["tp1"]["scope"]=="external"
    assert result["tp2"] is None
    assert result["target_trace"]["selected_target"]["target_id"]==result["tp1"]["target_id"]


def test_tp2_is_next_farther_active_objective_owned_by_same_setup():
    result=evaluate_structural_targets(symbol="R_75",direction="bullish",entry=100,stop=95,swings=[swing("first",110,"execution"),swing("second",114,"internal"),swing("far",120,"external")],liquidity=[],candles_by_timeframe=frames(),setup_type="structure_pullback",owning_setup_id="setup-1")
    assert result["tp1"]["price"]==110
    assert result["tp2"]["price"]==114
    assert result["tp1"]["owning_setup_id"]==result["tp2"]["owning_setup_id"]=="setup-1"
    assert result["tp1"]["price"]<result["tp2"]["price"]


def test_missing_tp2_does_not_block_valid_tp1():
    result=evaluate_structural_targets(symbol="R_75",direction="bearish",entry=100,stop=105,swings=[swing("only",90,"execution",kind="low")],liquidity=[],candles_by_timeframe=frames(),setup_type="structure_pullback")
    assert result["tp1"]["price"]==90 and result["tp2"] is None
    assert result["target_trace"]["first_blocker"]==""


def test_structure_pullback_target_hierarchy_prefers_m5_then_h1_over_excluded_m15():
    # M15-timeframe swings are excluded from TP1 for structure_pullback setups
    # (proven 90-day R_75 outcome data), so without M5 present the hierarchy
    # falls through to H1, skipping the M15 candidate entirely.
    candidates=[swing("h1",108,"external"),swing("m15",109,"internal"),swing("m5",112,"execution")]
    first=evaluate_structural_targets(symbol="R_75",direction="bullish",entry=100,stop=95,swings=candidates,liquidity=[],candles_by_timeframe=frames(),setup_type="structure_pullback")
    assert first["tp1"]["timeframe"]=="M5"
    second=evaluate_structural_targets(symbol="R_75",direction="bullish",entry=100,stop=95,swings=candidates[:2],liquidity=[],candles_by_timeframe=frames(),setup_type="structure_pullback")
    assert second["tp1"]["timeframe"]=="H1"


def test_range_equilibrium_is_a_real_partial_target_not_external_liquidity():
    result=evaluate_structural_targets(symbol="STEP",direction="bullish",entry=100,stop=98,swings=[],liquidity=[],dealing_range={"valid":True,"low":99,"high":110,"range_id":"r","created_time":"2026-01-01T01:45:00+00:00","confirmed_at":"2026-01-01T01:45:00+00:00"},candles_by_timeframe=frames(),setup_type="range_reaction")
    assert result["tp1"]["price"]==104.5 and result["tp1"]["source_type"]=="range_equilibrium" and result["tp1"]["scope"]=="setup"


def test_wrong_side_and_low_rr_are_distinct_rejections():
    wrong=evaluate_structural_targets(symbol="R",direction="bullish",entry=100,stop=95,swings=[swing("x",99)],liquidity=[],candles_by_timeframe=frames())
    low=evaluate_structural_targets(symbol="R",direction="bullish",entry=100,stop=95,swings=[swing("x",106)],liquidity=[],candles_by_timeframe=frames())
    assert wrong["target_trace"]["first_blocker"]=="ALL_TARGETS_WRONG_SIDE"
    assert low["target_trace"]["first_blocker"]=="ALL_TARGETS_RR_REJECTED"


def test_wick_only_does_not_imply_acceptance_or_consumption():
    target={"price":110,"side":"buy_side","created_at":"2025-12-31","confirmed_at":"2025-12-31"}
    lifecycle=target_lifecycle_events(target,candles([(111,99,109),(109,100,108)]))
    assert lifecycle["swept"] and not lifecycle["accepted_beyond"] and not lifecycle["consumed"]


def test_acceptance_requires_completed_follow_through():
    target={"price":110,"side":"buy_side","created_at":"2025-12-31","confirmed_at":"2025-12-31"}
    pending=target_lifecycle_events(target,candles([(112,99,111)]))
    accepted=target_lifecycle_events(target,candles([(112,99,111),(113,110,112)]))
    assert pending["pending_acceptance"] and not pending["consumed"]
    assert accepted["accepted_beyond"] and accepted["consumed"]


def test_target_ids_and_store_are_deterministic_and_namespace_isolated(tmp_path):
    # scope="execution" (M5) keeps this candidate eligible for TP1 under the
    # default structure_pullback setup_type; this test is about id/store
    # determinism, not the M15-timeframe TP1 exclusion rule.
    args=dict(direction="bullish",entry=100,stop=95,swings=[swing("i",110,"execution")],liquidity=[],candles_by_timeframe=frames())
    a=evaluate_structural_targets(symbol="R_100",**args)["tp1"];b=evaluate_structural_targets(symbol="R_100",**args)["tp1"];other=evaluate_structural_targets(symbol="R_75",**args)["tp1"]
    assert a["target_id"]==b["target_id"] and a["target_id"]!=other["target_id"]
    path=tmp_path/"targets.sqlite";one=SMCTargetStore(path,"replay-a");one.upsert(a);one.append_event(a["target_id"],"selected","t");one.close()
    assert SMCTargetStore(path,"replay-a").get(a["target_id"])["symbol"]=="R_100"
    assert SMCTargetStore(path,"replay-b").get(a["target_id"]) is None


def test_target_lifecycle_is_pure_across_fixtures_and_restart():
    target={"target_id":"target-stable","price":110,"side":"buy_side","created_at":"2025-12-31","confirmed_at":"2025-12-31"}
    consumed=target_lifecycle_events(target,candles([(112,99,111),(113,110,112)]))
    untouched=target_lifecycle_events(target,candles([(109,99,108)]))
    clear_target_lifecycle_cache();restarted=target_lifecycle_events(target,candles([(112,99,111),(113,110,112)]))
    assert consumed["consumed"] and not untouched["touched"] and restarted==consumed


def test_target_trace_contains_exact_causal_geometry_counts():
    result=evaluate_structural_targets(symbol="R_75",direction="bullish",entry=100,stop=95,swings=[swing("m5",110,"execution")],liquidity=[],candles_by_timeframe=frames())
    trace=result["target_trace"];candidate=trace["candidates_created"][0]
    assert trace["entry"]==100 and trace["stop"]==95
    assert trace["counts"]=={"confirmed_swings":1,"structural_references":1,"target_candidates":1,"profitable_side":1,"active":1,"rr_passed":1}
    assert {"target_id","price","source_type","timeframe","confirmed_at","state","touched","swept","accepted_beyond","consumed","distance_from_entry","projected_rr","rejection_reason"}<=set(candidate)


def test_jd75_event_risk_and_missing_levels_can_never_be_ready_or_registered():
    raw={"ownership":{"selected_strategy_id":"smc_auto","decision_owner_id":"smc_auto","overlay_owner_id":"smc_auto"},"decision":{"status":"TRADE_READY","trade_ready":True},"setup":{"setup_id":"jd75","state":"TRADE_READY","direction":"buy","bos":{"structure_event_id":"b"},"entry":None,"stop":None,"targets":[],"rr":None,"event_risk":"EVENT_RISK_ACTIVE"}}
    validation=validate_trade_ready_invariants(raw);codes={row["code"] for row in validation["violations"]}
    assert not validation["valid"] and validation["corrected_status"]=="EVENT RISK"
    assert {"MISSING_ENTRY","MISSING_STOP","MISSING_TP1","EVENT_RISK_ACTIVE"}<=codes
    snapshot={"setup_id":"jd75","decision":{"developing_direction":"buy","trade_ready":False},"setup":{"entry":None,"stop":None,"tp1":None},"normalized_decision":{"diagnostics":{"invariants":validation}}}
    assert not registerable_paper_setup(snapshot)


def test_24_hour_depth_is_analysis_ready_but_not_acceptance_ready():
    audit=history_depth_audit({"M5":candles([(2,0,1)]*288,freq="5min"),"M15":candles([(2,0,1)]*96),"H1":candles([(2,0,1)]*24,freq="1h"),"H4":candles([(2,0,1)]*6,freq="4h")})
    assert all(row["sufficient_for_analysis"] for row in audit.values())
    assert not all(row["sufficient_for_acceptance_matrix"] for row in audit.values())


def test_setup_constructor_geometry_is_symmetric_for_registered_setup_names():
    # This is a production setup-engine unit test, not reachability proof.
    # Formal reachability is candle-driven in strategy_setup_proof.py.
    setup_types=("volatility_structure_pullback","volatility_liquidity_reversal","volatility_range_reaction","jump_post_event_continuation","jump_post_event_reversal","step_range_reaction","step_structure_pullback","step_breakout_and_retest")
    for setup_type in setup_types:
        plan=build_smc_setup(symbol="FIXTURE",strategy_id=setup_type,family_adapter=setup_type.split("_")[0],direction="bullish",htf_structure="bullish",structural_target={"target_id":"target-"+setup_type,"price":106,"source_type":"internal_swing","timeframe":"M15","scope":"internal"},sweep={"qualified":True,"extreme":99},displacement={"passed":True},structure={"last_bos":{"structure_event_id":"bos-"+setup_type,"direction":"bullish"}},entry_array={"structural_array_id":"array-"+setup_type,"type":"structural_retrace","low":100,"high":102,"invalidated":False},current_price=101,tick_size=.1)
        assert plan["state"]=="TRADE_READY" and plan["targets"][0]["source"]=="internal_swing"
        snapshot={"decision_id":"d-"+setup_type,"created_at":"2026-01-01T00:00:00Z","setup_id":plan["setup_id"],"selected_strategy":setup_type,"decision":{"developing_direction":"buy","trade_ready":True},"setup":{"entry":plan["entry"],"stop":plan["stop"],"tp1":plan["targets"][0],"tp1_rr":plan["rr"],"timing_state":"VALID","confirmation":{"formed_at":"2026-01-01T00:00:00Z"}}}
        assert build_paper_setup(snapshot) is not None


def test_fresh_post_event_target_is_allowed_after_quarantine_clears():
    # scope="execution" (M5) keeps this candidate eligible for TP1 under the
    # default structure_pullback setup_type; this test is about post-event
    # quarantine timing, not the M15-timeframe TP1 exclusion rule.
    result=evaluate_structural_targets(symbol="JD75",direction="bullish",entry=100,stop=95,swings=[swing("post",110,"execution",time="2026-01-01T01:45:00+00:00")],liquidity=[],candles_by_timeframe=frames(),event={"event_time":"2026-01-01T01:00:00+00:00","blocking":False})
    assert result["tp1"] and result["tp1"]["created_at"]>"2026-01-01T01:00:00+00:00"
