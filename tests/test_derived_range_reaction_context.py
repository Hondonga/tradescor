from analysis.derived_range_reaction_context import build_range_reaction_context

def test_only_stable_supported_contexts_are_eligible():
    profile={"directional_efficiency":.1,"profile_quality":"good","volatility_regime":"NORMAL"}; quality={"analysis_allowed":True,"status":"good"}; cfg={}
    assert build_range_reaction_context({"family":"VOLATILITY"},{"regime":"RANGE"},profile,{},quality,cfg)["eligible"]
    assert not build_range_reaction_context({"family":"VOLATILITY"},{"regime":"EXPANSION"},profile,{},quality,cfg)["eligible"]
    step=build_range_reaction_context({"family":"STEP"},{"regime":"RANGE"},profile,{},quality,cfg)
    assert step["eligible"] and step["strategy_status"]=="research"
