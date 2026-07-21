"""Completed-candle directional structure and pullback-area observation."""

from __future__ import annotations

import pandas as pd

from analysis.top_down_engine import completed_candles


def analyze_directional_structure(*,m5_candles,analysis_time,features,top_down,asset_rules,current_price):
    rows=completed_candles(m5_candles,"M5",analysis_time); empty={"direction":"neutral","structure":"transition","last_lower_high":None,"last_lower_low":None,"last_higher_high":None,"last_higher_low":None,"broken_structure_level":None,"evidence":[],"contradictions":["Insufficient completed M5 structure."],"extended":False,"pullback_area":None,"confirmation":{"price":None,"state":"pending_zone_interaction"},"trade_ready":False}
    if len(rows)<12:return empty
    atr=_atr(rows); highs,lows=_pivots(rows); close=float(rows.iloc[-1].close); bearish,bullish=[],[]
    lower_high=len(highs)>=2 and highs[-1]["price"]<highs[-2]["price"]; lower_low=len(lows)>=2 and lows[-1]["price"]<lows[-2]["price"]; higher_high=len(highs)>=2 and highs[-1]["price"]>highs[-2]["price"]; higher_low=len(lows)>=2 and lows[-1]["price"]>lows[-2]["price"]; macro_lower_high=_descending_pivots(highs); macro_lower_low=_descending_pivots(lows); macro_higher_high=_ascending_pivots(highs); macro_higher_low=_ascending_pivots(lows)
    if lower_high:bearish.append("Confirmed lower highs.")
    if lower_low:bearish.append("Confirmed lower lows.")
    if macro_lower_high and not lower_high:bearish.append("Broader confirmed swing highs remain descending despite the current bounce.")
    if macro_lower_low and not lower_low:bearish.append("Broader confirmed swing lows remain descending despite the current bounce.")
    if higher_high:bullish.append("Confirmed higher highs.")
    if higher_low:bullish.append("Confirmed higher lows.")
    if macro_higher_high and not higher_high:bullish.append("Broader confirmed swing highs remain ascending despite the current pullback.")
    if macro_higher_low and not higher_low:bullish.append("Broader confirmed swing lows remain ascending despite the current pullback.")
    prior_low=lows[-2]["price"] if len(lows)>=2 else None; prior_high=highs[-2]["price"] if len(highs)>=2 else None; broken_low=_recent_break(rows,lows,"bearish"); broken_high=_recent_break(rows,highs,"bullish"); down_break=broken_low is not None; up_break=broken_high is not None
    if down_break:bearish.append(f"Completed close below prior swing low {broken_low}.")
    if up_break:bullish.append(f"Completed close above prior swing high {broken_high}.")
    last_lower_high=highs[-1]["price"] if highs and (lower_high or close<highs[-1]["price"]) else None; last_higher_low=lows[-1]["price"] if lows and (higher_low or close>lows[-1]["price"]) else None
    if last_lower_high is not None and close<last_lower_high:bearish.append("Price remains below the latest structural lower high.")
    if last_higher_low is not None and close>last_higher_low:bullish.append("Price remains above the latest structural higher low.")
    displacement=_displacement(rows,atr)
    if displacement=="bearish":bearish.append("Completed bearish displacement.")
    if displacement=="bullish":bullish.append("Completed bullish displacement.")
    efficiency=_efficiency(rows)
    if efficiency<-.12:bearish.append("Bearish directional efficiency and downside momentum.")
    if efficiency>.12:bullish.append("Bullish directional efficiency and upside momentum.")
    direction="bearish" if len(bearish)>=4 and len(bearish)>=len(bullish)+2 else "bullish" if len(bullish)>=4 and len(bullish)>=len(bearish)+2 else "neutral"
    if direction=="bearish":structure="breakdown" if down_break and displacement=="bearish" else "continuation" if lower_high and lower_low or down_break else "pullback"; evidence,contradictions=bearish,bullish
    elif direction=="bullish":structure="breakout" if up_break and displacement=="bullish" else "continuation" if higher_high and higher_low or up_break else "pullback"; evidence,contradictions=bullish,bearish
    else:structure="transition"; evidence,contradictions=[],bearish+bullish
    if direction=="bearish" and last_lower_high is None and macro_lower_high:last_lower_high=highs[-1]["price"]
    if direction=="bullish" and last_higher_low is None and macro_higher_low:last_higher_low=lows[-1]["price"]
    last_high=last_lower_high if direction=="bearish" else highs[-1]["price"] if highs else None; last_low=last_higher_low if direction=="bullish" else lows[-1]["price"] if lows else None
    extended=bool(direction=="bearish" and last_high is not None and last_high-close>atr*1.25 or direction=="bullish" and last_low is not None and close-last_low>atr*1.25)
    area=_pullback_area(direction,rows,atr,close,features,top_down,last_high,last_low,broken_low if down_break else broken_high if up_break else None,asset_rules)
    return {"direction":direction,"structure":structure,"last_lower_high":last_lower_high,"last_lower_low":min(row["price"] for row in lows[-6:]) if direction=="bearish" and lows else None,"last_higher_high":max(row["price"] for row in highs[-6:]) if direction=="bullish" and highs else None,"last_higher_low":last_higher_low,"broken_structure_level":broken_low if down_break else broken_high if up_break else None,"evidence":evidence,"contradictions":contradictions,"extended":extended,"pullback_area":area,"confirmation":{"price":None,"state":"pending_zone_interaction"},"trade_ready":False}


def _pullback_area(direction,rows,atr,current,features,top_down,last_high,last_low,broken,rules):
    if direction not in {"bearish","bullish"}:return None
    candidates=[]; bearish=direction=="bearish"; side="sell" if bearish else "buy"
    recent=rows.tail(20).reset_index(drop=True)
    for index in range(len(recent)-1,-1,-1):
        row=recent.iloc[index]; body=abs(float(row.close)-float(row.open)); candle_direction="bearish" if row.close<row.open else "bullish"
        if body>=atr*1.2 and candle_direction==direction:
            low=min(float(row.open),float(row.close)) if bearish else float(row.low); high=float(row.high) if bearish else max(float(row.open),float(row.close)); later=recent.iloc[index+1:]; touches=int(((later.high.astype(float)>=low)&(later.low.astype(float)<=high)).sum()) if not later.empty else 0
            candidates.append(_area(low,high,"m5_supply" if bearish else "m5_demand",row.time,touches,1,current,side,rules)); break
    if broken is not None:candidates.append(_area(broken-atr*.08,broken+atr*.08,"broken_support_retest" if bearish else "broken_resistance_retest",None,0,2,current,side,rules))
    frame=((features.get("timeframes") or {}).get("M5") or {}); fvgs=((frame.get("fvg") or {}).get("value")) or []
    for fvg in reversed(fvgs):
        if fvg.get("direction")==direction:candidates.append(_area(fvg.get("low"),fvg.get("high"),"bearish_fvg" if bearish else "bullish_fvg",fvg.get("formation_time"),0,3,current,side,rules)); break
    zone=(top_down.get("m15_setup") or {}).get("zone") or {}; expected="supply" if bearish else "demand"
    if str(zone.get("type"))==expected:candidates.append(_area(zone.get("low"),zone.get("high"),f"m15_{expected}",zone.get("start_time"),0,4,current,side,rules))
    anchor=last_high if bearish else last_low
    if anchor is not None:candidates.append(_area(anchor-atr*.1,anchor+atr*.1,"lower_high_reaction" if bearish else "higher_low_reaction",None,0,5,current,side,rules))
    valid=[row for row in candidates if row["valid"]]; return min(valid,key=lambda row:(row["priority"],row["distance_pips"] if row["distance_pips"] is not None else 1e9)) if valid else None


def _area(low,high,kind,formed,touches,priority,current,side,rules):
    low,high=_number(low),_number(high); reasons=[]
    if low is None or high is None:reasons.append("Area bounds are unavailable.")
    else:low,high=min(low,high),max(low,high)
    if low is not None and ((side=="sell" and high<=current) or (side=="buy" and low>=current)):reasons.append("Area is not on the pullback side of current price.")
    if touches>1:reasons.append("Area has too many prior mitigations.")
    distance=(max(0,low-current) if side=="sell" else max(0,current-high)) if low is not None else None; pips=round(distance/float(rules["pip_size"]),1) if distance is not None and rules.get("asset_class")=="forex" else round(distance,2) if distance is not None else None
    return {"low":low,"high":high,"type":kind,"formed_at":str(formed) if formed is not None else None,"freshness":"fresh" if touches==0 else "partially_mitigated","touch_count":touches,"distance_pips":pips,"valid":not reasons,"rejection_reasons":reasons,"priority":priority}


def _pivots(rows):
    highs=[]; lows=[]
    for i in range(2,len(rows)-2):
        row=rows.iloc[i]
        if float(row.high)>float(rows.iloc[i-2:i].high.max()) and float(row.high)>=float(rows.iloc[i+1:i+3].high.max()):highs.append({"price":float(row.high),"time":row.time.isoformat(),"index":i})
        if float(row.low)<float(rows.iloc[i-2:i].low.min()) and float(row.low)<=float(rows.iloc[i+1:i+3].low.min()):lows.append({"price":float(row.low),"time":row.time.isoformat(),"index":i})
    return highs,lows
def _atr(rows):
    previous=rows.close.astype(float).shift(); tr=pd.concat([rows.high.astype(float)-rows.low.astype(float),(rows.high.astype(float)-previous).abs(),(rows.low.astype(float)-previous).abs()],axis=1).max(axis=1); return max(float(tr.tail(14).mean()),1e-12)
def _displacement(rows,atr):
    for _,row in rows.tail(20).iloc[::-1].iterrows():
        if abs(float(row.close)-float(row.open))>=atr*1.2:return "bearish" if row.close<row.open else "bullish"
    return "neutral"
def _efficiency(rows):
    close=rows.close.astype(float).tail(40); path=float(close.diff().abs().sum()); return float(close.iloc[-1]-close.iloc[0])/path if path else 0

def _descending_pivots(values):
    if len(values)<4:return False
    midpoint=max(2,len(values[-6:])//2); recent=values[-6:]; return sum(row["price"] for row in recent[midpoint:])/len(recent[midpoint:]) < sum(row["price"] for row in recent[:midpoint])/len(recent[:midpoint])
def _ascending_pivots(values):
    if len(values)<4:return False
    midpoint=max(2,len(values[-6:])//2); recent=values[-6:]; return sum(row["price"] for row in recent[midpoint:])/len(recent[midpoint:]) > sum(row["price"] for row in recent[:midpoint])/len(recent[:midpoint])
def _recent_break(rows,pivots,direction):
    for pivot in reversed(pivots):
        after=rows.iloc[int(pivot["index"])+3:]
        if after.empty:continue
        crossed=(after.close.astype(float)<pivot["price"]) if direction=="bearish" else (after.close.astype(float)>pivot["price"])
        if bool(crossed.any()) and int(pivot["index"])>=len(rows)-40:return pivot["price"]
    return None
def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
