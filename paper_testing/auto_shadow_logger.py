"""Immutable shadow records for Auto and every competing expert."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


_LOCK = threading.Lock()


class AutoShadowLogger:
    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path or os.getenv("TRADESCOR_AUTO_SHADOW_PATH") or Path(__file__).resolve().parents[1] / "runtime" / "auto_shadow.jsonl")

    def record(self, decision: dict[str, object]) -> bool:
        decision_id = str(decision.get("decision_id") or "")
        if not decision_id: raise ValueError("decision_id is required")
        with _LOCK:
            if self._exists(decision_id): return False
            router = decision.get("router") or {}
            self._append({"event_type": "auto_shadow_decision", "recorded_at": _now(), "decision_id": decision_id, "setup_id": (decision.get("setup") or {}).get("setup_id"), "regime": decision.get("regime"), "eligible_strategies": router.get("eligible_strategies", []), "candidates": router.get("candidates", []), "selected_candidate": router.get("selected_candidate"), "rejected_candidates": [row for row in router.get("candidates", []) if row.get("strategy_id") != router.get("selected_strategy")], "evidence_status": router.get("evidence_status"), "execution": decision.get("execution"), "user_output": decision.get("user_output"), "benchmarks": {"equal_weight_agreement": _agreement(router.get("candidates", [])), "no_trade": True}})
        return True

    def record_outcome(self, *, decision_id: str, outcomes: dict[str, object], outcome_time: object) -> None:
        with _LOCK: self._append({"event_type": "auto_shadow_outcome", "recorded_at": _now(), "decision_id": decision_id, "outcome_time": str(outcome_time), "outcomes": outcomes})

    def _exists(self, decision_id: str) -> bool:
        if not self.path.exists(): return False
        return any(json.loads(line).get("decision_id") == decision_id and json.loads(line).get("event_type") == "auto_shadow_decision" for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())

    def _append(self, row: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, default=str, separators=(",", ":")) + "\n"); stream.flush(); os.fsync(stream.fileno())


def _agreement(candidates: list[dict[str, object]]) -> str:
    directions = {row.get("direction") for row in candidates if row.get("eligible") and row.get("direction") in {"buy", "sell"}}
    return directions.pop() if len(directions) == 1 else "conflict" if len(directions) > 1 else "none"
def _now() -> str: return datetime.now(timezone.utc).isoformat()
