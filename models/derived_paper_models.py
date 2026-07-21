"""Typed records for the Derived paper-testing persistence boundary."""
from dataclasses import dataclass,asdict
from typing import Any
@dataclass(frozen=True)
class DerivedDecisionSnapshot:
    decision_id:str;dedupe_key:str;created_at:str;analysis_candle_time:str;provider_symbol:str;family:str;selected_strategy:str|None;setup_id:str|None;payload:dict[str,Any]
    def as_dict(self):return asdict(self)
@dataclass(frozen=True)
class DerivedPaperSetup:
    paper_setup_id:str;decision_id:str;setup_id:str;strategy:str;direction:str;entry:float;stop:float;tp1:float;tp2:float|None;risk_points:float;tp1_rr:float|None;created_at:str;confirmation_time:str|None;entry_valid_until:str|None;state:str="waiting_for_fill"
    def as_dict(self):return asdict(self)
