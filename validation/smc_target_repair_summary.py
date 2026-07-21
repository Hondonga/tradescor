"""Build the before/after structural-target repair acceptance artifact."""
from __future__ import annotations

from collections import Counter
import html
import json
from pathlib import Path
import sqlite3

SYMBOLS=("R_10","R_50","R_75","R_100","JD10","JD50","JD75","JD100","stpRNG")


def build_summary(root="data/smc_matrix",output=None):
    root=Path(root);rows=[];rejections=Counter();sources=Counter();total_candidates=0;normalized_ready=0;raw_ready=0
    for symbol in SYMBOLS:
        db=_database(root,symbol);decisions=_decisions(db);report=_report(root,symbol);candidate_count=0;symbol_rejections=Counter();symbol_sources=Counter();symbol_raw=0;symbol_normalized=0
        for payload in decisions:
            smc=payload.get("smc_contract") or {};trace=smc.get("target_trace") or (smc.get("setup") or {}).get("target_trace") or {}
            found=trace.get("candidates_found") or [];candidate_count+=len(found);sources.update(x.get("source_type") or "unknown" for x in found);symbol_sources.update(x.get("source_type") or "unknown" for x in found)
            rejected=trace.get("candidates_rejected") or [];rejections.update(x.get("rejection_code") or "unknown" for x in rejected);symbol_rejections.update(x.get("rejection_code") or "unknown" for x in rejected)
            symbol_raw+=int((smc.get("setup") or {}).get("state")=="TRADE_READY");symbol_normalized+=int(((payload.get("normalized_decision") or {}).get("decision") or {}).get("trade_ready") is True)
        row=(report.get("reports") or [{}])[0];summary=(row.get("symbols") or [{}])[0]
        rows.append({"symbol":symbol,"decisions":len(decisions),"target_candidates":candidate_count,"candidate_sources":dict(symbol_sources),"rejection_codes":dict(symbol_rejections),"raw_trade_ready":symbol_raw,"normalized_trade_ready":symbol_normalized,"fills":summary.get("filled_trades",0),"resolved":summary.get("resolved_trades",0),"invalid_trade_plans":summary.get("invalid_trade_plans",0),"causality_violations":summary.get("causality_violations",0),"dominant_blocker":summary.get("most_common_blocker")})
        total_candidates+=candidate_count;raw_ready+=symbol_raw;normalized_ready+=symbol_normalized
    unavailable=[{"display_name":"Multi Step Index","status":"UNAVAILABLE"},{"display_name":"Skew Step Up Index","status":"UNAVAILABLE"},{"display_name":"Skew Step Down Index","status":"UNAVAILABLE"}]
    result={"milestone":"SMC structural target reachability repair","selection_policy":"fixed_calendar_v1; selected before outcome inspection","before":{"available_symbols":9,"decisions":2592,"target_reachable_setup_types":0,"fills":0,"causality_violations":0,"invalid_jd75_ready_state":1},"after":{"available_symbols":9,"decisions":sum(x["decisions"] for x in rows),"target_candidates_evaluated":total_candidates,"candidate_sources":dict(sources),"rejection_codes":dict(rejections),"raw_trade_ready":raw_ready,"normalized_trade_ready":normalized_ready,"fills":sum(x["fills"] for x in rows),"resolved":sum(x["resolved"] for x in rows),"invalid_trade_plans":sum(x["invalid_trade_plans"] for x in rows),"causality_violations":sum(x["causality_violations"] for x in rows),"evidence":"INSUFFICIENT"},"symbols":rows,"unavailable":unavailable,"interpretation":"Candidate creation and rejection are now observable. Trade count is not an acceptance criterion and no target was fabricated."}
    output=Path(output or root/"structural_target_repair_matrix.json");output.write_text(json.dumps(result,indent=2,sort_keys=True));output.with_suffix(".html").write_text(_html(result));return result


def _database(root,symbol):
    revised=root/"target_runs_v2"/f"{symbol}.db";return revised if revised.exists() else root/"target_runs"/f"{symbol}.db"
def _decisions(path):
    db=sqlite3.connect(path);rows=[json.loads(x[0]) for x in db.execute("SELECT payload_json FROM replay_decisions ORDER BY base_candle_index")];db.close();return rows
def _report(root,symbol):return json.loads((root/f"latest_matrix-{symbol}.json").read_text())
def _html(result):
    rows="".join(f"<tr><td>{html.escape(x['symbol'])}</td><td>{x['decisions']}</td><td>{x['target_candidates']}</td><td>{x['raw_trade_ready']}</td><td>{x['normalized_trade_ready']}</td><td>{x['invalid_trade_plans']}</td><td>{x['causality_violations']}</td></tr>" for x in result["symbols"])
    return f"<!doctype html><html><head><meta charset='utf-8'><title>SMC Target Repair Matrix</title><style>body{{font:14px system-ui;background:#07111f;color:#dce8f7;padding:28px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border-bottom:1px solid #24354b;text-align:left}}code,pre{{color:#86c7ff}}</style></head><body><h1>SMC Structural Target Repair</h1><p>Fixed preselected 24-hour window · evidence remains INSUFFICIENT</p><table><thead><tr><th>Symbol</th><th>Decisions</th><th>Target candidates</th><th>Raw ready</th><th>Normalized ready</th><th>Invalid plans</th><th>Causality</th></tr></thead><tbody>{rows}</tbody></table><h2>Rejection trace</h2><pre>{html.escape(json.dumps(result['after']['rejection_codes'],indent=2))}</pre><h2>Unavailable</h2><pre>{html.escape(json.dumps(result['unavailable'],indent=2))}</pre></body></html>"


if __name__=="__main__":print(json.dumps(build_summary()["after"],indent=2))
