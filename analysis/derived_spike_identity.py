"""Immutable identities for distinct qualified spike candles."""
from __future__ import annotations
import hashlib,json
_SPIKES={};_ACTIVE={}
def qualify_spike(spike,family):
    detected=bool(spike and spike.get("spike_detected"));classification=("expected_family_spike" if detected and spike.get("family_expected") else "opposite_abnormal_move" if detected else "none")
    return {"qualified":detected and spike.get("classification") in {"expected_family_spike","abnormal_move"},"classification":classification,"direction":spike.get("direction") if detected else None,"confidence":float(spike.get("confidence") or 0),"evidence":spike.get("evidence",[]),"rejection_reasons":[] if detected else ["No qualified completed-candle abnormal event."]}
def lock_spike(symbol,family,spike,source_timeframe="M5"):
    qualification=qualify_spike(spike,family)
    if not qualification["qualified"]:return None
    values=[symbol,family,spike.get("direction"),spike.get("formed_at"),spike.get("origin_price"),spike.get("extreme_price")];spike_id="spike-"+hashlib.sha256(json.dumps(values,default=str).encode()).hexdigest()[:20]
    if spike_id in _SPIKES:return dict(_SPIKES[spike_id])
    row={"spike_id":spike_id,"symbol":symbol,"family":family,"direction":spike.get("direction"),"origin_price":spike.get("origin_price"),"extreme_price":spike.get("extreme_price"),"started_at":spike.get("formed_at"),"completed_at":spike.get("formed_at"),"magnitude_points":spike.get("magnitude_points"),"magnitude_atr":spike.get("magnitude_atr"),"range_multiple":spike.get("range_multiple"),"family_expected":bool(spike.get("family_expected")),"source_timeframe":source_timeframe,"source_candle_time":spike.get("formed_at"),"locked":True};_SPIKES[spike_id]=row;_ACTIVE[symbol]=spike_id;return dict(row)
def active_spike(symbol):return dict(_SPIKES[_ACTIVE[symbol]]) if symbol in _ACTIVE else None
def clear_spikes():_SPIKES.clear();_ACTIVE.clear()
