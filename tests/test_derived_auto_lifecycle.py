from analysis.derived_auto_router import apply_auto_continuity,clear_auto_continuity
def test_active_setup_continuity_prevents_minor_flapping():
    clear_auto_continuity();apply_auto_continuity("x","a","RANGE","setup")
    row=apply_auto_continuity("x","b","RANGE","setup");assert row["current_selected_strategy"]=="a" and not row["selection_changed"]
def test_material_regime_change_allows_replacement():
    clear_auto_continuity();apply_auto_continuity("x","a","RANGE","setup");row=apply_auto_continuity("x","b","EXPANSION","new");assert row["current_selected_strategy"]=="b" and row["selection_changed"]
