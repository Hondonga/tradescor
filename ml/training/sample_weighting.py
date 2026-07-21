from __future__ import annotations
import pandas as pd

def setup_equal_weights(frame):
    counts=frame.groupby("setup_id").setup_id.transform("count");weights=1.0/counts;weights*=len(weights)/weights.sum();return pd.Series(weights,index=frame.index,name="training_weight")
