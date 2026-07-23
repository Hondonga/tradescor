"""Deterministic completed-candle sources for the strategy proof harness."""
from __future__ import annotations

import math
import os,tempfile
from datetime import datetime,timezone
import pandas as pd

from analysis.derived_engine import analyze_derived_index
from paper_testing.derived_paper_service import DerivedPaperService
from paper_testing.derived_paper_store import DerivedPaperStore
from validation.strategy_reachability_registry import strategy_reachability_registry
from validation.strategy_setup_proof import ChronologicalFixture


def registered_fixtures():
    fixtures=[]
    for strategy_id,spec in strategy_reachability_registry().items():
        for fixture_id in spec["fixture_ids"]:
            direction="sell" if fixture_id.endswith("_sell") or fixture_id.startswith("crash") else "buy"
            family="BOOM" if fixture_id.startswith("boom") else "CRASH" if fixture_id.startswith("crash") else spec["family"]
            behavior="breakout" if "breakout" in strategy_id else "range" if "range_reaction" in strategy_id else "sweep" if "reversal" in strategy_id or "liquidity" in strategy_id else "event" if "post_event" in strategy_id or "spike" in strategy_id else "pullback"
            frames=_focused_frames(direction) if strategy_id=="volatility_structure_pullback" else _frames(direction,behavior);m5=frames["M5"]
            indices=sorted(set(min(len(m5)-1,index) for index in (19,59,len(m5)-12,len(m5)-5,len(m5)-1)));checkpoints=tuple(m5.iloc[index].time for index in indices)
            symbol=_symbol(family);metadata={"family":family,"provider_symbol":symbol,"display_name":symbol,"proof_strategy_id":strategy_id}
            fixtures.append(ChronologicalFixture(fixture_id,strategy_id,direction,symbol,metadata,frames,checkpoints,_outcome(direction,m5.iloc[-1].time,float(m5.iloc[-1].close))))
    return fixtures


def production_evaluator(*,symbol,family,candles_by_timeframe,analysis_time):
    requested="volatility_structure_pullback" if family.get("proof_strategy_id")=="volatility_structure_pullback" else "auto"
    result=analyze_derived_index(symbol=symbol,metadata=family,candles_by_timeframe=candles_by_timeframe,tick_size=.01,analysis_time=analysis_time,requested_strategy=requested)
    return result.get("product_contract") or result
production_evaluator.production_pipeline=True


def production_paper_lifecycle(fixture,contract):
    setup=contract["setup"];confirmation=setup.get("completed_confirmation") or {};tp1=(setup.get("targets") or [None])[0];created=contract["meta"]["analysis_time"]
    legacy={"decision":{"setup_id":setup["setup_id"],"status":contract["decision"]["status"],"developing_direction":setup["direction"],"trade_ready":True,"strategy":"volatility_structure_pullback","paper_analysis_only":True},"active_trade_plan":{"entry":setup["entry"],"stop":setup["stop"],"tp1":tp1,"tp2":None,"tp1_rr":setup["rr"],"timing_state":"VALID","entry_type":"confirmation_close"},"confirmation":{"formed_at":confirmation.get("confirmed_at"),"completed":True},"ownership":contract["ownership"],"product_contract":contract}
    handle,path=tempfile.mkstemp(prefix="tradescor-proof-",suffix=".db");os.close(handle)
    try:
        service=DerivedPaperService(store=DerivedPaperStore(path),config={"enabled":True,"ambiguity":{"policy":"stop_first"},"fill":{"default_slippage_points":0}},enabled=True)
        # This harness proves paper_engine_capability (can a complete plan be
        # turned into a structurally valid paper setup) for the technical
        # reachability proof -- it must never be read as proof of real
        # strategy_paper_eligibility, so it is explicitly marked TEST_FIXTURE_ONLY.
        record=service.record_analysis(provider_symbol=fixture.symbol,display_name=fixture.symbol,family=fixture.family["family"],subfamily=fixture.family["family"],requested_strategy="volatility_structure_pullback",analysis_candle_time=created,decision_contract=legacy,candles=_paper_candles(setup,created),test_fixture_only=True)
        outcomes=service.outcomes(limit=10);detail=service.store.setup_detail(record.get("paper_setup_id")) if record.get("paper_setup_id") else None;outcome=(detail or {}).get("observed_outcome") or (outcomes[0] if outcomes else {})
        outcome_name=outcome.get("outcome") if outcome else None;filled=outcome_name in {"TP1_HIT","TP2_HIT","STOPPED","INVALIDATED_AFTER_FILL"}
        return {"paper_registered":bool(record.get("setup_registered")),"entry_filled":filled,"outcome_resolved":bool(outcome and outcome_name not in {None,"OPEN"}),"paper_setup_id":record.get("paper_setup_id"),"outcome":outcome_name,"realized_r":outcome.get("realized_r") if outcome else None,"excursion":(detail or {}).get("excursion")}
    finally:
        for suffix in ("","-wal","-shm"):
            try:os.remove(path+suffix)
            except OSError:pass


def _frames(direction,behavior):
    sign=1 if direction=="buy" else -1;start=pd.Timestamp(datetime(2026,1,1,tzinfo=timezone.utc));rows=[];price=100.0
    for index in range(720):
        phase=index%24;drift=sign*.018
        delta=(drift+math.sin(index/6)*.035) if index<600 else (math.sin(index/2)*.12 if behavior in {"range","sweep"} else drift+math.sin(index/4)*.045)
        if behavior=="pullback" and 650<=index<680:delta=-sign*.10
        if behavior=="breakout" and index==680:delta=sign*1.4
        if behavior=="breakout" and 681<=index<690:delta=-sign*.08
        if behavior=="sweep" and index==680:delta=-sign*1.2
        if behavior=="event" and index==640:delta=sign*3.5
        if index in {690,704}:delta=sign*.9
        open_=price;close=price+delta;wick=.05+abs(math.sin(phase))*.025;high=max(open_,close)+wick;low=min(open_,close)-wick
        if behavior in {"range","sweep"} and index==680:
            low-=1.1 if direction=="buy" else 0;high+=1.1 if direction=="sell" else 0
        rows.append({"time":start+pd.Timedelta(minutes=5*index),"open":open_,"high":high,"low":low,"close":close,"complete":True});price=close
    m5=pd.DataFrame(rows)
    return {"M5":m5,"M15":_resample(m5,"15min"),"H1":_resample(m5,"1h"),"H4":_resample(m5,"4h"),"D1":_resample(m5,"1D")}


def _focused_frames(direction):
    bullish=direction=="buy";end=pd.Timestamp("2026-02-01T00:00:00Z")
    h1=[]
    for base in range(100,116,2):h1 += [base,base+3,base+1]
    h1 += [116,115,120,119,118,117]
    m15=[105+i*.15+(.4 if i%6==0 else 0) for i in range(60)]+[114,115,116,117,118,119,120,121,120,119.5,119,118.5,118,117.5,117,117.2,117.4,117.6,117.8,118]
    m5=[115+(i%8)*.18 for i in range(95)]+[116,116.4,116.8,117.2,116.9,116.5,116.8,117.1,116.7,116.4,116.8,117.0,116.6,116.3,116.7,117.1,116.8,116.5,116.7,118.6,117.7,117.8,117.9,118,118.1]
    if not bullish:
        h1=[220-x for x in h1];m15=[220-x for x in m15];m5=[220-x for x in m5]
    h1f=_crafted(h1,"1h",end);m15f=_crafted(m15,"15min",end);m5f=_crafted(m5,"5min",end)
    return {"M5":m5f,"M15":m15f,"H1":h1f,"H4":_resample(h1f,"4h"),"D1":_resample(h1f,"1D")}


def _crafted(closes,freq,end):
    times=pd.date_range(end=end,periods=len(closes),freq=freq,tz="UTC");rows=[];previous=float(closes[0])
    for index,(value,time) in enumerate(zip(closes,times)):
        value=float(value);window=closes[max(0,index-2):min(len(closes),index+3)];peak=value>=max(window);valley=value<=min(window);rows.append({"time":time,"open":previous,"high":max(previous,value)+(.5 if peak else .08),"low":min(previous,value)-(.5 if valley else .08),"close":value,"complete":True});previous=value
    return pd.DataFrame(rows)


def _resample(rows,rule):
    frame=rows.set_index("time").resample(rule,label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index();frame["complete"]=True;return frame
def _symbol(family):return {"VOLATILITY":"R_75","JUMP":"JD75","STEP":"stpRNG","BOOM":"BOOM500","CRASH":"CRASH500"}.get(family,"R_75")
def _outcome(direction,start,price):
    sign=1 if direction=="buy" else -1
    return pd.DataFrame([{"time":pd.Timestamp(start)+pd.Timedelta(minutes=5*(index+1)),"open":price+sign*index*.2,"high":price+sign*(index+1)*.2+.05,"low":price+sign*(index+1)*.2-.05,"close":price+sign*(index+1)*.2,"complete":True} for index in range(12)])


def _paper_candles(setup,created):
    entry=float(setup["entry"]);stop=float(setup["stop"]);target=float(setup["targets"][0]["price"]);direction=setup["direction"];risk=abs(entry-stop);start=pd.Timestamp(created)
    if direction=="buy":values=[(entry+risk*.2,entry-risk*.1,entry),(target+risk*.05,entry,target)]
    else:values=[(entry+risk*.1,entry-risk*.2,entry),(entry,target-risk*.05,target)]
    return pd.DataFrame([{"time":start+pd.Timedelta(minutes=5*(i+1)),"open":entry,"high":max(high,low,close),"low":min(high,low,close),"close":close,"complete":True} for i,(high,low,close) in enumerate(values)])
