"""Namespace-isolated persistence for structural-target lifecycle events."""
import json
import sqlite3


class SMCTargetStore:
    def __init__(self,path=":memory:",namespace="live"):
        self.path=str(path);self.namespace=str(namespace);self.db=sqlite3.connect(self.path)
        self.db.execute("CREATE TABLE IF NOT EXISTS smc_targets(namespace TEXT,target_id TEXT,symbol TEXT,timeframe TEXT,payload TEXT,PRIMARY KEY(namespace,target_id))")
        self.db.execute("CREATE TABLE IF NOT EXISTS smc_target_events(id INTEGER PRIMARY KEY AUTOINCREMENT,namespace TEXT,target_id TEXT,event TEXT,event_time TEXT,payload TEXT)");self.db.commit()
    def upsert(self,target):
        self.db.execute("INSERT OR REPLACE INTO smc_targets VALUES(?,?,?,?,?)",(self.namespace,target["target_id"],target["symbol"],target["timeframe"],json.dumps(target,sort_keys=True,default=str)));self.db.commit()
    def append_event(self,target_id,event,event_time,payload=None):
        self.db.execute("INSERT INTO smc_target_events(namespace,target_id,event,event_time,payload) VALUES(?,?,?,?,?)",(self.namespace,target_id,event,str(event_time),json.dumps(payload or {},sort_keys=True,default=str)));self.db.commit()
    def get(self,target_id):
        row=self.db.execute("SELECT payload FROM smc_targets WHERE namespace=? AND target_id=?",(self.namespace,target_id)).fetchone();return json.loads(row[0]) if row else None
    def events(self,target_id):
        rows=self.db.execute("SELECT event,event_time,payload FROM smc_target_events WHERE namespace=? AND target_id=? ORDER BY id",(self.namespace,target_id)).fetchall();return [{"event":event,"time":time,"payload":json.loads(payload)} for event,time,payload in rows]
    def active(self,symbol,timeframe=None):
        sql="SELECT payload FROM smc_targets WHERE namespace=? AND symbol=?";args=[self.namespace,symbol]
        if timeframe:sql+=" AND timeframe=?";args.append(timeframe)
        return [json.loads(row[0]) for row in self.db.execute(sql,args).fetchall()]
    def close(self):self.db.close()
