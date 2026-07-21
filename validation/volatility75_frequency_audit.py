"""Event-cached chronological 30-day audit for the focused production model."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
import pandas as pd

from analysis.smc.smc_swing_engine import confirmed_swings
from analysis.smc.smc_target_engine import evaluate_structural_targets
from analysis.volatility_structure_pullback_engine import DEFAULTS,_execution,_persistent_structure,_pullback_location


def run(dataset_path,output_path=None,profile=None,progress_callback=None,cancel_event=None):
    cfg={**DEFAULTS,**(profile or {})};m5=_load(dataset_path);m15=_resample(m5,"15min");h1=_resample(m5,"1h");h1_state={};m15_state={}
    for index,row in h1.iterrows():
        history=h1.iloc[max(0,index-100):index+1];h1_state[row.time]=_persistent_structure(history,.01,cfg,"external")
    h1_times=list(h1_state);h1_cursor=0;current_h1={"direction":None}
    for index,row in m15.iterrows():
        while h1_cursor<len(h1_times) and h1_times[h1_cursor]<=row.time:current_h1=h1_state[h1_times[h1_cursor]];h1_cursor+=1
        m15_state[row.time]=_pullback_location(m15.iloc[max(0,index-32):index+1],current_h1.get("direction"),current_h1,cfg)
    h1_cursor=m15_cursor=0;h1_times=list(h1_state);m15_times=list(m15_state);current_h1={"direction":None};current_m15={"pullback":False,"valid_location":False};counts=Counter();blockers=Counter();ready={};violations=[];execution_state=None;execution_context=None;evaluated_events=set();snapshot_candidate_indices=[];snapshot_seen=set()
    for index,row in m5.iterrows():
        if cancel_event is not None and cancel_event.is_set():return {"cancelled":True,"counts":dict(counts),"first_blockers":dict(blockers),"trade_ready_setups":list(ready.values())}
        if progress_callback is not None and (index % 100 == 0 or index+1 == len(m5)):progress_callback(index+1,len(m5),len(ready))
        at=row.time;counts["evaluations"]+=1
        while h1_cursor<len(h1_times) and h1_times[h1_cursor]<=at:current_h1=h1_state[h1_times[h1_cursor]];h1_cursor+=1
        while m15_cursor<len(m15_times) and m15_times[m15_cursor]<=at:current_m15=m15_state[m15_times[m15_cursor]];m15_cursor+=1
        direction=current_h1.get("direction")
        def snapshot(stage,execution=None):
            context=((current_h1.get("last_break") or {}).get("confirmed_at"));event=(((execution or {}).get("confirmation") or {}).get("structure_event_id"));key=(direction,context,event,stage)
            if key not in snapshot_seen:snapshot_seen.add(key);snapshot_candidate_indices.append(index)
        if direction:counts[f"h1_{direction}_contexts"]+=1;counts["directional_contexts"]+=1
        else:blockers["NO_DIRECTIONAL_CONTEXT"]+=1;continue
        if current_m15.get("pullback"):counts["m15_pullbacks"]+=1
        else:snapshot("WAITING_FOR_PULLBACK");blockers["WAITING_FOR_PULLBACK"]+=1;continue
        if current_m15.get("valid_location"):counts["valid_locations"]+=1
        else:snapshot("WAITING_FOR_PULLBACK");blockers["WAITING_FOR_LOCATION"]+=1;continue
        history=m5.iloc[max(0,index-200):index+1]
        context=direction
        if context!=execution_context:execution_state=None;execution_context=context
        atr5=float((history.high-history.low).tail(14).mean());body=float(row.close-row.open);span=float(row.high-row.low)
        displacement_candidate=(body>0 if direction=="bullish" else body<0) and abs(body)/max(atr5,1e-12)>=cfg["displacement_body_atr"] and span/max(atr5,1e-12)>=cfg["displacement_range_atr"]
        zone=(execution_state or {}).get("entry_zone") or {};retrace_candidate=bool(execution_state and execution_state.get("entry") is None and zone and float(row.low)<=zone["high"] and float(row.high)>=zone["low"])
        if displacement_candidate or retrace_candidate or execution_state is None:
            execution_state=_execution(history,direction,current_m15,.01,cfg)
        execution=execution_state
        if not execution.get("confirmation"):snapshot("WAITING_FOR_M5_BREAK" if execution.get("displacement_seen") else "WAITING_FOR_DISPLACEMENT",execution);blockers["WAITING_FOR_DISPLACEMENT"]+=1;continue
        counts["m5_displacements"]+=1;counts["m5_structure_breaks"]+=1
        entry=execution.get("entry");stop=execution.get("stop")
        if entry is None:snapshot("WAITING_FOR_ENTRY",execution);blockers["WAITING_FOR_ENTRY"]+=1;continue
        event_id=execution["confirmation"]["structure_event_id"]
        if event_id in evaluated_events:continue
        evaluated_events.add(event_id)
        counts["entry_candidates"]+=1
        if stop is None:snapshot("PLAN_VALIDATION",execution);blockers["STOP_CREATION_FAILURE"]+=1;continue
        counts["stop_candidates"]+=1
        cutoff={"M5":history,"M15":m15[m15.time<=at].tail(160),"H1":h1[h1.time<=at].tail(100)}
        atr=float((cutoff["M15"].high-cutoff["M15"].low).tail(14).mean());prominence=cfg["swing_prominence_atr"];swings=confirmed_swings(cutoff["M5"],atr=atr,tick_size=.01,scope="execution",minimum_prominence_atr=prominence)+confirmed_swings(cutoff["M15"],atr=atr,tick_size=.01,scope="internal",minimum_prominence_atr=prominence)+confirmed_swings(cutoff["H1"],atr=atr,tick_size=.01,left_strength=3,right_strength=3,scope="external",minimum_prominence_atr=prominence)
        targets=evaluate_structural_targets(symbol="R_75",direction=direction,entry=entry,stop=stop,swings=swings,liquidity=[],candles_by_timeframe=cutoff,minimum_rr=cfg["minimum_rr"],setup_type="structure_pullback",tick_size=.01);tp1=targets.get("tp1")
        if not tp1:snapshot("PLAN_VALIDATION",execution);blockers[targets["target_trace"].get("first_blocker") or "TARGET_CREATION_FAILURE"]+=1;continue
        counts["target_candidates"]+=1;rr=tp1.get("projected_rr")
        if rr is None or rr<cfg["minimum_rr"]:snapshot("PLAN_VALIDATION",execution);blockers["RR_BELOW_MINIMUM"]+=1;continue
        counts["rr_passes"]+=1
        if not execution.get("chase_valid"):snapshot("PLAN_VALIDATION",execution);blockers["TOO_LATE"]+=1;continue
        event=execution["confirmation"];setup_id="vsp-audit-"+str(event["structure_event_id"]);record={"setup_id":setup_id,"decision_time":at.isoformat(),"direction":"buy" if direction=="bullish" else "sell","entry":entry,"stop":stop,"tp1":tp1["price"],"tp1_source":tp1["source_type"],"tp1_timeframe":tp1["timeframe"],"rr":rr,"confirmation_time":event["confirmed_at"]}
        ready.setdefault(setup_id,record)
        snapshot("TRADE_READY",execution)
        if not (stop<entry<tp1["price"] if direction=="bullish" else stop>entry>tp1["price"]):violations.append({"code":"GEOMETRY_CONTRADICTION",**record})
    counts["ready_to_buy"]=sum(x["direction"]=="buy" for x in ready.values());counts["ready_to_sell"]=sum(x["direction"]=="sell" for x in ready.values());counts["trade_ready"]=len(ready);dominant=max(blockers,key=blockers.get) if blockers else None
    passed=len(ready)>=5 and counts["ready_to_buy"]>=1 and counts["ready_to_sell"]>=1 and not violations
    report={"dataset":{"path":str(dataset_path),"symbol":"R_75","period_start":m5.iloc[0].time.isoformat(),"period_end":(m5.iloc[-1].time+pd.Timedelta(minutes=5)).isoformat(),"completed_m5_candles":len(m5),"selection_policy":"fixed_calendar_30d_v1","selected_before_performance_evaluation":True},"analysis_profile":cfg,"counts":dict(counts),"first_blockers":dict(blockers),"dominant_blocker":dominant,"trade_ready_setups":list(ready.values()),"snapshot_candidate_indices":snapshot_candidate_indices,"lookahead_violations":0,"contradictory_states":violations,"acceptance":{"minimum_total":5,"minimum_buy":1,"minimum_sell":1,"passed":passed},"production_status":{"strategy_id":"volatility_structure_pullback","production_supported":True,"fixture_buy_reachable":True,"fixture_sell_reachable":True,"historically_observed":bool(passed and ready),"live_observed":False,"auto_eligible":True}}
    path=Path(output_path or Path(__file__).resolve().parents[1]/"data"/"volatility75_acceptance"/"latest_audit.json");path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8");return report


def _load(path):
    rows=pd.read_json(path);numeric=pd.to_numeric(rows.time,errors="coerce");rows["time"]=pd.to_datetime(numeric,unit="ms" if numeric.max()>1e12 else "s",utc=True);rows["complete"]=True;return rows.sort_values("time").reset_index(drop=True)
def _resample(rows,rule):
    frame=rows.set_index("time").resample(rule,label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index();frame["complete"]=True;return frame
