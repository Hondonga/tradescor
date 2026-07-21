from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "app.js").read_text()
CSS = (ROOT / "static" / "style.css").read_text()


def test_setup_zones_use_price_and_time_coordinates():
    assert "priceToCoordinate(setup.setup_zone.high)" in JS
    assert "timeToCoordinate(seconds)" in JS
    assert "applyZoneGeometry(zone, setup.setup_zone" in JS
    assert "node.style.left" in JS
    assert "node.style.width" in JS


def test_strategy_zone_times_are_preserved():
    assert "source.start_time ?? source.time ?? source.departure_time" in JS
    assert "source.end_time ?? source.rectangle_end_time" in JS


def test_confirmation_is_one_line_and_fvg_is_a_real_box():
    assert "Confirmation ·" in JS
    assert "level-possible-trigger" in JS
    assert "Confirmation Zone" not in JS
    assert "applyZoneGeometry(node, geometry, y1, y2, analysis)" in JS


def test_overlay_is_visible_above_chart_and_has_semantic_zone_styles():
    assert "#chart-overlay { position: absolute; inset: 0; z-index: 3" in CSS
    assert ".possible-setup-zone.zone-supply" in CSS
    assert ".possible-setup-zone.zone-demand" in CSS
    assert ".possible-setup-zone.zone-retracement" in CSS


def test_zones_redraw_when_visible_time_range_changes():
    assert "subscribeVisibleTimeRangeChange(scheduleOverlayRedraw)" in JS
    assert "drawChartOverlays(latest || {})" in JS
