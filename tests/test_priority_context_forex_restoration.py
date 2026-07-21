import threading,time
import pandas as pd
from analysis.analysis_priority import AnalysisPriorityCoordinator,PRIORITY_1_WORKSPACE,PRIORITY_2_WATCHLIST
from analysis.decision_views import build_market_analysis,build_trade_plan
from analysis.smc.smc_structure_engine import analyze_structure
from analysis.smc.smc_dealing_range_engine import build_dealing_range
from paper_testing.derived_setup_tracker import registerable_paper_setup
from providers.market_registry import traditional_registry

def test_workspace_slot_never_waits_behind_lightweight_scanner_work():
    scheduler=AnalysisPriorityCoordinator();entered=threading.Event();release=threading.Event()
    def scan():
        with scheduler.slot(PRIORITY_2_WATCHLIST,"JD75"):entered.set();release.wait(1)
    worker=threading.Thread(target=scan);worker.start();assert entered.wait(.5)
    started=time.perf_counter()
    with scheduler.slot(PRIORITY_1_WORKSPACE,"R_50"):assert time.perf_counter()-started<.1
    release.set();worker.join();assert scheduler.snapshot()["limits"]=={"full_analysis_workers":1,"lightweight_analysis_workers":2,"history_download_workers":1,"research_workers":1,"background_market_scan":False}

def test_rapid_workspace_switch_rejects_obsolete_generation():
    scheduler=AnalysisPriorityCoordinator();old=scheduler.select_workspace("JD75");new=scheduler.select_workspace("R_50")
    assert not scheduler.current("JD75",old) and scheduler.current("R_50",new)

def test_focused_is_default_and_research_yields_to_workspace():
    scheduler=AnalysisPriorityCoordinator();assert scheduler.snapshot()["mode"]=="FOCUSED"
    with scheduler.slot(PRIORITY_1_WORKSPACE,"JD75"):assert scheduler.should_yield_research()
    assert not scheduler.should_yield_research()

def test_market_context_survives_missing_target_while_plan_is_blocked():
    setup={"direction":"sell","stage":"WAITING_FOR_TARGET","context_summary":"Bearish H1 leg with M15 consolidation","next_required_condition":"Completed bullish M5 MSS","invalidation":{"condition":"Accepted bullish break"},"trade_ready":False,"entry":None,"stop":None,"targets":[]}
    market={"external_structure":"bearish","internal_structure":"range","alignment":"pullback"};view=build_market_analysis(market=market,setup=setup,scenario="Potential bullish reaction");plan=build_trade_plan(setup,"WAITING FOR TARGET","No valid structural target is available")
    assert view["available"] and view["external_structure"]=="bearish" and view["developing_scenario"]=="Potential bullish reaction"
    assert not plan["available"] and plan["entry"] is None and plan["reason"]

def test_jump_directional_leg_is_not_called_range_without_range_evidence():
    rows=pd.DataFrame([{"time":pd.Timestamp("2026-01-01",tz="UTC")+pd.Timedelta(minutes=5*i),"open":120-i,"high":121-i,"low":119-i,"close":119.2-i,"complete":True} for i in range(30)])
    low={"type":"low","price":100,"swing_id":"low-1","confirmation_time":rows.iloc[20].time};result=analyze_structure(rows,[low],{"passed":True,"direction":"bearish","body_atr":2})
    assert result["external_structure"]=="transition" and not result["range_evidence"]["valid"] and result["classification_evidence"]["transition"] and result["active_leg"]["direction"]=="bearish"

def test_range_requires_alternation_and_archives_on_accepted_breakout():
    swings=[{"type":"high","scope":"external","price":110,"swing_id":"h1","confirmation_time":"1"},{"type":"low","scope":"external","price":90,"swing_id":"l1","confirmation_time":"2"},{"type":"high","scope":"external","price":110,"swing_id":"h2","confirmation_time":"3"},{"type":"low","scope":"external","price":90,"swing_id":"l2","confirmation_time":"4"}]
    valid=build_dealing_range(swings);broken=build_dealing_range(swings,{"type":"accepted_breakout"})
    assert valid["valid"] and valid["alternating_interactions"]>=2
    assert broken["archived"] and not broken["active"]

def test_forex_registry_and_lightweight_rows_are_non_registerable():
    rows={row["display_name"]:row for row in traditional_registry()}
    for symbol in ("EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD"):
        row=rows[symbol];assert row["market_source"]=="twelve_data" and row["provider_symbol"]==symbol and row["analysis_engine"]=="forex" and row["default_model"]=="universal_structure";assert "step_smc" not in {x["id"] for x in row["available_models"]}
    payload={"decision":{"trade_ready":False,"developing_direction":"sell"},"setup":{"entry":None,"stop":None,"tp1":None},"normalized_decision":{"analysis_depth":"lightweight","diagnostics":{"invariants":{"valid":True}}}}
    assert not registerable_paper_setup(payload)

def test_navigation_contains_no_automatic_full_analysis_trigger():
    # Phase 3: the "Analyze now" button and its analysis.mutate() wiring
    # were extracted from workspace-page.tsx into a dedicated
    # OpportunityQueue component (components/terminal/opportunity-queue.tsx),
    # which workspace-page.tsx renders. Check the combined source so this
    # keeps protecting the same invariant (no useEffect-driven auto-trigger,
    # a real manual "Analyze now" affordance exists) across the refactor.
    workspace_source=open("frontend/src/pages/workspace-page.tsx",encoding="utf-8").read()
    queue_source=open("frontend/src/components/terminal/opportunity-queue.tsx",encoding="utf-8").read()
    combined=workspace_source+queue_source
    assert "useEffect" not in workspace_source and "analysis.mutate()" in combined and "Analyze now" in combined
