"""Contracts for the focused chart-detail refinement."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


def test_chart_has_compact_state_and_timing_guidance():
    assert 'id="chart-state-badge"' in HTML
    assert 'id="chart-timing-note"' in HTML
    assert "function updateChartGuidance" in JS
    for label in ("SETUP FORMING", "Watching Area", "Near Confirmation", "Confirmed", "SETUP MISSED", "SETUP INVALIDATED", "NO VALID SETUP"):
        assert label in JS or label in HTML


def test_setup_zone_confirmation_invalidation_and_target_are_clear():
    assert "Confirmation ·" in JS
    assert '"Invalid Above" : "Invalid Below"' in JS
    assert 'addSetupLevel("Potential TP1 after confirmation"' in JS
    assert "overlay-zone-label" in JS
    assert ".possible-setup-zone" in CSS


def test_fvg_and_ifvg_receive_small_labels():
    assert '"IFVG" : "FVG"' in JS
    assert ".overlay-zone-label" in CSS


def test_possible_setup_panel_is_compact():
    markup = JS.split("function possibleSetupMarkup", 1)[1].split("function zonePriceLabel", 1)[0]
    for label in ("Zone", "Confirmation", "Invalidation", "Target"):
        assert label in markup
    for clutter in ("Scenario", "Setup Progress", "Risk / reward", "Entry timing"):
        assert clutter not in markup


def test_chart_path_remains_conditional_and_has_no_tp_route():
    draw = JS.split("function drawScenarioPath", 1)[1].split("function appendConditionalArrow", 1)[0]
    assert '"Retrace"' in draw
    assert '"Confirm"' in draw
    assert "Potential TP1" not in draw
