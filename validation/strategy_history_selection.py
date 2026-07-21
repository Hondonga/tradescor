"""Outcome-independent calendar selection for 30-day strategy validation."""
from __future__ import annotations
import hashlib
from datetime import date,timedelta


def select_fixed_30_day_period(symbol,available_start,available_end,selection_version="calendar_hash_v1"):
    start=date.fromisoformat(str(available_start)[:10]);end=date.fromisoformat(str(available_end)[:10]);latest=end-timedelta(days=29)
    if latest<start:raise ValueError("At least 30 calendar days are required.")
    span=(latest-start).days+1;offset=int(hashlib.sha256(f"{selection_version}:{symbol}".encode()).hexdigest()[:12],16)%span;selected=start+timedelta(days=offset)
    return {"symbol":symbol,"selection_version":selection_version,"selected_before_evaluation":True,"start":selected.isoformat(),"end":(selected+timedelta(days=29)).isoformat(),"selection_input":{"available_start":start.isoformat(),"available_end":end.isoformat()},"performance_input_used":False}
