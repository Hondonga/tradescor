"""Long-lived, reconnecting backend client for Deriv's public WebSocket API."""

from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Callable

from providers.deriv_connection_modes import (
    DERIV_PUBLIC_MARKET_DATA,
    DerivConnectionMode,
    require_public_market_data_request,
    public_market_data_connect_url,
)
from providers.runtime_health import runtime_health


class DerivAPIError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message); self.code = code; self.details = details or {}

    def as_dict(self): return {"code": self.code, "message": str(self), "details": self.details}


class DerivWebSocketClient:
    """Public market-data client. It deliberately has no authentication API."""
    URL = DERIV_PUBLIC_MARKET_DATA.endpoint

    def __init__(self, url: str | None = None, *, mode: DerivConnectionMode = DerivConnectionMode.DERIV_PUBLIC_MARKET_DATA,
                 ping_interval: float = 25, request_timeout: float = 15,
                 websocket_factory=None, autostart: bool = True):
        if mode != DerivConnectionMode.DERIV_PUBLIC_MARKET_DATA:
            raise ValueError("Authenticated Deriv trading transport is not part of the current milestone.")
        if url is not None and url != self.URL:
            raise ValueError("Public Deriv chart data must use the official public WebSocket endpoint.")
        self.mode=mode; self.url=self.URL; self.authentication_required=False
        self.ping_interval=ping_interval; self.request_timeout=request_timeout
        self._factory=websocket_factory; self._ws=None; self._running=False; self._thread=None
        self._req_id=0; self._lock=threading.RLock(); self._pending={}; self._subscriptions={}; self._server_offset=0.0
        self._status_listeners=[]
        if autostart: self.start()

    def start(self):
        with self._lock:
            if self._running: return
            self._running=True;runtime_health.connection("CONNECTING"); self._thread=threading.Thread(target=self._run, name="deriv-market-data", daemon=True); self._thread.start()

    def request(self, payload: dict, timeout: float | None = None) -> dict:
        require_public_market_data_request(payload)
        self.start(); req_id=self._next_id(); response_queue=queue.Queue(maxsize=1)
        message={**payload,"req_id":req_id}; self._pending[req_id]=response_queue
        try:
            self._send_when_connected(message, timeout or self.request_timeout)
            result=response_queue.get(timeout=timeout or self.request_timeout)
        except queue.Empty as exc:
            raise DerivAPIError("timeout", "Deriv market-data request timed out.", {"req_id":req_id}) from exc
        finally: self._pending.pop(req_id,None)
        if result.get("error"):
            error=result["error"]; raise DerivAPIError(str(error.get("code","deriv_error")),str(error.get("message","Deriv request failed.")),error)
        return result

    def subscribe(self, symbol: str, callback: Callable[[dict],None]) -> str:
        local_id=f"ticks:{symbol}"
        with self._lock:
            existed=local_id in self._subscriptions
            row=self._subscriptions.setdefault(local_id,{"symbol":symbol,"callbacks":[],"provider_id":None})
            if callback not in row["callbacks"]: row["callbacks"].append(callback)
        if existed:
            return local_id
        result=self.request({"ticks":symbol,"subscribe":1})
        tick=result.get("tick") or {}
        if result.get("msg_type")!="tick" or tick.get("symbol")!=symbol or not (result.get("subscription") or {}).get("id"):
            raise DerivAPIError("invalid_subscription","Deriv returned an invalid initial tick subscription.",{"symbol":symbol,"response_keys":sorted(result)})
        provider_id=((result.get("subscription") or {}).get("id")); row["provider_id"]=provider_id
        return local_id

    def unsubscribe(self, local_id: str, callback=None):
        with self._lock:
            row=self._subscriptions.get(local_id)
            if not row:return
            if callback in row["callbacks"]: row["callbacks"].remove(callback)
            if callback is not None and row["callbacks"]: return
            self._subscriptions.pop(local_id,None)
        if row.get("provider_id"):
            try:self.request({"forget":row["provider_id"]},timeout=5)
            except DerivAPIError:pass

    def server_time(self): return int(time.time()+self._server_offset)

    def close(self):
        self._running=False
        if self._ws:
            try:self._ws.close()
            except Exception:pass

    def add_status_listener(self,callback):
        if callback not in self._status_listeners:self._status_listeners.append(callback)
    def _notify_status(self,status):
        for callback in list(self._status_listeners):
            try:callback(status)
            except Exception:pass

    def _next_id(self):
        with self._lock:self._req_id+=1;return self._req_id

    def _send_when_connected(self,message,timeout):
        end=time.monotonic()+timeout
        while self._running and time.monotonic()<end:
            ws=self._ws
            if ws:
                try:ws.send(json.dumps(message));return
                except Exception:self._ws=None
            time.sleep(.05)
        raise DerivAPIError("disconnected","Deriv market data is reconnecting.")

    def _run(self):
        backoff=1.0
        while self._running:
            try:
                self._ws=self._connect(); backoff=1.0; self._restore_subscriptions(); self._notify_status("connected");runtime_health.connection("CONNECTED");last_ping=time.monotonic()
                while self._running:
                    if time.monotonic()-last_ping>=self.ping_interval:
                        self._ws.send(json.dumps({"ping":1,"req_id":self._next_id()})); last_ping=time.monotonic()
                    raw=self._ws.recv()
                    if not raw: raise ConnectionError("Deriv WebSocket closed")
                    self._on_message(json.loads(raw));runtime_health.heartbeat()
            except Exception:
                self._ws=None;self._notify_status("reconnecting");runtime_health.connection("RECONNECTING")
                if self._running: time.sleep(backoff); backoff=min(backoff*2,30)

    def _connect(self):
        if self._factory:return self._factory(self.url)
        try:import websocket
        except ImportError as exc:raise DerivAPIError("dependency_missing","Install websocket-client for Deriv live data.") from exc
        import certifi
        connection=websocket.create_connection(public_market_data_connect_url(),timeout=10,sslopt={"ca_certs":certifi.where()})
        connection.settimeout(max(30,self.ping_interval+5))
        return connection

    def _on_message(self,data):
        runtime_health.heartbeat()
        req_id=data.get("req_id")
        pending=self._pending.get(req_id)
        if pending:
            try:pending.put_nowait(data)
            except queue.Full:pass
        if data.get("time") is not None:
            try:self._server_offset=float(data["time"])-time.time()
            except (TypeError,ValueError):pass
        if data.get("tick") or data.get("subscription"):self._dispatch_subscription(data)

    def _dispatch_subscription(self,data):
        provider_id=((data.get("subscription") or {}).get("id")); tick=data.get("tick") or {}; symbol=tick.get("symbol")
        with self._lock: rows=list(self._subscriptions.values())
        for row in rows:
            if (provider_id and row.get("provider_id")==provider_id) or (symbol and row.get("symbol")==symbol):
                if provider_id:row["provider_id"]=provider_id
                for callback in list(row["callbacks"]):
                    try:callback(data)
                    except Exception:pass

    def _restore_subscriptions(self):
        with self._lock: rows=list(self._subscriptions.values())
        for row in rows:
            # A row with no provider id is a brand-new subscription whose
            # request is still about to be sent by ``subscribe``. Restoring it
            # here would race that request and Deriv correctly rejects the
            # second request as "already subscribed".
            if not row.get("provider_id"):
                continue
            # The receive loop cannot synchronously wait for its own response.
            row["provider_id"]=None
            self._ws.send(json.dumps({"ticks":row["symbol"],"subscribe":1,"req_id":self._next_id()}))
