from strategies.derived.base_derived_strategy import strategy_eligibility
from analysis.derived_strategy_decision import normalize_strategy_decision
def test_trend_is_eligible_but_range_and_post_spike_are_restricted():
    family={"family":"VOLATILITY"}
    assert strategy_eligibility(family=family,regime={"regime":"TREND_BULLISH"},profile_quality="good")["eligible"]
    assert not strategy_eligibility(family=family,regime={"regime":"RANGE"},profile_quality="good")["eligible"]
    assert not strategy_eligibility(family=family,regime={"regime":"POST_SPIKE"},profile_quality="good")["eligible"]
def test_no_confirmation_never_returns_ready():
    decision=normalize_strategy_decision(eligible=True,direction="buy",pullback={"state":"VALID_PULLBACK"},zone={"valid":True},execution_zone={"valid":True},confirmation=None,entry=None,stop=None,targets=None,rr=None,chase=None,setup_id="x")
    assert decision["status"]=="WAITING FOR M5 CONFIRMATION" and not decision["trade_ready"]
