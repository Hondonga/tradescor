"""Versioned transactional SQLite storage for immutable decisions and events."""
from __future__ import annotations
import json,sqlite3
from pathlib import Path
class DerivedPaperStore:
    def __init__(self,path="data/derived_paper_testing.db"):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self._migrate()
    def connect(self):
        db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row;db.execute("PRAGMA foreign_keys=ON");return db
    def _migrate(self):
        with self.connect() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL);INSERT OR IGNORE INTO schema_version VALUES(1,datetime('now'));
CREATE TABLE IF NOT EXISTS paper_decisions(decision_id TEXT PRIMARY KEY,dedupe_key TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,analysis_candle_time TEXT NOT NULL,provider_symbol TEXT NOT NULL,family TEXT,strategy TEXT,regime TEXT,direction TEXT,research_mode INTEGER DEFAULT 0,payload_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_decisions_symbol_time ON paper_decisions(provider_symbol,analysis_candle_time);CREATE INDEX IF NOT EXISTS idx_decisions_strategy ON paper_decisions(strategy,family,regime);
CREATE TABLE IF NOT EXISTS paper_setups(paper_setup_id TEXT PRIMARY KEY,decision_id TEXT NOT NULL,setup_id TEXT NOT NULL UNIQUE,strategy TEXT,direction TEXT,entry REAL,stop REAL,tp1 REAL,tp2 REAL,risk_points REAL,tp1_rr REAL,created_at TEXT,confirmation_time TEXT,entry_valid_until TEXT,state TEXT,last_processed_time TEXT,research_mode INTEGER DEFAULT 0,payload_json TEXT NOT NULL,FOREIGN KEY(decision_id) REFERENCES paper_decisions(decision_id));
CREATE INDEX IF NOT EXISTS idx_setups_state ON paper_setups(state,strategy,direction);
CREATE TABLE IF NOT EXISTS paper_fills(fill_id INTEGER PRIMARY KEY AUTOINCREMENT,paper_setup_id TEXT NOT NULL UNIQUE,fill_time TEXT,requested_entry REAL,filled_entry REAL,fill_type TEXT,slippage_points REAL,payload_json TEXT NOT NULL,FOREIGN KEY(paper_setup_id) REFERENCES paper_setups(paper_setup_id));
CREATE TABLE IF NOT EXISTS paper_outcome_events(event_id TEXT PRIMARY KEY,paper_setup_id TEXT NOT NULL,event TEXT NOT NULL,event_time TEXT NOT NULL,price REAL,payload_json TEXT NOT NULL,UNIQUE(paper_setup_id,event,event_time,price));
CREATE INDEX IF NOT EXISTS idx_events_setup_time ON paper_outcome_events(paper_setup_id,event_time);
CREATE TABLE IF NOT EXISTS paper_outcomes(paper_setup_id TEXT PRIMARY KEY,outcome TEXT,terminal_reason TEXT,terminal_time TEXT,entry_filled INTEGER,realized_r REAL,tp1_hit INTEGER DEFAULT 0,tp2_hit INTEGER DEFAULT 0,stop_hit INTEGER DEFAULT 0,intracandle_ambiguous INTEGER DEFAULT 0,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS paper_excursions(paper_setup_id TEXT PRIMARY KEY,mfe_points REAL,mfe_r REAL,mfe_time TEXT,mae_points REAL,mae_r REAL,mae_time TEXT,maximum_price REAL,minimum_price REAL,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS paper_router_evaluations(decision_id TEXT PRIMARY KEY,payload_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_data_snapshots(data_snapshot_id TEXT PRIMARY KEY,created_at TEXT,payload_json TEXT NOT NULL);""")
    def insert_decision(self,snapshot):
        row=snapshot.as_dict() if hasattr(snapshot,"as_dict") else snapshot;payload=row["payload"]
        with self.connect() as db:
            cur=db.execute("INSERT OR IGNORE INTO paper_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",(row["decision_id"],row["dedupe_key"],row["created_at"],row["analysis_candle_time"],row["provider_symbol"],row.get("family"),row.get("selected_strategy"),(payload.get("market_context") or {}).get("regime"),(payload.get("decision") or {}).get("developing_direction"),int(bool(payload.get("research_mode"))),json.dumps(payload,default=str,separators=(",",":"))))
            existing=db.execute("SELECT decision_id FROM paper_decisions WHERE dedupe_key=?",(row["dedupe_key"],)).fetchone();return existing[0],bool(cur.rowcount)
    def insert_setup(self,setup,payload=None,research_mode=False):
        row=setup.as_dict() if hasattr(setup,"as_dict") else setup
        with self.connect() as db:
            cur=db.execute("INSERT OR IGNORE INTO paper_setups VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(row["paper_setup_id"],row["decision_id"],row["setup_id"],row["strategy"],row["direction"],row["entry"],row["stop"],row["tp1"],row.get("tp2"),row["risk_points"],row.get("tp1_rr"),row["created_at"],row.get("confirmation_time"),row.get("entry_valid_until"),row.get("state","waiting_for_fill"),None,int(bool(research_mode)),json.dumps(payload or row,default=str,separators=(",",":"))));return bool(cur.rowcount)
    def append_event(self,paper_setup_id,event,event_time,price=None,payload=None):
        import hashlib;event_id="pe-"+hashlib.sha256(json.dumps([paper_setup_id,event,event_time,price],default=str).encode()).hexdigest()[:24]
        with self.connect() as db:
            cur=db.execute("INSERT OR IGNORE INTO paper_outcome_events VALUES(?,?,?,?,?,?)",(event_id,paper_setup_id,event,str(event_time),price,json.dumps(payload or {},default=str,separators=(",",":"))));return bool(cur.rowcount)
    def save_fill(self,paper_setup_id,fill):
        with self.connect() as db:db.execute("INSERT OR IGNORE INTO paper_fills(paper_setup_id,fill_time,requested_entry,filled_entry,fill_type,slippage_points,payload_json) VALUES(?,?,?,?,?,?,?)",(paper_setup_id,fill.get("fill_time"),fill.get("requested_entry"),fill.get("filled_entry"),fill.get("fill_type"),fill.get("slippage_points"),json.dumps(fill,default=str,separators=(",",":"))))
    def save_outcome(self,paper_setup_id,outcome):
        with self.connect() as db:db.execute("INSERT OR REPLACE INTO paper_outcomes VALUES(?,?,?,?,?,?,?,?,?,?,?)",(paper_setup_id,outcome.get("outcome"),outcome.get("terminal_reason"),outcome.get("terminal_time"),int(bool(outcome.get("entry_filled"))),outcome.get("realized_r"),int(bool(outcome.get("tp1_hit"))),int(bool(outcome.get("tp2_hit"))),int(bool(outcome.get("stop_hit"))),int(bool(outcome.get("intracandle_ambiguous"))),json.dumps(outcome,default=str,separators=(",",":"))))
    def save_excursion(self,paper_setup_id,row):
        with self.connect() as db:db.execute("INSERT OR REPLACE INTO paper_excursions VALUES(?,?,?,?,?,?,?,?,?,?)",(paper_setup_id,row.get("mfe_points"),row.get("mfe_r"),row.get("mfe_time"),row.get("mae_points"),row.get("mae_r"),row.get("mae_time"),row.get("maximum_price"),row.get("minimum_price"),json.dumps(row,default=str,separators=(",",":"))))
    def update_setup(self,paper_setup_id,**values):
        allowed={"state","last_processed_time"};items=[(key,value) for key,value in values.items() if key in allowed]
        if not items:return
        with self.connect() as db:db.execute(f"UPDATE paper_setups SET {','.join(key+'=?' for key,_ in items)} WHERE paper_setup_id=?",tuple(value for _,value in items)+(paper_setup_id,))
    def rows(self,table,filters=None,limit=200):
        allowed={"paper_decisions":{"provider_symbol","family","strategy","regime","direction","research_mode"},"paper_setups":{"strategy","direction","state","research_mode"},"paper_outcomes":{"outcome","terminal_reason"}};where=[];args=[]
        for key,value in (filters or {}).items():
            if key in allowed.get(table,set()) and value not in (None,""):where.append(key+"=?");args.append(value)
        with self.connect() as db:return [dict(row) for row in db.execute(f"SELECT * FROM {table}"+(" WHERE "+" AND ".join(where) if where else "")+" ORDER BY rowid DESC LIMIT ?",(*args,int(limit))).fetchall()]
    def active_setups(self):return self._active()
    def _active(self):
        with self.connect() as db:return [dict(row) for row in db.execute("SELECT * FROM paper_setups WHERE state IN ('waiting_for_fill','filled','tp1_hit') ORDER BY created_at").fetchall()]
    def setup_detail(self,paper_setup_id):
        with self.connect() as db:
            setup=db.execute("SELECT * FROM paper_setups WHERE paper_setup_id=?",(paper_setup_id,)).fetchone()
            if not setup:return None
            decision=db.execute("SELECT * FROM paper_decisions WHERE decision_id=?",(setup["decision_id"],)).fetchone();fill=db.execute("SELECT * FROM paper_fills WHERE paper_setup_id=?",(paper_setup_id,)).fetchone();outcome=db.execute("SELECT * FROM paper_outcomes WHERE paper_setup_id=?",(paper_setup_id,)).fetchone();exc=db.execute("SELECT * FROM paper_excursions WHERE paper_setup_id=?",(paper_setup_id,)).fetchone();events=db.execute("SELECT * FROM paper_outcome_events WHERE paper_setup_id=? ORDER BY event_time",(paper_setup_id,)).fetchall();return {"original_decision":dict(decision),"paper_setup":dict(setup),"fill":dict(fill) if fill else None,"observed_outcome":dict(outcome) if outcome else None,"excursion":dict(exc) if exc else None,"timeline":[dict(row) for row in events]}
