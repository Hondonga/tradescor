import pathlib
import unittest

from analysis.setup_recovery import apply_setup_recovery
from analysis.trade_chart import build_trade_chart


RULES={"asset_class":"forex","pip_size":.0001,"tick_size":.00001}


def _decision(state="too_late"):
    return {"setup":{"setup_id":"old-sell","direction":"sell","strategy":"ict_2022","stage":state,"zone":{"low":1.14431,"high":1.14451,"type":"fvg","origin_time":"2026-07-17T10:00:00Z"},"confirmation":{"price":1.1439,"confirmed":True,"confirmed_time":"2026-07-17T10:20:00Z"},"invalidation":{"price":1.1447},"created_time":"2026-07-17T10:00:00Z"},"execution":{"state":state,"entry":1.14391,"m5_execution_zone":{"low":1.14386,"high":1.14396},"confirmed_entry":{"price":1.14391,"confirmed_at":"2026-07-17T10:20:00Z"},"stop":1.1447,"targets":[{"price":1.1420}],"risk_reward":.6,"remaining_rr_from_current":.6},"quality":{"score":90,"confidence":"medium","trade_plan_valid":False},"user_output":{"status":"TOO LATE","direction":"Short"},"overlays":{"setup_zone":{}}}


class MissedSetupRecoveryTests(unittest.TestCase):
    def recovered(self):
        decision=_decision(); apply_setup_recovery(decision,current_price=1.14257,analysis_time="2026-07-17T11:12:00Z",asset_rules=RULES); return decision

    def test_terminal_setup_is_archived_and_removed_from_active_decision(self):
        decision=self.recovered(); self.assertIsNone(decision["active_setup"]); self.assertIsNone(decision["setup"]["setup_id"]); self.assertEqual(decision["setup"]["direction"],"neutral")
        self.assertEqual(decision["previous_setup"]["setup_id"],"old-sell"); self.assertEqual((decision["previous_setup"]["entry_low"],decision["previous_setup"]["entry_high"]),(1.14431,1.14451))
        self.assertEqual((decision["quality"]["score"],decision["quality"]["confidence"]),(0,"low")); self.assertEqual(decision["user_output"]["status"],"NO CURRENT SETUP")

    def test_previous_setup_distance_uses_nearest_locked_boundary(self):
        previous=self.recovered()["previous_setup"]; self.assertEqual(previous["distance_moved"],17.4); self.assertEqual(previous["distance_relation"],"below"); self.assertEqual(previous["remaining_rr"],.6)

    def test_reassessment_scans_both_directions_and_all_auto_strategies(self):
        scan=self.recovered()["current_market_decision"]["scan"]; self.assertEqual(scan["directions_evaluated"],["buy","sell"]); self.assertEqual(scan["strategies_evaluated"],["ict_2022","supply_demand","breakout_retest"]); self.assertEqual(scan["excluded_setup_id"],"old-sell")

    def test_archived_setup_cannot_render_as_active_trade_chart(self):
        chart=build_trade_chart(self.recovered(),current_price=1.14257,asset_rules=RULES); self.assertEqual(chart["idea"],"none"); self.assertIsNone(chart["expected_entry"]["low"]); self.assertEqual(chart["targets"],[]); self.assertIsNone(chart["stop"])

    def test_context_and_previous_setup_have_separate_toggle_ownership(self):
        js=(pathlib.Path(__file__).resolve().parents[1]/"static/app.js").read_text(); self.assertIn("if (ui.fvg.checked) drawMarketContext",js); self.assertIn("if (ui.labels.checked) { drawFvg(analysis); drawAmdOverlays",js); self.assertIn("drawPreviousSetup(analysis.decision?.previous_setup",js); self.assertIn("ui.previous.checked",js)


if __name__=="__main__": unittest.main()
