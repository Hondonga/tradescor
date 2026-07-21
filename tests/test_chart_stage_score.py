from app import _score_setup_stage


def test_fresh_untouched_zone_is_watching_even_if_strategy_state_mentions_confirmation():
    analysis = {
        "levels": {
            "important_zone": {
                "low": 1.14528,
                "high": 1.14558,
                "zone_status": "fresh",
                "touch_count": 0,
            }
        },
        "shared_analysis": {"current": {"current_price": 1.14722}},
    }
    strategy = {
        "state": "CONFIRMED_WAITING_FOR_ENTRY",
        "trade_decision": "PENDING",
        "levels_mode": "projected",
    }

    assert _score_setup_stage(analysis, strategy) == "WATCHING AREA"


def test_price_inside_zone_advances_to_in_setup_area():
    analysis = {
        "levels": {"important_zone": {"low": 1.40504, "high": 1.40549}},
        "shared_analysis": {"current": {"current_price": 1.40520}},
    }

    assert _score_setup_stage(analysis, {"state": "WAITING"}) == "IN SETUP AREA"
