from analysis.derived_range_lock import lock_range,active_range,clear_range_locks
def test_boundaries_and_identity_remain_immutable_after_future_breakout():
    clear_range_locks();base={"valid":True,"low":99,"high":101,"started_at":"a","ended_at":"b","quality":.8,"duration_candles":20};one=lock_range("RB100",base,[1,2]);two=lock_range("RB100",{**base,"high":110,"ended_at":"c"},[1,2,3]);assert one["range_id"]==two["range_id"] and two["high"]==101 and active_range("RB100")["low"]==99
