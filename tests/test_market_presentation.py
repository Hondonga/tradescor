import unittest

from analysis.market_presentation import build_market_presentation


def _features():
    wrap=lambda value:{"value":value}
    return {"timeframes":{"M15":{"structure_direction":wrap("bearish"),"displacement":wrap({"active":False,"direction":"bearish"}),"volatility_regime":wrap("normal"),"atr":wrap(.001),"range":wrap({"position":.15}),"liquidity":wrap({"equal_highs":[{"price":1.3462}],"equal_lows":[{"price":1.3432}]})}}}


def _top_down():
    return {"timeframes":{"D1":{"bias":"bearish"},"H4":{"bias":"bearish"},"H1":{"bias":"bearish"},"M15":{"bias":"bearish","structure":"lower_highs_lower_lows","recent_high":1.3456,"recent_low":1.3438,"unswept_highs":[{"price":1.3456}],"unswept_lows":[{"price":1.3438}]}},"regime":{"value":"bearish"}}


def _decision(active=False):
    candidate={"candidate_id":"fresh","eligible":True,"candidate_score":70,"present_quality_score":70,"direction":"sell","strategy_id":"supply_demand","setup_type":"supply_retracement","zone":{"low":1.3452,"high":1.3456,"type":"supply"},"confirmation_requirements":["price reaches supply","completed M5 bearish confirmation"],"eligibility_reasons":["Higher-timeframe bearish pullback context."]}
    return {"alignment":{"primary_direction":"sell","state":"aligned"},"market_regime":{"value":"bearish"},"router":{"candidates":[candidate]},"active_setup":{"setup_id":"active"} if active else None,"previous_setup":None,"execution":{"state":"waiting_for_m15_area","entry":None,"stop":None,"targets":[]},"user_output":{"status":"NO CURRENT SETUP","next_action":""},"quality":{"score":60,"confidence":"medium"},"top_down":{},"strategy_routing":{},"amd":{}}


class MarketPresentationTests(unittest.TestCase):
    def test_no_setup_retains_context_scenario_and_real_levels(self):
        decision=_decision(); result=build_market_presentation(decision,top_down=_top_down(),features=_features(),current_price=1.3440)
        self.assertEqual(result["decision"]["market_bias"],"bearish"); self.assertEqual(result["market_context"]["price_location"],"Near support")
        self.assertTrue(result["developing_scenario"]["available"]); self.assertEqual(result["developing_scenario"]["zone"],{"low":1.3452,"high":1.3456,"type":"supply","origin_time":None})
        self.assertEqual(result["key_levels"]["support"],1.3438); self.assertEqual(result["key_levels"]["resistance"],1.3456)
        self.assertIsNone(result["active_trade_plan"])

    def test_archived_zone_is_not_reused_as_developing_scenario(self):
        decision=_decision(); decision["previous_setup"]={"entry_low":1.3452,"entry_high":1.3456,"setup_id":"old"}
        result=build_market_presentation(decision,top_down=_top_down(),features=_features(),current_price=1.3440)
        self.assertFalse(result["developing_scenario"]["available"])

    def test_active_plan_suppresses_duplicate_developing_zone(self):
        result=build_market_presentation(_decision(active=True),top_down=_top_down(),features=_features(),current_price=1.3440)
        self.assertFalse(result["developing_scenario"]["available"]); self.assertIsNotNone(result["active_trade_plan"])

    def test_frontend_uses_presentation_without_neutral_entry(self):
        from pathlib import Path
        js=(Path(__file__).resolve().parents[1]/"static/app.js").read_text(); self.assertIn("analysis.decision?.presentation",js); self.assertIn('$("decision-trade-map").hidden=!active',js); self.assertNotIn("Expected Neutral Entry",js)


if __name__=="__main__":unittest.main()
