import pandas as pd
def track_mfe_mae(setup,candles,fill_time,resolved_time=None):
    """Excursion between fill and trade resolution.

    ``resolved_time`` bounds the window at the stop/target/expiration event.
    Without it, excursion is measured over every remaining candle in the
    dataset tail, which massively inflates MFE/MAE (buys showed ~78R MFE in
    the R_75 dataset because the window never closed).
    """
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows;rows=rows[rows.time>pd.Timestamp(fill_time)].sort_values("time") if "time" in rows else rows.iloc[0:0]
    if resolved_time is not None and "time" in rows:rows=rows[rows.time<=pd.Timestamp(resolved_time)]
    if rows.empty:return {"mfe_points":None,"mfe_r":None,"mfe_time":None,"mae_points":None,"mae_r":None,"mae_time":None,"maximum_price":None,"minimum_price":None}
    entry=float(setup["entry"]);risk=float(setup["risk_points"]);maximum=float(rows.high.max());minimum=float(rows.low.min())
    if setup["direction"]=="buy":mfe=maximum-entry;mae=entry-minimum;mfe_row=rows.loc[rows.high.idxmax()];mae_row=rows.loc[rows.low.idxmin()]
    else:mfe=entry-minimum;mae=maximum-entry;mfe_row=rows.loc[rows.low.idxmin()];mae_row=rows.loc[rows.high.idxmax()]
    return {"mfe_points":max(0,mfe),"mfe_r":max(0,mfe)/risk,"mfe_time":_time(mfe_row),"mae_points":max(0,mae),"mae_r":max(0,mae)/risk,"mae_time":_time(mae_row),"maximum_price":maximum,"minimum_price":minimum}
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
