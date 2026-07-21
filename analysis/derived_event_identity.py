"""Immutable identity for distinct Jump/DEX events."""
import hashlib,json
_EVENTS={};_ACTIVE={}
def event_identity(symbol,family,event):return "event-"+hashlib.sha256(json.dumps([symbol,family,event.get("direction"),event.get("completed_at"),event.get("origin_price"),event.get("extreme_price")],default=str).encode()).hexdigest()[:20]
def lock_event(symbol,family,event,source_timeframe="M5"):
    if not event or not event.get("qualified"):return None
    event_id=event_identity(symbol,family,event)
    if event_id in _EVENTS:return dict(_EVENTS[event_id])
    row={"event_id":event_id,"symbol":symbol,"family":family,"direction":event["direction"],"origin_price":event["origin_price"],"extreme_price":event["extreme_price"],"started_at":event["completed_at"],"completed_at":event["completed_at"],"source_timeframe":source_timeframe,"source_candle_time":event.get("source_candle_time",event["completed_at"]),"magnitude_points":event.get("magnitude_points"),"magnitude_atr":event.get("magnitude_atr"),"range_multiple":event.get("range_multiple"),"locked":True};_EVENTS[event_id]=row;_ACTIVE[symbol]=event_id;return dict(row)
def active_event(symbol):return dict(_EVENTS[_ACTIVE[symbol]]) if symbol in _ACTIVE else None
def clear_events():_EVENTS.clear();_ACTIVE.clear()
