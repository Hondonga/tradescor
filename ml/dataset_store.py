from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

class DatasetStore:
    def __init__(self,root="data/ml"):
        self.root=Path(root);self.datasets=self.root/"datasets";self.reports=self.root/"reports";self.checkpoints=self.root/"checkpoints"
        for path in (self.datasets,self.reports,self.checkpoints):path.mkdir(parents=True,exist_ok=True)
    def save(self,dataset_id,snapshots,manifest,report):
        folder=self.datasets/dataset_id;frame=pd.DataFrame([row.as_record() for row in snapshots]);sequences=np.asarray([row.sequence for row in snapshots],dtype=np.float32);ids=np.asarray([row.metadata["snapshot_id"] for row in snapshots]);checksum=_logical_checksum(frame,sequences,ids);manifest={**manifest,"checksum":checksum};manifest_path=folder/"manifest.json"
        if manifest_path.exists():
            existing=json.loads(manifest_path.read_text())
            if existing.get("checksum")==checksum:return existing
            raise RuntimeError("Frozen ML dataset cannot be overwritten. Create a new dataset version.")
        folder.mkdir(parents=True,exist_ok=False);tabular=folder/"features.parquet";frame.to_parquet(tabular,index=False,engine="pyarrow");np.savez_compressed(folder/"sequences.npz",sequences=sequences,snapshot_ids=ids);_json(manifest_path,manifest);_json(self.reports/f"{dataset_id}.json",report);(self.reports/f"{dataset_id}.html").write_text(_html(report),encoding="utf-8");return manifest
    def list(self):return [json.loads(path.read_text()) for path in sorted(self.datasets.glob("*/manifest.json"),reverse=True)]
    def manifest(self,dataset_id):return json.loads((self.datasets/dataset_id/"manifest.json").read_text())
    def report(self,dataset_id):return json.loads((self.reports/f"{dataset_id}.json").read_text())
    def save_checkpoint(self,dataset_id,payload):_json(self.checkpoints/f"{dataset_id}.json",payload)
    def checkpoint(self,dataset_id):
        path=self.checkpoints/f"{dataset_id}.json";return json.loads(path.read_text()) if path.exists() else None
def _json(path,payload):path.write_text(json.dumps(payload,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
def _logical_checksum(frame,sequences,ids):
    digest=hashlib.sha256();digest.update(frame.to_json(orient="records",date_format="iso",double_precision=15).encode());digest.update(sequences.tobytes());digest.update("\n".join(map(str,ids)).encode());return digest.hexdigest()
def _html(report):return "<!doctype html><meta charset='utf-8'><title>TradeScor ML Dataset Report</title><style>body{background:#080b10;color:#dbe5f3;font:14px system-ui;padding:32px}pre{white-space:pre-wrap;background:#101722;padding:20px;border-radius:8px}</style><h1>TradeScor ML Dataset Report</h1><p>No model training or accuracy is included.</p><pre>"+json.dumps(report,indent=2,default=str).replace("&","&amp;").replace("<","&lt;")+"</pre>"
