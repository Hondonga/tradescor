from analysis.derived_regime_hysteresis import apply_regime_hysteresis,clear_regime_hysteresis
def test_hysteresis_prevents_flapping_and_decisive_override():
    clear_regime_hysteresis(); apply_regime_hysteresis("x","SIDEWAYS_DRIFT",.9,3)
    pending=apply_regime_hysteresis("x","BEARISH_DRIFT",.9,1); assert pending["change_pending"] and pending["confirmed_regime"]=="SIDEWAYS_DRIFT"
    changed=apply_regime_hysteresis("x","BEARISH_DRIFT",.9,1,decisive_invalidation=True); assert changed["change_confirmed"]
