import hashlib,json
import pandas as pd

def structural_liquidity(swings,*,atr=0,tick_size=.01,equal_tolerance_atr=.08,equal_tolerance_ticks=3):
    tolerance=max(float(atr or 0)*equal_tolerance_atr,float(tick_size)*equal_tolerance_ticks);refs=[]
    for kind,side in (("high","buy_side"),("low","sell_side")):
        values=sorted((row for row in swings if row["type"]==kind),key=lambda x:x["candle_time"]);used=set()
        for i,row in enumerate(values):
            if i in used:continue
            cluster=[row]
            for j,other in enumerate(values[i+1:],i+1):
                if abs(float(other["price"])-float(row["price"]))<=tolerance:cluster.append(other);used.add(j)
            price=sum(float(x["price"]) for x in cluster)/len(cluster);source="equal_levels" if len(cluster)>1 else "swing";identity=hashlib.sha256(json.dumps([side,source,[x["swing_id"] for x in cluster]],sort_keys=True).encode()).hexdigest()[:20]
            refs.append({"reference_id":"liq-"+identity,"type":side,"source":source,"price":price,"touch_count":len(cluster),"member_swing_ids":[x["swing_id"] for x in cluster],"created_time":cluster[-1]["confirmation_time"],"swept":False,"accepted_beyond":False})
    return refs

def classify_reference_event(candles,reference,acceptance_buffer=0,confirmation_window=3):
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows
    if rows.empty or not reference:return {"type":"none","qualified":False,"evidence":[]}
    price=float(reference["price"]);side=reference["type"];recent=rows.tail(max(2,confirmation_window));latest=recent.iloc[-1];beyond_high=float(latest.high)>price;beyond_low=float(latest.low)<price
    wick_beyond=beyond_high if side=="buy_side" else beyond_low;closed_inside=float(latest.close)<=price if side=="buy_side" else float(latest.close)>=price;accepted=float(latest.close)>price+acceptance_buffer if side=="buy_side" else float(latest.close)<price-acceptance_buffer
    if wick_beyond and closed_inside:return {"type":"sweep","qualified":True,"direction":"bearish" if side=="buy_side" else "bullish","reference_id":reference["reference_id"],"reference_price":price,"extreme":float(latest.high if side=="buy_side" else latest.low),"event_time":_time(latest),"evidence":["Price traded beyond the reference.","The completed candle closed back inside."]}
    if accepted:return {"type":"accepted_breakout","qualified":True,"direction":"bullish" if side=="buy_side" else "bearish","reference_id":reference["reference_id"],"reference_price":price,"event_time":_time(latest),"evidence":["A completed candle closed beyond the acceptance buffer."]}
    prior=recent.iloc[:-1]
    prior_accepted=bool(((prior.close>price+acceptance_buffer) if side=="buy_side" else (prior.close<price-acceptance_buffer)).any())
    if prior_accepted and closed_inside:return {"type":"failed_breakout","qualified":True,"reference_id":reference["reference_id"],"reference_price":price,"event_time":_time(latest),"evidence":["Prior acceptance failed and price closed back inside."]}
    return {"type":"none","qualified":False,"reference_id":reference["reference_id"],"reference_price":price,"evidence":["No qualified completed-candle sweep or acceptance event."]}
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
