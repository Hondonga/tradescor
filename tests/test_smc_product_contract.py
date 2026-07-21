import pandas as pd
from analysis.smc.smc_product_contract import build_smc_product_contract
from analysis.smc.smc_data_readiness import evaluate_data_readiness

def candles(count,seconds):
    times=pd.date_range("2026-01-01",periods=count,freq=f"{seconds}s",tz="UTC")
    return pd.DataFrame({"time":times,"open":range(count),"high":[x+1 for x in range(count)],"low":[x-.5 for x in range(count)],"close":[x+.5 for x in range(count)],"complete":True})

def frames():return {"M1":candles(60,60),"M5":candles(60,300),"M15":candles(40,900),"H1":candles(20,3600),"H4":candles(6,14400),"D1":candles(2,86400)}

def result(ready=False):
    setup={"setup_id":"setup-1","state":"TRADE_READY" if ready else "WAITING_FOR_RETRACE","direction":"buy","entry_array":{"low":10,"high":11,"type":"order_block","origin_time":"2026-01-01T00:00:00Z","invalidation_boundary":9},"entry":10.5 if ready else None,"stop":9 if ready else None,"targets":[{"name":"TP1","price":13,"risk_reward":1.67}] if ready else [],"rr":1.67 if ready else None,"bos":{"structure_event_id":"bos-1","direction":"bullish"} if ready else None,"structural_target":{"price":13,"type":"buy_side","swept":False},"next_required_condition":"Wait for price to enter the area.","research_only":False}
    return {"ownership":{"requested_strategy_id":"auto","selected_strategy_id":"smc_auto","decision_owner_id":"smc_auto","overlay_owner_id":"smc_auto","adapter_id":"volatility_smc_adapter","selection_mode":"auto"},"setup":setup,"structure":{"external_structure":"bullish","internal_structure":"bullish"},"scoring":{"valid":True,"quality_score":72,"quality_grade":"B","essential_failures":[]},"invariants":{"valid":True,"failures":[]},"liquidity":[],"swings":[],"displacements":[],"fvgs":[],"order_blocks":[],"trade_chart":{"current_price":10.2}}

def test_data_readiness_excludes_incomplete_future_and_reports_duplicates():
    rows=frames();rows["M1"]=pd.concat([rows["M1"],rows["M1"].tail(1)],ignore_index=True)
    readiness=evaluate_data_readiness(rows,pd.Timestamp("2026-02-01",tz="UTC"))
    assert readiness["state"]=="insufficient" and readiness["duplicate_intervals"]

def test_product_contract_has_one_owner_and_no_actionable_levels_before_ready():
    contract=build_smc_product_contract(symbol="R_75",display_symbol="Volatility 75 Index",timeframe="M5",analysis_time="2026-02-01T00:00:00Z",family={"family":"VOLATILITY","variant":"VOLATILITY_75"},candles_by_timeframe=frames(),result=result(False))
    owner=contract["ownership"]
    assert owner["selected_model_id"]==owner["decision_owner_id"]==owner["overlay_owner_id"]
    assert contract["setup"]["entry"] is None
    assert not any(row["type"] in {"entry","stop","target"} for row in contract["overlays"])

def test_ready_contract_uses_only_backend_plan_and_owner_tagged_overlays():
    contract=build_smc_product_contract(symbol="R_75",display_symbol="Volatility 75 Index",timeframe="M5",analysis_time="2026-02-01T00:00:00Z",family={"family":"VOLATILITY","variant":"VOLATILITY_75"},candles_by_timeframe=frames(),result=result(True))
    assert contract["decision"]["status"]=="READY TO BUY"
    assert contract["setup"]["entry"]==10.5
    assert {x["type"] for x in contract["overlays"]}>={"entry","stop","tp1"}
    assert all(x["owner_id"]==contract["ownership"]["overlay_owner_id"] for x in contract["overlays"])
