from __future__ import annotations

import unittest

from app import _get_chart_query, app


class CreditDefaultTests(unittest.TestCase):
    def test_api_defaults_to_single_timeframe(self):
        with app.test_request_context("/api/analyze?manual=1&symbol=EUR/USD&timeframe=M5&bars=300"):
            query = _get_chart_query(require_manual=True)

        self.assertFalse(query["multi_timeframe_enabled"])
