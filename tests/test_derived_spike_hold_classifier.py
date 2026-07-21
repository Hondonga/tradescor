import pandas as pd
from analysis.derived_spike_hold_classifier import classify_spike_hold
def test_hold_and_full_retrace_are_distinguished():
    spike={"direction":"up","origin_price":100,"extreme_price":110,"completed_at":"2026-01-01T00:00:00Z"};hold=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:05:00Z"),"close":108,"complete":True}]);failed=pd.DataFrame([{"time":pd.Timestamp("2026-01-01T00:05:00Z"),"close":99,"complete":True}]);assert classify_spike_hold(hold,spike,1)["classification"]=="HOLDING_ABOVE_ORIGIN" and classify_spike_hold(failed,spike,1)["classification"]=="FAILED_HOLD"
