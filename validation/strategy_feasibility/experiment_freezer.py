"""Freeze a completed experiment as a consumed development result.

Once frozen, the data window + parameter hash are recorded so the same data
cannot be silently re-tuned and re-reported as independent evidence. A second
freeze against an already-seen (window, parameter_hash) is flagged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DIR = Path("data/strategy_feasibility")


def _ledger_path(base: Path) -> Path:
    return base / "consumed_ledger.json"


def _load_ledger(base: Path) -> list[dict]:
    path = _ledger_path(base)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def freeze_experiment(spec, report: dict, base_dir: str | Path = DEFAULT_DIR) -> dict:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    window = f"{spec.start_time}..{spec.end_time}"
    fingerprint = {"strategy_id": spec.strategy_id, "window": window,
                   "symbols": sorted(spec.symbols), "parameter_hash": spec.parameter_hash()}

    ledger = _load_ledger(base)
    already = any(row["fingerprint"] == fingerprint for row in ledger)

    frozen = {"frozen_at": datetime.now(timezone.utc).isoformat(),
              "status": "DEVELOPMENT_RESULT_CONSUMED", "promotion": report["promotion"],
              "fingerprint": fingerprint, "spec": spec.to_dict(), "report": report,
              "data_previously_consumed": already,
              "warning": ("This (strategy, window, parameters) was already consumed. "
                          "Re-reporting it as independent evidence is invalid.") if already else None}

    out_path = base / f"{spec.experiment_id}.json"
    out_path.write_text(json.dumps(frozen, indent=2, default=str), encoding="utf-8")
    ledger.append({"experiment_id": spec.experiment_id, "fingerprint": fingerprint,
                   "outcome": report["outcome"], "frozen_at": frozen["frozen_at"]})
    _ledger_path(base).write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    return frozen
