"""Price-distance and risk/reward metrics for finalized trade levels."""

from __future__ import annotations


def build_trade_metrics(
    *,
    symbol: str,
    asset_type: str,
    direction: str,
    levels_mode: str,
    levels: dict[str, object],
    objective_plan: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return display-ready distances without creating new trade levels."""
    objective_plan = objective_plan or {}
    unit_size, unit_label = _distance_unit(symbol, asset_type)
    entry = _number(levels.get("trigger_level"))
    if entry is None:
        entry = _entry_price(levels.get("entry_zone"))
    finalized = str(levels_mode).lower() == "final"
    projected = not finalized and str(objective_plan.get("decision", "PENDING")).upper() != "REJECT"
    stop = _number(levels.get("stop_loss")) if finalized else _number(levels.get("invalidation"))
    tp1 = _number(levels.get("tp1")) if finalized else _objective_price(objective_plan.get("primary_objective"))
    tp2 = _number(levels.get("tp2")) if finalized else _objective_price(objective_plan.get("secondary_objective"))

    if not finalized and not projected:
        entry = stop = tp1 = tp2 = None

    risk_price = abs(entry - stop) if entry is not None and stop is not None else None
    risk = _distance(risk_price, unit_size, unit_label)

    tp1_metrics = _target_metrics(entry, tp1, risk_price, unit_size, unit_label, direction)
    tp2_metrics = _target_metrics(entry, tp2, risk_price, unit_size, unit_label, direction)

    return {
        "unit": unit_label,
        "unit_size": unit_size,
        "entry_price": entry,
        "stop_loss": stop,
        "plan_mode": "final" if finalized else "projected" if projected else "unavailable",
        "risk": risk,
        "tp1": tp1_metrics,
        "tp2": tp2_metrics,
        "warnings": _reward_warnings(tp1_metrics, tp2_metrics),
    }


def _distance_unit(symbol: str, asset_type: str) -> tuple[float, str]:
    normalized_symbol = str(symbol or "").upper().replace(" ", "")
    normalized_asset = str(asset_type or "").lower()
    if normalized_asset == "forex":
        return (0.01, "pips") if normalized_symbol.endswith("/JPY") or normalized_symbol.endswith("JPY") else (0.0001, "pips")
    if normalized_asset in {"index", "crypto"}:
        return 1.0, "points"
    return 0.01, "points"


def _entry_price(value: object) -> float | None:
    if isinstance(value, dict):
        top = _number(value.get("top", value.get("top_price")))
        bottom = _number(value.get("bottom", value.get("bottom_price")))
        if top is not None and bottom is not None:
            return (top + bottom) / 2
    return _number(value)


def _objective_price(value: object) -> float | None:
    return _number(value.get("price")) if isinstance(value, dict) else None


def _target_metrics(
    entry: float | None,
    target: float | None,
    risk_price: float | None,
    unit_size: float,
    unit_label: str,
    direction: str,
) -> dict[str, object] | None:
    if entry is None or target is None:
        return None

    normalized_direction = str(direction or "").lower()
    reward_price = target - entry if normalized_direction == "bullish" else entry - target
    if reward_price <= 0:
        return None

    distance = _distance(reward_price, unit_size, unit_label)
    rr = round(reward_price / risk_price, 2) if risk_price and risk_price > 0 else None
    return {
        "price": target,
        "distance": distance,
        "risk_reward": rr,
    }


def _distance(price_distance: float | None, unit_size: float, unit_label: str) -> dict[str, object] | None:
    if price_distance is None or unit_size <= 0:
        return None
    value = round(abs(price_distance) / unit_size, 1)
    display_value = str(int(value)) if value.is_integer() else f"{value:.1f}"
    return {
        "value": value,
        "unit": unit_label,
        "display": f"{display_value} {unit_label}",
    }


def _reward_warnings(
    tp1: dict[str, object] | None,
    tp2: dict[str, object] | None,
) -> list[str]:
    tp1_rr = _number((tp1 or {}).get("risk_reward"))
    tp2_rr = _number((tp2 or {}).get("risk_reward"))
    if tp1_rr is None or tp1_rr >= 1.0:
        return []
    if tp2_rr is not None and tp2_rr >= 1.0:
        return ["TP1 has weak reward. TP2 is the first acceptable target."]
    return ["TP1 has weak reward. No acceptable target is available yet."]


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number
