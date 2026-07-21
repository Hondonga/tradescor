"""Chrome acceptance for the normalized TradeScor chart lifecycle.

Runs against the local Flask server with an isolated headless Chrome profile.
It uses the Chrome DevTools Protocol directly so no browser test dependency is
added to the application.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SYMBOLS = {
    "twelve_data:GBP/USD": "GBP/USD",
    "twelve_data:EUR/USD": "EUR/USD",
    "twelve_data:USD/JPY": "USD/JPY",
    "twelve_data:USD/CAD": "USD/CAD",
    "deriv:R_75": "Volatility 75 Index",
    "deriv:JD75": "Jump 75 Index",
    "deriv:stpRNG": "Step Index 100",
    "deriv:BOOM500": "Boom 500 Index",
    "deriv:CRASH500": "Crash 500 Index",
}


class CDP:
    def __init__(self, socket_url: str):
        self.socket = websocket.create_connection(socket_url, timeout=10)
        self.serial = 0
        self.events: list[dict] = []

    def call(self, method: str, params: dict | None = None, timeout: float = 30):
        self.serial += 1
        message_id = self.serial
        self.socket.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.socket.settimeout(max(.1, deadline - time.time()))
            message = json.loads(self.socket.recv())
            if message.get("id") == message_id:
                if message.get("error"):
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result") or {}
            self.events.append(message)
        raise TimeoutError(method)

    def evaluate(self, expression: str):
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        remote = result.get("result") or {}
        if remote.get("subtype") == "error":
            raise RuntimeError(remote.get("description") or expression)
        return remote.get("value")

    def close(self):
        try:
            self.socket.close()
        except OSError:
            pass


def wait_until(predicate, timeout=30, interval=.25, description="condition"):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except (RuntimeError, OSError, websocket.WebSocketException):
            pass
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for {description}; last={last!r}")


def key(cdp: CDP, value: str, code: str, virtual_key: int):
    common = {"key": value, "code": code, "windowsVirtualKeyCode": virtual_key, "nativeVirtualKeyCode": virtual_key}
    cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", **common})
    cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", **common})


def select_option(cdp: CDP, aria_label: str, wanted: str):
    selector = f'select[aria-label="{aria_label}"]'
    present = cdp.evaluate(f'Boolean(document.querySelector({json.dumps(selector)}))')
    if not present:
        raise AssertionError(f"Missing {aria_label} selector")
    options = cdp.evaluate(f'Array.from(document.querySelector({json.dumps(selector)}).options).map(o => o.value)')
    if wanted not in options:
        raise AssertionError(f"{wanted} missing from {aria_label}: {options}")
    changed = cdp.evaluate("""
      (() => {
        const select = document.querySelector(%s);
        const setter = Object.getOwnPropertyDescriptor(
          HTMLSelectElement.prototype, 'value'
        ).set;
        setter.call(select, %s);
        select.dispatchEvent(new Event('change', {bubbles: true}));
        return select.value;
      })()
    """ % (json.dumps(selector), json.dumps(wanted)))
    if changed != wanted:
        raise AssertionError(f"Could not select {wanted} in {aria_label}")
    wait_until(lambda: cdp.evaluate(f'document.querySelector({json.dumps(selector)}).value') == wanted, description=f"{aria_label}={wanted}")


def click_text_button(cdp: CDP, label: str):
    expression = """
      (() => {
        const node = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim() === %s);
        if (!node) return null;
        const r = node.getBoundingClientRect();
        return {x:r.left+r.width/2,y:r.top+r.height/2};
      })()
    """ % json.dumps(label)
    point = cdp.evaluate(expression)
    if not point:
        raise AssertionError(f"Missing button {label}")
    cdp.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": point["x"], "y": point["y"], "button": "left", "clickCount": 1})
    cdp.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": point["x"], "y": point["y"], "button": "left", "clickCount": 1})


def navigate(cdp: CDP, url: str):
    cdp.call("Page.navigate", {"url": url})
    wait_until(lambda: cdp.evaluate("document.readyState") == "complete", timeout=30, description=url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--workspace-timeout", type=int, default=180)
    parser.add_argument("--output", default="test-results/chrome_overlay_acceptance.json")
    parser.add_argument("--screenshot", default="test-results/chrome_overlay_acceptance.png")
    args = parser.parse_args()
    if not Path(CHROME).exists():
        raise SystemExit("Google Chrome is unavailable")
    profile = tempfile.mkdtemp(prefix="tradescor-chrome-")
    log_path = Path("test-results/chrome_overlay_acceptance.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen([
        CHROME,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-background-networking",
        "--disable-component-update",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-allow-origins=*",
        f"--remote-debugging-port={args.port}",
        f"--user-data-dir={profile}",
        "--window-size=1600,1000",
        "about:blank",
    ], stdout=log, stderr=log)
    cdp = None
    try:
        version_url = f"http://127.0.0.1:{args.port}/json/version"
        wait_until(lambda: json.load(urllib.request.urlopen(version_url, timeout=1)), timeout=15, description="Chrome debugger")
        target_url = f"http://127.0.0.1:{args.port}/json/new?{urllib.parse.quote(args.base_url + '/markets', safe=':/')}"
        request = urllib.request.Request(target_url, method="PUT")
        target = json.load(urllib.request.urlopen(request, timeout=5))
        cdp = CDP(target["webSocketDebuggerUrl"])
        for domain in ("Page.enable", "Runtime.enable", "DOM.enable", "Log.enable"):
            cdp.call(domain)
        wait_until(lambda: cdp.evaluate("document.readyState") == "complete", timeout=30, description="Markets page")
        wait_until(lambda: len(cdp.evaluate('Array.from(document.querySelectorAll(\'select[aria-label="Symbol"] option\')).map(o=>o.value)')) >= len(SYMBOLS), timeout=30, description="market registry options")
        switching = []
        for symbol_id, display_name in SYMBOLS.items():
            select_option(cdp, "Symbol", symbol_id)
            selected = cdp.evaluate('document.querySelector(\'select[aria-label="Symbol"]\').selectedOptions[0].textContent.trim()')
            if selected != display_name:
                raise AssertionError(f"{symbol_id} selected as {selected!r}, expected {display_name!r}")
            switching.append({"symbol_id": symbol_id, "display_name": selected, "passed": True})

        select_option(cdp, "Symbol", "deriv:R_75")
        navigate(cdp, args.base_url + "/workspace")
        wait_until(lambda: cdp.evaluate('document.querySelector(\'select[aria-label="Symbol"]\').value') == "deriv:R_75", description="R_75 workspace")
        wait_until(
            lambda: cdp.evaluate("""
              (() => {
                const rows=Array.from(document.querySelectorAll('dt'));
                const row=rows.find(x=>x.textContent.trim()==='Current price');
                return row && row.nextElementSibling && row.nextElementSibling.textContent.trim() !== '—' && !document.body.innerText.includes('Loading completed market context');
              })()
            """),
            timeout=args.workspace_timeout,
            interval=1,
            description="completed R_75 workspace decision",
        )
        state = cdp.evaluate("""
          (() => {
            const value=(label)=>{const dt=Array.from(document.querySelectorAll('dt')).find(x=>x.textContent.trim()===label);return dt?.nextElementSibling?.textContent.trim()||null};
            const button=(label)=>Array.from(document.querySelectorAll('button')).find(x=>x.textContent.trim()===label);
            const inspector=document.querySelector('select[aria-label="Inspect chart drawing metadata"]');
            return {
              body:document.body.innerText,
              current_price:value('Current price'),
              active_setup:value('Setup ID'),
              lifecycle:value('Lifecycle'),
              trade_plan_button:button('Trade Plan')?.className||null,
              advanced_button:button('Advanced SMC')?.className||null,
              previous_button:button('Previous Setup')?.className||null,
              drawing_count:inspector ? inspector.options.length-1 : 0,
              drawing_labels:inspector ? Array.from(inspector.options).slice(1).map(x=>x.textContent.trim()) : [],
            };
          })()
        """)
        if not state["current_price"] or not state["current_price"].replace("-", "").replace(".", "").isdigit() or len(state["current_price"].split(".")[-1]) != 4:
            raise AssertionError(f"R_75 precision mismatch: {state['current_price']!r}")
        if "No analysis yet" in state["body"]:
            raise AssertionError("Workspace never accepted the R_75 decision")
        if "border-transparent" not in (state["advanced_button"] or "") or "border-transparent" not in (state["previous_button"] or ""):
            raise AssertionError("Advanced or Previous Setup was visible by default")
        click_text_button(cdp, "Advanced SMC")
        time.sleep(.5)
        after_advanced = cdp.evaluate("""
          (()=>{const i=document.querySelector('select[aria-label="Inspect chart drawing metadata"]');return i?i.options.length-1:0})()
        """)
        if after_advanced < state["drawing_count"]:
            raise AssertionError("Advanced SMC removed visible backend drawings")
        screenshot = cdp.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        Path(args.screenshot).write_bytes(base64.b64decode(screenshot["data"]))

        select_option(cdp, "Model", "volatility_smc")
        wait_until(lambda: "No analysis yet" in cdp.evaluate("document.body.innerText"), timeout=5, description="model-switch overlay clear")
        report = {
            "browser": "Google Chrome",
            "base_url": args.base_url,
            "symbol_switch_matrix": switching,
            "workspace": {
                "symbol_id": "deriv:R_75",
                "current_price": state["current_price"],
                "active_setup": state["active_setup"],
                "lifecycle": state["lifecycle"],
                "drawing_count_default": state["drawing_count"],
                "drawing_count_advanced": after_advanced,
                "drawing_labels_default": state["drawing_labels"],
                "previous_setup_hidden_by_default": True,
                "model_switch_cleared_decision": True,
            },
            "console_errors": [event for event in cdp.events if event.get("method") == "Log.entryAdded" and ((event.get("params") or {}).get("entry") or {}).get("level") == "error"],
            "passed": True,
        }
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        if cdp:
            try:
                cdp.call("Browser.close", timeout=2)
            except (RuntimeError, OSError, TimeoutError, websocket.WebSocketException):
                pass
            cdp.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        log.close()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
