from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_frontend_renders_backend_gate_explanations_without_inference():
    source=(ROOT/"static"/"app.js").read_text();html=(ROOT/"templates"/"index.html").read_text()
    assert 'contract.gate_funnel||contract.diagnostics?.setup_gates' in source
    assert 'funnel.first_blocking_gate' in source and 'funnel.next_price_condition' in source
    assert 'Why no setup?' in html and 'Shadow Candidate' in html and 'History Availability' in html
    block=source[source.index("function renderSetupGateDiagnostics"):source.index("function renderBoomCrashState")]
    assert "trade_ready=" not in block and "active_trade_plan=" not in block
