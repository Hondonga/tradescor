from __future__ import annotations
import html,json
def report_html(report):
    body=html.escape(json.dumps(report,indent=2,default=str));return "<!doctype html><meta charset='utf-8'><title>TradeScor ML Training Report</title><style>body{background:#080b10;color:#dbe5f3;font:14px system-ui;padding:32px}pre{background:#101722;padding:20px;border-radius:8px;white-space:pre-wrap}</style><h1>TradeScor Offline ML Training Report</h1><p>Research only. No live activation endpoint exists.</p><pre>"+body+"</pre>"
