from pathlib import Path
import pandas as pd

class DerivedReplayCandleStore:
    def __init__(self,root="data/replay_datasets"):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def save(self,dataset_id,candles):candles.to_json(self.root/f"{dataset_id}.json",orient="records")
    def load(self,dataset_id):
        path=self.root/f"{dataset_id}.json"
        if not path.exists():raise FileNotFoundError("Replay dataset is not cached.")
        rows=pd.read_json(path);rows["time"]=pd.to_numeric(rows.time).astype("int64");return rows

