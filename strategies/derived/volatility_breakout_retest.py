from __future__ import annotations
from strategies.derived.base_derived_strategy import candidate,directional_result

def evaluate_breakout_retest(*,candles,profile,locked_range):
    low=locked_range.get("low");high=locked_range.get("high");close=float(candles.iloc[-1].close);atr=float(profile.get("atr") or 0);buffer=max(atr*.1,0);direction="buy" if high is not None and close>high+buffer else "sell" if low is not None and close<low-buffer else None
    wick_buy=high is not None and float(candles.iloc[-1].high)>high and close<=high;wick_sell=low is not None and float(candles.iloc[-1].low)<low and close>=low
    def side(name):
        accepted=direction==name;event="accepted_breakout" if accepted else "sweep_reclaim" if (wick_buy if name=="buy" else wick_sell) else "no_breakout"; boundary=high if name=="buy" else low
        zone={"low":boundary-buffer,"high":boundary+buffer,"type":"retest"} if boundary is not None else None
        return candidate("volatility_breakout_retest",name,eligible=accepted,state="WAITING_FOR_RETEST" if accepted else "FAILED_BREAKOUT" if event=="sweep_reclaim" else "NO_SETUP",zone=zone,quality=70 if accepted else 0,reasons=[event])|{"event_type":event,"breakout_buffer":buffer}
    return directional_result("volatility_breakout_retest",side("buy"),side("sell"))
