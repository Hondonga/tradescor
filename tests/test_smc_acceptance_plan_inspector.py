from validation.smc_plan_validator import validate_trade_plan
from validation.smc_decision_inspector import inspect_historical_decision
def ready():
    setup={"setup_id":"s","state":"TRADE_READY","direction":"buy","entry":100,"stop":98,"targets":[{"name":"TP1","price":104,"risk_reward":2}],"rr":2,"structural_target":{"price":104,"swept":False,"accepted_beyond":False},"entry_array":{"origin_time":"2026-01-01T00:05:00Z"}};chart={"confirmed_entry":100,"stop":98,"targets":setup["targets"]};return {"decision_id":"d","analysis_candle_time":"2026-01-01T00:10:00Z","decision":{"status":"READY TO BUY"},"smc_contract":{"ownership":{"decision_owner_id":"smc","overlay_owner_id":"smc"},"setup":setup,"trade_chart":chart,"gate_funnel":{"first_blocking_gate":""}}}
def test_trade_ready_geometry_and_owner_are_validated():assert validate_trade_plan(ready())["valid"]
def test_inspector_strictly_separates_later_outcome():
    result=inspect_historical_decision(ready(),{"outcome":"TP1_HIT"});assert result["information_available_then"]["future_candles_visible"] is False and result["observed_later"]["paper_outcome"]["outcome"]=="TP1_HIT" and "unavailable" in result["observed_later"]["label"].lower()

