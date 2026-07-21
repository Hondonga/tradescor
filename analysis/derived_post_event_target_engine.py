from analysis.derived_spike_target_engine import build_spike_targets
def build_post_event_targets(**kwargs):
    kwargs["spike"]=kwargs.pop("event");return build_spike_targets(**kwargs)
