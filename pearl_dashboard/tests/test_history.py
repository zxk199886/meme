import unittest

from pearl_dashboard import config as config_mod
from pearl_dashboard.check import run as run_check
from pearl_dashboard.controller import Controller
from pearl_dashboard.mock import FakeSession, FakeResponse
from pearl_dashboard.report import format_report, summarize
from pearl_dashboard.store import Store
from pearl_dashboard.strategy import rent_eligible

from .test_controller_mock import Clock

NOW = 1_800_000_000.0


def make(api_key="", price=2.5):
    cfg = config_mod.load("/nonexistent.yaml")
    cfg["vast"]["api_key"] = api_key
    clock = Clock()
    session = FakeSession(price=price, clock=clock)
    ctrl = Controller(cfg, session, Store(":memory:"), clock=clock)
    return cfg, clock, session, ctrl


class KeylessTest(unittest.TestCase):
    def test_simulates_without_api_key(self):
        _, clock, session, ctrl = make(api_key="")
        for _ in range(3):
            ctrl.cycle()
            clock.t += 60
        self.assertEqual(len(ctrl.sim_instances), 2)
        urls = [u for _, u in session.calls]
        self.assertFalse(any("/instances/" in u or "/users/" in u or "/asks/" in u for u in urls))
        self.assertIn("没有填 Vast API key", ctrl.live_blockers())

    def test_keyless_rejected_has_clear_message(self):
        _, _, session, ctrl = make(api_key="")
        session._route = lambda *a, **k: (FakeResponse({}, 401) if "bundles" in a[1]
                                          else FakeSession._route(session, *a, **k))
        ctrl.cycle()
        self.assertIn("API key", ctrl.state["errors"]["Vast 报价"])


class RentEligibleTest(unittest.TestCase):
    def test_conditions(self):
        lim = config_mod.load("/nonexistent.yaml")["limits"]
        good = {"rentable": True, "hashrate_th": 340, "margin": 0.3, "usd_per_hr_per_gpu": 0.38, "reliability": 0.99}
        self.assertTrue(rent_eligible(good, lim))
        for change in ({"rentable": False}, {"hashrate_th": 0}, {"margin": None}, {"margin": 0.1},
                       {"usd_per_hr_per_gpu": 0.5}, {"reliability": 0.9}):
            self.assertFalse(rent_eligible({**good, **change}, lim), change)


class ReportTest(unittest.TestCase):
    def test_one_hour_of_snapshots(self):
        _, clock, session, ctrl = make(price=2.5)
        start = clock.t
        for _ in range(61):
            ctrl.cycle()
            clock.t += 60
        s = summarize(ctrl.store, hours=24, now=clock.t)
        self.assertEqual(s["samples"], 61)
        self.assertAlmostEqual(s["observed_hours"], 1.0, places=2)
        self.assertAlmostEqual(s["rentable_hours"], 1.0, places=2)
        self.assertEqual(s["sim_rentals"], 2)
        # $0.38 card for 60 min, $0.42 card rented one cycle later (max_new_per_cycle=1) for 59 min
        self.assertAlmostEqual(s["sim_cost"], 0.38 + 0.42 * 59 / 60, places=3)
        self.assertGreater(s["sim_pnl"], 0)
        self.assertEqual(s["price_down_share"], 0)
        text = format_report(s)
        self.assertIn("模拟盈亏", text)
        self.assertGreater(clock.t, start)

    def test_sleep_gap_not_counted(self):
        _, clock, _, ctrl = make()
        ctrl.cycle()
        clock.t += 3 * 3600  # PC asleep
        ctrl.cycle()
        s = summarize(ctrl.store, hours=24, now=clock.t)
        self.assertLess(s["observed_hours"], 0.1)

    def test_not_enough_data(self):
        _, clock, _, ctrl = make()
        self.assertIn("还没有足够的数据", format_report(summarize(ctrl.store, now=clock.t)))


class CheckTest(unittest.TestCase):
    def test_all_ok(self):
        cfg = config_mod.load("/nonexistent.yaml")
        out = []
        self.assertTrue(run_check(cfg, FakeSession(), out.append))
        self.assertTrue(any(line.startswith("✅ SafeTrade") for line in out))
        self.assertIn("可以开始模拟", out[-1])

    def test_price_down(self):
        cfg = config_mod.load("/nonexistent.yaml")
        s = FakeSession()
        s.fail.add("safe.trade")
        out = []
        self.assertFalse(run_check(cfg, s, out.append))
        self.assertTrue(any(line.startswith("❌ SafeTrade") for line in out))
        self.assertIn("币价", out[-1])

    def test_shows_http_body_on_bad_json(self):
        cfg = config_mod.load("/nonexistent.yaml")
        s = FakeSession()
        orig = s._route
        s._route = lambda m, url, *a, **k: ({"error": "market not found"} if "safe.trade" in url else orig(m, url, *a, **k))
        out = []
        run_check(cfg, s, out.append)
        self.assertTrue(any("market not found" in line for line in out))


if __name__ == "__main__":
    unittest.main()
