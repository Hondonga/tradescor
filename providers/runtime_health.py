"""Thread-safe live-data tracing and resource-health snapshots."""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

PIPELINE_STAGES=("ACTIVE_SYMBOL_RESOLUTION","PROVIDER_CONNECTION","HISTORY_REQUEST","HISTORY_RESPONSE","CANDLE_NORMALIZATION","COMPLETED_CANDLE_FILTER","TIMEFRAME_AGGREGATION","CACHE_WRITE","CACHE_READ","ANALYSIS_READY","ANALYSIS_STARTED","ANALYSIS_COMPLETED")

def _utc(): return datetime.now(timezone.utc).isoformat()

class PipelineTrace:
    def __init__(self,symbol,timeframe,provider_symbol=None):
        self.request_id=str(uuid.uuid4());self.symbol=symbol;self.provider_symbol=provider_symbol or symbol;self.timeframe=timeframe;self.state="loading"
        self._rows={name:{"stage":name,"status":"pending","started_at":None,"completed_at":None,"duration_ms":None,"record_count":None,"error_code":None,"error_message":None} for name in PIPELINE_STAGES}
    def start(self,stage):
        row=self._rows[stage];row["started_at"]=_utc();row["_started"]=time.perf_counter();return self
    def pass_(self,stage,count=None):
        row=self._rows[stage];row["started_at"]=row["started_at"] or _utc();row["completed_at"]=_utc();row["status"]="passed";row["record_count"]=count
        started=row.pop("_started",None);row["duration_ms"]=round((time.perf_counter()-started)*1000,3) if started else 0.0;return self
    def fail(self,stage,code,message):
        row=self._rows[stage];row["started_at"]=row["started_at"] or _utc();row["completed_at"]=_utc();row["status"]="failed";row["error_code"]=code;row["error_message"]=str(message);self.state="error"
        started=row.pop("_started",None);row["duration_ms"]=round((time.perf_counter()-started)*1000,3) if started else 0.0;return self
    def ready(self):self.state="ready";return self
    def as_dict(self):return {"request_id":self.request_id,"symbol":self.symbol,"provider_symbol":self.provider_symbol,"timeframe":self.timeframe,"state":self.state,"stages":[{k:v for k,v in row.items() if not k.startswith("_")} for row in self._rows.values()]}

class RuntimeHealth:
    def __init__(self):
        self.lock=threading.RLock();self.connection_state="DISCONNECTED";self.last_heartbeat=None;self.reconnect_count=0;self.provider_states={"deriv":{"state":"disconnected","last_update":None},"twelve_data":{"state":"disconnected","last_update":None}};self.history_latencies=deque(maxlen=100);self.request_latencies=deque(maxlen=100);self.traces=deque(maxlen=100);self.cache_lock_wait_ms=0.0;self.sqlite_lock_wait_ms=0.0;self.analysis_queue_depth=0;self.worker={"state":"idle","queue_depth":0,"pid":None,"cpu_time_seconds":0.0,"memory_bytes":0,"progress":None}
    def connection(self,state):
        with self.lock:
            if state=="RECONNECTING":self.reconnect_count+=1
            self.connection_state=state
            if state in {"CONNECTED","READY"}:self.last_heartbeat=_utc()
            previous=self.provider_states.get("deriv",{});mapped={"CONNECTED":"ready","READY":"ready","LOADING_SYMBOLS":"loading","LOADING_HISTORY":"loading","RATE_LIMITED":"rate_limited","PROVIDER_ERROR":"error","STALE":"stale","RECONNECTING":"loading","CONNECTING":"loading","DISCONNECTED":"disconnected"}.get(state,state.lower());now=_utc();self.provider_states["deriv"]={"state":mapped,"last_update":now,"last_success":now if mapped=="ready" else previous.get("last_success")}
    def provider(self,name,state,remaining_credits=None):
        with self.lock:
            previous=self.provider_states.get(name,{});now=_utc();self.provider_states[name]={"state":state,"last_update":now,"last_success":now if state=="ready" else previous.get("last_success"),**({"remaining_credits":remaining_credits if remaining_credits is not None else previous.get("remaining_credits")} if name=="twelve_data" else {})}
    def heartbeat(self):
        with self.lock:self.last_heartbeat=_utc()
    def add_trace(self,trace):
        with self.lock:self.traces.append(trace.as_dict())
    def observe_history(self,ms):
        with self.lock:self.history_latencies.append(float(ms))
    def observe_request(self,ms):
        with self.lock:self.request_latencies.append(float(ms))
    def latest_trace(self,symbol=None):
        with self.lock:return next((x for x in reversed(self.traces) if not symbol or x["provider_symbol"]==symbol),None)
    def snapshot(self):
        with self.lock:
            history=list(self.history_latencies);requests=list(self.request_latencies);state=self.connection_state;worker=dict(self.worker)
            healthy=state in {"CONNECTED","READY","STALE"} and state!="PROVIDER_ERROR"
            for name,row in self.provider_states.items():row.setdefault("last_success",None);row.setdefault("remaining_credits",None) if name=="twelve_data" else None
            return {"providers":dict(self.provider_states),"live_provider":{"state":state,"last_heartbeat":self.last_heartbeat,"reconnect_count":self.reconnect_count,"endpoint":"wss://ws.binaryws.com/websockets/v3"},"historical_worker":worker,"queues":{"analysis":self.analysis_queue_depth,"replay":worker.get("queue_depth",0)},"database":{"sqlite_lock_wait_ms":self.sqlite_lock_wait_ms},"cache":{"lock_wait_ms":self.cache_lock_wait_ms},"latency":{"flask_request_ms":round(sum(requests)/len(requests),3) if requests else None,"history_request_ms":round(sum(history)/len(history),3) if history else None,"event_loop_lag_ms":0.0},"healthy":healthy}

runtime_health=RuntimeHealth()
