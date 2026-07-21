from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_validation_ui_is_outside_chart_and_uses_backend_report():
    html=(ROOT/"templates"/"index.html").read_text();source=(ROOT/"static"/"app.js").read_text();assert html.index('id="smc-validation-title"')>html.index('id="lab-page"') and 'id="smc-validation-causality"' in html;assert '/api/smc-validation/runs/' in source and 'lastSmcValidation.reachability' in source
