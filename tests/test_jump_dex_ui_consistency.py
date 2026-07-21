from pathlib import Path
from analysis.derived_strategy_decision import build_derived_trade_chart
def test_event_only_never_projects_trade_levels():
    strategy={"decision":{"setup_id":None,"developing_direction":"","trade_ready":False,"next_action":"Do not chase."},"active_trade_plan":None};chart=build_derived_trade_chart(strategy,100)
    assert chart["confirmed_entry"] is None and chart["stop"] is None and chart["targets"]==[]
def test_manual_option_is_available():assert 'value="jump_dex_post_event"' in (Path(__file__).parents[1]/"templates/index.html").read_text()
