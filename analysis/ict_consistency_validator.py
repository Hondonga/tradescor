"""Cross-field validation for normalized manual ICT responses."""

from __future__ import annotations


def validate_ict_consistency(ict: dict[str, object]) -> dict[str, object]:
    if ict.get("strategy_version") == "ict_2022_v2":
        return _validate_v2(ict)
    failures: list[str] = []; context = ict.get("ict_context") or {}; execution = ict.get("execution") or {}; sequence = ict.get("sequence") or {}; events = ict.get("sequence_events") or {}; overlays = ict.get("overlays") or {}; direction = context.get("direction"); zone = context.get("zone") or {}
    if direction == "buy" and zone.get("type") == "supply": failures.append("Buy context cannot describe its active zone as supply.")
    if direction == "sell" and zone.get("type") == "demand": failures.append("Sell context cannot describe its active zone as demand.")
    if not execution.get("available") and any(execution.get(key) for key in ("entry", "stop", "targets")): failures.append("Unavailable M5 data cannot expose an active trade plan.")
    if str(ict.get("status", "")).startswith("READY") and sequence.get("m5_confirmation") != "pass": failures.append("READY requires completed M5 confirmation.")
    if direction == "neutral" and any(execution.get(key) for key in ("entry", "stop", "targets")): failures.append("Neutral context cannot expose directional execution levels.")
    for key, state in sequence.items():
        if state == "pass" and not (events.get(key) or {}).get("timestamp"): failures.append(f"Completed ICT event '{key}' requires a timestamp.")
    entry = execution.get("entry"); stop = execution.get("stop"); targets = execution.get("targets") or []
    if entry is not None and stop is not None and ((direction == "buy" and stop >= entry) or (direction == "sell" and stop <= entry)): failures.append("ICT invalidation is on the wrong side of entry.")
    if entry is not None and any((direction == "buy" and row.get("price") <= entry) or (direction == "sell" and row.get("price") >= entry) for row in targets): failures.append("ICT target is on the wrong side of entry.")
    if not execution.get("available") and any(overlays.get(key) for key in ("confirmation", "invalidation", "entry", "stop", "targets")): failures.append("Unavailable M5 data cannot render execution overlays.")
    serious = bool(failures)
    return {"valid": not serious, "failures": failures, "downgrade_status": "EXECUTION DATA UNAVAILABLE" if serious and not execution.get("available") else "NO VALID ICT CONTEXT" if serious else None}


def _validate_v2(ict: dict[str, object]) -> dict[str, object]:
    failures=[]; sequence=ict.get("sequence") or {}; events=ict.get("sequence_events") or {}; setup=ict.get("setup") or {}; execution=ict.get("execution") or {}; direction=setup.get("direction")
    ordered=("opposing_liquidity","liquidity_sweep","displacement","mss","fvg","price_in_entry_array","m5_confirmation")
    previous=None
    for key in ordered:
        event=events.get(key) or {}; timestamp=event.get("timestamp")
        if sequence.get(key)=="pass" and not timestamp: failures.append(f"Completed ICT event '{key}' requires a timestamp.")
        if timestamp:
            from pandas import Timestamp
            current=Timestamp(timestamp)
            if previous is not None and current<previous and key!="mss": failures.append(f"ICT event '{key}' is temporally out of order.")
            previous=current
    sweep=(setup.get("sweep") or {}); mss=(setup.get("mss") or {}); displacement=(setup.get("displacement") or {}); array=(setup.get("entry_array") or {})
    if sweep and sweep.get("pool_formed_at") and sweep.get("sweep_time") and sweep["sweep_time"]<=sweep["pool_formed_at"]: failures.append("Sweep must occur after liquidity formation.")
    if displacement.get("start_time") and sweep.get("sweep_time") and displacement["start_time"]<sweep["sweep_time"]: failures.append("Displacement cannot precede the sweep.")
    if mss.get("break_time") and sweep.get("sweep_time") and mss["break_time"]<sweep["sweep_time"]: failures.append("MSS cannot precede the sweep.")
    if mss.get("break_time") and displacement.get("start_time") and mss["break_time"]<displacement["start_time"]: failures.append("MSS cannot precede displacement start.")
    if array.get("formed_at") and displacement.get("start_time") and array["formed_at"]<displacement["start_time"]: failures.append("Entry FVG must belong to the displacement sequence.")
    entry,stop=execution.get("entry"),execution.get("stop"); targets=execution.get("targets") or []
    if entry is not None and stop is not None and ((direction=="buy" and stop>=entry) or (direction=="sell" and stop<=entry)): failures.append("ICT stop is on the wrong side of entry.")
    if entry is not None and any(row.get("swept") or (direction=="buy" and row.get("price")<=entry) or (direction=="sell" and row.get("price")>=entry) for row in targets): failures.append("ICT target is swept or on the wrong side of entry.")
    ready=str((ict.get("user_output") or {}).get("status","")).startswith("READY")
    if ready and (sequence.get("m5_confirmation")!="pass" or not (ict.get("quality") or {}).get("trade_plan_valid")): failures.append("READY requires the complete M5-confirmed plan.")
    if (ict.get("quality") or {}).get("confidence")=="high" and not ready: failures.append("High confidence requires the complete sequence and valid plan.")
    if not ready and any(execution.get(key) for key in ("entry","stop","targets")): failures.append("Non-ready ICT context cannot expose actionable levels.")
    return {"valid":not failures,"failures":failures,"downgrade_status":"NO VALID ICT CONTEXT" if failures else None,"checked_strategy_version":"ict_2022_v2"}
