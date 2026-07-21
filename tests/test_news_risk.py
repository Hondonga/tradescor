from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

import app as flask_app
from analysis.news_risk import analyze_news_risk, symbol_currencies
from providers import marketaux_provider


NOW = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def _article(
    *,
    title: str = "Dollar volatility rises",
    impact: str = "high",
    time: str = "2026-07-09T11:45:00Z",
    sentiment_score: float = -0.72,
) -> dict[str, object]:
    return {
        "event": title,
        "title": title,
        "impact": impact,
        "time": time,
        "source": "Marketaux",
        "publisher": "Test Wire",
        "sentiment_score": sentiment_score,
        "url": "https://example.com/news",
    }


def test_missing_marketaux_token_returns_unavailable(monkeypatch):
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Marketaux API token missing.")),
    )

    result = analyze_news_risk(symbol="EUR/USD", now=NOW)

    assert result["available"] is False
    assert result["risk_level"] == "unavailable"
    assert result["blocks_entry"] is False
    assert "Marketaux API token is missing" in result["message"]


def test_high_impact_marketaux_news_within_30_minutes_blocks_entry(monkeypatch):
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: [_article(title="US inflation surprise", time="2026-07-09T11:40:00Z")],
    )

    result = analyze_news_risk(symbol="EUR/USD", now=NOW)

    assert result["available"] is True
    assert result["risk_level"] == "high"
    assert result["blocks_entry"] is True
    assert result["source"] == "Marketaux"
    assert result["minutes_until"] == -20


def test_high_impact_recent_marketaux_news_warns(monkeypatch):
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: [_article(title="FOMC minutes reaction", time="2026-07-09T11:00:00Z")],
    )

    result = analyze_news_risk(symbol="USD/JPY", now=NOW)

    assert result["risk_level"] == "medium"
    assert result["blocks_entry"] is False


def test_medium_impact_news_warns_but_does_not_block(monkeypatch):
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: [_article(title="Sterling volatility", impact="medium", time="2026-07-09T11:45:00Z")],
    )

    result = analyze_news_risk(symbol="GBP/JPY", now=NOW)

    assert result["risk_level"] == "medium"
    assert result["blocks_entry"] is False


def test_currency_detection_checks_both_sides_of_forex_pairs():
    assert symbol_currencies("EUR/USD") == {"EUR", "USD"}
    assert symbol_currencies("USD/JPY") == {"USD", "JPY"}


def test_news_risk_does_not_create_trades(monkeypatch):
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: [_article(title="CPI reaction", time="2026-07-09T11:55:00Z")],
    )

    result = analyze_news_risk(symbol="EUR/USD", now=NOW)

    assert "direction" not in result
    assert "signal" not in result
    assert result["blocks_entry"] is True


def test_ready_setup_is_downgraded_when_news_blocks_entry():
    analysis = {
        "trader_answers": {
            "trade_status": "Entry Ready",
            "trade_readiness": "Ready",
            "why": ["Confirmation is complete."],
            "next_action": "Use the trade plan below.",
            "market_story": "EUR/USD has a confirmed setup.",
        },
        "levels_mode": "final",
        "trade_decision": "ACCEPT",
        "trade_metrics": {"plan_mode": "final", "warnings": []},
    }
    strategy_result = {
        "trade_status": "Entry Ready",
        "trade_decision": "ACCEPT",
        "levels_mode": "final",
        "trader_answers": analysis["trader_answers"],
    }
    filters = {
        "news_risk": {
            "blocks_entry": True,
            "message": "High-impact Marketaux news just hit. Entry blocked.",
        }
    }

    changed = flask_app._apply_news_filter_gate(analysis, strategy_result, filters)

    assert changed is True
    assert analysis["trader_answers"]["trade_status"] == "Wait"
    assert strategy_result["trade_decision"] == "PENDING"
    assert strategy_result["levels_mode"] == "projected"
    assert "High-impact news is close" in analysis["trader_answers"]["next_action"]


def test_dxy_off_is_explicit_not_confirmation():
    result = flask_app._build_dxy_confirmation_filter(
        {"dxy_confirmation_enabled": False, "marketaux_enabled": True},
        replay=False,
    )

    assert result["available"] is False
    assert result["status"] == "Off"
    assert result["enabled"] is False
    assert result["supports_trade"] is None
    assert result["message"] == "DXY confirmation is turned off."


def test_marketaux_provider_errors_do_not_escape_news_risk(monkeypatch):
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Marketaux rate limit reached.")),
    )

    result = analyze_news_risk(symbol="EUR/USD", now=NOW)

    assert result["available"] is False
    assert result["blocks_entry"] is False
    assert "rate limit" in result["message"].lower()


def test_marketaux_token_rejected_is_not_low_or_high_risk(monkeypatch, tmp_path):
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Marketaux API token was rejected or does not have access.")),
    )
    monkeypatch.setattr("analysis.news_risk.LOCAL_CALENDAR_PATH", tmp_path / "missing.json")

    result = analyze_news_risk(symbol="EUR/USD", now=NOW)

    assert result["available"] is False
    assert result["risk_level"] == "unavailable"
    assert result["status"] == "Unavailable"
    assert "Marketaux API token was rejected" in result["message"]


def test_local_calendar_fallback_is_used_when_marketaux_unavailable(monkeypatch, tmp_path):
    calendar = tmp_path / "economic_calendar.json"
    calendar.write_text(json.dumps([
        {
            "title": "CPI",
            "currency": "USD",
            "impact": "High",
            "time": "2026-07-09T12:20:00Z",
        }
    ]))
    monkeypatch.setattr(
        marketaux_provider,
        "get_finance_news",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Marketaux API token was rejected or does not have access.")),
    )
    monkeypatch.setattr("analysis.news_risk.LOCAL_CALENDAR_PATH", calendar)

    result = analyze_news_risk(symbol="EUR/USD", now=NOW)

    assert result["available"] is True
    assert result["source"] == "Local calendar"
    assert result["risk_level"] == "high"
    assert result["blocks_entry"] is True


def test_marketaux_news_responses_are_cached(monkeypatch):
    marketaux_provider.clear_cache()
    monkeypatch.setattr(marketaux_provider, "_load_env", lambda: None)
    monkeypatch.setenv("MARKETAUX_ENABLED", "true")
    monkeypatch.setenv("MARKETAUX_API_KEY", "test-token")
    calls = {"count": 0}

    class Response:
        status_code = 200

        def json(self):
            return {
                "data": [
                    {
                        "title": "EUR/USD holds range before Fed remarks",
                        "description": "Currency markets wait for policy comments.",
                        "source": "Test Wire",
                        "url": "https://example.com/article",
                        "published_at": "2026-07-09T11:30:00Z",
                        "entities": [{"symbol": "EURUSD", "sentiment_score": -0.8}],
                    }
                ]
            }

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        return Response()

    monkeypatch.setattr(marketaux_provider.requests, "get", fake_get)

    first = marketaux_provider.get_finance_news(
        symbol="EUR/USD",
        published_after=NOW,
        published_before=NOW,
        limit=3,
    )
    second = marketaux_provider.get_finance_news(
        symbol="EUR/USD",
        published_after=NOW,
        published_before=NOW,
        limit=3,
    )

    assert first == second
    assert calls["count"] == 1
    assert first[0]["source"] == "Marketaux"


def test_marketaux_403_reports_token_access_problem(monkeypatch):
    marketaux_provider.clear_cache()
    monkeypatch.setattr(marketaux_provider, "_load_env", lambda: None)
    monkeypatch.setenv("MARKETAUX_ENABLED", "true")
    monkeypatch.setenv("MARKETAUX_API_KEY", "test-token")

    class Response:
        status_code = 403

        def json(self):
            return {"error": "You don't have access to this resource."}

    monkeypatch.setattr(marketaux_provider.requests, "get", lambda *_args, **_kwargs: Response())

    with pytest.raises(RuntimeError, match="Marketaux API token was rejected"):
        marketaux_provider.get_finance_news(
            symbol="EUR/USD",
            published_after=NOW,
            published_before=NOW,
            limit=3,
        )
