import json
import threading
import time
import unittest
import urllib.request

from pearl_dashboard import config as config_mod
from pearl_dashboard.controller import Controller
from pearl_dashboard.mock import FakeSession
from pearl_dashboard.server import TOKEN, build, loop
from pearl_dashboard.store import Store

from .test_controller_mock import Clock
from .test_strategy import NOW, inst, offer


class IdleReasonTest(unittest.TestCase):
    def setUp(self):
        self.cfg = config_mod.load("/nonexistent.yaml")

    def decide(self, **kw):
        from pearl_dashboard.strategy import decide
        args = dict(now=NOW, cfg=self.cfg, mode="simulate", price={"price": 2.0, "live": True},
                    last_live_price_ts=NOW, prl_per_th_day=5.75 / 370, fee=0.05,
                    hashrates={"RTX 5090": 340}, offers=[offer(1, 0.40)], instances=[], balance=None,
                    pool_workers=None, counters={})
        args.update(kw)
        return decide(**args)

    def test_margin_below_threshold_names_numbers(self):
        r = self.decide()["idle_reason"]
        self.assertIn("$0.400/h", r)
        self.assertIn("低于门槛 20%", r)
        self.assertIn("保本价", r)

    def test_other_reasons(self):
        self.assertEqual(self.decide(mode="halted")["idle_reason"], "已暂停租新卡")
        self.assertIn("实时币价", self.decide(price={"price": 2.0, "live": False})["idle_reason"])
        self.assertIn("报价", self.decide(offers=[])["idle_reason"])
        self.assertIn("余额", self.decide(mode="live", balance=None)["idle_reason"])
        self.assertIn("已到上限", self.decide(price={"price": 3.0, "live": True},
                                           instances=[inst("a"), inst("b")])["idle_reason"])
        self.assertIn("可靠性", self.decide(price={"price": 3.0, "live": True},
                                         offers=[offer(1, 0.30, rel=0.5)])["idle_reason"])

    def test_none_when_renting(self):
        d = self.decide(price={"price": 3.0, "live": True})
        self.assertTrue(d["rent"])
        self.assertIsNone(d["idle_reason"])


class SlowSession(FakeSession):
    """SafeTrade blocks until released, like a slow or unreachable network."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.gate = threading.Event()
        self.entered = threading.Event()

    def _route(self, method, url, params=None, json=None):
        if "safe.trade" in url:
            self.entered.set()
            self.gate.wait(5)
        return super()._route(method, url, params, json)


class ResponsivenessTest(unittest.TestCase):
    def test_mode_change_does_not_wait_for_slow_cycle(self):
        cfg = config_mod.load("/nonexistent.yaml")
        clock = Clock()
        session = SlowSession(price=3.0, clock=clock)
        ctrl = Controller(cfg, session, Store(":memory:"), clock=clock)
        t = threading.Thread(target=ctrl.cycle)
        t.start()
        self.assertTrue(session.entered.wait(2))
        started = time.monotonic()
        msg = ctrl.set_mode("halted")
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertIn("暂停", msg)
        session.gate.set()
        t.join(5)
        # the in-flight cycle saw the new mode when it acted: nothing rented
        self.assertEqual(ctrl.sim_instances, {})
        self.assertIn("已暂停", ctrl.state["activity"])

    def test_already_in_mode_message(self):
        ctrl = Controller(config_mod.load("/nonexistent.yaml"), FakeSession(), Store(":memory:"), clock=Clock())
        self.assertEqual(ctrl.set_mode("simulate"), "已经在模拟模式了")

    def test_request_cycle_wakes_loop(self):
        ctrl = Controller(config_mod.load("/nonexistent.yaml"), FakeSession(), Store(":memory:"), clock=Clock())
        calls = []
        ctrl.cycle = lambda: calls.append(time.monotonic())
        threading.Thread(target=loop, args=(ctrl, 3600), daemon=True).start()
        deadline = time.monotonic() + 2
        while not calls and time.monotonic() < deadline:
            time.sleep(0.01)
        ctrl.request_cycle()
        deadline = time.monotonic() + 2
        while len(calls) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(len(calls), 2)  # second cycle came from the wake, not the 1h tick


class ServerResponseTest(unittest.TestCase):
    def test_post_mode_returns_immediately_with_message(self):
        ctrl, httpd, url = build(mock=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        gate = threading.Event()
        real_fetch = ctrl._fetch

        def slow_fetch():
            gate.wait(5)
            return real_fetch()
        ctrl._fetch = slow_fetch
        threading.Thread(target=ctrl.cycle, daemon=True).start()  # a slow cycle in flight
        time.sleep(0.1)

        req = urllib.request.Request(url + "api/mode", data=json.dumps({"mode": "halted"}).encode(), method="POST",
                                     headers={"X-Token": TOKEN, "Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        started = time.monotonic()
        with opener.open(req, timeout=5) as r:
            data = json.loads(r.read())
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(data["state"]["mode"], "halted")
        self.assertIn("暂停", data["message"])
        gate.set()


if __name__ == "__main__":
    unittest.main()
