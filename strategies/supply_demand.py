"""Supply and Demand strategy for the shared TradeScor assistant."""

from __future__ import annotations

import pandas as pd

from analysis.candles import to_unix_seconds
from analysis.objectives import analyze_objectives
from analysis.setup_state import (
    build_setup_state,
    event_record,
    find_confirmation_event,
    find_zone_reaction,
    invalidation_event,
    select_trigger_after_zone,
)
from scanner.objective_engine import levels_from_objective_plan
from scanner.supply_demand_zones import detect_supply_demand_zones
from strategies.base import EMPTY_LEVELS, make_strategy_result, research_candidate, research_eligible, research_explain


STRATEGY_NAME = "Supply & Demand"
STRATEGY_VERSION = "supply_demand_v1"

def is_eligible(context): return research_eligible(context, "supply_demand")
def detect_setup(context): return research_candidate(context, "supply_demand")
def build_candidate(context, setup): return setup
def explain(candidate): return research_explain(candidate)


def analyze(
    candles: pd.DataFrame,
    shared_analysis: dict[str, object],
    *,
    symbol: str,
    timeframe: str,
    macro_context: dict[str, object] | None = None,
    multi_timeframe_context: dict[str, pd.DataFrame] | None = None,
    top_down_context: dict[str, object] | None = None,
    analysis_timestamp: object | None = None,
) -> tuple[dict[str, object], None]:
    """Analyze one current supply or demand setup without fetching data."""
    if len(candles) < 30:
        return _empty("Not enough candles to identify a reliable supply or demand zone.")

    structure = shared_analysis.get("structure") or {}
    volatility = shared_analysis.get("volatility") or {}
    current_price = float(candles.iloc[-1]["close"])
    atr = float(volatility.get("atr") or (candles["high"] - candles["low"]).tail(14).mean())
    zones = detect_supply_demand_zones(candles, atr=atr)
    direction = _direction(shared_analysis, top_down_context or {}, zones, current_price)
    zone = _active_zone(candles, zones, direction, current_price, atr)

    if not zone:
        return _empty("No clean active supply or demand zone is close enough to current price.")

    direction = "Bullish" if zone["type"] in {"support", "demand"} else "Bearish"
    quality = _zone_quality(candles, zone, direction, current_price, atr)
    in_zone = _inside_zone(current_price, zone)
    near_zone = _distance_to_zone(current_price, zone) <= atr * 1.5
    entry_proximity = _distance_to_zone(current_price, zone) <= atr * 0.35
    entered_now = _entered_on_current(candles, zone)
    zone_index = int(zone.get("start_index", 0))
    reaction_event = find_zone_reaction(candles, zone, direction, after_index=int(zone.get("confirmed_index", zone_index)))
    reaction = bool(reaction_event)
    trigger = select_trigger_after_zone(shared_analysis.get("swings") or {}, direction, zone_index)
    if not trigger:
        trigger = _trigger_level(structure, direction)
    confirmation_event = find_confirmation_event(
        candles,
        direction,
        trigger,
        after_index=max(zone_index + 1, int(reaction_event.get("index", zone_index)) + 1),
    )
    confirmed = bool(confirmation_event)
    invalidation = _invalidation(zone, direction, atr)
    invalidated_event = invalidation_event(
        candles,
        direction,
        invalidation,
        after_index=int(confirmation_event.get("index", len(candles))) + 1,
    ) if confirmed else {}
    technical_state = _state(
        candles,
        zone,
        direction,
        quality,
        in_zone,
        near_zone,
        entered_now,
        reaction,
        trigger,
        confirmed,
        entry_proximity,
    )
    if invalidated_event:
        technical_state = "INVALIDATED"
    provisional = _provisional_levels(zone, invalidation)
    entry = _zone_midpoint(zone)
    objective_plan = analyze_objectives(
        direction=direction,
        entry_price=entry,
        stop_loss=invalidation,
        shared_analysis=shared_analysis,
        context_candles=multi_timeframe_context or {},
        analysis_candles=candles,
    )
    trade_accepted = technical_state == "ENTRY_READY" and bool(objective_plan.get("trade_accepted"))
    state = technical_state if technical_state != "ENTRY_READY" or trade_accepted else "NO_TRADE"
    levels_mode = "final" if trade_accepted else "hidden"
    levels = _final_levels(provisional, objective_plan) if trade_accepted else EMPTY_LEVELS.copy()
    trade_decision = "ACCEPT" if trade_accepted else "REJECT" if technical_state == "ENTRY_READY" else "PENDING"
    story = _story(direction, state, zone, quality, reaction, confirmed, entry_proximity, objective_plan)
    next_action = _next_action(state, direction, zone, trigger, objective_plan)
    reasons = _why(direction, zone, quality, in_zone, reaction, confirmed, entry_proximity, objective_plan)
    overlays = _overlays(candles, zone, quality, trigger, invalidation, levels, levels_mode)

    result = make_strategy_result(
        strategy_name=STRATEGY_NAME,
        bias=direction,
        state=state,
        score=int(quality["score"]),
        market_story=story,
        next_trigger=next_action,
        levels_mode=levels_mode,
        levels=levels,
        overlays=overlays,
        progress=_progress(state),
        why=reasons,
    )
    result.update(
        {
            "setup_quality": int(quality["score"]),
            "trade_quality": int(objective_plan.get("trade_quality", 0) or 0),
            "trade_decision": trade_decision,
            "objective_plan": objective_plan,
            "confirmation_achieved": confirmed and reaction,
            "entry_zone_available": True,
            "entry_proximity": entry_proximity,
            "price_location": "Inside demand" if in_zone and direction == "Bullish" else "Inside supply" if in_zone else "Approaching demand" if direction == "Bullish" else "Approaching supply",
            "market_intent": "Testing buyer interest" if direction == "Bullish" else "Testing seller interest",
            "supply_demand_details": {
                "zone": zone,
                "zone_quality": quality,
                "reaction": reaction,
                "trigger": trigger,
                "confirmation_achieved": confirmed,
                "confirmation_event": confirmation_event,
                "reaction_event": reaction_event,
                "entry_proximity": entry_proximity,
                "technical_state": technical_state,
            },
            "timeline": _timeline(candles, direction, state, zone, reaction, confirmed),
        }
    )
    completed_events = [event_record("zone_identified", zone.get("confirmed_at", zone.get("start_time", candles.iloc[0]["time"])))]
    if reaction_event:
        completed_events.append(reaction_event)
    if trigger:
        completed_events.append(event_record("trigger_identified", trigger.get("confirmed_at", trigger.get("time", candles.iloc[0]["time"])), level=trigger.get("price")))
    if confirmation_event:
        completed_events.append(confirmation_event)
    if invalidated_event:
        completed_events.append(invalidated_event)
    result["setup_state"] = build_setup_state(
        strategy="supply_demand",
        direction=direction,
        created_at=zone.get("confirmed_at", zone.get("start_time", analysis_timestamp or candles.iloc[0]["time"])),
        current_state=state,
        completed_events=completed_events,
        active_zone=zone,
        trigger_level=trigger,
        confirmation_event=confirmation_event,
        entry_zone=zone,
        invalidation=invalidation,
        targets=objective_plan.get("targets", []),
        invalidated=bool(invalidated_event),
        invalidation_reason="Price closed beyond the supply or demand invalidation." if invalidated_event else None,
    )
    return result, None


def _empty(reason: str) -> tuple[dict[str, object], None]:
    return (
        make_strategy_result(
            strategy_name=STRATEGY_NAME,
            bias="Neutral",
            state="NO_TRADE",
            score=0,
            market_story=reason,
            next_trigger="Wait for price to approach a fresh supply or demand zone.",
            progress=_progress("NO_TRADE"),
            why=[{"key": "zone", "status": "waiting", "text": reason}],
        ),
        None,
    )


def _direction(shared: dict[str, object], top_down: dict[str, object], zones: dict[str, object], price: float) -> str:
    alignment = str(top_down.get("overall_alignment", "Neutral"))
    selected = str((shared.get("trend") or {}).get("direction", "Neutral"))
    if alignment in {"Bullish", "Bearish"}:
        return alignment
    if selected in {"Bullish", "Bearish"}:
        return selected

    demand = _nearest_candidate(zones.get("demand", []), price)
    supply = _nearest_candidate(zones.get("supply", []), price)
    if not demand and not supply:
        return "Neutral"
    if demand and not supply:
        return "Bullish"
    if supply and not demand:
        return "Bearish"

    demand_distance = abs(price - float(demand["price"]))
    supply_distance = abs(price - float(supply["price"]))
    if abs(demand_distance - supply_distance) <= 1e-12:
        return "Neutral"
    return "Bullish" if demand_distance < supply_distance else "Bearish"


def _nearest_candidate(candidates: list[dict[str, object]], price: float) -> dict[str, object]:
    active = [zone for zone in candidates if zone.get("status") != "invalidated"]
    if not active:
        return {}
    return min(active, key=lambda zone: abs(price - float(zone["price"])))


def _active_zone(
    candles: pd.DataFrame,
    zones: dict[str, object],
    direction: str,
    price: float,
    atr: float,
) -> dict[str, object] | None:
    if direction not in {"Bullish", "Bearish"}:
        return None
    candidates = zones.get("demand", []) if direction == "Bullish" else zones.get("supply", [])
    scored = []
    for zone in candidates[-8:]:
        quality = _zone_quality(candles, zone, direction, price, atr)
        distance = _distance_to_zone(price, zone)
        if quality["fully_mitigated"] or zone.get("status") == "overused" or distance > atr * 12:
            continue
        scored.append((int(quality["score"]), -distance, int(zone.get("start_index", 0)), zone))
    if not scored:
        return None
    return max(scored, key=lambda row: (row[0], row[1], row[2]))[3]


def _zone_quality(
    candles: pd.DataFrame,
    zone: dict[str, object],
    direction: str,
    price: float,
    atr: float,
) -> dict[str, object]:
    start = max(0, int(zone.get("start_index", 0)))
    after = candles.iloc[start + 1 : min(len(candles), start + 9)]
    top = float(zone["top_price"])
    bottom = float(zone["bottom_price"])
    if zone.get("impulse_atr") is not None:
        impulse = float(zone["impulse_atr"])
    elif after.empty:
        impulse = 0.0
    elif direction == "Bullish":
        impulse = max(0.0, float(after["high"].max()) - top) / max(atr, 1e-12)
    else:
        impulse = max(0.0, bottom - float(after["low"].min())) / max(atr, 1e-12)

    fully_mitigated = zone.get("status") == "invalidated"
    near = _distance_to_zone(price, zone) <= atr * 5
    score = 15
    score += 40 if impulse >= 2.0 else 30 if impulse >= 1.5 else 20 if impulse >= 1.25 else 0
    score += 25 if zone.get("fresh") else 16 if int(zone.get("touch_count", 0)) <= 1 else 5
    score += 10 if float(zone.get("base_quality", 0)) >= 0.35 else 5
    score += 10 if near else 3
    return {
        "score": min(100, score),
        "grade": "Strong" if score >= 80 else "Valid" if score >= 60 else "Weak",
        "impulse_atr": round(impulse, 2),
        "strong_impulse": impulse >= 1.5,
        "fully_mitigated": fully_mitigated,
        "near_current_price": near,
        "fresh": bool(zone.get("fresh")),
        "touch_count": int(zone.get("touch_count", 0)),
        "status": zone.get("status", "unknown"),
        "valid": score >= 60 and not fully_mitigated,
    }


def _state(
    candles: pd.DataFrame,
    zone: dict[str, object],
    direction: str,
    quality: dict[str, object],
    in_zone: bool,
    near_zone: bool,
    entered_now: bool,
    reaction: bool,
    trigger: dict[str, object],
    confirmed: bool,
    entry_proximity: bool,
) -> str:
    close = float(candles.iloc[-1]["close"])
    if quality.get("fully_mitigated") or (direction == "Bullish" and close < float(zone["bottom_price"])) or (direction == "Bearish" and close > float(zone["top_price"])):
        return "INVALIDATED"
    if not quality.get("valid"):
        return "ZONE_IDENTIFIED"
    if confirmed and reaction and entry_proximity:
        return "ENTRY_READY"
    if confirmed and reaction:
        return "CONFIRMED_WAITING_FOR_ENTRY"
    if reaction and trigger:
        return "WAITING_FOR_CONFIRMATION"
    if entered_now:
        return "PRICE_IN_ZONE"
    if in_zone:
        return "WAITING_FOR_REACTION"
    if near_zone:
        return "WAITING_FOR_PRICE_TO_ENTER_ZONE"
    return "ZONE_IDENTIFIED"


def _reaction(candles: pd.DataFrame, zone: dict[str, object], direction: str) -> bool:
    top = float(zone["top_price"])
    bottom = float(zone["bottom_price"])
    for _, candle in candles.tail(4).iterrows():
        touched = float(candle["low"]) <= top and float(candle["high"]) >= bottom
        bullish = float(candle["close"]) > float(candle["open"])
        if touched and ((direction == "Bullish" and bullish) or (direction == "Bearish" and not bullish)):
            return True
    return False


def _trigger_level(structure: dict[str, object], direction: str) -> dict[str, object]:
    return (structure.get("minor_swing_high") or {}) if direction == "Bullish" else (structure.get("minor_swing_low") or {})


def _confirmed(price: float, trigger: dict[str, object], direction: str) -> bool:
    if not trigger or trigger.get("price") is None:
        return False
    return price > float(trigger["price"]) if direction == "Bullish" else price < float(trigger["price"])


def _invalidation(zone: dict[str, object], direction: str, atr: float) -> float:
    buffer = max(atr * 0.2, abs(_zone_midpoint(zone)) * 0.00003)
    value = float(zone["bottom_price"]) - buffer if direction == "Bullish" else float(zone["top_price"]) + buffer
    return round(value, 6)


def _provisional_levels(zone: dict[str, object], invalidation: float) -> dict[str, object]:
    return {
        "entry_zone": {"top": float(zone["top_price"]), "bottom": float(zone["bottom_price"])},
        "stop_loss": invalidation,
        "tp1": None,
        "tp2": None,
        "rr1": None,
        "rr2": None,
    }


def _final_levels(provisional: dict[str, object], objective: dict[str, object]) -> dict[str, object]:
    levels = levels_from_objective_plan(
        entry_zone=provisional["entry_zone"],
        stop_loss=provisional["stop_loss"],
        objective_plan=objective,
    )
    levels["primary_objective"] = objective.get("primary_objective")
    levels["secondary_objective"] = objective.get("secondary_objective")
    return levels


def _overlays(
    candles: pd.DataFrame,
    zone: dict[str, object],
    quality: dict[str, object],
    trigger: dict[str, object],
    invalidation: float,
    levels: dict[str, object],
    mode: str,
) -> dict[str, object]:
    zone_overlay = {
        "type": zone.get("type", "zone"),
        "tag": "Demand" if zone.get("type") == "demand" else "Supply",
        "label": zone.get("label", "Active Zone"),
        "tooltip": (
            f"{zone.get('label', 'Active zone')} · {quality.get('grade', 'Valid')} quality · "
            f"{zone.get('status', 'active').title()} · {quality.get('impulse_atr', 0)} ATR departure"
        ),
        "visual_variant": "supply-demand",
        "quality": quality.get("grade", "Valid"),
        "zone_status": zone.get("status", "active"),
        "impulse_atr": quality.get("impulse_atr"),
        "touch_count": quality.get("touch_count", 0),
        "proximal_price": zone.get("proximal_price"),
        "distal_price": zone.get("distal_price"),
        "departure_time": to_unix_seconds(zone.get("departure_time", zone["confirmed_at"])),
        "start_time": to_unix_seconds(zone["start_time"]),
        "end_time": to_unix_seconds(candles.iloc[-1]["time"]),
        "top": float(zone["top_price"]),
        "bottom": float(zone["bottom_price"]),
    }
    return {
        "current_price": {"price": float(candles.iloc[-1]["close"]), "time": to_unix_seconds(candles.iloc[-1]["time"])},
        "supply_demand_zone": zone_overlay,
        "pullback_zone": zone_overlay,
        "reaction_level": trigger,
        "confirmation_level": {"price": trigger.get("price"), "label": "Trigger"} if trigger else {},
        "invalidation_level": invalidation,
        "entry_zone": zone_overlay if mode == "final" else None,
        "stop_loss": levels.get("stop_loss") if mode == "final" else None,
        "tp1": levels.get("tp1") if mode == "final" else None,
        "tp2": levels.get("tp2") if mode == "final" else None,
        "levels_mode": mode,
    }


def _story(direction, state, zone, quality, reaction, confirmed, proximity, objective) -> str:
    side = "demand" if direction == "Bullish" else "supply"
    if state == "ENTRY_READY":
        return f"{direction} structure is testing a {quality['grade'].lower()} {side} zone. The zone reacted, confirmation completed, and price is at the valid entry location."
    if state == "NO_TRADE":
        return f"The {side} reaction completed technically, but no trade is valid because {str(objective.get('reason', 'trade quality is insufficient')).lower()}"
    if state == "CONFIRMED_WAITING_FOR_ENTRY":
        return f"The {side} zone produced a valid reaction and confirmation, but price is extended. Wait for price to return to the zone."
    if state == "INVALIDATED":
        return f"The active {side} zone failed and is no longer valid. TradeScor is waiting for a fresh zone."
    return f"TradeScor is monitoring a {quality['grade'].lower()} {side} zone. Reaction is {'present' if reaction else 'not confirmed'} and the trigger is {'complete' if confirmed else 'still pending'}."


def _next_action(state, direction, zone, trigger, objective) -> str:
    side = "demand" if direction == "Bullish" else "supply"
    if state == "ENTRY_READY":
        return "Price is inside the confirmed zone. Use only the validated trade plan."
    if state == "NO_TRADE":
        return f"Stand aside. {objective.get('reason', 'The available reward does not justify the risk.')}"
    if state == "CONFIRMED_WAITING_FOR_ENTRY":
        return f"Wait for price to return to the {side} zone between {float(zone['bottom_price']):.6f} and {float(zone['top_price']):.6f}."
    if state in {"PRICE_IN_ZONE", "WAITING_FOR_REACTION"}:
        return f"Wait for {'buyers' if direction == 'Bullish' else 'sellers'} to defend the {side} zone."
    if state == "WAITING_FOR_CONFIRMATION" and trigger:
        relation = "above" if direction == "Bullish" else "below"
        return f"Wait for a candle close {relation} {float(trigger['price']):.6f}."
    if state == "INVALIDATED":
        return "Remain flat and wait for a fresh unmitigated zone."
    return f"Wait for price to enter the active {side} zone."


def _why(direction, zone, quality, in_zone, reaction, confirmed, proximity, objective):
    side = "demand" if direction == "Bullish" else "supply"
    return [
        {"key": "bias", "status": "completed", "text": f"Market bias favors {direction.lower()} {side} logic."},
        {"key": "zone", "status": "completed" if quality["valid"] else "waiting", "text": f"The active {side} zone is rated {quality['grade'].lower()} after a {quality['impulse_atr']} ATR impulse."},
        {"key": "location", "status": "completed" if in_zone else "waiting", "text": "Price is inside the active zone." if in_zone else "Price has not reached the active zone yet."},
        {"key": "reaction", "status": "completed" if reaction else "waiting", "text": "The zone produced a directional reaction." if reaction else "A directional reaction is still missing."},
        {"key": "confirmation", "status": "completed" if confirmed and proximity else "waiting", "text": "Confirmation and entry location are aligned." if confirmed and proximity else "Confirmation or entry proximity is still missing."},
    ]


def _progress(state: str) -> list[dict[str, object]]:
    stages = [
        ("zone", "Zone Identified", {"ZONE_IDENTIFIED", "WAITING_FOR_PRICE_TO_ENTER_ZONE"}),
        ("price", "Price In Zone", {"PRICE_IN_ZONE", "WAITING_FOR_REACTION"}),
        ("reaction", "Reaction", {"WAITING_FOR_CONFIRMATION"}),
        ("confirmation", "Confirmation", {"CONFIRMED_WAITING_FOR_ENTRY"}),
        ("entry", "Entry Ready", {"ENTRY_READY"}),
    ]
    current_index = next((index for index, (_key, _label, states) in enumerate(stages) if state in states), -1)
    rows = []
    for index, (key, label, _states) in enumerate(stages):
        status = "completed" if current_index > index or state == "ENTRY_READY" else "current" if index == current_index else "inactive"
        if state in {"NO_TRADE", "INVALIDATED"} and index == 0:
            status = "invalidated"
        rows.append({"key": key, "label": label, "status": status, "is_current": status == "current"})
    return rows


def _timeline(candles, direction, state, zone, reaction, confirmed):
    time = str(candles.iloc[-1]["time"])
    events = [
        {"time": zone.get("start_time", time), "event_type": "Zone Identified", "direction": direction, "explanation": zone.get("label", "Active zone identified.")},
    ]
    if reaction:
        events.append({"time": time, "event_type": "Zone Reaction", "direction": direction, "explanation": "Price defended the active zone."})
    if confirmed:
        events.append({"time": time, "event_type": "Confirmation", "direction": direction, "explanation": "Price closed beyond the reaction trigger."})
    events.append({"time": time, "event_type": state.replace("_", " ").title(), "direction": direction, "explanation": "Current Supply & Demand state."})
    return events


def _inside_zone(price: float, zone: dict[str, object]) -> bool:
    return float(zone["bottom_price"]) <= price <= float(zone["top_price"])


def _distance_to_zone(price: float, zone: dict[str, object]) -> float:
    if _inside_zone(price, zone):
        return 0.0
    return min(abs(price - float(zone["bottom_price"])), abs(price - float(zone["top_price"])))


def _entered_on_current(candles: pd.DataFrame, zone: dict[str, object]) -> bool:
    if len(candles) < 2:
        return False
    current = float(candles.iloc[-1]["close"])
    previous = float(candles.iloc[-2]["close"])
    return _inside_zone(current, zone) and not _inside_zone(previous, zone)


def _zone_midpoint(zone: dict[str, object]) -> float:
    return (float(zone["top_price"]) + float(zone["bottom_price"])) / 2
