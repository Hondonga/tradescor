from analysis.derived_spike_hold_classifier import classify_spike_hold
def classify_event_hold(candles,event,atr,config=None):
    row=classify_spike_hold(candles,event,atr,config);mapping={"HOLDING_ABOVE_ORIGIN":"HOLDING_ABOVE_EVENT_ORIGIN","HOLDING_BELOW_ORIGIN":"HOLDING_BELOW_EVENT_ORIGIN","RECLAIMED":"ORIGIN_RECLAIMED","FAILED_HOLD":"EVENT_REJECTED"};row["classification"]=mapping.get(row["classification"],row["classification"]);return row
