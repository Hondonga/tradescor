"""Per-symbol enter/exit hysteresis preventing regime flapping."""
_STATE={}
def apply_regime_hysteresis(symbol,candidate_regime,confidence,persistence_count,config=None,decisive_invalidation=False):
    cfg=config or {}; old=_STATE.get(symbol,""); enter=float(cfg.get("minimum_enter_confidence",.7)); exit_=float(cfg.get("minimum_exit_confidence",.65)); required=int(cfg.get("minimum_candidate_persistence",3)); changed=bool(old and old!=candidate_regime)
    confirmed=bool((not old and confidence>=enter and persistence_count>=required) or (changed and ((decisive_invalidation and confidence>=exit_) or confidence>=enter and persistence_count>=required)))
    if confirmed or not old and persistence_count>=required: _STATE[symbol]=candidate_regime
    current=_STATE.get(symbol,""); pending=bool(current and current!=candidate_regime)
    return {"previous_confirmed_regime":old,"confirmed_regime":current,"candidate_regime":candidate_regime,"change_pending":pending,"change_confirmed":confirmed and changed,"persistence_count":persistence_count,"reason":"Decisive structural invalidation confirmed the change." if decisive_invalidation and confirmed else "Candidate must persist before replacing the confirmed regime." if pending else "Confirmed regime retained."}
def clear_regime_hysteresis(): _STATE.clear()
