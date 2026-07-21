from strategies.derived.base_derived_strategy import candidate,directional_result
def evaluate_regime_switch(*,profile,regime):
    volatility=profile.get("volatility_regime","MEDIUM");unstable=regime.get("regime") in {"UNSTABLE","VOLATILITY_TRANSITION"};direction=regime.get("direction")
    def side(name):
        eligible=not unstable and direction==("bullish" if name=="buy" else "bearish") and volatility in {"HIGH","RISING"};return candidate("regime_switch",name,eligible=eligible,state="WAITING_FOR_RETEST" if eligible else "NO_SETUP",quality=65 if eligible else 0)
    return directional_result("regime_switch",side("buy"),side("sell"))|{"volatility_state":volatility}
