import unittest

from pearl_dashboard import config as config_mod
from pearl_dashboard.sources.vast import normalize_offer
from pearl_dashboard.strategy import decide

NOW = 1_800_000_000.0


def offer(i, dph, num=1, rel=0.99, gpu="RTX 5090"):
    return normalize_offer({"id": i, "gpu_name": gpu, "num_gpus": num, "dph_total": dph, "reliability2": rel})


def inst(i, dph=0.38, age_min=60, status="running", util=99.0, simulated=False, num=1):
    return {"id": i, "label": f"pearl-{i}", "gpu": "RTX 5090", "num_gpus": num, "usd_per_hr": dph,
            "status": status, "gpu_util": util, "start_date": NOW - age_min * 60, "simulated": simulated}


class StrategyTest(unittest.TestCase):
    def setUp(self):
        self.cfg = config_mod.load("/nonexistent.yaml")

    def run_decide(self, **kw):
        args = dict(now=NOW, cfg=self.cfg, mode="live", price={"price": 2.0, "live": True},
                    last_live_price_ts=NOW, prl_per_th_day=5.75 / 370, fee=0.05,
                    hashrates={"RTX 5090": 340}, offers=[], instances=[], balance=50.0,
                    pool_workers=None, counters={})
        args.update(kw)
        return decide(**args)

    def test_rents_best_profitable_offer(self):
        d = self.run_decide(offers=[offer(1, 0.42), offer(2, 0.30), offer(3, 0.60)])
        self.assertEqual([o["id"] for o, _ in d["rent"]], [2])

    def test_skips_below_min_margin_and_low_reliability(self):
        d = self.run_decide(offers=[offer(1, 0.40), offer(2, 0.20, rel=0.9)])
        # $0.40/h: margin ~ 4.6% < 20%; $0.20/h is great but unreliable
        self.assertEqual(d["rent"], [])

    def test_respects_gpu_cap(self):
        d = self.run_decide(offers=[offer(1, 0.30)], instances=[inst("a"), inst("b")])
        self.assertEqual(d["rent"], [])

    def test_respects_hourly_spend_cap(self):
        self.cfg["limits"]["max_hourly_spend"] = 0.5
        d = self.run_decide(offers=[offer(1, 0.30)], instances=[inst("a", dph=0.3)])
        self.assertEqual(d["rent"], [])

    def test_multi_gpu_offer_counts_all_gpus(self):
        d = self.run_decide(offers=[offer(1, 0.56, num=2)], instances=[inst("a", dph=0.3)])
        self.assertEqual(d["rent"], [])

    def test_one_new_per_cycle(self):
        d = self.run_decide(offers=[offer(1, 0.25), offer(2, 0.26)])
        self.assertEqual(len(d["rent"]), 1)

    def test_no_rent_when_halted_or_price_not_live(self):
        self.assertEqual(self.run_decide(mode="halted", offers=[offer(1, 0.25)])["rent"], [])
        d = self.run_decide(price={"price": 2.0, "live": False}, offers=[offer(1, 0.25)])
        self.assertEqual(d["rent"], [])

    def test_no_live_rent_without_balance(self):
        self.assertEqual(self.run_decide(balance=None, offers=[offer(1, 0.25)])["rent"], [])
        self.assertEqual(len(self.run_decide(mode="simulate", balance=None, offers=[offer(1, 0.25)])["rent"]), 1)

    def test_destroys_after_consecutive_losses(self):
        counters = {}
        for n in range(5):
            d = self.run_decide(price={"price": 1.0, "live": True}, instances=[inst("a")], counters=counters)
            counters = d["counters"]
            self.assertEqual(bool(d["destroy"]), n == 4, n)

    def test_loss_counter_resets_on_recovery(self):
        d = self.run_decide(price={"price": 1.0, "live": True}, instances=[inst("a")], counters={"a": {"bad": 3, "unhealthy": 0}})
        self.assertEqual(d["counters"]["a"]["bad"], 4)
        d = self.run_decide(instances=[inst("a")], counters=d["counters"])
        self.assertEqual(d["counters"]["a"]["bad"], 0)

    def test_unhealthy_after_warmup(self):
        counters = {"a": {"bad": 0, "unhealthy": 4}}
        d = self.run_decide(instances=[inst("a", util=3)], counters=counters)
        self.assertEqual(len(d["destroy"]), 1)
        self.assertIn("GPU", d["destroy"][0][1])
        # during warmup nothing is counted
        d = self.run_decide(instances=[inst("a", util=3, age_min=5)], counters=counters)
        self.assertEqual(d["destroy"], [])

    def test_zero_pool_hashrate_counts_as_unhealthy(self):
        d = self.run_decide(instances=[inst("a")], pool_workers={"vastb": 300})
        self.assertEqual(d["counters"]["a"]["unhealthy"], 1)
        d = self.run_decide(instances=[inst("a")], pool_workers={"vasta": 300})
        self.assertEqual(d["counters"]["a"]["unhealthy"], 0)

    def test_stale_price_destroys_everything(self):
        d = self.run_decide(price={"price": None, "live": False}, last_live_price_ts=NOW - 31 * 60,
                            instances=[inst("a"), inst("b", simulated=True)])
        self.assertEqual(len(d["destroy"]), 2)
        d = self.run_decide(price={"price": None, "live": False}, last_live_price_ts=NOW - 10 * 60,
                            instances=[inst("a")])
        self.assertEqual(d["destroy"], [])

    def test_low_balance_destroys_and_blocks(self):
        d = self.run_decide(balance=3.0, instances=[inst("a")], offers=[offer(1, 0.25)])
        self.assertEqual(len(d["destroy"]), 1)
        self.assertEqual(d["rent"], [])

    def test_expiring_instance_allows_replacement(self):
        lifetime = self.cfg["limits"]["max_lifetime_hours"] * 60
        d = self.run_decide(offers=[offer(1, 0.25)], instances=[inst("a"), inst("b", age_min=lifetime - 10)])
        self.assertEqual(len(d["rent"]), 1)

    def test_overdue_instance_destroyed(self):
        lifetime = self.cfg["limits"]["max_lifetime_hours"] * 60
        d = self.run_decide(instances=[inst("a", age_min=lifetime + 15)])
        self.assertEqual(len(d["destroy"]), 1)


if __name__ == "__main__":
    unittest.main()
