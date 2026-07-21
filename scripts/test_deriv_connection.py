#!/usr/bin/env python3
"""Raw, independent Deriv active-symbol diagnostic."""
import json,os,sys
import websocket,certifi

ENDPOINT=os.getenv("DERIV_PUBLIC_WS_URL","wss://ws.binaryws.com/websockets/v3")
CONNECT_URL=f"{ENDPOINT}?app_id={os.getenv('DERIV_PUBLIC_APP_ID','1089')}"
REQUEST={"active_symbols":"brief","product_type":"basic","req_id":1001}
def main():
    ws=None;raw=None
    try:
        print("DERIV_CONNECT_START",ENDPOINT);ws=websocket.create_connection(CONNECT_URL,timeout=15,sslopt={"ca_certs":certifi.where()});print("CONNECTION OPENED");print("DERIV_CONNECT_SUCCESS");print("DERIV_ACTIVE_SYMBOLS_SENT",json.dumps(REQUEST));ws.send(json.dumps(REQUEST));raw=ws.recv();print(raw);payload=json.loads(raw)
        if payload.get("error"):raise RuntimeError(json.dumps(payload["error"]))
        if payload.get("msg_type")!="active_symbols":raise RuntimeError(f"Unexpected msg_type: {payload.get('msg_type')}")
        symbols=payload.get("active_symbols");
        if not isinstance(symbols,list) or not symbols:raise RuntimeError("active_symbols was missing or empty")
        print("DERIV_ACTIVE_SYMBOLS_RECEIVED",len(symbols));print("FIRST TEN RAW SYMBOLS")
        for row in symbols[:10]:print(json.dumps(row,sort_keys=True))
        return 0
    except Exception as exc:
        print("FAILED",file=sys.stderr);print("exception_class",type(exc).__name__,file=sys.stderr);print("exception_message",str(exc),file=sys.stderr);print("endpoint",ENDPOINT,file=sys.stderr);print("request_payload",json.dumps(REQUEST),file=sys.stderr);print("raw_response",raw,file=sys.stderr);print("close_code",getattr(ws,"close_status_code",None),file=sys.stderr);print("close_reason",getattr(ws,"close_reason",None),file=sys.stderr);return 1
    finally:
        if ws:
            try:ws.close()
            except Exception:pass
if __name__=="__main__":raise SystemExit(main())
