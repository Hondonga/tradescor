"""Frontend contracts for conditional Possible Setups."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


def test_possible_setups_toggle_defaults_on():
    assert 'id="show-setups" type="checkbox" checked' in HTML
    assert "if (ui.zones.checked || ui.setups.checked) drawPossibleSetups" in JS


def test_bullish_and_bearish_labels_are_supported():
    assert '"Potential Buy"' in JS
    assert '"Potential Sell"' in JS
    assert 'direction === "Long" ? "buy" : "sell"' in JS


def test_possible_setup_does_not_imply_ready_status():
    assert "entry_available: confirmed" in JS
    assert "const confirmed = hasValidPlan(analysis)" in JS
    assert 'if (ready && direction === "Long") return "BUY CONFIRMED"' in JS


def test_missing_levels_remain_null():
    assert "price: Number.isFinite(triggerPrice) ? triggerPrice : null" in JS
    assert "price: Number.isFinite(invalidationPrice) ? invalidationPrice : null" in JS
    assert "target && setup.confirmation_viable" in JS


def test_muted_dashed_candidate_styling_is_separate():
    assert ".possible-setup-zone { border-style: dashed" in CSS
    assert ".level-possible-trigger" in CSS
    assert ".level-possible-invalidation" in CSS
    assert ".level-possible-target" in CSS
    assert 'mode === "valid"' in JS


def test_maximum_two_and_incomplete_alternative_filter():
    assert ").slice(0, 2)" in JS
    assert 'setup.priority === "alternative"' in JS
    assert "!Number.isFinite(setup.trigger?.price)" in JS
    assert "!Number.isFinite(setup.invalidation?.price)" in JS


def test_stage_identity_and_staleness_contracts():
    for stage in ("WATCHING AREA", "IN SETUP AREA", "CONFIRMATION FORMING", "SETUP CONFIRMED", "SETUP MISSED", "SETUP INVALIDATED"):
        assert stage in JS
    assert "setupIdentity(strategy, directionWord, zone, candleTime)" in JS
    assert "creation_time: candleTime" in JS
    assert "last_updated_time: candleTime" in JS
    assert 'setup.stage !== "SETUP MISSED"' in JS


def test_primary_direction_cannot_contradict_main_status():
    assert 'mainStatus === "BUY SETUP FORMING"' in JS
    assert 'setup.direction !== "buy"' in JS
    assert 'mainStatus === "SELL SETUP FORMING"' in JS
    assert 'setup.direction !== "sell"' in JS


def test_targets_are_filtered_for_side_swept_and_reward():
    assert "target.swept === true" in JS
    assert "target.rr < 1" in JS
    assert 'direction === "Long" ? target.price > reference : target.price < reference' in JS
