from strategies.derived.base_derived_strategy import candidate,directional_result
def evaluate_step(*,regime,price_location):
    direction=regime.get("direction");boundary=price_location in {"near_low","near_high"}
    buy=candidate("step_structure","buy",eligible=boundary and direction=="bullish",state="WAITING_FOR_CONFIRMATION" if boundary else "NO_SETUP",quality=55)|{"strategy_status":"research"};sell=candidate("step_structure","sell",eligible=boundary and direction=="bearish",state="WAITING_FOR_CONFIRMATION" if boundary else "NO_SETUP",quality=55)|{"strategy_status":"research"};return directional_result("step_structure",buy,sell)|{"strategy_status":"research"}
