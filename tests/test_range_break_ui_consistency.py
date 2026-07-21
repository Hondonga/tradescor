def test_range_break_chart_and_panel_are_backend_projections():
    engine=open("analysis/derived_engine.py",encoding="utf-8").read();js=open("static/app.js",encoding="utf-8").read();assert '"trade_chart":build_derived_trade_chart(adapter,current)' in engine and "analysis.decision?.trade_chart" in js and "presentation?.active_trade_plan" in js
