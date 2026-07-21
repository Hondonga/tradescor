from analysis.market_decision_normalizer import normalize_market_decision
from providers.market_registry import MODEL_REGISTRY, derived_registry, traditional_registry
from providers.runtime_health import RuntimeHealth


class _DerivedProvider:
    def list_symbols(self):
        return [
            {"provider_symbol": "R_50", "display_name": "Volatility 50 Index", "family": "VOLATILITY", "analysis_supported": True},
            {"provider_symbol": "JD75", "display_name": "Jump 75 Index", "family": "JUMP", "analysis_supported": True},
        ]


def test_registry_routes_required_markets_and_isolates_models():
    traditional = {row["display_name"]: row for row in traditional_registry()}
    derived = {row["provider_symbol"]: row for row in derived_registry(_DerivedProvider())}
    assert derived["R_50"]["market_source"] == "deriv"
    assert derived["JD75"]["market_source"] == "deriv"
    assert traditional["EUR/USD"]["market_source"] == "twelve_data"
    assert traditional["GBP/USD"]["market_source"] == "twelve_data"
    assert traditional["BTC/USD"]["market_source"] == "twelve_data"
    assert traditional["NASDAQ 100"]["market_source"] == "twelve_data"
    assert "ict_2022" not in {row["id"] for row in derived["R_50"]["available_models"]}
    assert "volatility_smc" not in {row["id"] for row in traditional["EUR/USD"]["available_models"]}
    assert {row["id"] for row in MODEL_REGISTRY["forex"]} >= {"ict_2022", "supply_demand", "breakout_retest"}


def test_traditional_normalizer_matches_workspace_contract_and_exact_levels():
    legacy = {
        "decision_id": "forex-1",
        "strategy_routing": {"selected_strategy": "ict_2022"},
        "setup": {"setup_id": "setup-1", "type": "ict_2022", "direction": "sell", "stage": "waiting", "zone": {"low": 1.4045, "high": 1.4049, "type": "fvg"}, "invalidation": {"price": 1.4052}},
        "execution": {"state": "waiting", "targets": []},
        "quality": {"score": 70, "confidence": "medium", "trade_plan_valid": False},
        "user_output": {"status": "SELL SETUP FORMING", "summary": "Wait for retracement", "next_action": "Wait"},
        "trade_chart": {"current_price": 1.4038, "expected_entry": {"low": 1.4045, "high": 1.4049}, "confirmation": {"price": None, "confirmed": False}, "invalidation": {"price": 1.4052}, "targets": []},
        "overlays": {},
    }
    result = normalize_market_decision(legacy, symbol="EUR/USD", display_symbol="EUR/USD", timeframe="M5", market_source="twelve_data", market_type="forex", market_schedule="24_5", analysis_time="2026-07-19T12:00:00Z")
    assert set(("meta", "ownership", "readiness", "market", "decision", "setup", "diagnostics", "overlays", "previous_setup")) <= set(result)
    assert result["meta"]["market_source"] == "twelve_data"
    assert result["setup"]["entry_area"] == {"low": 1.4045, "high": 1.4049, "type": "fvg"}
    assert any(row["type"] == "entry_area" and row["low"] == 1.4045 and row["high"] == 1.4049 for row in result["overlays"])
    assert not any(row["type"] == "confirmation" for row in result["overlays"])


def test_registry_endpoint_keeps_traditional_markets_when_deriv_fails(monkeypatch):
    import app as app_module

    class FailingProvider:
        def list_symbols(self):
            raise RuntimeError("Deriv unavailable")

    monkeypatch.setattr(app_module, "get_provider", lambda **kwargs: FailingProvider())
    response = app_module.app.test_client().get("/api/markets/registry")
    payload = response.get_json()
    assert response.status_code == 200
    assert any(row["display_name"] == "EUR/USD" for row in payload["markets"])
    assert payload["errors"]["deriv"]["state"] == "error"


def test_provider_health_failures_are_independent():
    health = RuntimeHealth()
    health.provider("deriv", "ready")
    health.provider("twelve_data", "rate_limited")
    states = health.snapshot()["providers"]
    assert states["deriv"]["state"] == "ready"
    assert states["twelve_data"]["state"] == "rate_limited"
    health.provider("deriv", "error")
    assert health.snapshot()["providers"]["twelve_data"]["state"] == "rate_limited"
