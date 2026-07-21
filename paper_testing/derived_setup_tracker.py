import hashlib
from datetime import datetime,timedelta,timezone
from models.derived_paper_models import DerivedPaperSetup
def registerable_paper_setup(snapshot):
    payload=snapshot.payload if hasattr(snapshot,"payload") else snapshot;setup=payload.get("setup") or {};decision=payload.get("decision") or {};direction=decision.get("developing_direction");entry=_price(setup.get("entry"));stop=_price(setup.get("stop"));tp1=_price(setup.get("tp1"));setup_id=payload.get("setup_id");risk=entry-stop if direction=="buy" and entry is not None and stop is not None else stop-entry if direction=="sell" and entry is not None and stop is not None else None
    normalized=payload.get("normalized_decision") or {};invariants=((normalized.get("diagnostics") or {}).get("invariants") or {});normalized_valid=invariants.get("valid",True)
    return bool(decision.get("trade_ready") and normalized_valid and setup_id and direction in {"buy","sell"} and entry is not None and stop is not None and tp1 is not None and risk and risk>0 and setup.get("tp1_rr") is not None and float(setup.get("tp1_rr"))>=1.5 and setup.get("timing_state") not in {"TOO_LATE","MISSED","EXTENDED"})
def build_paper_setup(snapshot,expiration_candles=12,timeframe_minutes=5):
    if not registerable_paper_setup(snapshot):return None
    payload=snapshot.payload if hasattr(snapshot,"payload") else snapshot;setup=payload["setup"];direction=payload["decision"]["developing_direction"];entry=_price(setup["entry"]);stop=_price(setup["stop"]);created=payload["created_at"];paper_id="paper-setup-"+hashlib.sha256(str(payload["setup_id"]).encode()).hexdigest()[:24]
    try:valid_until=(datetime.fromisoformat(created.replace("Z","+00:00"))+timedelta(minutes=timeframe_minutes*expiration_candles)).isoformat()
    except ValueError:valid_until=None
    confirmation=(setup.get("confirmation") or {}).get("formed_at") or (setup.get("confirmation") or {}).get("candle_time")
    return DerivedPaperSetup(paper_id,payload["decision_id"],payload["setup_id"],payload.get("selected_strategy") or "",direction,entry,stop,_price(setup["tp1"]),_price(setup.get("tp2")),abs(entry-stop),setup.get("tp1_rr"),created,confirmation,valid_until)
def _price(value):
    if isinstance(value,dict):value=value.get("price")
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None

def terminate_unfilled_setup(store,paper_setup_id,reason,terminal_time):
    """Record a pre-fill terminal state without converting it into a losing trade."""
    allowed={"expired":"SETUP_EXPIRED","invalidated_before_fill":"INVALIDATED_BEFORE_FILL","missed_entry":"MISSED_ENTRY","cancelled":"CANCELLED_BEFORE_FILL"}
    outcome=allowed.get(reason,"CANCELLED_BEFORE_FILL")
    payload={"outcome":outcome,"terminal_reason":reason,"terminal_time":str(terminal_time),"entry_filled":False,"realized_r":None,"tp1_hit":False,"tp2_hit":False,"stop_hit":False,"intracandle_ambiguous":False,"resolution_policy":"not_applicable","resolution_reason":"Setup ended before a simulated fill.","event_log":[]}
    store.save_outcome(paper_setup_id,payload);store.append_event(paper_setup_id,outcome.lower(),terminal_time,payload=payload);store.update_setup(paper_setup_id,state="resolved",last_processed_time=str(terminal_time));return payload
