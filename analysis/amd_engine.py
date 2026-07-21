"""Accumulation–liquidity-sweep–distribution context state machine."""

from __future__ import annotations

import hashlib
import json

import pandas as pd

from analysis.accumulation_detector import AccumulationConfig, detect_accumulation
from analysis.amd_liquidity import identify_amd_liquidity
from analysis.distribution_detector import detect_distribution
from analysis.manipulation_detector import detect_manipulation


def analyze_amd(*, symbol: str, asset_class: str, analysis_time: object, m5_candles: pd.DataFrame, top_down: dict[str, object], execution: dict[str, object] | None = None, filters: dict[str, object] | None = None, session: dict[str, object] | None = None, config: AccumulationConfig | None = None) -> dict[str, object]:
    execution = execution or {}; filters = filters or {}; session = session or {}; rows = _clean(m5_candles, analysis_time)
    accumulation = detect_accumulation(rows, config)
    liquidity = identify_amd_liquidity(rows, accumulation) if accumulation else []
    manipulation = detect_manipulation(rows, accumulation, liquidity) if accumulation else _empty_manipulation()
    distribution = detect_distribution(rows, accumulation, manipulation) if accumulation else _empty_distribution()
    htf_direction = str((top_down.get("alignment") or {}).get("primary_direction", "neutral")); amd_direction = "bullish" if manipulation.get("side") == "low" else "bearish" if manipulation.get("side") == "high" else "neutral" if accumulation else "unknown"
    aligned = (amd_direction == "bullish" and htf_direction == "buy") or (amd_direction == "bearish" and htf_direction == "sell")
    countertrend = amd_direction in {"bullish", "bearish"} and htf_direction in {"buy", "sell"} and not aligned
    target = _target(top_down, amd_direction, rows)
    phase, internal_state, started_at, confirmed_at = _phase(rows, accumulation, manipulation, distribution, execution, target, aligned, countertrend)
    event_context = "scheduled_news" if (filters.get("news_risk") or {}).get("restriction_active") and manipulation.get("sweep_time") else "unexpected_volatility" if _abnormal(rows, accumulation) else "normal" if not rows.empty else "data_unavailable"
    score = _score(accumulation, liquidity, manipulation, distribution, aligned, rows, execution, target, phase)
    confidence = "high" if phase == "distribution_confirmed" else "medium" if phase in {"manipulation_confirmed", "distribution_forming"} else "low"
    warnings = []
    if event_context == "scheduled_news": warnings.append("The boundary event occurred near an active scheduled-news risk window.")
    if countertrend: warnings.append("AMD direction opposes the higher-timeframe primary direction and is observational only.")
    if manipulation.get("both_sides_swept"): warnings.append("Both accumulation boundaries were swept without clean directional resolution.")
    if event_context in {"scheduled_news", "unexpected_volatility"} or countertrend or manipulation.get("both_sides_swept"): confidence = _reduce(confidence)
    cycle_type = "rolling" if asset_class == "crypto" else "session" if asset_class in {"forex", "index"} else "rolling"
    cycle_id = _cycle_id(symbol, cycle_type, accumulation) if accumulation else None
    missing = _missing(accumulation, liquidity, manipulation, distribution, execution, target, aligned)
    invalidation = []
    if manipulation.get("boundary_event") == "accepted_breakout": invalidation.append("Range acceptance indicates a potential real breakout, not an AMD sweep proxy.")
    if countertrend: invalidation.append("Countertrend AMD is disabled without confirmed higher-timeframe reversal.")
    if manipulation.get("both_sides_swept") and not distribution.get("detected"): invalidation.append("Both range sides were swept without distribution confirmation.")
    next_event, next_action = _next(phase, amd_direction, execution, target)
    result = {"amd_id": cycle_id, "cycle_id": cycle_id, "symbol": symbol, "asset_class": asset_class, "analysis_time": _utc(analysis_time).isoformat(), "available": accumulation is not None, "cycle_type": cycle_type, "direction": amd_direction, "phase": {"current": phase, "confidence": confidence, "started_at": started_at, "confirmed_at": confirmed_at}, "state": internal_state, "accumulation": accumulation or _empty_accumulation(), "liquidity": liquidity, "manipulation": manipulation, "distribution": distribution, "target": target, "boundary_event": manipulation.get("boundary_event", "unclear"), "event_context": event_context, "next_required_event": next_event, "next_action": next_action, "quality_score": score, "confidence": confidence, "countertrend": countertrend, "warnings": warnings, "validation": {"valid_cycle": phase == "distribution_confirmed" and aligned and not invalidation, "missing_requirements": missing, "contradictions": warnings, "invalidation_reasons": invalidation}, "state_history": _history(accumulation, manipulation, distribution, execution)}
    return result


def normalized_amd(amd: dict[str, object]) -> dict[str, object]:
    accumulation, manipulation, distribution = amd["accumulation"], amd["manipulation"], amd["distribution"]
    return {"available": amd["available"], "cycle_type": amd["cycle_type"], "cycle_id": amd["cycle_id"], "direction": amd["direction"], "phase": amd["phase"]["current"], "confidence": amd["confidence"], "accumulation": {"low": accumulation.get("range_low"), "high": accumulation.get("range_high"), "start_time": accumulation.get("start_time"), "end_time": accumulation.get("end_time"), "locked": bool(accumulation.get("locked")), "duration_bars": accumulation.get("duration_bars"), "width_atr": accumulation.get("width_atr")}, "manipulation": {"side": manipulation.get("side"), "sweep_price": manipulation.get("sweep_price"), "sweep_time": manipulation.get("sweep_time"), "reclaimed": manipulation.get("reclaimed_range"), "reclaim_time": manipulation.get("reclaim_time"), "boundary_event": manipulation.get("boundary_event")}, "distribution": {"direction": distribution.get("direction"), "displacement": bool(distribution.get("forming")), "mss_price": distribution.get("structure_break_price"), "mss_time": distribution.get("structure_break_time"), "confirmed": amd["phase"]["current"] == "distribution_confirmed", "fvg": distribution.get("fvg")}, "target": amd["target"], "event_context": amd["event_context"], "next_required_event": amd["next_required_event"], "next_action": amd["next_action"], "quality_score": amd["quality_score"], "warnings": amd["warnings"], "countertrend": amd["countertrend"], "boundary_event": amd["boundary_event"], "validation": amd["validation"], "state": amd["state"], "state_history": amd["state_history"]}


def _phase(rows, accumulation, manipulation, distribution, execution, target, aligned, countertrend):
    if not accumulation: return "searching", "SEARCHING_FOR_ACCUMULATION", None, None
    started = accumulation["start_time"]
    if manipulation.get("boundary_event") == "accepted_breakout": return "failed", "AMD_FAILED", started, manipulation.get("sweep_time")
    if manipulation.get("both_sides_swept") and not distribution.get("detected"): return "failed", "AMD_FAILED", started, manipulation.get("sweep_time")
    if not manipulation.get("sweep_time"): return "accumulation", "WAITING_FOR_RANGE_EVENT", started, accumulation["end_time"]
    if not manipulation.get("detected"): return "manipulation_forming", "WAITING_FOR_RECLAIM", started, None
    if not distribution.get("forming"): return "manipulation_confirmed", "WAITING_FOR_DISPLACEMENT", started, manipulation.get("reclaim_time")
    if distribution.get("forming") and not distribution.get("detected"): return "distribution_forming", "DISTRIBUTION_FORMING", started, None
    execution_confirmed = bool(execution.get("confirmed_signal") or execution.get("confirmed_state")); complete = execution.get("state") in {"entry_valid", "entry_available"} and execution_confirmed and target.get("valid") and aligned and not countertrend
    return ("distribution_confirmed", "DISTRIBUTION_CONFIRMED", started, (execution.get("confirmed_signal") or execution.get("confirmed_state") or {}).get("candle_time")) if complete else ("distribution_forming", "WAITING_FOR_M5_CONFIRMATION", started, None)


def _target(top_down, direction, rows):
    context = (top_down.get("m15_setup") or {}).get("target_context") or {}; price = _number(context.get("price")); current = float(rows.iloc[-1]["close"]) if not rows.empty else None
    valid = price is not None and current is not None and ((direction == "bullish" and price > current) or (direction == "bearish" and price < current))
    return {"price": price if valid else None, "type": context.get("reason", "") if valid else "", "unswept": bool(valid), "valid": bool(valid)}


def _score(accumulation, liquidity, manipulation, distribution, aligned, rows, execution, target, phase):
    score = (int(accumulation.get("quality_score", 0)) if accumulation else 0) + (max((int(row.get("quality", 0)) for row in liquidity), default=0) if manipulation.get("sweep_time") else 0) + int(manipulation.get("quality_score", 0)) + int(distribution.get("quality_score", 0)) + (10 if aligned else 0) + (5 if not rows.empty else 0)
    cap = 100 if phase == "distribution_confirmed" and target.get("valid") else 90 if execution.get("confirmed_signal") or execution.get("confirmed_state") else 75 if distribution.get("forming") else 60 if manipulation.get("detected") else 40 if manipulation.get("sweep_time") else 25
    return min(cap, score)


def _missing(accumulation, liquidity, manipulation, distribution, execution, target, aligned):
    checks = (("accumulation", bool(accumulation)), ("range_liquidity", bool(liquidity)), ("liquidity_sweep", manipulation.get("detected")), ("range_reclaim", manipulation.get("reclaimed_range")), ("displacement", distribution.get("forming")), ("mss_bos", distribution.get("detected")), ("m5_confirmation", bool(execution.get("confirmed_signal") or execution.get("confirmed_state"))), ("target", target.get("valid")), ("top_down_alignment", aligned))
    return [name for name, passed in checks if not passed]


def _next(phase, direction, execution, target):
    if phase == "searching": return "valid_accumulation", "Waiting for a valid accumulation range."
    if phase == "accumulation": return "range_boundary_sweep", "Watch for a sweep of either range boundary."
    if phase == "manipulation_forming": return "range_reclaim", "Wait to see whether price reclaims the range."
    if phase == "manipulation_confirmed": return "displacement", "Wait for displacement away from the sweep."
    if phase == "distribution_forming" and not (execution.get("confirmed_signal") or execution.get("confirmed_state")): return f"completed_m5_{'bullish' if direction == 'bullish' else 'bearish'}_confirmation", "Wait for a completed M5 structure confirmation."
    if phase == "distribution_forming" and not target.get("valid"): return "valid_target_rr", "Confirm that the nearest target provides enough reward."
    if phase in {"failed", "expired"}: return "new_accumulation", "The AMD cycle expired or failed. Wait for a new range."
    return "none", "AMD distribution is confirmed; execution remains governed by the final trade plan."


def _history(accumulation, manipulation, distribution, execution):
    rows = []
    if accumulation: rows += [{"state": "ACCUMULATION_LOCKED", "timestamp": accumulation["end_time"]}, {"state": "WAITING_FOR_RANGE_EVENT", "timestamp": accumulation["end_time"]}]
    if manipulation.get("sweep_time"): rows.append({"state": "POSSIBLE_LOW_SWEEP" if manipulation["side"] == "low" else "POSSIBLE_HIGH_SWEEP", "timestamp": manipulation["sweep_time"]})
    if manipulation.get("reclaim_time"): rows.append({"state": "MANIPULATION_CONFIRMED", "timestamp": manipulation["reclaim_time"]})
    if distribution.get("displacement_start"): rows.append({"state": "DISTRIBUTION_FORMING", "timestamp": distribution["displacement_start"]})
    confirmed = execution.get("confirmed_signal") or execution.get("confirmed_state") or {}
    if confirmed.get("candle_time"): rows.append({"state": "WAITING_FOR_M5_CONFIRMATION", "timestamp": confirmed["candle_time"]})
    return rows


def _abnormal(rows, accumulation):
    if rows.empty or not accumulation: return False
    return float((rows.iloc[-1]["high"] - rows.iloc[-1]["low"])) > float(accumulation["atr"]) * 3
def _reduce(value): return "medium" if value == "high" else "low"
def _cycle_id(symbol, cycle_type, accumulation): return "amd-" + hashlib.sha256(json.dumps({"symbol": symbol, "type": cycle_type, "start": accumulation["start_time"], "end": accumulation["end_time"], "low": accumulation["range_low"], "high": accumulation["range_high"]}, sort_keys=True).encode()).hexdigest()[:20]
def _clean(frame, boundary):
    if frame is None or frame.empty: return pd.DataFrame(columns=["time", "open", "high", "low", "close"])
    rows = frame.copy(); rows["time"] = pd.to_datetime(rows["time"], utc=True, errors="coerce"); cutoff = _utc(boundary); return rows.loc[rows["time"] + pd.Timedelta(minutes=5) <= cutoff].dropna().sort_values("time").drop_duplicates("time").reset_index(drop=True)
def _utc(value):
    stamp = pd.Timestamp(value); return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
def _number(value):
    try: return float(value) if value is not None else None
    except (TypeError, ValueError): return None
def _empty_accumulation(): return {"detected": False, "range_low": None, "range_high": None, "start_time": None, "end_time": None, "duration_bars": 0, "width": None, "width_atr": None, "overlap_ratio": None, "directional_efficiency": None, "boundary_tests_high": 0, "boundary_tests_low": 0, "quality_score": 0, "locked": False}
def _empty_manipulation(): return {"detected": False, "forming": False, "side": None, "sweep_price": None, "sweep_time": None, "excursion_distance": None, "excursion_atr": None, "reclaimed_range": False, "reclaim_time": None, "close_back_inside": False, "liquidity_source": "", "quality_score": 0, "boundary_event": "unclear", "both_sides_swept": False}
def _empty_distribution(): return {"detected": False, "forming": False, "direction": None, "displacement_start": None, "displacement_end": None, "structure_break_price": None, "structure_break_time": None, "fvg": None, "expansion_atr": None, "quality_score": 0}
