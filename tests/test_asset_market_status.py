from datetime import datetime, timezone

from scanner.session_engine import get_session_status


def test_crypto_market_is_open_24_7_during_forex_closed_hours():
    saturday = datetime(2025, 1, 4, 15, 0, tzinfo=timezone.utc)
    status = get_session_status(saturday, asset_type="crypto")

    assert status["market_open"] is True
    assert status["market_status"] == "OPEN_24_7"
    assert status["market_status_label"] == "24/7 Open"
    assert status["entry_allowed"] is True
    assert "Liquidity" in status["liquidity_window"]


def test_forex_keeps_weekend_market_closure():
    saturday = datetime(2025, 1, 4, 15, 0, tzinfo=timezone.utc)
    status = get_session_status(saturday, asset_type="forex")

    assert status["market_open"] is False
    assert status["market_status"] == "CLOSED"

