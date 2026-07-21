from analysis.derived_strategy_registry import derived_strategy_registry
def test_registry_contains_every_actionable_derived_strategy():
    rows=derived_strategy_registry();assert len(rows)==7
    assert all({"strategy_id","display_name","supported_families","supported_regimes","research_only","enabled","adapter","priority"}<=set(row) for row in rows.values())
