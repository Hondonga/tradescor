"""Immutable, fingerprinted range snapshots."""
from __future__ import annotations
import hashlib,json
_LOCKS={};_ACTIVE={}
def range_identity(symbol,detected_range):
    values=[symbol,"M15",detected_range.get("low"),detected_range.get("high"),detected_range.get("started_at"),detected_range.get("ended_at")];return "range-"+hashlib.sha256(json.dumps(values,sort_keys=True,default=str).encode()).hexdigest()[:20]
def lock_range(symbol,detected_range,candle_snapshot=None):
    if not detected_range or not detected_range.get("valid"):return None
    if symbol in _ACTIVE:return dict(_LOCKS[_ACTIVE[symbol]])
    range_id=range_identity(symbol,detected_range)
    if range_id in _LOCKS:return dict(_LOCKS[range_id])
    fingerprint=hashlib.sha256(json.dumps(candle_snapshot or [],sort_keys=True,default=str).encode()).hexdigest()
    row={"range_id":range_id,"symbol":symbol,"timeframe":"M15","low":detected_range["low"],"high":detected_range["high"],"midpoint":detected_range.get("midpoint"),"width_points":detected_range.get("width_points"),"width_atr":detected_range.get("width_atr"),"locked_at":detected_range.get("ended_at"),"source_candle_start":detected_range.get("started_at"),"source_candle_end":detected_range.get("ended_at"),"quality":detected_range.get("quality"),"quality_at_lock":detected_range.get("quality"),"duration_at_lock":detected_range.get("duration_candles"),"valid":True,"snapshot_fingerprint":fingerprint};_LOCKS[range_id]=row;_ACTIVE[symbol]=range_id;return dict(row)
def active_range(symbol):return dict(_LOCKS[_ACTIVE[symbol]]) if symbol in _ACTIVE else None
def release_range(symbol,range_id):
    if _ACTIVE.get(symbol)==range_id:_ACTIVE.pop(symbol,None)
def clear_range_locks():_LOCKS.clear();_ACTIVE.clear()
