from __future__ import annotations

from analysis.trade_score import build_trade_score


def test_rejected_poor_reward_caps_visible_trade_score():
    result = build_trade_score(
        setup_quality=86,
        trade_quality=72,
        trade_decision="REJECT",
        levels_mode="hidden",
        objective_plan={
            "reason": "Best available objective offers only 0.64R; TradeScor requires at least 1.50R.",
        },
        trade_metrics={},
    )

    assert result["score"] <= 55
    assert result["confidence"] == "Medium"
    assert result["cap_reason"] == "No acceptable target is available."


def test_weak_tp1_caps_visible_trade_score_below_high_confidence():
    result = build_trade_score(
        setup_quality=86,
        trade_quality=80,
        trade_decision="PENDING",
        levels_mode="projected",
        objective_plan={},
        trade_metrics={
            "tp1": {"risk_reward": 0.64},
            "tp2": {"risk_reward": 2.1},
            "warnings": ["TP1 has weak reward. TP2 is the first acceptable target."],
        },
    )

    assert result["score"] <= 64
    assert result["confidence"] == "Medium"
    assert result["cap_reason"] == "Reward is too small compared to risk."


def test_accepted_trade_blends_setup_and_trade_quality():
    result = build_trade_score(
        setup_quality=86,
        trade_quality=70,
        trade_decision="ACCEPT",
        levels_mode="final",
        objective_plan={},
        trade_metrics={"tp1": {"risk_reward": 1.5}},
        setup_stage="SETUP CONFIRMED",
    )

    assert result["score"] == 80
    assert result["confidence"] == "High"
    assert result["cap_reason"] == ""


def test_watching_area_cannot_score_100_or_show_high_confidence():
    result = build_trade_score(
        setup_quality=100,
        trade_quality=100,
        trade_decision="PENDING",
        levels_mode="projected",
        setup_stage="WATCHING AREA",
    )

    assert result["score"] == 60
    assert result["confidence"] == "Medium"


def test_unconfirmed_setup_cannot_have_high_confidence():
    result = build_trade_score(
        setup_quality=100,
        trade_quality=100,
        trade_decision="PENDING",
        levels_mode="projected",
        setup_stage="CONFIRMATION FORMING",
    )

    assert result["score"] == 80
    assert result["confidence"] == "Medium"


def test_confirmed_setup_with_poor_remaining_rr_is_rejected():
    result = build_trade_score(
        setup_quality=100,
        trade_quality=100,
        trade_decision="ACCEPT",
        levels_mode="final",
        setup_stage="SETUP CONFIRMED",
        trade_metrics={"tp1": {"risk_reward": 0.75}},
    )

    assert result["score"] <= 64
    assert result["confidence"] == "Medium"
    assert "too late" in result["cap_reason"].lower()


def test_invalid_entry_timing_caps_high_setup_score():
    result = build_trade_score(
        setup_quality=85,
        trade_quality=90,
        trade_decision="REJECT",
        levels_mode="hidden",
        objective_plan={"reason": "The technical setup is no longer active."},
        trade_metrics={},
        entry_timing={
            "available": True,
            "entry_timing_status": "invalid",
        },
    )

    assert result["score"] == 25
    assert result["confidence"] == "Waiting"
    assert result["cap_reason"] == "Entry timing invalidated the setup."


def test_too_late_entry_timing_caps_score_below_medium_watchlist():
    result = build_trade_score(
        setup_quality=85,
        trade_quality=90,
        trade_decision="PENDING",
        levels_mode="projected",
        objective_plan={},
        trade_metrics={},
        entry_timing={
            "available": True,
            "entry_timing_status": "too_late",
        },
    )

    assert result["score"] == 45
    assert result["confidence"] == "Low"
    assert result["cap_reason"] == "Price is too far from the entry area."


def test_failed_strategy_state_caps_visible_trade_score():
    result = build_trade_score(
        setup_quality=85,
        trade_quality=90,
        trade_decision="PENDING",
        levels_mode="hidden",
        state="FAILED_BREAKOUT",
        objective_plan={},
        trade_metrics={},
        entry_timing={"available": True, "entry_timing_status": "near_entry"},
    )

    assert result["score"] == 25
    assert result["confidence"] == "Waiting"
    assert result["cap_reason"] == "The setup state is not tradeable."
