"""D1/H4/H1 narrative and explicit directional draw on liquidity."""

from __future__ import annotations

from analysis.ict_dealing_range import identify_dealing_range
from analysis.ict_state import evidence_result


def build_narrative(*, bundle, top_down):
    frames = top_down.get("timeframes") or {}; biases = {tf: str((frames.get(tf) or {}).get("bias", "neutral")) for tf in ("D1","H4","H1")}
    bullish=sum(value=="bullish" for value in biases.values()); bearish=sum(value=="bearish" for value in biases.values())
    if bullish >= 2: direction="buy"
    elif bearish >= 2: direction="sell"
    else: direction="neutral"
    expected="bullish" if direction=="buy" else "bearish" if direction=="sell" else "neutral"
    opposing=any(value not in {expected,"neutral"} for value in biases.values()) if direction!="neutral" else True
    alignment = "aligned" if direction != "neutral" and len(set(biases.values())) == 1 else "mixed" if opposing else "partial" if direction != "neutral" else "mixed"
    dealing = identify_dealing_range(bundle["timeframes"]["H4"]["candles"], timeframe="H4")
    range_value = dealing.get("result") or {}; draw = range_value.get("high") if direction=="buy" else range_value.get("low") if direction=="sell" else None
    current_frame=bundle["timeframes"]["M5"]["candles"]; current=float(current_frame.iloc[-1].close) if not current_frame.empty else None
    reached = draw is not None and current is not None and (current >= draw if direction=="buy" else current <= draw)
    valid=direction in {"buy","sell"} and alignment in {"aligned","partial"} and draw is not None and not reached
    result={"direction":direction,"alignment":alignment,"draw_on_liquidity":draw if not reached else None,"draw_type":"external_range" if draw is not None else "","confidence":"medium" if alignment=="aligned" and valid else "low","dealing_range":range_value if dealing["valid"] else None,"premium_discount":range_value.get("location"),"lower_timeframe_role":_role(direction,str((frames.get("M15") or {}).get("bias","neutral"))),"draw_reached":reached,"evidence":[f"{tf} is {biases[tf]}." for tf in biases],"contradictions":[f"{tf} opposes the primary narrative." for tf in biases if direction!="neutral" and biases[tf] not in {direction.replace("buy","bullish").replace("sell","bearish"),"neutral"}]}
    reason=None if valid else "Higher-timeframe evidence is mixed; provisional direction is diagnostic only." if direction in {"buy","sell"} and alignment=="mixed" else "The higher-timeframe draw has already been reached." if reached else "No coherent unreached higher-timeframe draw on liquidity."
    return evidence_result(result=result,timestamp=bundle["analysis_time_utc"] if valid else None,timeframe="D1/H4/H1",valid=valid,evidence=result["evidence"],rejection_reason=reason,data_quality=bundle["data_quality"],state="pass" if valid else "fail" if direction=="neutral" else "waiting")


def _role(direction,m15):
    expected="bullish" if direction=="buy" else "bearish" if direction=="sell" else "neutral"
    return "continuation" if m15==expected else "pullback" if direction!="neutral" and m15 not in {expected,"neutral"} else "transition"
