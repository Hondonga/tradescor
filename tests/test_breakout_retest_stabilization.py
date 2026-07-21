import unittest

import pandas as pd

from analysis.auto_strategy_router import _breakout_candidate
from analysis.m5_execution_engine import build_m5_execution_plan
from analysis.decision_engine import _amd_result, _breakout_result


def _features():
    return {"timeframes":{"M15":{"range":{"value":{"low":1.40293,"high":1.40354,"boundary_tests":3}},"displacement":{"value":{"active":False}},"compression":{"value":{"active":False}}},"H1":{}}}


def _amd(side="high"):
    return {"boundary_event":"accepted_breakout","accumulation":{"range_low":1.40293,"range_high":1.40354,"atr":.0005},"manipulation":{"side":side,"boundary":1.40354 if side=="high" else 1.40293,"breakout_close":1.40380 if side=="high" else 1.40270,"breakout_time":"2026-07-17T12:15:00+00:00","sweep_time":"2026-07-17T12:10:00+00:00"}}


class BreakoutRetestStabilizationTests(unittest.TestCase):
    def test_accepted_breakout_routes_even_when_amd_failed(self):
        row=_breakout_candidate("USD/CAD","forex","RANGING",_features(),{"alignment":{"primary_direction":"sell"}},_amd(),"buy",0.00002)
        self.assertTrue(row["eligible"]); self.assertEqual(row["direction"],"buy")
        self.assertEqual(row["relationship"],"countertrend_breakout"); self.assertEqual(row["minimum_rr"],2.0)

    def test_retest_zone_uses_broken_boundary_not_whole_range(self):
        row=_breakout_candidate("USD/CAD","forex","RANGING",_features(),{"alignment":{"primary_direction":"sell"}},_amd(),"buy",0.00002)
        self.assertLess(row["zone"]["low"],1.40354); self.assertGreater(row["zone"]["high"],1.40354)
        self.assertLess(row["zone"]["high"]-row["zone"]["low"],1.40354-1.40293)

    def test_mirrored_bearish_breakout_uses_range_low(self):
        row=_breakout_candidate("USD/CAD","forex","RANGING",_features(),{"alignment":{"primary_direction":"buy"}},_amd("low"),"sell",0.00002)
        self.assertTrue(row["eligible"]); self.assertEqual(row["breakout"]["direction"],"bearish")
        self.assertLess(row["zone"]["low"],1.40293); self.assertGreater(row["zone"]["high"],1.40293)

    def test_failed_amd_and_eligible_breakout_are_separate_results(self):
        amd={**_amd(),"validation":{"valid_cycle":False},"phase":{"current":"failed"}}
        candidate=_breakout_candidate("USD/CAD","forex","RANGING",_features(),{"alignment":{"primary_direction":"sell"}},amd,"buy",.00002)
        self.assertEqual(_amd_result(amd)["failure_reason"],"accepted_breakout")
        result=_breakout_result(candidate,{"state":"waiting_for_zone","confirmed_signal":None,"trigger":None,"message":""},1.40380)
        self.assertTrue(result["eligible"]); self.assertEqual(result["state"],"WAITING_FOR_RETEST")
        self.assertEqual(result["primary_actionable_direction"],"neutral"); self.assertIsNone(result["confirmation"]["price"])

    def test_failed_break_does_not_create_opposite_candidate(self):
        amd={**_amd(),"boundary_event":"failed_break","manipulation":{**_amd()["manipulation"],"boundary_event":"failed_break"}}
        row=_breakout_candidate("USD/CAD","forex","RANGING",_features(),{"alignment":{"primary_direction":"sell"}},amd,"sell",.00002)
        self.assertFalse(row["eligible"])

    def test_confirmation_before_breakout_is_ignored(self):
        times=pd.date_range("2026-07-17T11:15:00Z",periods=14,freq="5min")
        candles=pd.DataFrame({"time":times,"open":[1.4035]*14,"high":[1.4037]*14,"low":[1.4033]*14,"close":[1.4036]*14})
        setup={"alignment":{"primary_direction":"buy"},"m15_setup":{"enabled":True,"countertrend":False,"zone":{"low":1.40348,"high":1.40360,"valid_after":"2026-07-17T12:15:00Z"}}}
        result=build_m5_execution_plan(top_down_analysis=setup,m5_candles=candles,analysis_timestamp="2026-07-17T12:25:00Z",current_price=1.4038,asset_type="forex")
        self.assertIsNone(result["trigger"]); self.assertIsNone(result["confirmed_signal"])


if __name__ == "__main__": unittest.main()
