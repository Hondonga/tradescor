"""Structural objectives for accepted range breakouts."""
from analysis.derived_target_engine import structural_target_candidates,build_derived_targets
def build_breakout_targets(*,candles_by_timeframe,direction,entry,stop,locked_range,atr,minimum_rr=1.5,current_price=None):
    side="buy" if direction=="bullish" else "sell";candidates=structural_target_candidates(candles_by_timeframe,side,entry);width=float(locked_range["high"]-locked_range["low"]);projection=float(locked_range["high"]+width if side=="buy" else locked_range["low"]-width);candidates.append({"price":projection,"type":"range_width_secondary","source_timeframe":"M15","swept":False,"already_reached":False,"quality":.5})
    return build_derived_targets(direction=side,entry=entry,stop=stop,candidates=candidates,current_price=current_price,minimum_rr=minimum_rr,atr=atr)
