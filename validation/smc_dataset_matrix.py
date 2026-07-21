from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import hashlib,json
import pandas as pd
from replay.derived_replay_dataset import build_replay_dataset

REQUIRED_SYMBOLS=(
 {"symbol":"R_10","display_name":"Volatility 10 Index","family":"VOLATILITY","variant":"VOLATILITY_10"},{"symbol":"R_50","display_name":"Volatility 50 Index","family":"VOLATILITY","variant":"VOLATILITY_50"},{"symbol":"R_75","display_name":"Volatility 75 Index","family":"VOLATILITY","variant":"VOLATILITY_75"},{"symbol":"R_100","display_name":"Volatility 100 Index","family":"VOLATILITY","variant":"VOLATILITY_100"},
 {"symbol":"JD10","display_name":"Jump 10 Index","family":"JUMP","variant":"JUMP_10"},{"symbol":"JD50","display_name":"Jump 50 Index","family":"JUMP","variant":"JUMP_50"},{"symbol":"JD75","display_name":"Jump 75 Index","family":"JUMP","variant":"JUMP_75"},{"symbol":"JD100","display_name":"Jump 100 Index","family":"JUMP","variant":"JUMP_100"},
 {"symbol":"stpRNG","display_name":"Step Index 100","family":"STEP_CLASSIC","variant":"STEP_100"},{"symbol":None,"display_name":"Multi Step Index","family":"STEP_MULTI","variant":"STEP_MULTI"},{"symbol":None,"display_name":"Skew Step Up Index","family":"STEP_SKEW_UP","variant":"STEP_SKEW_UP"},{"symbol":None,"display_name":"Skew Step Down Index","family":"STEP_SKEW_DOWN","variant":"STEP_SKEW_DOWN"})

SELECTION_POLICY={"policy_id":"fixed_calendar_v1","period_start":"2026-07-01T00:00:00Z","period_end":"2026-07-02T00:00:00Z","seed":0,"selection_reason":"Fixed calendar block selected before performance evaluation; sufficient chronological provider coverage is required.","performance_fields_used":[]}

def select_neutral_period(candles,policy=None):
    policy={**SELECTION_POLICY,**(policy or {})};rows=candles.copy() if isinstance(candles,pd.DataFrame) else pd.DataFrame(candles);times=_times(rows.time);start=pd.Timestamp(policy["period_start"]);end=pd.Timestamp(policy["period_end"]);selected=rows[(times>=start)&(times<end)].copy();return selected,policy

def build_matrix_dataset(spec,candles,policy=None,downloaded_at=None):
    selected,selection=select_neutral_period(candles,policy);duplicates=_duplicate_intervals(selected);descriptor,normalized=build_replay_dataset(provider_symbol=spec["symbol"],display_name=spec["display_name"],family=spec["family"],candles=selected,base_timeframe="M1",metadata={"download_timestamp":downloaded_at or datetime.now(timezone.utc).isoformat()});row=descriptor.as_dict();return {"dataset_id":row["dataset_id"],"symbol":spec["symbol"],"family":spec["family"],"variant":spec["variant"],"start_time":row["start_time"],"end_time":row["end_time"],"source_timeframe":"M1","candle_count":row["candle_count"],"checksum":row["checksum"],"missing_intervals":row["missing_intervals"],"duplicate_intervals":duplicates,"data_quality":row["quality"],"downloaded_at":downloaded_at,"selection_reason":selection["selection_reason"],"selection_policy":selection},normalized

def unavailable_matrix_rows(active_symbols):
    names={str(x.get("display_name","")).lower() for x in active_symbols};return [{**spec,"data_quality":"unavailable","selection_reason":"Official Deriv active_symbols did not expose this required variant; no substitute was fabricated."} for spec in REQUIRED_SYMBOLS if spec["symbol"] is None and spec["display_name"].lower() not in names]

def resolve_required_symbols(active_symbols):
    """Resolve name-only requirements without silently substituting a variant."""
    by_name={str(row.get("display_name","")).strip().lower():row for row in active_symbols}
    resolved=[]
    for spec in REQUIRED_SYMBOLS:
        if spec["symbol"]:
            resolved.append(dict(spec));continue
        active=by_name.get(spec["display_name"].lower())
        if active and active.get("provider_symbol"):
            resolved.append({**spec,"symbol":active["provider_symbol"]})
    return resolved
def _times(values):
    return pd.to_datetime(values,unit="s",utc=True,errors="coerce") if pd.api.types.is_numeric_dtype(values) else pd.to_datetime(values,utc=True,errors="coerce")
def _duplicate_intervals(rows):
    times=_times(rows.time);counts=times.value_counts();return [{"time":time.isoformat(),"count":int(count)} for time,count in counts.items() if count>1]
