from analysis.derived_post_spike_zone_engine import build_post_spike_zone,narrow_post_spike_execution_zone
def build_post_event_zone(candles,direction,event,structure,atr,current_price=None,config=None,timeframe="M15"):
    adapted={**structure,"formed_after_spike":structure.get("formed_after_event")};row=build_post_spike_zone(candles,direction,event,adapted,atr,current_price,(config or {}).get("post_event",config or {}),timeframe);row["formed_after_event"]=row.pop("formed_after_spike",False);row["valid_for_event_id"]=event.get("event_id") if event else None;row.pop("valid_for_spike_id",None);return row
def narrow_post_event_execution_zone(zone,atr):return narrow_post_spike_execution_zone(zone,atr)
