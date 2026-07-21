"""Chronological fill evaluation strictly after the decision snapshot."""
import pandas as pd
def evaluate_paper_fill(setup,candles,entry_type="confirmation_close",slippage_points=0):
    rows=_after(candles,setup["created_at"]);base={"filled":False,"fill_time":None,"requested_entry":setup["entry"],"filled_entry":None,"fill_type":entry_type,"slippage_points":None,"fill_reason":"","miss_reason":""}
    if rows.empty:return {**base,"miss_reason":"No completed candle exists after the decision."}
    if setup.get("entry_valid_until"):rows=rows[rows.time<=pd.Timestamp(setup["entry_valid_until"])]
    if rows.empty:return {**base,"miss_reason":"Entry window expired before a subsequent candle."}
    if entry_type in {"confirmation_close","market_at_next_available_tick","next_base_candle_open"}:row=rows.iloc[0];reference=float(row.open) if entry_type=="next_base_candle_open" else float(setup["entry"]);price=reference+float(slippage_points)*(1 if setup["direction"]=="buy" else -1)
    else:
        touched=rows[(rows.low<=float(setup["entry"]))&(rows.high>=float(setup["entry"]))]
        if touched.empty:return {**base,"miss_reason":"Subsequent candles did not reach the locked entry."}
        row=touched.iloc[0];price=float(setup["entry"])+float(slippage_points)*(1 if setup["direction"]=="buy" else -1)
    return {**base,"filled":True,"fill_time":_time(row),"filled_entry":price,"slippage_points":float(slippage_points),"fill_reason":"First eligible completed post-decision candle satisfied the configured entry policy."}
def _after(candles,time):
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows
    return rows[rows.time>pd.Timestamp(time)].sort_values("time") if "time" in rows else rows.iloc[0:0]
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
