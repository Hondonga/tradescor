"""Deterministic real-data runner for the SMC historical acceptance matrix."""

from __future__ import annotations

from datetime import datetime, timezone
import html
import json
from pathlib import Path

import pandas as pd

from providers.deriv_provider import DerivProvider
from replay.derived_replay_dataset import acquire_deriv_dataset
from replay.derived_replay_service import DerivedReplayService
from validation.smc_acceptance_service import SMCAcceptanceService
from validation.smc_dataset_matrix import (
    SELECTION_POLICY,
    build_matrix_dataset,
    resolve_required_symbols,
    unavailable_matrix_rows,
)


class SMCHistoricalMatrixRunner:
    def __init__(self, provider=None, replay_service=None, acceptance_service=None, cache_dir="data/smc_matrix"):
        self.provider=provider or DerivProvider()
        self.replay=replay_service or DerivedReplayService()
        self.acceptance=acceptance_service or SMCAcceptanceService(self.replay)
        self.cache_dir=Path(cache_dir)
        self.cache_dir.mkdir(parents=True,exist_ok=True)

    def acquire(self, policy=None):
        policy={**SELECTION_POLICY,**(policy or {})}
        active=self.provider.list_symbols()
        datasets=[]
        for spec in resolve_required_symbols(active):
            downloaded_at=datetime.now(timezone.utc).isoformat()
            raw=self._load_cached(spec,policy)
            if raw is None:
                _,raw=acquire_deriv_dataset(
                    self.provider,
                    provider_symbol=spec["symbol"],
                    display_name=spec["display_name"],
                    family=spec["family"],
                    start_time=policy["period_start"],
                    end_time=policy["period_end"],
                    base_timeframe="M1",
                    cache_dir=self.cache_dir/"provider",
                )
                self._save_cached(spec,policy,raw,downloaded_at)
            else:
                downloaded_at=self._cache_metadata(spec,policy).get("downloaded_at")
            metadata,normalized=build_matrix_dataset(spec,raw,policy,downloaded_at)
            datasets.append({"spec":spec,"metadata":metadata,"candles":normalized})
        return {
            "selection_policy":policy,
            "datasets":datasets,
            "unavailable":unavailable_matrix_rows(active),
        }

    def run(self, policy=None, symbols=None):
        acquisition=self.acquire(policy)
        requested=set(symbols or ())
        reports=[]
        for item in acquisition["datasets"]:
            spec=item["spec"]
            if requested and spec["symbol"] not in requested:continue
            run=self.replay.create_run(
                provider_symbol=spec["symbol"],
                display_name=spec["display_name"],
                family=spec["family"],
                candles=item["candles"],
                base_timeframe="M1",
                strategy="Auto",
                metadata={"acceptance_selection_policy":acquisition["selection_policy"]},
                background=False,
            )
            run_id=run["replay_run_id"]
            if run["status"] != "completed":
                reports.append({"symbol":spec["symbol"],"run_id":run_id,"status":run["status"],"error":run.get("error")})
                continue
            reports.append(self.acceptance.validate_run(run_id,item["metadata"]))
        result={"selection_policy":acquisition["selection_policy"],"reports":reports,"unavailable":acquisition["unavailable"]}
        suffix="-"+"-".join(sorted(requested)) if requested else ""
        (self.cache_dir/f"latest_matrix{suffix}.json").write_text(json.dumps(result,indent=2,default=str))
        (self.cache_dir/f"latest_matrix{suffix}.html").write_text(render_matrix_html(result))
        return result

    def _key(self,spec,policy):
        safe=str(spec["symbol"]).replace("/","_")
        start=pd.Timestamp(policy["period_start"]).strftime("%Y%m%d%H%M")
        end=pd.Timestamp(policy["period_end"]).strftime("%Y%m%d%H%M")
        return f"v2-{safe}-{start}-{end}"

    def _load_cached(self,spec,policy):
        path=self.cache_dir/f"{self._key(spec,policy)}.json"
        if not path.exists():return None
        return pd.read_json(path)

    def _save_cached(self,spec,policy,rows,downloaded_at):
        key=self._key(spec,policy)
        rows.to_json(self.cache_dir/f"{key}.json",orient="records",double_precision=15)
        (self.cache_dir/f"{key}.meta.json").write_text(json.dumps({"downloaded_at":downloaded_at,"selection_policy":policy},indent=2))

    def _cache_metadata(self,spec,policy):
        path=self.cache_dir/f"{self._key(spec,policy)}.meta.json"
        return json.loads(path.read_text()) if path.exists() else {}


def render_matrix_html(result):
    rows=[]
    for report in result.get("reports",[]):
        for symbol in report.get("symbols",[]):
            rows.append(f"<tr><td>{html.escape(str(symbol['symbol']))}</td><td>{html.escape(str(symbol['family']))}</td><td>{symbol['decisions']}</td><td>{symbol['trade_ready_setups']}</td><td>{symbol['filled_trades']}</td><td>{symbol['causality_violations']}</td><td>{symbol['invalid_trade_plans']}</td><td>{html.escape(symbol['evidence'])}</td></tr>")
    for item in result.get("unavailable",[]):
        rows.append(f"<tr><td>{html.escape(item['display_name'])}</td><td>{html.escape(item['family'])}</td><td colspan='5'>Unavailable from official active_symbols; no substitute used</td><td>INSUFFICIENT</td></tr>")
    policy=html.escape(json.dumps(result.get("selection_policy",{}),sort_keys=True))
    return "<!doctype html><html><head><meta charset='utf-8'><title>TradeScor SMC Matrix</title><style>body{font:14px system-ui;background:#07111f;color:#dce8f7;padding:28px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #24354b;text-align:left}code{color:#86c7ff}</style></head><body><h1>SMC Historical Acceptance Matrix</h1><p><code>"+policy+"</code></p><table><thead><tr><th>Symbol</th><th>Family</th><th>Decisions</th><th>Ready</th><th>Filled</th><th>Causality</th><th>Invalid plans</th><th>Evidence</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table></body></html>"


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol",action="append",help="Run only this provider symbol; repeatable.")
    parser.add_argument("--period-start",help="Preselected inclusive UTC start; never derived from outcomes.")
    parser.add_argument("--period-end",help="Preselected exclusive UTC end; never derived from outcomes.")
    args=parser.parse_args()
    policy={"period_start":args.period_start,"period_end":args.period_end,"policy_id":"fixed_calendar_7d_v1","selection_reason":"Fixed seven-day calendar block selected before performance evaluation.","performance_fields_used":[]} if args.period_start and args.period_end else None
    result=SMCHistoricalMatrixRunner().run(policy=policy,symbols=args.symbol)
    print(json.dumps({"reports":len(result["reports"]),"unavailable":result["unavailable"]},indent=2))


if __name__ == "__main__":main()
