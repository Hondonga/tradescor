import json

def validate_dataset(dataset):
    errors=[]
    if dataset.quality=="invalid" or not dataset.candle_count:errors.append("Dataset has no valid candles.")
    if not dataset.checksum:errors.append("Dataset checksum is required.")
    return {"valid":not errors,"errors":errors,"warnings":list(dataset.warnings)}

def validate_no_lookahead(frames,replay_time):
    import pandas as pd
    t=pd.Timestamp(replay_time)
    violations=[]
    seconds={"M5":300,"M15":900,"M30":1800,"H1":3600,"H2":7200,"H4":14400,"D1":86400}
    for name,rows in frames.items():
        if name in seconds and len(rows) and (pd.to_datetime(rows.time,utc=True)+pd.to_timedelta(seconds[name],unit="s")>t).any():violations.append(name)
    return {"valid":not violations,"future_timeframes":violations,"replay_time":str(replay_time)}

def parity_report(live,replay,keys=("decision","active_trade_plan","m15_setup_zone","m5_execution_zone","confirmation")):
    differences={key:{"live":live.get(key),"replay":replay.get(key)} for key in keys if json.dumps(live.get(key),sort_keys=True,default=str)!=json.dumps(replay.get(key),sort_keys=True,default=str)}
    return {"parity":not differences,"differences":differences}

