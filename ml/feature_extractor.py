from __future__ import annotations
import hashlib,json
import numpy as np
import pandas as pd
from ml.models import FeatureSnapshot
from ml.feature_schema import SCHEMA_VERSION,ENGINE_VERSION,CATEGORICAL
from ml.candle_sequence_encoder import encode_m5_sequence

ELIGIBLE={"DIRECTIONAL_CONTEXT","WAITING_FOR_PULLBACK","WAITING_FOR_DISPLACEMENT","WAITING_FOR_M5_BREAK","WAITING_FOR_ENTRY","PLAN_VALIDATION","TRADE_READY","READY_TO_BUY","READY_TO_SELL","WAITING_FOR_LOCATION"}

def extract_snapshot(*,decision,frames,dataset_id,config_hash,sequence_length=64):
    at=pd.Timestamp(decision["meta"]["analysis_time"]);stage=_stage(decision);direction=(decision.get("decision") or {}).get("direction");readiness=(decision.get("readiness") or {}).get("state")
    if stage not in ELIGIBLE or direction not in {"buy","sell"} or readiness in {"stale","insufficient","error"}:return None
    inv=((decision.get("diagnostics") or {}).get("invariants") or {});setup=decision.get("setup") or {}
    if inv.get("valid") is False and setup.get("trade_ready"):return None
    h1=_cut(frames.get("H1"),at);m15=_cut(frames.get("M15"),at);m5=_cut(frames.get("M5"),at);current=float(m5.iloc[-1].close);h1d=(decision["diagnostics"].get("h1") or {});m15d=(decision["diagnostics"].get("m15") or {});m5d=(decision["diagnostics"].get("m5") or {});target=(setup.get("targets") or [setup.get("projected_target") or {}])[0] or {}
    h1atr=_atr(h1);m15atr=_atr(m15);m5atr=_atr(m5);last_h1=h1d.get("last_break") or {};confirmation=m5d.get("confirmation") or {};entry=setup.get("projected_entry");stop=setup.get("projected_stop");tp=target.get("price");zone=m5d.get("entry_zone") or {}
    features={
      "h1_external_structure":_cat("h1_external_structure",decision["market"].get("external_structure")),"h1_active_leg_direction":1 if h1d.get("direction")=="bullish" else -1,"h1_active_leg_distance_atr":_ratio(current,((last_h1.get("broken_swing") or {}).get("price")),h1atr),"h1_active_leg_age":_age(h1,last_h1.get("confirmed_at")),"h1_latest_bos_direction":1 if last_h1.get("direction")=="bullish" else -1 if last_h1.get("direction")=="bearish" else 0,"h1_latest_bos_age":_age(h1,last_h1.get("confirmed_at")),"h1_swing_high_distance_atr":_swing_distance(h1,current,"high",h1atr),"h1_swing_low_distance_atr":_swing_distance(h1,current,"low",h1atr),"h1_atr":h1atr,"h1_directional_efficiency":_efficiency(h1),"h1_overlap_ratio":_overlap(h1),
      "m15_condition":_cat("m15_condition",m15d.get("condition")),"m15_pullback_depth_pct":m15d.get("depth"),"m15_pullback_depth_atr":_n((float(m15d.get("range_high",current))-float(m15d.get("range_low",current)))*float(m15d.get("depth") or 0),m15atr),"m15_setup_distance_atr":_zone_distance(current,zone,m15atr),"m15_premium_discount":_position(current,m15d.get("range_low"),m15d.get("range_high")),"m15_swing_high_distance_atr":_swing_distance(m15,current,"high",m15atr),"m15_swing_low_distance_atr":_swing_distance(m15,current,"low",m15atr),"m15_displacement_strength":_last_body_atr(m15,m15atr),"m15_range_width_atr":_n(float(m15d.get("range_high",current))-float(m15d.get("range_low",current)),m15atr),"m15_location_valid":int(bool(m15d.get("valid_location"))),
      "m5_displacement_body_atr":_last_body_atr(m5,m5atr),"m5_displacement_range_atr":_n(float(m5.iloc[-1].high-m5.iloc[-1].low),m5atr),"m5_close_location":_close_location(m5.iloc[-1]),"m5_directional_close_count":_directional_count(m5,direction),"m5_bos":int(bool(confirmation)),"m5_mss":int(bool(confirmation)),"m5_structure_break_distance_atr":_ratio(current,confirmation.get("broken_price"),m5atr),"m5_retracement_depth":_position(current,zone.get("low"),zone.get("high")),"m5_entry_distance_atr":_ratio(current,entry,m5atr),"m5_stop_distance_atr":_ratio(entry,stop,m5atr),"m5_target_distance_atr":_ratio(entry,tp,m5atr),"m5_target_timeframe":_cat("target_timeframe",target.get("timeframe")),"m5_tp1_rr":target.get("risk_reward") or setup.get("projected_rr"),"m5_chase_distance_atr":_ratio(current,entry,m5atr),"m5_confirmation_age":_age(m5,confirmation.get("confirmed_at")),"target_source":target.get("source") or target.get("source_type") or "","target_age":_age(m5,target.get("confirmed_at")),"target_consumed":int(bool(target.get("consumed"))),
      "returns_5":_ret(m5,5),"returns_10":_ret(m5,10),"returns_20":_ret(m5,20),"returns_50":_ret(m5,50),"rolling_volatility":float(m5.close.astype(float).pct_change().tail(20).std() or 0),"rolling_directional_efficiency":_efficiency(m5.tail(20))}
    setup_id=setup.get("setup_id");context_id=_context_id(decision);identity=[dataset_id,decision["meta"]["symbol"],stage,setup_id,context_id,at.isoformat()];snapshot_id="mlsnap-"+hashlib.sha256(json.dumps(identity,default=str).encode()).hexdigest()[:24]
    sequence_rows=m5.tail(int(sequence_length));metadata={"schema_version":SCHEMA_VERSION,"snapshot_id":snapshot_id,"dataset_id":dataset_id,"symbol":decision["meta"]["symbol"],"strategy_id":"volatility_structure_pullback","direction":direction,"decision_time":at.isoformat(),"stage":stage,"setup_id":setup_id,"structural_context_id":context_id,"directional_leg_id":_leg_id(last_h1),"config_hash":config_hash,"engine_version":ENGINE_VERSION,"trade_ready":bool((decision.get("decision") or {}).get("trade_ready")),"quality_grade":setup.get("quality_grade"),"structure_state":decision["market"].get("external_structure"),"volatility_regime":_vol_regime(m5),"sequence_start_time":pd.Timestamp(sequence_rows.iloc[0].time).isoformat() if len(sequence_rows) else None,"sequence_end_time":at.isoformat(),"sequence_completed_candles":len(sequence_rows)}
    return FeatureSnapshot(metadata,features,encode_m5_sequence(m5,at,sequence_length),at.isoformat())

def _stage(d):
    stage=str((d.get("decision") or {}).get("stage") or (d.get("setup") or {}).get("stage") or "").upper()
    if stage=="NO_DIRECTIONAL_CONTEXT":return ""
    if stage=="WAITING_FOR_LOCATION":return "WAITING_FOR_PULLBACK"
    if stage=="WAITING_FOR_DISPLACEMENT" and (((d.get("diagnostics") or {}).get("m5") or {}).get("displacement_seen")):return "WAITING_FOR_M5_BREAK"
    if stage in {"READY_TO_BUY","READY_TO_SELL"}:return "TRADE_READY"
    return stage
def _cut(rows,at):
    x=rows.copy();x=x[x.complete.astype(bool)] if "complete" in x else x;return x[pd.to_datetime(x.time,utc=True)<=at].sort_values("time")
def _atr(x):return float((x.high.astype(float)-x.low.astype(float)).tail(14).mean()) if len(x) else 0
def _n(v,d):return float(v)/float(d) if v is not None and d else None
def _ratio(a,b,d):return _n(abs(float(a)-float(b)),d) if a is not None and b is not None else None
def _age(rows,time):
    if not time:return None
    return int((pd.to_datetime(rows.time,utc=True)>pd.Timestamp(time)).sum())
def _cat(name,value):return CATEGORICAL[name].get(str(value or ""),0)
def _ret(x,n):return float(x.iloc[-1].close/x.iloc[-min(n,len(x))].close-1) if len(x) else None
def _efficiency(x):
    closes=x.close.astype(float);travel=closes.diff().abs().sum();return float(abs(closes.iloc[-1]-closes.iloc[0])/travel) if len(x)>1 and travel else 0
def _overlap(x):
    x=x.tail(20);return float(np.mean([max(0,min(a.high,b.high)-max(a.low,b.low))/max(a.high-a.low,b.high-b.low,1e-12) for (_,a),(_,b) in zip(x.iloc[:-1].iterrows(),x.iloc[1:].iterrows())])) if len(x)>1 else 0
def _swing_distance(x,current,kind,atr):return _ratio(current,float(x.high.tail(20).max()) if kind=="high" else float(x.low.tail(20).min()),atr) if len(x) else None
def _zone_distance(current,z,atr):return 0 if z and z.get("low")<=current<=z.get("high") else _ratio(current,z.get("low") if current<(z or {}).get("low",current) else z.get("high"),atr) if z else None
def _position(v,lo,hi):return (float(v)-float(lo))/max(float(hi)-float(lo),1e-12) if v is not None and lo is not None and hi is not None else None
def _last_body_atr(x,atr):return _n(abs(float(x.iloc[-1].close-x.iloc[-1].open)),atr) if len(x) else None
def _close_location(r):return float((r.close-r.low)/max(r.high-r.low,1e-12))
def _directional_count(x,d):return int(((x.close>x.open) if d=="buy" else (x.close<x.open)).tail(10).sum())
def _context_id(d):return "ctx-"+hashlib.sha256(json.dumps([(d.get("market") or {}).get("external_structure"),((d.get("diagnostics") or {}).get("h1") or {}).get("last_break")],default=str,sort_keys=True).encode()).hexdigest()[:16]
def _leg_id(event):return "leg-"+hashlib.sha256(json.dumps(event,default=str,sort_keys=True).encode()).hexdigest()[:16]
def _vol_regime(x):
    ranges=(x.high-x.low).astype(float);recent=float(ranges.tail(14).mean());base=float(ranges.tail(50).mean());return "high" if base and recent>base*1.25 else "low" if base and recent<base*.75 else "normal"
