def resolve_auto_conflict(selected,runner_up,regime):
    conflicts=[];resolved=False
    if selected and runner_up and selected.get("direction") and runner_up.get("direction") and selected["direction"]!=runner_up["direction"]:conflicts.append("Opposite directional candidates were not averaged.");resolved=True
    if regime in {"ACCEPTED_BREAKOUT","BREAKOUT_ATTEMPT"} and runner_up and selected and selected["strategy_id"]=="derived_range_reaction":selected,runner_up=runner_up,selected;resolved=True;conflicts.append("Breakout sequence overrides a boundary fade.")
    return {"selected_candidate":selected,"runner_up":runner_up,"conflict_resolved":resolved,"conflicts":conflicts}
