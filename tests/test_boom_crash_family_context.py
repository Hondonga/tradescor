import pandas as pd
from analysis.boom_crash_family_context import build_boom_crash_family_context
def test_family_context_uses_expected_direction_but_measures_drift():
    rows=pd.DataFrame([{"close":100-i,"complete":True} for i in range(20)]);boom=build_boom_crash_family_context("BOOM",rows);crash=build_boom_crash_family_context("CRASH",rows);assert boom["expected_spike_direction"]=="up" and crash["expected_spike_direction"]=="down" and boom["current_drift_direction"]=="bearish"
