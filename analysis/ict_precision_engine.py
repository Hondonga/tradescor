"""Strict ICT Precision context, sequence, and execution-state contract."""

from __future__ import annotations

import hashlib
import json

import pandas as pd


SEQUENCE_ORDER = ("htf_context", "directional_liquidity", "opposing_liquidity", "liquidity_sweep", "displacement", "mss_choch", "entry_array", "price_in_entry_array", "m5_confirmation", "stop_valid", "target_valid", "risk_reward")


def build_ict_precision(*, bundle: dict[str, object], features: dict[str, object], top_down: dict[str, object], execution: dict[str, object], minimum_rr: float, amd: dict[str, object] | None = None) -> dict[str, object]:
    amd = amd or {}
    frames = top_down.get("timeframes") or {}; d1 = str((frames.get("D1") or {}).get("bias", "neutral")); h4 = str((frames.get("H4") or {}).get("bias", "neutral")); h1 = str((frames.get("H1") or {}).get("bias", "neutral"))
    direction, alignment = _direction(d1, h4, h1)
    setup = top_down.get("m15_setup") or {}; zone = setup.get("zone") if setup.get("enabled") and setup.get("direction") == direction else None
    context_available = direction in {"buy", "sell"} and zone is not None
    m15 = (features.get("timeframes") or {}).get("M15", {}); h1_features = (features.get("timeframes") or {}).get("H1", {})
    amd_direction = "buy" if amd.get("direction") == "bullish" else "sell" if amd.get("direction") == "bearish" else "neutral"
    amd_aligned = amd_direction == direction and not amd.get("countertrend")
    amd_manipulation = amd.get("manipulation") or {}; amd_distribution = amd.get("distribution") or {}
    directional = _directional_liquidity(h1_features, direction); opposing = _opposing_liquidity(m15, direction); sweep = _sweep_event(m15, direction)
    if not sweep and amd_aligned and amd_manipulation.get("detected"):
        sweep = {"sweep_time": amd_manipulation.get("sweep_time"), "price": amd_manipulation.get("sweep_price"), "source": "amd_locked_range"}
    displacement = _displacement_event(m15, direction)
    if not displacement and amd_aligned and amd_distribution.get("forming"):
        displacement = {"event_time": amd_distribution.get("displacement_start"), "direction": amd.get("direction"), "source": "amd_distribution"}
    m5_frame = bundle["timeframes"].get("M5") or {}; m5_available = bool(m5_frame.get("valid"))
    mss = _mss_event(m5_frame.get("candles", pd.DataFrame()), direction, sweep)
    if not mss and amd_aligned and amd_distribution.get("detected"):
        mss = {"time": amd_distribution.get("structure_break_time"), "level": amd_distribution.get("structure_break_price"), "source": "amd_distribution"}
    entry_array = _entry_array(m15, direction) or (amd_distribution.get("fvg") if amd_aligned else None); current = _last_close(m5_frame.get("available_candles", pd.DataFrame())) or _last_close(bundle["timeframes"]["M15"]["candles"])
    inside = bool(entry_array and current is not None and float(entry_array["low"]) <= current <= float(entry_array["high"]))
    confirmed = execution.get("confirmed_signal") or {}; stop = _number(execution.get("stop")); targets = [row for row in execution.get("targets", []) if row.get("valid") and not row.get("swept")]
    entry = _number(execution.get("entry") or execution.get("trigger")); target_valid = _target_valid(direction, entry, targets); stop_valid = _stop_valid(direction, zone, entry, stop)
    rr = _number(execution.get("risk_reward")); rr_valid = rr is not None and rr >= minimum_rr
    events = {"htf_context": _event(context_available, bundle["analysis_time_utc"] if context_available else None), "directional_liquidity": _event(bool(directional), directional.get("time") if directional else None), "opposing_liquidity": _event(bool(opposing), opposing.get("time") if opposing else None), "liquidity_sweep": _event(bool(sweep), sweep.get("sweep_time") if sweep else None), "displacement": _event(bool(displacement), displacement.get("event_time") if displacement else None), "mss_choch": _event(bool(mss), mss.get("time") if mss else None), "entry_array": _event(bool(entry_array), entry_array.get("formation_time") if entry_array else None), "price_in_entry_array": _event(inside, bundle["analysis_time_utc"] if inside else None), "m5_confirmation": _event(bool(confirmed), confirmed.get("candle_time") if confirmed else None, unavailable=not m5_available), "stop_valid": _event(stop_valid, confirmed.get("candle_time") if stop_valid else None, unavailable=not m5_available), "target_valid": _event(target_valid, confirmed.get("candle_time") if target_valid else None), "risk_reward": _event(rr_valid, confirmed.get("candle_time") if rr_valid else None)}
    sequence = {key: row["state"] for key, row in events.items()}; missing = [key for key in SEQUENCE_ORDER if sequence[key] != "pass"]
    sequence_started = any(sequence[key] == "pass" for key in ("liquidity_sweep", "displacement"))
    full = not missing and execution.get("state") == "entry_valid"
    if not context_available: eligibility_state = "unavailable"
    elif full: eligibility_state = "confirmed"
    elif sequence_started and not m5_available: eligibility_state = "waiting_for_m5"
    elif sequence_started: eligibility_state = "sequence_forming"
    else: eligibility_state = "context_only"
    status = _status(direction, context_available, sequence_started, full, execution.get("state"))
    score = _score(sequence, full); confidence = "high" if full else "medium" if sequence["mss_choch"] == sequence["entry_array"] == "pass" else "low"
    context_id = _id({"symbol": bundle["symbol"], "direction": direction, "zone": zone}) if context_available else None
    relation = _zone_relation(zone, current, bundle["asset_class"], bundle["symbol"]) if zone and current is not None else None
    first_missing = next((key for key in SEQUENCE_ORDER if sequence[key] != "pass"), None)
    next_action = _next_action(first_missing, direction, m5_available, entry_array, rr)
    why = _why(d1, h4, h1, direction, alignment, zone, sequence_started, m5_available)
    return {"requested_strategy": "ict_2022", "ict_context": {"available": context_available, "context_id": context_id, "direction": direction if context_available else "neutral", "alignment": alignment, "quality": "strong" if alignment == "aligned" and sequence_started else "developing" if context_available else "weak", "reason": " ".join(why), "summary": f"D1 is {d1}, H4 is {h4}, and H1 is {h1}. {relation or 'No relevant ICT area is active.'}", "zone": zone, "zone_relation": relation}, "ict_eligibility": {"eligible": sequence_started and context_available, "state": eligibility_state, "missing_requirements": missing}, "sequence": sequence, "sequence_events": events, "execution": {"timeframe": "M5", "available": m5_available, "execution_available": m5_available, "state": execution.get("state") if m5_available else "unavailable", "blocker": None if m5_available else "missing_m5_data", "execution_blocker": None if m5_available else "missing_m5_data", "entry": _number(execution.get("entry")) if full else None, "stop": stop if full else None, "targets": targets if full else [], "remaining_rr": rr if full else None}, "score": score, "confidence": confidence, "status": status, "direction_label": "Long bias" if direction == "buy" else "Short bias" if direction == "sell" else "Neutral", "strategy_label": f"ICT Precision — {'Eligible' if sequence_started else 'Not yet eligible'}" if context_available else "ICT Precision — Unavailable", "entry_timing": "Execution unavailable" if not m5_available else "Ready" if full else "Sequence incomplete", "next_action": next_action, "why": why, "overlays": _overlays(zone, entry_array, directional, opposing, events, full, execution), "checklist": _checklist(sequence, direction, zone, m5_available), "amd_support": {"available": bool(amd.get("available")), "aligned": amd_aligned, "phase": (amd.get("phase") or {}).get("current"), "cycle_id": amd.get("cycle_id")}}


def _direction(d1: str, h4: str, h1: str) -> tuple[str, str]:
    if d1 == h1 and d1 in {"bullish", "bearish"} and h4 in {d1, "neutral"}: return ("buy" if d1 == "bullish" else "sell"), ("aligned" if h4 == d1 else "partial")
    if d1 == h4 and d1 in {"bullish", "bearish"}: return ("buy" if d1 == "bullish" else "sell"), ("aligned" if h1 == d1 else "partial" if h1 == "neutral" else "conflicting")
    return "neutral", "conflicting"


def _directional_liquidity(frame, direction):
    liquidity = _value(frame, "liquidity") or {}; rows = liquidity.get("unswept_highs" if direction == "buy" else "unswept_lows") or []
    return rows[-1] if rows else None
def _opposing_liquidity(frame, direction):
    liquidity = _value(frame, "liquidity") or {}; rows = (liquidity.get("equal_lows") or liquidity.get("unswept_lows") or []) if direction == "buy" else (liquidity.get("equal_highs") or liquidity.get("unswept_highs") or [])
    return rows[-1] if rows else None
def _sweep_event(frame, direction):
    swings = _value(frame, "swings") or {}; rows = swings.get("lows" if direction == "buy" else "highs") or []
    swept = [row for row in rows if row.get("swept") and row.get("sweep_time")]
    return swept[-1] if swept else None
def _displacement_event(frame, direction):
    row = _value(frame, "displacement") or {}; expected = "bullish" if direction == "buy" else "bearish"
    return row if row.get("active") and row.get("direction") == expected and row.get("event_time") else None
def _entry_array(frame, direction):
    expected = "bullish" if direction == "buy" else "bearish"; rows = _value(frame, "fvg") or []
    return next((row for row in reversed(rows) if row.get("direction") == expected and not row.get("mitigated")), None)


def _mss_event(candles: pd.DataFrame, direction: str, sweep: dict[str, object] | None):
    if not sweep or candles is None or len(candles) < 8: return None
    sweep_time = pd.Timestamp(sweep["sweep_time"]); sweep_time = sweep_time.tz_localize("UTC") if sweep_time.tzinfo is None else sweep_time.tz_convert("UTC")
    rows = candles.reset_index(drop=True); times = pd.to_datetime(rows["time"], utc=True)
    for index in range(4, len(rows)):
        if times.iloc[index] <= sweep_time: continue
        prior = rows.iloc[index - 4:index]; close = float(rows.iloc[index]["close"])
        valid = close > float(prior["high"].max()) if direction == "buy" else close < float(prior["low"].min())
        if valid: return {"time": times.iloc[index].isoformat(), "level": float(prior["high"].max()) if direction == "buy" else float(prior["low"].min())}
    return None


def _event(passed: bool, timestamp: object, unavailable: bool = False): return {"state": "unavailable" if unavailable else "pass" if passed else "waiting", "timestamp": str(timestamp) if passed and timestamp is not None else None}
def _target_valid(direction, entry, targets): return bool(entry is not None and any((float(row["price"]) > entry if direction == "buy" else float(row["price"]) < entry) for row in targets if _number(row.get("price")) is not None))
def _stop_valid(direction, zone, entry, stop): return bool(zone and stop is not None and entry is not None and (stop < float(zone["low"]) and stop < entry if direction == "buy" else stop > float(zone["high"]) and stop > entry))


def _score(sequence, full):
    values = {"htf_context": 15, "directional_liquidity": 10, "opposing_liquidity": 5, "liquidity_sweep": 10, "displacement": 10, "mss_choch": 10, "entry_array": 10, "price_in_entry_array": 5, "m5_confirmation": 15, "stop_valid": 3, "target_valid": 3, "risk_reward": 4}
    score = sum(points for key, points in values.items() if sequence[key] == "pass")
    if full: return min(100, score)
    if sequence["m5_confirmation"] == "pass": return min(90, score)
    if sequence["mss_choch"] == sequence["entry_array"] == "pass": return min(80, score)
    if sequence["liquidity_sweep"] == "pass" or sequence["displacement"] == "pass": return min(70, score)
    return min(40, score)


def _status(direction, context, started, full, execution_state):
    if execution_state == "invalidated": return "ICT SETUP INVALIDATED"
    if execution_state in {"too_late", "entry_extended"}: return "ICT SETUP MISSED"
    if full: return "READY TO BUY" if direction == "buy" else "READY TO SELL"
    if started: return "BUY ICT SETUP FORMING" if direction == "buy" else "SELL ICT SETUP FORMING"
    if context: return "POTENTIAL BUY CONTEXT" if direction == "buy" else "POTENTIAL SELL CONTEXT"
    return "NO VALID ICT CONTEXT"


def _next_action(missing, direction, m5_available, entry_array, rr):
    side = "bullish" if direction == "buy" else "bearish"; liquidity = "sell-side" if direction == "buy" else "buy-side"
    if not m5_available: return f"Load valid M5 data, then wait for {liquidity} liquidity to be swept and {side} confirmation."
    return {"htf_context": "Wait for a coherent higher-timeframe ICT direction.", "directional_liquidity": "Wait for a valid directional liquidity objective.", "opposing_liquidity": f"Wait for a defined {liquidity} liquidity pool.", "liquidity_sweep": f"Wait for {liquidity} liquidity to be swept.", "displacement": f"Wait for {side} displacement away from the sweep.", "mss_choch": f"Wait for a {side} MSS on M5.", "entry_array": "Wait for a valid FVG, IFVG, or configured entry array.", "price_in_entry_array": "Wait for price to return to the active FVG.", "m5_confirmation": "Wait for the M5 confirmation candle to close.", "stop_valid": "Wait for valid M5 execution structure for the stop.", "target_valid": "Wait for an unswept target on the correct side.", "risk_reward": "Confirmation is too late; wait for a fresh setup."}.get(missing, "Review the confirmed ICT plan.")


def _zone_relation(zone, current, asset_class, symbol):
    kind = str(zone.get("type") or "area").lower(); kind = "OTE area" if kind == "ote" else kind
    if current > float(zone["high"]): relation, distance = "above", current - float(zone["high"])
    elif current < float(zone["low"]): relation, distance = "below", float(zone["low"]) - current
    else: return f"Price is inside {kind}."
    pip = .01 if asset_class == "forex" and str(symbol).upper().endswith("JPY") else .0001 if asset_class == "forex" else 1.0
    unit = "pips" if asset_class == "forex" else "points"
    return f"Price is {distance / pip:.1f} {unit} {relation} {kind}."


def _why(d1, h4, h1, direction, alignment, zone, started, m5):
    why = [f"D1 and H1 support a {'bullish' if direction == 'buy' else 'bearish' if direction == 'sell' else 'neutral'} context."] if direction != "neutral" else ["Higher-timeframe direction is conflicting or unavailable."]
    if alignment == "partial": why.append(f"H4 is {h4}, so alignment is incomplete.")
    if zone: why.append(f"M15 {zone.get('type', 'area')} is identified.")
    why.append("The required ICT sequence is forming." if started else "The required ICT sweep/displacement sequence has not started.")
    if not m5: why.append("Required M5 execution data is unavailable.")
    return why


def _overlays(zone, entry_array, directional, opposing, events, full, execution):
    return {"setup_zone": zone, "entry_array": entry_array, "directional_liquidity": directional, "opposing_liquidity": opposing, "liquidity_sweep": events["liquidity_sweep"] if events["liquidity_sweep"]["state"] == "pass" else None, "mss_choch": events["mss_choch"] if events["mss_choch"]["state"] == "pass" else None, "confirmation": {"price": execution.get("trigger"), "confirmed": True} if full else None, "invalidation": {"price": execution.get("stop")} if full else None, "entry": {"price": execution.get("entry")} if full else None, "stop": {"price": execution.get("stop")} if full else None, "targets": execution.get("targets", []) if full else [], "conditional_arrow": None}


def _checklist(sequence, direction, zone, m5):
    labels = [("htf_context", f"{'Bullish' if direction == 'buy' else 'Bearish' if direction == 'sell' else 'Directional'} higher-timeframe context"), ("directional_liquidity", "Directional liquidity identified"), ("opposing_liquidity", "Opposing liquidity identified"), ("liquidity_sweep", "Liquidity sweep"), ("displacement", f"{'Bullish' if direction == 'buy' else 'Bearish'} displacement"), ("mss_choch", "MSS / CHoCH"), ("entry_array", "Valid FVG / IFVG"), ("price_in_entry_array", "Price returns to entry array"), ("m5_confirmation", "M5 confirmation"), ("risk_reward", "Target and RR validation")]
    return [{"key": key, "label": label, "state": sequence[key]} for key, label in labels]


def _value(frame, name): return (frame.get(name) or {}).get("value")
def _last_close(frame): return float(frame.iloc[-1]["close"]) if frame is not None and not frame.empty else None
def _number(value):
    try: return float(value) if value is not None else None
    except (TypeError, ValueError): return None
def _id(value): return "ict-context-" + hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]
