import json,sqlite3
from pathlib import Path
class SMCAcceptanceStore:
    def __init__(self,path="data/smc_acceptance.db"):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self._migrate()
    def connect(self):db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row;return db
    def _migrate(self):
        with self.connect() as db:db.executescript("""CREATE TABLE IF NOT EXISTS acceptance_schema_version(version INTEGER PRIMARY KEY,applied_at TEXT);INSERT OR IGNORE INTO acceptance_schema_version VALUES(1,datetime('now'));CREATE TABLE IF NOT EXISTS acceptance_datasets(dataset_id TEXT PRIMARY KEY,symbol TEXT,family TEXT,variant TEXT,checksum TEXT,quality TEXT,payload_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS acceptance_entities(entity_key TEXT PRIMARY KEY,dataset_id TEXT,replay_run_id TEXT,entity_type TEXT,symbol TEXT,creation_candle TEXT,confirmation_candle TEXT,payload_json TEXT NOT NULL);CREATE INDEX IF NOT EXISTS idx_acceptance_entity ON acceptance_entities(symbol,entity_type,creation_candle);CREATE TABLE IF NOT EXISTS acceptance_reports(report_id TEXT PRIMARY KEY,replay_run_id TEXT,dataset_id TEXT,created_at TEXT,payload_json TEXT NOT NULL);""")
    def save_dataset(self,row):
        with self.connect() as db:db.execute("INSERT OR REPLACE INTO acceptance_datasets VALUES(?,?,?,?,?,?,?)",(row["dataset_id"],row["symbol"],row["family"],row["variant"],row["checksum"],row["data_quality"],json.dumps(row,default=str)))
    def save_entities(self,dataset_id,run_id,entities):
        import hashlib
        with self.connect() as db:
            for row in entities:
                key=hashlib.sha256(json.dumps([run_id,row.get("replay_decision_id"),row.get("entity_type"),row.get("entity_id")],default=str).encode()).hexdigest();db.execute("INSERT OR IGNORE INTO acceptance_entities VALUES(?,?,?,?,?,?,?,?)",(key,dataset_id,run_id,row["entity_type"],row.get("symbol"),str(row.get("creation_candle")),str(row.get("confirmation_candle")),json.dumps(row,default=str)))
    def save_report(self,report_id,run_id,dataset_id,created_at,payload):
        with self.connect() as db:db.execute("INSERT OR REPLACE INTO acceptance_reports VALUES(?,?,?,?,?)",(report_id,run_id,dataset_id,created_at,json.dumps(payload,default=str)))
    def reports(self):
        with self.connect() as db:return [json.loads(x[0]) for x in db.execute("SELECT payload_json FROM acceptance_reports ORDER BY created_at DESC").fetchall()]
    def report(self,report_id):
        with self.connect() as db:row=db.execute("SELECT payload_json FROM acceptance_reports WHERE report_id=?",(report_id,)).fetchone();return json.loads(row[0]) if row else None

