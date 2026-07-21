import unittest

import numpy as np
import pandas as pd

from analysis.directional_structure import analyze_directional_structure
from analysis.market_features import feature
from analysis.market_presentation import build_market_presentation


RULES={"asset_class":"forex","pip_size":.0001,"tick_size":.00001}


def _candles(bearish=True):
    times=pd.date_range("2026-07-17T08:00:00Z",periods=48,freq="5min"); sign=-1 if bearish else 1
    center=1.1500+sign*(np.arange(48)*.00016)+np.sin(np.arange(48)*np.pi/3)*.00034
    opened=center-sign*.00008; closed=center+sign*.00008; high=np.maximum(opened,closed)+.00016; low=np.minimum(opened,closed)-.00016
    # Finish with a completed directional displacement through prior structure.
    closed[-3]=closed[-4]+sign*.00075; opened[-3]=closed[-4]; high[-3]=max(opened[-3],closed[-3])+.00008; low[-3]=min(opened[-3],closed[-3])-.00008
    closed[-2]=closed[-3]+sign*.00018; opened[-2]=closed[-3]; high[-2]=max(opened[-2],closed[-2])+.00008; low[-2]=min(opened[-2],closed[-2])-.00008
    return pd.DataFrame({"time":times,"open":opened,"high":high,"low":low,"close":closed})


def _features(direction):
    stamp="2026-07-17T12:30:00Z"; frame={"fvg":feature([],stamp,"M5"),"structure_direction":feature(direction,stamp,"M15"),"displacement":feature({"active":False,"direction":direction},stamp,"M15"),"volatility_regime":feature("normal",stamp,"M15"),"range":feature({"position":.1 if direction=="bearish" else .9},stamp,"M15"),"liquidity":feature({"equal_highs":[],"equal_lows":[]},stamp,"M15"),"atr":feature(.0005,stamp,"M15")}; return {"timeframes":{"M5":frame,"M15":frame}}


def _top(direction):
    side="sell" if direction=="bearish" else "buy"; return {"alignment":{"primary_direction":"neutral","state":"aligned"},"regime":{"value":"range"},"m15_setup":{"zone":None},"timeframes":{"D1":{"bias":"neutral"},"H4":{"bias":"neutral"},"H1":{"bias":"neutral"},"M15":{"bias":direction,"structure":"overlapping_transition","recent_high":1.151,"recent_low":1.141,"unswept_highs":[],"unswept_lows":[]}}}


class DirectionalStructureTests(unittest.TestCase):
    def analyze(self,bearish=True):
        direction="bearish" if bearish else "bullish"; rows=_candles(bearish); return analyze_directional_structure(m5_candles=rows,analysis_time=rows.iloc[-1].time+pd.Timedelta(minutes=5),features=_features(direction),top_down=_top(direction),asset_rules=RULES,current_price=float(rows.iloc[-2].close))

    def test_lower_highs_lows_and_downside_break_produce_bearish_context(self):
        result=self.analyze(True); self.assertEqual(result["direction"],"bearish"); self.assertIn(result["structure"],{"continuation","breakdown"}); self.assertIsNotNone(result["last_lower_high"]); self.assertTrue(any("lower lows" in row.lower() for row in result["evidence"]))

    def test_bearish_structure_does_not_create_confirmation_or_trade(self):
        result=self.analyze(True); self.assertFalse(result["trade_ready"]); self.assertIsNone(result["confirmation"]["price"]); self.assertEqual(result["confirmation"]["state"],"pending_zone_interaction")

    def test_sell_pullback_area_is_above_current_when_available(self):
        result=self.analyze(True); current=float(_candles(True).iloc[-2].close)
        if result["pullback_area"]: self.assertGreater(result["pullback_area"]["high"],current); self.assertEqual(result["pullback_area"]["touch_count"],0)

    def test_bullish_structure_is_mirrored(self):
        result=self.analyze(False); self.assertEqual(result["direction"],"bullish"); self.assertIn(result["structure"],{"continuation","breakout"}); self.assertFalse(result["trade_ready"])

    def test_no_active_trade_preserves_local_bias_and_developing_direction(self):
        structure=self.analyze(True); decision={"alignment":{"primary_direction":"neutral","state":"aligned"},"market_regime":{"value":"range"},"directional_structure":structure,"router":{"candidates":[]},"active_setup":None,"previous_setup":None,"execution":{"entry":None,"stop":None,"targets":[]},"quality":{"trade_plan_valid":False},"user_output":{"status":"NO CURRENT SETUP","next_action":""}}
        presentation=build_market_presentation(decision,top_down=_top("bearish"),features=_features("bearish"),current_price=float(_candles(True).iloc[-2].close)); self.assertEqual(presentation["decision"]["market_bias"],"bearish"); self.assertEqual(presentation["decision"]["developing_direction"],"sell"); self.assertFalse(presentation["decision"]["trade_ready"]); self.assertEqual(presentation["developing_scenario"]["label"],"Potential Sell Pullback")


if __name__=="__main__":unittest.main()
