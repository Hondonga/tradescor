"""Causal, directionally symmetric structure and market-regime detection."""
from __future__ import annotations
import pandas as pd

def detect_derived_structure(candles):
    rows=_rows(candles);base={"direction":"neutral","structure":"INSUFFICIENT_DATA","last_confirmed_swing_high":None,"last_confirmed_swing_low":None,"last_higher_low":None,"last_lower_high":None,"bullish_break":None,"bearish_break":None,"evidence":[],"contradictions":[]}
    if len(rows)<12:return base
    highs=[];lows=[]
    # Confirmation uses only the two candles immediately following each swing;
    # replaying any prefix therefore produces the same historical result.
    for i in range(2,len(rows)-2):
        if rows.high.iloc[i]>rows.high.iloc[i-2:i].max() and rows.high.iloc[i]>=rows.high.iloc[i+1:i+3].max():highs.append({"price":float(rows.high.iloc[i]),"time":_time(rows.iloc[i])})
        if rows.low.iloc[i]<rows.low.iloc[i-2:i].min() and rows.low.iloc[i]<=rows.low.iloc[i+1:i+3].min():lows.append({"price":float(rows.low.iloc[i]),"time":_time(rows.iloc[i])})
    hh=len(highs)>=2 and highs[-1]["price"]>highs[-2]["price"];lh=len(highs)>=2 and highs[-1]["price"]<highs[-2]["price"];hl=len(lows)>=2 and lows[-1]["price"]>lows[-2]["price"];ll=len(lows)>=2 and lows[-1]["price"]<lows[-2]["price"]
    current=float(rows.close.iloc[-1]);bull_break=highs[-1] if highs and current>highs[-1]["price"] else None;bear_break=lows[-1] if lows and current<lows[-1]["price"] else None
    if (hh and hl) or bull_break:direction="bullish";structure="higher_highs_higher_lows";evidence=["Confirmed higher-high and higher-low progression."] if hh and hl else ["Close accepted above the last confirmed swing high."]
    elif (lh and ll) or bear_break:direction="bearish";structure="lower_highs_lower_lows";evidence=["Confirmed lower-high and lower-low progression."] if lh and ll else ["Close accepted below the last confirmed swing low."]
    elif highs and lows:direction="neutral";structure="range_or_transition";evidence=["Confirmed swings do not have directional agreement."]
    else:direction="neutral";structure="developing";evidence=[]
    return {**base,"direction":direction,"structure":structure,"last_confirmed_swing_high":highs[-1] if highs else None,"last_confirmed_swing_low":lows[-1] if lows else None,"last_higher_low":lows[-1] if hl else None,"last_lower_high":highs[-1] if lh else None,"bullish_break":bull_break,"bearish_break":bear_break,"evidence":evidence}

def detect_derived_regime(candles,profile,spike=None,volatility=None,family="OTHER_DERIVED",previous_regime=""):
    rows=_rows(candles);structure=detect_derived_structure(rows);base={"regime":"INSUFFICIENT_DATA","direction":"neutral","confidence":0.0,"formed_at":None,"evidence":[],"contradictions":[],"previous_regime":previous_regime,"regime_changed":bool(previous_regime and previous_regime!="INSUFFICIENT_DATA"),"structure":structure}
    if len(rows)<20:return base
    if (spike or {}).get("cooldown_recommended"):regime="POST_SPIKE";direction=structure["direction"];evidence=["Recent abnormal event requires structural recalibration."]
    else:
        efficiency=float(profile.get("directional_efficiency") or 0);persistence=float(profile.get("trend_persistence") or 0);compression=float(profile.get("compression_ratio") or 1);expansion=float(profile.get("expansion_ratio") or 1);direction=structure["direction"]
        if compression<=.72:regime="COMPRESSION";direction="neutral";evidence=["Recent normalized ranges are compressed."]
        elif expansion>=1.45:regime="EXPANSION";evidence=["Recent normalized ranges are expanding."]
        elif efficiency<=.20:regime="RANGE";direction="neutral";evidence=["Directional efficiency supports a stable range."]
        elif direction=="bullish" and efficiency>=.30:regime="TREND_BULLISH";evidence=structure["evidence"]
        elif direction=="bearish" and efficiency>=.30:regime="TREND_BEARISH";evidence=structure["evidence"]
        else:regime="UNSTABLE";direction="mixed" if direction=="neutral" else direction;evidence=["Structure and normalized momentum are not fully aligned."]
    confidence=.9 if regime.startswith("TREND") else .82 if regime in {"RANGE","COMPRESSION"} else .7
    return {**base,"regime":regime,"direction":direction,"confidence":confidence,"formed_at":_time(rows.iloc[-1]),"evidence":evidence,"regime_changed":bool(previous_regime and previous_regime!=regime)}

def _rows(candles):
    rows=candles.copy() if candles is not None else pd.DataFrame()
    if "complete" in rows.columns:rows=rows[rows.complete.astype(bool)]
    return rows.reset_index(drop=True)
def _time(row):
    value=row.get("time")
    return value.isoformat() if hasattr(value,"isoformat") else str(value) if value is not None else None
