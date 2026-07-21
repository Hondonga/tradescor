"""Select one primary ICT entry array without widening it through confluence."""

from analysis.ict_state import evidence_result


def select_entry_array(fvg_event: dict, *, profile="fvg"):
    fvg=fvg_event.get("result") if fvg_event else None
    if not fvg or not fvg_event.get("valid"):return evidence_result(timeframe="M15",rejection_reason="No valid displacement-created FVG.",state="waiting")
    low,high=float(fvg["low"]),float(fvg["high"]); preferred=fvg["consequent_encroachment"] if profile=="fvg_ce" else None
    result={"type":profile,"low":low,"high":high,"preferred_price":preferred,"formed_at":fvg["formation_time"],"first_touch_at":fvg["first_touch_time"],"valid":True,"fvg_id":fvg["fvg_id"]}
    return evidence_result(result=result,timestamp=result["formed_at"],timeframe="M15",valid=True,evidence=["Primary entry array is the displacement-created FVG."])
