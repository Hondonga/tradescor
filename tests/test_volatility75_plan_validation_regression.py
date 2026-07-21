"""Regression fixture for the reported Volatility 75 M5 PLAN VALIDATION state:
sell setup, entry/stop resolved, TARGET_SCOPE_MISMATCH blocking the plan, an
oversized M15 pullback area, a duplicated DEVELOPING prefix, an unlabeled
invalidation/confirmation pair, and a "Decision-time Current" label shown in
Live mode.
"""
import pandas as pd

from analysis.global_overlay_contract import normalize_global_decision
from analysis.volatility_structure_pullback_engine import _pullback_location, DEFAULTS
from analysis.blocker_translations import translate_blocker, translate_next_requirement


SETUP_ID = "vsp-setup-regression"


def _reported_state_product(*, overlay_mode="LIVE"):
    current_price = 51181.9235
    invalidation_price = 51618.4373
    confirmation_price = 50675.0
    return {
        "decision_id": "d-regression",
        "meta": {
            "symbol": "R_75", "display_symbol": "Volatility 75 Index", "timeframe": "M5",
            "analysis_time": "2026-07-20T12:00:00Z", "market_source": "deriv",
            "market_type": "derived", "live": True,
        },
        "ownership": {
            "selected_model_id": "volatility_structure_pullback",
            "decision_owner_id": "volatility_structure_pullback",
            "overlay_owner_id": "volatility_structure_pullback",
        },
        "readiness": {"state": "ready"},
        "market": {"external_structure": "bearish", "internal_structure": "pullback", "current_price": current_price},
        "decision": {
            "status": "PLAN VALIDATION", "stage": "PLAN_VALIDATION", "direction": "sell",
            "trade_ready": False, "next_action": translate_next_requirement("TARGET_SCOPE_MISMATCH", direction="bearish"),
            "first_blocking_gate": translate_blocker("plan_geometry"),
        },
        "setup": {
            "setup_id": SETUP_ID, "setup_type": "structure_pullback", "direction": "sell",
            "stage": "PLAN_VALIDATION", "status": "PLAN_VALIDATION", "trade_ready": False,
            "entry": None, "stop": None, "targets": [], "rr": None,
            "entry_area": {"low": 51100.0, "high": 51150.0, "type": "m5_displacement_retrace"},
            "completed_confirmation": {"confirmed": True},
            "production_supported": True, "family_compatible": True, "chase_valid": True,
            "next_required_condition": translate_next_requirement("TARGET_SCOPE_MISMATCH", direction="bearish"),
        },
        "overlays": [
            {"owner_id": "volatility_structure_pullback", "setup_id": None, "visibility_category": "market_structure",
             "type": "h1_context", "state": "active", "price": 52200.0, "name": "H1 Bearish Context", "created_at": "t"},
            # The exact reported bug: an M15 pullback area spanning ~50303-53000,
            # far wider than any reasonable ATR-relative bound.
            {"owner_id": "volatility_structure_pullback", "setup_id": SETUP_ID, "visibility_category": "context_levels",
             "type": "m15_pullback_area", "state": "active", "low": 50303.0, "high": 53000.0,
             "name": "M15 Pullback Area", "created_at": "t"},
            {"owner_id": "volatility_structure_pullback", "setup_id": SETUP_ID, "visibility_category": None,
             "type": "confirmation", "state": "active", "price": confirmation_price,
             "name": "M5 Structure Break", "created_at": "t"},
            {"owner_id": "volatility_structure_pullback", "setup_id": SETUP_ID, "visibility_category": None,
             "type": "stop", "state": "conditional", "price": invalidation_price,
             "name": "Invalidation", "created_at": "t"},
        ],
        "previous_setup": None,
        "overlay_mode": overlay_mode,
    }


def test_reported_plan_validation_state_is_fully_repaired():
    value = normalize_global_decision(_reported_state_product(), mode="LIVE")

    # lifecycle remains PLAN VALIDATION, sell direction remains
    assert value["decision"]["status"] == "PLAN VALIDATION"
    assert value["decision"]["direction"] == "sell"

    # no actionable overlays, no TP1/TP2, trade plan unavailable
    assert not [row for row in value["overlays"] if row["actionable"]]
    assert not value["trade_plan"]["available"]
    assert value["trade_plan"]["entry"] is None and value["trade_plan"]["stop"] is None

    labels = [row["label"] for row in value["overlays"]]

    # the oversized zone is never duplicated or fabricated at the boundary;
    # whether it should be drawn at all is the engine-level ATR gate covered
    # by test_wide_m15_pullback_zone_is_rejected_at_the_engine_source below.
    assert len([row for row in value["overlays"] if row["type"] == "m15_pullback_area"]) <= 1

    # no duplicated DEVELOPING prefix anywhere
    assert not any(label.count("DEVELOPING") > 1 for label in labels)

    # invalidation has a semantic label, not a bare "MONITORING LEVEL"
    invalidation_rows = [row for row in value["overlays"] if row.get("price") == 51618.4373]
    assert invalidation_rows and all(row["label"] == "IDEA INVALIDATION" for row in invalidation_rows)

    # the confirmation level at ~50675 has a meaningful role label, not a bare "MONITORING LEVEL"
    confirmation_rows = [row for row in value["overlays"] if row.get("price") == 50675.0]
    assert confirmation_rows and all(row["label"] == "CONFIRMATION LEVEL" for row in confirmation_rows)

    # Live mode labels current price as "Current"
    current_rows = [row for row in value["overlays"] if row["type"] == "current_price"]
    assert current_rows and current_rows[0]["label"] == "Current"

    # target mismatch has a human-readable explanation, raw codes stay diagnostic-only
    assert value["decision"]["first_blocking_gate"] == "The setup exists, but the complete entry, stop and target geometry has not passed validation."
    assert "plan_geometry" not in value["decision"]["first_blocking_gate"]
    assert value["decision"]["next_action"] == "Wait for a fresh unswept structural objective below the proposed sell entry."
    assert "TARGET_SCOPE_MISMATCH" not in value["decision"]["next_action"]


def test_reported_plan_validation_state_survives_double_normalization():
    # The known trigger for the duplicate-prefix bug: some derived paths run
    # normalize_global_decision twice on the same already-normalized product.
    once = normalize_global_decision(_reported_state_product(), mode="LIVE")
    twice = normalize_global_decision(once, mode="LIVE")
    labels = [row["label"] for row in twice["overlays"]]
    assert not any(label.count("DEVELOPING") > 1 for label in labels)
    assert once["overlays"] == twice["overlays"] or all(
        row["label"] == other["label"]
        for row, other in zip(sorted(once["overlays"], key=lambda r: r["overlay_id"]), sorted(twice["overlays"], key=lambda r: r["overlay_id"]))
    )


def test_historical_and_replay_modes_use_their_own_current_price_label():
    historical = normalize_global_decision(_reported_state_product(), mode="HISTORICAL_INSPECTION")
    replay = normalize_global_decision(_reported_state_product(), mode="REPLAY")
    assert [row["label"] for row in historical["overlays"] if row["type"] == "current_price"] == ["Decision-time Current"]
    assert [row["label"] for row in replay["overlays"] if row["type"] == "current_price"] == ["Replay Current"]


def test_wide_m15_pullback_zone_is_rejected_at_the_engine_source():
    # Same geometry as the reported bug (~50303-53000), reproduced through
    # the real ATR-relative width gate rather than injected directly.
    times = pd.date_range("2026-07-19", periods=40, freq="15min", tz="UTC")
    base = 51181.9235
    rows = []
    for i, t in enumerate(times):
        high, low = base + 80, base - 80
        if i == 10:
            high = 53000.0
        if i == 9:
            low = 50303.0
        rows.append({"time": t, "open": base, "high": high, "low": low, "close": base, "complete": True})
    frame = pd.DataFrame(rows)
    result = _pullback_location(frame, "bearish", {}, DEFAULTS)
    assert result["valid_location"] is True  # setup progression is untouched
    assert result["zone_valid"] is False  # but the drawn zone is rejected
    assert result["zone_width_atr"] > DEFAULTS["pullback_zone_max_width_atr"]
