"""Flask app for the ICT 2022 chart scanner."""

from __future__ import annotations

import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from providers.runtime_health import runtime_health
from providers.market_registry import unified_registry, resolve_market
from analysis.market_decision_normalizer import normalize_market_decision
from analysis.global_overlay_contract import normalize_global_decision
from analysis.analysis_priority import coordinator,PRIORITY_1_WORKSPACE,PRIORITY_2_WATCHLIST,PRIORITY_3_RESEARCH_SCAN
from analysis.smc.smc_data_readiness import evaluate_data_readiness
from analysis.decision_views import build_market_analysis,build_trade_plan
import json
import queue

from analysis import build_shared_analysis
from analysis.answer_qa import build_answer_qa
from analysis.direction import build_direction_debug
from analysis.decision_engine import build_decision
from analysis.dxy_confirmation import unavailable_dxy_confirmation
from analysis.entry_timing import evaluate_entry_timing
from analysis.news_risk import analyze_news_risk
from analysis.price_precision import display_precision
from analysis.time_context import build_temporal_context
from analysis.trade_metrics import build_trade_metrics
from analysis.trade_score import build_trade_score
from analysis.top_down_engine import analyze_top_down_market
from analysis.m5_execution_engine import build_m5_execution_plan
from analysis.temporal_validation import validate_temporal_analysis
from analysis.top_down_context import analyze_top_down_context
from analysis.trader_answers import (
    actionable_rejection_instruction,
    actionable_wait_instruction,
    build_trader_answers,
)
from data_feed import get_candles
from fvg_detector import detect_fvgs
from providers.multi_timeframe import get_multi_timeframe_context, normalize_context_depth
from providers.symbol_map import resolve_symbol
from providers.provider_router import get_provider
from providers.deriv_connection_modes import DERIV_PUBLIC_MARKET_DATA
from providers.deriv_ws_client import DerivAPIError
from analysis.derived_family_classifier import classify_derived_family
from analysis.derived_index_rules import derived_index_rules
from analysis.synthetic_volatility import synthetic_volatility_profile
from analysis.synthetic_spike_detector import detect_synthetic_spike
from analysis.derived_engine import analyze_derived_index
from analysis.derived_intelligence_service import get_derived_intelligence_service
from paper_testing.derived_signal_logger import DerivedSignalLogger
from paper_testing.derived_paper_service import DerivedPaperService
from replay.derived_replay_service import DerivedReplayService
from replay.derived_replay_dataset import acquire_deriv_dataset
from analysis.strategy_gate_diagnostics_store import StrategyGateDiagnosticsStore
from analysis.strategy_reachability_gate import production_strategy_status, NO_VALIDATED_STRATEGY_MESSAGE
from analysis.strategy_quarantine_registry import strategy_validation_registry, is_auto_eligible
from analysis.volatility_latest_setup_search import LatestVolatilitySetupSearch
from ml.dataset_builder import MLDatasetService
from ml.training import MLTrainingService
from validation.smc_acceptance_service import SMCAcceptanceService
from providers.deriv_live_stream import get_deriv_live_manager
from scanner.dxy_correlation import analyze_dxy_correlation, symbol_needs_dxy
from scanner.macro_dashboard import build_macro_dashboard, directional_bias_from_alignment
from scanner.market_phase import detect_market_phase
from scanner.multi_timeframe import analyze_top_down, required_timeframes
from scanner.session_engine import get_session_status
from strategies import analyze_strategy, normalize_strategy_key
from strategies.base import strategy_bias_to_legacy
from backtesting import run_backtest, build_report
from backtesting.engine import get_config


app = Flask(__name__)

@app.before_request
def _runtime_request_started():
    request._runtime_started=time.perf_counter()

@app.after_request
def _runtime_request_finished(response):
    started=getattr(request,"_runtime_started",None)
    if started is not None:runtime_health.observe_request((time.perf_counter()-started)*1000)
    return response

@app.get("/api/system/runtime-health")
def api_runtime_health():return jsonify(runtime_health.snapshot())

@app.get("/api/system/data-pipeline")
def api_data_pipeline():
    symbol=str(request.args.get("symbol","")).strip()
    return jsonify(runtime_health.latest_trace(symbol) or {"request_id":"","symbol":symbol,"provider_symbol":symbol,"timeframe":str(request.args.get("timeframe","M5")),"state":"loading","stages":[]})

@app.route("/api/system/analysis-priority",methods=["GET","POST"])
def api_analysis_priority():
    try:
        if request.method=="POST":coordinator.set_mode((request.get_json(silent=True) or {}).get("mode","FOCUSED"))
        return jsonify(coordinator.snapshot())
    except ValueError as error:return jsonify({"error":str(error)}),400

@app.get("/api/markets/registry")
def api_market_registry():
    rows,errors=unified_registry(get_provider(provider="deriv",asset_class="derived_index"));market_type=str(request.args.get("market_type","")).lower()
    if market_type and market_type!="all":rows=[row for row in rows if row["market_type"]==market_type]
    for row in rows:
        cached=coordinator.cached(row["provider_symbol"])
        if cached:row["cached_analysis"]={"decision":cached["decision"],"analysis_depth":cached["analysis_depth"],"last_analysis":cached["last_analysis"],"data_freshness":cached["data_freshness"]}
    return jsonify({"markets":rows,"provider_states":runtime_health.snapshot().get("providers",{}),"errors":errors})
_derived_paper_service = None
_derived_replay_service = None
_smc_acceptance_service = None
_latest_setup_search = None
_ml_dataset_service = None
_ml_training_service = None

def get_ml_training_service():
    global _ml_training_service
    if _ml_training_service is None:_ml_training_service=MLTrainingService()
    return _ml_training_service

@app.post("/api/ml/training/runs")
def api_ml_training_start():
    try:return jsonify(get_ml_training_service().start(request.get_json(silent=True) or {})),202
    except (ValueError,RuntimeError) as error:return jsonify({"error":str(error)}),409

@app.get("/api/ml/training/runs")
def api_ml_training_runs():return jsonify({"runs":get_ml_training_service().list(),"live_activation_available":False})

@app.get("/api/ml/training/runs/<run_id>")
@app.get("/api/ml/training/runs/<run_id>/progress")
def api_ml_training_run(run_id):
    try:return jsonify(get_ml_training_service().get(run_id))
    except KeyError:return jsonify({"error":"ML training run not found."}),404

@app.get("/api/ml/training/runs/<run_id>/report")
def api_ml_training_report(run_id):
    try:
        if request.args.get("format")=="html":return Response((get_ml_training_service().registry.reports/f"{run_id}.html").read_text(),mimetype="text/html")
        return jsonify(get_ml_training_service().report(run_id))
    except (KeyError,FileNotFoundError):return jsonify({"error":"ML training report not found."}),404

@app.post("/api/ml/training/runs/<run_id>/cancel")
def api_ml_training_cancel(run_id):
    try:return jsonify(get_ml_training_service().cancel(run_id))
    except KeyError:return jsonify({"error":"ML training run not found."}),404

@app.post("/api/ml/training/runs/<run_id>/validate")
def api_ml_training_validate(run_id):
    try:return jsonify(get_ml_training_service().validate(run_id))
    except KeyError:return jsonify({"error":"ML training run not found."}),404

def get_ml_dataset_service():
    global _ml_dataset_service
    if _ml_dataset_service is None:_ml_dataset_service=MLDatasetService(lambda:get_provider(provider="deriv",asset_class="derived_index"))
    return _ml_dataset_service

@app.post("/api/ml/datasets/build")
def api_ml_dataset_build():
    try:return jsonify(get_ml_dataset_service().build(request.get_json(silent=True) or {})),202
    except (ValueError,RuntimeError) as error:return jsonify({"error":str(error)}),409

@app.get("/api/ml/datasets")
def api_ml_datasets():return jsonify({"datasets":get_ml_dataset_service().list(),"training_enabled":False})

@app.get("/api/ml/datasets/<dataset_id>")
def api_ml_dataset(dataset_id):
    try:return jsonify(get_ml_dataset_service().get(dataset_id))
    except KeyError:return jsonify({"error":"ML dataset not found."}),404

@app.get("/api/ml/datasets/<dataset_id>/progress")
def api_ml_dataset_progress(dataset_id):
    try:return jsonify(get_ml_dataset_service().progress(dataset_id))
    except KeyError:return jsonify({"error":"ML dataset not found."}),404

@app.get("/api/ml/datasets/<dataset_id>/report")
def api_ml_dataset_report(dataset_id):
    try:
        if request.args.get("format")=="html":
            path=get_ml_dataset_service().store.reports/f"{dataset_id}.html"
            return Response(path.read_text(encoding="utf-8"),mimetype="text/html")
        return jsonify(get_ml_dataset_service().report(dataset_id))
    except FileNotFoundError:return jsonify({"error":"ML dataset report is not available."}),404

@app.post("/api/ml/datasets/<dataset_id>/validate")
def api_ml_dataset_validate(dataset_id):
    try:return jsonify(get_ml_dataset_service().validate(dataset_id))
    except FileNotFoundError:return jsonify({"error":"ML dataset is not complete."}),409

@app.post("/api/ml/datasets/<dataset_id>/<action>")
def api_ml_dataset_action(dataset_id,action):
    if action not in {"pause","resume","cancel"}:return jsonify({"error":"Unsupported dataset action."}),400
    try:return jsonify(get_ml_dataset_service().action(dataset_id,action))
    except KeyError:return jsonify({"error":"ML dataset not found."}),404

def get_latest_setup_search():
    global _latest_setup_search
    if _latest_setup_search is None:
        _latest_setup_search=LatestVolatilitySetupSearch(lambda:get_provider(provider="deriv",asset_class="derived_index"))
    return _latest_setup_search

@app.post("/api/workspace/latest-valid-setup")
def api_latest_valid_setup_start():
    try:return jsonify(get_latest_setup_search().start((request.get_json(silent=True) or {}).get("period_days",30))),202
    except ValueError as error:return jsonify({"error":str(error)}),400

@app.get("/api/workspace/latest-valid-setup/<job_id>")
def api_latest_valid_setup_status(job_id):
    try:return jsonify(get_latest_setup_search().result(job_id))
    except KeyError:return jsonify({"error":"Historical search job not found."}),404

@app.post("/api/workspace/latest-valid-setup/<job_id>/cancel")
def api_latest_valid_setup_cancel(job_id):
    try:return jsonify(get_latest_setup_search().cancel(job_id))
    except KeyError:return jsonify({"error":"Historical search job not found."}),404

@app.post("/api/workspace/latest-valid-setup/<job_id>/reveal-outcome")
def api_latest_valid_setup_reveal(job_id):
    try:return jsonify(get_latest_setup_search().reveal(job_id))
    except KeyError:return jsonify({"error":"Historical search job not found."}),404

def get_derived_paper_service():
    global _derived_paper_service
    if _derived_paper_service is None:_derived_paper_service=DerivedPaperService()
    return _derived_paper_service

def get_derived_replay_service():
    global _derived_replay_service
    if _derived_replay_service is None:_derived_replay_service=DerivedReplayService()
    return _derived_replay_service
def get_smc_acceptance_service():
    global _smc_acceptance_service
    if _smc_acceptance_service is None:_smc_acceptance_service=SMCAcceptanceService(get_derived_replay_service())
    return _smc_acceptance_service

TIMEFRAME_INTERVALS = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H2": "2h",
    "H4": "4h",
    "D1": "1day",
    "W1": "1week",
}


@app.route("/")
def index():
    """Show the charting page."""
    frontend=Path(__file__).resolve().parent/"frontend"/"dist"
    if (frontend/"index.html").exists():return send_from_directory(frontend,"index.html")
    return Response("TradeScor frontend build is unavailable. Run the frontend production build.",status=503,mimetype="text/plain")

@app.get("/assets/<path:filename>")
def frontend_assets(filename):
    frontend=Path(__file__).resolve().parent/"frontend"/"dist"/"assets"
    if frontend.exists():return send_from_directory(frontend,filename)
    return ("Frontend asset not found",404)

@app.get("/favicon.svg")
def frontend_favicon():
    frontend=Path(__file__).resolve().parent/"frontend"/"dist"
    if (frontend/"favicon.svg").exists():return send_from_directory(frontend,"favicon.svg")
    return ("Frontend favicon not found",404)

@app.get("/markets")
@app.get("/workspace")
@app.get("/research")
def frontend_route():return index()

def _paper_filters():
    return {key:request.args.get(key) for key in ("provider_symbol","family","strategy","regime","direction","outcome","research_mode") if request.args.get(key) not in (None,"")}

@app.get("/api/paper/summary")
def api_paper_summary():return jsonify(get_derived_paper_service().summary())
@app.get("/api/paper/decisions")
def api_paper_decisions():return jsonify({"decisions":get_derived_paper_service().decisions(_paper_filters(),request.args.get("limit",200,type=int))})
@app.get("/api/paper/setups")
def api_paper_setups():return jsonify({"setups":get_derived_paper_service().setups(_paper_filters(),request.args.get("limit",200,type=int))})
@app.get("/api/paper/outcomes")
def api_paper_outcomes():return jsonify({"outcomes":get_derived_paper_service().outcomes(_paper_filters(),request.args.get("limit",200,type=int))})
@app.get("/api/paper/active")
def api_paper_active():return jsonify({"active":get_derived_paper_service().active()})
@app.get("/api/paper/performance")
def api_paper_performance():return jsonify(get_derived_paper_service().performance(_paper_filters()))
@app.get("/api/paper/evidence")
def api_paper_evidence():return jsonify(get_derived_paper_service().evidence())
@app.get("/api/paper/setup/<paper_setup_id>")
def api_paper_setup(paper_setup_id):
    row=get_derived_paper_service().store.setup_detail(paper_setup_id);return (jsonify(row),200) if row else (jsonify({"error":"Paper setup not found."}),404)
@app.post("/api/paper/reconcile")
def api_paper_reconcile():return jsonify(get_derived_paper_service().reconcile())

@app.get("/api/strategy-diagnostics/gates")
def api_strategy_gate_diagnostics():return jsonify(StrategyGateDiagnosticsStore().report(**{key:request.args.get(key) for key in ("symbol","family","strategy","regime","day") if request.args.get(key)}))

@app.post("/api/replay/runs")
def api_create_replay_run():
    body=request.get_json(silent=True) or {};required=("provider_symbol","start_time","end_time")
    if any(not body.get(key) for key in required):return jsonify({"error":"provider_symbol, start_time, and end_time are required."}),400
    try:
        candles=body.get("candles")
        if candles is None:
            _,rows=acquire_deriv_dataset(get_provider("deriv"),provider_symbol=body["provider_symbol"],display_name=body.get("display_name",body["provider_symbol"]),family=body.get("family",""),start_time=body["start_time"],end_time=body["end_time"],base_timeframe=body.get("base_timeframe","M1"));candles=rows
        run=get_derived_replay_service().create_run(provider_symbol=body["provider_symbol"],display_name=body.get("display_name",body["provider_symbol"]),family=body.get("family",""),candles=candles,base_timeframe=body.get("base_timeframe","M1"),strategy=body.get("strategy","Auto"),metadata=body.get("metadata"),start_time=body["start_time"],end_time=body["end_time"],background=True);return jsonify(run),202
    except (ValueError,RuntimeError,DerivAPIError) as error:return jsonify({"error":str(error)}),400

@app.get("/api/replay/runs")
def api_replay_runs():return jsonify({"runs":get_derived_replay_service().list_runs()})
@app.get("/api/replay/runs/<run_id>")
def api_replay_run(run_id):
    row=get_derived_replay_service().get_run(run_id);return (jsonify(row),200) if row else (jsonify({"error":"Replay run not found."}),404)
@app.post("/api/replay/runs/<run_id>/pause")
def api_replay_pause(run_id):return _replay_action(get_derived_replay_service().pause,run_id)
@app.post("/api/replay/runs/<run_id>/resume")
def api_replay_resume(run_id):return _replay_action(get_derived_replay_service().resume,run_id)
@app.post("/api/replay/runs/<run_id>/cancel")
def api_replay_cancel(run_id):return _replay_action(get_derived_replay_service().cancel,run_id)
def _replay_action(action,run_id):
    try:return jsonify(action(run_id))
    except KeyError as error:return jsonify({"error":str(error)}),404
@app.get("/api/replay/runs/<run_id>/progress")
def api_replay_progress(run_id):return _replay_action(get_derived_replay_service().progress,run_id)
@app.get("/api/replay/runs/<run_id>/decisions")
def api_replay_decisions(run_id):return jsonify({"decisions":get_derived_replay_service().records(run_id,"decisions")})
@app.get("/api/replay/runs/<run_id>/setups")
def api_replay_setups(run_id):return jsonify({"setups":get_derived_replay_service().records(run_id,"setups")})
@app.get("/api/replay/runs/<run_id>/outcomes")
def api_replay_outcomes(run_id):return jsonify({"outcomes":get_derived_replay_service().records(run_id,"outcomes")})
@app.get("/api/replay/runs/<run_id>/report")
def api_replay_report(run_id):return _replay_action(get_derived_replay_service().report,run_id)
@app.post("/api/replay/runs/<run_id>/validate")
def api_replay_validate(run_id):return _replay_action(get_derived_replay_service().validate,run_id)

@app.post("/api/smc-validation/runs/<run_id>")
def api_smc_validate_run(run_id):
    try:return jsonify(get_smc_acceptance_service().validate_run(run_id,request.get_json(silent=True) or {}))
    except (KeyError,ValueError) as error:return jsonify({"error":str(error)}),400
@app.get("/api/smc-validation/reports")
def api_smc_validation_reports():return jsonify({"reports":get_smc_acceptance_service().reports()})
@app.get("/api/smc-validation/reports/<report_id>")
def api_smc_validation_report(report_id):
    row=get_smc_acceptance_service().report(report_id);return (jsonify(row),200) if row else (jsonify({"error":"Acceptance report not found."}),404)
@app.get("/api/smc-validation/reports/<report_id>/html")
def api_smc_validation_html(report_id):
    try:return get_smc_acceptance_service().html(report_id),200,{"Content-Type":"text/html; charset=utf-8"}
    except KeyError as error:return jsonify({"error":str(error)}),404
@app.get("/api/smc-validation/runs/<run_id>/decisions/<decision_id>")
def api_smc_decision_inspector(run_id,decision_id):
    try:return jsonify(get_smc_acceptance_service().inspect(run_id,decision_id))
    except KeyError as error:return jsonify({"error":str(error)}),404

@app.get("/api/strategy-reachability")
def api_strategy_reachability():
    path=Path(__file__).resolve().parent/"data"/"strategy_setup_proof"/"latest.json"
    if not path.exists():return jsonify({"error":"Strategy setup-proof report has not been generated."}),404
    try:
        report=json.loads(path.read_text(encoding="utf-8"));report["production_status"]=production_strategy_status()
        # Phase 6: this is the one registry-health diagnostics surface --
        # reachability (technical) and validation_registry (historical edge,
        # Auto/paper/live/ML eligibility) are reported side by side so no
        # caller needs to re-derive eligibility from raw proof data.
        # production_strategy_status() only knows raw fixture reachability,
        # not historical validation -- its own auto_eligible is stale here
        # and must never be trusted for anything Auto/paper/live-facing.
        report["production_status"]["auto_eligible"]=is_auto_eligible("volatility_structure_pullback")
        report["validation_registry"]=strategy_validation_registry()
        report["no_validated_strategy_message"]=NO_VALIDATED_STRATEGY_MESSAGE
        return jsonify(report)
    except ValueError:return jsonify({"error":"Strategy setup-proof report is invalid."}),500


@app.route("/api/candles")
def api_candles():
    """Return live candles in the format expected by Lightweight Charts."""
    query = None
    try:
        query = _get_chart_query()
        candles = _fetch_provider_candles(query)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": _friendly_market_error(str(error), query)}), 500

    return jsonify(
        {
            "symbol": query["display_symbol"],
            "display_symbol": query["display_symbol"],
            "api_symbol": query["api_symbol"],
            "asset_type": query["asset_type"],
            "timeframe": query["timeframe"],
            "interval": query["interval"],
            "bars": query["bars"],
            "time_metadata": candles.attrs.get("time_metadata", {}),
            "candles": _candles_to_chart_records(candles),
        }
    )


@app.route("/api/deriv/symbols")
def api_deriv_symbols():
    """Discover active Derived Indices from Deriv; no credentials are exposed."""
    try:
        symbols=get_provider(provider="deriv",asset_class="derived_index").list_symbols()
        for row in symbols: row["classification"]=classify_derived_family(row)
        return jsonify({"provider":"deriv","asset_class":"derived_index","cached_for_seconds":1800,"symbols":symbols})
    except RuntimeError as error:
        return jsonify({"error":"Data reconnecting","details":str(error),"symbols":[]}),503


@app.route("/api/deriv/candles")
def api_deriv_candles():
    symbol=str(request.args.get("symbol","")).strip();timeframe=str(request.args.get("timeframe","M5")).upper()
    try:
        count=max(1,min(int(request.args.get("count","300")),5000))
        if not symbol:raise ValueError("symbol is required")
        result=get_provider(provider="deriv",asset_class="derived_index").fetch_chart_candles(symbol,timeframe,count)
        print("DERIV_FLASK_RESPONSE",{"symbol":symbol,"valid":result["valid_count"]})
        return jsonify({"ok":True,"provider":"deriv","symbol":symbol,"timeframe":timeframe,"granularity":result["granularity"],"count":count,"received_count":result["received_count"],"valid_count":result["valid_count"],"candles":result["candles"]})
    except ValueError as error:return jsonify({"ok":False,"provider":"deriv","stage":"validation","symbol":symbol,"timeframe":timeframe,"error_type":type(error).__name__,"error_message":str(error),"deriv_error":None}),400
    except DerivAPIError as error:return jsonify({"ok":False,"provider":"deriv","stage":"history","symbol":symbol,"timeframe":timeframe,"error_type":type(error).__name__,"error_message":str(error),"deriv_error":error.as_dict()}),502
    except RuntimeError as error:return jsonify({"ok":False,"provider":"deriv","stage":"history","symbol":symbol,"timeframe":timeframe,"error_type":type(error).__name__,"error_message":str(error),"deriv_error":None}),502


@app.route("/api/debug/deriv/connection")
def api_debug_deriv_connection():
    endpoint=str(DERIV_PUBLIC_MARKET_DATA.endpoint)
    try:
        provider=get_provider(provider="deriv",asset_class="derived_index");response=provider.client.request({"active_symbols":"brief","product_type":"basic"});rows=response.get("active_symbols")
        if response.get("msg_type")!="active_symbols" or not isinstance(rows,list) or not rows:raise RuntimeError("Deriv active_symbols response was missing or empty.")
        return jsonify({"ok":True,"endpoint":endpoint,"connected":True,"response_msg_type":response.get("msg_type"),"symbol_count":len(rows),"sample_symbols":rows[:10],"error":None})
    except DerivAPIError as error:return jsonify({"ok":False,"stage":"active_symbols","endpoint":endpoint,"error_type":type(error).__name__,"error_message":str(error),"deriv_error":error.as_dict()}),502
    except Exception as error:return jsonify({"ok":False,"stage":"connection","endpoint":endpoint,"error_type":type(error).__name__,"error_message":str(error),"deriv_error":None}),502


@app.route("/api/deriv/profile")
def api_deriv_profile():
    try:
        symbol=str(request.args.get("symbol","")).strip()
        if not symbol:raise ValueError("symbol is required")
        provider=get_provider(provider="deriv",asset_class="derived_index")
        frames={timeframe:provider.fetch_candles(symbol,timeframe,300 if timeframe!="D1" else 180) for timeframe in ("D1","H4","H1","M15","M5")}
        result=analyze_derived_index(symbol=symbol,metadata={"provider_symbol":symbol,"display_name":request.args.get("display_name",symbol),"family":request.args.get("family","")},candles_by_timeframe=frames,analysis_time=pd.Timestamp.now(tz="UTC"))
        return jsonify({"provider":"deriv","asset_class":"derived_index","symbol":symbol,**result})
    except ValueError as error:return jsonify({"error":str(error)}),400
    except RuntimeError as error:return jsonify({"error":"Historical data unavailable","details":str(error)}),503


@app.route("/api/deriv/intelligence")
def api_deriv_intelligence():
    symbol=str(request.args.get("symbol","")).strip();timeframe=str(request.args.get("timeframe","M5")).upper()
    try:
        if not symbol:raise ValueError("symbol is required")
        if timeframe not in {"M1","M5","M15","M30","H1","H4","D1"}:raise ValueError("unsupported timeframe")
        provider=get_provider(provider="deriv",asset_class="derived_index");service=get_derived_intelligence_service(provider)
        intelligence=service.analyze(symbol,request.args.get("display_name") or symbol,timeframe,force=request.args.get("refresh")=="1")
        return jsonify({"ok":True,"intelligence":intelligence})
    except ValueError as error:return jsonify({"ok":False,"stage":"validation","error_type":type(error).__name__,"error_message":str(error)}),400
    except Exception as error:return jsonify({"ok":False,"stage":"market_intelligence","error_type":type(error).__name__,"error_message":str(error)}),503


@app.route("/api/stream/deriv")
def api_deriv_stream():
    """SSE projection of the shared backend Deriv subscription."""
    symbol=str(request.args.get("symbol","")).strip(); timeframe=str(request.args.get("timeframe","M5")).upper()
    if not symbol:return jsonify({"error":"symbol is required"}),400
    display_name=str(request.args.get("display_name",symbol));events=queue.Queue(maxsize=50);manager=get_deriv_live_manager()
    def callback(event):
        try:events.put_nowait(event)
        except queue.Full:
            try:events.get_nowait();events.put_nowait(event)
            except queue.Empty:pass
    try:consumer_id,generation=manager.acquire(symbol,timeframe,callback,display_name)
    except (RuntimeError,ValueError) as error:return jsonify({"error":"Data reconnecting","details":str(error)}),503
    @stream_with_context
    def stream():
        try:
            while True:
                try:
                    event=events.get(timeout=20);yield f"event: {event.get('event_type','stream_status')}\ndata: {json.dumps(event)}\n\n"
                except queue.Empty:yield "event: ping\ndata: {}\n\n"
        finally:manager.release(consumer_id)
    return Response(stream(),mimetype="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


@app.route("/api/debug/deriv/live")
def api_debug_deriv_live():return jsonify(get_deriv_live_manager().health())


@app.route("/api/fvg")
def api_fvg():
    """Return detected Fair Value Gap zones for live candles."""
    query = None
    try:
        query = _get_chart_query()
        candles = _fetch_provider_candles(query)
        fvgs = detect_fvgs(candles)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": _friendly_market_error(str(error), query)}), 500

    return jsonify(
        {
            "symbol": query["display_symbol"],
            "display_symbol": query["display_symbol"],
            "api_symbol": query["api_symbol"],
            "asset_type": query["asset_type"],
            "timeframe": query["timeframe"],
            "interval": query["interval"],
            "bars": query["bars"],
            "time_metadata": candles.attrs.get("time_metadata", {}),
            "fvg_zones": _to_json_records(fvgs),
        }
    )


@app.route("/api/analyze",methods=["GET","POST"])
def api_analyze():
    """Return one current ICT setup analysis for the selected chart."""
    query = None
    try:
        if request.method=="POST":
            payload=request.get_json(silent=True) or {};query=_get_replay_query(payload);query["bars"]=max(1,min(int(payload.get("bars",300)),2000))
        else:
            query = _get_chart_query(require_manual=True)
        priority=str(request.args.get("priority",PRIORITY_1_WORKSPACE));depth=str(request.args.get("analysis_depth","full")).lower();symbol=str(query["api_symbol"])
        if priority not in {PRIORITY_1_WORKSPACE,PRIORITY_2_WATCHLIST,PRIORITY_3_RESEARCH_SCAN}:priority=PRIORITY_1_WORKSPACE
        with coordinator.slot(priority,symbol) as generation:
            with coordinator.history:candles = _fetch_provider_candles(query)
            response = _build_lightweight_response(candles,query) if depth=="lightweight" else _build_analysis_response(candles, query)
            decision=response.get("decision") or {};decision["analysis_depth"]="lightweight" if depth=="lightweight" else "full";response["decision"]=decision
            if priority==PRIORITY_1_WORKSPACE and not coordinator.current(symbol,generation):return jsonify({"error":"OBSOLETE_WORKSPACE_ANALYSIS","cancelled":True}),409
            coordinator.remember(symbol,decision,decision["analysis_depth"])
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": _friendly_market_error(str(error), query)}), 500

    return jsonify(_acyclic_projection(response))

def _build_lightweight_response(candles,query):
    multi=get_multi_timeframe_context(query["api_symbol"],query["timeframe"],min(int(query["bars"]),300),depth="balanced",selected_candles=candles,provider=str(query.get("provider","twelve_data")),asset_class=str(query.get("asset_type","forex")));frames=multi["context"];temporal=build_temporal_context(selected_candles=multi["selected"]["candles"],context=frames,selected_timeframe=str(query["timeframe"]),replay=False);frames=temporal["context"];at=temporal["analysis_timestamp"];view=analyze_top_down_market(symbol=str(query["display_symbol"]),candles_by_timeframe=frames,analysis_timestamp=at);readiness=evaluate_data_readiness(frames,at,source=str(query.get("provider")));tf=view["timeframes"];external=(tf.get("H1") or {}).get("bias");internal=(tf.get("M15") or {}).get("bias");bias=(view.get("alignment") or {}).get("primary_direction");direction=bias if bias in {"buy","sell"} else None;blocker="Full setup geometry has not been requested.";decision_id=f"lightweight:{query['api_symbol']}:{int(pd.Timestamp(at).timestamp())}"
    market_analysis={"available":True,"regime":(view.get("regime") or {}).get("value"),"external_structure":external,"internal_structure":internal,"alignment":(view.get("alignment") or {}).get("state"),"directional_bias":direction,"active_leg":(tf.get("M15") or {}).get("structure"),"recent_bos":None,"recent_mss":None,"recent_sweep":None,"price_location":(tf.get("M15") or {}).get("location"),"developing_scenario":((view.get("primary_scenario") or {}).get("summary") or (view.get("primary_scenario") or {}).get("message") or "Monitor completed structure."),"invalidation":"Requires full analysis.","next_confirmation":"Run full analysis when a developing candidate requires execution validation."}
    trade_plan={"available":False,"status":"NOT_EVALUATED_LIGHTWEIGHT","entry":None,"stop":None,"targets":[],"reason":"Lightweight scanner analysis does not construct a trade plan."}
    product={"decision_id":decision_id,"meta":{"symbol":query["api_symbol"],"display_symbol":query["display_symbol"],"timeframe":query["timeframe"],"analysis_time":str(at),"market_source":query.get("provider"),"market_type":"derived" if query["asset_type"]=="derived_index" else query["asset_type"],"live":readiness["state"]=="ready","market_schedule":"24_7" if query["asset_type"] in {"derived_index","crypto"} else "24_5" if query["asset_type"]=="forex" else "exchange","analysis_clock":"UTC"},"ownership":{"selected_model_id":"lightweight_context","decision_owner_id":"lightweight_context","overlay_owner_id":"lightweight_context"},"readiness":readiness,"market":{"external_structure":external,"internal_structure":internal,"current_price":float(candles.iloc[-1].close) if len(candles) else None,"session":None},"market_analysis":market_analysis,"trade_plan":trade_plan,"decision":{"status":"MARKET CONTEXT","direction":direction,"setup_type":None,"stage":"LIGHTWEIGHT_CONTEXT","headline":"MARKET CONTEXT","summary":market_analysis["developing_scenario"],"next_action":"Use Analyze now for a complete trade-plan evaluation.","first_blocking_gate":blocker,"trade_ready":False},"setup":{"setup_id":None,"setup_type":None,"direction":direction,"stage":"LIGHTWEIGHT_CONTEXT","status":"MARKET CONTEXT","context_summary":market_analysis["developing_scenario"],"next_required_condition":"Full on-demand analysis.","first_blocking_gate":blocker,"trade_ready":False,"entry":None,"stop":None,"targets":[],"rr":None,"invalidation":{"price":None,"condition":"Requires full analysis."},"entry_area":None,"market_quality_score":None,"setup_quality_score":None,"quality_score":None,"quality_grade":None},"diagnostics":{},"overlays":[],"previous_setup":None,"paper_analysis_only":True}
    product=normalize_global_decision(product,instrument_metadata=query.get("symbol_metadata") or {},mode="LIVE")
    return {"decision":product,"candles":_candles_to_chart_records(candles),"analysis_mode":"lightweight"}


@app.route("/api/analyze-replay", methods=["POST"])
def api_analyze_replay():
    """Analyze a browser-provided candle slice without loading market data."""
    query = None
    try:
        payload = request.get_json(silent=True) or {}
        query = _get_replay_query(payload)
        candles = _candles_from_chart_records(payload.get("candles", []))
        posted_context = _context_candles_from_payload(payload.get("context_candles", {}))
        query["bars"] = len(candles)
        response = _build_analysis_response(
            candles,
            query,
            replay=True,
            provided_context_candles=posted_context,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": _friendly_market_error(str(error), query)}), 500

    return jsonify(response)


def _build_analysis_response(
    candles: pd.DataFrame,
    query: dict[str, object],
    replay: bool = False,
    provided_context_candles: dict[str, pd.DataFrame] | None = None,
) -> dict[str, object]:
    """Build one shared response shape for live and replay analysis."""
    selected_time_metadata = dict(candles.attrs.get("time_metadata", {}))
    context_candles = provided_context_candles or {query["timeframe"]: candles}
    context_errors: dict[str, str] = {}
    cache_status: dict[str, str] = {query["timeframe"]: "fresh"}

    if not replay:
        multi_timeframe = get_multi_timeframe_context(
            query["api_symbol"],
            query["timeframe"],
            int(query["bars"]),
            depth="balanced",
            selected_candles=candles,
            provider=str(query.get("provider","twelve_data")),
            asset_class=str(query.get("asset_type","forex")),
        )
        context_candles = multi_timeframe["context"]
        context_errors = multi_timeframe["errors"]
        cache_status = multi_timeframe["cache"]
        candles = multi_timeframe["selected"]["candles"]
    elif query["multi_timeframe_enabled"] and replay and provided_context_candles:
        context_candles[query["timeframe"]] = candles
        cache_status = {timeframe: "posted" for timeframe in context_candles}
    else:
        context_candles = {query["timeframe"]: candles}

    temporal = build_temporal_context(
        selected_candles=candles,
        context=context_candles,
        selected_timeframe=str(query["timeframe"]),
        replay=replay,
    )
    analysis_timestamp = temporal["analysis_timestamp"]
    candles = temporal["selected_candles"]
    context_candles = temporal["context"]
    if candles.empty:
        raise ValueError("No selected candles were available at the analysis timestamp.")

    top_down_analysis = analyze_top_down(context_candles, query["timeframe"])
    top_down_context = analyze_top_down_context(context_candles, query["timeframe"])
    derived = query["asset_type"] == "derived_index"
    session_context = ({"entry_allowed":True,"market_status":"OPEN_24_7","market_open":True,"name":"24/7","phase":"UTC Activity Window","expected_behavior":"Continuous synthetic market; strategy timing is structure-based.","timezone":"UTC","current_time":analysis_timestamp.isoformat(),"next_session":"Continuous","time_remaining_label":"24/7"}
                       if derived else get_session_status(analysis_timestamp, asset_type=str(query["asset_type"]), symbol=str(query["display_symbol"])))
    dxy_confirmation = _build_dxy_confirmation_filter(query, replay)
    dxy_correlation = _macro_dxy_from_filter(query["display_symbol"], dxy_confirmation)
    economic_news = analyze_news_risk(
        symbol=str(query["display_symbol"]),
        now=analysis_timestamp,
        enabled=bool(query.get("news_risk_enabled")) and not replay and not derived,
        provider_enabled=bool(query.get("marketaux_enabled")),
    )
    market_filters = {
        "news_risk": economic_news,
        "dxy_confirmation": dxy_confirmation,
    }
    market_phase = detect_market_phase(candles, session_context)
    macro_dashboard = build_macro_dashboard(
        session=session_context,
        top_down=top_down_analysis,
        dxy_correlation=dxy_correlation,
        economic_news=economic_news,
        market_phase=market_phase,
    )
    macro_dashboard["top_down_context"] = top_down_context
    shared_analysis = build_shared_analysis(candles)
    strategy_result, legacy_analysis = analyze_strategy(
        query["strategy"],
        candles,
        shared_analysis,
        symbol=query["display_symbol"],
        timeframe=query["timeframe"],
        top_down_analysis=top_down_analysis,
        context_candles=context_candles,
        macro_context=macro_dashboard,
        multi_timeframe_context=context_candles,
        top_down_context=top_down_context,
        analysis_timestamp=analysis_timestamp,
    )
    temporal_validation = validate_temporal_analysis(
        analysis_timestamp=analysis_timestamp,
        selected_timeframe=str(query["timeframe"]),
        context=context_candles,
        strategy_result=strategy_result,
        session=session_context,
        news=economic_news,
    )
    if not temporal_validation["valid"]:
        _apply_temporal_downgrade(strategy_result, temporal_validation["warnings"])
    analysis = legacy_analysis or _strategy_result_to_analysis(
        strategy_result,
        shared_analysis,
        macro_dashboard,
        top_down_analysis,
        top_down_context,
        query,
    )
    candle_records = _candles_to_chart_records(candles)
    context_records = {
        timeframe: _candles_to_chart_records(frame_candles)
        for timeframe, frame_candles in context_candles.items()
    }

    analysis["display_symbol"] = query["display_symbol"]
    analysis["api_symbol"] = query["api_symbol"]
    analysis["asset_type"] = query["asset_type"]
    analysis["provider"] = query.get("provider","twelve_data")
    analysis["requested_strategy"] = query["strategy"]
    analysis["selected_strategy"] = strategy_result.get("selected_strategy", query["strategy"])
    analysis["selected_strategy_key"] = strategy_result.get("selected_strategy_key", query["strategy"])
    analysis["strategy_reason"] = strategy_result.get("strategy_reason", "The selected strategy was requested manually.")
    analysis["selected_timeframe"] = query["timeframe"]
    analysis["multi_timeframe_enabled"] = query["multi_timeframe_enabled"]
    analysis["context_depth"] = query["context_depth"]
    analysis["analysis_timestamp"] = temporal["analysis_timestamp_iso"]
    analysis["analysis_timestamp_epoch"] = temporal["analysis_timestamp_epoch"]
    analysis["time_metadata"] = selected_time_metadata or {
        "source_timezone": "UTC",
        "normalized_timezone": "UTC",
        "timestamp_policy": "replay_epoch_utc" if replay else "assumed_utc",
        "timezone_warning": None if replay else "Provider timestamp metadata was unavailable.",
    }
    analysis["temporal_validation"] = temporal_validation
    analysis["shared_analysis"] = shared_analysis
    analysis["strategy_result"] = strategy_result
    analysis["top_down_context"] = top_down_context
    analysis["context_errors"] = context_errors
    analysis["cache"] = cache_status
    analysis["overlays"] = strategy_result.get("overlays", {})
    analysis["top_down_analysis"] = top_down_analysis
    analysis["macro_dashboard"] = macro_dashboard
    analysis["market_filters"] = market_filters
    analysis["interval"] = query["interval"]
    analysis["bars"] = query["bars"]
    analysis["analysis_mode"] = "replay" if replay else "live"
    analysis["price_precision"] = display_precision(
        str(query["display_symbol"]),
        str(query["asset_type"]),
        float(candles.iloc[-1]["close"]),
    )
    strategy_answers = strategy_result.get("trader_answers")
    if isinstance(strategy_answers, dict) and strategy_answers:
        analysis["trader_answers"] = strategy_answers
    else:
        analysis["trader_answers"] = build_trader_answers(
            symbol=query["display_symbol"],
            timeframe=query["timeframe"],
            shared_analysis=shared_analysis,
            strategy_result=strategy_result,
            analysis=analysis,
            top_down_context=top_down_context,
        )
    analysis["market_story"] = analysis["trader_answers"].get(
        "market_story",
        strategy_result.get("market_story", ""),
    )
    analysis["timeline"] = strategy_result.get("timeline") or analysis.get(
        "analysis_timeline",
        [],
    )
    analysis["answer_qa"] = build_answer_qa(
        trader_answers=analysis["trader_answers"],
        shared_analysis=shared_analysis,
        strategy_result=strategy_result,
        analysis=analysis,
        top_down_context=top_down_context,
    )
    analysis["answer_qa"]["temporal_validation"] = temporal_validation
    validation = analysis["answer_qa"]["validation"]
    if (
        analysis["trader_answers"].get("trade_status") == "Entry Ready"
        and not validation.get("valid")
    ):
        warnings = list(validation.get("warnings", []))
        _downgrade_invalid_entry_ready(
            analysis,
            strategy_result,
            query["display_symbol"],
            warnings,
        )
        analysis["answer_qa"] = build_answer_qa(
            trader_answers=analysis["trader_answers"],
            shared_analysis=shared_analysis,
            strategy_result=strategy_result,
            analysis=analysis,
            top_down_context=top_down_context,
        )
        analysis["answer_qa"]["temporal_validation"] = temporal_validation
        analysis["answer_qa"]["validation"] = {
            "valid": False,
            "warnings": warnings,
            "downgraded": True,
        }
    analysis["answer_validation"] = analysis["answer_qa"]["validation"]
    analysis["market_story"] = analysis["trader_answers"].get("market_story", "")
    _finalize_strategy_contract(strategy_result, analysis)
    analysis["trade_metrics"] = build_trade_metrics(
        symbol=str(query["display_symbol"]),
        asset_type=str(query["asset_type"]),
        direction=str(strategy_result.get("bias", "Neutral")),
        levels_mode=str(strategy_result.get("levels_mode", "hidden")),
        levels=analysis.get("levels") or {},
        objective_plan=analysis.get("objective_plan") or {},
    )
    strategy_result["trade_metrics"] = analysis["trade_metrics"]
    entry_timing = evaluate_entry_timing(
        symbol=str(query["display_symbol"]),
        asset_type=str(query["asset_type"]),
        direction=str(strategy_result.get("bias", "Neutral")),
        current_price=(shared_analysis.get("current") or {}).get("current_price"),
        entry_zone=(analysis.get("levels") or {}).get("entry_zone"),
        trigger_level=analysis["trade_metrics"].get("entry_price")
        or (analysis.get("levels") or {}).get("trigger_level"),
        stop_loss=analysis["trade_metrics"].get("stop_loss")
        or (analysis.get("levels") or {}).get("invalidation"),
        tp1=(analysis["trade_metrics"].get("tp1") or {}).get("price"),
        tp2=(analysis["trade_metrics"].get("tp2") or {}).get("price"),
        atr=(shared_analysis.get("volatility") or {}).get("atr"),
    )
    analysis["entry_timing"] = entry_timing
    strategy_result["entry_timing"] = entry_timing
    timing_downgraded = _apply_entry_timing_gate(analysis, strategy_result)
    if timing_downgraded:
        analysis["answer_qa"] = build_answer_qa(
            trader_answers=analysis["trader_answers"],
            shared_analysis=shared_analysis,
            strategy_result=strategy_result,
            analysis=analysis,
            top_down_context=top_down_context,
        )
        analysis["answer_qa"]["temporal_validation"] = temporal_validation
        analysis["answer_validation"] = analysis["answer_qa"]["validation"]
    _polish_pending_decision(
        analysis=analysis,
        strategy_result=strategy_result,
        symbol=str(query["display_symbol"]),
        timeframe=str(query["timeframe"]),
    )
    _apply_news_filter_gate(analysis, strategy_result, market_filters)
    direction_debug = build_direction_debug(strategy_result, analysis)
    strategy_result["direction_debug"] = direction_debug
    strategy_result["user_status"] = direction_debug["user_status"]
    analysis["direction_debug"] = direction_debug
    analysis["trade_direction"] = direction_debug["final_direction"]
    analysis["user_status"] = direction_debug["user_status"]
    _apply_trade_score(analysis, strategy_result)
    rebuilt_top_down, execution_plan = _apply_fixed_m5_execution_pipeline(
        analysis=analysis,
        strategy_result=strategy_result,
        context_candles=context_candles,
        analysis_timestamp=analysis_timestamp,
        query=query,
        session_context=session_context,
        market_filters=market_filters,
    )
    top_down_analysis = rebuilt_top_down
    decision = build_decision(
        symbol=str(query["display_symbol"]),
        asset_class=str(query["asset_type"]),
        display_timeframe=str(query["timeframe"]),
        candles_by_timeframe=context_candles,
        analysis_timestamp=analysis_timestamp,
        requested_strategy=str(query["strategy"]),
        session=session_context,
        filters=market_filters,
        spread=(shared_analysis.get("current") or {}).get("spread", 0),
        minimum_rr=float(query.get("minimum_rr", 1.5)),
        execution_mode=str(query.get("execution_mode", "conservative")),
        time_metadata=analysis.get("time_metadata") or {},
        asset_metadata=query.get("symbol_metadata") or {},
    )
    if derived:
        metadata=dict(query.get("symbol_metadata") or {});metadata["source_timeframe"]="M1" if "M1" in context_candles else str(query["timeframe"])
        derived_result=analyze_derived_index(symbol=str(query["api_symbol"]),metadata=metadata,candles_by_timeframe=context_candles,tick_size=float(derived_index_rules(str(query["api_symbol"]),metadata).get("tick_size",.01)),analysis_time=analysis_timestamp,requested_strategy=str(query.get("strategy","auto")))
        family=derived_result["advanced_details"]["family"];volatility=derived_result["market_profile"];spike=derived_result["spike_state"]
        decision["market"]={"provider":"deriv","asset_class":"derived_index","market_schedule":"24_7","market_open":True,"family":family["family"],"paper_analysis_only":True}
        # Never embed the product contract inside the legacy contract: the
        # product contract later mirrors this legacy view and would otherwise
        # form a circular response graph that Flask cannot serialize.
        derived_contract=_acyclic_projection({key:value for key,value in derived_result.items() if key!="product_contract"})
        if derived_result.get("model_resolution"):decision["model_resolution"]=derived_result["model_resolution"]
        decision["derived_index"]={"rules":derived_index_rules(str(query["api_symbol"]),metadata),"family":family,"volatility":volatility,"spike":spike,"execution_timeframe":"M5","contract":derived_contract}
        decision["trade_chart"]=derived_result.get("trade_chart") or decision.get("trade_chart")
        decision["presentation"]=_acyclic_projection({"decision":derived_result["decision"],"market_context":derived_result["market_context"],"developing_scenario":derived_result["developing_scenario"],"active_trade_plan":derived_result["active_trade_plan"],"key_levels":derived_result["key_levels"],"previous_setup":derived_result["previous_setup"],"advanced_details":derived_result["advanced_details"]})
        decision.setdefault("filters",{}).update({"news_applicable":False,"dxy_applicable":False,"forex_session_applicable":False})
        if not replay and str(query.get("strategy","auto")).lower()=="auto" and not os.getenv("PYTEST_CURRENT_TEST"):
            completed_m5=context_candles.get("M5",pd.DataFrame());completed_m5=completed_m5[completed_m5.complete.astype(bool)] if "complete" in completed_m5 else completed_m5;paper_time=(completed_m5.iloc[-1].time if len(completed_m5) else analysis_timestamp);decision["paper_testing"]=get_derived_paper_service().record_analysis(provider_symbol=str(query["api_symbol"]),display_name=str(query["display_symbol"]),family=family["family"],subfamily=family.get("subfamily",family["family"]),requested_strategy="Auto",analysis_candle_time=str(paper_time),decision_contract=derived_result,candles=completed_m5,data_snapshot_id=str((derived_result.get("intelligence") or {}).get("snapshot_id") or ""))
        if not replay:
            smc_funnel=derived_result.get("gate_funnel");smc_owner=(derived_result.get("ownership") or {}).get("decision_owner_id")
            if smc_funnel and smc_owner:
                try:StrategyGateDiagnosticsStore().record(symbol=str(query["api_symbol"]),family=family["family"],strategy=smc_owner,regime=(derived_result.get("structure") or {}).get("external_structure",""),funnel=smc_funnel,day=str(pd.Timestamp(analysis_timestamp).date()))
                except Exception:pass
            plan=derived_result.get("active_trade_plan") or {};strategy_detail=derived_result.get("strategy_result") or {}
            decision_detail=derived_result.get("decision") or {};advanced_detail=derived_result.get("advanced_details") or {};regime_detail=advanced_detail.get("regime") or {}
            DerivedSignalLogger().append_decision({"timestamp":str(analysis_timestamp),"symbol":query["api_symbol"],"family":family["family"],"strategy":decision_detail.get("strategy"),"strategy_status":decision_detail.get("strategy_status"),"market_regime":decision_detail.get("regime"),"volatility_regime":volatility.get("volatility_regime"),"spike_state":spike,"spike_id":decision_detail.get("spike_id"),"locked_spike":strategy_detail.get("spike"),"cooldown":strategy_detail.get("cooldown"),"spike_hold":strategy_detail.get("spike_hold"),"post_spike_structure":strategy_detail.get("post_spike_structure"),"risk_alignment":decision_detail.get("risk_alignment"),"direction":decision_detail.get("developing_direction") or decision_detail.get("direction"),"setup_state":decision_detail.get("status"),"pullback_state":(derived_result.get("pullback") or {}).get("state"),"range_id":decision_detail.get("range_id"),"locked_range":derived_result.get("range"),"boundary_quality":derived_result.get("boundary_quality"),"boundary_pressure":derived_result.get("boundary_pressure"),"range_price_location":derived_result.get("price_location"),"boundary_rejection":derived_result.get("boundary_rejection"),"breakout":derived_result.get("breakout"),"retest_zone":derived_result.get("retest_zone"),"m15_zone":derived_result.get("m15_setup_zone"),"m5_execution_zone":derived_result.get("m5_execution_zone"),"confirmation":derived_result.get("confirmation"),"entry":plan.get("entry"),"stop":plan.get("stop"),"tp1":plan.get("tp1"),"tp2":plan.get("tp2"),"rr":plan.get("tp1_rr"),"chase_state":plan.get("timing_state"),"setup_id":decision_detail.get("setup_id"),"lifecycle":strategy_detail.get("lifecycle"),"evidence":regime_detail.get("evidence",[]),"contradictions":regime_detail.get("contradictions",[]),"rejected_strategies":strategy_detail.get("rejection_reasons",strategy_detail.get("rejected_candidates",[]))})
    legacy_decision_contract=decision
    _mirror_decision_contract(analysis, strategy_result, legacy_decision_contract)
    if derived and (derived_result.get("product_contract") or {}):
        decision=derived_result["product_contract"]
        decision["legacy_contract"]=legacy_decision_contract
        analysis["decision"]=decision
        analysis["overlays"]=decision["overlays"]
    elif not derived:
        market_type=str(query.get("asset_type") or "forex");schedule="24_7" if market_type=="crypto" else "exchange" if market_type=="index" else "24_5"
        decision=normalize_market_decision(legacy_decision_contract,symbol=str(query["api_symbol"]),display_symbol=str(query["display_symbol"]),timeframe=str(query["timeframe"]),market_source=str(query.get("provider") or "twelve_data"),market_type=market_type,market_schedule=schedule,analysis_time=analysis_timestamp,live=not replay)
        analysis["decision"]=decision;analysis["overlays"]=decision["overlays"]
    if isinstance(decision,dict) and decision.get("meta"):
        decision=normalize_global_decision(decision,instrument_metadata=query.get("symbol_metadata") or {},mode="REPLAY" if replay else "LIVE")
        analysis["decision"]=decision;analysis["overlays"]=decision["overlays"]
    if isinstance(decision,dict) and decision.get("setup"):
        decision["market_analysis"]=build_market_analysis(market=decision.get("market") or {},setup=decision["setup"],smc=decision.get("smc") or {},scenario=(decision.get("decision") or {}).get("summary"));decision["trade_plan"]=build_trade_plan(decision["setup"],(decision.get("decision") or {}).get("status",""),(decision.get("decision") or {}).get("first_blocking_gate") or decision["setup"].get("next_required_condition"));trace=((decision.get("diagnostics") or {}).get("target_trace") or {});decision["trade_plan"]["target_candidates_checked"]=trace.get("candidates_found") or [];decision["trade_plan"]["target_rejections"]=trace.get("candidates_rejected") or []
    if isinstance(decision,dict) and not derived:
        # UI polish: expose the already-computed entry-timing classification
        # (analysis/entry_timing.py) on the normalized contract so the
        # frontend can show one consistent AT_ENTRY/NEAR_ENTRY/EXTENDED/
        # TOO_LATE/MISSED/INVALID message instead of nothing at all -- pure
        # data exposure, no new computation.
        timing=analysis.get("entry_timing") or strategy_result.get("entry_timing") or {}
        if timing.get("available"):decision["entry_timing"]={"status":timing.get("entry_timing_status"),"message":timing.get("message"),"next_action":timing.get("next_action"),"can_enter_now":timing.get("can_enter_now")}
    execution_plan = analysis["execution_plan"]
    if not replay:
        _log_live_paper_decision(decision)

    response = {
        "symbol": query["display_symbol"],
        "display_symbol": query["display_symbol"],
        "api_symbol": query["api_symbol"],
        "asset_type": query["asset_type"],
        "provider": query.get("provider","twelve_data"),
        "timeframe": query["timeframe"],
        "interval": query["interval"],
        "bars": query["bars"],
        "selected_strategy": query["strategy"],
        "selected_timeframe": query["timeframe"],
        "multi_timeframe_enabled": query["multi_timeframe_enabled"],
        "context_depth": query["context_depth"],
        "analysis_timestamp": temporal["analysis_timestamp_iso"],
        "analysis_timestamp_epoch": temporal["analysis_timestamp_epoch"],
        "time_metadata": analysis["time_metadata"],
        "top_down_context": top_down_context,
        "top_down_analysis": rebuilt_top_down,
        "execution_plan": execution_plan,
        "decision": decision,
        "display_analysis": analysis["display_analysis"],
        "trader_answers": analysis["trader_answers"],
        "answer_qa": analysis["answer_qa"],
        "answer_validation": analysis["answer_validation"],
        "temporal_validation": temporal_validation,
        "price_precision": analysis["price_precision"],
        "market_story": analysis["market_story"],
        "market_filters": market_filters,
        "timeline": analysis["timeline"],
        "cache": cache_status,
        "multi_timeframe": {
            "selected": {"timeframe": query["timeframe"], "candles": candle_records},
            "context": context_records,
            "errors": context_errors,
            "cache": cache_status,
            "depth": query["context_depth"],
        },
        "candles": candle_records,
        "analysis": analysis,
        "analysis_mode": "replay" if replay else "live",
    }
    response.update(analysis)
    response["candles"] = candle_records
    response["analysis"] = analysis

    return response


def _mirror_decision_contract(
    analysis: dict[str, object],
    strategy_result: dict[str, object],
    decision: dict[str, object],
) -> None:
    """Project the normalized decision into temporary legacy response fields."""
    setup = decision["setup"]
    execution = decision["execution"]
    quality = decision["quality"]
    output = decision["user_output"]
    ready = bool(quality["trade_plan_valid"])
    direction = str(output["direction"])
    targets = execution.get("targets") or []
    tp1 = targets[0] if targets else None
    tp2 = targets[1] if len(targets) > 1 else None
    possible_setups = []
    zone = setup.get("zone") or {}
    if setup.get("setup_id") and zone.get("low") is not None and zone.get("high") is not None:
        possible_setups.append(
            {
                "id": setup["setup_id"], "priority": "primary", "direction": setup["direction"],
                "label": f"M15 {str(setup['direction']).title()} Setup · M5 Execution",
                "stage": _decision_legacy_stage(str(setup["stage"])), "strategy": setup["strategy"],
                "setup_zone": {**zone, "label": "Demand Zone" if setup["direction"] == "buy" else "Supply Zone", "start_time": zone.get("origin_time")},
                "trigger": {"price": setup["confirmation"]["price"], "type": setup["confirmation"]["type"], "message": setup.get("confirmation_hint", "")},
                "invalidation": {"price": setup["invalidation"]["price"], "message": setup.get("invalidation_context", "")},
                "targets": targets, "estimated_rr": execution.get("risk_reward"), "entry_available": ready,
                "confirmation_viable": ready, "remaining_rr": execution.get("risk_reward"),
                "next_action": output["next_action"], "creation_time": setup.get("created_time"), "last_updated_time": setup.get("updated_time"),
            }
        )
    existing_metrics = dict(analysis.get("trade_metrics") or {})
    existing_metrics.update({"entry_price": execution.get("entry"), "stop_loss": execution.get("stop"), "tp1": tp1, "tp2": tp2, "plan_mode": "final" if ready else "projected"})
    incomplete_context = quality.get("data_quality") == "invalid" and any("Missing required candle data" in str(reason) for reason in quality.get("rejection_reasons", []))
    manual_diagnostic = str(analysis.get("requested_strategy", "auto")) != "auto" and not decision.get("primary_strategy")
    manual_ict_context = str(analysis.get("requested_strategy", "auto")) == "ict_2022" and not bool((decision.get("ict_eligibility") or {}).get("eligible"))
    legacy_direction = analysis.get("trade_direction", direction)
    legacy_status = analysis.get("user_status", output["status"])
    analysis.update(
        {
            "decision": decision, "trade_direction": direction, "user_status": output["status"],
            "trade_score": quality["score"], "score": quality["score"], "readiness": quality["score"],
            "trade_confidence": quality["confidence"].title(), "possible_setups": possible_setups,
            "execution_plan": execution, "overlays": decision["overlays"],
            "levels_mode": "final" if ready else "projected", "trade_decision": "ACCEPT" if ready else "PENDING",
            "levels": {"entry_zone": execution.get("entry_zone"), "stop_loss": execution.get("stop"), "tp1": tp1.get("price") if tp1 else None, "tp2": tp2.get("price") if tp2 else None, "rr1": execution.get("risk_reward")},
            "trade_metrics": existing_metrics,
            "entry_timing": {"available": True, "entry_timing_status": execution["state"], "status": execution["state"], "can_enter_now": ready, "remaining_rr_to_tp1": execution.get("risk_reward"), "message": execution.get("message")},
            "selected_strategy": decision["strategy_routing"].get("selected_strategy") or "Auto",
            "strategy_reason": decision["strategy_routing"].get("reason", ""),
        }
    )
    if incomplete_context or manual_diagnostic or manual_ict_context:
        analysis["trade_direction"] = legacy_direction
        analysis["user_status"] = legacy_status
    strategy_result.update({"decision": decision, "authoritative_execution": False, "trade_score": quality["score"], "user_status": output["status"], "execution_plan": execution})


def _decision_legacy_stage(stage: str) -> str:
    return {"waiting_for_area": "WATCHING AREA", "in_area": "IN SETUP AREA", "reaction_forming": "REACTION FORMING", "waiting_for_m5_close": "CONFIRMATION FORMING", "confirmed": "SETUP CONFIRMED", "too_late": "SETUP MISSED", "missed": "SETUP MISSED", "invalidated": "SETUP INVALIDATED", "none": "WATCHING AREA"}.get(stage, "WATCHING AREA")


def _log_live_paper_decision(decision: dict[str, object]) -> None:
    """Append live paper decisions only when explicitly enabled outside tests."""
    if app.testing or decision.get("paper_registration_allowed") is False:
        return
    if _truthy(os.getenv("TRADESCOR_PAPER_LOG", "0")):
        from paper_testing.logger import PaperDecisionLogger
        PaperDecisionLogger().record_decision(decision)
    if _truthy(os.getenv("TRADESCOR_AUTO_SHADOW_LOG", "0")):
        from paper_testing.auto_shadow_logger import AutoShadowLogger
        AutoShadowLogger().record(decision)


def _finalize_strategy_contract(
    strategy_result: dict[str, object],
    analysis: dict[str, object],
) -> None:
    """Attach the strategy-neutral V1 response fields used by the frontend."""
    answers = analysis.get("trader_answers") or {}
    overlays = strategy_result.get("overlays") or analysis.get("overlays") or {}
    raw_levels = strategy_result.get("levels") or analysis.get("levels") or {}
    important_zone = (
        overlays.get("entry_zone")
        or overlays.get("pullback_zone")
        or overlays.get("supply_demand_zone")
        or overlays.get("retest_zone")
        or overlays.get("active_fvg")
    )
    trigger = overlays.get("confirmation_level") or overlays.get("breakout_level") or {}
    if isinstance(trigger, dict):
        trigger = trigger.get("price", trigger.get("level"))
    invalidation = overlays.get("invalidation_level") or raw_levels.get("stop_loss")
    if isinstance(invalidation, dict):
        invalidation = invalidation.get("price", invalidation.get("level"))
    levels = {
        "important_zone": important_zone,
        "trigger_level": trigger,
        "invalidation": invalidation,
        "entry_zone": raw_levels.get("entry_zone"),
        "stop_loss": raw_levels.get("stop_loss"),
        "tp1": raw_levels.get("tp1"),
        "tp2": raw_levels.get("tp2"),
        "rr1": raw_levels.get("rr1"),
        "rr2": raw_levels.get("rr2"),
        **{
            key: value
            for key, value in raw_levels.items()
            if key not in {
                "important_zone",
                "trigger_level",
                "invalidation",
                "entry_zone",
                "stop_loss",
                "tp1",
                "tp2",
                "rr1",
                "rr2",
            }
        },
    }
    strategy_result.update(
        {
            "trade_status": answers.get("trade_status", "No Trade"),
            "market_clarity": answers.get("market_clarity", "Low"),
            "trade_readiness": answers.get("trade_readiness", "Not Ready"),
            "market_story": answers.get("market_story", strategy_result.get("market_story", "")),
            "next_action": answers.get("next_action", strategy_result.get("next_trigger", "")),
            "levels": levels,
            "overlays": overlays,
            "timeline": strategy_result.get("timeline") or analysis.get("timeline") or [],
            "validation": analysis.get("answer_validation") or {"valid": True, "warnings": []},
            "trader_answers": answers,
        }
    )
    analysis["levels"] = levels


def _apply_fixed_m5_execution_pipeline(
    *,
    analysis: dict[str, object],
    strategy_result: dict[str, object],
    context_candles: dict[str, pd.DataFrame],
    analysis_timestamp: object,
    query: dict[str, object],
    session_context: dict[str, object],
    market_filters: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Make D1/H4/H1 context + M15 location + M5 execution authoritative."""
    legacy_direction = str(analysis.get("trade_direction") or strategy_result.get("bias") or "Neutral")
    legacy_status = str(analysis.get("user_status") or strategy_result.get("user_status") or "NO VALID SETUP")
    legacy_score = int(analysis.get("trade_score", analysis.get("score", 0)) or 0)
    context_complete = all(
        timeframe in context_candles and context_candles[timeframe] is not None and not context_candles[timeframe].empty
        for timeframe in ("D1", "H4", "H1", "M15", "M5")
    )
    top_down = analyze_top_down_market(
        symbol=str(query["display_symbol"]),
        candles_by_timeframe=context_candles,
        analysis_timestamp=analysis_timestamp,
    )
    m5_candles = context_candles.get("M5", pd.DataFrame())
    current_price = None
    if m5_candles is not None and not m5_candles.empty:
        current_price = float(m5_candles.iloc[-1]["close"])
    execution = build_m5_execution_plan(
        top_down_analysis=top_down,
        m5_candles=m5_candles,
        analysis_timestamp=analysis_timestamp,
        current_price=current_price,
        spread=(analysis.get("shared_analysis") or {}).get("current", {}).get("spread", 0),
        asset_type=str(query["asset_type"]),
        news_filters=market_filters,
        session_context=session_context,
        minimum_rr=float(query.get("minimum_rr", 1.5)),
        mode=str(query.get("execution_mode", "conservative")),
    )
    direction = str(execution.get("direction", "neutral"))
    state = str(execution.get("state", "waiting_for_zone"))
    actionable = state == "entry_valid"
    display_direction = "Buy" if direction == "buy" else "Sell" if direction == "sell" else "Neutral"

    score = int(top_down.get("score_before_execution", 0) or 0)
    if execution.get("confirmed_signal"):
        score = min(90, score + 25)
    if execution.get("risk_reward") is not None and float(execution["risk_reward"]) >= 1.5:
        score += 10
    if actionable:
        score = min(100, score + 5)
    else:
        score = min(70 if not execution.get("confirmed_signal") else 90, score)

    if state == "invalidated":
        user_status = "SETUP INVALIDATED"
    elif state == "too_late":
        user_status = "SETUP MISSED"
    elif actionable:
        user_status = f"{direction.upper()} CONFIRMED"
    elif direction in {"buy", "sell"}:
        user_status = f"{direction.upper()} SETUP FORMING"
    else:
        user_status = "NO VALID SETUP"

    setup = top_down.get("m15_setup") or {}
    zone = setup.get("zone")
    possible_setups: list[dict[str, object]] = []
    has_setup = direction in {"buy", "sell"} and isinstance(zone, dict) and setup.get("enabled")
    if has_setup:
        trigger = execution.get("trigger")
        stop = execution.get("stop")
        targets = [
            {
                "name": target.get("name", f"TP{index + 1}"),
                "price": target.get("price"),
                "reason": target.get("reason", "Structure objective"),
                "valid": bool(target.get("valid")),
                "swept": bool(target.get("swept", False)),
            }
            for index, target in enumerate(execution.get("targets") or [])
            if target.get("valid")
        ]
        possible_setups.append(
            {
                "id": f"top-down-{query['display_symbol']}-{zone.get('start_time', 'current')}-{direction}",
                "priority": "primary",
                "direction": direction,
                "label": f"M15 {direction.title()} Setup · M5 Execution",
                "stage": _execution_setup_stage(state),
                "strategy": "Top-Down Execution",
                "setup_zone": zone,
                "trigger": {
                    "price": trigger,
                    "type": "m5_closed_candle_structure",
                    "message": f"M5 {'bullish close above' if direction == 'buy' else 'bearish close below'} confirmation.",
                },
                "invalidation": {
                    "price": stop,
                    "message": f"Invalid {'below' if direction == 'buy' else 'above'} M5 execution structure.",
                },
                "targets": targets,
                "estimated_rr": execution.get("risk_reward"),
                "entry_available": actionable,
                "conditions_met": 4 if actionable else 2 + int(bool(execution.get("confirmed_signal"))),
                "conditions_total": 4,
                "conditions": [],
                "next_action": execution.get("message", "Wait for M5 execution confirmation."),
                "creation_time": zone.get("start_time"),
                "last_updated_time": analysis.get("analysis_timestamp_epoch"),
            }
        )

    if not has_setup and not actionable and context_complete:
        user_status = "NO VALID SETUP"
    if not context_complete:
        display_direction = legacy_direction
        user_status = legacy_status
        score = min(70, legacy_score)

    metrics = dict(analysis.get("trade_metrics") or {})
    levels = dict(analysis.get("levels") or {})
    if actionable:
        target_rows = execution.get("targets") or []
        valid_targets = [target for target in target_rows if target.get("valid")]
        metrics.update(
            {
                "entry_price": execution.get("entry"),
                "stop_loss": execution.get("stop"),
                "tp1": valid_targets[0] if valid_targets else None,
                "tp2": valid_targets[1] if len(valid_targets) > 1 else None,
                "plan_mode": "final",
            }
        )
        levels.update(
            {
                "entry_zone": execution.get("entry_zone"),
                "stop_loss": execution.get("stop"),
                "tp1": valid_targets[0]["price"] if valid_targets else None,
                "tp2": valid_targets[1]["price"] if len(valid_targets) > 1 else None,
                "rr1": execution.get("risk_reward"),
            }
        )
        levels_mode, trade_decision = "final", "ACCEPT"
    else:
        metrics.update({"entry_price": None, "stop_loss": None, "tp1": None, "tp2": None, "plan_mode": "projected"})
        levels.update({"entry_zone": None, "stop_loss": None, "tp1": None, "tp2": None, "rr1": None, "rr2": None})
        levels_mode, trade_decision = "projected", "PENDING"

    top_down["timeframes"]["M5"]["trigger_state"] = state
    top_down["alignment"]["execution_direction"] = direction
    analysis.update(
        {
            "top_down_analysis": top_down,
            "execution_plan": execution,
            "display_analysis": {
                "selected_timeframe": query["timeframe"],
                "display_timeframe": query["timeframe"],
                "analysis_timeframes": ["D1", "H4", "H1", "M15", "M5"],
                "execution_timeframe": "M5",
                "context_message": f"{query['timeframe']} is the display chart. Entries are generated only from M5.",
            },
            "multi_timeframe_enabled": True,
            "trade_direction": display_direction,
            "user_status": user_status,
            "trade_score": score,
            "score": score,
            "readiness": score,
            "possible_setups": possible_setups,
            "trade_metrics": metrics,
            "levels": levels,
            "levels_mode": levels_mode,
            "trade_decision": trade_decision,
            "entry_timing": {
                "available": True,
                "entry_timing_status": str(execution.get("entry_timing", "")).lower().replace(" ", "_"),
                "status": execution.get("entry_timing"),
                "can_enter_now": actionable,
                "remaining_rr_to_tp1": execution.get("risk_reward"),
                "message": execution.get("message"),
            },
        }
    )
    # Preserve the selected strategy's diagnostic contract. The authoritative
    # direction and actionable prices live at analysis.execution_plan only.
    strategy_result["execution_plan"] = execution
    strategy_result["top_down_analysis"] = top_down
    strategy_result["authoritative_execution"] = False
    return top_down, execution


def _execution_setup_stage(state: str) -> str:
    return {
        "waiting_for_zone": "WATCHING AREA",
        "in_zone": "IN SETUP AREA",
        "waiting_for_trigger": "IN SETUP AREA",
        "trigger_forming": "CONFIRMATION FORMING",
        "trigger_confirmed": "CONFIRMATION FORMING",
        "entry_valid": "SETUP CONFIRMED",
        "too_late": "SETUP MISSED",
        "invalidated": "SETUP INVALIDATED",
    }.get(state, "WATCHING AREA")


def _apply_trade_score(
    analysis: dict[str, object],
    strategy_result: dict[str, object],
) -> None:
    """Set the user-facing score after objective, timing, and filter gates."""
    setup_quality = int(analysis.get("setup_quality", strategy_result.get("setup_quality", strategy_result.get("score", 0))) or 0)
    trade_quality = int(analysis.get("trade_quality", strategy_result.get("trade_quality", 0)) or 0)
    score = build_trade_score(
        setup_quality=setup_quality,
        trade_quality=trade_quality,
        trade_decision=strategy_result.get("trade_decision", analysis.get("trade_decision", "PENDING")),
        levels_mode=strategy_result.get("levels_mode", analysis.get("levels_mode", "hidden")),
        state=strategy_result.get("state", analysis.get("setup_status", "")),
        objective_plan=analysis.get("objective_plan") or strategy_result.get("objective_plan") or {},
        trade_metrics=analysis.get("trade_metrics") or strategy_result.get("trade_metrics") or {},
        entry_timing=analysis.get("entry_timing") or strategy_result.get("entry_timing") or {},
        setup_stage=_score_setup_stage(analysis, strategy_result),
    )
    trade_score = int(score["score"])
    analysis["trade_score"] = trade_score
    analysis["score"] = trade_score
    analysis["readiness"] = trade_score
    analysis["readiness_level"] = {
        **(analysis.get("readiness_level") or {}),
        "percent": trade_score,
    }
    analysis["trade_score_details"] = score
    strategy_result["trade_score"] = trade_score
    strategy_result["trade_score_details"] = score


def _score_setup_stage(
    analysis: dict[str, object],
    strategy_result: dict[str, object],
) -> str:
    """Translate the strategy lifecycle into user-facing readiness stages."""
    decision = str(strategy_result.get("trade_decision", analysis.get("trade_decision", ""))).upper()
    mode = str(strategy_result.get("levels_mode", analysis.get("levels_mode", ""))).lower()
    state = str(strategy_result.get("state", analysis.get("setup_status", ""))).upper()
    zone = (analysis.get("levels") or {}).get("important_zone")
    current = ((analysis.get("shared_analysis") or {}).get("current") or {}).get("current_price")
    if isinstance(zone, dict):
        low = zone.get("low", zone.get("bottom", zone.get("bottom_price")))
        high = zone.get("high", zone.get("top", zone.get("top_price")))
        try:
            if float(low) <= float(current) <= float(high):
                return "IN SETUP AREA"
        except (TypeError, ValueError):
            pass
        if str(zone.get("zone_status", "")).lower() == "fresh" and int(zone.get("touch_count", 0) or 0) == 0:
            return "WATCHING AREA"
    if decision == "ACCEPT" and mode == "final":
        return "SETUP CONFIRMED"
    if "CONFIRM" in state or "MSS" in state or "IFVG" in state:
        return "CONFIRMATION FORMING"
    if isinstance(zone, dict):
        return "WATCHING AREA"
    return "DIRECTION ONLY"


def _apply_entry_timing_gate(
    analysis: dict[str, object],
    strategy_result: dict[str, object],
) -> bool:
    """Prevent a technically valid setup from becoming a chase entry."""
    timing = analysis.get("entry_timing") or {}
    if not timing.get("available"):
        return False

    timing_status = str(timing.get("entry_timing_status", "invalid"))
    current_rr = timing.get("remaining_rr_to_tp1")
    entry_ready = (
        str((analysis.get("trader_answers") or {}).get("trade_status")) == "Entry Ready"
        or str(strategy_result.get("state")) == "ENTRY_READY"
        or str(strategy_result.get("levels_mode")) == "final"
    )
    must_block = timing_status in {"extended", "too_late", "missed", "invalid"}
    must_block = must_block or (entry_ready and not bool(timing.get("can_enter_now")))
    must_block = must_block or (
        entry_ready
        and isinstance(current_rr, (int, float))
        and float(current_rr) < 1.0
    )
    if not must_block:
        return False

    answers = analysis.get("trader_answers") or {}
    message = str(timing.get("message") or "Current price is not suitable for entry.")
    next_action = str(timing.get("next_action") or "Wait for a fresh entry opportunity.")
    if not entry_ready:
        if timing_status not in {"extended", "too_late"}:
            return False
        answers["next_action"] = next_action
        reasons = [str(reason) for reason in answers.get("why", [])]
        reasons.append(message)
        answers["why"] = reasons[-5:]
        strategy_result["next_action"] = next_action
        strategy_result["next_trigger"] = next_action
        strategy_result["trader_answers"] = answers
        strategy_result["entry_timing_action"] = "AVOID" if timing_status == "too_late" else "WATCHLIST"
        analysis["trader_answers"] = answers
        analysis["missing_confirmation"] = next_action
        analysis["suggested_action"] = next_action
        analysis["next_required_confirmation"] = next_action
        return True

    terminal = timing_status in {"missed", "invalid"}
    trade_status = "No Trade" if terminal else "Wait"
    levels_mode = "hidden" if terminal else "projected"
    decision = "REJECT" if terminal else "PENDING"

    answers["trade_status"] = trade_status
    answers["trade_readiness"] = "Not Ready" if terminal else "Building"
    answers["next_action"] = next_action
    reasons = [str(reason) for reason in answers.get("why", [])]
    reasons.append(message)
    answers["why"] = reasons[-5:]
    story = str(answers.get("market_story") or strategy_result.get("market_story") or "").strip()
    if message not in story:
        story = f"{story} {message}".strip()
    answers["market_story"] = story

    overlays = dict(strategy_result.get("overlays") or analysis.get("overlays") or {})
    overlays["levels_mode"] = levels_mode
    if terminal:
        for key in ("entry_zone", "stop_loss", "tp1", "tp2", "trade_levels"):
            overlays[key] = None
        hidden_levels = dict(analysis.get("levels") or {})
        for key in ("entry_zone", "stop_loss", "tp1", "tp2", "rr1", "rr2"):
            hidden_levels[key] = None
        analysis["levels"] = hidden_levels
        strategy_result["levels"] = hidden_levels

    state = "NO_TRADE" if terminal else "CONFIRMED_WAITING_FOR_ENTRY"
    strategy_result.update(
        {
            "state": state,
            "trade_status": trade_status,
            "trade_readiness": answers["trade_readiness"],
            "trade_decision": decision,
            "levels_mode": levels_mode,
            "overlays": overlays,
            "next_action": next_action,
            "next_trigger": next_action,
            "trader_answers": answers,
            "entry_timing_action": "AVOID" if terminal or timing_status == "too_late" else "WATCHLIST",
        }
    )
    metrics = analysis.get("trade_metrics") or {}
    metrics["plan_mode"] = "unavailable" if terminal else "projected"
    if terminal:
        metrics.update(
            {
                "entry_price": None,
                "stop_loss": None,
                "risk": None,
                "tp1": None,
                "tp2": None,
            }
        )
    warnings = list(metrics.get("warnings") or [])
    warnings.append(message)
    metrics["warnings"] = list(dict.fromkeys(warnings))

    analysis.update(
        {
            "setup_status": state.replace("_", " "),
            "status": state.replace("_", " "),
            "trade_decision": decision,
            "levels_mode": levels_mode,
            "overlays": overlays,
            "trader_answers": answers,
            "market_story": story,
            "missing_confirmation": next_action,
            "suggested_action": next_action,
            "next_required_confirmation": next_action,
        }
    )
    return True


def _polish_pending_decision(
    *,
    analysis: dict[str, object],
    strategy_result: dict[str, object],
    symbol: str,
    timeframe: str,
) -> None:
    """Give pending Scanner decisions a numeric, direction-aware next action."""
    answers = analysis.get("trader_answers") or {}
    timing_status = str((analysis.get("entry_timing") or {}).get("entry_timing_status", ""))
    if timing_status in {"extended", "too_late", "missed", "invalid"}:
        return
    trade_status = str(answers.get("trade_status", "No Trade"))
    decision = str(strategy_result.get("trade_decision", "PENDING")).upper()
    if trade_status in {"Entry Ready", "Trade Active", "Invalidated"}:
        return

    levels = analysis.get("levels") or {}
    instruction = actionable_wait_instruction(
        symbol=symbol,
        timeframe=timeframe,
        direction=str(strategy_result.get("bias", "Neutral")),
        trigger_level=levels.get("trigger_level"),
        precision=int(analysis.get("price_precision", 5) or 5),
    )
    if not instruction:
        return
    if decision == "REJECT":
        instruction = actionable_rejection_instruction(
            symbol=symbol,
            direction=str(strategy_result.get("bias", "Neutral")),
            trigger_level=levels.get("trigger_level"),
            precision=int(analysis.get("price_precision", 5) or 5),
        ) or instruction

    previous_action = str(answers.get("next_action", "")).strip()
    answers["next_action"] = instruction
    story = str(answers.get("market_story", ""))
    if previous_action and previous_action in story:
        story = story.replace(previous_action, instruction)
        answers["market_story"] = story
        analysis["market_story"] = story

    strategy_result["next_action"] = instruction
    strategy_result["next_trigger"] = instruction
    strategy_result["trader_answers"] = answers
    analysis["next_required_confirmation"] = instruction
    analysis["missing_confirmation"] = instruction
    analysis["suggested_action"] = instruction

    answer_qa = analysis.get("answer_qa") or {}
    source = answer_qa.get("source_strategy") or {}
    source["next_trigger"] = instruction


def _apply_temporal_downgrade(
    strategy_result: dict[str, object],
    warnings: list[str],
) -> None:
    """Keep the main assistant conservative when temporal checks fail."""
    levels = dict(strategy_result.get("levels") or {})
    for key in ("entry_zone", "stop_loss", "tp1", "tp2", "rr1", "rr2"):
        levels[key] = None
    overlays = dict(strategy_result.get("overlays") or {})
    for key in ("entry_zone", "stop_loss", "tp1", "tp2", "trade_levels"):
        overlays[key] = None
    overlays["levels_mode"] = "hidden"
    setup = dict(strategy_result.get("setup_state") or {})
    if setup:
        setup["current_state"] = "NO_TRADE"
        setup["temporal_warnings"] = list(warnings)
    strategy_result.update(
        {
            "state": "NO_TRADE",
            "trade_status": "No Trade",
            "trade_readiness": "Not Ready",
            "trade_decision": "PENDING",
            "levels_mode": "hidden",
            "levels": levels,
            "overlays": overlays,
            "setup_state": setup,
            "market_story": "No Trade — analysis data is incomplete.",
            "next_trigger": "Wait for temporally complete market data before considering a trade.",
            "next_action": "Wait for temporally complete market data before considering a trade.",
            "trader_answers": {},
        }
    )


def _downgrade_invalid_entry_ready(
    analysis: dict[str, object],
    strategy_result: dict[str, object],
    symbol: str,
    warnings: list[str],
) -> None:
    """Hide final levels and replace a contradictory Entry Ready answer."""
    primary_warning = warnings[0] if warnings else "The setup is missing a required confirmation."
    hard_reject = any(
        phrase in warning.lower()
        for warning in warnings
        for phrase in ("risk/reward", "target is closer", "valid target", "current reward", "1.50r")
    )
    trade_status = "No Trade" if hard_reject else "Wait"
    next_action = _validation_next_action(warnings)
    answers = analysis["trader_answers"]
    trend = str(answers.get("trend", "Unclear"))
    direction_text = (
        f"The current market bias remains {trend.lower()},"
        if trend in {"Bullish", "Bearish"}
        else "Market direction is not clear,"
    )
    answers["trade_status"] = trade_status
    answers["trade_readiness"] = "Not Ready" if trade_status == "No Trade" else "Building"
    answers["next_action"] = next_action
    answers["market_story"] = (
        f"{symbol}: {direction_text} but no actionable entry is valid. "
        f"{primary_warning} {next_action}"
    )
    reasons = [
        str(reason)
        for reason in answers.get("why", [])
        if "meet the current confirmation rules" not in str(reason).lower()
    ]
    reasons.append(f"Entry is blocked: {primary_warning}")
    answers["why"] = reasons[-5:]
    answers["market_timeline"] = [
        f"Market bias: {trend}.",
        "The proposed entry failed V1 readiness validation.",
        next_action,
    ]

    hidden_levels = {
        "entry_zone": None,
        "stop_loss": None,
        "tp1": None,
        "tp2": None,
        "rr1": None,
        "rr2": None,
    }
    overlays = dict(strategy_result.get("overlays") or analysis.get("overlays") or {})
    overlays.update(
        {
            "entry_zone": None,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "trade_levels": None,
            "levels_mode": "hidden",
        }
    )
    state = "NO_TRADE" if hard_reject else "CONFIRMED_WAITING_FOR_ENTRY"
    decision = "REJECT" if hard_reject else "PENDING"
    strategy_result.update(
        {
            "state": state,
            "trade_decision": decision,
            "levels_mode": "hidden",
            "levels": hidden_levels.copy(),
            "overlays": overlays,
            "validation_downgraded": True,
        }
    )
    analysis.update(
        {
            "setup_status": state.replace("_", " "),
            "status": state.replace("_", " "),
            "trade_decision": decision,
            "levels_mode": "hidden",
            "levels": hidden_levels.copy(),
            "overlays": overlays,
            "missing_confirmation": next_action,
            "suggested_action": next_action,
            "next_required_confirmation": next_action,
            "summary": answers["market_story"],
        }
    )


def _validation_next_action(warnings: list[str]) -> str:
    text = " ".join(warnings).lower()
    if "inside or near" in text:
        return "Wait for price to pull back into the highlighted entry zone before considering entry."
    if "confirmation" in text:
        return "Wait for price to satisfy the confirmation trigger, then reassess the entry location."
    if "clear bullish or bearish" in text or "mixed market story" in text:
        return "Wait for market direction to become clear before considering a trade."
    if any(phrase in text for phrase in ("risk/reward", "target is closer", "valid target", "current reward", "1.50r")):
        return "Stand aside. Wait for a setup with a meaningful target and at least 1.50R."
    if "entry zone" in text:
        return "Wait for a valid entry zone to form before considering a trade."
    return "Wait for the missing trade conditions to align, then reassess."


def _strategy_result_to_analysis(
    strategy_result: dict[str, object],
    shared_analysis: dict[str, object],
    macro_dashboard: dict[str, object],
    top_down_analysis: dict[str, object],
    top_down_context: dict[str, object],
    query: dict[str, object],
) -> dict[str, object]:
    """Adapt the standard strategy result to the existing UI response shape."""
    bias = strategy_bias_to_legacy(str(strategy_result.get("bias", "Neutral")))
    state = str(strategy_result.get("state", "NO_SETUP"))
    score = int(strategy_result.get("score", 0) or 0)
    setup_quality = int(strategy_result.get("setup_quality", score) or 0)
    trade_quality = int(strategy_result.get("trade_quality", 0) or 0)
    trade_decision = str(strategy_result.get("trade_decision", "PENDING"))
    objective_plan = strategy_result.get("objective_plan") or {}
    levels_mode = str(strategy_result.get("levels_mode", "hidden"))
    levels = strategy_result.get("levels") or {}
    overlays = strategy_result.get("overlays") or {}
    progress = strategy_result.get("progress") or []
    current_stage = next((step for step in progress if step.get("is_current")), progress[0] if progress else {})
    session_context = macro_dashboard.get("session", {})
    market_phase = (macro_dashboard.get("market_phase") or {}).get("current_phase") or session_context.get("phase", "Waiting")
    story = str(strategy_result.get("market_story", "No market story available."))
    next_trigger = str(strategy_result.get("next_trigger", "Wait for the next confirmation."))
    setup_status = state.replace("_", " ")

    mentor = {
        "market_bias": strategy_result.get("bias", "Neutral"),
        "market_phase": market_phase,
        "trade_status": _strategy_trade_status(state, trade_decision),
        "trade_confidence": setup_quality,
        "setup_quality": setup_quality,
        "trade_quality": trade_quality,
        "trade_decision": trade_decision,
        "objective_plan": objective_plan,
        "current_stage": current_stage,
        "setup_journey": progress,
        "story_steps": strategy_result.get("why", []),
        "why": strategy_result.get("why", []),
        "next_trigger": next_trigger,
        "if_this_happens": _if_strategy_trigger_happens(state),
        "what_next": next_trigger,
        "progression": progress,
        "trade_opportunity": {
            "status": "Entry Ready" if levels_mode == "final" and trade_decision == "ACCEPT" else "No Trade",
            "message": "Entry-ready levels are available." if levels_mode == "final" and trade_decision == "ACCEPT" else str(objective_plan.get("reason") or "No valid trade yet."),
            "levels_mode": levels_mode,
            "levels": levels,
            "objective_plan": objective_plan,
        },
        "narrative": story,
    }

    return {
        "symbol": query["display_symbol"],
        "timeframe": query["timeframe"],
        "bias": bias,
        "setup_status": setup_status,
        "readiness": score,
        "readiness_level": {"percent": score, "label": state},
        "active_zone": _active_strategy_zone(overlays),
        "invalidation_level": None,
        "missing_confirmation": next_trigger,
        "suggested_action": next_trigger,
        "next_required_confirmation": next_trigger,
        "levels_mode": levels_mode,
        "invalidation_reason": None,
        "direction": _strategy_direction_text(strategy_result),
        "status": setup_status,
        "score": score,
        "setup_quality": setup_quality,
        "trade_quality": trade_quality,
        "trade_decision": trade_decision,
        "objective_plan": objective_plan,
        "checklist": _strategy_checklist(shared_analysis, strategy_result),
        "checklist_flags": _strategy_checklist_flags(shared_analysis, strategy_result),
        "levels": levels,
        "zones": _strategy_zones(shared_analysis),
        "overlays": overlays,
        "market_context": _strategy_market_context(shared_analysis, macro_dashboard),
        "recent_structure": _strategy_recent_structure(shared_analysis),
        "order_blocks": (shared_analysis.get("zones") or {}).get("order_blocks", {}),
        "session": session_context,
        "kill_zone": session_context,
        "liquidity_map": _strategy_liquidity_map(shared_analysis),
        "analysis_timeline": _strategy_timeline(strategy_result),
        "mentor": mentor,
        "market_narrative": story,
        "macro_dashboard": macro_dashboard,
        "top_down_analysis": top_down_analysis,
        "top_down_context": top_down_context,
        "summary": story,
    }


def _strategy_trade_status(state: str, trade_decision: str = "PENDING") -> str:
    if state == "ENTRY_READY" and trade_decision == "REJECT":
        return "No Trade"
    if state == "ENTRY_READY" and trade_decision == "PENDING":
        return "Building Setup"
    if state in {"ENTRY_READY", "TRADE_ACTIVE", "TP1_HIT", "TP2_HIT"}:
        return "Entry Ready" if state == "ENTRY_READY" else "Trade Active"
    if state in {"PULLBACK_ACTIVE", "AT_IMPORTANT_ZONE", "WAITING_FOR_CONFIRMATION", "WAITING_FOR_ENTRY", "CONFIRMED_WAITING_FOR_ENTRY"}:
        return "Building Setup"
    if state == "INVALIDATED":
        return "Invalidated"
    return "Watching"


def _if_strategy_trigger_happens(state: str) -> str:
    if state == "ENTRY_READY":
        return "If price trades into the active zone, the setup can move into trade management."
    if state in {"PULLBACK_ACTIVE", "AT_IMPORTANT_ZONE", "WAITING_FOR_CONFIRMATION"}:
        return "If confirmation closes beyond the trigger level, TradeScor will reveal final levels."
    if state in {"WAITING_FOR_ENTRY", "CONFIRMED_WAITING_FOR_ENTRY"}:
        return "If price returns to the active zone, TradeScor will reassess entry readiness."
    return "If the next condition forms, TradeScor will advance the selected strategy state."


def _strategy_direction_text(strategy_result: dict[str, object]) -> str:
    bias = str(strategy_result.get("bias", "Neutral"))
    if strategy_result.get("levels_mode") == "final" and bias in {"Bullish", "Bearish"}:
        return f"{bias.upper()} SETUP"
    if bias in {"Bullish", "Bearish"}:
        return f"{bias.upper()} BIAS"
    return "NO SETUP"


def _active_strategy_zone(overlays: dict[str, object]) -> dict[str, object]:
    zone = overlays.get("entry_zone") or overlays.get("pullback_zone") or {}
    if not zone:
        return {}
    return {"name": zone.get("label", "Active Zone"), **zone}


def _strategy_checklist(shared_analysis: dict[str, object], strategy_result: dict[str, object]) -> dict[str, str]:
    flags = _strategy_checklist_flags(shared_analysis, strategy_result)
    return {key: "detected" if value else "waiting" for key, value in flags.items()}


def _strategy_checklist_flags(shared_analysis: dict[str, object], strategy_result: dict[str, object]) -> dict[str, bool]:
    structure = shared_analysis.get("structure") or {}
    zones = shared_analysis.get("zones") or {}
    liquidity = shared_analysis.get("liquidity") or {}
    return {
        "htf_fvg": bool((zones.get("fvg") or [])),
        "liquidity_sweep": bool(liquidity.get("latest_sweep")),
        "mss": bool(structure.get("bos") or structure.get("choch")),
        "ifvg": str(strategy_result.get("state")) == "ENTRY_READY",
        "premium_discount": bool((shared_analysis.get("current") or {}).get("range_location")),
        "displacement": str(strategy_result.get("state")) in {"WAITING_FOR_CONFIRMATION", "ENTRY_READY"},
        "session": bool((strategy_result.get("confluence") or {}).get("components", {}).get("session_context")),
        "risk_reward": bool((strategy_result.get("levels") or {}).get("rr1")),
    }


def _strategy_zones(shared_analysis: dict[str, object]) -> dict[str, object]:
    zones = shared_analysis.get("zones") or {}
    fvgs = zones.get("fvg") or []
    return {
        "htf_fvg": fvgs[-1] if fvgs else {},
        "liquidity_zone": {},
        "ifvg": {},
        "mss": {},
        "support": zones.get("nearest_support") or {},
        "resistance": zones.get("nearest_resistance") or {},
    }


def _strategy_market_context(
    shared_analysis: dict[str, object],
    macro_dashboard: dict[str, object],
) -> dict[str, object]:
    current = shared_analysis.get("current") or {}
    trend = shared_analysis.get("trend") or {}
    session = macro_dashboard.get("session") or {}
    return {
        "bias_source": trend.get("reason", "Shared structure analysis"),
        "active_fvg_type": "",
        "dealing_range_high": current.get("range_high"),
        "dealing_range_low": current.get("range_low"),
        "premium_discount": current.get("range_location"),
        "current_session": session.get("name") or session.get("session"),
        "session_phase": session.get("phase"),
        "entry_allowed": session.get("entry_allowed"),
    }


def _strategy_recent_structure(shared_analysis: dict[str, object]) -> dict[str, object]:
    structure = shared_analysis.get("structure") or {}
    liquidity = shared_analysis.get("liquidity") or {}
    order_blocks = (shared_analysis.get("zones") or {}).get("order_blocks") or {}
    return {
        "last_swing_high": structure.get("last_swing_high") or {},
        "last_swing_low": structure.get("last_swing_low") or {},
        "liquidity_sweep": liquidity.get("latest_sweep") or {},
        "mss": structure.get("bos") or structure.get("choch") or {},
        "order_block": order_blocks.get("nearest") or {},
    }


def _strategy_liquidity_map(shared_analysis: dict[str, object]) -> dict[str, object]:
    liquidity = shared_analysis.get("liquidity") or {}
    current = shared_analysis.get("current") or {}
    return {
        "current_price": current.get("current_price"),
        "buy_side": [
            {"label": "Swing High", "price": level.get("price")}
            for level in liquidity.get("previous_swing_highs", [])
        ],
        "sell_side": [
            {"label": "Swing Low", "price": level.get("price")}
            for level in liquidity.get("previous_swing_lows", [])
        ],
        "current_target": {},
    }


def _strategy_timeline(strategy_result: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "time": "Current",
            "event_type": strategy_result.get("state", "Analysis"),
            "direction": strategy_result.get("bias", "Neutral"),
            "explanation": strategy_result.get("market_story", ""),
        }
    ]


def _get_chart_query(require_manual: bool = False) -> dict[str, object]:
    """Read and validate shared chart query parameters."""
    if require_manual and request.args.get("manual") != "1":
        raise ValueError("Click Load Chart to fetch candles.")

    symbol_text = request.args.get("symbol", "EUR/USD").strip() or "EUR/USD"
    requested_provider=str(request.args.get("provider","")).strip().lower()
    requested_asset=str(request.args.get("asset_class",request.args.get("asset_type",""))).strip().lower()
    timeframe = request.args.get("timeframe", "M5").strip().upper() or "M5"
    bars_text = request.args.get("bars", "300").strip()
    strategy = normalize_strategy_key(request.args.get("strategy", "auto"))
    multi_timeframe_enabled = _truthy(request.args.get("multi_timeframe", "0"))
    context_depth = normalize_context_depth(request.args.get("context_depth", "balanced"))
    marketaux_enabled = _truthy(request.args.get("marketaux_enabled", "1"))
    news_risk_enabled = _truthy(request.args.get("news_risk", "1"))
    dxy_confirmation_enabled = _truthy(request.args.get("dxy_confirmation", "0"))
    execution_mode = str(request.args.get("execution_mode", "conservative")).strip().lower()
    if execution_mode not in {"conservative", "aggressive"}:
        execution_mode = "conservative"
    try:
        minimum_rr = max(1.0, min(5.0, float(request.args.get("minimum_rr", "1.5"))))
    except ValueError:
        minimum_rr = 1.5
    is_deriv=requested_provider=="deriv" or requested_asset in {"derived","derived_index"}
    market_entry=None
    if is_deriv:symbol={"display_symbol":str(request.args.get("display_name") or symbol_text),"api_symbol":symbol_text,"asset_type":"derived_index"}
    else:
        try:
            market_entry=resolve_market(symbol_text);symbol={"display_symbol":market_entry["display_name"],"api_symbol":market_entry["provider_symbol"],"asset_type":market_entry["market_type"]}
        except ValueError:symbol=resolve_symbol(str(request.args.get("display_name") or symbol_text))

    if timeframe not in TIMEFRAME_INTERVALS:
        supported = ", ".join(TIMEFRAME_INTERVALS)
        raise ValueError(f"Unsupported timeframe '{timeframe}'. Use one of: {supported}")

    try:
        bars = int(bars_text)
    except ValueError:
        raise ValueError("bars must be a whole number") from None

    if bars <= 0:
        raise ValueError("bars must be greater than 0")

    return {
        "display_symbol": symbol["display_symbol"],
        "api_symbol": symbol["api_symbol"],
        "asset_type": symbol["asset_type"],
        "timeframe": timeframe,
        "interval": TIMEFRAME_INTERVALS[timeframe],
        "bars": bars,
        "strategy": strategy,
        "multi_timeframe_enabled": multi_timeframe_enabled,
        "context_depth": context_depth,
        "marketaux_enabled": marketaux_enabled,
        "news_risk_enabled": news_risk_enabled,
        "dxy_confirmation_enabled": dxy_confirmation_enabled,
        "execution_mode": execution_mode,
        "minimum_rr": minimum_rr,
        "provider":"deriv" if is_deriv else "twelve_data",
        "symbol_metadata":market_entry or {"provider_symbol":symbol_text,"display_name":str(request.args.get("display_name") or symbol_text),"family":request.args.get("family",""),"pip_size":_optional_float(request.args.get("pip_size")),"tick_size":_optional_float(request.args.get("tick_size")),"price_decimals":_optional_int(request.args.get("price_decimals")),"quantity_decimals":_optional_int(request.args.get("quantity_decimals"))},
    }


def _get_replay_query(payload: dict[str, object]) -> dict[str, object]:
    """Read and validate replay JSON parameters."""
    symbol_text = str(payload.get("symbol", "EUR/USD")).strip() or "EUR/USD"
    timeframe = str(payload.get("timeframe", "M5")).strip().upper() or "M5"
    strategy = normalize_strategy_key(payload.get("strategy", "auto"))
    multi_timeframe_enabled = _truthy(payload.get("multi_timeframe", bool(payload.get("context_candles"))))
    context_depth = normalize_context_depth(payload.get("context_depth", "balanced"))
    marketaux_enabled = _truthy(payload.get("marketaux_enabled", False))
    news_risk_enabled = _truthy(payload.get("news_risk", False))
    dxy_confirmation_enabled = _truthy(payload.get("dxy_confirmation", False))
    execution_mode = str(payload.get("execution_mode", "conservative")).strip().lower()
    if execution_mode not in {"conservative", "aggressive"}:
        execution_mode = "conservative"
    try:
        minimum_rr = max(1.0, min(5.0, float(payload.get("minimum_rr", 1.5))))
    except (TypeError, ValueError):
        minimum_rr = 1.5
    requested_provider=str(payload.get("provider","")).lower();requested_asset=str(payload.get("asset_class",payload.get("asset_type",""))).lower();is_deriv=requested_provider=="deriv" or requested_asset in {"derived","derived_index"};market_entry=None
    if is_deriv:symbol={"display_symbol":str(payload.get("display_name") or symbol_text),"api_symbol":symbol_text,"asset_type":"derived_index"}
    else:
        try:market_entry=resolve_market(symbol_text);symbol={"display_symbol":market_entry["display_name"],"api_symbol":market_entry["provider_symbol"],"asset_type":market_entry["market_type"]}
        except ValueError:symbol=resolve_symbol(str(payload.get("display_name") or symbol_text))

    if timeframe not in TIMEFRAME_INTERVALS:
        supported = ", ".join(TIMEFRAME_INTERVALS)
        raise ValueError(f"Unsupported timeframe '{timeframe}'. Use one of: {supported}")

    return {
        "display_symbol": symbol["display_symbol"],
        "api_symbol": symbol["api_symbol"],
        "asset_type": symbol["asset_type"],
        "timeframe": timeframe,
        "interval": TIMEFRAME_INTERVALS[timeframe],
        "bars": 0,
        "strategy": strategy,
        "multi_timeframe_enabled": multi_timeframe_enabled,
        "context_depth": context_depth,
        "marketaux_enabled": marketaux_enabled,
        "news_risk_enabled": news_risk_enabled,
        "dxy_confirmation_enabled": dxy_confirmation_enabled,
        "execution_mode": execution_mode,
        "minimum_rr": minimum_rr,
        "provider":"deriv" if is_deriv else "twelve_data",
        "symbol_metadata":payload.get("symbol_metadata") or market_entry or {"provider_symbol":symbol_text,"display_name":str(payload.get("display_name") or symbol_text),"family":payload.get("family","")},
    }


def _fetch_provider_candles(query:dict[str,object])->pd.DataFrame:
    provider=get_provider(provider=str(query.get("provider","twelve_data")),asset_class=str(query.get("asset_type","forex")))
    timeframe=str(query["timeframe"]) if provider.name=="deriv" else str(query["interval"])
    return provider.fetch_candles(str(query["api_symbol"]),timeframe,int(query["bars"]))


def _optional_float(value):
    try:return float(value) if value not in {None,""} else None
    except (TypeError,ValueError):return None

def _optional_int(value):
    try:return int(value) if value not in {None,""} else None
    except (TypeError,ValueError):return None

def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _acyclic_projection(value, stack=None):
    """Copy a response graph while cutting only true recursive references."""
    stack=set() if stack is None else stack
    if isinstance(value,dict):
        identity=id(value)
        if identity in stack:return None
        stack.add(identity);result={key:_acyclic_projection(item,stack) for key,item in value.items()};stack.remove(identity);return result
    if isinstance(value,(list,tuple)):
        identity=id(value)
        if identity in stack:return []
        stack.add(identity);result=[_acyclic_projection(item,stack) for item in value];stack.remove(identity);return result
    return value


def _load_context_candles(
    symbol: str,
    current_timeframe: str,
    current_candles: pd.DataFrame,
    current_bars: int,
) -> dict[str, pd.DataFrame]:
    """Fetch only the HTFs needed for the selected chart."""
    candles_by_timeframe = {current_timeframe: current_candles}

    for timeframe in required_timeframes(current_timeframe):
        if timeframe == current_timeframe:
            continue

        interval = TIMEFRAME_INTERVALS[timeframe]
        candles_by_timeframe[timeframe] = get_candles(
            symbol=symbol,
            timeframe=interval,
            bars=_top_down_bars(timeframe, current_bars),
        )

    return candles_by_timeframe


def _build_dxy_confirmation_filter(
    query: dict[str, object],
    replay: bool = False,
) -> dict[str, object]:
    """Return DXY filter shape without faking unavailable data."""
    if replay:
        result = unavailable_dxy_confirmation()
        result["message"] = "DXY unavailable during replay — not included in analysis."
        result["status"] = "Unavailable"
        result["enabled"] = False
        return result
    if not query.get("dxy_confirmation_enabled"):
        result = unavailable_dxy_confirmation()
        result["dxy_bias"] = "off"
        result["status"] = "Off"
        result["enabled"] = False
        result["message"] = "DXY confirmation is turned off."
        return result
    if not query.get("marketaux_enabled"):
        result = unavailable_dxy_confirmation()
        result["status"] = "Unavailable"
        result["enabled"] = False
        result["message"] = "DXY data provider is disabled."
        return result
    # Live DXY candles are intentionally deferred until symbol access is verified.
    result = unavailable_dxy_confirmation()
    result["status"] = "Unavailable"
    result["enabled"] = True
    return result


def _macro_dxy_from_filter(
    symbol: str,
    dxy_filter: dict[str, object],
) -> dict[str, object]:
    """Adapt the standardized market filter into the existing macro shape."""
    if not symbol_needs_dxy(symbol):
        return {
            "enabled": False,
            "dxy_trend": "Disabled",
            "correlation_status": "Not applicable",
            "confidence_impact": "No impact",
            "score_impact": 0,
            "message": "DXY correlation is only shown for USD-related symbols.",
        }
    return {
        "enabled": bool(dxy_filter.get("available")),
        "dxy_trend": str(dxy_filter.get("dxy_bias") or "Unavailable").title(),
        "correlation_status": "Waiting" if not dxy_filter.get("available") else "Neutral",
        "confidence_impact": "No impact",
        "score_impact": 0,
        "message": dxy_filter.get("message") or "DXY unavailable — not included in analysis.",
    }


def _apply_news_filter_gate(
    analysis: dict[str, object],
    strategy_result: dict[str, object],
    market_filters: dict[str, object],
) -> bool:
    """Downgrade ready setups when high-impact news blocks entry."""
    news = market_filters.get("news_risk") or {}
    if not news.get("blocks_entry"):
        return False

    answers = analysis.get("trader_answers") or {}
    trade_status = str(answers.get("trade_status") or strategy_result.get("trade_status") or "")
    final_plan = str(strategy_result.get("levels_mode") or analysis.get("levels_mode")).lower() == "final"
    accepted = str(strategy_result.get("trade_decision") or analysis.get("trade_decision")).upper() == "ACCEPT"
    if trade_status not in {"Entry Ready", "Trade Active"} and not (final_plan and accepted):
        _append_news_warning(answers, news)
        strategy_result["trader_answers"] = answers
        analysis["trader_answers"] = answers
        return True

    next_action = "High-impact news is close. Do not enter before the release. Wait for volatility to settle."
    message = str(news.get("message") or "High-impact news is close.")
    answers["trade_status"] = "Wait"
    answers["trade_readiness"] = "Building"
    answers["next_action"] = next_action
    reasons = [str(reason) for reason in answers.get("why", [])]
    reasons.append(message)
    answers["why"] = list(dict.fromkeys(reasons))[-5:]
    story = str(answers.get("market_story") or strategy_result.get("market_story") or "")
    if message not in story:
        story = f"{story} {message}".strip()
    answers["market_story"] = story

    strategy_result.update(
        {
            "trade_status": "Wait",
            "trade_readiness": "Building",
            "trade_decision": "PENDING",
            "levels_mode": "projected",
            "next_action": next_action,
            "next_trigger": next_action,
            "trader_answers": answers,
            "news_filter_action": "BLOCKED_ENTRY",
        }
    )
    metrics = analysis.get("trade_metrics") or {}
    metrics["plan_mode"] = "projected"
    warnings = list(metrics.get("warnings") or [])
    warnings.append(message)
    metrics["warnings"] = list(dict.fromkeys(warnings))

    analysis.update(
        {
            "trader_answers": answers,
            "market_story": story,
            "trade_decision": "PENDING",
            "levels_mode": "projected",
            "missing_confirmation": next_action,
            "suggested_action": next_action,
            "next_required_confirmation": next_action,
        }
    )
    return True


def _append_news_warning(answers: dict[str, object], news: dict[str, object]) -> None:
    message = str(news.get("message") or "")
    if not message or str(news.get("risk_level")) not in {"high", "medium"}:
        return
    reasons = [str(reason) for reason in answers.get("why", [])]
    reasons.append(message)
    answers["why"] = list(dict.fromkeys(reasons))[-5:]


def _build_dxy_correlation(
    symbol: str,
    top_down_analysis: dict[str, object],
    allow_market_request: bool = False,
) -> dict[str, object]:
    """Load DXY only when it is useful for the selected symbol."""
    alignment = str(top_down_analysis.get("overall_alignment", "Neutral"))
    directional_bias = directional_bias_from_alignment(alignment)

    if not symbol_needs_dxy(symbol):
        return analyze_dxy_correlation(symbol, directional_bias, None)

    if not allow_market_request:
        return analyze_dxy_correlation(symbol, directional_bias, None)

    try:
        dxy_candles = get_candles(symbol="DXY", timeframe="1h", bars=160)
    except RuntimeError:
        dxy_candles = None

    return analyze_dxy_correlation(symbol, directional_bias, dxy_candles)


def _friendly_market_error(
    message: str,
    query: dict[str, object] | None,
) -> str:
    """Return a helpful, safe error message for the frontend."""
    lower_message = message.lower()
    if "missing twelve_data_api_key" in lower_message or "rate limit" in lower_message:
        return message

    if query and query.get("asset_type") == "index":
        return (
            "This symbol may not be available on your Twelve Data plan. "
            "Try another symbol or update the mapping."
        )

    return message


def _top_down_bars(timeframe: str, current_bars: int) -> int:
    """Use enough HTF candles for context without requesting oversized payloads."""
    if timeframe == "W1":
        return 120
    if timeframe == "D1":
        return 180
    if timeframe in {"H4", "H1"}:
        return 220
    return min(max(current_bars, 120), 500)


def _candles_to_chart_records(candles):
    """Convert candles into Lightweight Charts candlestick records."""
    clean_candles = candles.copy()
    clean_candles["time"] = pd.to_datetime(clean_candles["time"], errors="coerce")

    for column in ["open", "high", "low", "close"]:
        clean_candles[column] = pd.to_numeric(clean_candles[column], errors="coerce")

    clean_candles = clean_candles.dropna(subset=["time", "open", "high", "low", "close"])
    clean_candles = clean_candles.sort_values("time")
    clean_candles = clean_candles.drop_duplicates(subset=["time"], keep="last")

    records = []

    for _, candle in clean_candles.iterrows():
        records.append(
            {
                "time": _to_unix_seconds(candle["time"]),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            }
        )

    return records


def _deriv_candle_records(candles):
    """Return normalized provider candles without frontend-derived fields."""
    return [{"time":_to_unix_seconds(row["time"]),"open":float(row["open"]),"high":float(row["high"]),"low":float(row["low"]),"close":float(row["close"]),"complete":bool(row.get("complete",True)),"provider":"deriv","symbol":str(row.get("symbol","")),"timeframe":str(row.get("timeframe",""))} for _,row in candles.iterrows()]


def _candles_from_chart_records(records) -> pd.DataFrame:
    """Convert posted Lightweight Charts records into scanner candles."""
    if not isinstance(records, list) or not records:
        raise ValueError("Replay requires a non-empty candles array.")

    candles = pd.DataFrame(records)
    required_columns = ["time", "open", "high", "low", "close"]
    missing_columns = [column for column in required_columns if column not in candles.columns]

    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Replay candles are missing column(s): {missing}.")

    candles["time"] = [_parse_candle_time(value) for value in candles["time"]]

    for column in ["open", "high", "low", "close"]:
        candles[column] = pd.to_numeric(candles[column], errors="coerce")

    candles = candles.dropna(subset=["time", "open", "high", "low", "close"])
    candles = candles.sort_values("time")
    candles = candles.drop_duplicates(subset=["time"], keep="last")

    if candles.empty:
        raise ValueError("Replay candles were received, but none were usable.")

    return candles[["time", "open", "high", "low", "close"]].reset_index(drop=True)


def _context_candles_from_payload(payload_context: object) -> dict[str, pd.DataFrame]:
    """Convert posted context candles into timeframe DataFrames without market calls."""
    if not isinstance(payload_context, dict):
        return {}

    context: dict[str, pd.DataFrame] = {}
    for timeframe, records in payload_context.items():
        try:
            normalized_timeframe = str(timeframe).upper()
            if normalized_timeframe not in TIMEFRAME_INTERVALS:
                continue
            context[normalized_timeframe] = _candles_from_chart_records(records)
        except ValueError:
            continue

    return context


def _parse_candle_time(value):
    """Parse a Unix-second or datetime candle time."""
    numeric_value = pd.to_numeric(value, errors="coerce")

    if pd.notna(numeric_value):
        return pd.to_datetime(int(numeric_value), unit="s", utc=True)

    return pd.to_datetime(value, errors="coerce", utc=True)


def _to_unix_seconds(value) -> int:
    """Convert a pandas datetime value into Unix seconds for the chart."""
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")

    return int(timestamp.timestamp())


def _to_json_records(dataframe):
    """Convert a pandas DataFrame into JSON-friendly records."""
    clean_dataframe = dataframe.copy()

    for column in clean_dataframe.columns:
        if str(clean_dataframe[column].dtype).startswith("datetime"):
            clean_dataframe[column] = clean_dataframe[column].astype(str)

    return clean_dataframe.to_dict(orient="records")


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    """Run a multi-strategy backtest on historical candles.

    Only executes when the client explicitly calls this endpoint.
    Candles are fetched once and shared across all requested strategies.
    """
    t_start = time.time()
    payload = request.get_json(silent=True) or {}
    print(f"[BACKTEST] request received: {payload}")

    try:
        symbol_text = str(payload.get("symbol", "EUR/USD")).strip() or "EUR/USD"
        timeframe = str(payload.get("timeframe", "M15")).strip().upper() or "M15"
        bars_raw = payload.get("bars", 300)
        risk_per_trade = float(payload.get("risk_per_trade", 1.0))
        starting_balance = float(payload.get("starting_balance", 10_000.0))
        requested_strategies = payload.get(
            "strategies", ["universal_structure", "supply_demand", "breakout_retest"]
        )

        if not isinstance(requested_strategies, list) or not requested_strategies:
            requested_strategies = ["universal_structure", "supply_demand", "breakout_retest"]

        # Mode determines signal step and analysis window
        mode = str(payload.get("mode", "fast")).strip().lower()
        if mode not in {"fast", "accurate"}:
            mode = "fast"
        config = get_config(mode)
        requested_bars = max(50, int(bars_raw))
        bars = min(requested_bars, config.max_bars)

        if timeframe not in TIMEFRAME_INTERVALS:
            supported = ", ".join(TIMEFRAME_INTERVALS)
            return jsonify({"ok": False, "error": f"Unsupported timeframe '{timeframe}'. Use one of: {supported}"}), 400

        symbol = resolve_symbol(symbol_text)
        api_symbol = symbol["api_symbol"]
        display_symbol = symbol["display_symbol"]
        interval = TIMEFRAME_INTERVALS[timeframe]

    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc), "result": None}), 400

    try:
        # Fetch candles once — reuse cache if available
        candles = get_candles(symbol=api_symbol, timeframe=interval, bars=bars)
        if candles.empty:
            return jsonify({"ok": False, "error": "No candles were returned. Check the symbol and timeframe.", "result": None}), 500

        print(f"[BACKTEST] fetched {len(candles)} candles for {display_symbol} {timeframe}")
        print(f"[BACKTEST] running strategies: {requested_strategies} mode={mode}")

    except RuntimeError as exc:
        return jsonify({"ok": False, "error": _friendly_market_error(str(exc), None), "result": None}), 500

    try:
        backtest_result = run_backtest(
            candles,
            requested_strategies,
            symbol=display_symbol,
            timeframe=timeframe,
            risk_per_trade=risk_per_trade,
            starting_balance=starting_balance,
            mode=mode,
        )

        if (backtest_result.get("metadata") or {}).get("timed_out"):
            return jsonify({
                "ok": False,
                "error": "Backtest timed out before producing results.",
                "result": None,
            }), 408

        generated_at = datetime.now(timezone.utc).isoformat()
        result_identity = {
            "tested_symbol": display_symbol,
            "tested_timeframe": timeframe,
            "tested_bars": backtest_result["n_candles"],
            "requested_bars": requested_bars,
            "tested_mode": mode,
            "tested_strategies": requested_strategies,
            "generated_at": generated_at,
        }
        backtest_result["metadata"].update(result_identity)
        backtest_result["metadata"]["bars_capped"] = requested_bars > bars

        report = build_report(
            backtest_result["trades"],
            n_candles=backtest_result["n_candles"],
            symbol=display_symbol,
            timeframe=timeframe,
            risk_per_trade=risk_per_trade,
            starting_balance=starting_balance,
            backtest_warnings=backtest_result["warnings"],
            metadata=backtest_result.get("metadata"),
            diagnostics_by_strategy=backtest_result.get("diagnostics"),
            selected_strategies=requested_strategies,
        )

    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Backtest engine error: {exc}", "result": None}), 500

    elapsed = round(time.time() - t_start, 1)
    print(f"[BACKTEST] complete in {elapsed}s — strategies: {list(backtest_result['trades'].keys())}")

    return jsonify({**report, **result_identity, "result_identity": result_identity, "ok": True})



if __name__ == "__main__":
    # The Werkzeug reloader forks the application and must never inherit the
    # dedicated historical process pool or live WebSocket. Development debug
    # output remains opt-in, while the serving process stays singular.
    app.run(debug=_truthy(os.getenv("FLASK_DEBUG","0")),use_reloader=False)
