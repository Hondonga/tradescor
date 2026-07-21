from __future__ import annotations
import hashlib,json

SCHEMA_VERSION="smc-ml-features-v1"
ENGINE_VERSION="volatility_structure_pullback_engine-v2"
CATEGORICAL={"h1_external_structure":{"neutral":0,"bullish":1,"bearish":-1,"range":2},"m15_condition":{"insufficient":0,"impulsing":1,"impulse":1,"pullback":2,"range":3,"invalidated":4},"target_timeframe":{"":0,"M5":1,"M15":2,"H1":3}}
FEATURE_NAMES=("h1_external_structure","h1_active_leg_direction","h1_active_leg_distance_atr","h1_active_leg_age","h1_latest_bos_direction","h1_latest_bos_age","h1_swing_high_distance_atr","h1_swing_low_distance_atr","h1_atr","h1_directional_efficiency","h1_overlap_ratio","m15_condition","m15_pullback_depth_pct","m15_pullback_depth_atr","m15_setup_distance_atr","m15_premium_discount","m15_swing_high_distance_atr","m15_swing_low_distance_atr","m15_displacement_strength","m15_range_width_atr","m15_location_valid","m5_displacement_body_atr","m5_displacement_range_atr","m5_close_location","m5_directional_close_count","m5_bos","m5_mss","m5_structure_break_distance_atr","m5_retracement_depth","m5_entry_distance_atr","m5_stop_distance_atr","m5_target_distance_atr","m5_target_timeframe","m5_tp1_rr","m5_chase_distance_atr","m5_confirmation_age","target_source","target_age","target_consumed","returns_5","returns_10","returns_20","returns_50","rolling_volatility","rolling_directional_efficiency")

def schema():return {"schema_version":SCHEMA_VERSION,"engine_version":ENGINE_VERSION,"features":list(FEATURE_NAMES),"categorical_encodings":CATEGORICAL,"absolute_price_predictors":False,"availability_required":True}
def schema_hash():return hashlib.sha256(json.dumps(schema(),sort_keys=True,separators=(",",":")).encode()).hexdigest()
