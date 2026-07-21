from validation.smc_causality_validator import validate_smc_causality
def payload(smc):return {"decision_id":"d","analysis_candle_time":"2026-01-01T00:15:00Z","smc_contract":smc}
def test_causal_entities_pass_and_future_confirmation_fails():
    valid=payload({"swings":[{"swing_id":"s","candle_time":"2026-01-01T00:00:00Z","confirmation_time":"2026-01-01T00:10:00Z"}],"fvgs":[{"fvg_id":"f","source_times":["2026-01-01T00:00:00Z","2026-01-01T00:05:00Z","2026-01-01T00:10:00Z"],"created_time":"2026-01-01T00:10:00Z"}]});assert validate_smc_causality([valid])["valid"]
    invalid=payload({"swings":[{"swing_id":"s","candle_time":"2026-01-01T00:00:00Z","confirmation_time":"2026-01-01T00:20:00Z"}]});assert not validate_smc_causality([invalid])["valid"]
def test_pre_event_jump_entry_is_a_causality_violation():
    row=payload({"event":{"event_id":"e","qualified":True,"event_time":"2026-01-01T00:10:00Z"},"setup":{"entry_array":{"origin_time":"2026-01-01T00:05:00Z"}}});assert validate_smc_causality([row])["causality_violations"][0]["violation"]=="pre_event_jump_entry_array"

