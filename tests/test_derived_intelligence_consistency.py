from analysis.derived_intelligence_normalizer import normalize_derived_intelligence
def test_normalized_intelligence_contains_no_trade_prices_and_ui_reads_contract():
    intelligence=normalize_derived_intelligence(family={"provider_symbol":"R_100","display_name":"Volatility 100 Index","family":"VOLATILITY","subfamily":"VOLATILITY_100"},profile={"profile_quality":"good"},volatility={"regime":"HIGH"},spike={"spike_detected":False},regime={"regime":"TREND_BEARISH","direction":"bearish"},top_down={"alignment":"bearish"},market_context={"bias":"bearish"},data_quality={"status":"good"})
    text=str(intelligence).lower();assert all(f"'{key}':" not in text for key in ("entry","stop","targets","tp1","tp2"))
    js=open("static/app.js",encoding="utf-8").read();assert "renderDerivedIntelligence(payload.intelligence)" in js and "intelligence.regime" in js
