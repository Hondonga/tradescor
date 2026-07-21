from analysis.step_regime_classifier import classify_step_regime
import pandas as pd
def test_insufficient_profile_is_explicit():
    assert classify_step_regime(pd.DataFrame(),{"quality":"insufficient"},{})["regime"]=="INSUFFICIENT_DATA"
