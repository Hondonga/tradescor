"""Phase 4 checkpoint 21 -- Forex paper-testing safety gate.

A minimal, Forex-named eligibility check analogous to
paper_testing/derived_setup_tracker.py::registerable_paper_setup(). Built on
top of -- not duplicating -- the shared, already-correct
analysis/global_overlay_contract.py::normalize_global_decision gate
(overlay_mode == "LIVE", complete trade-ready geometry, no lifecycle
contradiction, readiness == "ready"). Re-asserting those conditions here is
deliberate defense in depth, not a second source of truth: this function
never grants eligibility the shared gate denied, it only ever narrows.

Phase 4 proves reachability and contract correctness only -- it never
proves historical edge, backtested profitability, or live-execution
readiness -- so those three claims are always recorded False, regardless of
eligibility.
"""
from __future__ import annotations


def registerable_forex_paper_setup(product: dict) -> dict:
    decision = product.get("decision") or {}
    setup = product.get("active_setup") or {}
    meta = product.get("meta") or {}
    readiness = str((product.get("readiness") or {}).get("state") or "").lower()
    has_tp1 = any(str((row or {}).get("name") or "").lower() == "tp1" for row in setup.get("targets") or [])
    eligible = bool(
        product.get("paper_registration_allowed")
        and product.get("overlay_mode") == "LIVE"
        and meta.get("market_type") == "forex"
        and decision.get("trade_ready") is True
        and readiness == "ready"
        and setup.get("setup_id")
        and setup.get("entry") is not None
        and setup.get("stop") is not None
        and has_tp1
    )
    reason = None
    if not eligible:
        if product.get("overlay_mode") != "LIVE":
            reason = "Overlay mode is not LIVE (replay/historical inspection is never paper-eligible)."
        elif meta.get("market_type") != "forex":
            reason = "Not a Forex decision."
        elif readiness != "ready":
            reason = f"Data is not live-ready (readiness={readiness})."
        elif not decision.get("trade_ready"):
            reason = "Decision has not reached TRADE_READY."
        else:
            reason = "No active setup with complete entry/stop/TP1 geometry."
    return {
        "eligible": eligible,
        "reason": reason,
        "historical_edge_proven": False,
        "profitability_claim_allowed": False,
        "live_execution_allowed": False,
    }
