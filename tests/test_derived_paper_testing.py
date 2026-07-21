import json
import pandas as pd

from paper_testing.derived_signal_snapshot import build_derived_signal_snapshot
from paper_testing.derived_setup_tracker import build_paper_setup,terminate_unfilled_setup
from paper_testing.derived_paper_store import DerivedPaperStore
from paper_testing.derived_fill_engine import evaluate_paper_fill
from paper_testing.derived_outcome_resolver import resolve_paper_outcome
from paper_testing.derived_mfe_mae_tracker import track_mfe_mae
from paper_testing.derived_r_multiple import planned_r
from paper_testing.derived_evidence_classifier import classify_derived_evidence
from paper_testing.derived_paper_service import DerivedPaperService


def contract(direction="buy"):
    entry,stop,tp1,tp2=(100,98,104,106) if direction=="buy" else (100,102,96,94)
    return {"decision":{"setup_id":"locked-1","status":"READY","developing_direction":direction,"trade_ready":True},"auto_evaluation":{"selected_strategy":"derived_range_reaction","eligible_strategies":["derived_range_reaction"]},"active_trade_plan":{"entry":entry,"stop":stop,"tp1":tp1,"tp2":tp2,"tp1_rr":2,"tp2_rr":3,"entry_type":"confirmation_close"}}


def snapshot(direction="buy"):
    return build_derived_signal_snapshot(provider_symbol="R_50",display_name="Volatility 50",family="volatility",subfamily="continuous",requested_strategy="auto",analysis_candle_time="2026-01-01T00:00:00+00:00",decision_contract=contract(direction))


def candles(rows):
    return pd.DataFrame(rows,columns=["time","open","high","low","close","complete"]).assign(time=lambda x:pd.to_datetime(x.time,utc=True))


def test_signal_snapshot_is_deterministic_and_store_is_immutable(tmp_path):
    first,second=snapshot(),snapshot();assert first.decision_id==second.decision_id and first.dedupe_key==second.dedupe_key
    store=DerivedPaperStore(tmp_path/"paper.db");assert store.insert_decision(first)[1] is True;assert store.insert_decision(second)[1] is False
    stored=store.rows("paper_decisions")[0];assert json.loads(stored["payload_json"])["setup"]["entry"]==100


def test_setup_registration_requires_complete_valid_plan():
    assert build_paper_setup(snapshot()) is not None
    broken=contract();broken["active_trade_plan"]["tp1"]=None
    snap=build_derived_signal_snapshot(provider_symbol="R_50",display_name="V50",family="volatility",subfamily="continuous",requested_strategy="auto",analysis_candle_time="2026-01-01T00:00:00+00:00",decision_contract=broken)
    assert build_paper_setup(snap) is None


def test_fill_engine_is_directionally_symmetric_and_has_no_lookahead():
    buy=build_paper_setup(snapshot()).as_dict();sell=build_paper_setup(snapshot("sell")).as_dict()
    data=candles([["2025-12-31T23:55:00Z",100,101,99,100,True],["2026-01-01T00:00:00Z",100,105,95,100,True],["2026-01-01T00:05:00Z",100,101,99,100,True]])
    assert evaluate_paper_fill(buy,data)["fill_time"].startswith("2026-01-01T00:05")
    assert evaluate_paper_fill(sell,data)["filled"] is True


def test_outcomes_begin_after_fill_and_ambiguity_is_not_fabricated():
    setup=build_paper_setup(snapshot()).as_dict();data=candles([["2026-01-01T00:05:00Z",100,105,97,100,True],["2026-01-01T00:10:00Z",100,105,97,100,True]])
    result=resolve_paper_outcome(setup,data,"2026-01-01T00:05:00+00:00")
    assert result["outcome"]=="AMBIGUOUS" and result["realized_r"] is None and result["terminal_time"].startswith("2026-01-01T00:10")
    assert resolve_paper_outcome(setup,data,"2026-01-01T00:05:00+00:00","worst_case")["outcome"]=="STOPPED"


def test_mfe_mae_and_r_are_directionally_correct():
    data=candles([["2026-01-01T00:05:00Z",100,999,1,100,True],["2026-01-01T00:10:00Z",100,103,99,102,True]])
    buy=build_paper_setup(snapshot()).as_dict();metrics=track_mfe_mae(buy,data,"2026-01-01T00:05:00+00:00")
    assert metrics["mfe_r"]==1.5 and metrics["mae_r"]==.5
    assert planned_r("buy",100,98,104)==2 and planned_r("sell",100,102,96)==2


def test_prefill_cancellation_is_not_a_loss(tmp_path):
    store=DerivedPaperStore(tmp_path/"paper.db");snap=snapshot();store.insert_decision(snap);setup=build_paper_setup(snap);store.insert_setup(setup,snap.payload)
    outcome=terminate_unfilled_setup(store,setup.paper_setup_id,"expired","2026-01-01T01:00:00Z")
    assert outcome["entry_filled"] is False and outcome["realized_r"] is None and store.active_setups()==[]


def test_restart_recovery_and_idempotent_events(tmp_path):
    path=tmp_path/"paper.db";store=DerivedPaperStore(path);snap=snapshot();store.insert_decision(snap);setup=build_paper_setup(snap);store.insert_setup(setup,snap.payload)
    service=DerivedPaperService(store=DerivedPaperStore(path),config={"enabled":True,"ambiguity":{"policy":"mark_ambiguous"},"evidence":{}},enabled=True)
    assert service.reconcile()["pending_setups_recovered"]==1
    assert store.append_event(setup.paper_setup_id,"test","2026-01-01T00:05:00Z") is True
    assert store.append_event(setup.paper_setup_id,"test","2026-01-01T00:05:00Z") is False


def test_evidence_labels_depend_on_filled_sample_size():
    assert classify_derived_evidence(0)["evidence_label"].lower().startswith("insufficient")
    assert classify_derived_evidence(100)["filled_sample_size"]==100
