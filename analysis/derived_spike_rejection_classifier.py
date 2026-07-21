"""Independent rejection/normalization qualification."""
def classify_spike_rejection(spike,hold,structure):
    rejected=hold.get("classification") in {"RECLAIMED","FAILED_HOLD","FULL_RETRACE"};expected_shift="bearish" if spike and spike.get("direction")=="up" else "bullish";structure_shift=structure.get("direction")==expected_shift and structure.get("formed_after_spike")
    valid=bool(rejected and structure_shift)
    return {"rejected":valid,"direction":expected_shift if valid else None,"classification":"SPIKE_REJECTION" if valid else "UNRESOLVED","confidence":min(float(hold.get("confidence") or 0),.9) if valid else .2,"evidence":["Origin reclaim and fresh opposite structure confirm rejection."] if valid else [],"rejection_reasons":[] if valid else ["Spike rejection requires both origin failure and fresh opposite structure."]}
