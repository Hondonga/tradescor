"""Phase 6: single authoritative validation-status model for every strategy.

This is the ONE place that answers "is this strategy eligible for Auto
routing / paper signals / live execution / ML filtering, and why not" for
the whole application. It supersedes the Phase 2 quarantine view (which
only understood technical reachability) by also incorporating the frozen
Phase 5 experimental verdict and the same conservative-by-default posture
for every other family that has never been formally walk-forward tested.

Reachability (can the engine construct a complete BUY/SELL plan) and
historical validation (has that plan been proven to hold a post-cost edge)
are deliberately different axes. A strategy can be fully reachable and
still be research-only -- "reachable does not mean validated".

Every other module that needs to know whether a strategy may enter Auto
routing, register a paper signal, run live, or drive an ML filter must
import from here rather than re-deriving its own eligibility logic.
"""
from __future__ import annotations

import json
from pathlib import Path

from analysis.strategy_reachability_gate import production_strategy_status, reachability_status
from validation.strategy_reachability_registry import strategy_reachability_registry

_ROOT = Path(__file__).resolve().parents[1]
_PHASE5_FROZEN_RECORD = (
    _ROOT / "data" / "stabilization" / "phase5" / "frozen"
    / "phase5-r75-vsp-walkforward-v1" / "experiment_record.json"
)
_PHASE6_START = _ROOT / "data" / "stabilization" / "phase6" / "baseline" / "phase6_start.json"

# The 17 required validation_status values (Phase 6 spec, Part 1). This is a
# closed vocabulary describing where a strategy sits in the validation
# pipeline. validation_verdict is a free-text specific reason and may use
# legacy/product wording (e.g. "NO_CONFIRMED_DIRECTIONAL_EDGE",
# "REJECTED_POOR_CALIBRATION") even when it does not literally match a
# validation_status value.
VALIDATION_STATES = frozenset({
    "NOT_TESTED",
    "REACHABILITY_ONLY",
    "VALIDATION_IN_PROGRESS",
    "REJECTED_INSUFFICIENT_HISTORY",
    "REJECTED_INSUFFICIENT_SAMPLE",
    "REJECTED_NO_EDGE_AFTER_COSTS",
    "REJECTED_NO_DIRECTIONAL_EDGE",
    "REJECTED_GEOMETRY_ONLY_EFFECT",
    "REJECTED_RANDOM_CONTROL",
    "REJECTED_UNSTABLE_ACROSS_FOLDS",
    "REJECTED_UNSTABLE_BY_DIRECTION",
    "REJECTED_EXCESSIVE_DRAWDOWN",
    "REJECTED_HOLDOUT_FAILURE",
    "ELIGIBLE_FOR_PAPER_SHADOW",
    "PAPER_SHADOW_IN_PROGRESS",
    "PAPER_SHADOW_REJECTED",
    "PAPER_SHADOW_PASSED",
})

REQUIRED_FIELDS = (
    "strategy_id", "market_family", "reachability_status", "validation_status", "validation_verdict",
    "historical_edge_proven", "profitability_claim_allowed", "auto_eligible", "paper_signal_allowed",
    "paper_shadow_eligible", "live_execution_allowed", "ml_filter_allowed", "research_only",
    "evidence_source", "experiment_id", "experiment_commit", "updated_at",
)

NO_VALIDATED_STRATEGY_MESSAGE = "No strategy for this market has passed the required historical validation."

# Required paper-signal block-reason codes (Phase 6 spec, Part 5).
BLOCK_REASON_REJECTED_NO_EDGE_AFTER_COSTS = "STRATEGY_REJECTED_NO_EDGE_AFTER_COSTS"
BLOCK_REASON_NOT_HISTORICALLY_VALIDATED = "STRATEGY_NOT_HISTORICALLY_VALIDATED"
BLOCK_REASON_RESEARCH_ONLY = "STRATEGY_RESEARCH_ONLY"
BLOCK_REASON_NOT_PAPER_ELIGIBLE = "STRATEGY_NOT_PAPER_ELIGIBLE"
BLOCK_REASON_NOT_PAPER_SHADOW_ELIGIBLE = "STRATEGY_NOT_PAPER_SHADOW_ELIGIBLE"

_DISABLED_ACTION_MESSAGE = "Disabled because this strategy has no verified post-cost edge."


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _phase6_started_at():
    record = _read_json(_PHASE6_START)
    return (record or {}).get("started_at") or "2026-07-23T00:00:00Z"


def _phase5_volatility_record():
    return _read_json(_PHASE5_FROZEN_RECORD)


def _phase5_final_commit():
    # experiment_record.json's own source_commit is the commit the freeze
    # script ran at (mid Phase 5); the frozen/reviewable Phase 5 endpoint --
    # and the commit Phase 6 actually branched from -- is phase6_start.json's
    # starting_commit. That is the value Phase 6 Part 2 requires here.
    record = _read_json(_PHASE6_START)
    return (record or {}).get("starting_commit") or "0b28f14f21cae5e8f450e2980ea3090ea3ce97a9"


def _reach_label(buy_reachable, sell_reachable):
    if buy_reachable and sell_reachable:
        return "REACHABLE_BOTH_DIRECTIONS"
    if buy_reachable:
        return "REACHABLE_BUY_ONLY"
    if sell_reachable:
        return "REACHABLE_SELL_ONLY"
    return "NOT_REACHABLE"


def _entry(
    strategy_id, market_family, *, buy_reachable, sell_reachable, validation_status,
    validation_verdict="", historical_edge_proven=False, profitability_claim_allowed=False,
    auto_eligible=False, paper_signal_allowed=False, paper_shadow_eligible=False,
    live_execution_allowed=False, ml_filter_allowed=False, research_only=True,
    evidence_source="", experiment_id=None, experiment_commit=None, disabled_reason="",
    updated_at=None, **extra,
):
    if validation_status not in VALIDATION_STATES:
        raise ValueError(f"{strategy_id}: {validation_status!r} is not a required validation_status value")
    entry = {
        "strategy_id": strategy_id,
        "market_family": market_family,
        "buy_reachable": bool(buy_reachable),
        "sell_reachable": bool(sell_reachable),
        "reachability_status": _reach_label(buy_reachable, sell_reachable),
        "validation_status": validation_status,
        "validation_verdict": validation_verdict,
        "historical_edge_proven": bool(historical_edge_proven),
        "profitability_claim_allowed": bool(profitability_claim_allowed),
        "auto_eligible": bool(auto_eligible),
        "paper_signal_allowed": bool(paper_signal_allowed),
        "paper_shadow_eligible": bool(paper_shadow_eligible),
        "live_execution_allowed": bool(live_execution_allowed),
        "ml_filter_allowed": bool(ml_filter_allowed),
        "research_only": bool(research_only),
        "evidence_source": evidence_source,
        "experiment_id": experiment_id,
        "experiment_commit": experiment_commit,
        "disabled_reason": disabled_reason,
        "updated_at": updated_at or _phase6_started_at(),
        # Backward-compatible alias consumed by older callers/tests.
        "production_supported": bool(auto_eligible),
    }
    entry.update(extra)
    return entry


def strategy_validation_registry() -> dict:
    """Returns {strategy_id: {...Part-1 required fields + extras}}.

    Covers every strategy the declarative reachability registry knows about
    (Volatility/Jump/Step/Boom-Crash), plus the Forex ICT and ML entries
    that have no counterpart there.
    """
    registry = strategy_reachability_registry()
    view = {}

    # -- Volatility family -------------------------------------------------
    phase5 = _phase5_volatility_record()
    for strategy_id, spec in registry.items():
        if spec["family"] != "VOLATILITY":
            continue
        status = production_strategy_status(strategy_id) if spec["production_supported"] else None
        reach = reachability_status(strategy_id)
        buy_reachable = bool(status and status["fixture_buy_reachable"])
        sell_reachable = bool(status and status["fixture_sell_reachable"])
        if strategy_id == "volatility_structure_pullback" and phase5:
            verdict = phase5["strategy_verdict"]
            view[strategy_id] = _entry(
                strategy_id, "volatility", buy_reachable=buy_reachable, sell_reachable=sell_reachable,
                validation_status="REJECTED_NO_EDGE_AFTER_COSTS", validation_verdict=verdict,
                historical_edge_proven=False, profitability_claim_allowed=False, auto_eligible=False,
                paper_signal_allowed=False, paper_shadow_eligible=False, live_execution_allowed=False,
                ml_filter_allowed=False, research_only=True, evidence_source="phase5_walk_forward",
                experiment_id=phase5["experiment_id"], experiment_commit=_phase5_final_commit(),
                disabled_reason=verdict, updated_at=phase5.get("generated_at"),
                validation_process_stage="COMPLETED",
            )
        else:
            # Other Volatility-family setups (liquidity reversal, range
            # reaction, breakout & retest): no frozen experiment exists for
            # any of them, so they default to NOT_TESTED like Step/Boom-Crash.
            view[strategy_id] = _entry(
                strategy_id, "volatility", buy_reachable=buy_reachable, sell_reachable=sell_reachable,
                validation_status="NOT_TESTED", disabled_reason=spec.get("support_status", "NOT_PRODUCTION_SUPPORTED"),
            )

    # -- Jump / JDBR ---------------------------------------------------------
    for strategy_id in ("jump_post_event_continuation", "jump_post_event_reversal"):
        if strategy_id not in registry:
            continue
        view[strategy_id] = _entry(
            strategy_id, "jump", buy_reachable=False, sell_reachable=False,
            validation_status="REJECTED_NO_DIRECTIONAL_EDGE", validation_verdict="NO_CONFIRMED_DIRECTIONAL_EDGE",
            disabled_reason="NO_CONFIRMED_DIRECTIONAL_EDGE",
        )

    # -- Step ------------------------------------------------------------
    for strategy_id in ("step_range_reaction", "step_structure_pullback", "step_breakout_and_retest"):
        if strategy_id not in registry:
            continue
        view[strategy_id] = _entry(
            strategy_id, "step", buy_reachable=False, sell_reachable=False,
            validation_status="NOT_TESTED", disabled_reason=registry[strategy_id].get("support_status", "NOT_PRODUCTION_SUPPORTED"),
        )

    # -- Boom/Crash --------------------------------------------------------
    for strategy_id in ("boom_crash_spike_state",):
        if strategy_id not in registry:
            continue
        view[strategy_id] = _entry(
            strategy_id, "boom_crash", buy_reachable=False, sell_reachable=False,
            validation_status="NOT_TESTED", disabled_reason=registry[strategy_id].get("support_status", "NOT_PRODUCTION_SUPPORTED"),
        )

    # -- Forex ICT (GBP/USD) -- has no entry in the Deriv-only declarative
    # registry, so it is defined here directly. Reachability was proven in
    # Phase 4 (both directions); historical validation has never been run.
    view["ict_2022"] = _entry(
        "ict_2022", "forex", buy_reachable=True, sell_reachable=True,
        validation_status="REACHABILITY_ONLY", validation_verdict="",
        disabled_reason="REACHABILITY_ONLY",
    )

    # -- Other generic Auto-router candidates (used across forex/crypto/
    # other derived families). Never formally tested; conservative default.
    for strategy_id in ("breakout_retest", "supply_demand"):
        view[strategy_id] = _entry(
            strategy_id, "cross_asset", buy_reachable=False, sell_reachable=False,
            validation_status="NOT_TESTED", disabled_reason="NOT_TESTED",
        )

    # -- ML ------------------------------------------------------------------
    view["ml"] = _entry(
        "ml", "ml", buy_reachable=False, sell_reachable=False,
        validation_status="REJECTED_NO_DIRECTIONAL_EDGE", validation_verdict="REJECTED_POOR_CALIBRATION",
        disabled_reason="INACTIVE_REJECTED_MODEL",
        model_status="REJECTED_POOR_CALIBRATION", live_activation_available=False,
        decision_owner_allowed=False, overlay_owner_allowed=False, filtering_allowed=False,
        recommendation_allowed=False,
    )

    return view


# Backward-compatible name used by earlier (Phase 2) callers and tests.
def strategy_quarantine_view() -> dict:
    return strategy_validation_registry()


def validation_entry(strategy_id: str) -> dict:
    """Returns the registry entry for strategy_id, or a safe unknown-strategy
    default (never eligible for anything) if it is not in the registry."""
    entry = strategy_validation_registry().get(strategy_id)
    if entry is not None:
        return entry
    return _entry(
        strategy_id, "unknown", buy_reachable=False, sell_reachable=False,
        validation_status="NOT_TESTED", disabled_reason="UNKNOWN_STRATEGY",
    )


def is_auto_eligible(strategy_id: str) -> bool:
    return bool(strategy_validation_registry().get(strategy_id, {}).get("auto_eligible"))


def is_paper_signal_allowed(strategy_id: str) -> bool:
    return bool(strategy_validation_registry().get(strategy_id, {}).get("paper_signal_allowed"))


def paper_signal_block_reason(strategy_id: str) -> str:
    """Returns one of the required STRATEGY_* block-reason codes explaining
    why strategy_id may not register a production paper signal right now."""
    entry = validation_entry(strategy_id)
    if entry["paper_signal_allowed"]:
        return ""
    if entry["validation_verdict"] == "REJECTED_NO_EDGE_AFTER_COSTS" or entry["validation_status"] == "REJECTED_NO_EDGE_AFTER_COSTS":
        return BLOCK_REASON_REJECTED_NO_EDGE_AFTER_COSTS
    if entry["research_only"]:
        return BLOCK_REASON_RESEARCH_ONLY
    if not entry["historical_edge_proven"]:
        return BLOCK_REASON_NOT_HISTORICALLY_VALIDATED
    if not entry["paper_shadow_eligible"]:
        return BLOCK_REASON_NOT_PAPER_SHADOW_ELIGIBLE
    return BLOCK_REASON_NOT_PAPER_ELIGIBLE


def strategy_evidence_contract(strategy_id: str) -> dict:
    """Builds the Phase 6 Part 6 `strategy_evidence` object for the
    normalized decision contract. Backend-authoritative; the frontend must
    not infer any of these values."""
    entry = validation_entry(strategy_id)
    if entry["research_only"] and not entry["historical_edge_proven"]:
        if entry["validation_verdict"]:
            summary = f"{strategy_id}: {entry['validation_verdict'].replace('_', ' ').lower()}."
        else:
            summary = f"{strategy_id}: historical validation not yet completed; research only."
    else:
        summary = f"{strategy_id}: historical edge proven."
    return {
        "reachability_status": entry["reachability_status"],
        "validation_status": entry["validation_status"],
        "validation_verdict": entry["validation_verdict"],
        "historical_edge_proven": entry["historical_edge_proven"],
        "profitability_claim_allowed": entry["profitability_claim_allowed"],
        "auto_eligible": entry["auto_eligible"],
        "paper_signal_allowed": entry["paper_signal_allowed"],
        "paper_shadow_eligible": entry["paper_shadow_eligible"],
        "live_execution_allowed": entry["live_execution_allowed"],
        "research_only": entry["research_only"],
        "experiment_id": entry["experiment_id"],
        "evidence_summary": summary,
    }


def product_actionability(strategy_id: str, *, lifecycle: str, plan_complete: bool) -> dict:
    """Phase 6 Part 14: explicit engine_readiness / product_actionability
    separation. Engine readiness (technical lifecycle) can never override
    validation eligibility -- an engine that reaches TRADE_READY on a
    rejected or unvalidated strategy is still not actionable."""
    entry = validation_entry(strategy_id)
    lifecycle = str(lifecycle or "").upper()
    validated_and_allowed = bool(entry["historical_edge_proven"] and not entry["research_only"])
    actionable = bool(lifecycle == "TRADE_READY" and plan_complete and validated_and_allowed)
    if actionable:
        status = "TRADE_READY"
    elif lifecycle == "TRADE_READY" and plan_complete:
        status = "RESEARCH_PLAN"
    elif "CONTEXT" in lifecycle or lifecycle in {"", "DATA_LOADING"}:
        status = "MARKET_CONTEXT"
    else:
        status = "RESEARCH_WATCH"
    blocker = None if actionable else (entry["validation_verdict"] or entry["validation_status"] or "NOT_HISTORICALLY_VALIDATED")
    return {
        "engine_readiness": {"lifecycle": lifecycle, "plan_complete": bool(plan_complete)},
        "product_actionability": {
            "actionable": actionable,
            "status": status,
            "blocker": blocker,
            "auto_allowed": entry["auto_eligible"],
            "paper_allowed": entry["paper_signal_allowed"],
            "live_allowed": entry["live_execution_allowed"],
        },
    }


def disabled_action_message() -> str:
    return _DISABLED_ACTION_MESSAGE
