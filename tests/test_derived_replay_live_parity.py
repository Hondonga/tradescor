from replay.derived_replay_validator import parity_report

def test_structured_live_replay_parity_report():
    decision={"decision":{"status":"READY"},"active_trade_plan":{"entry":100}}
    assert parity_report(decision,decision)["parity"] is True
    mismatch=parity_report(decision,{"decision":{"status":"WAITING"}});assert not mismatch["parity"] and "decision" in mismatch["differences"]
