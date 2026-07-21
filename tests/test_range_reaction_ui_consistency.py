from pathlib import Path
from analysis.derived_strategy_decision import build_derived_trade_chart

def test_trade_chart_never_invents_unconfirmed_levels():
    strategy={"decision":{"setup_id":"drr-1","developing_direction":"buy","trade_ready":False,"next_action":"Wait."},"m15_setup_zone":{"low":100,"high":101,"type":"range_demand","valid":True},"m5_execution_zone":None,"confirmation":None,"active_trade_plan":None}
    chart=build_derived_trade_chart(strategy,100.5)
    assert chart["m15_setup_zone"]["low"]==100
    assert chart["confirmed_entry"] is None and chart["stop"] is None and chart["targets"]==[]

def test_manual_strategy_is_exposed_and_frontend_does_not_calculate_levels():
    root=Path(__file__).parents[1]
    assert 'value="derived_range_reaction"' in (root/"templates/index.html").read_text()
    assert "derived_range_reaction" in (root/"strategies/__init__.py").read_text()
