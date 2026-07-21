"""Shared contracts and deterministic lifecycle helpers for ICT 2022 v2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "ict_2022_v2.yaml"


def load_config() -> tuple[dict[str, object], str]:
    raw = CONFIG_PATH.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def evidence_result(*, result=None, timestamp=None, timeframe="", valid=False, evidence=None, rejection_reason=None, data_quality="valid", state=None, detected_candidates=None, rejection_reasons=None, thresholds_used=None):
    reasons=list(rejection_reasons or ([] if rejection_reason is None else [rejection_reason]))
    return {"result": result, "timestamp": iso(timestamp), "source_timeframe": timeframe, "valid": bool(valid), "evidence": evidence or [], "rejection_reason": rejection_reason, "data_quality": data_quality, "state": state or ("pass" if valid else "waiting"), "diagnostics": {"status": state or ("pass" if valid else "waiting"), "detected_candidates": detected_candidates or [], "selected_candidate": result, "rejection_reasons": reasons, "thresholds_used": thresholds_used or {}}}


def iso(value):
    if value is None: return None
    stamp = pd.Timestamp(value)
    stamp = stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
    return stamp.isoformat()


def stable_id(prefix: str, value: object) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:20]
    return f"{prefix}-{digest}"


def completed(frame):
    return frame.copy().sort_values("time").reset_index(drop=True) if frame is not None else pd.DataFrame()
