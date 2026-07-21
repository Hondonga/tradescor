"""Completed-candle persistence gate; wall-clock time is never evidence."""
_STATE={}
def evaluate_regime_stability(symbol,candidate_regime,confidence,completed_candle_id,minimum_required_candles=3):
    old=_STATE.get(symbol); same=bool(old and old["candidate"]==candidate_regime); count=(old["count"]+1) if same and old.get("candle")!=completed_candle_id else old["count"] if same else 1
    _STATE[symbol]={"candidate":candidate_regime,"count":count,"candle":completed_candle_id}; stable=count>=minimum_required_candles and confidence>=.7
    return {"candidate_regime":candidate_regime,"confirmed_regime":candidate_regime if stable else "","completed_candles_in_candidate":count,"minimum_required_candles":minimum_required_candles,"confidence":confidence,"stable":stable,"release_allowed":stable,"reasons":[] if stable else ["Waiting for completed-candle regime persistence."]}
def clear_regime_stability(): _STATE.clear()
