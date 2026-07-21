"""Strategy-neutral entry timing and chase-risk evaluation."""

from __future__ import annotations

from analysis.price_precision import display_precision


LATE_STATUSES = {"extended", "too_late", "missed", "invalid"}


def evaluate_entry_timing(
    *,
    symbol: str,
    asset_type: str,
    direction: str,
    current_price: object,
    entry_zone: object = None,
    trigger_level: object = None,
    stop_loss: object = None,
    tp1: object = None,
    tp2: object = None,
    atr: object = None,
    allowed_entry_distance: object = None,
) -> dict[str, object]:
    """Evaluate whether entering at the current price would be chasing."""
    side = _direction(direction)
    current = _number(current_price)
    zone_bottom, zone_top = _zone_bounds(entry_zone)
    trigger = _number(trigger_level)
    entry = trigger if trigger is not None else _midpoint(zone_bottom, zone_top)
    stop = _number(stop_loss)
    target1 = _number(tp1)
    target2 = _number(tp2)
    atr_value = _positive_number(atr)
    unit_size, unit_label = _distance_unit(symbol, asset_type)

    base = {
        "entry_timing_status": "invalid",
        "can_enter_now": False,
        "available": False,
        "distance_from_entry": None,
        "distance_from_entry_pips": None,
        "distance_unit": unit_label,
        "distance_to_tp1": None,
        "distance_to_tp1_pips": None,
        "planned_rr_to_tp1": None,
        "remaining_rr_to_tp1": None,
        "current_risk": None,
        "progress_to_tp1": None,
        "chase_risk": "high",
        "message": "Entry timing is unavailable until a valid trade plan exists.",
        "next_action": "Look for a valid entry, stop, and target before considering a trade.",
    }
    if side is None or None in {current, entry, stop, target1}:
        return base

    planned_risk = _directional_risk(side, entry, stop)
    planned_reward = _directional_reward(side, entry, target1)
    if planned_risk <= 0 or planned_reward <= 0:
        return {
            **base,
            "available": True,
            "message": "Setup is invalidated. Do not enter.",
            "next_action": "Do not enter. Look for a new valid setup.",
        }

    distance = abs(current - entry)
    remaining_reward = _directional_reward(side, current, target1)
    current_risk = _directional_risk(side, current, stop)
    planned_rr = planned_reward / planned_risk
    current_rr = remaining_reward / current_risk if current_risk > 0 and remaining_reward > 0 else 0.0
    favorable_move = _directional_reward(side, entry, current)
    progress = max(favorable_move / planned_reward, 0.0)
    distance_from_zone = _distance_from_zone(current, zone_bottom, zone_top, entry)
    allowed = _positive_number(allowed_entry_distance)
    if allowed is None:
        allowed = max((atr_value or 0.0) * 0.2, planned_risk * 0.25, abs(entry) * 0.00002)
    atr_distance = distance_from_zone / atr_value if atr_value else None
    inside_zone = zone_bottom is not None and zone_top is not None and zone_bottom <= current <= zone_top
    invalidated = current <= stop if side == "buy" else current >= stop
    target_reached = current >= target1 if side == "buy" else current <= target1

    metrics = {
        **base,
        "available": True,
        "distance_from_entry": round(distance, 8),
        "distance_from_entry_pips": round(distance / unit_size, 1),
        "distance_to_tp1": round(max(remaining_reward, 0.0), 8),
        "distance_to_tp1_pips": round(max(remaining_reward, 0.0) / unit_size, 1),
        "planned_rr_to_tp1": round(planned_rr, 2),
        "remaining_rr_to_tp1": round(current_rr, 2),
        "current_risk": round(max(current_risk, 0.0), 8),
        "progress_to_tp1": round(progress, 3),
        "entry_price": round(entry, 8),
        "current_price": round(current, 8),
        "stop_loss": round(stop, 8),
        "tp1": round(target1, 8),
        "tp2": round(target2, 8) if target2 is not None else None,
        "allowed_entry_distance": round(allowed, 8),
        "atr_distance": round(atr_distance, 2) if atr_distance is not None else None,
    }

    if invalidated:
        return {
            **metrics,
            "entry_timing_status": "invalid",
            "chase_risk": "high",
            "message": "Setup is invalidated. Do not enter.",
            "next_action": "Do not enter. Look for a new setup after structure resets.",
        }

    if target_reached:
        return {
            **metrics,
            "entry_timing_status": "missed",
            "chase_risk": "high",
            "message": "Setup already moved to target area. Look for the next setup.",
            "next_action": "Do not chase. Look for the next setup.",
        }

    price_label = _format_price(entry, symbol, asset_type)
    moved_toward_target = favorable_move > 0
    too_late = (
        moved_toward_target
        and (
            progress >= 0.70
            or current_rr < 1.0
            or (atr_distance is not None and atr_distance >= 1.0)
        )
    )
    extended = (
        moved_toward_target
        and (
            progress >= 0.35
            or distance_from_zone > allowed
            or (atr_distance is not None and atr_distance >= 0.5)
        )
    )

    if too_late:
        return {
            **metrics,
            "entry_timing_status": "too_late",
            "chase_risk": "high",
            "message": "Price already moved away from the entry area.",
            "next_action": "Do not chase. Look for a fresh entry or a clean pullback.",
        }

    if extended:
        return {
            **metrics,
            "entry_timing_status": "extended",
            "chase_risk": "high",
            "message": "Price has moved away from entry. Do not chase. Look for a pullback.",
            "next_action": f"Look for a clean pullback toward {price_label} before reassessing.",
        }

    if inside_zone:
        can_enter = current_rr >= 1.0
        return {
            **metrics,
            "entry_timing_status": "at_entry" if can_enter else "too_late",
            "can_enter_now": can_enter,
            "chase_risk": "low" if can_enter else "high",
            "message": (
                "Price is inside the entry zone. Confirm risk before entering."
                if can_enter
                else "Price already moved away from the entry area."
            ),
            "next_action": (
                "Confirm the setup is still active before entering."
                if can_enter
                else "Do not chase. Look for a fresh entry or a clean pullback."
            ),
        }

    near_entry = distance_from_zone <= allowed and current_rr >= 1.0
    return {
        **metrics,
        "entry_timing_status": "near_entry",
        "can_enter_now": near_entry,
        "chase_risk": "medium",
        "message": "Price is near the entry zone. Entry may still be valid if risk/reward holds.",
        "next_action": (
            "Confirm risk/reward and the original setup before entering."
            if near_entry
            else f"Look for price to return toward {price_label} and confirm the setup again."
        ),
    }


def _direction(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"buy", "bullish", "long"}:
        return "buy"
    if normalized in {"sell", "bearish", "short"}:
        return "sell"
    return None


def _directional_risk(side: str, entry: float, stop: float) -> float:
    return entry - stop if side == "buy" else stop - entry


def _directional_reward(side: str, entry: float, target: float) -> float:
    return target - entry if side == "buy" else entry - target


def _zone_bounds(value: object) -> tuple[float | None, float | None]:
    if not isinstance(value, dict):
        point = _number(value)
        return point, point
    top = _number(value.get("top", value.get("top_price")))
    bottom = _number(value.get("bottom", value.get("bottom_price")))
    if top is None or bottom is None:
        return None, None
    return min(top, bottom), max(top, bottom)


def _midpoint(bottom: float | None, top: float | None) -> float | None:
    if bottom is None or top is None:
        return None
    return (bottom + top) / 2


def _distance_from_zone(
    price: float,
    bottom: float | None,
    top: float | None,
    fallback: float,
) -> float:
    if bottom is None or top is None:
        return abs(price - fallback)
    if bottom <= price <= top:
        return 0.0
    return bottom - price if price < bottom else price - top


def _distance_unit(symbol: str, asset_type: str) -> tuple[float, str]:
    normalized_symbol = str(symbol or "").upper().replace(" ", "")
    normalized_asset = str(asset_type or "").lower()
    if normalized_asset == "forex":
        return (0.01, "pips") if normalized_symbol.endswith("/JPY") or normalized_symbol.endswith("JPY") else (0.0001, "pips")
    if normalized_asset in {"index", "crypto"} or normalized_asset.startswith("derived"):
        return 1.0, "points"
    return 0.01, "points"


def _format_price(value: float, symbol: str, asset_type: str) -> str:
    # Reuses the canonical precision rule (analysis.price_precision.display_precision) so
    # this message text never drifts from the chart, decision panel, and overlay labels.
    precision = display_precision(symbol, asset_type, value)
    return f"{value:.{precision}f}"


def _positive_number(value: object) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None


def _number(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
