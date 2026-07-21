from __future__ import annotations
from dataclasses import dataclass,field,asdict
from typing import Any

@dataclass(frozen=True)
class FeatureSnapshot:
    metadata:dict[str,Any];features:dict[str,Any];sequence:list[list[float]];available_at_time:str;labels:dict[str,Any]=field(default_factory=dict)
    def as_record(self):return {**self.metadata,**self.features,"available_at_time":self.available_at_time,**self.labels}

@dataclass(frozen=True)
class DatasetManifest:
    dataset_id:str;schema_version:str;symbol:str;strategy:str;period:dict;splits:dict;rows:int;setups:int;buy_setups:int;sell_setups:int;trade_ready_rows:int;resolved_rows:int;checksum:str;leakage_violations:int;candle_checksum:str="";config_hash:str="";application_version:str=""
    def as_dict(self):return asdict(self)
