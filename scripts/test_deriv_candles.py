#!/usr/bin/env python3
"""Raw, independent Deriv history diagnostic using a discovered symbol."""
import json,os,sys
import websocket,certifi
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from providers.deriv_provider import normalize_deriv_candles

ENDPOINT=os.getenv("DERIV_PUBLIC_WS_URL","wss://ws.binaryws.com/websockets/v3")
CONNECT_URL=f"{ENDPOINT}?app_id={os.getenv('DERIV_PUBLIC_APP_ID','1089')}"
def exchange(ws,payload):ws.send(json.dumps(payload));raw=ws.recv();print(raw);result=json.loads(raw);return result
def main():
    ws=None;request=None;raw_error=None
    try:
        ws=websocket.create_connection(CONNECT_URL,timeout=15,sslopt={"ca_certs":certifi.where()});symbols=exchange(ws,{"active_symbols":"brief","product_type":"basic","req_id":1001})
        if symbols.get("error"):raise RuntimeError(json.dumps(symbols["error"]))
        record=next((row for row in symbols.get("active_symbols",[]) if "synthetic" in " ".join(str(row.get(key,"")) for key in ("market","submarket","market_display_name")).lower()),None)
        if not record:raise RuntimeError("No Derived Index was discovered")
        symbol=record.get("symbol") or record.get("underlying_symbol");print("DERIV_SYMBOL_SELECTED",json.dumps(record,sort_keys=True));request={"ticks_history":symbol,"end":"latest","count":500,"style":"candles","granularity":300,"req_id":1002};print("DERIV_HISTORY_SENT",json.dumps(request));history=exchange(ws,request)
        if history.get("error"):raw_error=history["error"];raise RuntimeError(json.dumps(raw_error))
        if history.get("msg_type")!="candles":raise RuntimeError(f"Unexpected msg_type: {history.get('msg_type')}")
        rows=normalize_deriv_candles(history.get("candles"));print("DERIV_HISTORY_NORMALIZED",len(rows));print("FIRST",rows[0]);print("LAST",rows[-1]);return 0
    except Exception as exc:
        print("FAILED",{"exception_class":type(exc).__name__,"exception_message":str(exc),"endpoint":ENDPOINT,"request":request,"deriv_error":raw_error},file=sys.stderr);return 1
    finally:
        if ws:
            try:ws.close()
            except Exception:pass
if __name__=="__main__":raise SystemExit(main())
