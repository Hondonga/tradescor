import hashlib,json
import pandas as pd

def analyze_structure(candles,swings,displacement=None,liquidity_event=None,buffer=0):
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows
    highs=[x for x in swings if x["type"]=="high"];lows=[x for x in swings if x["type"]=="low"];last_close=float(rows.iloc[-1].close) if len(rows) else None;disp=displacement or {};last_bos=None;last_mss=None
    high=highs[-1] if highs else None;low=lows[-1] if lows else None
    if last_close is not None and disp.get("passed") and high and last_close>float(high["price"])+buffer and disp.get("direction")=="bullish" and not _consumed(rows,high,"bullish",buffer):last_bos=_event("bos","bullish",high,rows.iloc[-1])
    elif last_close is not None and disp.get("passed") and low and last_close<float(low["price"])-buffer and disp.get("direction")=="bearish" and not _consumed(rows,low,"bearish",buffer):last_bos=_event("bos","bearish",low,rows.iloc[-1])
    sweep=liquidity_event or {}
    if sweep.get("type")=="sweep" and disp.get("passed"):
        if sweep.get("direction")=="bullish" and high and last_close>float(high["price"])+buffer:last_mss=_event("mss","bullish",high,rows.iloc[-1],sweep)
        elif sweep.get("direction")=="bearish" and low and last_close<float(low["price"])-buffer:last_mss=_event("mss","bearish",low,rows.iloc[-1],sweep)
    direction=(last_bos or last_mss or {}).get("direction");range_evidence=_range_evidence(rows,highs,lows,last_bos,disp);external=direction if direction else "range" if range_evidence["valid"] else "transition" if disp.get("passed") else "compression";internal=(last_mss or last_bos or {}).get("direction") or external
    return {"external_structure":external,"internal_structure":internal,"last_bos":last_bos,"last_mss":last_mss,"active_leg":{"low":low,"high":high,"direction":disp.get("direction"),"displacement_passed":bool(disp.get("passed"))},"range_evidence":range_evidence,"classification_evidence":{"range":range_evidence,"bearish":bool(direction=="bearish"),"bullish":bool(direction=="bullish"),"transition":bool(external=="transition"),"compression":bool(external=="compression")},"structure_conflict":bool(last_bos and last_mss and last_bos["direction"]!=last_mss["direction"])}
def _range_evidence(rows,highs,lows,last_bos,displacement):
    high=highs[-1] if highs else None;low=lows[-1] if lows else None;upper=float(high["price"]) if high else None;lower=float(low["price"]) if low else None;events=sorted([("high",x.get("confirmation_time") or x.get("candle_time")) for x in highs[-3:]]+[("low",x.get("confirmation_time") or x.get("candle_time")) for x in lows[-3:]],key=lambda x:str(x[1]));alternations=sum(a[0]!=b[0] for a,b in zip(events,events[1:]));bounded=bool(upper is not None and lower is not None and lower<upper and len(rows) and rows.tail(min(20,len(rows))).close.astype(float).between(lower,upper).mean()>=.8);accepted=bool(last_bos);valid=bool(upper is not None and lower is not None and alternations>=2 and bounded and not accepted and not displacement.get("passed"))
    return {"valid_upper_boundary":upper is not None,"valid_lower_boundary":lower is not None,"upper_boundary":upper,"lower_boundary":lower,"alternating_interactions":alternations,"sufficient_alternating_interaction":alternations>=2,"bounded_price_behavior":bounded,"accepted_directional_breakout":accepted,"directional_displacement":displacement.get("direction") if displacement.get("passed") else None,"valid":valid}
def _event(kind,direction,reference,row,sweep=None):
    time=_time(row);identity=hashlib.sha256(json.dumps([kind,direction,reference["swing_id"],time],default=str).encode()).hexdigest()[:20];return {"structure_event_id":kind+"-"+identity,"type":kind,"direction":direction,"broken_swing_id":reference["swing_id"],"broken_price":reference["price"],"confirmed_at":time,"completed_close":float(row.close),"sweep_id":(sweep or {}).get("reference_id")}
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
def _consumed(rows,reference,direction,buffer):
    prior=rows.iloc[:-1]
    if prior.empty:return False
    try:prior=prior[pd.to_datetime(prior.time,utc=True)>=pd.Timestamp(reference.get("confirmation_time"))]
    except (ValueError,TypeError):pass
    return bool((prior.close.astype(float)>float(reference["price"])+buffer).any()) if direction=="bullish" else bool((prior.close.astype(float)<float(reference["price"])-buffer).any())
