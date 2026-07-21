from __future__ import annotations
import json
from pathlib import Path

class ModelRegistry:
    def __init__(self,root="data/ml"):
        self.root=Path(root);self.models=self.root/"models";self.runs=self.root/"training_runs";self.reports=self.root/"training_reports"
        for path in (self.models,self.runs,self.reports):path.mkdir(parents=True,exist_ok=True)
    def save_run(self,run):
        path=self.runs/f"{run['run_id']}.json";temporary=path.with_suffix(".json.tmp");temporary.write_text(json.dumps(run,indent=2,sort_keys=True,default=str)+"\n");temporary.replace(path);return path
    def get(self,run_id):
        path=self.runs/f"{run_id}.json"
        if not path.exists():raise KeyError(run_id)
        return json.loads(path.read_text())
    def list(self):return sorted((json.loads(path.read_text()) for path in self.runs.glob("*.json")),key=lambda row:row.get("created_at",""),reverse=True)
