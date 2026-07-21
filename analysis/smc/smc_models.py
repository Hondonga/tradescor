from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class SMCSwing:
    swing_id:str;type:str;scope:str;price:float;candle_time:object;confirmation_time:object;left_strength:int;right_strength:int;prominence_atr:float;prominence_ticks:int;invalidated:bool=False
    def as_dict(self):return asdict(self)

