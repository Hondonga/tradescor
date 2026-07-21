from pathlib import Path
from analysis.step_decision_normalizer import normalize_step_decision
def test_ready_output_keeps_research_label_and_false_validated_edge():
    delegated={"decision":{"trade_ready":True,"developing_direction":"sell","setup_id":"s","status":"READY TO SELL"}}
    row=normalize_step_decision(eligible=True,regime={"regime":"BEARISH_RUN","direction":"bearish"},routing={},delegated=delegated,sequence={},risk={"confidence_ceiling":.65})
    assert row["status"]=="RESEARCH SELL SETUP" and row["validated_edge"] is False and row["paper_analysis_only"] is True
def test_manual_option_and_research_badge_are_present():
    root=Path(__file__).parents[1];assert 'value="step_structure_research"' in (root/"templates/index.html").read_text();assert "RESEARCH MODE" in (root/"static/app.js").read_text()
