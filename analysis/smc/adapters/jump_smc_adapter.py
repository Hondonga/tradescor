import hashlib,json
import pandas as pd
from analysis.smc.adapters._shared import evaluate_shared
_EVENTS={}

def detect_jump_event(candles,tick_size=.01,minimum_range_atr=3,minimum_zscore=3):
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)].reset_index(drop=True) if "complete" in rows else rows.reset_index(drop=True)
    if len(rows)<20:return {"event_id":None,"direction":None,"event_time":None,"magnitude_atr":0.0,"magnitude_ticks":0,"return_zscore":0.0,"qualified":False}
    ranges=(rows.high-rows.low).astype(float);baseline=float(ranges.iloc[:-1].tail(20).mean());std=float(ranges.iloc[:-1].tail(20).std() or 0);row=rows.iloc[-1];magnitude=float(row.high-row.low);z=(magnitude-baseline)/std if std>1e-12 else 999.0 if magnitude>baseline else 0;ratio=magnitude/max(baseline,1e-12);qualified=ratio>=minimum_range_atr and z>=minimum_zscore;direction="up" if row.close>row.open else "down" if row.close<row.open else None;time=_time(row);identity=hashlib.sha256(json.dumps([time,direction,float(row.open),float(row.close)]).encode()).hexdigest()[:20] if qualified else None
    return {"event_id":"jump-"+identity if identity else None,"direction":direction if qualified else None,"event_time":time if qualified else None,"magnitude_atr":ratio,"magnitude_ticks":magnitude/max(tick_size,1e-12),"return_zscore":z,"qualified":qualified}
def evaluate_jump_smc(*,symbol,family,candles_by_timeframe,tick_size=.01,requested_strategy="auto",**_):
    event=detect_jump_event(candles_by_timeframe.get("M5"),tick_size);previous=_EVENTS.get(symbol);new_event_invalidation={"invalidated":True,"previous_event_id":previous["event_id"],"new_event_id":event["event_id"],"reason":"A new completed abnormal event invalidated every pre-event setup."} if event.get("qualified") and previous and previous.get("event_id")!=event.get("event_id") else None
    if event.get("qualified"):_EVENTS[symbol]=event
    excluded=[event["event_time"]] if event["qualified"] else [];frames=candles_by_timeframe
    if event["qualified"]:
        cutoff=pd.Timestamp(event["event_time"]);frames={key:(rows[pd.to_datetime(rows.time,utc=True)>cutoff].copy() if rows is not None and len(rows) and "time" in rows else rows) for key,rows in candles_by_timeframe.items()}
    result=evaluate_shared(symbol=symbol,family=family,frames=frames,tick_size=tick_size,requested_strategy=requested_strategy,adapter_id="jump_smc_adapter",model_name="Jump Post-Event SMC" if event["qualified"] else "Jump Inter-Event SMC Research",fvg_supported=True,ob_supported=True,excluded_times=excluded,event=event,research_only=not event["qualified"]);result["expected_next_event_direction"]=None
    mode="JUMP_POST_EVENT_SMC" if event["qualified"] else "JUMP_INTER_EVENT_RESEARCH" if (result.get("setup") or {}).get("setup_type")=="range_reaction" else "JUMP_WAITING_FOR_FRESH_STRUCTURE"
    result["jump_mode"]=mode;result["setup"]["jump_mode"]=mode
    if mode=="JUMP_INTER_EVENT_RESEARCH":result["setup"].update(setup_type="jump_inter_event_range_reaction",research_only=True);result["decision"].update(strategy_label="Jump Inter-Event Range Reaction",research_only=True)
    if event["qualified"]:
        result["setup"].update(
            setup_type="jump_post_event_smc",
            state="WAITING_FOR_DISPLACEMENT",
            research_only=True,
            entry=None,
            stop=None,
            targets=[],
            rr=None,
            recent_event={
                "status":"Completed Jump event detected",
                "event_id":event.get("event_id"),
                "event_time":event.get("event_time"),
                "completed_direction":event.get("direction"),
                "future_direction":None,
            },
            confirmation_levels={
                "bullish":"Close above latest M5 internal swing high",
                "bearish":"Close below latest M5 internal swing low",
            },
            setup_blocker="No completed M5 displacement has formed from fresh post-event structure.",
            plan_blocker="No valid opposing structural target currently provides acceptable geometry.",
            next_required_condition="Wait for completed displacement. Do not enter solely because price reacted.",
        )
        result["decision"].update(
            status="DEVELOPING",
            strategy_label="Jump Post-Event SMC",
            research_only=True,
            trade_ready=False,
            setup_stage="WAITING_FOR_DISPLACEMENT",
            first_blocking_gate="displacement",
            next_action=result["setup"]["next_required_condition"],
        )
        result["active_trade_plan"]=None;result["m15_setup_zone"]=None;result["m5_execution_zone"]=None;result["trade_chart"].update(state="none",m15_setup_zone={"low":None,"high":None,"type":""},m5_execution_zone={"low":None,"high":None,"type":""},confirmed_entry=None,stop=None,targets=[])
    result["new_event_invalidation"]=new_event_invalidation;return result
def clear_jump_event_state():_EVENTS.clear()
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
