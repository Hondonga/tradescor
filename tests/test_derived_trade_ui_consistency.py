def test_frontend_does_not_invent_derived_trade_prices():
    js=open("static/app.js",encoding="utf-8").read();assert "presentation.active_trade_plan" in js or "active_trade_plan" in js
    assert "No confirmed plan yet" in js
