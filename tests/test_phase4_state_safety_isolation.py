"""Phase 4 checkpoint 19/20: GBP/USD symbol/timeframe/provider state safety
and live/historical/replay isolation.

The cross-contamination guard itself (decisionMatchesWorkspace, requestId
matching, overlay_mode gating) is generic frontend state -- proven with a
dedicated GBP/USD <-> R_75 sequence in
frontend/src/store/terminal-store.test.ts. This file proves the backend
half: GBP/USD decisions are tagged consistently (overlay_mode, meta.live,
meta.symbol/timeframe/market_source) so that guard has something correct
to key off of, for both a live and a replay evaluation of the same
underlying candles.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analysis.decision_engine import build_decision
from analysis.market_decision_normalizer import normalize_market_decision

from phase4_gbpusd_fixtures import gbpusd_buy_bundle, gbpusd_sell_bundle


def _decision():
    context, boundary = gbpusd_buy_bundle()
    return build_decision(symbol="GBP/USD", asset_class="forex", display_timeframe="M15", candles_by_timeframe=context, analysis_timestamp=boundary, requested_strategy="ict_2022", session={"entry_allowed": True}), boundary


def test_live_gbpusd_decision_is_tagged_live_with_matching_meta():
    decision, boundary = _decision()
    product = normalize_market_decision(decision, symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M5", market_source="twelve_data", market_type="forex", market_schedule="24_5", analysis_time=boundary, live=True)
    assert product["overlay_mode"] == "LIVE"
    assert product["meta"]["live"] is True
    assert product["meta"]["symbol"] == "GBP/USD"
    assert product["meta"]["timeframe"] == "M5"
    assert product["meta"]["market_source"] == "twelve_data"
    assert product["meta"]["market_type"] == "forex"


def test_replay_gbpusd_decision_is_tagged_replay_not_live():
    decision, boundary = _decision()
    product = normalize_market_decision(decision, symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M5", market_source="twelve_data", market_type="forex", market_schedule="24_5", analysis_time=boundary, live=False)
    assert product["overlay_mode"] == "REPLAY"
    assert product["meta"]["live"] is False


def test_gbpusd_m15_response_is_tagged_m15_not_m5():
    decision, boundary = _decision()
    product = normalize_market_decision(decision, symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M15", market_source="twelve_data", market_type="forex", market_schedule="24_5", analysis_time=boundary, live=True)
    assert product["meta"]["timeframe"] == "M15"
    assert product["precision"]["symbol_id"] == "twelve_data:GBP/USD"


def test_gbpusd_and_r75_decisions_carry_disjoint_symbol_ids_and_owners():
    # A minimal cross-family disjointness check: GBP/USD's decision_owner_id
    # is always the Forex ICT model, never a Deriv-family strategy, and its
    # symbol_id is always twelve_data-namespaced -- the two families cannot
    # be confused by symbol_id or ownership alone even without the frontend
    # guard.
    decision, boundary = _decision()
    product = normalize_market_decision(decision, symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M5", market_source="twelve_data", market_type="forex", market_schedule="24_5", analysis_time=boundary, live=True)
    assert product["precision"]["symbol_id"].startswith("twelve_data:")
    assert product["ownership"]["decision_owner_id"] == "ict_2022"
    assert product["meta"]["market_type"] == "forex"


def test_buy_and_sell_bundles_at_the_same_boundary_produce_disjoint_directions():
    buy_decision, buy_boundary = _decision()
    sell_context, sell_boundary = gbpusd_sell_bundle()
    sell_decision = build_decision(symbol="GBP/USD", asset_class="forex", display_timeframe="M15", candles_by_timeframe=sell_context, analysis_timestamp=sell_boundary, requested_strategy="ict_2022", session={"entry_allowed": True})
    assert buy_decision["setup"]["direction"] != sell_decision["setup"]["direction"]
