"""Temporally valid, asset-aware liquidity objectives for every strategy."""

from __future__ import annotations

import hashlib
import json
import math
import pandas as pd

from analysis.asset_rules import asset_rules, normalize_price


def build_liquidity_targets(*, symbol, asset_class, direction, entry_price, stop_price,
                            candles_by_timeframe, decision_timestamp, higher_timeframe_draw=None,
                            strategy="ict_2022", spread=0, atr=None, minimum_tp1_rr=1.0,
                            preferred_rr=1.5, enable_tp3=False, apply_offset=True,candidate_levels=None):
    """Return ranked real-liquidity targets; never manufacture a fixed-R price."""
    rules=asset_rules(symbol,asset_class); now=_utc(decision_timestamp); entry=_number(entry_price); stop=_number(stop_price)
    frames={key:_before(value,now) for key,value in (candles_by_timeframe or {}).items() if key in {"M5","M15","H1","H4","D1"}}
    volatility=_number(atr) or _atr(frames.get("M15")) or _atr(frames.get("M5")); tolerance=_tolerance(rules,spread,volatility)
    raw=[]
    for timeframe in ("M5","M15","H1","H4"):
        raw.extend(_swing_candidates(frames.get(timeframe),timeframe,direction,now))
    raw.extend(_period_candidates(frames.get("H1"),direction,now))
    raw.extend(_session_candidates(frames.get("M15"),direction,now))
    for row in candidate_levels or []:
        price=_number(row.get("price")); formed=row.get("formed_at") or row.get("time")
        if price is None or formed is None:continue
        raw.append(_raw(price,"buy_side" if direction=="buy" else "sell_side",row.get("type") or "major_unresolved_liquidity",row.get("source_timeframe") or "H1",_utc(formed),_utc(formed),row.get("prominence",16),row.get("touch_count",1)))
    clustered=_cluster(raw,direction,tolerance)
    candidates=[_validate(row,direction,entry,stop,frames,now,rules,tolerance,volatility,higher_timeframe_draw,strategy,spread,apply_offset) for row in clustered]
    candidates.sort(key=lambda row:(not row["valid"],row["distance_from_entry"] if row["distance_from_entry"] is not None else math.inf,-row["quality"]))
    valid=[row for row in candidates if row["valid"]]
    selected={"tp1":None,"tp2":None,"tp3":None}; gate={"passed":False,"reason":"No valid unswept liquidity objective is available.","nearest_rr":None}
    poor_nearby=[row for row in candidates if row["rejection_reasons"]==["Nearest objective is too close to justify the risk."]]
    if poor_nearby and (not valid or poor_nearby[0]["distance_from_entry"]<valid[0]["distance_from_entry"]):
        rr=poor_nearby[0]["projected_rr"]; gate={"passed":False,"reason":f"Trade rejected because the nearest realistic target provides only {rr:.2f}R.","nearest_rr":rr}; valid=[]
    if valid:
        nearest=valid[0]; gate["nearest_rr"]=nearest["projected_rr"]
        if entry is None or nearest["projected_rr"] is None or nearest["projected_rr"]>=minimum_tp1_rr:
            selected["tp1"]=_selected(nearest,"TP1"); rr_ready=entry is not None and stop is not None and nearest["projected_rr"] is not None; passed=bool(rr_ready and nearest["projected_rr"]>=preferred_rr); gate={"passed":passed,"projected_valid":True,"reason":"Projected target only; M5 entry and stop are pending." if not rr_ready else "Nearest target passes the preferred RR gate." if passed else f"Nearest realistic target provides only {nearest['projected_rr']:.2f}R.","nearest_rr":nearest["projected_rr"]}
            beyond=[row for row in valid[1:] if _beyond(direction,row["executable_tp_price"],nearest["executable_tp_price"])]
            if beyond:selected["tp2"]=_selected(beyond[0],"TP2")
            if enable_tp3 and len(beyond)>1 and str(higher_timeframe_draw or "").lower() in {direction,"bullish" if direction=="buy" else "bearish"}:selected["tp3"]=_selected(beyond[1],"TP3")
        else:gate["reason"]=f"Trade rejected because the nearest realistic target provides only {nearest['projected_rr']:.2f}R."
    return {"direction":direction if direction in {"buy","sell"} else "neutral","entry_price":entry,"stop_price":stop,"candidates":candidates,"selected_targets":selected,"quality_gate":gate,"offset_applied":bool(apply_offset),"minimum_tp1_rr":minimum_tp1_rr,"preferred_rr":preferred_rr}


def _swing_candidates(frame,timeframe,direction,now):
    if frame is None or len(frame)<5:return []
    rows=frame.reset_index(drop=True); result=[]; field="high" if direction=="buy" else "low"; side="buy_side" if direction=="buy" else "sell_side"
    for index in range(2,len(rows)-2):
        price=float(rows.iloc[index][field]); left=rows.iloc[index-2:index][field].astype(float); right=rows.iloc[index+1:index+3][field].astype(float)
        pivot=price>left.max() and price>=right.max() if direction=="buy" else price<left.min() and price<=right.min()
        if not pivot:continue
        formed=_utc(rows.iloc[index].time); confirmed=_utc(rows.iloc[index+2].time)
        if confirmed>now:continue
        result.append(_raw(price,side,"confirmed_swing",timeframe,formed,confirmed,prominence=_prominence(rows,index,price,direction),touch_count=1))
    return result[-20:]


def _period_candidates(frame,direction,now):
    if frame is None or frame.empty:return []
    rows=frame.copy(); times=pd.to_datetime(rows.time,utc=True); rows=rows.assign(_day=times.dt.floor("D"),_week=times.dt.tz_localize(None).dt.to_period("W").astype(str)); side="buy_side" if direction=="buy" else "sell_side"; field="high" if direction=="buy" else "low"; result=[]
    days=sorted(rows._day.unique())
    if len(days)>=2:
        day=days[-2]; group=rows.loc[rows._day==day]; price=float(group[field].max() if direction=="buy" else group[field].min()); result.append(_raw(price,side,"previous_day_high" if direction=="buy" else "previous_day_low","D1",_utc(group.iloc[-1].time),_utc(day)+pd.Timedelta(days=1),18,1))
    weeks=list(dict.fromkeys(rows._week.tolist()))
    if len(weeks)>=2:
        week=weeks[-2]; group=rows.loc[rows._week==week]; price=float(group[field].max() if direction=="buy" else group[field].min()); result.append(_raw(price,side,"previous_week_high" if direction=="buy" else "previous_week_low","W1",_utc(group.iloc[-1].time),_utc(group.iloc[-1].time)+pd.Timedelta(hours=1),20,1))
    return result


def _session_candidates(frame,direction,now):
    if frame is None or frame.empty:return []
    rows=frame.copy(); times=pd.to_datetime(rows.time,utc=True); cutoff=now.floor("D"); prior=rows.loc[(times>=cutoff-pd.Timedelta(days=1))&(times<cutoff)]
    if prior.empty:return []
    field="high" if direction=="buy" else "low"; price=float(prior[field].max() if direction=="buy" else prior[field].min())
    return [_raw(price,"buy_side" if direction=="buy" else "sell_side","previous_session_high" if direction=="buy" else "previous_session_low","M15",_utc(prior.iloc[-1].time),cutoff,14,1)]


def _cluster(rows,direction,tolerance):
    if not rows:return []
    ordered=sorted(rows,key=lambda row:row["price"]); groups=[]
    for row in ordered:
        if groups and row["price"]-groups[-1][-1]["price"]<=tolerance:groups[-1].append(row)
        else:groups.append([row])
    result=[]
    for group in groups:
        low=min(row["price"] for row in group); high=max(row["price"] for row in group); representative=low if direction=="buy" else high; strongest=max(group,key=lambda row:(_tf_points(row["source_timeframe"]),row["prominence"]))
        merged={**strongest,"price":representative,"type":"liquidity_cluster" if len(group)>1 else strongest["type"],"cluster_low":low,"cluster_high":high,"representative_price":representative,"level_count":len(group),"touch_count":sum(row["touch_count"] for row in group),"prominence":min(20,max(row["prominence"] for row in group)+min(4,len(group)-1)*2),"sources":[{"type":row["type"],"source_timeframe":row["source_timeframe"],"price":row["price"]} for row in group]}
        merged["target_id"]=_id({"side":merged["side"],"low":low,"high":high,"formed_at":str(merged["formed_at"])}) ; result.append(merged)
    return result


def _validate(row,direction,entry,stop,frames,now,rules,tolerance,atr,draw,strategy,spread,offset_enabled):
    price=float(row["representative_price"]); reasons=[]; formed=_utc(row["formed_at"]); confirmed=_utc(row["confirmed_at"])
    if confirmed>now:reasons.append("Level was confirmed after the decision timestamp.")
    sweep_time=_swept_at(price,direction,confirmed,frames,tolerance); swept=sweep_time is not None
    if swept:reasons.append("Liquidity was already swept.")
    if entry is not None and not _correct(direction,price,entry):reasons.append("Target is on the wrong side of entry.")
    risk=abs(entry-stop) if entry is not None and stop is not None else None; reward=abs(price-entry) if entry is not None and _correct(direction,price,entry) else None; rr=reward/risk if risk and reward else None; volatility=reward/atr if reward is not None and atr else None
    if rr is not None and rr<1:reasons.append("Nearest objective is too close to justify the risk.")
    if volatility is not None and volatility>10:reasons.append("Objective is unrealistically far relative to volatility.")
    age=(now-formed).total_seconds()/86400; max_age={"M5":3,"M15":10,"H1":45,"H4":120,"D1":180,"W1":365}.get(row["source_timeframe"],30)
    if age>max_age:reasons.append("Liquidity objective is stale for its timeframe.")
    offset=_offset(rules,spread,atr) if offset_enabled else 0; executable=price-offset if direction=="buy" else price+offset; executable=normalize_price(executable,rules,rounding="down" if direction=="buy" else "up")
    if entry is not None and not _correct(direction,executable,entry):reasons.append("Conservative offset places target on the wrong side.")
    distance=abs(executable-entry) if entry is not None else None; unit,unit_distance=_distance(distance,entry,rules)
    components={"prominence":min(20,int(row["prominence"])),"touches":min(10,int(row["touch_count"])*3),"timeframe":_tf_points(row["source_timeframe"]),"alignment":20 if str(draw or "").lower() in {direction,"bullish" if direction=="buy" else "bearish"} else 12,"freshness":0 if swept else 15,"distance_realism":10 if volatility is None or volatility<=5 else 5 if volatility<=10 else 0,"risk_reward":10 if rr is not None and rr>=2 else 8 if rr is not None and rr>=1.5 else 5 if rr is not None and rr>=1 else 0}
    quality=sum(components.values()); valid=not reasons and quality>=45
    return {**row,"formed_at":formed.isoformat(),"confirmed_at":confirmed.isoformat(),"quality":quality,"quality_components":components,"swept":swept,"swept_at":sweep_time.isoformat() if sweep_time is not None else None,"already_reached":swept,"distance_from_entry":unit_distance,"distance_unit":unit,"projected_rr":round(rr,2) if rr is not None else None,"volatility_distance_atr":round(volatility,2) if volatility is not None else None,"liquidity_objective_price":normalize_price(price,rules),"executable_tp_price":executable,"offset":normalize_price(abs(price-executable),rules),"valid":valid,"rejection_reasons":reasons,"reason":_reason(row)}


def _swept_at(price,direction,formed,frames,tolerance):
    hits=[]
    for frame in frames.values():
        if frame is None or frame.empty:continue
        times=pd.to_datetime(frame.time,utc=True); after=frame.loc[times>formed]
        crossed=after.loc[after.high.astype(float)>=price+tolerance] if direction=="buy" else after.loc[after.low.astype(float)<=price-tolerance]
        if not crossed.empty:hits.append(_utc(crossed.iloc[0].time))
    return min(hits) if hits else None


def _selected(row,name):return {"name":name,"target_id":row["target_id"],"price":row["executable_tp_price"],"liquidity_objective_price":row["liquidity_objective_price"],"executable_tp_price":row["executable_tp_price"],"type":row["type"],"source_timeframe":row["source_timeframe"],"reason":row["reason"],"risk_reward":row["projected_rr"],"quality":row["quality"],"swept":False,"valid":True,"offset":row["offset"]}
def _raw(price,side,kind,timeframe,formed,confirmed,prominence=10,touch_count=1):return {"target_id":"","price":float(price),"side":side,"type":kind,"source_timeframe":timeframe,"formed_at":formed,"confirmed_at":confirmed,"prominence":_number(prominence) or 10,"touch_count":int(_number(touch_count) or 1)}
def _reason(row):
    label=row["type"].replace("_"," "); return f"Targets the nearest unswept {label} ({row['source_timeframe']})."
def _correct(direction,price,entry):return price>entry if direction=="buy" else price<entry
def _beyond(direction,price,first):return price>first if direction=="buy" else price<first
def _tf_points(tf):return {"M5":5,"M15":8,"H1":12,"H4":15,"D1":15,"W1":15}.get(tf,5)
def _prominence(rows,index,price,direction):
    atr=_atr(rows); neighborhood=rows.iloc[max(0,index-5):index+6]; baseline=float(neighborhood.low.min() if direction=="buy" else neighborhood.high.max()); return min(20,max(1,int(abs(price-baseline)/(atr or abs(price)*1e-5)*4)))
def _atr(frame):
    if frame is None or len(frame)<2:return None
    values=frame.tail(30); previous=values.close.astype(float).shift(); tr=pd.concat([(values.high.astype(float)-values.low.astype(float)),(values.high.astype(float)-previous).abs(),(values.low.astype(float)-previous).abs()],axis=1).max(axis=1); value=float(tr.mean()); return value if value>0 else None
def _tolerance(rules,spread,atr):return max(float(rules["tick_size"])*2,_number(spread) or 0,(atr or 0)*.04)
def _offset(rules,spread,atr):return max(float(rules["tick_size"]),(_number(spread) or 0)*.5,(atr or 0)*.02)
def _distance(distance,entry,rules):
    if distance is None:return ("pips" if rules["asset_class"]=="forex" else "points",None)
    if rules["asset_class"]=="forex":return "pips",round(distance/float(rules["pip_size"]),1)
    return ("percent",round(distance/entry*100,2)) if rules["asset_class"]=="crypto" and entry else ("points",round(distance,2))
def _before(frame,now):
    if frame is None or not hasattr(frame,"empty") or frame.empty:return pd.DataFrame(columns=["time","open","high","low","close"])
    rows=frame.copy(); return rows.loc[pd.to_datetime(rows.time,utc=True)<=now].sort_values("time").reset_index(drop=True)
def _utc(value):
    timestamp=pd.Timestamp(value); return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
def _id(value):return "liq-target-"+hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()[:20]
