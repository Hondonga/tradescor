from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text()
JS = (ROOT / "static" / "app.js").read_text()
CSS = (ROOT / "static" / "style.css").read_text()


def test_clean_overlay_defaults():
    assert 'id="show-zones" type="checkbox" checked' in HTML
    assert 'id="show-setups" type="checkbox" checked' in HTML
    assert 'id="show-fvg" type="checkbox" checked' in HTML
    assert 'id="show-path" type="checkbox" checked' not in HTML
    assert 'id="show-labels" type="checkbox" checked' not in HTML


def test_status_language_is_shared_and_bounded():
    for status in (
        "NO VALID SETUP",
        "BUY SETUP FORMING",
        "SELL SETUP FORMING",
        "BUY CONFIRMED",
        "SELL CONFIRMED",
        "SETUP MISSED",
        "SETUP INVALIDATED",
    ):
        assert status in JS or status in HTML
    assert "formatUserStatus({ ...analysis, possible_setups: setups })" in JS
    assert 'if (mainStatus === "NO VALID SETUP") return []' in JS


def test_entry_timing_uses_short_stage_labels():
    for label in ("Watching Area", "In Zone", "Reaction Forming", "Near Confirmation", "Confirmed", "Too Late", "Invalid"):
        assert label in JS


def test_possible_setup_is_only_essential_rows():
    markup = JS.split("function possibleSetupMarkup", 1)[1].split("function zonePriceLabel", 1)[0]
    for row in ("Zone", "Confirmation", "Invalidation", "Target"):
        assert row in markup
    for clutter in ("Scenario", "Setup Progress", "Risk / reward", "Entry timing", "Show on Chart"):
        assert clutter not in markup


def test_only_one_stage_specific_path_guide_is_drawn():
    paths = JS.split("function drawScenarioPaths", 1)[1].split("function appendConditionalArrow", 1)[0]
    assert "drawScenarioPath(setups[0], false)" in paths
    assert 'setup.stage === "WATCHING AREA"' in paths
    assert '["IN SETUP AREA", "REACTION FORMING", "CONFIRMATION FORMING"].includes(setup.stage)' in paths
    assert '"Retrace"' in paths
    assert '"Confirm"' in paths
    assert "Watching for reaction" not in paths
    assert "Only valid after confirmation" not in paths


def test_flat_zone_gets_single_price_and_visible_band():
    assert "function zonePriceLabel" in JS
    assert "effectivelyFlat || low === high" in JS
    assert "Math.max(4, rawHeight)" in JS
    assert 'node.classList.add("zone-line-band")' in JS
    assert ".zone-line-band .overlay-zone-label" in CSS


def test_confirmation_and_invalidation_labels_are_compact():
    assert "Confirmation ·" in JS
    assert '"Below" : "Above"' in JS
    assert '"Invalid Above" : "Invalid Below"' in JS


def test_next_action_is_one_short_sentence():
    assert "function shortNextAction" in JS
    assert "Setup is invalid. Do not enter." in JS
    assert "Price is too extended. Wait for a fresh setup." in JS
    assert "Watch for price to retrace into the" in JS


def test_panel_hides_secondary_trade_plan_and_filters():
    assert '<section hidden><span>Trade Plan</span>' in HTML
    assert '<section hidden><span>Market Filters</span>' in HTML
