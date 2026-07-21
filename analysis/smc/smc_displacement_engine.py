import hashlib,json
import pandas as pd

def measure_displacement(candles,*,atr=None,tick_size=.01,direction=None,structure_broken=False,minimum_body_atr=.6,minimum_range_atr=.8,minimum_close_location=.7):
    rows=_completed(candles)
    if rows.empty:return _empty()
    row=rows.iloc[-1];atr=float(atr or _atr(rows) or tick_size);body=float(row.close-row.open);inferred="bullish" if body>0 else "bearish" if body<0 else "neutral";direction=direction or inferred;span=max(float(row.high-row.low),1e-12);close_location=(float(row.close-row.low)/span) if direction=="bullish" else float(row.high-row.close)/span;consecutive=0
    for _,candidate in rows.iloc[::-1].iterrows():
        if direction=="bullish" and candidate.close>candidate.open or direction=="bearish" and candidate.close<candidate.open:consecutive+=1
        else:break
    body_atr=abs(body)/atr;range_atr=span/atr;ticks=int(round(span/max(float(tick_size),1e-12)));passed=direction in {"bullish","bearish"} and body_atr>=minimum_body_atr and range_atr>=minimum_range_atr and close_location>=minimum_close_location
    identity=hashlib.sha256(json.dumps([_time(row),direction,float(row.open),float(row.close)],default=str).encode()).hexdigest()[:20]
    return {"displacement_id":"disp-"+identity,"direction":direction,"candle_time":_time(row),"body_atr":body_atr,"range_atr":range_atr,"close_location":close_location,"consecutive_closes":consecutive,"structure_broken":bool(structure_broken),"fvg_created":False,"distance_ticks":ticks,"overlap_ratio":_overlap(rows),"passed":bool(passed)}
def _empty():return {"displacement_id":None,"direction":"","body_atr":0.0,"range_atr":0.0,"close_location":0.0,"consecutive_closes":0,"structure_broken":False,"fvg_created":False,"distance_ticks":0,"overlap_ratio":None,"passed":False}
def _completed(rows):
    rows=rows.copy() if rows is not None else pd.DataFrame();return rows[rows.complete.astype(bool)].reset_index(drop=True) if "complete" in rows else rows.reset_index(drop=True)
def _atr(rows):return float((rows.high-rows.low).tail(14).mean()) if len(rows) else None
def _overlap(rows):
    if len(rows)<2:return None
    a,b=rows.iloc[-2],rows.iloc[-1];overlap=max(0,min(a.high,b.high)-max(a.low,b.low));return float(overlap/max(min(a.high-a.low,b.high-b.low),1e-12))
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)

