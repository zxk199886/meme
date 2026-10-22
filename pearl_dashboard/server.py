"""Local web dashboard + control loop.

    python -m pearl_dashboard.server            # real data, reads config.yaml
    MOCK=1 python -m pearl_dashboard.server     # fake data, for trying the page out
"""
import argparse
import json
import os
import secrets
import sys
import threading
import time
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
            self._send(code, json.dumps(obj, ensure_ascii=False, default=str))

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
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._host_ok():
                return
            if not secrets.compare_digest(self.headers.get("X-Token", ""), TOKEN):
                return self._json(403, {"error": "bad token"})
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            try:
                if self.path == "/api/mode":
                    ctrl.set_mode(body.get("mode"))
                elif self.path == "/api/stop_all":
                    ctrl.stop_all()
                elif self.path == "/api/destroy":
                    ctrl.destroy_one(body.get("id"))
                elif self.path != "/api/refresh":
                    return self._json(404, {"error": "not found"})
                ctrl.cycle()
                self._json(200, ctrl.state)
            except Exception as exc:
                self._json(400, {"error": str(exc)})

    return Handler


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
        time.sleep(seconds)


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
        db = HERE / "pearl-mock.sqlite3"
        db.unlink(missing_ok=True)
    else:
        session = requests.Session()
        db = HERE / "pearl.sqlite3"
    ctrl = Controller(cfg, session, Store(str(db)))
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
