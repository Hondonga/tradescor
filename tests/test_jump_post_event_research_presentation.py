from pathlib import Path

from analysis.decision_views import build_market_analysis, build_trade_plan
from analysis.smc.smc_product_contract import build_smc_product_contract


def _result():
    return {
        "ownership": {
            "selected_strategy_id": "jump_post_event_smc",
            "decision_owner_id": "jump_smc_adapter",
            "overlay_owner_id": "jump_smc_adapter",
            "adapter_id": "jump_smc_adapter",
        },
        "setup": {
            "setup_type": "jump_post_event_smc",
            "jump_mode": "JUMP_POST_EVENT_SMC",
            "state": "WAITING_FOR_DISPLACEMENT",
            "research_only": True,
            "recent_event": {
                "status": "Completed Jump event detected",
                "future_direction": None,
            },
            "confirmation_levels": {
                "bullish": "Close above latest M5 internal swing high",
                "bearish": "Close below latest M5 internal swing low",
            },
            "setup_blocker": "No completed M5 displacement has formed from fresh post-event structure.",
            "plan_blocker": "No valid opposing structural target currently provides acceptable geometry.",
            "next_required_condition": "Wait for completed displacement. Do not enter solely because price reacted.",
            "entry": None,
            "stop": None,
            "targets": [],
        },
        "structure": {
            "external_structure": "compression",
            "internal_structure": "compression",
        },
        "scoring": {"quality_score": 37.5, "quality_grade": "D", "valid": False},
        "event": {"qualified": True},
        "trade_chart": {"current_price": 100.0},
    }


def test_jump_post_event_contract_is_developing_research_only(monkeypatch):
    monkeypatch.setattr(
        "analysis.smc.smc_product_contract.evaluate_data_readiness",
        lambda *_args, **_kwargs: {"state": "ready"},
    )
    contract = build_smc_product_contract(
        symbol="JD75",
        display_symbol="Jump 75 Index",
        timeframe="M5",
        analysis_time="2026-07-19T12:00:00Z",
        family={"family": "JUMP", "variant": "75"},
        candles_by_timeframe={},
        result=_result(),
    )
    assert contract["decision"]["status"] == "DEVELOPING"
    assert contract["decision"]["stage"] == "WAITING_FOR_DISPLACEMENT"
    assert contract["decision"]["trade_ready"] is False
    assert contract["setup"]["research_only"] is True
    assert contract["setup"]["setup_quality_score"] == 37.5
    assert contract["setup"]["entry"] is None


def test_jump_views_keep_setup_and_plan_blockers_separate():
    setup = _result()["setup"]
    market = {"external_structure": "compression", "internal_structure": "compression"}
    view = build_market_analysis(market=market, setup=setup)
    plan = build_trade_plan(setup, "DEVELOPING", setup["setup_blocker"])
    assert view["price_location"] == "Near lower compression area"
    assert view["recent_event"]["future_direction"] is None
    assert view["setup_blocker"].startswith("No completed M5 displacement")
    assert plan["available"] is False
    assert plan["reason"].startswith("No valid opposing structural target")


def test_jump_research_rail_contains_non_predictive_confirmation_copy():
    source = (Path(__file__).parents[1] / "frontend/src/components/terminal/decision-rail.tsx").read_text()
    assert 'decision.setup.jump_mode === "JUMP_POST_EVENT_SMC"' in source
    assert "Future jump direction" in source
    assert "Confirmation levels" in source
    assert "Plan blocker" in source
