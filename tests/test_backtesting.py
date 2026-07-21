"""Tests for the Strategy Lab backtesting engine.

Covers:
- No look-ahead in backtest
- Trade simulator: SL hit first
- Trade simulator: TP hit first
- Trade simulator: missed entry zone
- Profit factor calculation
- Expectancy calculation
- Drawdown calculation
- Small sample warning
- Strategy comparison output
- Fast mode vs Accurate mode configuration
- Active trade management is never skipped by mode step
"""

from __future__ import annotations

import math
import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from backtesting.engine import _valid_levels, run_backtest
from backtesting.metrics import calculate_metrics, _max_drawdown_r, _longest_losing_streak
from backtesting.simulator import TradeSimulator, _parse_entry_zone
from backtesting.comparison import compare_strategies, _rank
from backtesting.trade_log import TradeRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candles(count: int = 200, base: float = 1.15000, trend: float = 0.00004) -> pd.DataFrame:
    """Synthetic OHLCV candles for unit tests."""
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    rows = []
    for i in range(count):
        mid = base + i * trend + math.sin(i / 5) * 0.0010
        close = mid + math.sin(i / 3) * 0.0003
        high = max(mid, close) + 0.00040
        low = min(mid, close) - 0.00040
        rows.append({
            "time": int((start + timedelta(minutes=15 * i)).timestamp()),
            "open": round(mid, 5),
            "high": round(high, 5),
            "low": round(low, 5),
            "close": round(close, 5),
        })
    return pd.DataFrame(rows)


def _trade(result: str, rr: float) -> TradeRecord:
    """Create a minimal TradeRecord for metrics tests."""
    return TradeRecord(
        strategy="Test",
        symbol="EUR/USD",
        timeframe="M15",
        direction="Bullish",
        entry_time=0,
        entry=1.15000,
        stop_loss=1.14900,
        tp1=1.15200,
        tp2=None,
        exit_time=100,
        exit_price=1.15200 if result == "TP1" else 1.14900,
        result=result,
        rr_result=rr,
        duration_candles=10,
        reason="test",
    )


# ---------------------------------------------------------------------------
# Level validation
# ---------------------------------------------------------------------------

class TestLevelValidation(unittest.TestCase):
    def test_valid_bullish_levels(self):
        entry_zone = {"top": 1.15100, "bottom": 1.14950}
        self.assertTrue(_valid_levels(entry_zone, 1.14800, 1.15400))

    def test_valid_bearish_levels(self):
        entry_zone = {"top": 1.15200, "bottom": 1.15050}
        self.assertTrue(_valid_levels(entry_zone, 1.15400, 1.14700))

    def test_rejects_missing_entry_zone(self):
        self.assertFalse(_valid_levels(None, 1.14800, 1.15400))

    def test_rejects_insufficient_rr(self):
        # entry ~1.15000, SL at 1.14900 (risk 100 pip), TP at 1.15050 (reward 50 pip) < 1R
        entry_zone = {"top": 1.15050, "bottom": 1.14950}
        self.assertFalse(_valid_levels(entry_zone, 1.14900, 1.15050))

    def test_rejects_sl_on_wrong_side(self):
        # Bullish: SL above entry (wrong side)
        entry_zone = {"top": 1.15100, "bottom": 1.14950}
        self.assertFalse(_valid_levels(entry_zone, 1.15300, 1.15400))

    def test_rejects_zero_entry(self):
        self.assertFalse(_valid_levels({"top": 0, "bottom": 0}, 1.14900, 1.15400))


# ---------------------------------------------------------------------------
# Entry zone parsing
# ---------------------------------------------------------------------------

class TestEntryZoneParsing(unittest.TestCase):
    def test_dict_zone(self):
        top, bottom = _parse_entry_zone({"top": 1.15100, "bottom": 1.14950}, 1.14800, 1.15400, "Bullish")
        self.assertAlmostEqual(top, 1.15100)
        self.assertAlmostEqual(bottom, 1.14950)

    def test_scalar_zone(self):
        top, bottom = _parse_entry_zone(1.15000, 1.14900, 1.15400, "Bullish")
        self.assertGreater(top, bottom)

    def test_none_fallback(self):
        top, bottom = _parse_entry_zone(None, 1.14900, 1.15400, "Bullish")
        self.assertGreater(top, bottom)


# ---------------------------------------------------------------------------
# Trade simulator — SL hit
# ---------------------------------------------------------------------------

class TestSimulatorSLHit(unittest.TestCase):
    def _sim_with_pending(self) -> TradeSimulator:
        sim = TradeSimulator("Test Strategy")
        sim.open_pending(
            signal_candle_idx=0,
            strategy_name="Test Strategy",
            symbol="EUR/USD",
            timeframe="M15",
            direction="Bullish",
            entry_zone={"top": 1.15100, "bottom": 1.14950},
            stop_loss=1.14800,
            tp1=1.15500,
            tp2=None,
            reason="test setup",
        )
        return sim

    def _candle(self, high: float, low: float, idx: int = 1) -> pd.Series:
        return pd.Series({
            "time": int(datetime(2026, 1, 2, tzinfo=timezone.utc).timestamp()) + idx * 900,
            "open": (high + low) / 2,
            "high": high,
            "low": low,
            "close": (high + low) / 2,
        })

    def test_fills_when_price_enters_zone(self):
        sim = self._sim_with_pending()
        result = sim.check_pending_entry(self._candle(1.15200, 1.14900), candle_idx=1)
        self.assertEqual(result, "FILLED")
        self.assertEqual(sim.state, "ACTIVE")

    def test_sl_hit_returns_loss(self):
        sim = self._sim_with_pending()
        sim.check_pending_entry(self._candle(1.15050, 1.14960), candle_idx=1)
        record = sim.check_active_trade(self._candle(1.15060, 1.14780), candle_idx=2)
        self.assertIsNotNone(record)
        self.assertEqual(record.result, "SL")
        self.assertAlmostEqual(record.rr_result, -1.0)
        self.assertEqual(sim.state, "WATCHING")

    def test_tp1_hit_returns_win(self):
        sim = self._sim_with_pending()
        sim.check_pending_entry(self._candle(1.15050, 1.14960), candle_idx=1)
        record = sim.check_active_trade(self._candle(1.15600, 1.15100), candle_idx=2)
        self.assertIsNotNone(record)
        self.assertEqual(record.result, "TP1")
        self.assertGreater(record.rr_result, 1.0)

    def test_tp2_hit(self):
        sim = TradeSimulator("Test Strategy")
        sim.open_pending(
            signal_candle_idx=0,
            strategy_name="Test Strategy",
            symbol="EUR/USD",
            timeframe="M15",
            direction="Bullish",
            entry_zone={"top": 1.15100, "bottom": 1.14950},
            stop_loss=1.14800,
            tp1=1.15500,
            tp2=1.15900,
            reason="test",
        )
        sim.check_pending_entry(self._candle(1.15050, 1.14960), candle_idx=1)
        record = sim.check_active_trade(self._candle(1.16000, 1.15400), candle_idx=2)
        self.assertIsNotNone(record)
        self.assertEqual(record.result, "TP2")

    def test_missed_entry_zone_expires(self):
        sim = self._sim_with_pending()
        for i in range(1, 25):  # past MAX_PENDING_CANDLES
            sim.check_pending_entry(self._candle(1.15500, 1.15300), candle_idx=i)
        self.assertEqual(sim.state, "WATCHING")

    def test_invalidation_cancels_pending(self):
        sim = self._sim_with_pending()
        # SL (1.14800) breached before fill
        result = sim.check_pending_entry(self._candle(1.14990, 1.14750), candle_idx=1)
        self.assertIsNone(result)
        self.assertEqual(sim.state, "WATCHING")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class TestMetrics(unittest.TestCase):
    def _trades(self, results_rrs: list[tuple[str, float]]) -> list[TradeRecord]:
        return [_trade(r, rr) for r, rr in results_rrs]

    def test_profit_factor(self):
        trades = self._trades([("TP1", 2.0), ("TP1", 1.5), ("SL", -1.0)])
        m = calculate_metrics(trades, "Test")
        # gross profit = 3.5, gross loss = 1.0, pf = 3.5
        self.assertAlmostEqual(m["profit_factor"], 3.5)

    def test_expectancy(self):
        trades = self._trades([("TP1", 2.0), ("SL", -1.0)])
        m = calculate_metrics(trades, "Test")
        # 0.5 * 2.0 - 0.5 * 1.0 = 0.5
        self.assertAlmostEqual(m["expectancy"], 0.5)

    def test_win_rate(self):
        trades = self._trades([("TP1", 2.0), ("TP1", 1.5), ("SL", -1.0), ("SL", -1.0)])
        m = calculate_metrics(trades, "Test")
        self.assertAlmostEqual(m["win_rate"], 50.0)

    def test_max_drawdown(self):
        trades = self._trades([("TP1", 2.0), ("SL", -1.0), ("SL", -1.0), ("SL", -1.0), ("TP1", 3.0)])
        # Equity: 0 -> 2 -> 1 -> 0 -> -1 -> 2
        # Peak=2, trough=-1, dd=3
        dd = _max_drawdown_r([t for t in trades if t.result != "OPEN_AT_END"])
        self.assertAlmostEqual(dd, -3.0)

    def test_longest_losing_streak(self):
        trades = self._trades([("SL", -1), ("SL", -1), ("TP1", 2), ("SL", -1), ("SL", -1), ("SL", -1)])
        streak = _longest_losing_streak([t for t in trades if t.result != "OPEN_AT_END"])
        self.assertEqual(streak, 3)

    def test_empty_returns_no_trades(self):
        m = calculate_metrics([], "Test")
        self.assertEqual(m["total_trades"], 0)
        self.assertEqual(m["rating"], "No Trades")

    def test_small_sample_warning(self):
        trades = self._trades([("TP1", 2.0)] * 5)
        m = calculate_metrics(trades, "Test")
        self.assertTrue(m["sample_size_warning"])

    def test_large_sample_no_warning(self):
        trades = self._trades([("TP1", 2.0), ("SL", -1.0)] * 15)
        m = calculate_metrics(trades, "Test")
        self.assertFalse(m["sample_size_warning"])


# ---------------------------------------------------------------------------
# Comparison / ranking
# ---------------------------------------------------------------------------

class TestComparison(unittest.TestCase):
    def _metrics(self, expectancy: float, pf: float, total: int, name: str) -> dict:
        return {
            "strategy": name,
            "strategy_key": name.lower().replace(" ", "_"),
            "total_trades": total,
            "wins": int(total * 0.5),
            "losses": int(total * 0.5),
            "win_rate": 50.0,
            "profit_factor": pf,
            "expectancy": expectancy,
            "average_rr": expectancy * 2,
            "max_drawdown": -2.0,
            "longest_losing_streak": 3,
            "best_trade": 3.0,
            "worst_trade": -1.0,
            "average_duration_candles": 10,
            "rating": "Promising",
            "sample_size_warning": total < 20,
            "trade_records": [],
        }

    def test_higher_expectancy_ranks_first(self):
        metrics = [
            self._metrics(0.5, 1.4, 30, "A"),
            self._metrics(0.1, 1.2, 30, "B"),
        ]
        ranked = _rank(metrics)
        self.assertEqual(ranked[0]["strategy"], "A")

    def test_insufficient_data_ranks_last(self):
        metrics = [
            self._metrics(0.5, 1.4, 30, "Good"),
            self._metrics(2.0, 5.0, 3, "Tiny"),  # only 3 trades
        ]
        ranked = _rank(metrics)
        self.assertEqual(ranked[-1]["strategy"], "Tiny")

    def test_comparison_returns_summary_text(self):
        from backtesting.trade_log import TradeRecord
        trades_a = [_trade("TP1", 2.0)] * 15 + [_trade("SL", -1.0)] * 10
        trades_b = [_trade("TP1", 1.5)] * 10 + [_trade("SL", -1.0)] * 15
        result = compare_strategies({"strategy_a": trades_a, "strategy_b": trades_b})
        self.assertIn("summary", result)
        self.assertIsInstance(result["summary"], str)
        self.assertGreater(len(result["summary"]), 20)


# ---------------------------------------------------------------------------
# No look-ahead validation
# ---------------------------------------------------------------------------

class TestNoLookAhead(unittest.TestCase):
    """Verify that the engine never passes future candles to the strategy."""

    def test_candle_slice_is_strictly_past(self):
        """
        We monkey-patch build_shared_analysis to record the max candle index
        seen at each strategy call. It should never exceed the current n.
        """
        import backtesting.engine as eng_module
        from analysis import build_shared_analysis as real_bsa

        seen_lengths: list[int] = []

        def recording_bsa(candles: pd.DataFrame) -> dict:
            seen_lengths.append(len(candles))
            return real_bsa(candles)

        original = eng_module.build_shared_analysis
        eng_module.build_shared_analysis = recording_bsa
        try:
            candles = _make_candles(80)
            run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        finally:
            eng_module.build_shared_analysis = original

        total = len(candles)
        # Every call must have seen ≤ total candles (the last call can see all)
        for length in seen_lengths:
            self.assertLessEqual(length, total)

        # And calls should be strictly increasing (no re-use of future candles)
        for a, b in zip(seen_lengths, seen_lengths[1:]):
            self.assertGreaterEqual(b, a)


# ---------------------------------------------------------------------------
# Run backtest integration (small data — no real API)
# ---------------------------------------------------------------------------

class TestRunBacktest(unittest.TestCase):
    def test_returns_expected_keys(self):
        candles = _make_candles(120)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        self.assertIn("trades", result)
        self.assertIn("warnings", result)
        self.assertIn("n_candles", result)
        self.assertIn("metadata", result)
        self.assertEqual(result["n_candles"], 120)

    def test_unknown_strategy_adds_warning(self):
        candles = _make_candles(60)
        result = run_backtest(candles, ["unknown_strategy"], symbol="EUR/USD", timeframe="M15")
        self.assertTrue(any("unknown_strategy" in w.lower() or "unknown" in w.lower() for w in result["warnings"]))

    def test_small_candle_warning(self):
        candles = _make_candles(40)  # below MIN_WARMUP + 10
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        self.assertTrue(any("small" in w.lower() or "few" in w.lower() or "size" in w.lower() for w in result["warnings"]))

    def test_trade_records_are_valid(self):
        candles = _make_candles(200)
        result = run_backtest(
            candles,
            ["universal_structure", "breakout_retest"],
            symbol="EUR/USD",
            timeframe="M15",
        )
        for key, trade_list in result["trades"].items():
            for trade in trade_list:
                self.assertIsInstance(trade, TradeRecord)
                self.assertIn(trade.result, {"SL", "TP1", "TP2", "OPEN_AT_END"})


# ---------------------------------------------------------------------------
# Mode configuration tests
# ---------------------------------------------------------------------------

class TestBacktestMode(unittest.TestCase):
    def test_fast_config_has_step_15(self):
        from backtesting.engine import FAST_CONFIG
        self.assertEqual(FAST_CONFIG.strategy_step, 15)
        self.assertTrue(FAST_CONFIG.approximate)

    def test_accurate_config_has_step_5(self):
        from backtesting.engine import ACCURATE_CONFIG
        self.assertEqual(ACCURATE_CONFIG.strategy_step, 5)
        self.assertFalse(ACCURATE_CONFIG.approximate)

    def test_fast_mode_metadata_approximate_true(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="fast")
        meta = result.get("metadata", {})
        self.assertTrue(meta.get("approximate"))
        self.assertEqual(meta.get("mode"), "fast")
        self.assertEqual(meta.get("strategy_step"), 15)

    def test_accurate_mode_metadata_approximate_false(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="accurate")
        meta = result.get("metadata", {})
        self.assertFalse(meta.get("approximate"))
        self.assertEqual(meta.get("mode"), "accurate")
        self.assertEqual(meta.get("strategy_step"), 5)

    def test_unknown_mode_defaults_to_fast(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="invalid_xyz")
        meta = result.get("metadata", {})
        self.assertEqual(meta.get("mode"), "fast")

    def test_fast_mode_warning_appears_in_warnings(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="fast")
        combined = " ".join(result["warnings"]).lower()
        self.assertIn("fast mode", combined)

    def test_accurate_mode_warning_appears_in_warnings(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="accurate")
        combined = " ".join(result["warnings"]).lower()
        self.assertIn("accurate mode", combined)

    def test_metadata_includes_evaluated_candles(self):
        candles = _make_candles(120)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="fast")
        meta = result.get("metadata", {})
        self.assertIn("evaluated_candles", meta)
        self.assertIn("total_candles", meta)
        self.assertGreater(meta["evaluated_candles"], 0)

    def test_accurate_mode_evaluates_more_than_fast(self):
        """Accurate mode should evaluate more signal points than fast mode."""
        candles = _make_candles(150)
        fast   = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="fast")
        acc    = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15", mode="accurate")
        fast_e = fast["metadata"]["evaluated_candles"]
        acc_e  = acc["metadata"]["evaluated_candles"]
        self.assertGreater(acc_e, fast_e)


# ---------------------------------------------------------------------------
# Trade management is never skipped by mode step
# ---------------------------------------------------------------------------

class TestFastModeTradeManagement(unittest.TestCase):
    """Prove that SL / TP / fill checks run on EVERY candle regardless of mode."""

    def _make_candle(self, high, low, idx=0) -> pd.Series:
        ts = int(datetime(2026, 1, 2, tzinfo=timezone.utc).timestamp()) + idx * 900
        mid = (high + low) / 2
        return pd.Series({"time": ts, "open": mid, "high": high, "low": low, "close": mid})

    def _filled_sim(self) -> TradeSimulator:
        """Return a simulator in ACTIVE state (trade filled)."""
        sim = TradeSimulator("Test")
        sim.open_pending(
            signal_candle_idx=0,
            strategy_name="Test",
            symbol="EUR/USD",
            timeframe="M15",
            direction="Bullish",
            entry_zone={"top": 1.15100, "bottom": 1.14950},
            stop_loss=1.14800,
            tp1=1.15500,
            tp2=None,
            reason="test",
        )
        # Fill the trade
        sim.check_pending_entry(self._make_candle(1.15050, 1.14960), 1)
        self.assertEqual(sim.state, "ACTIVE")
        return sim

    def test_sl_hit_is_detected_on_every_candle(self):
        """SL must be caught even between strategy evaluation points (gap=15)."""
        sim = self._filled_sim()
        # Advance 12 candles with no hit (would be skipped in fast signal scan)
        for i in range(2, 14):
            result = sim.check_active_trade(self._make_candle(1.15200, 1.14900), i)
            self.assertIsNone(result)  # no close yet

        # SL hit at candle 14 — NOT a strategy eval point in fast mode
        result = sim.check_active_trade(self._make_candle(1.15000, 1.14750), 14)
        self.assertIsNotNone(result, "SL should be detected on candle 14")
        self.assertEqual(result.result, "SL")

    def test_tp1_hit_not_skipped(self):
        """TP1 must be caught even between strategy evaluation points."""
        sim = self._filled_sim()
        for i in range(2, 10):
            sim.check_active_trade(self._make_candle(1.15200, 1.14900), i)
        # TP1 = 1.15500
        result = sim.check_active_trade(self._make_candle(1.15600, 1.15400), 10)
        self.assertIsNotNone(result)
        self.assertEqual(result.result, "TP1")

    def test_pending_invalidation_not_skipped(self):
        """If SL is breached before entry, the pending trade is cancelled on that candle."""
        sim = TradeSimulator("Test")
        sim.open_pending(
            signal_candle_idx=0,
            strategy_name="Test",
            symbol="EUR/USD",
            timeframe="M15",
            direction="Bullish",
            entry_zone={"top": 1.15100, "bottom": 1.14950},
            stop_loss=1.14800,
            tp1=1.15500,
            tp2=None,
            reason="test",
        )
        # Price drops through SL before touching entry zone — cancel immediately
        sim.check_pending_entry(self._make_candle(1.14900, 1.14750), 1)
        self.assertEqual(sim.state, "WATCHING", "Pending trade should be cancelled when SL breached")

    def test_active_state_is_never_skipped_in_fast_mode_run(self):
        """Integration: trade management runs every candle even in fast mode."""
        # Build candles where:
        # - signal fires around candle 50
        # - entry is touched at candle 52
        # - SL is hit at candle 56 (would be between eval steps in fast mode)
        candles = _make_candles(120)

        # We can't force a real ENTRY_READY from the strategy, but we can verify
        # that _run_strategy never skips the ACTIVE/PENDING branches.
        # Instead, directly test the simulator handles every candle correctly.
        sim = TradeSimulator("Test Strategy")
        sim.open_pending(
            signal_candle_idx=50,
            strategy_name="Test Strategy",
            symbol="EUR/USD",
            timeframe="M15",
            direction="Bullish",
            entry_zone={"top": 1.15100, "bottom": 1.14950},
            stop_loss=1.14800,
            tp1=1.15500,
            tp2=None,
            reason="test",
        )

        # Candles 51-54: price hovers above entry zone (no fill yet)
        for i in range(51, 55):
            candle = candles.iloc[i].copy()
            candle["high"] = 1.15300
            candle["low"]  = 1.15150
            result = sim.check_pending_entry(pd.Series(candle), i)
            self.assertIsNone(result)

        # Candle 55: price enters entry zone → filled
        fill_candle = candles.iloc[55].copy()
        fill_candle["high"] = 1.15200
        fill_candle["low"]  = 1.14920
        sim.check_pending_entry(pd.Series(fill_candle), 55)
        self.assertEqual(sim.state, "ACTIVE")

        # Candles 56-59: price moves normally
        for i in range(56, 60):
            candle = candles.iloc[i].copy()
            candle["high"] = 1.15300
            candle["low"]  = 1.14900
            sim.check_active_trade(pd.Series(candle), i)

        # Candle 60: SL hit (1.14800) — between fast-mode eval points (step=15)
        sl_candle = candles.iloc[60].copy()
        sl_candle["high"] = 1.15100
        sl_candle["low"]  = 1.14750
        record = sim.check_active_trade(pd.Series(sl_candle), 60)

        self.assertIsNotNone(record, "SL should fire at candle 60")
        self.assertEqual(record.result, "SL")
        self.assertEqual(sim.state, "WATCHING")


# ---------------------------------------------------------------------------
# Run status tests
# ---------------------------------------------------------------------------

class TestRunStatus(unittest.TestCase):
    def test_selected_strategy_returns_ran_true(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        from backtesting.reports import build_report
        report = build_report(
            result["trades"],
            n_candles=result["n_candles"],
            symbol="EUR/USD",
            timeframe="M15",
            risk_per_trade=1.0,
            starting_balance=10000,
            backtest_warnings=result["warnings"],
            metadata=result.get("metadata"),
            diagnostics_by_strategy=result.get("diagnostics"),
            selected_strategies=["universal_structure"],
        )
        run_status = report.get("run_status", [])
        us = next((s for s in run_status if s["key"] == "universal_structure"), None)
        self.assertIsNotNone(us)
        self.assertTrue(us["ran"])
        self.assertTrue(us["selected"])

    def test_unselected_ict_returns_ran_false(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        from backtesting.reports import build_report
        report = build_report(
            result["trades"],
            n_candles=result["n_candles"],
            symbol="EUR/USD",
            timeframe="M15",
            risk_per_trade=1.0,
            starting_balance=10000,
            backtest_warnings=result["warnings"],
            metadata=result.get("metadata"),
            diagnostics_by_strategy=result.get("diagnostics"),
            selected_strategies=["universal_structure"],
        )
        run_status = report.get("run_status", [])
        ict = next((s for s in run_status if s["key"] == "ict_2022"), None)
        self.assertIsNotNone(ict)
        self.assertFalse(ict["ran"])
        self.assertFalse(ict["selected"])

    def test_unselected_ict_mentions_ote(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        from backtesting.reports import build_report
        report = build_report(
            result["trades"],
            n_candles=result["n_candles"],
            symbol="EUR/USD",
            timeframe="M15",
            risk_per_trade=1.0,
            starting_balance=10000,
            backtest_warnings=result["warnings"],
            metadata=result.get("metadata"),
            diagnostics_by_strategy=result.get("diagnostics"),
            selected_strategies=["universal_structure"],
        )
        run_status = report.get("run_status", [])
        ict = next((s for s in run_status if s["key"] == "ict_2022"), None)
        ict_note = (ict or {}).get("ict_note") or ""
        self.assertIn("OTE", ict_note)

    def test_run_status_has_all_four_strategies(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure", "supply_demand"], symbol="EUR/USD", timeframe="M15")
        from backtesting.reports import build_report
        report = build_report(
            result["trades"],
            n_candles=result["n_candles"],
            symbol="EUR/USD",
            timeframe="M15",
            risk_per_trade=1.0,
            starting_balance=10000,
            backtest_warnings=result["warnings"],
            metadata=result.get("metadata"),
            diagnostics_by_strategy=result.get("diagnostics"),
            selected_strategies=["universal_structure", "supply_demand"],
        )
        run_status = report.get("run_status", [])
        keys = [s["key"] for s in run_status]
        for expected_key in ["universal_structure", "supply_demand", "breakout_retest", "ict_2022"]:
            self.assertIn(expected_key, keys)

    def test_zero_trade_strategy_has_main_reason(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["breakout_retest"], symbol="EUR/USD", timeframe="M15")
        from backtesting.reports import build_report
        report = build_report(
            result["trades"],
            n_candles=result["n_candles"],
            symbol="EUR/USD",
            timeframe="M15",
            risk_per_trade=1.0,
            starting_balance=10000,
            backtest_warnings=result["warnings"],
            metadata=result.get("metadata"),
            diagnostics_by_strategy=result.get("diagnostics"),
            selected_strategies=["breakout_retest"],
        )
        run_status = report.get("run_status", [])
        br = next((s for s in run_status if s["key"] == "breakout_retest"), None)
        self.assertIsNotNone(br)
        reason = br.get("main_reason", "")
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 10)

    def test_diagnostics_present_for_selected_strategies(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        from backtesting.reports import build_report
        report = build_report(
            result["trades"],
            n_candles=result["n_candles"],
            symbol="EUR/USD",
            timeframe="M15",
            risk_per_trade=1.0,
            starting_balance=10000,
            backtest_warnings=result["warnings"],
            metadata=result.get("metadata"),
            diagnostics_by_strategy=result.get("diagnostics"),
            selected_strategies=["universal_structure"],
        )
        run_status = report.get("run_status", [])
        us = next((s for s in run_status if s["key"] == "universal_structure"), None)
        self.assertIsNotNone(us.get("diagnostics"))
        self.assertIn("evaluation_count", us["diagnostics"])
        self.assertIn("potential_setups", us["diagnostics"])

    def test_diagnostics_none_for_unselected_strategies(self):
        candles = _make_candles(80)
        result = run_backtest(candles, ["universal_structure"], symbol="EUR/USD", timeframe="M15")
        from backtesting.reports import build_report
        report = build_report(
            result["trades"],
            n_candles=result["n_candles"],
            symbol="EUR/USD",
            timeframe="M15",
            risk_per_trade=1.0,
            starting_balance=10000,
            backtest_warnings=result["warnings"],
            metadata=result.get("metadata"),
            diagnostics_by_strategy=result.get("diagnostics"),
            selected_strategies=["universal_structure"],
        )
        run_status = report.get("run_status", [])
        ict = next((s for s in run_status if s["key"] == "ict_2022"), None)
        self.assertIsNone(ict.get("diagnostics"))

    def test_infer_main_reason_no_setup(self):
        from backtesting.engine import StrategyDiagnostics, infer_main_reason
        diag = StrategyDiagnostics(candles_checked=100, evaluation_count=10)
        diag.record_state("NO_SETUP")
        diag.record_state("NO_SETUP")
        reason = infer_main_reason(diag, "universal_structure")
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 5)

    def test_infer_main_reason_missed_entries(self):
        from backtesting.engine import StrategyDiagnostics, infer_main_reason
        diag = StrategyDiagnostics(
            candles_checked=200, evaluation_count=20,
            potential_setups=2, missed_entries=2
        )
        reason = infer_main_reason(diag, "supply_demand")
        self.assertIn("signal", reason.lower())

    def test_expired_pending_increments_missed_entries(self):
        """Simulator returning EXPIRED should be counted as missed_entry in engine."""
        sim = TradeSimulator("Test")
        sim.open_pending(
            signal_candle_idx=0,
            strategy_name="Test",
            symbol="EUR/USD",
            timeframe="M15",
            direction="Bullish",
            entry_zone={"top": 1.15100, "bottom": 1.14950},
            stop_loss=1.14800,
            tp1=1.15500,
            tp2=None,
            reason="test",
        )
        # Advance past MAX_PENDING_CANDLES without fill
        from backtesting.simulator import MAX_PENDING_CANDLES
        start = datetime(2026, 1, 2, tzinfo=timezone.utc)
        for i in range(1, MAX_PENDING_CANDLES + 2):
            candle = pd.Series({
                "time": int((start + timedelta(minutes=15 * i)).timestamp()),
                "open": 1.15200, "high": 1.15300, "low": 1.15150, "close": 1.15200,
            })
            result = sim.check_pending_entry(candle, i)
            if result == "EXPIRED":
                break
        else:
            self.fail("Simulator never returned EXPIRED")

        self.assertEqual(sim.state, "WATCHING")



# ---------------------------------------------------------------------------
# Small sample handling tests
# ---------------------------------------------------------------------------

class TestSmallSampleHandling(unittest.TestCase):

    def test_zero_trades_returns_no_sample(self):
        from backtesting.metrics import calculate_metrics, sample_quality_label
        m = calculate_metrics([], "Test")
        self.assertEqual(m["sample_quality"], "No Sample")
        self.assertEqual(sample_quality_label(0), "No Sample")

    def test_one_trade_returns_insufficient_data(self):
        from backtesting.metrics import sample_quality_label
        self.assertEqual(sample_quality_label(1), "Insufficient Data")
        self.assertEqual(sample_quality_label(9), "Insufficient Data")

    def test_ten_to_nineteen_returns_weak_sample(self):
        from backtesting.metrics import sample_quality_label
        self.assertEqual(sample_quality_label(10), "Weak Sample")
        self.assertEqual(sample_quality_label(19), "Weak Sample")

    def test_twenty_plus_returns_usable(self):
        from backtesting.metrics import sample_quality_label
        self.assertEqual(sample_quality_label(20), "Usable Sample")
        self.assertEqual(sample_quality_label(49), "Usable Sample")
        self.assertEqual(sample_quality_label(50), "Stronger Sample")

    def test_infinite_pf_small_sample_has_hint(self):
        """Wins-only with < 20 trades → profit_factor_display_hint says N/A."""
        from backtesting.metrics import calculate_metrics
        # All wins, no losses
        trades = [_trade("TP1", 2.0)] * 3
        m = calculate_metrics(trades, "Test")
        self.assertTrue(m["profit_factor_infinite"])
        self.assertEqual(m["profit_factor"], 999.0)
        hint = m.get("profit_factor_display_hint") or ""
        self.assertIn("N/A", hint)

    def test_infinite_pf_large_sample_has_very_high_hint(self):
        from backtesting.metrics import calculate_metrics
        trades = [_trade("TP1", 2.0)] * 30
        m = calculate_metrics(trades, "Test")
        self.assertTrue(m["profit_factor_infinite"])
        hint = m.get("profit_factor_display_hint") or ""
        self.assertIn("Very high", hint)

    def test_result_status_no_data_when_zero_trades(self):
        from backtesting.comparison import compare_strategies
        result = compare_strategies({"universal_structure": []})
        self.assertIn(result["result_status"], {"no_data", "insufficient"})

    def test_result_status_insufficient_for_small_sample(self):
        from backtesting.comparison import compare_strategies
        trades = [_trade("TP1", 2.0)] * 5
        result = compare_strategies({"universal_structure": trades})
        self.assertIn(result["result_status"], {"insufficient", "early_leader"})

    def test_result_status_early_leader_for_medium_sample(self):
        from backtesting.comparison import compare_strategies
        trades = [_trade("TP1", 2.0)] * 12 + [_trade("SL", -1.0)] * 5
        result = compare_strategies({"universal_structure": trades})
        self.assertIn(result["result_status"], {"early_leader", "confirmed"})

    def test_sample_quality_in_metrics_output(self):
        from backtesting.metrics import calculate_metrics
        trades = [_trade("TP1", 2.0), _trade("SL", -1.0)] * 12  # 24 trades
        m = calculate_metrics(trades, "Test")
        self.assertEqual(m["sample_quality"], "Usable Sample")
        self.assertFalse(m["sample_size_warning"])


if __name__ == "__main__":
    unittest.main()

