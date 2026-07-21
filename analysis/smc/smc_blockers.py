"""Stable blocker codes with separate trader-facing labels."""
TARGET_CODES={
 "NO_STRUCTURAL_TARGET":("No structural target is available",None,None),"TARGET_WRONG_SIDE":("Target is on the wrong side",None,None),"TARGET_ALREADY_SWEPT":("Target was already swept",None,None),"TARGET_ACCEPTED_BEYOND":("Price accepted beyond the target",None,None),"TARGET_STALE":("Target is stale",None,None),"TARGET_EVENT_INVALIDATED":("Target was invalidated by a new event",None,None),"TARGET_RR_BELOW_MINIMUM":("Target does not provide enough reward",None,"1.50R"),"FRESH_POST_EVENT_TARGET_UNAVAILABLE":("Fresh post-event target is unavailable",None,None),"TARGET_TIMEFRAME_UNAVAILABLE":("Target timeframe history is unavailable",None,None),
}
GATE_LABELS={"external_structure":"No confirmed directional structure","location":"Price has not reached the setup area","entry_array":"No valid entry area is available","sweep":"No completed boundary sweep","displacement":"No completed displacement","confirmation":"No completed M5 confirmation","history":"Required completed history is unavailable","state_contradiction":"State contradiction","chase":"Entry is too extended"}
def target_blocker_detail(trace):
    first=str((trace or {}).get("first_blocker") or "");rejected=(trace or {}).get("candidates_rejected") or [];mapping={"NO_STRUCTURAL_TARGET":"NO_STRUCTURAL_TARGET","TARGET_EXISTS_WRONG_SIDE":"TARGET_WRONG_SIDE","TARGET_EXISTS_ALREADY_CONSUMED":"TARGET_ALREADY_SWEPT","TARGET_EXISTS_EVENT_INVALIDATED":"TARGET_EVENT_INVALIDATED","TARGET_EXISTS_RR_REJECTED":"TARGET_RR_BELOW_MINIMUM","TARGET_EXISTS_GEOMETRY_UNAVAILABLE":"NO_STRUCTURAL_TARGET"};code=mapping.get(first,first if first in TARGET_CODES else None)
    if not code:return None
    current=None
    if code=="TARGET_RR_BELOW_MINIMUM":
        row=next((x for x in rejected if x.get("rejection_code")=="RR_BELOW_MINIMUM"),{});value=row.get("projected_rr");current=f"{float(value):.2f}R" if value is not None else None
    label,_,required=TARGET_CODES[code];return {"code":code,"label":label,"current_value":current,"required_value":required}
def blocker_label(value,detail=None):return detail["label"] if detail else GATE_LABELS.get(str(value),str(value or "").replace("_"," ").strip().capitalize())
