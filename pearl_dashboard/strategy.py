"""Rent / release decisions. Pure function of the inputs so it can be unit tested."""
from .calc import evaluate


def instance_age_min(inst, now):
    return (now - (inst.get("start_date") or now)) / 60


def rent_eligible(o, lim):
    """Offer-level rent conditions (an evaluated offer), ignoring caps and balance."""
    return (o["rentable"] and o["hashrate_th"] > 0 and o["margin"] is not None
            and o["margin"] >= lim["min_margin"]
            and o["usd_per_hr_per_gpu"] <= lim["max_usd_per_hr_per_gpu"]
            and (o.get("reliability") or 0) >= lim["min_reliability"])


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
    idle_reason = None
    can_rent = mode == "simulate" or (mode == "live" and balance is not None)
    if mode == "halted":
        idle_reason = "已暂停租新卡"
    elif global_reason:
        idle_reason = global_reason
    elif not rent_price_ok:
        idle_reason = "这一轮没拿到实时币价（可在设置里开启“用手动价格模拟”）"
    elif not can_rent:
        idle_reason = "拿不到 Vast 余额，真租时不租新卡"
    elif not offers:
        idle_reason = "没有可租的 Vast 报价（没拿到，或都被已租的卡占着）"
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
            if not rent_eligible(o, lim):
                continue
            if gpus + o["num_gpus"] > lim["max_gpus"] or spend + o["usd_per_hr"] > lim["max_hourly_spend"]:
                continue
            if balance is not None and balance - lim["min_balance_reserve"] < o["usd_per_hr"]:
                continue
            rent.append((o, f"预期利润率 {o['margin']*100:.0f}%，日利润 ${o['profit_day']:.2f}"))
            gpus += o["num_gpus"]
            spend += o["usd_per_hr"]
        if not rent and offers:
            idle_reason = _why_not(evaluated, lim, gpus, spend)

    return {"rent": rent, "destroy": destroy, "counters": new_counters, "offers": evaluated,
            "idle_reason": None if rent else idle_reason}


def _why_not(evaluated, lim, gpus, spend):
    """Plain-language reason no offer was rented this cycle."""
    if any(rent_eligible(o, lim) for o in evaluated):
        return (f"已到上限（{gpus}/{lim['max_gpus']} 张卡，${spend:.2f}/{lim['max_hourly_spend']:.2f} 每小时，"
                f"或余额不够）")
    usable = [o for o in evaluated if o["rentable"] and o["hashrate_th"] > 0 and o["margin"] is not None]
    if not usable:
        return "报价里没有已知算力的卡（检查 config 里的 gpus）"
    def blocked_by(o):
        if (o.get("reliability") or 0) < lim["min_reliability"]:
            return f"可靠性 {(o.get('reliability') or 0) * 100:.0f}% 低于要求 {lim['min_reliability'] * 100:.0f}%"
        if o["usd_per_hr_per_gpu"] > lim["max_usd_per_hr_per_gpu"]:
            return f"单卡 ${o['usd_per_hr_per_gpu']:.3f}/h 超过上限 ${lim['max_usd_per_hr_per_gpu']}/h"
        return None

    def too_thin(o):
        return (f"最好的卡 ${o['usd_per_hr_per_gpu']:.3f}/h 利润率 {o['margin'] * 100:.0f}%，"
                f"低于门槛 {lim['min_margin'] * 100:.0f}%（保本价 ${o['breakeven_price']:.3f}）")

    allowed = [o for o in usable if not blocked_by(o)]
    best_allowed = max(allowed, key=lambda o: o["margin"], default=None)
    good_but_blocked = [o for o in usable if o["margin"] >= lim["min_margin"] and blocked_by(o)]
    if not good_but_blocked:
        return too_thin(best_allowed or max(usable, key=lambda o: o["margin"]))
    o = max(good_but_blocked, key=lambda o: o["margin"])
    msg = f"利润率够的卡（${o['usd_per_hr_per_gpu']:.3f}/h，{o['margin'] * 100:.0f}%）{blocked_by(o)}"
    if best_allowed:
        msg += "；其余" + too_thin(best_allowed)
    return msg

