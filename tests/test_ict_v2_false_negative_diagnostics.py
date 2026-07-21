from datetime import datetime, timezone

import pandas as pd

from analysis.decision_engine import build_decision
from analysis.ict_displacement import detect_displacement
from analysis.ict_fvg import identify_displacement_fvg
from analysis.ict_liquidity import identify_liquidity
from analysis.ict_sweep import classify_sweep
from strategies.ict_2022_v2 import _entry_timing, _lifecycle, _setup_score


def _frame(values, freq="15min"):
    times=pd.date_range("2026-01-01",periods=len(values),freq=freq,tz="UTC")
    return pd.DataFrame([{"time":times[i],"open":o,"high":h,"low":l,"close":c} for i,(o,h,l,c) in enumerate(values)])


def test_near_equal_highs_form_normalized_buy_side_cluster():
    values=[]
    for i in range(24):
        high=101.00 if i==5 else 101.03 if i==11 else 100.5+(i%3)*.05
        low=99.7-(.25 if i in {7,17} else 0); values.append((100,high,low,100.05 if i%2 else 99.95))
    result=identify_liquidity(_frame(values),direction="sell",prominence_atr=.1,tolerance_atr=.15,tick_size=.00001)
    clusters=[row for row in result["result"]["candidate_pools"] if row["type"]=="near_equal_highs"]
    assert clusters and clusters[0]["touches"]>=2
    assert clusters[0]["tolerance_used"]>abs(101.03-101.00)


def test_liquidity_pool_must_precede_multi_candle_sweep_and_reclaim():
    rows=_frame([(100,101,99.5,100),(100,100.8,99.7,100),(100,101.3,99.9,101.1),(101.1,101.4,100.7,101.2),(101.2,101.25,100.2,100.5)])
    pool={"liquidity_id":"cluster","price":101,"formed_at":rows.iloc[0].time.isoformat()}
    result=classify_sweep(rows,pool,direction="sell",reclaim_window=4,tick_size=.01)
    assert result["valid"] and result["result"]["sweep_time"]>pool["formed_at"]
    assert result["result"]["reclaim_time"]>result["result"]["sweep_time"]


def test_multi_candle_bearish_displacement_can_pass_impulse_score():
    rows=_frame([(100,100.4,99.6,100)]*6+[(100,100.1,99.55,99.65),(99.65,99.7,98.9,99.0)])
    sweep={"confirmed":True,"sweep_time":rows.iloc[4].time.isoformat(),"reclaim_time":rows.iloc[5].time.isoformat()}
    result=detect_displacement(rows,sweep,direction="sell",body_atr_threshold=2.0,range_atr_threshold=1.0,close_location_threshold=.6,impulse_score_threshold=.5,maximum_candles=3)
    assert result["valid"] and result["result"]["candle_count"]==2
    assert result["result"]["impulse_score"]>=.5 and result["result"]["structure_level_broken"] is not None


def test_bearish_fvg_is_linked_and_filled_candidate_explains_rejection():
    rows=_frame([(101,101.2,100.5,100.8),(100.8,100.9,99.4,99.5),(99.5,100.2,99.2,99.4)])
    displacement={"displacement_id":"bear-disp","start_index":1,"candle_index":1,"start_time":rows.iloc[1].time.isoformat()}
    result=identify_displacement_fvg(rows,displacement,direction="sell",tick_size=.01)
    assert result["valid"] and result["result"]["low"]==100.2 and result["result"]["high"]==100.5
    assert result["result"]["displacement_id"]=="bear-disp"
    filled=pd.concat([rows,_frame([(99.4,100.6,99.3,100.5)],freq="15min").assign(time=rows.iloc[-1].time+pd.Timedelta(minutes=15))],ignore_index=True)
    rejected=identify_displacement_fvg(filled,displacement,direction="sell",tick_size=.01)
    assert not rejected["valid"] and any("fully mitigated" in reason for reason in rejected["diagnostics"]["rejection_reasons"])


def test_setup_quality_and_entry_timing_are_independent():
    sequence={key:"pass" for key in ("directional_draw","opposing_liquidity","liquidity_sweep","displacement","mss","fvg")}
    quality=_setup_score(sequence,"valid",{"direction":"sell"})
    assert quality>=70 and _entry_timing("WAITING_FOR_RETURN")=="waiting"


def test_completed_sequence_with_only_filled_fvg_is_missed_not_no_context():
    sequence={"liquidity_sweep":"pass","displacement":"pass","mss":"pass","fvg":"fail","htf_narrative":"waiting"}
    assert _lifecycle(sequence,{}, {},False)=="EXPIRED"


def test_incomplete_timeframes_return_precise_data_diagnostics():
    def trend(tf):
        freq={"D1":"1D","H4":"4h","H1":"1h","M15":"15min"}[tf]; times=pd.date_range("2025-01-01",periods=30,freq=freq,tz="UTC"); return pd.DataFrame([{"time":t,"open":100+i,"high":101+i,"low":99.8+i,"close":100.8+i} for i,t in enumerate(times)])
    candles={tf:trend(tf) for tf in ("D1","H4","H1","M15")}; candles["M5"]=pd.DataFrame(columns=["time","open","high","low","close"])
    decision=build_decision(symbol="EUR/USD",asset_class="forex",display_timeframe="M15",candles_by_timeframe=candles,analysis_timestamp=datetime(2026,1,1,tzinfo=timezone.utc),requested_strategy="ict_2022",session={"entry_allowed":True})
    diagnostics=decision["ict_model"]["diagnostics"]["data"]
    assert diagnostics["M5"]["validation_status"]=="unavailable"
    assert diagnostics["M5"]["candle_count"]==0 and diagnostics["M5"]["failure_reason"]
    assert all("candle_count" in diagnostics[tf] and "last_completed_candle" in diagnostics[tf] for tf in ("D1","H4","H1","M15","M5"))


def test_every_rejected_core_event_exposes_diagnostics_contract():
    rows=_frame([(100,100.2,99.8,100)]*12)
    liquidity=identify_liquidity(rows,direction="sell")
    sweep=classify_sweep(rows,None,direction="sell")
    displacement=detect_displacement(rows,None,direction="sell")
    for event in (liquidity,sweep,displacement):
        diagnostics=event["diagnostics"]
        assert set(diagnostics)=={"status","detected_candidates","selected_candidate","rejection_reasons","thresholds_used"}
        assert diagnostics["rejection_reasons"]
