from __future__ import annotations
import hashlib,json
from pathlib import Path
import yaml

def load_config(path="config/ml_training.yaml"):
    value=yaml.safe_load(Path(path).read_text())
    value["config_hash"]=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return value
