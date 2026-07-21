from analysis.derived_historical_evidence import normalize_historical_evidence
def test_small_sample_is_insufficient_and_cannot_rank():
    row=normalize_historical_evidence("s","x","VOLATILITY","RANGE",[{"r":5}]*10);assert row["evidence_label"]=="insufficient" and not row["eligible_for_ranking"]
def test_out_of_sample_required_for_ranking():
    rows=[{"r":1,"out_of_sample":False}]*120;assert not normalize_historical_evidence("s","x","V","R",rows)["eligible_for_ranking"]
