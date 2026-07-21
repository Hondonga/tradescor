import pandas as pd
from analysis.step_sequence_analyzer import analyze_step_sequence
def test_long_sequence_never_predicts_reversal():
    close=list(range(30));rows=pd.DataFrame({"close":close,"complete":[True]*30});result=analyze_step_sequence(rows)
    assert result["extension_state"] in {"extended","extreme"} and result["reversal_due"] is False
