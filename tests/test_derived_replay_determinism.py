from replay.derived_replay_service import configuration_hash
from replay.derived_replay_checkpoint import checkpoint_payload,validate_checkpoint
from replay.derived_replay_state import DerivedReplayState

def test_configuration_hash_and_checkpoint_are_deterministic():
    assert configuration_hash({"b":2,"a":1})==configuration_hash({"a":1,"b":2})
    state=DerivedReplayState(candle_index=9,replay_time="2026-01-01T00:50:00Z")
    first=checkpoint_payload("run",state,"cfg","data",0);second=checkpoint_payload("run",state,"cfg","data",0)
    assert first==second and validate_checkpoint(first,"cfg","data")

