import tempfile
import unittest
from pathlib import Path

from pearl_dashboard import config as config_mod
from pearl_dashboard.controller import Controller
from pearl_dashboard.mock import FakeSession
from pearl_dashboard.store import Store


class Clock:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self):
        return self.t


class ControllerTest(unittest.TestCase):
    def make(self, dry_run=True, price=2.5):
        cfg = config_mod.load("/nonexistent.yaml")
        cfg["vast"]["api_key"] = "k"
        cfg["pool"]["wallet"] = "WALLET"
        cfg["dry_run"] = dry_run
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self.session = FakeSession(price=price, clock=self.clock)
        store = Store(str(Path(self.tmp.name) / "t.sqlite3"))
        return Controller(cfg, self.session, store, clock=self.clock)

    def tearDown(self):
        self.tmp.cleanup()

    def writes(self):
        return [c for c in self.session.calls if c[0] in ("PUT", "DELETE")]

    def test_simulate_never_writes_to_vast(self):
        c = self.make()
        for _ in range(5):
            c.cycle()
            self.clock.t += 60
        self.assertEqual(self.writes(), [])
        self.assertEqual(len(c.sim_instances), 2)  # max_gpus
        offer_ids = [i["offer_id"] for i in c.sim_instances.values()]
        self.assertEqual(len(set(offer_ids)), 2)
        self.assertGreater(c.state["totals"]["sim"]["cost"], 0)

    def test_going_live_drops_simulated(self):
        c = self.make(dry_run=False)
        c.cycle()
        self.assertTrue(c.sim_instances)
        c.set_mode("live")
        self.assertEqual(c.sim_instances, {})

    def test_live_requires_config_unlock(self):
        c = self.make(dry_run=True)
        with self.assertRaises(ValueError):
            c.set_mode("live")

    def test_live_rents_with_env_and_onstart(self):
        c = self.make(dry_run=False)
        c.set_mode("live")
        c.cycle()
        puts = [u for m, u in self.writes() if m == "PUT"]
        self.assertEqual(len(puts), 1)
        inst = next(iter(self.session.instances.values()))
        self.assertTrue(inst["label"].startswith("pearl-"))
        self.assertEqual(inst["_env"]["PRL_WALLET"], "WALLET")
        self.assertEqual(inst["_env"]["PRL_POOL"], "prl.kryptex.network:7048")
        self.assertEqual(c.state["instances"][0]["simulated"], False)

    def test_live_price_crash_releases(self):
        c = self.make(dry_run=False)
        c.set_mode("live")
        c.cycle()
        self.assertEqual(len(self.session.instances), 1)
        self.session.price = 0.8
        for _ in range(5):
            self.clock.t += 60
            c.cycle()
        self.assertEqual(len(self.session.instances), 0)
        self.assertIn("亏损", c.store.events()[0]["message"])

    def test_ignores_foreign_instances(self):
        c = self.make(dry_run=False)
        self.session.instances[1] = {"id": 1, "label": "my-training-job", "gpu_name": "RTX 5090", "num_gpus": 1,
                                     "dph_total": 0.5, "actual_status": "running", "gpu_util": 0,
                                     "start_date": self.clock.t - 99999, "_offer": 99}
        c.set_mode("live")
        c.stop_all()
        self.assertIn(1, self.session.instances)

    def test_stop_all(self):
        c = self.make(dry_run=False)
        c.set_mode("live")
        c.cycle()
        c.stop_all()
        self.assertEqual(self.session.instances, {})
        self.assertEqual(c.mode, "halted")
        self.clock.t += 60
        c.cycle()
        self.assertEqual(self.session.instances, {})

    def test_vanished_instance_closed(self):
        c = self.make(dry_run=False)
        c.set_mode("live")
        c.cycle()
        iid = next(iter(self.session.instances))
        self.session.instances.clear()  # self-destroyed on the host
        c.set_mode("halted")
        self.clock.t += 60
        c.cycle()
        r = next(r for r in c.store.rentals() if r["id"] == str(iid))
        self.assertIsNotNone(r["ended"])

    def test_vast_outage_blocks_live_renting(self):
        c = self.make(dry_run=False)
        c.set_mode("live")
        self.session.fail.add("vast.ai")
        c.cycle()
        self.assertEqual(self.writes(), [])
        self.assertTrue(any("Vast" in k for k in c.state["errors"]))


if __name__ == "__main__":
    unittest.main()
