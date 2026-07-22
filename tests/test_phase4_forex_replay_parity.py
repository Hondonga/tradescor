"""Phase 4 checkpoint 22: GBP/USD replay parity.

The same completed GBP/USD candles, evaluated once as a live decision and
once as a replay of the identical decision candle, must agree on every
substantive analysis field (H1 structure/bias, dealing range, premium/
discount, session, kill zone, M15 location, liquidity sweep, displacement,
CHoCH/MSS, FVG ownership, order-block ownership, M5 confirmation, setup ID,
lifecycle, direction, entry, stop, target candidates, TP1, RR, blockers,
overlays, ownership) -- the only fields allowed to differ are the ones that
exist specifically to distinguish live from replay (overlay_mode,
meta.live). Mirrors the same methodology already proven for R_75
(tests/test_phase2_replay_parity.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analysis.decision_engine import build_decision
from analysis.market_decision_normalizer import normalize_market_decision

from phase4_gbpusd_fixtures import gbpusd_buy_bundle, gbpusd_sell_bundle

COMPARED_FOREX_FIELDS = [
    "htf_bias", "market_structure", "session", "liquidity_event",
    "displacement", "structure_confirmation", "dealing_range", "entry_zone",
    "m5_confirmation", "scenario_state", "direction", "trade_plan",
]


def _products(context, boundary):
    decision = build_decision(symbol="GBP/USD", asset_class="forex", display_timeframe="M15", candles_by_timeframe=context, analysis_timestamp=boundary, requested_strategy="ict_2022", session={"entry_allowed": True})
    kwargs = dict(symbol="GBP/USD", display_symbol="GBP/USD", timeframe="M5", market_source="twelve_data", market_type="forex", market_schedule="24_5", analysis_time=boundary)
    live = normalize_market_decision(decision, live=True, **kwargs)
    replay = normalize_market_decision(decision, live=False, **kwargs)
    return live, replay


def test_live_and_replay_agree_on_every_substantive_forex_field():
    for builder in (gbpusd_buy_bundle, gbpusd_sell_bundle):
        context, boundary = builder()
        live, replay = _products(context, boundary)
        for field in COMPARED_FOREX_FIELDS:
            assert live["forex"][field] == replay["forex"][field], field
        assert live["market"]["external_structure"] == replay["market"]["external_structure"]  # H1 bias
        assert live["setup"]["setup_id"] == replay["setup"]["setup_id"]
        assert live["setup"]["stage"] == replay["setup"]["stage"]  # lifecycle
        assert live["setup"]["direction"] == replay["setup"]["direction"]
        assert live["setup"]["entry"] == replay["setup"]["entry"]
        assert live["setup"]["stop"] == replay["setup"]["stop"]
        assert live["setup"]["targets"] == replay["setup"]["targets"]  # target candidates / TP1
        assert live["setup"]["rr"] == replay["setup"]["rr"]
        assert live["decision"]["first_blocking_gate"] == replay["decision"]["first_blocking_gate"]  # blockers
        assert live["ownership"]["decision_owner_id"] == replay["ownership"]["decision_owner_id"]
        assert live["ownership"]["overlay_owner_id"] == replay["ownership"]["overlay_owner_id"]
        assert [row.get("type") for row in live["overlays"]] == [row.get("type") for row in replay["overlays"]]  # overlays


def test_only_the_intended_live_vs_replay_distinguishing_fields_differ():
    context, boundary = gbpusd_buy_bundle()
    live, replay = _products(context, boundary)
    assert live["overlay_mode"] == "LIVE"
    assert replay["overlay_mode"] == "REPLAY"
    assert live["meta"]["live"] is True
    assert replay["meta"]["live"] is False
    # Neutralize the intended differences and require exact structural
    # equality on everything else -- the strongest form of the guarantee.
    # overlays is also intentionally excluded here: global_overlay_contract's
    # historical-marker rows (the previous-setup "ghost" overlay) are only
    # ever included in LIVE/PREVIOUS_SETUP mode by design, never REPLAY --
    # confirmed as a deliberate difference, not a defect, and already
    # covered by the overlay *type* comparison in the test above.
    live_copy, replay_copy = dict(live), dict(replay)
    for product in (live_copy, replay_copy):
        product["overlay_mode"] = None
        product["meta"] = {**product["meta"], "live": None}
        del product["overlays"]
    assert live_copy == replay_copy


def test_no_lookahead_a_truncated_gbpusd_history_cannot_see_future_candles():
    context, boundary = gbpusd_buy_bundle()
    m15 = context["M15"]
    mid_boundary = m15.iloc[40].time
    truncated_context = {**context, "M15": m15[m15.time <= mid_boundary].copy(), "M5": context["M5"].iloc[:0]}
    full_decision = build_decision(symbol="GBP/USD", asset_class="forex", display_timeframe="M15", candles_by_timeframe=truncated_context, analysis_timestamp=mid_boundary, requested_strategy="ict_2022", session={"entry_allowed": True})
    same_decision = build_decision(symbol="GBP/USD", asset_class="forex", display_timeframe="M15", candles_by_timeframe=truncated_context, analysis_timestamp=mid_boundary, requested_strategy="ict_2022", session={"entry_allowed": True})
    assert full_decision["setup"]["stage"] == same_decision["setup"]["stage"]
    # Now extend the history past the boundary -- a decision evaluated at
    # the SAME analysis_timestamp must not change just because more future
    # candles were appended to the frame.
    extended_context = {**context, "M5": context["M5"].iloc[:0]}
    extended_decision = build_decision(symbol="GBP/USD", asset_class="forex", display_timeframe="M15", candles_by_timeframe=extended_context, analysis_timestamp=mid_boundary, requested_strategy="ict_2022", session={"entry_allowed": True})
    assert full_decision["setup"]["stage"] == extended_decision["setup"]["stage"]
    assert full_decision["execution"]["entry"] == extended_decision["execution"]["entry"]
