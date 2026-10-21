"""Local web dashboard + control loop.

    python -m pearl_dashboard.server            # real data, reads config.yaml
    MOCK=1 python -m pearl_dashboard.server     # fake data, for trying the page out
"""
import argparse
import json
import os
import secrets
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

from . import config as config_mod
from .controller import Controller
from .mock import FakeSession
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
                self._json(200, ctrl.state)
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


def loop(ctrl, seconds, on_tick=None):
    while True:
        try:
            if on_tick:
                on_tick()
            ctrl.cycle()
        except Exception:
            ctrl.store.log("error", "控制循环出错：" + traceback.format_exc(limit=3))
        time.sleep(seconds)


def main():
    ap = argparse.ArgumentParser(description="Pearl 租卡挖矿控制器")
    ap.add_argument("--config", help="配置文件路径（默认 pearl_dashboard/config.yaml）")
    args = ap.parse_args()
    cfg = config_mod.load(args.config)
    mock = os.environ.get("MOCK") == "1"
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
    ctrl.cycle()

    threading.Thread(target=loop, args=(ctrl, cfg["loop_seconds"], session.wiggle if mock else None),
                     daemon=True).start()
    port = int(cfg["listen_port"])
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(ctrl, port))
    print(f"面板: http://127.0.0.1:{port}   模式: {'模拟数据 MOCK' if mock else '真实数据'}")
    if ctrl.live_blockers():
        print("真租未解锁：" + "；".join(ctrl.live_blockers()))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。注意：已经租的实例不会因为关掉面板而停止，"
              "它们会在最长寿命到期时自毁；想立即停止请运行 python -m pearl_dashboard.stop_all")


if __name__ == "__main__":
    main()
