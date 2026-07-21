"""Pair/regime evidence registry with small-sample shrinkage."""

from __future__ import annotations

import json
from pathlib import Path


GRADE_THRESHOLDS = ((100, "USABLE"), (50, "MODERATE"), (20, "EARLY"), (1, "INSUFFICIENT"), (0, "NO_EVIDENCE"))
CONSERVATIVE_PRIOR_R = -0.05


class PerformanceRegistry:
    def __init__(self, path: str | Path | None = None, records: list[dict[str, object]] | None = None) -> None:
        self.path = Path(path) if path else None
        self.records = list(records or self._read())

    def lookup(self, context: dict[str, object]) -> dict[str, object]:
        matches = [row for row in self.records if row.get("out_of_sample") is True and all(row.get(key) == value for key, value in context.items() if value not in {None, ""})]
        if not matches:
            return _empty_evidence()
        closed = sum(int(row.get("closed_trades", 0)) for row in matches)
        observed = sum(float(row.get("expectancy_r", 0) or 0) * int(row.get("closed_trades", 0)) for row in matches) / max(1, closed)
        variance = sum(float(row.get("expectancy_variance", 1) or 1) for row in matches) / len(matches)
        folds = len({row.get("evaluation_period") for row in matches})
        reliability = min(.9, closed / (closed + 40)) * min(1.0, max(.25, folds / 3)) * max(.4, 1 / (1 + variance))
        shrunk = reliability * observed + (1 - reliability) * CONSERVATIVE_PRIOR_R
        grade = evidence_grade(closed)
        multiplier = max(.70, min(1.10, 0.90 + max(-.20, min(.20, shrunk)) + reliability * .05))
        return {"closed_trades": closed, "expectancy_r": observed, "shrunk_expectancy_r": round(shrunk, 4), "reliability": round(reliability, 4), "evidence_grade": grade, "multiplier": round(multiplier, 4), "out_of_sample": True, "matching_folds": folds}

    def append(self, record: dict[str, object]) -> None:
        if record.get("out_of_sample") is not True:
            raise ValueError("Only out-of-sample evidence may enter the performance registry.")
        self.records.append(record)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.records, sort_keys=True, indent=2, default=str), encoding="utf-8")

    def _read(self) -> list[dict[str, object]]:
        if not self.path or not self.path.exists(): return []
        loaded = json.loads(self.path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, list) else []


def evidence_grade(closed_trades: int) -> str:
    return next(label for minimum, label in GRADE_THRESHOLDS if closed_trades >= minimum)


def _empty_evidence() -> dict[str, object]:
    return {"closed_trades": 0, "expectancy_r": None, "shrunk_expectancy_r": CONSERVATIVE_PRIOR_R, "reliability": 0.0, "evidence_grade": "NO_EVIDENCE", "multiplier": 0.90, "out_of_sample": True, "matching_folds": 0}
