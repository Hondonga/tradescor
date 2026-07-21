"""Static contracts for the rebuilt TradeScor frontend."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")

def test_single_shell_and_pages():
    for token in ('class="app-shell"', 'class="app-sidebar"', 'class="terminal-toolbar"', 'class="page-content"', 'id="home-page"', 'id="scanner-page"', 'id="chart-page"', 'id="lab-page"', 'id="settings-page"'):
        assert token in HTML

def test_compact_unique_toolbar_controls():
    for id_ in ("symbol", "timeframe", "strategy", "analyze-button"):
        assert HTML.count(f'id="{id_}"') == 1
    assert "#symbol { width: 150px; }" in CSS
    assert "#timeframe { width: 100px; }" in CSS
    assert "#strategy { width: 210px; }" in CSS
    assert "#analyze-button { width: 120px; }" in CSS

def test_canonical_status_mapping_and_neutral_default():
    for status in ("BUY CONFIRMED", "SELL CONFIRMED", "BUY SETUP FORMING", "SELL SETUP FORMING", "NO VALID SETUP"):
        assert status in JS or status in HTML
    assert 'return "Neutral"' in JS

def test_central_render_functions_exist():
    for name in ("showPage", "renderToolbar", "renderChartPage", "renderDecisionPanel", "renderScannerPage", "renderHomePage", "renderLabPage", "formatUserStatus", "formatDirection", "renderMarketFilters"):
        assert f"function {name}" in JS

def test_home_and_scanner_contracts():
    assert 'id="home-symbol"' in HTML and 'id="home-timeframe"' in HTML
    assert 'id="home-strategy"' not in HTML
    for id_ in ("scanner-status", "scanner-direction", "scanner-score", "scanner-confidence", "scanner-next", "scanner-plan", "scanner-why", "scanner-filters"):
        assert f'id="{id_}"' in HTML

def test_lab_and_settings_contracts():
    assert "Compare historical strategy performance." in HTML
    assert "No winner — insufficient data" in JS
    assert "Early leader — weak sample" in JS
    assert "Best performer — usable sample" in JS
    assert 'id="setting-marketaux"' in HTML and 'id="setting-dxy"' in HTML

def test_no_legacy_ui_structures():
    for token in ("terminal-top-bar", "assistant-panel", "button-option-group", "Manual Fetch", "API Protected"):
        assert token not in HTML
