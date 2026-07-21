"""Append-only JSONL journal for live decisions and later outcomes."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


_LOCK = threading.Lock()


class PaperDecisionLogger:
    """Persist immutable snapshots; lifecycle changes are separate events."""

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        configured = path or os.getenv("TRADESCOR_PAPER_LOG_PATH")
        self.path = Path(configured) if configured else Path(__file__).resolve().parents[1] / "runtime" / "paper_decisions.jsonl"

    def record_decision(self, decision: dict[str, object]) -> bool:
        decision_id = str(decision.get("decision_id") or "")
        if not decision_id:
            raise ValueError("decision_id is required")
        with _LOCK:
            if self._has_created(decision_id):
                return False
            self._append({"event_type": "decision_created", "recorded_at": _now(), "decision_id": decision_id, "setup_id": (decision.get("setup") or {}).get("setup_id"), "snapshot": decision})
        return True

    def record_outcome(self, *, decision_id: str, setup_id: str | None, outcome: str, mfe: float | None = None, mae: float | None = None, realized_r: float | None = None, outcome_time: object = None, details: dict[str, object] | None = None) -> None:
        if not decision_id or not outcome:
            raise ValueError("decision_id and outcome are required")
        with _LOCK:
            self._append({"event_type": "outcome_recorded", "recorded_at": _now(), "decision_id": decision_id, "setup_id": setup_id, "outcome": outcome, "mfe": mfe, "mae": mae, "realized_r": realized_r, "outcome_time": str(outcome_time or _now()), "details": details or {}})

    def record_lifecycle(self, *, decision_id: str, setup_id: str, state: str, event_time: object, details: dict[str, object] | None = None) -> None:
        with _LOCK:
            self._append({"event_type": "setup_lifecycle", "recorded_at": _now(), "decision_id": decision_id, "setup_id": setup_id, "state": state, "event_time": str(event_time), "details": details or {}})

    def read_events(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _has_created(self, decision_id: str) -> bool:
        return any(event.get("event_type") == "decision_created" and event.get("decision_id") == decision_id for event in self.read_events())

    def _append(self, event: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True, default=str, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
