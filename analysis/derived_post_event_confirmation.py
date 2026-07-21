from analysis.derived_post_spike_confirmation import post_spike_zone_interaction,confirm_post_spike,lock_post_spike_entry
def post_event_zone_interaction(candles,zone,after_time):return post_spike_zone_interaction(candles,zone,after_time)
def confirm_post_event(candles,direction,zone,setup_id,event_id,interaction_time,cooldown):
    row=confirm_post_spike(candles,direction,zone,setup_id,event_id,interaction_time,cooldown)
    if row is not None:row["valid_for_event_id"]=row.pop("valid_for_spike_id",None)
    return row
def lock_post_event_entry(confirmation,setup_id,event_id,price,existing=None):
    adapted={**confirmation,"valid_for_spike_id":confirmation.get("valid_for_event_id")} if confirmation else None;row=lock_post_spike_entry(adapted,setup_id,event_id,price,existing);row["event_id"]=row.pop("spike_id",event_id);return row
