"""Append-only Derived Index decision snapshots."""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path

class DerivedSignalLogger:
    def __init__(self,path=None,enabled=None):
        self.path=Path(path or os.getenv("DERIVED_PAPER_LOG","runtime_data/derived_signals.jsonl"));self.enabled=(os.getenv("DERIVED_PAPER_LOG_ENABLED","0")=="1") if enabled is None else enabled
    def append_decision(self,record):
        if not self.enabled:return None
        snapshot=json.loads(json.dumps(record,default=str));snapshot_id="derived-snapshot-"+hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()[:20];snapshot={"event":"decision_created","snapshot_id":snapshot_id,**snapshot};self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8") as handle:handle.write(json.dumps(snapshot,separators=(",",":"))+"\n")
        return snapshot_id
    def append_outcome(self,snapshot_id,outcome):
        if not self.enabled:return None
        event={"event":"outcome_appended","snapshot_id":snapshot_id,**json.loads(json.dumps(outcome,default=str))};self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8") as handle:handle.write(json.dumps(event,separators=(",",":"))+"\n")
        return event
