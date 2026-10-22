import json
import math
import tempfile
import unittest
from pathlib import Path

import yaml

from pearl_dashboard import config as config_mod
from pearl_dashboard.controller import Controller
from pearl_dashboard.mock import FakeSession
from pearl_dashboard.server import _finite, apply_settings, settings_view
from pearl_dashboard.sources.price import _safetrade, get_prl_price
from pearl_dashboard.sources.vast import normalize_offer
from pearl_dashboard.store import Store

from .test_controller_mock import Clock

KEY = "a" * 64


def form(**over):
    body = {"price": {"safetrade_market": "prlusdt", "coingecko_id": "", "manual_usd": "",
                      "manual_in_simulation": False},
            "vast_api_key": "", "clear_vast_key": False, "wallet": ""}
    body.update(over)
    return body


class SettingsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "config.yaml"
        self.path.write_text("limits:\n  max_gpus: 1\n", encoding="utf-8")  # an existing user setting
        cfg = config_mod.load(self.path)
        self.ctrl = Controller(cfg, FakeSession(), Store(":memory:"), clock=Clock())

    def saved(self):
        return yaml.safe_load(self.path.read_text(encoding="utf-8"))

    def test_saves_price_and_key_and_reloads(self):
        apply_settings(self.ctrl, form(price={"safetrade_market": "PRL_USDT", "coingecko_id": "pearl",
                                              "manual_usd": "2.1", "manual_in_simulation": True},
                                       vast_api_key=KEY, wallet="prl1qxyz0123456789"))
        s = self.saved()
        self.assertEqual(s["limits"]["max_gpus"], 1)  # untouched setting kept
        self.assertEqual(s["price"], {"safetrade_market": "prl_usdt", "coingecko_id": "pearl",
                                      "manual_usd": 2.1, "manual_in_simulation": True})
        self.assertEqual(s["vast"]["api_key"], KEY)
        self.assertTrue(self.ctrl.vast.has_key)
        self.assertEqual(self.ctrl.cfg["price"]["manual_usd"], 2.1)
        view = settings_view(self.ctrl)
        self.assertTrue(view["vast_key_set"])
        self.assertEqual(view["vast_key_hint"], "aaaa")
        self.assertNotIn(KEY, json.dumps(view))  # never sent back to the page

    def test_empty_key_keeps_existing_and_clear_removes(self):
        apply_settings(self.ctrl, form(vast_api_key=KEY))
        apply_settings(self.ctrl, form())
        self.assertEqual(self.saved()["vast"]["api_key"], KEY)
        apply_settings(self.ctrl, form(clear_vast_key=True))
        self.assertEqual(self.saved()["vast"]["api_key"], "")
        self.assertFalse(self.ctrl.vast.has_key)

    def test_rejects_bad_input(self):
        for body in (form(price={"safetrade_market": "prl usdt;rm"}), form(price={"safetrade_market": ""}),
                     form(price={"safetrade_market": "prlusdt", "manual_usd": "abc"}),
                     form(price={"safetrade_market": "prlusdt", "manual_usd": "-1"}),
                     form(vast_api_key="short"), form(wallet="bad wallet!")):
            with self.assertRaises(ValueError, msg=body):
                apply_settings(self.ctrl, body)
        self.assertNotIn("price", self.saved())

    def test_mock_mode_cannot_save(self):
        self.ctrl.mock = True
        with self.assertRaises(ValueError):
            apply_settings(self.ctrl, form())


class ManualPriceSimulationTest(unittest.TestCase):
    def make(self, manual_in_simulation):
        cfg = config_mod.load("/nonexistent.yaml")
        cfg["price"].update(manual_usd=2.5, manual_in_simulation=manual_in_simulation)
        session = FakeSession()
        session.fail.add("safe.trade")
        clock = Clock()
        session.clock = clock
        return Controller(cfg, session, Store(":memory:"), clock=clock)

    def test_manual_price_drives_simulation_when_enabled(self):
        ctrl = self.make(True)
        ctrl.cycle()
        self.assertEqual(ctrl.state["price"]["source"], "手动价格（仅模拟）")
        self.assertTrue(ctrl.sim_instances)

    def test_manual_price_ignored_by_default(self):
        ctrl = self.make(False)
        ctrl.cycle()
        self.assertFalse(ctrl.sim_instances)

    def test_never_used_for_live(self):
        ctrl = self.make(True)
        ctrl.cfg["dry_run"] = False
        ctrl.cfg["vast"]["api_key"] = KEY
        ctrl.cfg["pool"]["wallet"] = "w" * 10
        ctrl.reload(ctrl.cfg)
        ctrl.set_mode("live")
        ctrl.cycle()
        self.assertFalse(ctrl.state["price"]["live"])
        self.assertFalse([c for c in ctrl.session.calls if c[0] == "PUT"])


class SafeTradeParsingTest(unittest.TestCase):
    class S:
        def __init__(self, routes):
            self.routes = routes

        def get(self, url, **kw):
            data = self.routes[url]

            class R:
                def json(self_inner):
                    return data
            return R()

    PCFG = {"safetrade_market": "prlusdt",
            "safetrade_url": "https://safe.trade/api/v2/peatio/public/markets/{market}/tickers"}
    ONE = "https://safe.trade/api/v2/peatio/public/markets/prlusdt/tickers"
    ALL = "https://safe.trade/api/v2/peatio/public/markets/tickers"

    def test_variants(self):
        for data in ({"ticker": {"last": "1.9", "vol": "5"}}, {"last": "1.9"}, {"ticker": {"last_price": 1.9}}):
            self.assertEqual(_safetrade(self.S({self.ONE: data}), self.PCFG)["price"], 1.9)

    def test_finds_market_in_all_tickers(self):
        s = self.S({self.ONE: {"errors": ["record.not_found"]},
                    self.ALL: {"btcusdt": {"ticker": {"last": "60000"}}, "prl_usdt": {"ticker": {"last": "2.05"}}}})
        self.assertEqual(_safetrade(s, self.PCFG)["price"], 2.05)

    def test_error_shows_response(self):
        s = self.S({self.ONE: {"errors": ["market.not_found"]}, self.ALL: {}})
        with self.assertRaises(ValueError) as cm:
            _safetrade(s, self.PCFG)
        self.assertIn("market.not_found", str(cm.exception))

    def test_reported_through_get_prl_price(self):
        cfg = config_mod.load("/nonexistent.yaml")
        s = self.S({self.ONE: {"errors": ["x"]}, self.ALL: {}})
        p = get_prl_price(s, cfg)
        self.assertIn("交易对 prlusdt", p["errors"]["SafeTrade"])


class NanTest(unittest.TestCase):
    def test_offer_nan_becomes_none(self):
        o = normalize_offer({"id": 1, "gpu_name": "RTX 5090", "num_gpus": 1, "dph_total": 0.4,
                             "reliability2": float("nan")})
        self.assertIsNone(o["reliability"])

    def test_finite_json(self):
        out = json.dumps(_finite({"a": [float("nan"), 1.0, {"b": math.inf}]}))
        self.assertEqual(json.loads(out), {"a": [None, 1.0, {"b": None}]})


if __name__ == "__main__":
    unittest.main()
