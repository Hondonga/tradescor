from strategies.derived.base_derived_strategy import candidate,directional_result
def evaluate_post_event(*,spike,regime):
    cooldown=spike.get("cooldown_active");direction=regime.get("direction")
    def side(name):
        eligible=spike.get("spike_detected") and not cooldown and direction==("bullish" if name=="buy" else "bearish");return candidate("post_event_structure",name,eligible=eligible,state="WAITING_FOR_RETEST" if eligible else "POST_EVENT_COOLDOWN" if cooldown else "NO_SETUP",quality=70 if eligible else 0)
    return directional_result("post_event_structure",side("buy"),side("sell"))
