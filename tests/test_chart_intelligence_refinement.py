from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "app.js").read_text()
HTML = (ROOT / "templates" / "index.html").read_text()
CSS = (ROOT / "static" / "style.css").read_text()


def test_chart_and_panel_share_one_normalized_setup():
    assert "function finalizeNormalizedSetup" in JS
    assert "zone: setup.setup_zone" in JS
    assert "confirmation: setup.trigger" in JS
    assert "zonePriceLabel(zoneName, setup.zone)" in JS
    assert "priceToCoordinate(setup.setup_zone.low)" in JS


def test_zone_uses_recent_origin_fallback_and_future_extension():
    assert "candles.length - 6" in JS
    assert "explicitStart ?? recentOriginX" in JS
    assert "explicitEnd ?? rightEdge" in JS
    assert "start + 24" in JS


def test_zone_label_is_compact_and_uses_exact_values():
    assert '"Sell Zone"' in JS
    assert '"Buy Zone"' in JS
    assert "function zonePriceLabel" in JS
    assert "effectivelyFlat" in JS


def test_pip_distance_uses_forex_and_jpy_conventions():
    assert 'symbol.includes("JPY")' in JS
    assert "return 0.01" in JS
    assert "return 0.0001" in JS
    assert "/ pip).toFixed(1)" in JS


def test_unconfirmed_setup_has_no_active_trade_levels_or_target_path():
    forming_branch = JS.split("function drawChartOverlays", 1)[1].split("function addLevel", 1)[0]
    assert 'mode === "valid"' in forming_branch
    assert 'mode === "forming"' not in forming_branch
    path = JS.split("function drawScenarioPath", 1)[1].split("function appendConditionalArrow", 1)[0]
    assert "Potential TP1" not in path
    assert "Potential TP2" not in path


def test_target_and_confirmation_require_remaining_rr():
    assert "setup.confirmation_viable" in JS
    assert 'setup.confirmation_rr_status !== "poor"' in JS
    assert "Potential TP1 after confirmation" in JS
    assert "target && setup.confirmation_viable" in JS


def test_missed_and_invalidated_setups_hide_conditional_visuals():
    assert '["SETUP MISSED", "SETUP INVALIDATED"].includes(setup.stage)' in JS
    assert '["SETUP CONFIRMED", "SETUP MISSED", "SETUP INVALIDATED"].includes(setup.stage)' in JS


def test_toolbar_defaults_and_toggles_control_renderers():
    for control in ('show-zones', 'show-setups'):
        assert f'id="{control}" type="checkbox" checked' in HTML
    assert 'id="show-fvg" type="checkbox" checked' in HTML
    assert 'id="show-path" type="checkbox" checked' not in HTML
    assert 'id="show-labels" type="checkbox"' in HTML
    assert "if (ui.fvg.checked) drawFvg" in JS
    assert "ui.zones.checked || ui.setups.checked" in JS
    assert "ui.scenarioLayer.hidden = !ui.path.checked" in JS
    assert "if (ui.labels.checked) drawZoneDistance" in JS


def test_null_zero_and_stale_levels_do_not_render():
    assert "low <= 0 || high < low" in JS
    assert "!Number.isFinite(price) || price <= 0" in JS
    assert "target.setup_id === item.id" in JS


def test_visual_style_is_restrained_and_type_specific():
    assert "rgba(56,189,248,.08)" in CSS
    assert "rgba(245,158,11,.08)" in CSS
    assert "rgba(59,130,246,.05)" in CSS
    assert "rgba(139,92,246,.06)" in CSS


def test_label_collision_priority_is_enforced():
    assert "function resolveOverlayLabelCollisions" in JS
    assert 'node.closest(".level-current") ? 1' in JS
    assert 'node.closest(".possible-setup-zone") ? 2' in JS
    assert "priority(label) >= 6" in JS


def test_rendering_does_not_make_an_api_call():
    renderer = JS.split("function drawChartOverlays", 1)[1].split("function renderLabPage", 1)[0]
    assert "fetch(" not in renderer
