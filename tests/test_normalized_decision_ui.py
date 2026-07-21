from pathlib import Path


JS = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text()


def test_primary_ui_fields_read_normalized_decision():
    assert "analysis.decision?.user_output?.direction" in JS
    assert "analysis.decision?.user_output?.status" in JS
    assert "analysis.decision?.quality?.score" in JS
    assert "analysis.decision?.quality?.trade_plan_valid" in JS
    assert "analysis.decision?.execution" in JS


def test_frontend_does_not_apply_score_or_confidence_thresholds():
    trade_score = JS.split("function tradeScore", 1)[1].split("function", 1)[0]
    confidence = JS.split("function confidence", 1)[1].split("function", 1)[0]
    assert "Math.min" not in trade_score
    assert ">=" not in confidence
