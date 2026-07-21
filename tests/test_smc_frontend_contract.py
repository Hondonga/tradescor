from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_derived_header_is_24_7_utc_not_a_liquidity_window():
    source=(ROOT/"static"/"app.js").read_text();assert 'derived?"Analysis Context"' in source and 'derived?"24/7 UTC"' in source
def test_frontend_uses_backend_owner_and_smc_gate_explanations():
    source=(ROOT/"static"/"app.js").read_text();assert "contract.gate_funnel" in source and "ownership.decision_owner_id" in source
    html=(ROOT/"templates"/"index.html").read_text();assert "SMC Auto · Recommended" in html and 'label="Legacy Research"' in html and 'id="smc-model-card"' in html
