"""Contracts for strategy-backed likely retracement zones."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


def test_retracement_zone_reuses_possible_setup_range():
    assert "setup.setup_zone.high" in JS
    assert "setup.setup_zone.low" in JS
    assert "zonePriceLabel(zoneLabel, setup.zone)" in JS


def test_only_current_primary_setup_can_render():
    assert "setups.slice(0, 1)" in JS
    assert "enforcePossibleSetupRules" in JS


def test_retracement_state_is_price_and_timing_aware():
    assert "function retracementZoneState" in JS
    for state in ("Not reached", "In retracement zone", "Reacting", "Left zone", "Missed retracement"):
        assert state in JS
    assert "current >= zone.low && current <= zone.high" in JS


def test_bullish_and_bearish_zones_have_subtle_distinct_tints():
    assert ".possible-setup-zone" in CSS
    assert "rgba(56,189,248,.08)" in CSS
    assert ".possible-setup-zone.sell" in CSS
    assert "rgba(245,158,11,.08)" in CSS


def test_path_guidance_points_to_zone_without_inventing_range():
    assert "zoneEdgePrice" in JS
    assert '"Retrace"' in JS
    assert "if (!zone || ![zone.low, zone.high].every(Number.isFinite)) return" in JS
