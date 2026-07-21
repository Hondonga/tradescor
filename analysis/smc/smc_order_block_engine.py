import hashlib,json
import pandas as pd

def detect_order_blocks(candles,displacements,structure_events):
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)].reset_index(drop=True) if "complete" in rows else rows.reset_index(drop=True);events=[x for x in structure_events if x];result=[]
    for displacement in displacements:
        if not displacement.get("passed") or not displacement.get("structure_broken"):continue
        event=next((x for x in events if x.get("direction")==displacement.get("direction")),None)
        if not event:continue
        matches=rows.index[rows.time.astype(str)==str(displacement.get("candle_time"))].tolist();index=matches[-1] if matches else len(rows)-1
        opposing=None
        for offset in range(index-1,max(-1,index-4),-1):
            row=rows.iloc[offset]
            if displacement["direction"]=="bullish" and row.close<row.open or displacement["direction"]=="bearish" and row.close>row.open:opposing=row;break
        if opposing is None:continue
        identity=hashlib.sha256(json.dumps([displacement["displacement_id"],event["structure_event_id"],_time(opposing)],default=str).encode()).hexdigest()[:20]
        result.append({"order_block_id":"ob-"+identity,"direction":displacement["direction"],"high":float(opposing.high),"low":float(opposing.low),"origin_time":_time(opposing),"displacement_id":displacement["displacement_id"],"structure_event_id":event["structure_event_id"],"mitigated":False,"invalidated":False,"invalidation_boundary":float(opposing.low if displacement["direction"]=="bullish" else opposing.high),"quality_score":min(1,(displacement.get("body_atr",0)+displacement.get("close_location",0))/2)})
    return result
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)

