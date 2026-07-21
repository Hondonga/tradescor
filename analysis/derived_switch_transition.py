"""Transition identity and terminal cancellation of stale delegated setups."""
import hashlib,json
from analysis.derived_setup_lifecycle import cancel_active_setups_for_regime_switch
def manage_switch_transition(*,symbol,from_regime,to_candidate_regime,started_at,change_pending=False,change_confirmed=False):
    active=bool(change_pending or change_confirmed); transition_id="switch-"+hashlib.sha256(json.dumps([symbol,from_regime,to_candidate_regime,started_at],default=str).encode()).hexdigest()[:20] if active else ""
    cancelled=cancel_active_setups_for_regime_switch(symbol,started_at) if change_confirmed else []; cancelled_id=cancelled[-1]["setup_id"] if cancelled else None
    return {"transition_id":transition_id,"from_regime":from_regime,"to_candidate_regime":to_candidate_regime,"started_at":started_at if active else None,"confirmed_at":started_at if change_confirmed else None,"cancelled_setup_id":cancelled_id,"state":"confirmed" if change_confirmed else "pending" if change_pending else "stabilizing" if active else "failed","reason":"Confirmed regime switch cancelled the previous setup." if change_confirmed else "Candidate regime is waiting for completed-candle stability." if change_pending else "No active transition."}
