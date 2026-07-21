"""Single authoritative view of which strategies Auto routing may select.

This does not replace the existing gating mechanisms (analysis.strategy_
reachability_gate.gate_auto_result / gate_normalized_auto_result, which read
data/strategy_setup_proof/latest.json and already block every non-reachable
strategy at the point Auto results are produced) or the declarative fixture
registry (validation.strategy_reachability_registry). It is a read-only
summary over those existing, already-tested sources of truth, shaped to the
Phase 2 stabilization milestone's exact field contract, so any caller (a
report, a test, a future UI) has one place to ask "is this strategy eligible"
without re-deriving the logic.
"""
from __future__ import annotations

from analysis.strategy_reachability_gate import production_strategy_status, reachability_status
from validation.strategy_reachability_registry import strategy_reachability_registry

# Families with no formal production-proof entity in the strategy registry at
# all (they're research-only by construction, not merely "not yet proven").
_RESEARCH_ONLY_FAMILIES_WITHOUT_REGISTRY_ENTRY = {}


def strategy_quarantine_view() -> dict:
    """Returns {strategy_id: {...Phase 2 required fields...}} for every
    strategy the declarative registry knows about, plus a synthetic "ml"
    entry documenting the frozen/rejected model's exclusion."""
    registry = strategy_reachability_registry()
    view = {}
    for strategy_id, spec in registry.items():
        status = production_strategy_status(strategy_id) if spec["production_supported"] else None
        reach = reachability_status(strategy_id)
        buy_reachable = bool(status and status["fixture_buy_reachable"])
        sell_reachable = bool(status and status["fixture_sell_reachable"])
        auto_eligible = bool(spec["production_supported"] and reach == "REACHABLE")
        view[strategy_id] = {
            "strategy_id": strategy_id,
            "family": spec["family"],
            "production_supported": spec["production_supported"],
            "buy_reachable": buy_reachable,
            "sell_reachable": sell_reachable,
            "auto_eligible": auto_eligible,
            "historical_edge_proven": False,
            "profitability_claim_allowed": False,
            "research_only": not spec["production_supported"],
            "paper_signal_allowed": auto_eligible,
            "reachability_status": reach,
            "disabled_reason": "" if spec["production_supported"] else spec.get("support_status", "NOT_PRODUCTION_SUPPORTED"),
        }
    # Jump/JDBR is explicitly called out by the milestone with its own reason
    # code, distinct from the generic NOT_PRODUCTION_SUPPORTED label already
    # used by the underlying registry — surfaced here without changing that
    # registry's own (already-tested) support_status values.
    for jump_id in ("jump_post_event_continuation", "jump_post_event_reversal"):
        if jump_id in view:
            view[jump_id]["disabled_reason"] = "NO_CONFIRMED_DIRECTIONAL_EDGE"
    view["ml"] = {
        "strategy_id": "ml",
        "family": "ML",
        "production_supported": False,
        "buy_reachable": False,
        "sell_reachable": False,
        "auto_eligible": False,
        "historical_edge_proven": False,
        "profitability_claim_allowed": False,
        "research_only": True,
        "paper_signal_allowed": False,
        "reachability_status": "REJECTED_POOR_CALIBRATION",
        "disabled_reason": "INACTIVE_REJECTED_MODEL",
    }
    return view


def is_auto_eligible(strategy_id: str) -> bool:
    return bool(strategy_quarantine_view().get(strategy_id, {}).get("auto_eligible"))
