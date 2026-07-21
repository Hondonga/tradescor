from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "app.js").read_text()
CSS = (ROOT / "static" / "style.css").read_text()


def test_frontend_caps_score_and_confidence_by_stage():
    assert '"WATCHING AREA": 60' in JS
    assert '"IN SETUP AREA": 70' in JS
    assert '"CONFIRMATION FORMING": 80' in JS
    assert 'normalized === "SETUP CONFIRMED"' in JS
    assert 'validConfirmedPlan ? "High" : "Medium"' in JS


def test_confirmation_rr_uses_confirmation_stop_and_unswept_target():
    assert "const entry = finiteOrNull(setup.trigger?.price)" in JS
    assert "const stop = finiteOrNull(setup.invalidation?.price)" in JS
    assert "candidate.swept !== true" in JS
    assert 'remainingRr >= 1 ? "acceptable" : "poor"' in JS
    assert "Confirmation may be too late for a clean entry." in JS


def test_bearish_level_geometry_is_enforced():
    assert "invalidation > zone.high && confirmation < zone.low" in JS


def test_overlay_uses_exact_normalized_backend_zone():
    assert "low = numeric(source.low ?? source.bottom" in JS
    assert "high = numeric(source.high ?? source.top" in JS
    assert "priceToCoordinate(setup.setup_zone.high)" in JS
    assert "priceToCoordinate(setup.setup_zone.low)" in JS


def test_sell_zone_is_visible_and_named():
    assert '"Sell Zone"' in JS
    assert "background: rgba(245,158,11,.08)" in CSS
    assert "border-color: rgba(245,158,11,.45)" in CSS
