"""Rent / release decisions. Pure function of the inputs so it can be unit tested."""
from .calc import evaluate


def instance_age_min(inst, now):
    return (now - (inst.get("start_date") or now)) / 60


def decide(*, now, cfg, mode, price, last_live_price_ts, prl_per_th_day, fee, hashrates,
           offers, instances, balance, pool_workers, counters):
    """Return {"rent": [(offer, reason)], "destroy": [(instance, reason)], "counters", "offers"}.

    mode: "live" | "simulate" | "halted". Destroys are always protective and returned in
    every mode; rents only in live/simulate.
    hashrates: TH/s per GPU model (measured if available, else from config).
    pool_workers: {worker_name: TH/s} or None when pool stats are unavailable.
    counters: {instance_id: {"bad": int, "unhealthy": int}} from the previous cycle.
    """
    lim = cfg["limits"]
    lifetime_min = lim["max_lifetime_hours"] * 60
    price_usd = price.get("price") if price else None
    price_fresh = (last_live_price_ts is not None
                   and now - last_live_price_ts <= lim["price_stale_minutes"] * 60)
    rent_price_ok = bool(price and price.get("live")) and price_fresh

    destroy, new_counters = [], {}

    def econ(usd_per_hr, gpu, num_gpus):
        return evaluate(usd_per_hr, hashrates.get(gpu, 0) * num_gpus, prl_per_th_day,
                        price_usd, fee)

    global_reason = None
    if not price_fresh:
        global_reason = f"实时币价超过 {lim['price_stale_minutes']} 分钟拿不到"
    elif balance is not None and balance < lim["min_balance_reserve"]:
        global_reason = f"余额 ${balance:.2f} 低于保留 ${lim['min_balance_reserve']}"

    for inst in instances:
        iid = inst["id"]
        c = dict(counters.get(iid, {"bad": 0, "unhealthy": 0}))
        age = instance_age_min(inst, now)
        if global_reason:
            destroy.append((inst, global_reason))
            continue
        if age >= lifetime_min + 10:
            destroy.append((inst, f"超过最长寿命 {lim['max_lifetime_hours']} 小时"))
            continue

        e = econ(inst["usd_per_hr"], inst["gpu"], inst["num_gpus"])
        c["bad"] = c["bad"] + 1 if (e["margin"] is not None and e["margin"] < 0) else 0
        if c["bad"] >= lim["stop_after_bad_checks"]:
            destroy.append((inst, f"连续 {c['bad']} 次检查亏损（保本价 ${e['breakeven_price']:.3f}）"))
            continue

        if not inst.get("simulated") and age > lim["warmup_minutes"]:
            problems = []
            if inst.get("status") != "running":
                problems.append(f"状态 {inst.get('status')}")
            util = inst.get("gpu_util")
            if util is not None and util < lim["min_gpu_util"]:
                problems.append(f"GPU 利用率 {util:.0f}%")
            worker = f"vast{iid}"
            if pool_workers is not None and pool_workers.get(worker, 0) <= 0:
                problems.append("矿池没有算力")
            c["unhealthy"] = c["unhealthy"] + 1 if problems else 0
            if c["unhealthy"] >= lim["unhealthy_checks"]:
                destroy.append((inst, "不健康：" + "，".join(problems)))
                continue
        new_counters[iid] = c

    # Evaluate the market
    evaluated = []
    for o in offers:
        e = econ(o["usd_per_hr"], o["gpu"], o["num_gpus"])
        evaluated.append({**o, **e, "hashrate_th": hashrates.get(o["gpu"], 0) * o["num_gpus"]})
    evaluated.sort(key=lambda o: (o["margin"] is None, -(o["margin"] or 0)))

    rent = []
    can_rent = mode == "simulate" or (mode == "live" and balance is not None)
    if can_rent and rent_price_ok and not global_reason:
        destroyed = {i["id"] for i, _ in destroy}
        # Instances close to their lifetime don't count, so a replacement can be rented in time.
        active = [i for i in instances if i["id"] not in destroyed
                  and instance_age_min(i, now) < lifetime_min - lim["renew_before_minutes"]]
        gpus = sum(i["num_gpus"] for i in active)
        spend = sum(i["usd_per_hr"] for i in active)
        for o in evaluated:
            if len(rent) >= lim["max_new_per_cycle"]:
                break
            if not o["rentable"] or o["hashrate_th"] <= 0 or o["margin"] is None:
                continue
            if o["margin"] < lim["min_margin"]:
                break  # sorted by margin, nothing better follows
            if o["usd_per_hr_per_gpu"] > lim["max_usd_per_hr_per_gpu"]:
                continue
            if (o.get("reliability") or 0) < lim["min_reliability"]:
                continue
            if gpus + o["num_gpus"] > lim["max_gpus"] or spend + o["usd_per_hr"] > lim["max_hourly_spend"]:
                continue
            if balance is not None and balance - lim["min_balance_reserve"] < o["usd_per_hr"]:
                continue
            rent.append((o, f"预期利润率 {o['margin']*100:.0f}%，日利润 ${o['profit_day']:.2f}"))
            gpus += o["num_gpus"]
            spend += o["usd_per_hr"]

    return {"rent": rent, "destroy": destroy, "counters": new_counters, "offers": evaluated}
