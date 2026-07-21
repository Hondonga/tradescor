import time

from providers.deriv_provider import DerivAPIError, DerivProvider, normalize_active_symbol
from providers.runtime_health import PIPELINE_STAGES, PipelineTrace


class FakeClient:
    def __init__(self, histories=None):
        self.histories=list(histories or [])
    def request(self,payload):
        if "active_symbols" in payload:
            return {"active_symbols":[{"symbol":"R_50","display_name":"Volatility 50 Index","market":"synthetic_index","submarket":"random_index","subgroup":"synthetics","pip":.0001,"exchange_is_open":1}]}
        result=self.histories.pop(0)
        if isinstance(result,Exception):raise result
        return {"candles":result}
    def close(self):pass


def candle(epoch,close=100):return {"epoch":epoch,"open":close,"high":close+1,"low":close-1,"close":close}


def test_pipeline_trace_exposes_every_required_stage():
    trace=PipelineTrace("R_50","M5");trace.start("HISTORY_REQUEST").pass_("HISTORY_REQUEST",10).ready();payload=trace.as_dict()
    assert [row["stage"] for row in payload["stages"]]==list(PIPELINE_STAGES)
    assert payload["state"]=="ready" and payload["stages"][2]["record_count"]==10


def test_current_incomplete_candle_is_excluded(monkeypatch):
    now=int(time.time());base=(now//300)*300
    provider=DerivProvider(FakeClient([[candle(base-300),candle(base)]]));provider.SYMBOL_TTL=999
    frame=provider.fetch_candles("R_50","M5",2)
    assert len(frame)==1 and bool(frame.iloc[-1].complete)


def test_empty_provider_response_does_not_overwrite_known_good(monkeypatch):
    now=int(time.time());base=(now//300)*300
    provider=DerivProvider(FakeClient([[candle(base-600),candle(base-300)],DerivAPIError("empty_history","empty")]))
    first=provider.fetch_candles("R_50","M5",2);provider.HISTORY_TTL=0
    second=provider.fetch_candles("R_50","M5",2)
    assert len(second)==len(first) and second.attrs["stale_data"] is True


def test_symbol_metadata_keeps_support_separate_from_availability():
    row=normalize_active_symbol({"symbol":"R_50","display_name":"Volatility 50 Index","market":"synthetic_index","submarket":"random_index","pip":.0001})
    assert row["provider_symbol"]=="R_50" and row["family_display"]=="Volatility"
    assert row["analysis_support_status"] in {"SUPPORTED","UNSUPPORTED_MODEL"}


def test_frontend_explicitly_authorizes_analysis_load_and_worker_is_process_isolated():
    api=open("frontend/src/lib/api.ts",encoding="utf-8").read();service=open("replay/derived_replay_service.py",encoding="utf-8").read()
    assert 'manual: "1"' in api and 'asset_class: "derived_index"' in api
    assert "ProcessPoolExecutor" in service and "ThreadPoolExecutor" not in service
