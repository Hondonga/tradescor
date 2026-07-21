from analysis.derived_post_spike_structure import analyze_post_spike_structure
def analyze_post_event_structure(candles,event):
    spike={**event,"spike_id":event.get("event_id")} if event else None;row=analyze_post_spike_structure(candles,spike)
    return {"direction":row["direction"],"state":row["state"].replace("SPIKE","EVENT"),"last_swing_high":row.get("last_swing_high"),"last_swing_low":row.get("last_swing_low"),"last_higher_low":None,"last_lower_high":None,"bullish_structure_break":row.get("bullish_structure_break"),"bearish_structure_break":row.get("bearish_structure_break"),"formed_after_event":row.get("formed_after_spike",False),"valid_for_event_id":event.get("event_id") if event else None,"evidence":row.get("evidence",[]),"contradictions":row.get("contradictions",[])}
