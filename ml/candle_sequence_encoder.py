from __future__ import annotations
import numpy as np
import pandas as pd

def encode_m5_sequence(candles,decision_time,length=64):
    rows=_completed(candles,decision_time).tail(int(length)).copy()
    if rows.empty:return []
    atr=(rows.high.astype(float)-rows.low.astype(float)).rolling(14,min_periods=1).mean().replace(0,np.nan);previous=rows.close.astype(float).shift(1).fillna(rows.open.astype(float));span=(rows.high-rows.low).astype(float).replace(0,np.nan);body=(rows.close-rows.open).astype(float)
    values=np.column_stack(((rows.open-previous)/atr,(rows.high-rows.open)/atr,(rows.low-rows.open)/atr,(rows.close-previous)/atr,body/atr,span/atr,(rows.high-rows[["open","close"]].max(axis=1))/span,(rows[["open","close"]].min(axis=1)-rows.low)/span))
    values=np.nan_to_num(values,nan=0.0,posinf=0.0,neginf=0.0)
    if len(values)<length:values=np.vstack((np.zeros((length-len(values),8)),values))
    return values.tolist()

def _completed(rows,at):
    frame=rows.copy() if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows or []);frame=frame[frame.complete.astype(bool)] if "complete" in frame else frame
    return frame[pd.to_datetime(frame.time,utc=True)<=pd.Timestamp(at)].sort_values("time")
