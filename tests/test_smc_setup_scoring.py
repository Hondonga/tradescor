from analysis.smc.smc_scoring import score_smc
from analysis.smc.smc_setup_engine import build_smc_setup

def test_optional_quality_cannot_replace_or_kill_essential_validity():
    quality={"htf_alignment":1,"displacement_strength":1,"clean_sweep":1,"fvg_quality":0,"order_block_quality":0,"premium_discount_alignment":0,"target_clarity":1,"low_structural_conflict":1}
    valid=score_smc({"structure":True,"confirmation":True},quality);blocked=score_smc({"structure":True,"confirmation":False},quality);assert valid["valid"] and not blocked["valid"] and blocked["quality_grade"]=="REJECTED"

def test_structurally_complete_fixture_reaches_trade_ready():
    structure={"last_mss":{"structure_event_id":"m","direction":"bullish"},"last_bos":None};setup=build_smc_setup(symbol="R_100",strategy_id="smc",family_adapter="volatility",direction="bullish",htf_structure="bullish",structural_target={"reference_id":"t","type":"buy_side","price":110},sweep={"qualified":True,"type":"sweep","extreme":98},displacement={"passed":True,"body_atr":1},structure=structure,entry_array={"fvg_id":"f","type":"fvg","low":100,"high":102,"invalidated":False},current_price=101,tick_size=.1)
    assert setup["state"]=="TRADE_READY" and setup["entry"]==101 and setup["stop"]<setup["entry"] and setup["rr"]>=1.5

def test_shadow_or_developing_setup_has_no_actionable_levels():
    setup=build_smc_setup(symbol="R_100",strategy_id="smc",family_adapter="volatility",direction="bullish",htf_structure="bullish",structural_target={},sweep={},displacement={},structure={},entry_array={},current_price=100);assert setup["state"]!="TRADE_READY" and setup["entry"] is None and setup["stop"] is None and setup["targets"]==[]

