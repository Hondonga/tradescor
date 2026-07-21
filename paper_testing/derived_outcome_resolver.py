"""Conservative chronological stop/target resolution after fill."""
import pandas as pd
from paper_testing.derived_r_multiple import planned_r
def resolve_paper_outcome(setup,candles,fill_time,policy="mark_ambiguous",management=None):
    rows=candles.copy() if candles is not None else pd.DataFrame();rows=rows[rows.complete.astype(bool)] if "complete" in rows else rows;rows=rows[rows.time>pd.Timestamp(fill_time)].sort_values("time") if "time" in rows else rows.iloc[0:0];events=[];tp1_hit=False;tp2_hit=False;stop_hit=False;ambiguous=False;terminal=None
    for _,row in rows.iterrows():
        stop_touch=float(row.low)<=setup["stop"] if setup["direction"]=="buy" else float(row.high)>=setup["stop"];tp1_touch=float(row.high)>=setup["tp1"] if setup["direction"]=="buy" else float(row.low)<=setup["tp1"];tp2_touch=bool(setup.get("tp2") is not None and (float(row.high)>=setup["tp2"] if setup["direction"]=="buy" else float(row.low)<=setup["tp2"]));time=_time(row)
        if stop_touch and (tp1_touch or tp2_touch):
            ambiguous=True;events.append({"event":"ambiguous_stop_target","time":time,"price":None})
            if policy=="target_first":tp1_hit=tp1_touch;tp2_hit=tp2_touch;terminal="TP2_HIT" if tp2_hit else "TP1_HIT"
            elif policy in {"worst_case","stop_first"}:stop_hit=True;terminal="STOPPED"
            else:terminal="AMBIGUOUS"
            break
        if tp1_touch and not tp1_hit:
            tp1_hit=True;events.append({"event":"tp1_hit","time":time,"price":setup["tp1"]})
            if setup.get("tp2") is None:terminal="TP1_HIT";break
        if tp2_touch:tp2_hit=True;events.append({"event":"tp2_hit","time":time,"price":setup["tp2"]});terminal="TP1_THEN_TP2" if tp1_hit else "TP2_HIT";break
        if stop_touch:stop_hit=True;events.append({"event":"stop_hit","time":time,"price":setup["stop"]});terminal="TP1_THEN_STOP" if tp1_hit else "STOPPED";break
    if not terminal:return {"outcome":"OPEN","terminal_reason":None,"terminal_time":None,"entry_filled":True,"tp1_hit":tp1_hit,"tp2_hit":False,"stop_hit":False,"intracandle_ambiguous":False,"resolution_policy":policy,"resolution_reason":"No terminal event in processed candles.","event_log":events,"realized_r":None}
    tp1_r=planned_r(setup["direction"],setup["entry"],setup["stop"],setup["tp1"]);tp2_r=planned_r(setup["direction"],setup["entry"],setup["stop"],setup.get("tp2")) if setup.get("tp2") is not None else None;cfg=management or {};f1=float(cfg.get("tp1_close_fraction",.5));f2=float(cfg.get("tp2_close_fraction",.5));realized=-1 if terminal=="STOPPED" else None if terminal=="AMBIGUOUS" else tp1_r if terminal=="TP1_HIT" else f1*tp1_r-f2 if terminal=="TP1_THEN_STOP" else f1*tp1_r+f2*(tp2_r or tp1_r) if terminal in {"TP1_THEN_TP2","TP2_HIT"} else None
    return {"outcome":terminal,"terminal_reason":terminal,"terminal_time":events[-1]["time"],"entry_filled":True,"tp1_hit":tp1_hit,"tp2_hit":tp2_hit,"stop_hit":stop_hit,"intracandle_ambiguous":ambiguous,"resolution_policy":policy,"resolution_reason":"OHLC ambiguity was handled by configured policy." if ambiguous else "Chronological completed-candle event.","event_log":events,"realized_r":realized}
def _time(row):
    value=row.get("time");return value.isoformat() if hasattr(value,"isoformat") else str(value)
