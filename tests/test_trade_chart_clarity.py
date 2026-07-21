from pathlib import Path

from analysis.asset_rules import asset_rules
from analysis.trade_chart import build_trade_chart


def _decision(direction="sell", state="waiting_for_area", ready=False):
    return {"setup":{"setup_id":"setup-1","direction":direction,"stage":state,"zone":{"low":1.40450,"high":1.40493,"origin_time":"2026-01-01T00:00:00+00:00"},"confirmation":{"price":None,"confirmed":False},"invalidation":{"price":1.40520 if direction=="sell" else 1.40420}},"execution":{"state":state,"entry":None,"stop":None,"targets":[],"risk_reward":None},"quality":{"trade_plan_valid":ready}}


def test_expected_entry_and_forex_distance_are_backend_values():
    chart=build_trade_chart(_decision(),current_price=1.40254,asset_rules=asset_rules("USD/CAD","forex"))
    assert chart["idea"]=="sell" and chart["expected_entry"]["low"]==1.40450 and chart["expected_entry"]["high"]==1.40493
    assert chart["distance_to_entry"]==19.6 and chart["distance_unit"]=="pips"
    assert "19.6 pips below" in chart["message"]


def test_preferred_entry_is_optional_and_trigger_is_null_before_structure():
    chart=build_trade_chart(_decision(),current_price=1.40254,asset_rules=asset_rules("USD/CAD","forex"))
    assert chart["expected_entry"]["preferred"] is None
    assert chart["confirmation"]["price"] is None


def test_projected_invalidation_is_not_an_active_stop():
    chart=build_trade_chart(_decision(),current_price=1.40254,asset_rules=asset_rules("USD/CAD","forex"))
    assert chart["invalidation"]["price"]==1.40520 and chart["stop"] is None


def test_confirmed_plan_exposes_entry_stop_targets_and_rr():
    decision=_decision(state="entry_available",ready=True); decision["setup"]["confirmation"]={"price":1.40392,"confirmed":True}; decision["execution"].update({"entry":1.40461,"stop":1.40518,"risk_reward":1.6,"targets":[{"name":"TP1","price":1.40220,"risk_reward":1.6,"swept":False},{"name":"TP2","price":1.40080,"risk_reward":2.5,"swept":False}]})
    chart=build_trade_chart(decision,current_price=1.40461,asset_rules=asset_rules("USD/CAD","forex"))
    assert chart["state"]=="entry_available" and chart["confirmed_entry"]==1.40461 and chart["stop"]==1.40518
    assert [row["price"] for row in chart["targets"]]==[1.40220,1.40080]


def test_too_late_removes_active_trade_levels():
    decision=_decision(state="too_late",ready=True); decision["execution"].update({"entry":1.403,"stop":1.4052,"targets":[{"price":1.4}],"risk_reward":.8})
    chart=build_trade_chart(decision,current_price=1.400,asset_rules=asset_rules("USD/CAD","forex"))
    assert chart["state"]=="too_late" and chart["confirmed_entry"] is None and chart["stop"] is None and chart["targets"]==[]


def test_no_setup_hides_every_trade_overlay_value():
    chart=build_trade_chart({"setup":{},"execution":{},"quality":{}},current_price=100,asset_rules=asset_rules("BTC/USD","crypto"))
    assert chart["idea"]=="none" and chart["expected_entry"]["low"] is None and chart["stop"] is None and chart["targets"]==[]


def test_crypto_and_index_use_points_with_crypto_percentage():
    crypto=build_trade_chart({**_decision(),"setup":{**_decision()["setup"],"zone":{"low":110,"high":112,"origin_time":None},"invalidation":{"price":114}}},current_price=100,asset_rules=asset_rules("BTC/USD","crypto"))
    index=build_trade_chart({**_decision(),"setup":{**_decision()["setup"],"zone":{"low":20100,"high":20120,"origin_time":None},"invalidation":{"price":20140}}},current_price=20000,asset_rules=asset_rules("NASDAQ100","index"))
    assert crypto["distance_unit"]=="points" and crypto["distance_percent"]==10.0
    assert index["distance_unit"]=="points" and index["distance_to_entry"]==100


def test_chart_renderer_consumes_trade_chart_and_defaults_context_on():
    root=Path(__file__).resolve().parents[1]; html=(root/"templates"/"index.html").read_text(); js=(root/"static"/"app.js").read_text()
    assert "Trade Plan" in html and "Context" in html and 'id="show-fvg" type="checkbox"' in html
    assert 'id="show-fvg" type="checkbox" checked' in html
    draw=js.split("function drawChartOverlays",1)[1].split("function resolveOverlayLabelCollisions",1)[0]
    assert "analysis.decision?.trade_chart" in draw
    assert "normalizePossibleSetups" not in draw and "drawPossibleSetups" not in draw
    assert "fetch(" not in draw


def test_trade_plan_renders_entry_bounds_and_backend_trigger_only():
    js=(Path(__file__).resolve().parents[1]/"static"/"app.js").read_text()
    trade=js.split("function drawTradePlan",1)[1].split("function drawTradeChartGuide",1)[0]
    assert "Entry High ·" in trade and "Entry Low ·" in trade
    assert "M5 Confirm" in trade and "tradeChartPrice(plan.confirmation?.price)" in trade
    assert "M5 trigger appears after price reaches this zone." in trade


def test_invalidation_stop_and_targets_use_stage_appropriate_labels():
    js=(Path(__file__).resolve().parents[1]/"static"/"app.js").read_text()
    trade=js.split("function drawTradePlan",1)[1].split("function drawTradeChartGuide",1)[0]
    active=trade.split("if (active)",1)[1].split("} else",1)[0]
    projected=trade.split("} else",1)[1]
    assert "STOP LOSS ·" in active and "TP${index + 1}" in active
    assert "Idea Invalid" in projected and "Potential ${target.name" in projected


def test_missing_trade_chart_prices_cannot_become_zero_lines():
    js=(Path(__file__).resolve().parents[1]/"static"/"app.js").read_text()
    helper=js.split("function tradeChartPrice",1)[1].split("function resolveOverlayLabelCollisions",1)[0]
    assert 'value === null || value === undefined || value === ""' in helper
    assert "number > 0" in helper


def test_trade_plan_is_independent_from_context_toggle():
    js=(Path(__file__).resolve().parents[1]/"static"/"app.js").read_text()
    draw=js.split("function drawChartOverlays",1)[1].split("function drawTradePlan",1)[0]
    assert "if (ui.zones.checked) drawTradePlan" in draw
    assert "if (ui.fvg.checked)" in draw
