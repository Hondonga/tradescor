from dataclasses import dataclass,field,asdict

@dataclass
class DerivedReplayState:
    candle_index:int=-1
    replay_time:str|None=None
    pending_setup_ids:list[str]=field(default_factory=list)
    filled_setup_ids:list[str]=field(default_factory=list)
    selected_strategy:str|None=None
    analytical_state:dict=field(default_factory=dict)
    last_outcome_event:str|None=None
    def as_dict(self):return asdict(self)

