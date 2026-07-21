from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text()
JS = (ROOT / "static" / "app.js").read_text()


def test_compact_top_down_strip_has_fixed_hierarchy():
    assert 'id="top-down-strip"' in HTML
    assert '["D1", "H4", "H1", "M15", "M5"]' in JS
    assert 'id="execution-summary"' in HTML


def test_frontend_uses_backend_top_down_and_execution_objects():
    assert "analysis.top_down_analysis" in JS
    assert "analysis.execution_plan" in JS
    assert "execution.direction" in JS
    assert "execution.entry_timing" in JS


def test_view_m5_entry_uses_cached_context_without_fetch():
    function = JS.split("function viewCachedM5Entry", 1)[1].split("function", 1)[0]
    assert "latest.execution_candles" in function
    assert 'ui.timeframe.value = "M5"' in function
    assert "renderChartPage(latest)" in function
    assert "fetch(" not in function


def test_view_m5_button_only_appears_for_actionable_cached_plan():
    assert 'id="view-m5-entry"' in HTML
    assert 'execution.state !== "entry_valid"' in JS
    assert "!analysis.execution_candles?.length" in JS


def test_crypto_header_uses_asset_aware_backend_market_status():
    assert "market.market_status_label" in JS
    assert 'market.market_status === "OPEN_24_7"' in JS
    assert 'crypto ? "Liquidity Window" : "Session"' in JS

