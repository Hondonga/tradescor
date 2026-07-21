"""Contracts for faint conditional Scenario Path drawings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


def test_path_toggle_and_svg_default_off():
    assert 'id="show-path" type="checkbox"' in HTML
    assert 'id="show-path" type="checkbox" checked' not in HTML
    assert 'aria-label="Show conditional setup path"' in HTML
    assert 'aria-pressed="false"' in HTML
    assert 'id="scenario-path-layer"' in HTML


def test_conditional_not_predictive_copy():
    assert "This shows a conditional guide, not an exact prediction." in HTML


def test_buy_and_sell_paths_use_directional_backend_levels():
    assert "zoneEdgePrice" in JS
    assert '"Confirm"' in JS
    assert "setup.setup_zone" in JS and "setup.trigger?.price" in JS and "setup.targets" in JS


def test_missing_levels_stop_supported_segments():
    assert "if (triggerPrice === null)" in JS
    assert "if (!zone || ![zone.low, zone.high].every(Number.isFinite)) return" in JS
    assert "if (!Number.isFinite(currentPrice)) return" in JS


def test_inactive_stages_hide_paths():
    assert '["SETUP CONFIRMED", "SETUP MISSED", "SETUP INVALIDATED"].includes(setup.stage)' in JS
    assert 'mode === "valid"' in JS


def test_path_style_is_faint_dashed_and_noninteractive():
    assert "stroke-dasharray: 6 6" in CSS
    assert "opacity: .38" in CSS
    assert "stroke-width: 1.75" in CSS
    assert "pointer-events: none" in CSS


def test_only_primary_path_is_drawn():
    assert "drawScenarioPath(setups[0], false)" in JS
    assert ".scenario-path.alternative" in CSS
    assert "opacity: .18" in CSS


def test_future_space_and_coordinate_conversion():
    assert "chart.timeScale().timeToCoordinate" in JS
    assert "candleSeries.priceToCoordinate" in JS
    assert "rightOffset: 18" in JS
    assert "const endX = width -" in JS


def test_path_is_disconnected_and_never_routes_to_targets():
    draw = JS.split("function drawScenarioPath", 1)[1].split("function appendConditionalArrow", 1)[0]
    assert draw.count("appendConditionalArrow(") == 2
    assert "Potential TP1" not in draw
    assert "Potential TP2" not in draw
    assert '"Retrace"' in draw
    assert '"Confirm"' in draw
    assert 'setup.stage === "WATCHING AREA"' in draw


def test_countertrend_label_uses_higher_timeframe_context():
    assert "function possibleSetupLabel" in JS
    assert "Possible Countertrend" in JS
    assert "higher_timeframe_bias" in JS


def test_redraws_are_debounced_for_resize_and_visible_range():
    assert "function scheduleOverlayRedraw" in JS
    assert "setTimeout(() => drawChartOverlays" in JS
    assert "subscribeVisibleTimeRangeChange(scheduleOverlayRedraw)" in JS
    assert "new ResizeObserver(scheduleOverlayRedraw)" in JS


def test_rendering_makes_no_network_request():
    function = JS.split("function drawScenarioPaths", 1)[1].split("function drawScenarioPath", 1)[0]
    assert "fetch(" not in function
