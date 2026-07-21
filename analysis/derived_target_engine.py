"""Nearest valid structural objectives and RR from confirmed entry only."""
from __future__ import annotations

def structural_target_candidates(candles_by_timeframe,direction,entry):
    rows=[]
    for timeframe in ("M15","H1","H4"):
        candles=candles_by_timeframe.get(timeframe)
        if candles is None or len(candles)<7:continue
        completed=candles[candles.complete.astype(bool)] if "complete" in candles else candles
        for i in range(2,len(completed)-2):
            row=completed.iloc[i];formed=row.get("time");formed=formed.isoformat() if hasattr(formed,"isoformat") else str(formed)
            if direction=="buy" and row.high>=completed.high.iloc[i-2:i].max() and row.high>=completed.high.iloc[i+1:i+3].max() and float(row.high)>entry:price=float(row.high);kind="confirmed_swing_high"
            elif direction=="sell" and row.low<=completed.low.iloc[i-2:i].min() and row.low<=completed.low.iloc[i+1:i+3].min() and float(row.low)<entry:price=float(row.low);kind="confirmed_swing_low"
            else:continue
            subsequent=completed.iloc[i+1:];swept=bool((subsequent.high>price).any()) if direction=="buy" else bool((subsequent.low<price).any());rows.append({"price":price,"type":kind,"direction":direction,"formed_at":formed,"source_timeframe":timeframe,"swept":swept,"already_reached":swept,"quality":.8 if timeframe in {"H1","H4"} else .7})
    return rows

def build_derived_targets(*,direction,entry,stop,candidates,current_price=None,minimum_rr=1.5,atr=None):
    if entry is None or stop is None:return {"candidates":[],"tp1":None,"tp2":None,"valid":False,"rejection_reasons":["Confirmed entry and structural stop are required."]}
    entry=float(entry);stop=float(stop);risk=entry-stop if direction=="buy" else stop-entry
    if risk<=0:return {"candidates":[],"tp1":None,"tp2":None,"valid":False,"rejection_reasons":["Stop is on the wrong side of entry."]}
    rows=[]
    for source in candidates:
        price=float(source["price"]);reward=price-entry if direction=="buy" else entry-price;reasons=[]
        if reward<=0:reasons.append("Target is on the wrong side of entry.")
        if source.get("swept"):reasons.append("Target has been swept.")
        if source.get("already_reached"):reasons.append("Target was already reached.")
        rr=reward/risk if risk else None
        if rr is not None and rr<minimum_rr:reasons.append("Remaining RR is below requirement.")
        rows.append({"price":price,"type":source.get("type","structure"),"direction":direction,"formed_at":source.get("formed_at"),"source_timeframe":source.get("source_timeframe","M15"),"swept":bool(source.get("swept")),"already_reached":bool(source.get("already_reached")),"quality":source.get("quality",.5),"distance_points":abs(price-entry),"distance_atr":abs(price-entry)/atr if atr else None,"rr":rr,"valid":not reasons,"rejection_reasons":reasons})
    valid=sorted((row for row in rows if row["valid"]),key=lambda row:abs(row["price"]-entry));tp1=valid[0] if valid else None;tp2=valid[1] if len(valid)>1 else None
    return {"candidates":rows,"tp1":tp1,"tp2":tp2,"valid":bool(tp1),"rejection_reasons":[] if tp1 else ["No nearest structural target passes RR."]}
