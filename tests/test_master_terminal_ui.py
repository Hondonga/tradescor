from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_terminal_navigation_and_derived_model_choices_are_present():
    html=(ROOT/"templates"/"index.html").read_text()
    for page in ("home","scanner","chart","replay","paper","performance","settings"):assert f'data-page-link="{page}"' in html
    assert "SMC Auto · Recommended" in html
    assert all(value in html for value in ('value="volatility_smc"','value="jump_smc"','value="step_smc"'))

def test_derived_terminal_uses_utc_and_normalized_overlay_contract():
    html=(ROOT/"templates"/"index.html").read_text();source=(ROOT/"static"/"app.js").read_text()
    assert "24/7 UTC" in html and "Advanced SMC" in html
    assert "product.overlays" in source and "overlay.owner_id!==product.ownership?.overlay_owner_id" in source
    assert "analysis.decision?.meta?.market_type" in source

def test_focus_styles_and_responsive_breakpoints_exist():
    css=(ROOT/"static"/"style.css").read_text()
    assert ":focus-visible" in css and "max-width: 760px" in css and "max-width: 1280px" in css
