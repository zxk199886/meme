import unittest

from pearl_dashboard import config as config_mod
from pearl_dashboard.mock import FakeSession
from pearl_dashboard.sources import kryptex, runpod
from pearl_dashboard.sources.price import get_prl_price
from pearl_dashboard.sources.vast import VastClient


class PriceTest(unittest.TestCase):
    def setUp(self):
        self.cfg = config_mod.load("/nonexistent.yaml")
        self.s = FakeSession(price=1.85)

    def test_safetrade(self):
        p = get_prl_price(self.s, self.cfg)
        self.assertEqual((p["price"], p["source"], p["live"]), (1.85, "SafeTrade", True))

    def test_fallback_to_manual_is_not_live(self):
        self.s.fail.add("safe.trade")
        self.cfg["price"]["manual_usd"] = 1.5
        p = get_prl_price(self.s, self.cfg)
        self.assertEqual((p["price"], p["live"]), (1.5, False))
        self.assertIn("SafeTrade", p["errors"])

    def test_total_outage(self):
        self.s.fail.add("safe.trade")
        p = get_prl_price(self.s, self.cfg)
        self.assertIsNone(p["price"])


class VastTest(unittest.TestCase):
    def test_offers_and_instances(self):
        s = FakeSession()
        v = VastClient(s, "k")
        offers = v.search_offers(["RTX 5090"], 0.97, 10)
        self.assertEqual(offers[0]["platform"], "Vast.ai")
        two = next(o for o in offers if o["num_gpus"] == 2)
        self.assertAlmostEqual(two["usd_per_hr_per_gpu"], 0.45)
        iid = v.create_instance(1, "pearl-x", {"A": "1"}, "img", 10)
        self.assertEqual([i["id"] for i in v.list_instances()], [iid])
        put = s.instances[iid]
        self.assertEqual(put["_env"], {"A": "1"})
        v.destroy_instance(iid)
        self.assertEqual(v.list_instances(), [])
        self.assertEqual(v.get_balance(), 50.0)


class OtherSourcesTest(unittest.TestCase):
    def test_runpod_filters_wanted_gpus(self):
        offers = runpod.fetch_offers(FakeSession(), "k", ["RTX 5090"])
        self.assertEqual({o["platform"] for o in offers}, {"RunPod Community", "RunPod Secure", "RunPod Spot"})
        self.assertFalse(any(o["rentable"] for o in offers))

    def test_kryptex_parse_variants(self):
        a = kryptex.parse({"data": {"balance": "1.5", "workers": [{"worker": "vast1", "hashrate": 3.4e14}]}})
        self.assertAlmostEqual(a["workers_th"]["vast1"], 340)
        self.assertEqual(a["balance_prl"], 1.5)
        b = kryptex.parse({"unpaid": 2, "total_paid": 3, "rigs": [{"name": "vast2", "hashrate_current": 330}]})
        self.assertEqual((b["workers_th"], b["balance_prl"], b["paid_prl"]), ({"vast2": 330}, 2, 3))


if __name__ == "__main__":
    unittest.main()
