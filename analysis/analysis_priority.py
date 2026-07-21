"""Bounded, observable analysis priority coordinator."""
from __future__ import annotations
import threading
from pathlib import Path
from contextlib import contextmanager
PRIORITY_1_WORKSPACE="PRIORITY_1_WORKSPACE";PRIORITY_2_WATCHLIST="PRIORITY_2_WATCHLIST";PRIORITY_3_RESEARCH_SCAN="PRIORITY_3_RESEARCH_SCAN";MODES={"FOCUSED","BALANCED","RESEARCH"}
LIVE_PRESSURE_MARKER=Path("/tmp/tradescor-live-priority")
class AnalysisPriorityCoordinator:
    def __init__(self):
        self.lock=threading.RLock();self.full=threading.Semaphore(1);self.light=threading.Semaphore(2);self.history=threading.Semaphore(1);self.research=threading.Semaphore(1);self.mode="FOCUSED";self.workspace={"symbol":"","running":False,"queued":False,"generation":0};self.watchlist={"queued":0,"running":0};self.research_state={"queued":0,"running":False};self.cache={};self.live_pressure=threading.Event()
    def set_mode(self,mode):
        value=str(mode).upper()
        if value not in MODES:raise ValueError("Mode must be FOCUSED, BALANCED, or RESEARCH.")
        with self.lock:self.mode=value
        return self.snapshot()
    def select_workspace(self,symbol):
        with self.lock:
            if self.workspace["symbol"]!=symbol:self.workspace["generation"]+=1
            self.workspace.update(symbol=symbol,queued=True);return self.workspace["generation"]
    def current(self,symbol,generation):
        with self.lock:return self.workspace["symbol"]==symbol and self.workspace["generation"]==generation
    @contextmanager
    def slot(self,priority,symbol=""):
        if priority==PRIORITY_1_WORKSPACE:
            generation=self.select_workspace(symbol);self.live_pressure.set();LIVE_PRESSURE_MARKER.touch();semaphore=self.full
        elif priority==PRIORITY_2_WATCHLIST:
            generation=None;semaphore=self.light
            with self.lock:self.watchlist["queued"]+=1
        else:
            generation=None;semaphore=self.research
            with self.lock:self.research_state["queued"]+=1
        semaphore.acquire()
        try:
            with self.lock:
                if priority==PRIORITY_1_WORKSPACE:self.workspace.update(queued=False,running=True)
                elif priority==PRIORITY_2_WATCHLIST:self.watchlist.update(queued=max(0,self.watchlist["queued"]-1),running=self.watchlist["running"]+1)
                else:self.research_state.update(queued=max(0,self.research_state["queued"]-1),running=True)
            yield generation
        finally:
            with self.lock:
                if priority==PRIORITY_1_WORKSPACE:self.workspace["running"]=False
                elif priority==PRIORITY_2_WATCHLIST:self.watchlist["running"]=max(0,self.watchlist["running"]-1)
                else:self.research_state["running"]=False
            semaphore.release()
            if priority==PRIORITY_1_WORKSPACE:
                self.live_pressure.clear()
                try:LIVE_PRESSURE_MARKER.unlink()
                except FileNotFoundError:pass
    def remember(self,symbol,decision,depth):
        with self.lock:self.cache[symbol]={"decision":decision,"analysis_depth":depth,"last_analysis":((decision or {}).get("meta") or {}).get("analysis_time"),"data_freshness":((decision or {}).get("readiness") or {}).get("state")}
    def cached(self,symbol):
        with self.lock:return self.cache.get(symbol)
    def should_yield_research(self):return self.live_pressure.is_set() or LIVE_PRESSURE_MARKER.exists()
    def snapshot(self):
        with self.lock:return {"mode":self.mode,"limits":{"full_analysis_workers":1,"lightweight_analysis_workers":2,"history_download_workers":1,"research_workers":1,"background_market_scan":False},"workspace":{k:v for k,v in self.workspace.items() if k!="generation"},"watchlist":dict(self.watchlist),"research":dict(self.research_state)}
coordinator=AnalysisPriorityCoordinator()
