"""Unswept opposing-liquidity target selection and actual-entry RR."""

from analysis.ict_state import evidence_result


def select_targets(*, liquidity: dict, direction: str, entry, stop, minimum_rr=1.5):
    pool=(liquidity or {}).get("directional_target"); entry=_number(entry); stop=_number(stop)
    if not pool or pool.get("swept"):return evidence_result(timeframe=pool.get("source_timeframe","") if pool else "",rejection_reason="No valid unswept opposing-liquidity target.")
    price=_number(pool.get("price")); correct=entry is not None and price is not None and (price>entry if direction=="buy" else price<entry)
    risk=abs(entry-stop) if entry is not None and stop is not None else None; reward=(price-entry if direction=="buy" else entry-price) if correct else None; rr=reward/risk if risk and reward and reward>0 else None
    valid=correct and rr is not None and rr>=minimum_rr
    result={"targets":[{**pool,"name":"TP1","risk_reward":rr}] if correct else [],"remaining_rr":rr,"valid":valid,"rating":"strong" if rr is not None and rr>=2 else "acceptable" if valid else "weak" if rr is not None and rr>=1 else "reject"}
    return evidence_result(result=result,timestamp=pool.get("formed_at") if valid else None,timeframe=pool.get("source_timeframe",""),valid=valid,evidence=["Nearest target is unswept and on the correct side.","RR uses the proposed M5 entry."] if valid else [],rejection_reason=None if valid else "Remaining reward is below the actionable threshold or target is invalid.")


def _number(value):
    try:return float(value) if value is not None else None
    except (TypeError,ValueError):return None
