"""Normalized rolling statistics calculated from completed candles only."""
from __future__ import annotations
import math
import pandas as pd

def build_derived_market_profile(candles:pd.DataFrame,*,family="OTHER_DERIVED",tick_size=.01,timeframe="M5",symbol="")->dict[str,object]:
    rows=_completed(candles).tail(200);base={"symbol":symbol or _attr(rows,"symbol"),"timeframe":timeframe,"sample_size":len(rows),"atr":None,"normalized_atr":None,"atr_percentile":None,"median_range":None,"median_candle_range":None,"average_range":None,"range_percentile":None,"body_to_range_ratio":None,"upper_wick_ratio":None,"lower_wick_ratio":None,"realized_volatility":None,"volatility_percentile":None,"directional_efficiency":None,"trend_persistence":None,"compression_ratio":None,"expansion_ratio":None,"abnormal_candle_frequency":None,"abnormal_move_magnitude":None,"average_pullback_depth_atr":None,"average_pullback_depth":None,"median_pullback_depth_atr":None,"recent_gap_frequency":None,"profile_quality":"insufficient","family":family,"volatility_regime":"INSUFFICIENT_DATA"}
    if len(rows)<20:return base
    o,h,l,c=[pd.to_numeric(rows[key],errors="coerce") for key in ("open","high","low","close")];valid=pd.concat([o,h,l,c],axis=1).dropna()
    if len(valid)<20:return base
    o,h,l,c=[valid.iloc[:,i] for i in range(4)];ranges=(h-l).clip(lower=0);prev=c.shift(1);tr=pd.concat([ranges,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1);atr_series=tr.rolling(14,min_periods=14).mean().dropna();atr=float(atr_series.iloc[-1]);median=float(ranges.median());mean_price=float(c.abs().median());returns=c.pct_change().dropna();rv_series=returns.rolling(20,min_periods=10).std()*math.sqrt(20);rv_series=rv_series.dropna();rv=float(rv_series.iloc[-1]) if len(rv_series) else None
    body=(c-o).abs();upper=(h-pd.concat([o,c],axis=1).max(axis=1)).clip(lower=0);lower=(pd.concat([o,c],axis=1).min(axis=1)-l).clip(lower=0);safe=ranges.replace(0,float("nan"));changes=c.diff();net=abs(float(c.iloc[-1]-c.iloc[max(0,len(c)-20)]));path=float(changes.tail(19).abs().sum());sign=1 if c.iloc[-1]>=c.iloc[max(0,len(c)-20)] else -1;counter=changes[changes*sign<0].abs()/max(atr,tick_size);long=float(ranges.tail(50).mean());recent=float(ranges.tail(10).mean());exp=float(ranges.tail(3).mean());threshold=max(atr*2.5,median*3,tick_size);abnormal=ranges[ranges>=threshold];gaps=((o-prev).abs()>max(atr*.25,tick_size))
    result={**base,"atr":atr,"normalized_atr":atr/max(mean_price,tick_size),"atr_percentile":_pct(atr_series,atr),"median_range":median,"median_candle_range":median,"average_range":float(ranges.mean()),"range_percentile":_pct(ranges,float(ranges.iloc[-1])),"body_to_range_ratio":_mean(body/safe),"upper_wick_ratio":_mean(upper/safe),"lower_wick_ratio":_mean(lower/safe),"realized_volatility":rv,"volatility_percentile":_pct(rv_series,rv) if rv is not None else None,"directional_efficiency":net/path if path>0 else 0.0,"trend_persistence":float(((changes*sign)>0).tail(20).mean()),"compression_ratio":recent/max(long,tick_size),"expansion_ratio":exp/max(long,tick_size),"abnormal_candle_frequency":float(len(abnormal)/len(ranges)),"abnormal_move_magnitude":float((abnormal/max(atr,tick_size)).mean()) if len(abnormal) else 0.0,"average_pullback_depth_atr":float(counter.mean()) if len(counter) else 0.0,"average_pullback_depth":float(counter.mean()) if len(counter) else 0.0,"median_pullback_depth_atr":float(counter.median()) if len(counter) else 0.0,"recent_gap_frequency":float(gaps.tail(50).mean()),"profile_quality":"good" if len(rows)>=100 else "partial","volatility_regime":"HIGH" if _pct(atr_series,atr)>=75 else "LOW" if _pct(atr_series,atr)<=25 else "NORMAL"}
    return _finite(result)

def _completed(candles):
    if candles is None:return pd.DataFrame()
    rows=candles.copy()
    if "complete" in rows.columns:rows=rows[rows["complete"].astype(bool)]
    return rows.dropna(subset=[key for key in ("open","high","low","close") if key in rows.columns])
def _pct(series,value):return float((series<=value).mean()*100) if len(series) else None
def _mean(series):value=series.mean();return float(value) if pd.notna(value) else None
def _attr(rows,name):
    try:return str(rows[name].iloc[-1]) if name in rows else ""
    except Exception:return ""
def _finite(value):
    if isinstance(value,dict):return {key:_finite(item) for key,item in value.items()}
    if isinstance(value,float) and not math.isfinite(value):return None
    return value
