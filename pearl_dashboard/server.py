"""Local web dashboard + control loop.

    python -m pearl_dashboard.server            # real data, reads config.yaml
    MOCK=1 python -m pearl_dashboard.server     # fake data, for trying the page out
"""
import argparse
import json
import math
import os
import re
import secrets
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

from . import config as config_mod
from .controller import Controller
from .mock import FakeSession, seed_history
from .report import summarize
from .store import Store

HERE = Path(__file__).resolve().parent
TOKEN = secrets.token_urlsafe(16)


def make_handler(ctrl, port):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    page = (HERE / "static" / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(_finite(obj), ensure_ascii=False, default=str))

        def _host_ok(self):
            # Blocks DNS-rebinding: only answer requests addressed to localhost.
            if self.headers.get("Host") not in allowed_hosts:
                self._json(403, {"error": "bad host"})
                return False
            return True

        def do_GET(self):
            if not self._host_ok():
                return
            if self.path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._json(200, ctrl.state or {"loading": True, "error": ctrl.last_error})
            elif self.path == "/api/history":
                self._json(200, history(ctrl))
            elif self.path == "/api/settings":
                self._json(200, settings_view(ctrl))
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._host_ok():
                return
            if not secrets.compare_digest(self.headers.get("X-Token", ""), TOKEN):
                return self._json(403, {"error": "bad token"})
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            # Answer right away; the background loop picks up the change on its next
            # cycle, which request_cycle() starts immediately.
            try:
                if self.path == "/api/mode":
                    message = ctrl.set_mode(body.get("mode"))
                elif self.path == "/api/stop_all":
                    ctrl.stop_all()
                    message = "已退掉所有实例并暂停"
                elif self.path == "/api/destroy":
                    ctrl.destroy_one(body.get("id"))
                    message = f"已退租 {body.get('id')}"
                elif self.path == "/api/settings":
                    apply_settings(ctrl, body)
                    ctrl.request_cycle()
                    return self._json(200, settings_view(ctrl))
                elif self.path == "/api/refresh":
                    message = "正在用最新数据检查…"
                else:
                    return self._json(404, {"error": "not found"})
                ctrl.request_cycle()
                self._json(200, {"state": ctrl.state, "message": message})
            except Exception as exc:
                self._json(400, {"error": str(exc)})

    return Handler


def _finite(obj):
    """NaN/Infinity aren't valid JSON and would break the page's parser."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: _finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_finite(v) for v in obj]
    return obj


def settings_view(ctrl):
    """The editable settings, with the API key masked."""
    cfg = ctrl.cfg
    key = cfg["vast"]["api_key"] or ""
    p = cfg["price"]
    return {
        "mock": ctrl.mock,
        "config_path": cfg.get("_path"),
        "price": {k: p.get(k) for k in ("safetrade_market", "coingecko_id", "manual_usd", "manual_in_simulation")},
        "vast_key_set": bool(key),
        "vast_key_hint": key[-4:] if len(key) >= 8 else "",
        "vast_key_from_env": bool(os.environ.get("VAST_API_KEY")),
        "wallet": cfg["pool"].get("wallet") or "",
    }


SLUG = re.compile(r"^[A-Za-z0-9_.\-]{0,64}$")


def apply_settings(ctrl, body):
    """Validate the settings form, write them to config.yaml and reload."""
    if ctrl.mock:
        raise ValueError("演示模式（假数据）不能保存设置")
    p = body.get("price") or {}
    updates = {"price": {}, "vast": {}, "pool": {}}
    market = str(p.get("safetrade_market", "")).strip().lower()
    if not market or not SLUG.match(market):
        raise ValueError("SafeTrade 交易对只能是字母数字，例如 prlusdt")
    coin = str(p.get("coingecko_id") or "").strip().lower()
    if not SLUG.match(coin):
        raise ValueError("CoinGecko 币 id 只能是字母数字和 - ，例如 pearl")
    manual = p.get("manual_usd")
    if manual in ("", None):
        manual = None
    else:
        try:
            manual = float(manual)
        except (TypeError, ValueError):
            raise ValueError("手动价格要填数字") from None
        if not 0 < manual < 1e6:
            raise ValueError("手动价格要大于 0")
    updates["price"] = {"safetrade_market": market, "coingecko_id": coin, "manual_usd": manual,
                        "manual_in_simulation": bool(p.get("manual_in_simulation"))}
    key = str(body.get("vast_api_key") or "").strip()
    if body.get("clear_vast_key"):
        updates["vast"]["api_key"] = ""
    elif key:
        if not re.fullmatch(r"[A-Za-z0-9_\-]{16,200}", key):
            raise ValueError("Vast API key 格式不对（应该是一长串字母数字）")
        updates["vast"]["api_key"] = key
    wallet = str(body.get("wallet") or "").strip()
    if wallet and not re.fullmatch(r"[A-Za-z0-9_.:\-]{8,200}", wallet):
        raise ValueError("钱包地址格式不对")
    updates["pool"]["wallet"] = wallet
    path = config_mod.save({k: v for k, v in updates.items() if v}, ctrl.cfg.get("_path"))
    ctrl.reload(config_mod.load(path))


def history(ctrl, hours=24, max_points=300):
    now = ctrl.clock()
    snaps = ctrl.store.snapshots(now - hours * 3600)
    step = max(1, len(snaps) // max_points)
    keep = ("ts", "price", "price_live", "cheapest_breakeven", "rentable_n")
    points = [{k: s[k] for k in keep} for s in snaps[::step]]
    return {"points": points, "summary": summarize(ctrl.store, hours, now)}


def loop(ctrl, seconds, on_tick=None):
    while True:
        try:
            if on_tick:
                on_tick()
            ctrl.cycle()
            ctrl.last_error = None
        except Exception:
            ctrl.last_error = traceback.format_exc(limit=3)
            ctrl.store.log("error", "控制循环出错：" + ctrl.last_error)
            print("控制循环出错：\n" + ctrl.last_error, file=sys.stderr)
        # Sleep until the next tick, or until a button click asks for a cycle now.
        ctrl.wake.wait(seconds)
        ctrl.wake.clear()


def keep_awake():
    """Stop Windows from sleeping while this process runs (the display may still turn off).

    Windows clears the request automatically when the process exits.
    """
    if sys.platform != "win32":
        return False
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    return bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED))


def build(config_path=None, mock=False):
    """Create the controller, start its loop thread and bind the HTTP server.

    Returns (ctrl, httpd, url). The caller runs httpd.serve_forever().
    If the configured port is taken, a free one is used instead.
    """
    cfg = config_mod.load(config_path)
    if mock:
        session = FakeSession(price=2.4)
        cfg["vast"]["api_key"] = "mock"
        cfg["pool"].update(wallet="mockwallet", stats_url="https://kryptex.mock/{wallet}")
        cfg["dry_run"] = False
        cfg["loop_seconds"] = 5
        db = ":memory:"  # demo data is throwaway, and several demos can run side by side
    else:
        session = requests.Session()
        db = HERE / "pearl.sqlite3"
    ctrl = Controller(cfg, session, Store(str(db)))
    ctrl.mock = mock
    if mock:
        seed_history(ctrl, session)

    # The first cycle runs in the background so the page is reachable right away,
    # even when a data source is slow or blocked.
    threading.Thread(target=loop, args=(ctrl, cfg["loop_seconds"], session.wiggle if mock else None),
                     daemon=True).start()
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", int(cfg["listen_port"])), None)
    except OSError:
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), None)
    port = httpd.server_address[1]
    httpd.RequestHandlerClass = make_handler(ctrl, port)
    return ctrl, httpd, f"http://127.0.0.1:{port}/"


def main():
    ap = argparse.ArgumentParser(description="Pearl 租卡挖矿控制器")
    ap.add_argument("--config", help="配置文件路径（默认 pearl_dashboard/config.yaml）")
    args = ap.parse_args()
    mock = os.environ.get("MOCK") == "1"
    ctrl, httpd, url = build(args.config, mock)
    print(f"面板: {url}   模式: {'模拟数据 MOCK' if mock else '真实数据'}")
    if keep_awake():
        print("已阻止电脑休眠（关闭这个窗口即恢复）。笔记本请插电，别合盖。")
    if ctrl.live_blockers():
        print("真租未解锁：" + "；".join(ctrl.live_blockers()))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。注意：已经租的实例不会因为关掉面板而停止，"
              "它们会在最长寿命到期时自毁；想立即停止请运行 python -m pearl_dashboard.stop_all")


if __name__ == "__main__":
    main()
