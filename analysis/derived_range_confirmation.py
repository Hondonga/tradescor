"""Range-id-bound confirmation and immutable entry wrappers."""
from analysis.derived_execution_confirmation import confirm_m5_execution,lock_confirmed_entry

def confirm_range_reaction(candles,direction,m15_zone,execution_zone,setup_id,range_id,rejection):
    result=confirm_m5_execution(candles,direction,m15_zone,execution_zone,setup_id,(rejection or {}).get("rejection_time"))
    return {**result,"valid_for_range_id":range_id if result.get("valid") else None}

def lock_range_reaction_entry(confirmation,setup_id,range_id,price):
    valid=confirmation and confirmation.get("valid_for_range_id")==range_id
    return {**lock_confirmed_entry(confirmation if valid else None,setup_id,price=price),"range_id":range_id}
