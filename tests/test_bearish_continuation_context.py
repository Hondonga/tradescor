from pathlib import Path

from analysis.decision_views import build_market_analysis, build_trade_plan


def test_bearish_compression_is_presented_as_continuation_pullback():
    setup={"direction":"sell","stage":"WAITING_FOR_DISPLACEMENT","trade_ready":False,"entry":None,"targets":[]}
    view=build_market_analysis(
        market={"external_structure":"bearish","internal_structure":"compression","alignment":"pullback"},
        setup=setup,
        scenario="H1 bearish / M15 compression",
    )
    assert view["continuation_context"]=="bearish_pullback"
    assert view["external_structure_display"]=="Bearish directional leg or bearish-to-compression transition"
    assert view["internal_structure_display"]=="Retracement / local consolidation"
    assert view["developing_scenario"]=="Potential bearish continuation pullback"
    assert view["price_location"].startswith("Price has retraced")
    assert view["next_confirmation"].startswith("Completed bearish M5 displacement")


def test_bearish_context_remains_non_actionable_without_geometry():
    setup={"direction":"sell","trade_ready":False,"entry":None,"targets":[]}
    plan=build_trade_plan(setup,"DEVELOPING","target")
    assert plan["available"] is False
    assert plan["entry"] is None and plan["targets"]==[]
    assert plan["reason"]=="No confirmed entry location and opposing structural target currently produce valid geometry"


def test_bearish_context_has_a_dedicated_decision_rail():
    source=(Path(__file__).parents[1]/"frontend/src/components/terminal/decision-rail.tsx").read_text()
    assert 'continuation_context === "bearish_pullback"' in source
    assert "Confirmation required" in source
