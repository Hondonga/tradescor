"""Phase 2 checkpoints 8, 9: golden-path label/product-language translation
and default chart density limits. Backend label/blocker translation is
verified here; frontend density limits (max_default_right_edge_tags=7, etc.)
are verified in frontend/src/components/chart/chart-price-tags.test.tsx and
frontend/src/lib/overlay-density.test.ts.
"""
from analysis.blocker_translations import translate_blocker, translate_next_requirement


def test_plan_geometry_translates_to_the_general_validation_message():
    assert translate_blocker("plan_geometry") == (
        "The setup exists, but the complete entry, stop and target geometry has not passed validation."
    )
    assert "plan_geometry" not in translate_blocker("plan_geometry")


def test_target_scope_mismatch_translates_directionally():
    assert translate_next_requirement("TARGET_SCOPE_MISMATCH", direction="bearish") == (
        "Wait for a fresh unswept structural objective below the proposed sell entry."
    )
    assert translate_next_requirement("TARGET_SCOPE_MISMATCH", direction="bullish") == (
        "Wait for a fresh unswept structural objective above the proposed buy entry."
    )
    assert "TARGET_SCOPE_MISMATCH" not in translate_next_requirement("TARGET_SCOPE_MISMATCH", direction="bearish")


def test_waiting_for_structure_confirmation_has_a_human_translation():
    assert translate_blocker("waiting_for_structure_confirmation") == "Waiting for completed M5 structure confirmation."


def test_unmapped_codes_never_leak_as_raw_underscored_text():
    # Even an unmapped code must not pass through verbatim with underscores;
    # the fallback formatter title-cases and adds punctuation.
    translated = translate_blocker("some_new_unmapped_code")
    assert "_" not in translated
    assert translated.endswith(".")
