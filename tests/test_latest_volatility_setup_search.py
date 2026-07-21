import pandas as pd

from analysis.volatility_latest_setup_search import LatestVolatilitySetupSearch
from validation.strategy_reachability_fixtures import _focused_frames


def test_historical_result_freezes_at_decision_and_hides_outcome(monkeypatch,tmp_path):
    frames=_focused_frames("sell");m5=frames["M5"].copy()
    # Real-provider acquisition is the service boundary; the search itself only
    # receives provider candles and never injects a decision.
    m1=m5.copy();m1["time"]=m1.time.map(lambda x:int(pd.Timestamp(x).timestamp()))
    descriptor=type("D",(),{"dataset_id":"real-cache","metadata":{"data_source_id":"deriv_public"}})()
    monkeypatch.setattr("analysis.volatility_latest_setup_search.acquire_deriv_dataset",lambda *a,**k:(descriptor,m1))
    monkeypatch.setattr("analysis.volatility_latest_setup_search._resample",lambda rows,rule: frames[{"5min":"M5","15min":"M15","1h":"H1"}[rule]].copy().reset_index(drop=True))
    monkeypatch.setattr("analysis.volatility_latest_setup_search.run_frequency_audit",lambda *a,**k:{"trade_ready_setups":[{"decision_time":m5.iloc[-1].time.isoformat()}],"counts":{"trade_ready":1,"rr_passes":1,"target_candidates":1,"entry_candidates":1},"dominant_blocker":"WAITING_FOR_PULLBACK"})
    service=LatestVolatilitySetupSearch(lambda:object(),tmp_path)
    job={"job_id":"j","symbol":"R_75","strategy":"volatility_structure_pullback","period_days":30,"processed_candles":0,"total_candles":0,"trade_ready_found":0,"state":"queued","cancel":__import__("threading").Event(),"result":None,"future_candles":None,"error":None}
    service._run(job)
    result=job["result"]
    assert job["state"]=="completed" and result["decision"]["decision"]["trade_ready"]
    assert result["label"]=="HISTORICAL SETUP" and "outcome" not in result
    cutoff=pd.Timestamp(result["decision"]["meta"]["analysis_time"])
    assert max(pd.Timestamp(row["time"]) for row in result["candles"])<=cutoff
    assert result["report"]["future_candles_excluded"] is True


def test_search_period_is_neutral_and_bounded(tmp_path):
    service=LatestVolatilitySetupSearch(lambda:object(),tmp_path)
    try: service.start(12)
    except ValueError as error: assert "30 or 90" in str(error)
    else: raise AssertionError("A profitability-selected period must not be accepted")
