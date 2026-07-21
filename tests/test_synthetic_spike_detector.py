import pandas as pd
from analysis.synthetic_spike_detector import detect_synthetic_spike
def rows(direction):
    data=[]
    for i in range(25):
        opened=100;close=100.1;high=100.2;low=99.9
        if i==24:
            close=110 if direction=="up" else 90;high=max(opened,close)+.2;low=min(opened,close)-.2
        data.append({"time":i,"open":opened,"high":high,"low":low,"close":close,"complete":True})
    return pd.DataFrame(data)
def test_spike_is_family_aware_but_opposite_move_is_preserved():
    assert detect_synthetic_spike(rows("up"),family="BOOM")["classification"]=="expected_family_spike"
    assert detect_synthetic_spike(rows("down"),family="CRASH")["family_expected"] is True
    opposite=detect_synthetic_spike(rows("down"),family="BOOM");assert opposite["spike_detected"] and not opposite["family_expected"]
    assert "predicted" not in str(opposite).lower()
