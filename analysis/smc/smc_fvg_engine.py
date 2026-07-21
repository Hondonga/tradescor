import hashlib,json
import pandas as pd

def detect_fvgs(candles,*,atr=None,tick_size=.01,minimum_gap_ticks=2,minimum_gap_atr=.05,displacements=None,excluded_times=None,supported=True,research_only=False):
    if not supported:return []
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)].reset_index(drop=True) if "complete" in rows else rows.reset_index(drop=True);atr=float(atr or ((rows.high-rows.low).tail(14).mean() if len(rows) else tick_size));excluded={str(x) for x in (excluded_times or [])};disp_times={str(x.get("candle_time")) for x in (displacements or []) if x.get("passed")};result=[]
    for index in range(2,len(rows)):
        one,two,three=rows.iloc[index-2],rows.iloc[index-1],rows.iloc[index];times=[_time(one),_time(two),_time(three)]
        if any(str(x) in excluded for x in times):continue
        if float(three.low)>float(one.high):direction="bullish";low=float(one.high);high=float(three.low)
        elif float(three.high)<float(one.low):direction="bearish";low=float(three.high);high=float(one.low)
        else:continue
        gap=high-low;associated=not disp_times or _time(two) in disp_times
        if gap/max(float(tick_size),1e-12)<minimum_gap_ticks or gap/max(atr,1e-12)<minimum_gap_atr or not associated:continue
        future=rows.iloc[index+1:];fully=bool(((future.low<=low) if direction=="bullish" else (future.high>=high)).any());partial=bool(((future.low<high) if direction=="bullish" else (future.high>low)).any()) and not fully;ce=(low+high)/2;ce_hit=bool(((future.low<=ce) if direction=="bullish" else (future.high>=ce)).any());identity=hashlib.sha256(json.dumps([direction,times,low,high],default=str).encode()).hexdigest()[:20]
        result.append({"fvg_id":"fvg-"+identity,"direction":direction,"low":low,"high":high,"created_time":times[-1],"source_times":times,"gap_ticks":gap/max(float(tick_size),1e-12),"gap_atr":gap/max(atr,1e-12),"associated_displacement":associated,"state":"fully_mitigated" if fully else "partially_mitigated" if partial else "unmitigated","consequent_encroachment_reached":ce_hit,"invalidated":fully,"inverted":False,"research_only":bool(research_only)})
    return result
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)

