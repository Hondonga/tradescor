"""Phase 2 checkpoint 13: replay parity for the R_75 golden path. The same
completed candles, run through two independent invocations (simulating a
live request and a replay request), must produce field-for-field identical
decisions -- and a request missing the final (forming) candles must never
see a result influenced by candles it wasn't given.
"""
from replay.derived_replay_validator import parity_report
from validation.strategy_reachability_fixtures import _focused_frames
from analysis.volatility_structure_pullback_engine import evaluate_volatility_structure_pullback

COMPARED_SETUP_FIELDS = [
    "setup_id", "stage", "direction", "entry", "stop", "targets", "rr",
    "target_source", "target_timeframe", "next_required_condition",
]


def _run(direction):
    frames = _focused_frames(direction)
    at = frames["M5"].iloc[-1].time
    return evaluate_volatility_structure_pullback(
        symbol="R_75", display_symbol="Volatility 75 Index",
        candles_by_timeframe=frames, tick_size=.01, analysis_time=at,
    )


def test_live_and_replay_style_invocations_match_on_every_required_field():
    for direction in ("buy", "sell"):
        live = _run(direction)
        replay = _run(direction)  # independent call, same inputs -> "replay" framing
        assert live["market"]["external_structure"] == replay["market"]["external_structure"]  # H1 structure
        assert live["diagnostics"]["m15"]["pullback"] == replay["diagnostics"]["m15"]["pullback"]  # M15 pullback
        assert live["diagnostics"]["m5"]["confirmation"] == replay["diagnostics"]["m5"]["confirmation"]  # M5 confirmation
        for field in COMPARED_SETUP_FIELDS:
            assert live["setup"][field] == replay["setup"][field], field
        assert live["decision"]["direction"] == replay["decision"]["direction"]
        assert live["decision"]["stage"] == replay["decision"]["stage"]
        assert live["decision"]["first_blocking_gate"] == replay["decision"]["first_blocking_gate"]
        assert live["ownership"]["decision_owner_id"] == replay["ownership"]["decision_owner_id"]
        assert live["ownership"]["overlay_owner_id"] == replay["ownership"]["overlay_owner_id"]
        assert live == replay  # exact structural equality as the strongest form of the same guarantee


def test_parity_report_utility_flags_a_real_divergence():
    a = _run("buy")
    b = _run("sell")
    result = parity_report(a, b)
    assert result["parity"] is False


def test_no_lookahead_truncated_history_cannot_see_future_candles():
    frames = _focused_frames("sell")
    at = frames["M5"].iloc[100].time  # decision time mid-series
    full = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=frames, tick_size=.01, analysis_time=at)
    truncated_frames = {k: v[v.time <= at].copy() for k, v in frames.items()}
    truncated = evaluate_volatility_structure_pullback(symbol="R_75", candles_by_timeframe=truncated_frames, tick_size=.01, analysis_time=at)
    assert full["setup"]["entry"] == truncated["setup"]["entry"]
    assert full["setup"]["stop"] == truncated["setup"]["stop"]
    assert full["decision"]["stage"] == truncated["decision"]["stage"]
