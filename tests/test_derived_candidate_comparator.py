from analysis.derived_candidate_comparator import compare_derived_candidates
def test_ineligible_high_score_cannot_win():
    rows=[{"strategy_id":"a","quality_score":.99,"trade_ready":True,"blocking_reasons":["blocked"]},{"strategy_id":"b","quality_score":.6,"trade_ready":False,"blocking_reasons":[]}];registry={"a":{"priority":1},"b":{"priority":2}}
    assert compare_derived_candidates(rows,registry)["selected_candidate"]["strategy_id"]=="b"
def test_no_meaningful_candidate_returns_none():assert compare_derived_candidates([],{})["selected_candidate"] is None
