from analysis.derived_range_detector import detect_derived_range
def build_step_range_context(candles,atr,config=None):return detect_derived_range(candles,atr,{"minimum_range_duration":18,"minimum_boundary_reactions":3,"minimum_reactions_per_side":1,"minimum_width_atr":.5,"maximum_width_atr":6,"minimum_range_quality":(config or {}).get("minimum_range_quality",.7)})
