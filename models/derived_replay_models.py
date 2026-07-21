from dataclasses import dataclass,asdict
from typing import Any

@dataclass(frozen=True)
class DerivedReplayDataset:
    dataset_id:str;provider:str;provider_symbol:str;display_name:str;family:str;base_timeframe:str;start_time:str|None;end_time:str|None;candle_count:int;checksum:str;missing_intervals:tuple;quality:str;warnings:tuple;metadata:dict[str,Any]
    def as_dict(self):
        row=asdict(self);row["missing_intervals"]=list(row["missing_intervals"]);row["warnings"]=list(row["warnings"]);return row

@dataclass(frozen=True)
class DerivedReplayRun:
    replay_run_id:str;dataset_id:str;provider_symbol:str;family:str;requested_strategy:str;start_time:str;end_time:str;configuration_hash:str;code_version:str;random_seed:int|None;started_at:str;completed_at:str|None;status:str
    def as_dict(self):return asdict(self)

