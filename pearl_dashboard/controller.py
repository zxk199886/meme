"""One control cycle: collect data → decide → act → publish state for the dashboard."""
import itertools
import statistics
import threading
import time

from . import config as config_mod
from .calc import evaluate
from .sources import kryptex, runpod
from .sources.price import get_prl_price
from .sources.vast import VastClient
from .sources.yield_ import get_prl_per_th_day
from .strategy import decide, instance_age_min, rent_eligible


class Controller:
    def __init__(self, cfg, session, store, clock=time.time):
        self.cfg = cfg
        self.session = session
        self.store = store
        self.clock = clock
        self.fee = config_mod.total_fee(cfg)
        self.vast = VastClient(session, cfg["vast"]["api_key"], cfg["vast"]["base_url"])
        self.mode = "simulate"
        self.sim_instances = {}
        self._sim_ids = itertools.count(1)
        self.counters = {}
        self.last_live_price_ts = None
        self.started = clock()  # price-staleness grace period starts here
        self.state = {}
        self.last_error = None  # traceback of the last failed cycle, shown on the page
        self.lock = threading.RLock()
        # Simulated rentals don't survive a restart.
        for r in store.open_rentals():
            if r["simulated"]:
                store.close_rental(r["id"], "控制器重启")

    # ------------------------------------------------------------------ mode
    def live_blockers(self):
        problems = []
        if self.cfg.get("dry_run", True):
            problems.append("config.yaml 里 dry_run 还是 true")
        if not self.vast.has_key:
            problems.append("没有填 Vast API key")
        if not self.cfg["pool"].get("wallet"):
            problems.append("没有填钱包地址 pool.wallet")
        return problems

    def set_mode(self, mode):
        with self.lock:
            if mode == "live":
                blockers = self.live_blockers()
                if blockers:
                    raise ValueError("；".join(blockers))
            self.mode = mode
            if mode == "live":
                for inst in list(self.sim_instances.values()):
                    self.destroy(inst, "切换到真租")
            self.store.log("mode", {"live": "开始真租", "simulate": "切换到模拟", "halted": "已暂停"}[mode])

    # --------------------------------------------------------------- actions
    def _managed(self, instances):
        prefix = self.cfg["instance"]["label_prefix"]
        return [i for i in instances if i["label"].startswith(prefix)]

    def destroy(self, inst, reason):
        if inst.get("simulated"):
            self.sim_instances.pop(inst["id"], None)
        else:
            self.vast.destroy_instance(inst["id"])
        self.counters.pop(inst["id"], None)
        self.store.close_rental(inst["id"], reason, self.clock())
        self.store.log("destroy", f"退租 {inst['id']} {inst['gpu']} ${inst['usd_per_hr']:.3f}/h：{reason}",
                       inst.get("simulated", False))

    def _rent(self, offer, reason, now):
        icfg = self.cfg["instance"]
        label = f"{icfg['label_prefix']}{offer['gpu'].replace(' ', '')}-{int(now)}"
        if self.mode == "simulate":
            iid = f"sim-{next(self._sim_ids)}"
            inst = {"id": iid, "label": label, "gpu": offer["gpu"], "num_gpus": offer["num_gpus"],
                    "usd_per_hr": offer["usd_per_hr"], "status": "running", "gpu_util": None,
                    "start_date": now, "simulated": True, "offer_id": offer["id"]}
            self.sim_instances[iid] = inst
        else:
            env = {
                "PRL_WALLET": self.cfg["pool"]["wallet"],
                "PRL_POOL": self.cfg["pool"]["stratum"],
                "MINER_URL": icfg["miner_url"],
                "MINER_SHA256": icfg.get("miner_sha256") or "",
                "MINER_EXTRA": icfg.get("extra_args") or "",
                "MAX_LIFETIME_HOURS": str(self.cfg["limits"]["max_lifetime_hours"]),
                "VAST_BASE": self.cfg["vast"]["base_url"],
            }
            iid = self.vast.create_instance(offer["id"], label, env, icfg["image"], icfg["disk_gb"])
            inst = {"id": iid, "label": label, "gpu": offer["gpu"], "num_gpus": offer["num_gpus"],
                    "usd_per_hr": offer["usd_per_hr"], "status": "loading", "gpu_util": None,
                    "start_date": now, "simulated": False}
        self.store.open_rental(inst, self.mode == "simulate")
        self.store.log("rent", f"租用 {iid} {offer['gpu']}×{offer['num_gpus']} ${offer['usd_per_hr']:.3f}/h：{reason}",
                       self.mode == "simulate")
        return inst

    def stop_all(self):
        with self.lock:
            self.mode = "halted"
            self.store.log("mode", "紧急停止：退掉所有实例并暂停")
            for inst in list(self.sim_instances.values()):
                self.destroy(inst, "紧急停止")
            if self.vast.has_key:
                for inst in self._managed(self.vast.list_instances()):
                    self.destroy(inst, "紧急停止")

    def destroy_one(self, instance_id):
        with self.lock:
            if instance_id in self.sim_instances:
                return self.destroy(self.sim_instances[instance_id], "手动退租")
            for inst in self._managed(self.vast.list_instances() if self.vast.has_key else []):
                if str(inst["id"]) == str(instance_id):
                    return self.destroy(inst, "手动退租")
            raise ValueError("找不到这个实例")

    # ----------------------------------------------------------------- cycle
    def _measured_hashrates(self, real, pool_workers, now):
        cfg_rates = {g: float(h or 0) for g, h in self.cfg["gpus"].items()}
        per_gpu = {}
        if pool_workers:
            for inst in real:
                th = pool_workers.get(f"vast{inst['id']}")
                if th and instance_age_min(inst, now) > self.cfg["limits"]["warmup_minutes"]:
                    per_gpu.setdefault(inst["gpu"], []).append(th / inst["num_gpus"])
        measured = {g: statistics.median(v) for g, v in per_gpu.items()}
        used = {g: measured.get(g, h) for g, h in cfg_rates.items()}
        return used, {g: {"config": cfg_rates.get(g), "measured": measured.get(g)} for g in cfg_rates}

    def cycle(self):
        with self.lock:
            return self._cycle()

    def _cycle(self):
        cfg, now, errors = self.cfg, self.clock(), {}
        lim = cfg["limits"]

        price = get_prl_price(self.session, cfg)
        errors.update({f"币价 {k}": v for k, v in price["errors"].items()})
        if price["live"]:
            self.last_live_price_ts = now
        yld = get_prl_per_th_day(self.session, cfg)
        if yld["error"]:
            errors["产出"] = yld["error"]

        gpu_names = [g for g, h in cfg["gpus"].items() if h]
        offers, real, balance = [], None, None
        calls = [("Vast 报价", lambda: self.vast.search_offers(gpu_names, lim["min_reliability"],
                                                              cfg["instance"]["disk_gb"]))]
        if self.vast.has_key:
            calls += [("Vast 实例", lambda: self._managed(self.vast.list_instances())),
                      ("Vast 余额", self.vast.get_balance)]
        else:
            real = []  # no key: nothing of ours can be running
        for name, fn in calls:
            try:
                value = fn()
            except Exception as exc:
                errors[name] = f"{type(exc).__name__}: {exc}"
                continue
            if name == "Vast 报价":
                offers = value
            elif name == "Vast 实例":
                real = value
            else:
                balance = value

        display_offers = []
        if cfg["runpod"].get("api_key"):
            try:
                display_offers += runpod.fetch_offers(self.session, cfg["runpod"]["api_key"], gpu_names)
            except Exception as exc:
                errors["RunPod"] = f"{type(exc).__name__}: {exc}"
        for m in cfg.get("manual_offers") or []:
            display_offers.append({"platform": m["platform"], "id": f"manual-{m['platform']}", "gpu": m["gpu"],
                                   "num_gpus": 1, "usd_per_hr": float(m["usd_per_hr"]),
                                   "usd_per_hr_per_gpu": float(m["usd_per_hr"]), "reliability": None,
                                   "location": m.get("note"), "rentable": False})

        pool = None
        try:
            pool = kryptex.get_stats(self.session, cfg)
        except Exception as exc:
            errors["矿池"] = f"{type(exc).__name__}: {exc}"
        pool_workers = pool["workers_th"] if pool else None

        # Reconcile real rentals with what Vast reports.
        if real is not None:
            for inst in real:
                self.store.open_rental(inst, False)
            live_ids = {str(i["id"]) for i in real}
            for r in self.store.open_rentals():
                if not r["simulated"] and r["id"] not in live_ids:
                    self.store.close_rental(r["id"], "实例已不存在（自毁/余额耗尽/被房东收回）", now)
                    self.store.log("destroy", f"实例 {r['id']} 已不存在")

        # A simulated rental keeps its offer off the market, like a real one would.
        market = offers
        taken = {i["offer_id"] for i in self.sim_instances.values()}
        offers = [o for o in offers if o["id"] not in taken]

        hashrates, hashrate_info = self._measured_hashrates(real or [], pool_workers, now)
        mode = self.mode
        if mode == "live" and real is None:
            mode = "halted"  # can't see our instances, so don't add more
        instances = (real or []) + list(self.sim_instances.values())

        decision = decide(now=now, cfg=cfg, mode=mode, price=price,
                          last_live_price_ts=self.last_live_price_ts or self.started, prl_per_th_day=yld["value"],
                          fee=self.fee, hashrates=hashrates, offers=offers, instances=instances,
                          balance=balance, pool_workers=pool_workers,
                          counters=self.counters)
        self.counters = decision["counters"]

        for inst, reason in decision["destroy"]:
            try:
                self.destroy(inst, reason)
            except Exception as exc:
                errors[f"退租 {inst['id']}"] = f"{type(exc).__name__}: {exc}"
                self.store.log("error", f"退租 {inst['id']} 失败：{exc}")
        rented = []
        for offer, reason in decision["rent"]:
            try:
                inst = self._rent(offer, reason, now)
                if not inst["simulated"]:
                    rented.append(inst)
            except Exception as exc:
                errors[f"租用 {offer['id']}"] = f"{type(exc).__name__}: {exc}"
                self.store.log("error", f"租用 {offer['id']} 失败：{exc}")

        # Accrue cost / estimated output for everything still running.
        destroyed = {i["id"] for i, _ in decision["destroy"]}
        current = ([i for i in (real or []) if i["id"] not in destroyed] + rented
                   + list(self.sim_instances.values()))
        for inst in current:
            th = hashrates.get(inst["gpu"], 0) * inst["num_gpus"]
            self.store.accrue(inst["id"], now, inst["usd_per_hr"], th * yld["value"] * (1 - self.fee) / 86400)

        self._snapshot(now, price, yld, hashrates, market)
        self._publish(now, price, yld, hashrate_info, hashrates, balance, pool, pool_workers,
                      current, decision["offers"], display_offers, errors)

    def _snapshot(self, now, price, yld, hashrates, market):
        """One row of history per cycle, for the 24h report and chart.

        Uses the whole market, including offers our simulated rentals are holding.
        """
        lim = self.cfg["limits"]
        offers = []
        for o in market:
            th = hashrates.get(o["gpu"], 0) * o["num_gpus"]
            offers.append({**o, **evaluate(o["usd_per_hr"], th, yld["value"], price["price"], self.fee),
                           "hashrate_th": th})
        usable = [o for o in offers if o["rentable"] and o["hashrate_th"] > 0
                  and (o.get("reliability") or 0) >= lim["min_reliability"]]
        cheapest = min(usable, key=lambda o: o["usd_per_hr_per_gpu"], default=None)
        margins = [o["margin"] for o in usable if o["margin"] is not None]
        sim = self.store.totals(True)
        self.store.add_snapshot({
            "ts": now, "price": price["price"], "price_live": int(price["live"]),
            "prl_per_th_day": yld["value"], "offers_n": len(offers),
            "cheapest_usd_per_gpu": cheapest["usd_per_hr_per_gpu"] if cheapest else None,
            "cheapest_breakeven": cheapest["breakeven_price"] if cheapest else None,
            "best_margin": max(margins, default=None),
            "rentable_n": sum(rent_eligible(o, lim) for o in offers) if price["live"] else 0,
            "sim_running": len(self.sim_instances), "sim_cost": sim["cost"], "sim_prl": sim["prl_est"],
        })

    def _publish(self, now, price, yld, hashrate_info, hashrates, balance, pool, pool_workers,
                 current, offers, display_offers, errors):
        p = price["price"]
        rentals = {r["id"]: r for r in self.store.rentals(500)}
        inst_rows = []
        for inst in current:
            r = rentals.get(str(inst["id"]), {})
            e = evaluate(inst["usd_per_hr"], hashrates.get(inst["gpu"], 0) * inst["num_gpus"],
                         yld["value"], p, self.fee)
            inst_rows.append({**inst, "age_min": instance_age_min(inst, now),
                              "pool_th": (pool_workers or {}).get(f"vast{inst['id']}"),
                              "expected_th": hashrates.get(inst["gpu"], 0) * inst["num_gpus"],
                              "cost": r.get("cost", 0), "prl_est": r.get("prl_est", 0),
                              "margin": e["margin"], "breakeven_price": e["breakeven_price"],
                              "bad_checks": self.counters.get(inst["id"], {}).get("bad", 0)})

        for o in display_offers:
            th = hashrates.get(o["gpu"], 0)
            offers.append({**o, **evaluate(o["usd_per_hr"], th, yld["value"], p, self.fee), "hashrate_th": th})
        offers.sort(key=lambda o: (o["margin"] is None, -(o["margin"] or 0)))

        totals = {}
        for key, sim in (("real", False), ("sim", True)):
            t = self.store.totals(sim)
            totals[key] = {**t, "revenue_est": t["prl_est"] * p if p else None,
                           "pnl_est": t["prl_est"] * p - t["cost"] if p else None}
        if pool and pool.get("balance_prl") is not None:
            mined = (pool["balance_prl"] or 0) + (pool["paid_prl"] or 0)
            base = self.store.get_meta("pool_baseline")
            if base is None:
                self.store.set_meta("pool_baseline", mined)
                base = mined
            totals["real"]["prl_pool"] = mined - base
            totals["real"]["pnl_pool"] = (mined - base) * p - totals["real"]["cost"] if p else None

        spend = sum(i["usd_per_hr"] for i in current if not i.get("simulated"))
        reserve = self.cfg["limits"]["min_balance_reserve"]
        self.state = {
            "now": now, "mode": self.mode, "live_blockers": self.live_blockers(),
            "price": {k: price[k] for k in ("price", "source", "live", "volume")},
            "last_live_price_ts": self.last_live_price_ts,
            "yield": {"value": yld["value"], "source": yld["source"]}, "fee": self.fee,
            "hashrates": hashrate_info,
            "balance": balance, "hourly_spend": spend,
            "runway_days": (balance - reserve) / (spend * 24) if balance is not None and spend else None,
            "instances": inst_rows, "offers": offers[:80], "totals": totals,
            "pool": pool, "errors": errors, "events": self.store.events(60),
            "limits": self.cfg["limits"], "loop_seconds": self.cfg["loop_seconds"],
        }
