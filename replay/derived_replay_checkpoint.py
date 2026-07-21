import hashlib,json

def checkpoint_payload(run_id,state,configuration_hash,dataset_checksum,random_seed=0):
    payload={"replay_run_id":run_id,"replay_candle_index":state.candle_index,"replay_timestamp":state.replay_time,"active_pending_setups":state.pending_setup_ids,"active_filled_positions":state.filled_setup_ids,"current_strategy_selection":state.selected_strategy,"analytical_state":state.analytical_state,"last_processed_outcome_event":state.last_outcome_event,"random_seed":random_seed,"configuration_hash":configuration_hash,"dataset_checksum":dataset_checksum}
    payload["checkpoint_hash"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest();return payload

def validate_checkpoint(payload,configuration_hash,dataset_checksum):
    check=dict(payload);received=check.pop("checkpoint_hash",None);expected=hashlib.sha256(json.dumps(check,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    if received!=expected:raise ValueError("Replay checkpoint checksum is invalid.")
    if payload.get("configuration_hash")!=configuration_hash:raise ValueError("Replay checkpoint configuration does not match.")
    if payload.get("dataset_checksum")!=dataset_checksum:raise ValueError("Replay checkpoint dataset does not match.")
    return True

