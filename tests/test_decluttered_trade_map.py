import pathlib
import unittest


ROOT=pathlib.Path(__file__).resolve().parents[1]


class DeclutteredTradeMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js=(ROOT/"static/app.js").read_text()
        cls.html=(ROOT/"templates/index.html").read_text()

    def test_missed_state_exits_before_active_levels(self):
        block=self.js.split("function drawTradePlan",1)[1].split("function drawTradeChartGuide",1)[0]
        self.assertIn("if (missed) return;",block)
        self.assertIn('trade-entry-zone ${plan.idea}${missed ? " missed"',block)

    def test_default_entry_is_single_priority_selection(self):
        block=self.js.split("function drawTradePlan",1)[1].split("function drawTradeChartGuide",1)[0]
        self.assertIn("selectDisplayEntry(plan)",block)
        self.assertNotIn("M5 Entry Low",block)
        self.assertNotIn("M5 Entry High",block)

    def test_advanced_boundaries_require_labels_toggle(self):
        block=self.js.split("function drawTradePlan",1)[1].split("function drawTradeChartGuide",1)[0]
        self.assertIn("if (ui.labels.checked)",block)
        self.assertIn("Entry High",block)

    def test_details_are_collapsed_by_default(self):
        self.assertIn('<details class="decision-details"><summary>Strategy Details</summary>',self.html)
        self.assertNotIn('<details class="decision-details" open>',self.html)

    def test_market_context_is_on_by_default(self):
        self.assertIn('<input id="show-fvg" type="checkbox" checked><span>Market Context</span>',self.html)


if __name__=="__main__": unittest.main()
