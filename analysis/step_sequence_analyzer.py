"""Descriptive completed-candle Step sequences; never predicts reversal."""
import pandas as pd
def analyze_step_sequence(candles):
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows;base={"current_sequence_direction":"flat","current_sequence_length":0,"average_sequence_length":None,"sequence_percentile":None,"extension_state":"unknown","reversal_due":False,"evidence":[],"warnings":[]}
    if len(rows)<5:return base
    signs=rows.close.diff().fillna(0).map(lambda x:1 if x>0 else -1 if x<0 else 0).tolist();runs=[];current=0;last=0
    for sign in signs:
        if sign==0:continue
        if sign==last:current+=1
        else:
            if current:runs.append(current)
            last=sign;current=1
    if current:runs.append(current)
    avg=sum(runs)/len(runs) if runs else 0;length=current;percentile=sum(value<=length for value in runs)/len(runs)*100 if runs else None;state="extreme" if percentile is not None and percentile>=95 else "extended" if percentile is not None and percentile>=80 else "normal"
    return {**base,"current_sequence_direction":"up" if last>0 else "down" if last<0 else "flat","current_sequence_length":length,"average_sequence_length":avg,"sequence_percentile":percentile,"extension_state":state,"evidence":["Sequence length is descriptive and does not imply reversal."],"warnings":["An extended sequence may make chase timing unfavorable."] if state in {"extended","extreme"} else []}
