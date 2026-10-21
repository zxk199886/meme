"""One-shot check of every data source. Paste the output if something is ❌.

    python -m pearl_dashboard.check
"""
import json

import requests

from . import config as config_mod
from .sources import kryptex, runpod
from .sources.price import _coingecko, _safetrade
from .sources.vast import VastClient
from .sources.yield_ import get_prl_per_th_day


class Recorder:
    """Wraps a session and remembers the last response, to show it when a check fails."""

    def __init__(self, session):
        self.s = session
        self.last = None

    def _call(self, method, url, **kw):
        self.last = (method.upper(), url, None, "")
        r = getattr(self.s, method)(url, **kw)
        text = getattr(r, "text", None)
        if text is None:
            try:
                text = json.dumps(r.json(), ensure_ascii=False)
            except Exception:
                text = ""
        self.last = (method.upper(), url, r.status_code, text)
        return r

    def get(self, url, **kw):
        return self._call("get", url, **kw)

    def post(self, url, **kw):
        return self._call("post", url, **kw)


def run(cfg, session, out=print):
    rec = Recorder(session)
    results = {}

    def check(name, fn):
        rec.last = None
        try:
            msg = fn()
            ok = True
            out(f"✅ {name}：{msg}")
        except Exception as exc:
            ok = False
            out(f"❌ {name}：{type(exc).__name__}: {exc}")
            if rec.last and rec.last[2] is not None:
                method, url, status, body = rec.last
                out(f"   {method} {url.split('?')[0]} → HTTP {status}")
                if body:
                    out("   返回内容：" + body[:300].replace("\n", " "))
        results[name] = ok

    pcfg = cfg["price"]

    def safetrade():
        r = _safetrade(rec, pcfg)
        return f"PRL = ${r['price']:.4f}（24h 成交量 {r['volume']:,.0f}）"
    check("SafeTrade 币价", safetrade)
    if pcfg.get("coingecko_id"):
        check("CoinGecko 币价", lambda: f"PRL = ${_coingecko(rec, pcfg)['price']:.4f}")

    vast = VastClient(rec, cfg["vast"]["api_key"], cfg["vast"]["base_url"])
    gpus = [g for g, h in cfg["gpus"].items() if h]

    def offers():
        found = vast.search_offers(gpus, cfg["limits"]["min_reliability"], cfg["instance"]["disk_gb"])
        if not found:
            raise RuntimeError(f"没有符合条件的 {', '.join(gpus)} 报价（可靠性 ≥ {cfg['limits']['min_reliability']}）")
        best = min(found, key=lambda o: o["usd_per_hr_per_gpu"])
        return (f"{len(found)} 个报价，最便宜 ${best['usd_per_hr_per_gpu']:.3f}/小时/卡"
                + ("" if vast.has_key else "（未登录查询）"))
    check("Vast 报价", offers)
    if vast.has_key:
        check("Vast 余额", lambda: f"${vast.get_balance():.2f}")

    def yld():
        y = get_prl_per_th_day(rec, cfg)
        if y["error"]:
            raise RuntimeError(y["error"])
        return f"{y['value'] * 1000:.2f} PRL/天 每 1000 TH/s（来源：{y['source']}）"
    check("每日产出", yld)

    if cfg["pool"].get("stats_url") and cfg["pool"].get("wallet"):
        def pool():
            s = kryptex.get_stats(rec, cfg)
            return f"{len(s['workers_th'])} 个矿工，余额 {s['balance_prl']}"
        check("Kryptex 矿池", pool)
    if cfg["runpod"].get("api_key"):
        check("RunPod 比价", lambda: f"{len(runpod.fetch_offers(rec, cfg['runpod']['api_key'], gpus))} 个价格")

    failed = []
    if not (results["SafeTrade 币价"] or results.get("CoinGecko 币价")):
        failed.append("币价")
    if not results["Vast 报价"]:
        failed.append("Vast 报价")
    out("")
    if failed:
        out("还不能开始模拟，先解决：" + "、".join(failed) + "。把上面的输出贴给 Claude。")
    else:
        out("可以开始模拟：python -m pearl_dashboard.server")
    return not failed


def main():
    raise SystemExit(0 if run(config_mod.load(), requests.Session()) else 1)


if __name__ == "__main__":
    main()
