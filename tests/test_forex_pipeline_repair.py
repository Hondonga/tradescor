import json
from pathlib import Path
import pandas as pd
import pytest

from analysis.market_decision_normalizer import normalize_market_decision
from providers.twelvedata import normalize_time_series_payload
from providers.twelvedata_audit import audit_timeframe

def _legacy(*,state="EXPIRED",direction="sell",htf="buy",status="SELL SETUP FORMING",zone=True,relationship="invalid"):
    array={"low":1.34635,"high":1.34641,"type":"fvg","formed_at":"2026-07-20T10:00:00Z"} if zone else {}
    ict={"strategy_version":"ict_2022_v2","narrative":{"direction":htf,"alignment":"aligned"},"setup":{"setup_id":None if state=="EXPIRED" else "ict-1","direction":direction,"relationship":relationship,"state":state,"entry_array":array,"expiration_reason":"Price did not return before expiration."},"execution":{"state":state,"confirmed_at":None,"entry":None,"stop":None,"targets":[],"remaining_rr":None},"quality":{"trade_plan_valid":False},"user_output":{"status":status}}
    return {"requested_strategy":"ict_2022","primary_strategy":"ict_2022","setup":{"setup_id":ict["setup"]["setup_id"],"direction":direction,"type":"ict_2022_v2","stage":state.lower(),"zone":array,"invalidation":{}},"execution":{"state":state.lower(),"entry":None,"stop":None,"targets":[]},"quality":{"trade_plan_valid":False,"score":70,"data_quality":"valid"},"user_output":{"status":status,"direction":direction},"strategy_routing":{"selected_strategy":"ict_2022"},"top_down":{"H1":{"structure":"Higher Highs / Higher Lows"}},"ict_model":ict,"trade_chart":{"current_price":1.345,"expected_entry":array,"confirmation":{"price":None,"confirmed":False},"invalidation":{"price":None},"targets":[]},"candle_bundle":{"timeframes":{tf:{"valid":True,"candle_count":100,"last_completed_time":"2026-07-20T11:55:00Z"} for tf in ("M5","M15","H1")}}}

def _normalize(legacy,market_type="forex"):
    return normalize_market_decision(legacy,symbol="GBP/USD",display_symbol="GBP/USD",timeframe="M15",market_source="twelve_data",market_type=market_type,market_schedule="24_5",analysis_time="2026-07-20T12:00:00Z",live=True)

def test_expired_gbpusd_is_terminal_and_clears_direction_zone_and_plan():
    result=_normalize(_legacy())
    assert result["decision"]["status"]=="SETUP EXPIRED" and result["decision"]["direction"] is None
    assert result["setup"]["entry_area"] is None and result["trade_plan"]["available"] is False
    assert not [row for row in result["overlays"] if row["category"]=="actionable"]
    assert result["paper_registration_allowed"] is False

def test_permanent_gbpusd_regression_fixture_resolves_to_expired_without_direction():
    fixture=json.loads(Path("tests/fixtures/gbpusd_expired_ict_regression.json").read_text());legacy=fixture["legacy_decision_sequence"][0];result=_normalize(_legacy(state=legacy["scenario_state"],direction=legacy["direction"],status=legacy["status"]))
    expected=fixture["expected"];assert result["decision"]["status"]==expected["status"] and result["decision"]["direction"] is None
    assert result["forex"]["entry_zone"] is None and result["forex"]["m5_confirmation"] is None and result["forex"]["trade_plan"] is None

def test_bullish_h1_cannot_silently_create_sell_setup():
    result=_normalize(_legacy(state="WAITING_FOR_RETURN",status="SELL SETUP FORMING"))
    assert result["decision"]["status"]=="STATE CONTRADICTION"
    assert "bullish HTF structure" in result["diagnostics"]["forex_invariants"]["failures"][1 if len(result["diagnostics"]["forex_invariants"]["failures"])>1 else 0]
    assert result["forex"]["entry_zone"] is None and result["forex"]["direction"] is None

def test_valid_countertrend_zone_has_owned_exact_overlay():
    result=_normalize(_legacy(state="WAITING_FOR_RETURN",status="SELL SETUP FORMING",relationship="countertrend_reversal_candidate"))
    zone=next(row for row in result["overlays"] if row["type"]=="developing_entry_area")
    assert (zone["low"],zone["high"],zone["owner_id"],zone["timeframe"])==(1.34635,1.34641,"ict_2022","M15")

def test_derived_normalization_does_not_receive_forex_fields():
    result=_normalize(_legacy(),market_type="derived")
    assert "forex" not in result and result["paper_registration_allowed"] is False

def test_provider_normalization_reports_raw_integrity():
    payload={"meta":{"symbol":"GBP/USD","exchange_timezone":"UTC"},"values":[{"datetime":"2026-07-20 10:00:00","open":"1.1","high":"1.2","low":"1.0","close":"1.15"},{"datetime":"2026-07-20 10:05:00","open":"1.15","high":"1.25","low":"1.1","close":"1.2"}]}
    rows,metadata=normalize_time_series_payload(payload,interval="5min",requested_timezone="UTC")
    assert len(rows)==2 and metadata["validation_passed"] and metadata["duplicate_timestamps"]==0

class _Response:
    def __init__(self,payload):self.payload=payload;self.status_code=200
    def raise_for_status(self):pass
    def json(self):return self.payload
class _Session:
    def __init__(self,payload):self.payload=payload
    def get(self,*args,**kwargs):return _Response(self.payload)

def test_raw_audit_persists_provider_response(monkeypatch,tmp_path):
    monkeypatch.setenv("TWELVE_DATA_API_KEY","test-key");values=[]
    for i in range(25):
        at=pd.Timestamp("2026-07-20T10:00:00Z")+pd.Timedelta(minutes=5*i);values.append({"datetime":at.strftime("%Y-%m-%d %H:%M:%S"),"open":"1.10000","high":"1.10100","low":"1.09900","close":"1.10050"})
    report=audit_timeframe("GBP/USD","M5",tmp_path,session=_Session({"meta":{"symbol":"GBP/USD","exchange_timezone":"UTC"},"values":list(reversed(values))}),now="2026-07-20T12:10:00Z")
    assert report["validation_passed"] and report["raw_rows"]==25 and Path(report["raw_response_path"]).exists()
    assert json.loads(Path(report["raw_response_path"]).read_text())["request"]["symbol"]=="GBP/USD"

def test_usdcad_no_context_never_renders_premature_targets_or_invalidation():
    fixture=json.loads(Path("tests/fixtures/usdcad_no_ict_context_overlay_regression.json").read_text());legacy=_legacy(state="NO_ICT_CONTEXT",direction="buy",htf="neutral",status="BUY SETUP FORMING",zone=False);ict=legacy["ict_model"];ict["setup"].update({"setup_id":None,"sweep":{"sweep_extreme":1.372,"sweep_time":"2026-07-20T10:00:00Z"},"displacement":{"confirmed":True,"structure_level_broken":1.371,"start_time":"2026-07-20T10:15:00Z","end_time":"2026-07-20T10:30:00Z","direction":"up"},"mss":{"level":1.3712,"break_time":"2026-07-20T10:30:00Z"}});ict["liquidity"]={"directional_target":{"price":1.375,"source_timeframe":"M15","type":"prominent_swing","formed_at":"2026-07-20T09:00:00Z"}};legacy["trade_chart"].update({"targets":[{"name":"TP1","price":1.375,"valid":True},{"name":"TP2","price":1.378,"valid":True}],"invalidation":{"price":1.369}})
    result=_normalize(legacy);expected=fixture["expected"]
    assert result["decision"]["status"]==expected["status"] and result["decision"]["direction"] is None
    assert not [row for row in result["overlays"] if row["category"]=="actionable"]
    assert not [row for row in result["overlays"] if row["name"] in {"TP1","TP2","INVALIDATION"}]
    assert any(row["category"]=="context" for row in result["overlays"])
    assert result["paper_registration_allowed"] is False

def test_developing_area_and_structural_objective_are_context_not_actionable():
    legacy=_legacy(state="WAITING_FOR_RETURN",direction="sell",htf="sell",status="SELL SETUP DEVELOPING",relationship="aligned_continuation");ict=legacy["ict_model"];ict["liquidity"]={"opposing_pool":{"price":1.4051,"source_timeframe":"M15","type":"near_equal_highs","formed_at":"2026-07-20T09:00:00Z"}};ict["setup"]["liquidity_targets"]={"selected_targets":{"tp1":{"price":1.401,"source_timeframe":"M15","type":"confirmed_swing","reason":"Previous M15 swing low."},"tp2":None}};result=_normalize(legacy)
    area=next(row for row in result["overlays"] if row["type"]=="developing_entry_area");objective=next(row for row in result["overlays"] if row["type"]=="structural_objective")
    assert area["name"]=="DEVELOPING · NOT AN ENTRY" and not area["actionable"] and area["category"]=="developing"
    assert objective["name"]=="Potential Structural Objective" and not objective["actionable"]
    assert all(row["name"] not in {"TP1","TP2"} for row in result["overlays"])
    assert all(row["name"]=="Potential Structural Objective" for row in result["forex_overlays"]["potential_structural_objectives"])

def test_targets_require_confirmation_entry_stop_rr_and_complete_plan():
    legacy=_legacy(state="ENTRY_AVAILABLE",direction="sell",htf="sell",status="READY TO SELL",relationship="aligned_continuation");ict=legacy["ict_model"];ict["quality"]["trade_plan_valid"]=True;ict["execution"].update({"confirmed_at":"2026-07-20T11:00:00Z","entry":None,"stop":1.4052,"targets":[{"name":"TP1","price":1.401,"risk_reward":2.0}],"remaining_rr":2.0})
    result=_normalize(legacy)
    assert not [row for row in result["overlays"] if row["category"]=="actionable"]
    ict["execution"]["entry"]=1.4045;ict["execution"]["stop"]=None;result=_normalize(legacy)
    assert not [row for row in result["overlays"] if row["type"]=="target"]

def test_every_forex_overlay_has_backend_ownership_and_source_metadata():
    legacy=_legacy(state="WAITING_FOR_RETURN",direction="sell",htf="sell",status="SELL SETUP DEVELOPING",relationship="aligned_continuation");result=_normalize(legacy)
    required={"overlay_id","decision_owner_id","setup_id","symbol","timeframe","category","type","source","created_at","expires_at","active","actionable"}
    assert result["overlays"] and all(required<=set(row) for row in result["overlays"])
