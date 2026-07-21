from analysis.derived_auto_conflict_resolver import resolve_auto_conflict
def test_opposite_candidates_are_not_averaged():
    row=resolve_auto_conflict({"strategy_id":"a","direction":"buy"},{"strategy_id":"b","direction":"sell"},"RANGE");assert row["conflict_resolved"] and row["selected_candidate"]["direction"]=="buy"
