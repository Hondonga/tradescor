def classify_acceptance_evidence(*,resolved_trades,periods,symbols,regimes,directions,config=None):
    cfg={"preliminary_resolved":10,"moderate_resolved":40,"strong_resolved":100,"moderate_periods":2,"strong_periods":4,"moderate_symbols":2,"strong_symbols":4,**(config or {})};n=int(resolved_trades);periods=int(periods);symbols=int(symbols);coverage=bool(regimes>=2 and directions>=2)
    label="STRONG" if n>=cfg["strong_resolved"] and periods>=cfg["strong_periods"] and symbols>=cfg["strong_symbols"] and coverage else "MODERATE" if n>=cfg["moderate_resolved"] and periods>=cfg["moderate_periods"] and symbols>=cfg["moderate_symbols"] and coverage else "PRELIMINARY" if n>=cfg["preliminary_resolved"] else "INSUFFICIENT"
    return {"label":label,"resolved_trade_count":n,"independent_periods":periods,"symbols":symbols,"regime_coverage":regimes,"directional_coverage":directions,"eligible_for_ranking":label in {"MODERATE","STRONG"}}

