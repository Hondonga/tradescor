import json
from pathlib import Path
import pytest
from analysis.global_overlay_contract import normalize_global_decision
from analysis.instrument_precision import precision_registry,format_price
from analysis.derived_index_rules import derived_index_rules

REQUIRED={"overlay_id","decision_owner_id","strategy_id","setup_id","symbol_id","provider_symbol","market_type","timeframe","category","type","label","source","price","high","low","start_time","end_time","created_at","confirmed_at","expires_at","invalidated_at","active","historical","actionable","priority","display_group","metadata"}

def product(*,stage="WAITING_FOR_CONFIRMATION",status="SETUP DEVELOPING",entry=None,stop=None,targets=None,rr=None,setup_id="setup-1",direction="buy",readiness="ready",overlays=None,owner="strategy-1"):
    ready=stage=="TRADE_READY";setup={"setup_id":setup_id,"setup_type":"structure_pullback","direction":direction,"stage":stage,"trade_ready":ready,"entry":entry,"stop":stop,"targets":targets or [],"rr":rr,"entry_area":{"low":99.5,"high":100.0,"type":"pullback"} if setup_id else None,"completed_confirmation":{"confirmed":True} if ready else None,"production_supported":True,"family_compatible":True,"chase_valid":True,"next_required_condition":"Wait for completed confirmation."}
    return {"decision_id":"d1","meta":{"symbol":"R_75","display_symbol":"Volatility 75 Index","timeframe":"M5","analysis_time":"2026-07-20T12:00:00Z","market_source":"deriv","market_type":"derived","live":True},"ownership":{"selected_model_id":owner,"decision_owner_id":owner,"overlay_owner_id":owner},"readiness":{"state":readiness},"market":{"external_structure":"bullish","internal_structure":"pullback","current_price":100.25},"decision":{"status":status,"stage":stage,"direction":direction,"trade_ready":ready,"next_action":"Wait."},"setup":setup,"overlays":overlays or [],"previous_setup":None}

def types(value,category=None):return {row["type"] for row in value["overlays"] if category is None or row["category"]==category}

@pytest.mark.parametrize("entry,stop,targets",[(None,99,[{"price":102}]),(100,None,[{"price":102}]),(100,99,[])])
def test_incomplete_ready_geometry_never_renders_actionable(entry,stop,targets):
    value=normalize_global_decision(product(stage="TRADE_READY",status="READY TO BUY",entry=entry,stop=stop,targets=targets,rr=2),instrument_metadata={"pip_size":.0001})
    assert value["decision"]["status"]=="STATE CONTRADICTION" and not [x for x in value["overlays"] if x["actionable"]]

def test_non_ready_lifecycle_converts_plan_roles_to_developing_language():
    rows=[{"type":"target","name":"TP1","price":102,"setup_id":"setup-1","owner_id":"strategy-1"},{"type":"stop","name":"Stop Loss","price":99,"setup_id":"setup-1","owner_id":"strategy-1"}]
    value=normalize_global_decision(product(overlays=rows));labels={x["label"] for x in value["overlays"]}
    assert "TP1" not in labels and "Stop Loss" not in labels and {"POTENTIAL STRUCTURAL OBJECTIVE","IDEA INVALIDATION"}<=labels
    assert not [x for x in value["overlays"] if x["actionable"]]

@pytest.mark.parametrize("stage",["EXPIRED","INVALIDATED","CANCELLED","TOO_LATE","CLOSED","REPLACED","EVENT_CANCELLED"])
def test_terminal_setup_moves_to_previous_and_preserves_current_context(stage):
    value=normalize_global_decision(product(stage=stage,status=stage,entry=100,stop=99,targets=[{"price":102}],rr=2))
    assert value["active_setup"] is None and value["previous_setup"]["setup_id"]=="setup-1"
    assert value["current_market"]["current_price"]==100.25 and value["decision"]["direction"] is None
    assert not [x for x in value["overlays"] if x["category"] in {"developing","actionable"}]
    assert [x for x in value["overlays"] if x["category"]=="historical"] and all(not x["active"] for x in value["overlays"] if x["historical"])

def test_previous_overlay_group_is_isolated_and_hidden_by_default_metadata():
    value=normalize_global_decision(product(stage="EXPIRED",status="EXPIRED",entry=100,stop=99,targets=[{"price":102}],rr=2))
    historical=[x for x in value["overlays"] if x["display_group"]=="previous_setup"]
    assert historical and all(x["historical"] and not x["active"] for x in historical)

def test_duplicate_context_levels_cluster_with_supporting_sources():
    rows=[{"type":"swing_high","name":"H1 Swing High","price":101.0000,"timeframe":"H1","source":"swing","owner_id":"strategy-1","priority":80},{"type":"equal_high","name":"Equal Highs","price":101.00005,"timeframe":"M15","source":"equal_levels","owner_id":"strategy-1","priority":40}]
    value=normalize_global_decision(product(setup_id=None,direction=None,status="MARKET CONTEXT",stage="CONTEXT",overlays=rows),instrument_metadata={"pip_size":.0001})
    cluster=[x for x in value["overlays"] if x.get("price") and abs(x["price"]-101)<.001]
    assert len(cluster)==1 and cluster[0]["metadata"]["supporting_sources"]

def test_precision_matrix_and_exact_trailing_zero_formatting():
    fixture=json.loads(Path("tests/fixtures/instrument_precision_matrix.json").read_text())
    for row in fixture:
        registry=precision_registry(symbol=row["symbol"],provider=row["provider"],market_type=row["market_type"],metadata=row["metadata"]);assert registry["price_decimals"]==row["price_decimals"] and registry["tick_size"]==row["tick_size"]
    assert format_price(1.1,precision_registry(symbol="EUR/USD",provider="twelve_data",market_type="forex"))=="1.10000"

def test_derived_rules_accept_provider_float_pip_steps():
    assert derived_index_rules("R_75",{"pip_size":.0001})["precision"]==4
    assert derived_index_rules("stpRNG",{"pip_size":.1})["tick_size"]==.1

def test_every_visible_overlay_is_explained_and_owned():
    value=normalize_global_decision(product())
    assert value["overlays"] and all(REQUIRED<=set(row) for row in value["overlays"])
    assert all(row["decision_owner_id"]==value["ownership"]["decision_owner_id"] and row["metadata"].get("visibility_reason") and row["metadata"].get("invalidation_condition") for row in value["overlays"])

def test_owner_and_symbol_mismatches_cannot_restore_overlays():
    rows=[{"type":"swing_high","price":101,"owner_id":"old-model"},{"type":"swing_low","price":99,"owner_id":"strategy-1","provider_symbol":"OLD"}]
    value=normalize_global_decision(product(overlays=rows));assert value["decision"]["status"]=="STATE CONTRADICTION"
    assert not [row for row in value["overlays"] if row["category"] in {"developing","actionable"}]
    assert len(value["diagnostics"]["global_overlay_conflicting_fields"])==2

@pytest.mark.parametrize("mode",["LIVE","REPLAY","HISTORICAL_INSPECTION"])
def test_modes_are_explicit_and_do_not_change_backend_values(mode):
    value=normalize_global_decision(product(),mode=mode);assert value["overlay_mode"]==mode and all(row["provider_symbol"]=="R_75" and row["metadata"]["overlay_mode"]==mode for row in value["overlays"])

def test_previous_setup_mode_contains_archived_objects_only():
    value=normalize_global_decision(product(stage="EXPIRED",status="EXPIRED",entry=100,stop=99,targets=[{"price":102}],rr=2),mode="PREVIOUS_SETUP")
    assert value["overlays"] and all(row["category"]=="historical" and not row["active"] for row in value["overlays"])
    assert value["paper_registration_allowed"] is False

def test_setup_specific_objective_requires_active_setup():
    row={"type":"structural_objective","price":102,"name":"Potential Objective","owner_id":"strategy-1"}
    value=normalize_global_decision(product(setup_id=None,direction=None,status="MARKET CONTEXT",stage="CONTEXT",overlays=[row]));assert "structural_objective" not in types(value)

def test_actionable_rows_exactly_match_complete_backend_plan():
    value=normalize_global_decision(product(stage="TRADE_READY",status="READY TO BUY",entry=100,stop=99,targets=[{"price":101.5,"source":"M15"},{"price":103,"source":"H1"}],rr=1.5))
    rows={x["type"]:x for x in value["overlays"] if x["actionable"]};assert rows["entry"]["price"]==100 and rows["stop"]["price"]==99 and rows["tp1"]["price"]==101.5 and rows["tp2"]["price"]==103

def test_stale_data_suspends_actionable_plan():
    value=normalize_global_decision(product(stage="TRADE_READY",status="READY TO BUY",entry=100,stop=99,targets=[{"price":102}],rr=2,readiness="stale"));assert not [x for x in value["overlays"] if x["actionable"]] and not value["decision"]["trade_ready"]

def test_fixture_inventory_covers_all_required_market_families():
    fixture=json.loads(Path("tests/fixtures/global_overlay_lifecycle_matrix.json").read_text());assert set(fixture)=={"forex","volatility","jump","step","boom_crash"}

def test_every_lifecycle_fixture_drives_coherent_chart_and_panel_state():
    matrix=json.loads(Path("tests/fixtures/global_overlay_lifecycle_matrix.json").read_text())
    for family,fixtures in matrix.items():
        for fixture in fixtures:
            direction=fixture.get("direction","buy")
            has_setup=fixture.get("setup",True)
            actionable=fixture["actionable"]
            if actionable and direction=="sell":entry,stop,targets=100,101,[{"name":"TP1","price":98,"source":"M15"}]
            elif actionable:entry,stop,targets=100,99,[{"name":"TP1","price":102,"source":"M15"}]
            else:entry,stop,targets=None,None,[]
            value=product(stage=fixture["stage"],status=fixture["status"],direction=direction,setup_id=f"{family}-{fixture['fixture']}" if has_setup else None,entry=entry,stop=stop,targets=targets,rr=2 if actionable else None)
            if fixture.get("event_risk"):value["setup"]["event_risk"]="EVENT_RISK_ACTIVE"
            normalized=normalize_global_decision(value)
            assert (normalized["active_setup"] is not None) is fixture["active"],fixture["fixture"]
            assert (normalized["previous_setup"] is not None) is fixture["previous"],fixture["fixture"]
            chart_actionables=[row for row in normalized["overlays"] if row["category"]=="actionable"]
            assert bool(chart_actionables) is actionable,fixture["fixture"]
            assert normalized["trade_plan"]["available"] is actionable,fixture["fixture"]
            assert normalized["current_market"]["current_price"]==100.25
            if not fixture["active"]:
                assert not [row for row in normalized["overlays"] if row["category"]=="developing"]

def test_strategy_and_adapter_may_differ_while_overlay_owner_stays_exact():
    value=product(owner="jump_smc_adapter")
    value["ownership"].update(selected_model_id="jump_post_event_smc",selected_strategy_id="jump_post_event_smc")
    normalized=normalize_global_decision(value)
    assert normalized["decision"]["status"]!="STATE CONTRADICTION"
    assert all(row["decision_owner_id"]=="jump_smc_adapter" for row in normalized["overlays"])
    assert all(row["strategy_id"]=="jump_post_event_smc" for row in normalized["overlays"])

def test_live_ready_requires_live_data_and_research_setup_is_never_actionable():
    stale=product(stage="TRADE_READY",status="READY TO BUY",entry=100,stop=99,targets=[{"price":102}],rr=2)
    stale["meta"]["live"]=False
    normalized=normalize_global_decision(stale)
    assert normalized["decision"]["status"]=="STATE CONTRADICTION"
    research=product(stage="TRADE_READY",status="READY TO BUY",entry=100,stop=99,targets=[{"price":102}],rr=2)
    research["setup"]["research_only"]=True
    normalized=normalize_global_decision(research)
    assert not normalized["trade_plan"]["available"] and normalized["paper_registration_allowed"] is False

def test_registry_metadata_preserves_forex_pip_size_with_nested_precision():
    registry=precision_registry(symbol="USD/JPY",provider="twelve_data",market_type="forex",metadata={"symbol_id":"twelve_data:USD/JPY","instrument_precision":{"tick_size":.001,"pip_size":.01,"price_decimals":3}})
    assert registry=={"symbol_id":"twelve_data:USD/JPY","price_decimals":3,"pip_size":.01,"tick_size":.001,"quantity_decimals":None}

def test_chart_hides_native_last_price_duplicate():
    source=Path("frontend/src/components/chart/market-chart.tsx").read_text()
    assert "priceLineVisible: false" in source
    assert "lastValueVisible: false" in source

def test_global_terminal_set_stays_a_superset_of_every_family_vocabulary():
    from analysis.global_overlay_contract import TERMINAL
    from analysis.derived_setup_lifecycle import TERMINAL as derived_terminal
    from analysis.forex_decision_normalizer import TERMINAL_STATES as forex_terminal
    assert derived_terminal<=TERMINAL,derived_terminal-TERMINAL
    assert forex_terminal<=TERMINAL,forex_terminal-TERMINAL

@pytest.mark.parametrize("stage",["REGIME_SWITCH_CANCELLED","NEW_EVENT_CANCELLED","COMPLETED","MISSED","POOR_REWARD","DATA_ERROR"])
def test_derived_only_terminal_states_are_universally_terminal_at_the_boundary(stage):
    value=normalize_global_decision(product(stage=stage,status=stage,entry=100,stop=99,targets=[{"price":102}],rr=2))
    assert value["active_setup"] is None and value["previous_setup"]["setup_id"]=="setup-1"
    assert not [x for x in value["overlays"] if x["category"] in {"developing","actionable"}]
