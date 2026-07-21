"""Chart-overlay contracts for the rebuilt terminal."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")

def test_one_chart_and_floating_toolbar():
    assert HTML.count('id="chart"') == 1
    for id_ in ("show-zones", "show-fvg", "show-labels"):
        assert HTML.count(f'id="{id_}"') == 1
    assert ".chart-overlay-toolbar { position: absolute" in CSS

def test_overlay_defaults():
    assert 'id="show-zones" type="checkbox" checked' in HTML
    assert 'id="show-fvg" type="checkbox"' in HTML
    assert 'id="show-fvg" type="checkbox" checked' in HTML
    assert 'id="show-labels" type="checkbox"><span>Labels' in HTML

def test_invalid_forming_and_valid_modes_are_distinct():
    assert 'const mode = hasValidPlan(analysis) ? "valid"' in JS
    assert 'mode === "valid"' in JS
    assert 'mode === "none"' in JS
    assert 'ui.chartMessage.textContent = "No complete setup is available yet."' in JS

def test_valid_plan_draws_entry_stop_and_targets_only():
    for level in ('addLevel("Entry"', 'addLevel("Stop"', 'addLevel("TP1"', 'addLevel("TP2"'):
        assert level in JS
    assert 'addLevel("Current Price"' in JS

def test_fvg_is_optional_and_safe():
    assert "if (ui.fvg.checked) drawFvg(analysis);" in JS
    assert "if (!zone) return;" in JS
    assert ".zone-fvg" in CSS
