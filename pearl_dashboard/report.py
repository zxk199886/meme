"""Summary of the last N hours from the snapshot history.

    python -m pearl_dashboard.report [--hours 24]
"""
import argparse
import statistics
import time
from collections import Counter
from pathlib import Path

from .store import Store

HERE = Path(__file__).resolve().parent

MAX_GAP = 300  # seconds; longer gaps mean the PC slept, they don't count as observed time


def summarize(store, hours=24, now=None):
    now = now or time.time()
    since = now - hours * 3600
    snaps = store.snapshots(since)
    if len(snaps) < 2:
        return {"samples": len(snaps), "hours": hours}

    observed = good = 0.0
    revenue = 0.0
    last_price = None
    for a, b in zip(snaps, snaps[1:]):
        dt = min(b["ts"] - a["ts"], MAX_GAP)
        observed += dt
        if a["rentable_n"]:
            good += dt
        last_price = b["price"] if b["price"] is not None else last_price
        if last_price is not None:
            revenue += ((b["sim_prl"] or 0) - (a["sim_prl"] or 0)) * last_price
    cost = (snaps[-1]["sim_cost"] or 0) - (snaps[0]["sim_cost"] or 0)
    prl = (snaps[-1]["sim_prl"] or 0) - (snaps[0]["sim_prl"] or 0)

    prices = [s["price"] for s in snaps if s["price"] is not None and s["price_live"]]
    margins = [s["best_margin"] for s in snaps if s["best_margin"] is not None]
    cheapest = [s["cheapest_usd_per_gpu"] for s in snaps if s["cheapest_usd_per_gpu"] is not None]
    reasons = Counter(r["end_reason"] for r in store.sim_rentals_ended(since))
    return {
        "hours": hours, "samples": len(snaps),
        "first_ts": snaps[0]["ts"], "last_ts": snaps[-1]["ts"],
        "observed_hours": observed / 3600,
        "rentable_hours": good / 3600,
        "price_min": min(prices, default=None), "price_max": max(prices, default=None),
        "price_avg": statistics.mean(prices) if prices else None,
        "price_last": prices[-1] if prices else None,
        "price_down_share": 1 - len(prices) / len(snaps),
        "no_offer_share": sum(1 for s in snaps if not s["offers_n"]) / len(snaps),
        "cheapest_seen": min(cheapest, default=None),
        "median_best_margin": statistics.median(margins) if margins else None,
        "sim_rentals": store.sim_rentals_started(since),
        "sim_cost": cost, "sim_prl": prl, "sim_revenue": revenue, "sim_pnl": revenue - cost,
        "end_reasons": dict(reasons),
    }


def _usd(v, d=2):
    return "—" if v is None else ("-$" if v < 0 else "$") + f"{abs(v):.{d}f}"


def format_report(s):
    if s["samples"] < 2:
        return f"过去 {s['hours']} 小时还没有足够的数据（{s['samples']} 条），让面板多跑一会儿再看。"
    t = time.strftime
    lines = [
        f"=== Pearl 模拟报告：{t('%m-%d %H:%M', time.localtime(s['first_ts']))} → "
        f"{t('%m-%d %H:%M', time.localtime(s['last_ts']))} ===",
        f"实际观察时长    {s['observed_hours']:.1f} 小时（{s['samples']} 次采样；电脑休眠的时间不算）",
        f"PRL 价格        最低 {_usd(s['price_min'], 3)} · 平均 {_usd(s['price_avg'], 3)} · "
        f"最高 {_usd(s['price_max'], 3)} · 最新 {_usd(s['price_last'], 3)}",
        f"有合格卡的时间  {s['rentable_hours']:.1f} 小时"
        f"（{s['rentable_hours'] / s['observed_hours'] * 100 if s['observed_hours'] else 0:.0f}%）",
        f"见过最便宜的卡  {_usd(s['cheapest_seen'], 3)}/小时 · 最好利润率中位数 "
        + ("—" if s["median_best_margin"] is None else f"{s['median_best_margin'] * 100:.0f}%"),
        f"模拟租用        {s['sim_rentals']} 次 · 花费 {_usd(s['sim_cost'])} · 挖到约 {s['sim_prl']:.3f} PRL"
        f" · 价值 {_usd(s['sim_revenue'])}",
        f"模拟盈亏        {_usd(s['sim_pnl'])}",
    ]
    if s["end_reasons"]:
        lines.append("退租原因        " + "；".join(f"{k} ×{v}" for k, v in s["end_reasons"].items()))
    if s["price_down_share"] > 0.05:
        lines.append(f"⚠️ {s['price_down_share'] * 100:.0f}% 的时间拿不到实时币价")
    if s["no_offer_share"] > 0.05:
        lines.append(f"⚠️ {s['no_offer_share'] * 100:.0f}% 的时间拿不到 Vast 报价")
    verdict = (f"结论：{s['observed_hours']:.1f} 小时里有 {s['rentable_hours']:.1f} 小时值得租，"
               f"模拟{'净赚' if s['sim_pnl'] >= 0 else '亏损'} {_usd(abs(s['sim_pnl']))}。"
               "模拟没算开机等待和坏机器，真实结果会更差一些。")
    lines.append(verdict)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Pearl 模拟报告")
    ap.add_argument("--hours", type=float, default=24)
    args = ap.parse_args()
    print(format_report(summarize(Store(str(HERE / "pearl.sqlite3")), args.hours)))


if __name__ == "__main__":
    main()
