"""Target-selection intelligence for TradeScor trade plans.

The objective engine does not fetch data. It ranks objectives already found in
the loaded chart and its cached higher-timeframe context, then rejects plans
that do not offer enough reward for the proposed risk.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


DEFAULT_MIN_RISK_REWARD = 1.5


def build_objective_plan(
    *,
    direction: str | None,
    entry_price: float | None,
    stop_loss: float | None,
    swings: dict[str, list[dict[str, object]]] | None = None,
    equal_levels: dict[str, list[dict[str, object]]] | None = None,
    zones: dict[str, object] | None = None,
    fvgs: list[dict[str, object]] | None = None,
    context_candles: dict[str, pd.DataFrame] | None = None,
    liquidity_map: dict[str, object] | None = None,
    extra_candidates: list[dict[str, object]] | None = None,
    analysis_candles: pd.DataFrame | None = None,
    min_risk_reward: float = DEFAULT_MIN_RISK_REWARD,
) -> dict[str, object]:
    """Rank available objectives and decide whether the trade is worthwhile."""
    normalized_direction = _normalize_direction(direction)
    entry = _number(entry_price)
    stop = _number(stop_loss)
    minimum_rr = max(0.1, float(min_risk_reward))

    if normalized_direction is None or entry is None or stop is None:
        return _pending_plan(minimum_rr, "Entry and invalidation must be known before objectives can be scored.")

    risk = abs(entry - stop)
    stop_is_valid = stop < entry if normalized_direction == "bullish" else stop > entry
    if risk <= 0 or not stop_is_valid:
        return _pending_plan(minimum_rr, "The proposed invalidation is not on the risk side of the entry.")

    raw_candidates: list[dict[str, object]] = []
    _add_swing_candidates(raw_candidates, normalized_direction, swings or {})
    _add_equal_level_candidates(raw_candidates, normalized_direction, equal_levels or {})
    _add_context_candidates(raw_candidates, normalized_direction, context_candles or {})
    _add_liquidity_candidates(raw_candidates, normalized_direction, liquidity_map or {})
    _add_zone_candidates(raw_candidates, normalized_direction, zones or {})
    _add_fvg_candidates(raw_candidates, normalized_direction, fvgs or [])
    _add_extra_candidates(raw_candidates, extra_candidates or [])
    raw_candidates = _annotate_target_status(raw_candidates, analysis_candles, normalized_direction)

    directional = [
        candidate
        for candidate in raw_candidates
        if _is_beyond_entry(normalized_direction, float(candidate["price"]), entry)
    ]
    unique = _deduplicate(directional, entry, risk)
    scored = [
        _score_candidate(candidate, normalized_direction, entry, risk, minimum_rr)
        for candidate in unique
    ]
    scored.sort(key=lambda candidate: (int(candidate["score"]), float(candidate["rr"])), reverse=True)

    accepted = [candidate for candidate in scored if candidate["accepted"]]
    primary = accepted[0] if accepted else None
    secondary = _secondary_objective(primary, accepted)
    best_available = primary or (scored[0] if scored else None)

    if primary is None:
        best_rr = max((float(candidate["rr"]) for candidate in scored), default=None)
        if scored and all(candidate.get("taken") for candidate in scored):
            reason = "All directional liquidity objectives have already been traded through."
        elif best_rr is None:
            reason = "No directional liquidity objective is available beyond the entry."
        else:
            reason = f"Best available objective offers only {best_rr:.2f}R; TradeScor requires at least {minimum_rr:.2f}R."
        return {
            "decision": "REJECT",
            "trade_accepted": False,
            "minimum_rr": round(minimum_rr, 2),
            "risk": round(risk, 6),
            "trade_quality": int(best_available["score"]) if best_available else 0,
            "primary_objective": None,
            "secondary_objective": None,
            "best_rejected_objective": best_available,
            "candidates": scored,
            "reason": reason,
            "summary": f"No trade. {reason}",
        }

    return {
        "decision": "ACCEPT",
        "trade_accepted": True,
        "minimum_rr": round(minimum_rr, 2),
        "risk": round(risk, 6),
        "trade_quality": int(primary["score"]),
        "primary_objective": primary,
        "secondary_objective": secondary,
        "best_rejected_objective": None,
        "candidates": scored,
        "reason": str(primary["reason"]),
        "summary": f"Trade accepted. {primary['name']} offers {float(primary['rr']):.2f}R and is the strongest available objective.",
    }


def levels_from_objective_plan(
    *,
    entry_zone: dict[str, float] | None,
    stop_loss: float | None,
    objective_plan: dict[str, object],
) -> dict[str, object]:
    """Convert an accepted objective plan into the existing trade-level shape."""
    if not objective_plan.get("trade_accepted"):
        return {
            "entry_zone": None,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "rr1": None,
            "rr2": None,
        }

    primary = objective_plan.get("primary_objective") or {}
    secondary = objective_plan.get("secondary_objective") or {}
    return {
        "entry_zone": entry_zone,
        "stop_loss": _rounded(stop_loss),
        "tp1": primary.get("price"),
        "tp2": secondary.get("price"),
        "rr1": primary.get("rr"),
        "rr2": secondary.get("rr"),
    }


def _pending_plan(minimum_rr: float, reason: str) -> dict[str, object]:
    return {
        "decision": "PENDING",
        "trade_accepted": False,
        "minimum_rr": round(minimum_rr, 2),
        "risk": None,
        "trade_quality": 0,
        "primary_objective": None,
        "secondary_objective": None,
        "best_rejected_objective": None,
        "candidates": [],
        "reason": reason,
        "summary": reason,
    }


def _add_swing_candidates(
    candidates: list[dict[str, object]],
    direction: str,
    swings: dict[str, list[dict[str, object]]],
) -> None:
    key = "highs" if direction == "bullish" else "lows"
    name = "Previous Swing High" if direction == "bullish" else "Previous Swing Low"
    reason = "Untaken swing liquidity in the direction of the setup."
    for swing in swings.get(key, [])[-8:]:
        _append_candidate(
            candidates,
            name,
            swing.get("price"),
            "swing",
            76,
            reason,
            formed_at=swing.get("confirmed_at") or swing.get("time"),
            formed_index=swing.get("confirmed_index", swing.get("index")),
            candidate_type="swing_high" if direction == "bullish" else "swing_low",
        )


def _add_equal_level_candidates(
    candidates: list[dict[str, object]],
    direction: str,
    equal_levels: dict[str, list[dict[str, object]]],
) -> None:
    key = "equal_highs" if direction == "bullish" else "equal_lows"
    name = "Equal Highs" if direction == "bullish" else "Equal Lows"
    reason = "Clustered stops create a clear external liquidity objective."
    for level in equal_levels.get(key, [])[-5:]:
        _append_candidate(
            candidates,
            name,
            level.get("price"),
            key,
            91,
            reason,
            formed_at=level.get("end_time") or level.get("time") or level.get("start_time"),
            formed_index=level.get("index"),
            candidate_type=key[:-1] if key.endswith("s") else key,
        )


def _add_context_candidates(
    candidates: list[dict[str, object]],
    direction: str,
    context: dict[str, pd.DataFrame],
) -> None:
    daily = context.get("D1")
    if daily is not None and len(daily) >= 2:
        clean_daily = daily.sort_values("time")
        previous = clean_daily.iloc[-2]
        if direction == "bullish":
            _append_candidate(candidates, "Previous Day High", previous.get("high"), "daily", 87, "Previous-day liquidity is a commonly watched institutional objective.", formed_at=previous.get("time"), candidate_type="previous_day_high")
        else:
            _append_candidate(candidates, "Previous Day Low", previous.get("low"), "daily", 87, "Previous-day liquidity is a commonly watched institutional objective.", formed_at=previous.get("time"), candidate_type="previous_day_low")

        previous_week = _previous_week_range(clean_daily)
        if previous_week:
            if direction == "bullish":
                _append_candidate(candidates, "Previous Week High", previous_week["high"], "weekly", 82, "Previous-week liquidity is a major higher-timeframe objective.", formed_at=previous_week.get("formed_at"), candidate_type="previous_week_high")
            else:
                _append_candidate(candidates, "Previous Week Low", previous_week["low"], "weekly", 82, "Previous-week liquidity is a major higher-timeframe objective.", formed_at=previous_week.get("formed_at"), candidate_type="previous_week_low")

    weekly = context.get("W1")
    if weekly is not None and len(weekly) >= 2:
        previous = weekly.sort_values("time").iloc[-2]
        if direction == "bullish":
            _append_candidate(candidates, "Previous Week High", previous.get("high"), "weekly", 82, "Previous-week liquidity is a major higher-timeframe objective.", formed_at=previous.get("time"), candidate_type="previous_week_high")
        else:
            _append_candidate(candidates, "Previous Week Low", previous.get("low"), "weekly", 82, "Previous-week liquidity is a major higher-timeframe objective.", formed_at=previous.get("time"), candidate_type="previous_week_low")


def _previous_week_range(daily: pd.DataFrame) -> dict[str, float] | None:
    clean = daily.copy()
    times = pd.to_datetime(clean["time"], errors="coerce", utc=True).dt.tz_localize(None)
    clean = clean.assign(_week=times.dt.to_period("W-SUN")).dropna(subset=["_week"])
    weeks = list(clean["_week"].drop_duplicates())
    if len(weeks) < 2:
        return None
    previous = clean[clean["_week"] == weeks[-2]]
    if previous.empty:
        return None
    return {
        "high": float(previous["high"].max()),
        "low": float(previous["low"].min()),
        "formed_at": previous.iloc[-1]["time"],
    }


def _add_liquidity_candidates(
    candidates: list[dict[str, object]],
    direction: str,
    liquidity_map: dict[str, object],
) -> None:
    key = "buy_side" if direction == "bullish" else "sell_side"
    for level in liquidity_map.get(key, []) or []:
        label = str(level.get("label", "Liquidity Pool"))
        source = str(level.get("source", "liquidity"))
        probability = {
            "equal_highs": 91,
            "equal_lows": 91,
            "daily": 87,
            "weekly": 82,
            "session": 74,
            "round_number": 54,
        }.get(source, 72)
        _append_candidate(candidates, label, level.get("price"), source, probability, "Untaken directional liquidity is available at this level.", formed_at=level.get("time") or level.get("start_time"), formed_index=level.get("index"), candidate_type=source)


def _add_zone_candidates(
    candidates: list[dict[str, object]],
    direction: str,
    zones: dict[str, object],
) -> None:
    key = "resistance" if direction == "bullish" else "support"
    name = "Resistance Objective" if direction == "bullish" else "Support Objective"
    for zone in zones.get(key, []) or []:
        price = zone.get("price")
        _append_candidate(candidates, name, price, key, 68, "The next opposing structure zone may attract price and cap the move.", formed_at=zone.get("confirmed_at") or zone.get("start_time"), formed_index=zone.get("confirmed_index", zone.get("start_index")), candidate_type=key)


def _add_fvg_candidates(
    candidates: list[dict[str, object]],
    direction: str,
    fvgs: Iterable[dict[str, object]],
) -> None:
    desired_type = "bearish" if direction == "bullish" else "bullish"
    price_key = "bottom_price" if direction == "bullish" else "top_price"
    name = "Opposing FVG"
    for zone in fvgs:
        if str(zone.get("type", "")).lower() == desired_type:
            _append_candidate(candidates, name, zone.get(price_key), "fvg", 63, "An opposing imbalance is a possible delivery objective, but ranks below visible liquidity.", formed_at=zone.get("start_time"), formed_index=zone.get("start_index"), candidate_type="opposing_fvg")


def _add_extra_candidates(
    candidates: list[dict[str, object]],
    extra_candidates: list[dict[str, object]],
) -> None:
    for candidate in extra_candidates:
        _append_candidate(
            candidates,
            str(candidate.get("name", "Strategy Objective")),
            candidate.get("price"),
            str(candidate.get("source", "strategy")),
            int(candidate.get("probability", 70) or 70),
            str(candidate.get("reason", "Strategy-aligned objective.")),
            formed_at=candidate.get("formed_at"),
            formed_index=candidate.get("formed_index"),
            candidate_type=str(candidate.get("type", candidate.get("source", "strategy"))),
        )


def _append_candidate(
    candidates: list[dict[str, object]],
    name: str,
    price: object,
    source: str,
    probability: int,
    reason: str,
    *,
    formed_at: object = None,
    formed_index: object = None,
    candidate_type: str | None = None,
) -> None:
    clean_price = _number(price)
    if clean_price is None:
        return
    candidates.append(
        {
            "name": name,
            "level": round(clean_price, 6),
            "price": round(clean_price, 6),
            "type": candidate_type or source,
            "source": source,
            "probability": max(0, min(100, int(probability))),
            "reason": reason,
            "formed_at": _timestamp_text(formed_at),
            "formed_index": int(formed_index) if formed_index is not None else None,
            "taken": False,
            "taken_at": None,
        }
    )


def _annotate_target_status(
    candidates: list[dict[str, object]],
    candles: pd.DataFrame | None,
    direction: str,
) -> list[dict[str, object]]:
    if candles is None or candles.empty:
        return [{**candidate, "quality": _quality(int(candidate["probability"]))} for candidate in candidates]

    clean = candles.copy()
    clean["time"] = pd.to_datetime(clean["time"], errors="coerce", utc=True)
    clean = clean.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    annotated = []
    for candidate in candidates:
        formed_index = candidate.get("formed_index")
        formed_at = candidate.get("formed_at")
        if formed_index is not None and 0 <= int(formed_index) < len(clean):
            later = clean.iloc[int(formed_index) + 1 :]
        elif formed_at:
            timestamp = pd.to_datetime(formed_at, errors="coerce", utc=True)
            later = clean[clean["time"] > timestamp] if pd.notna(timestamp) else clean.iloc[0:0]
        else:
            later = clean.iloc[0:0]

        level = float(candidate["price"])
        if direction == "bullish":
            hits = later[later["high"].astype(float) >= level]
        else:
            hits = later[later["low"].astype(float) <= level]
        taken = not hits.empty
        taken_at = hits.iloc[0]["time"].isoformat() if taken else None
        reason = str(candidate["reason"])
        if taken:
            reason = f"{candidate['name']} was already traded through at {taken_at}."
        annotated.append(
            {
                **candidate,
                "taken": taken,
                "taken_at": taken_at,
                "quality": _quality(int(candidate["probability"])),
                "reason": reason,
            }
        )
    return annotated


def _quality(probability: int) -> str:
    if probability >= 85:
        return "high"
    if probability >= 68:
        return "medium"
    return "low"


def _timestamp_text(value: object) -> str | None:
    if value is None or value == "":
        return None
    timestamp = (
        pd.to_datetime(value, unit="s", errors="coerce", utc=True)
        if isinstance(value, (int, float))
        else pd.to_datetime(value, errors="coerce", utc=True)
    )
    return timestamp.isoformat() if pd.notna(timestamp) else None


def _deduplicate(
    candidates: list[dict[str, object]],
    entry: float,
    risk: float,
) -> list[dict[str, object]]:
    tolerance = max(abs(entry) * 0.000001, risk * 0.03)
    unique: list[dict[str, object]] = []
    for candidate in sorted(candidates, key=lambda item: int(item["probability"]), reverse=True):
        price = float(candidate["price"])
        if any(abs(price - float(existing["price"])) <= tolerance for existing in unique):
            continue
        unique.append(candidate)
    return unique


def _score_candidate(
    candidate: dict[str, object],
    direction: str,
    entry: float,
    risk: float,
    minimum_rr: float,
) -> dict[str, object]:
    price = float(candidate["price"])
    reward = price - entry if direction == "bullish" else entry - price
    rr = reward / risk
    probability = int(candidate["probability"])
    reward_score = min(100.0, (rr / 3.0) * 100.0)
    score = round((probability * 0.7) + (reward_score * 0.3))
    accepted = rr >= minimum_rr and not bool(candidate.get("taken"))
    if not accepted:
        score = min(score, 49)

    return {
        **candidate,
        "rr": round(rr, 2),
        "score": max(0, min(100, int(score))),
        "accepted": accepted,
        "status": "Accept" if accepted else "Reject",
        "rejection_reason": None if accepted else (
            "Target was already traded through."
            if candidate.get("taken")
            else f"Reward is below the {minimum_rr:.2f}R minimum."
        ),
    }


def _secondary_objective(
    primary: dict[str, object] | None,
    accepted: list[dict[str, object]],
) -> dict[str, object] | None:
    if primary is None:
        return None
    farther = [candidate for candidate in accepted[1:] if float(candidate["rr"]) > float(primary["rr"]) + 0.2]
    if not farther:
        return None
    farther.sort(key=lambda candidate: (int(candidate["score"]), float(candidate["rr"])), reverse=True)
    return farther[0]


def _normalize_direction(direction: str | None) -> str | None:
    value = str(direction or "").strip().lower()
    if value in {"bullish", "long"}:
        return "bullish"
    if value in {"bearish", "short"}:
        return "bearish"
    return None


def _is_beyond_entry(direction: str, price: float, entry: float) -> bool:
    return price > entry if direction == "bullish" else price < entry


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(result):
        return None
    return result


def _rounded(value: object) -> float | None:
    number = _number(value)
    return round(number, 6) if number is not None else None
