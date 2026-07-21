from __future__ import annotations
import sqlite3
from datetime import date
from pathlib import Path

class StrategyGateDiagnosticsStore:
    def __init__(self,path="data/strategy_gate_diagnostics.db"):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self._migrate()
    def _connect(self):db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row;return db
    def _migrate(self):
        with self._connect() as db:db.executescript("""CREATE TABLE IF NOT EXISTS strategy_gate_daily(day TEXT,symbol TEXT,family TEXT,strategy TEXT,regime TEXT,gate TEXT,evaluations INTEGER DEFAULT 0,first_blocking_count INTEGER DEFAULT 0,near_miss_count INTEGER DEFAULT 0,trade_ready_count INTEGER DEFAULT 0,PRIMARY KEY(day,symbol,family,strategy,regime,gate));CREATE INDEX IF NOT EXISTS idx_gate_blockers ON strategy_gate_daily(strategy,gate,day);""")
    def record(self,*,symbol,family,strategy,regime,funnel,day=None):
        gate=funnel.get("first_blocking_gate") or "all_passed";near=int(funnel.get("passed_gate_count",0)>=max(1,funnel.get("total_gate_count",0)-2) and bool(funnel.get("first_blocking_gate")));ready=int(not funnel.get("first_blocking_gate"));key=(str(day or date.today()),symbol,family,strategy or "none",regime or "unknown",gate)
        with self._connect() as db:db.execute("INSERT INTO strategy_gate_daily VALUES(?,?,?,?,?,?,1,?,?,?) ON CONFLICT(day,symbol,family,strategy,regime,gate) DO UPDATE SET evaluations=evaluations+1,first_blocking_count=first_blocking_count+excluded.first_blocking_count,near_miss_count=near_miss_count+excluded.near_miss_count,trade_ready_count=trade_ready_count+excluded.trade_ready_count",key+(int(gate!="all_passed"),near,ready))
    def report(self,**filters):
        allowed={"symbol","family","strategy","regime","day"};where=[];args=[]
        for key,value in filters.items():
            if key in allowed and value:where.append(key+"=?");args.append(value)
        with self._connect() as db:rows=[dict(x) for x in db.execute("SELECT * FROM strategy_gate_daily"+(" WHERE "+" AND ".join(where) if where else ""),args).fetchall()]
        counts={};evaluations=near=ready=0
        for row in rows:evaluations+=row["evaluations"];near+=row["near_miss_count"];ready+=row["trade_ready_count"];counts[row["gate"]]=counts.get(row["gate"],0)+row["first_blocking_count"]
        return {"evaluations":evaluations,"first_blocking_gate_counts":counts,"most_common_blocker":max(counts,key=counts.get) if counts else "","near_miss_count":near,"trade_ready_count":ready}

