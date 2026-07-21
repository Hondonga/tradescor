from __future__ import annotations
import pandas as pd
from paper_testing.derived_fill_engine import evaluate_paper_fill
from paper_testing.derived_outcome_resolver import resolve_paper_outcome
from paper_testing.derived_mfe_mae_tracker import track_mfe_mae

EMPTY={"outcome_label":None,"entry_filled":None,"tp1_before_stop":None,"tp2_before_stop":None,"realized_r":None,"mfe_r":None,"mae_r":None,"candles_to_entry":None,"candles_to_tp1":None,"candles_to_tp2":None,"candles_to_stop":None,"candles_to_expiration":None}

def label_trade_plan(decision,future_m5,expiration_candles=12):
    plan=decision.get("trade_plan") or {};targets=plan.get("targets") or []
    if not plan.get("available") or not targets:return dict(EMPTY)
    created=pd.Timestamp(decision["meta"]["analysis_time"]);setup={"created_at":created.isoformat(),"entry_valid_until":(created+pd.Timedelta(minutes=5*expiration_candles)).isoformat(),"direction":decision["decision"]["direction"],"entry":plan["entry"],"stop":plan["stop"],"tp1":targets[0]["price"],"tp2":targets[1]["price"] if len(targets)>1 else None,"risk_points":abs(float(plan["entry"])-float(plan["stop"]))}
    fill=evaluate_paper_fill(setup,future_m5,entry_type="confirmation_close")
    if not fill["filled"]:return {**EMPTY,"outcome_label":"ENTRY_NOT_FILLED","entry_filled":0,"candles_to_expiration":expiration_candles}
    outcome=resolve_paper_outcome(setup,future_m5,fill["fill_time"],policy="stop_first");exc=track_mfe_mae(setup,future_m5,fill["fill_time"],resolved_time=outcome.get("terminal_time"));events=outcome.get("event_log") or []
    label="AMBIGUOUS" if outcome.get("intracandle_ambiguous") else "ENTRY_FILLED_TP2" if outcome.get("tp2_hit") else "ENTRY_FILLED_TP1" if outcome.get("tp1_hit") else "ENTRY_FILLED_STOP" if outcome.get("stop_hit") else "EXPIRED"
    return {"outcome_label":label,"entry_filled":1,"tp1_before_stop":int(bool(outcome.get("tp1_hit"))),"tp2_before_stop":int(bool(outcome.get("tp2_hit"))),"realized_r":outcome.get("realized_r"),"mfe_r":exc.get("mfe_r"),"mae_r":exc.get("mae_r"),"candles_to_entry":_candles(created,fill.get("fill_time")),"candles_to_tp1":_event_candles(created,events,"tp1_hit"),"candles_to_tp2":_event_candles(created,events,"tp2_hit"),"candles_to_stop":_event_candles(created,events,"stop_hit"),"candles_to_expiration":expiration_candles if label=="EXPIRED" else None}

def label_progression(snapshot,later_snapshots):
    stages=[row.metadata.get("stage") for row in later_snapshots if row.metadata.get("direction")==snapshot.metadata.get("direction") and row.metadata.get("structural_context_id")==snapshot.metadata.get("structural_context_id")]
    return {"reached_valid_location":int(any(x in stages for x in ("WAITING_FOR_DISPLACEMENT","WAITING_FOR_M5_BREAK","WAITING_FOR_ENTRY","PLAN_VALIDATION","TRADE_READY"))),"reached_displacement":int(any(x in stages for x in ("WAITING_FOR_M5_BREAK","WAITING_FOR_ENTRY","PLAN_VALIDATION","TRADE_READY"))),"reached_structure_confirmation":int(any(x in stages for x in ("WAITING_FOR_ENTRY","PLAN_VALIDATION","TRADE_READY"))),"reached_trade_ready":int("TRADE_READY" in stages),"never_progressed":int(not stages),"progression_invalidated":int("INVALIDATED" in stages)}
def _candles(a,b):return int((pd.Timestamp(b)-pd.Timestamp(a)).total_seconds()//300) if b else None
def _event_candles(created,events,name):
    row=next((x for x in events if x.get("event")==name),None);return _candles(created,row.get("time")) if row else None
