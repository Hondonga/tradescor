from __future__ import annotations
import json,sqlite3
from pathlib import Path

class DerivedReplayStore:
    def __init__(self,path="data/derived_replay.db"):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self._migrate()
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row;db.execute("PRAGMA journal_mode=WAL");db.execute("PRAGMA busy_timeout=30000");return db
    def _migrate(self):
        with self.connect() as db:db.executescript("""
CREATE TABLE IF NOT EXISTS replay_schema_version(version INTEGER PRIMARY KEY,applied_at TEXT);INSERT OR IGNORE INTO replay_schema_version VALUES(1,datetime('now'));
CREATE TABLE IF NOT EXISTS replay_datasets(dataset_id TEXT PRIMARY KEY,checksum TEXT NOT NULL UNIQUE,payload_json TEXT NOT NULL,candles_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS replay_runs(replay_run_id TEXT PRIMARY KEY,dataset_id TEXT NOT NULL,provider_symbol TEXT,family TEXT,requested_strategy TEXT,start_time TEXT,end_time TEXT,configuration_hash TEXT,code_version TEXT,random_seed INTEGER,started_at TEXT,completed_at TEXT,status TEXT,error TEXT,current_index INTEGER DEFAULT -1,current_time TEXT,configuration_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_replay_runs_status ON replay_runs(status,started_at);
CREATE TABLE IF NOT EXISTS replay_decisions(decision_id TEXT PRIMARY KEY,replay_run_id TEXT NOT NULL,replay_time TEXT NOT NULL,base_candle_index INTEGER,payload_json TEXT NOT NULL,UNIQUE(replay_run_id,replay_time));
CREATE TABLE IF NOT EXISTS replay_setups(paper_setup_id TEXT PRIMARY KEY,replay_run_id TEXT NOT NULL,decision_id TEXT,setup_id TEXT,strategy TEXT,direction TEXT,entry REAL,stop REAL,tp1 REAL,tp2 REAL,risk_points REAL,created_at TEXT,entry_valid_until TEXT,state TEXT,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS replay_fills(paper_setup_id TEXT PRIMARY KEY,replay_run_id TEXT,fill_time TEXT,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS replay_outcome_events(event_id TEXT PRIMARY KEY,replay_run_id TEXT,paper_setup_id TEXT,event_time TEXT,event TEXT,payload_json TEXT NOT NULL,UNIQUE(paper_setup_id,event_time,event));
CREATE TABLE IF NOT EXISTS replay_outcomes(paper_setup_id TEXT PRIMARY KEY,replay_run_id TEXT,terminal_time TEXT,outcome TEXT,entry_filled INTEGER,realized_r REAL,tp1_hit INTEGER,tp2_hit INTEGER,stop_hit INTEGER,intracandle_ambiguous INTEGER,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS replay_excursions(paper_setup_id TEXT PRIMARY KEY,replay_run_id TEXT,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS replay_checkpoints(replay_run_id TEXT NOT NULL,candle_index INTEGER NOT NULL,replay_time TEXT,payload_json TEXT NOT NULL,PRIMARY KEY(replay_run_id,candle_index));
CREATE TABLE IF NOT EXISTS replay_configuration_snapshots(replay_run_id TEXT PRIMARY KEY,configuration_hash TEXT,payload_json TEXT NOT NULL);
""")
    def save_dataset(self,dataset,candles):
        payload=dataset.as_dict();serial=candles.to_json(orient="records")
        with self.connect() as db:db.execute("INSERT OR IGNORE INTO replay_datasets VALUES(?,?,?,?)",(dataset.dataset_id,dataset.checksum,json.dumps(payload,default=str),serial))
    def load_dataset(self,dataset_id):
        import pandas as pd
        from io import StringIO
        with self.connect() as db:row=db.execute("SELECT * FROM replay_datasets WHERE dataset_id=?",(dataset_id,)).fetchone()
        if not row:raise KeyError("Replay dataset not found.")
        return json.loads(row["payload_json"]),pd.read_json(StringIO(row["candles_json"]),orient="records")
    def create_run(self,run,configuration):
        row=run.as_dict()
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO replay_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(row["replay_run_id"],row["dataset_id"],row["provider_symbol"],row["family"],row["requested_strategy"],row["start_time"],row["end_time"],row["configuration_hash"],row["code_version"],row["random_seed"],row["started_at"],row["completed_at"],row["status"],None,-1,None,json.dumps(configuration,sort_keys=True,default=str)))
            db.execute("INSERT OR IGNORE INTO replay_configuration_snapshots VALUES(?,?,?)",(row["replay_run_id"],row["configuration_hash"],json.dumps(configuration,sort_keys=True,default=str)))
    def update_run(self,run_id,**values):
        allowed={"status","error","current_index","current_time","completed_at"};items=[(k,v) for k,v in values.items() if k in allowed]
        if items:
            with self.connect() as db:db.execute(f"UPDATE replay_runs SET {','.join(k+'=?' for k,_ in items)} WHERE replay_run_id=?",tuple(v for _,v in items)+(run_id,))
    def run(self,run_id):
        with self.connect() as db:row=db.execute("SELECT * FROM replay_runs WHERE replay_run_id=?",(run_id,)).fetchone();return dict(row) if row else None
    def runs(self):
        with self.connect() as db:return [dict(x) for x in db.execute("SELECT * FROM replay_runs ORDER BY started_at DESC").fetchall()]
    def save_decision(self,run_id,index,replay_time,snapshot):
        row=snapshot.as_dict();payload=row["payload"]
        with self.connect() as db:return bool(db.execute("INSERT OR IGNORE INTO replay_decisions VALUES(?,?,?,?,?)",(row["decision_id"],run_id,replay_time,index,json.dumps(payload,default=str,separators=(",",":")))).rowcount)
    def save_setup(self,run_id,setup,payload):
        row=setup.as_dict()
        with self.connect() as db:return bool(db.execute("INSERT OR IGNORE INTO replay_setups VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(row["paper_setup_id"],run_id,row["decision_id"],row["setup_id"],row["strategy"],row["direction"],row["entry"],row["stop"],row["tp1"],row.get("tp2"),row["risk_points"],row["created_at"],row.get("entry_valid_until"),row["state"],json.dumps(payload,default=str))).rowcount)
    def active_setups(self,run_id):
        with self.connect() as db:return [dict(x) for x in db.execute("SELECT * FROM replay_setups WHERE replay_run_id=? AND state IN ('waiting_for_fill','filled') ORDER BY created_at",(run_id,)).fetchall()]
    def update_setup(self,setup_id,state):
        with self.connect() as db:db.execute("UPDATE replay_setups SET state=? WHERE paper_setup_id=?",(state,setup_id))
    def save_fill(self,run_id,setup_id,fill):
        with self.connect() as db:db.execute("INSERT OR IGNORE INTO replay_fills VALUES(?,?,?,?)",(setup_id,run_id,fill.get("fill_time"),json.dumps(fill,default=str)))
    def fill(self,setup_id):
        with self.connect() as db:row=db.execute("SELECT * FROM replay_fills WHERE paper_setup_id=?",(setup_id,)).fetchone();return json.loads(row["payload_json"]) if row else None
    def save_outcome(self,run_id,setup_id,outcome,excursion):
        import hashlib
        with self.connect() as db:
            for event in outcome.get("event_log",[]):
                eid="re-"+hashlib.sha256(json.dumps([setup_id,event.get("event"),event.get("time")]).encode()).hexdigest()[:24];db.execute("INSERT OR IGNORE INTO replay_outcome_events VALUES(?,?,?,?,?,?)",(eid,run_id,setup_id,event.get("time"),event.get("event"),json.dumps(event,default=str)))
            if outcome.get("outcome")!="OPEN":db.execute("INSERT OR IGNORE INTO replay_outcomes VALUES(?,?,?,?,?,?,?,?,?,?,?)",(setup_id,run_id,outcome.get("terminal_time"),outcome.get("outcome"),int(bool(outcome.get("entry_filled"))),outcome.get("realized_r"),int(bool(outcome.get("tp1_hit"))),int(bool(outcome.get("tp2_hit"))),int(bool(outcome.get("stop_hit"))),int(bool(outcome.get("intracandle_ambiguous"))),json.dumps(outcome,default=str)))
            db.execute("INSERT OR REPLACE INTO replay_excursions VALUES(?,?,?)",(setup_id,run_id,json.dumps(excursion,default=str)))
    def save_checkpoint(self,run_id,index,replay_time,payload):
        with self.connect() as db:db.execute("INSERT OR IGNORE INTO replay_checkpoints VALUES(?,?,?,?)",(run_id,index,replay_time,json.dumps(payload,default=str)))
    def latest_checkpoint(self,run_id):
        with self.connect() as db:row=db.execute("SELECT payload_json FROM replay_checkpoints WHERE replay_run_id=? ORDER BY candle_index DESC LIMIT 1",(run_id,)).fetchone();return json.loads(row[0]) if row else None
    def rows(self,table,run_id):
        allowed={"replay_decisions","replay_setups","replay_outcomes","replay_excursions"}
        if table not in allowed:raise ValueError("Unsupported replay record type.")
        with self.connect() as db:
            rows=[dict(x) for x in db.execute(f"SELECT * FROM {table} WHERE replay_run_id=? ORDER BY rowid",(run_id,)).fetchall()]
        for row in rows:
            if "payload_json" in row:row["payload"]=json.loads(row.pop("payload_json"))
        return rows
