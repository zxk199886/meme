"""PRL/USD price: SafeTrade → CoinGecko → manual value from config."""
import json
import time

TIMEOUT = 15


def _ticker_price(ticker):
    raw = next((ticker[k] for k in ("last", "last_price", "price", "close") if ticker.get(k) is not None), None)
    if raw is None:
        raise ValueError(f"SafeTrade 行情里没有成交价字段：{json.dumps(ticker, ensure_ascii=False)[:200]}")
    last = float(raw)
    if last <= 0:
        raise ValueError("SafeTrade returned non-positive price")
    return {"price": last, "volume": float(ticker.get("vol") or ticker.get("volume") or 0)}


def _find_ticker(data, market):
    """Pull a ticker dict out of a Peatio-style response, or None."""
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("ticker"), dict):
        return data["ticker"]
    if "last" in data:
        return data
    # all-markets response: {"prlusdt": {"ticker": {...}}, ...}
    entry = data.get(market)
    if isinstance(entry, dict):
        return _find_ticker(entry, market)
    return None


def _safetrade(session, pcfg):
    market = pcfg["safetrade_market"]
    url = pcfg["safetrade_url"].format(market=market)
    data = session.get(url, timeout=TIMEOUT).json()
    # Peatio: {"at": 1700000000, "ticker": {"last": "1.85", "buy": ..., "sell": ..., "vol": ...}}
    ticker = _find_ticker(data, market)
    if ticker is None:
        # The market id may differ (e.g. prl_usdt): look it up in the all-markets ticker list.
        all_url = url.rsplit("/markets/", 1)[0] + "/markets/tickers"
        try:
            everything = session.get(all_url, timeout=TIMEOUT).json()
        except Exception:
            everything = None
        if isinstance(everything, dict):
            for key, entry in everything.items():
                k = key.lower().replace("_", "").replace("-", "").replace("/", "")
                if k.startswith("prl") and k.endswith("usdt"):
                    ticker = _find_ticker(entry, key)
                    break
    if ticker is None:
        raise ValueError(f"SafeTrade 返回里没有价格（交易对 {market}）：{json.dumps(data, ensure_ascii=False)[:200]}")
    return _ticker_price(ticker)


def _coingecko(session, pcfg):
    coin = pcfg["coingecko_id"]
    url = "https://api.coingecko.com/api/v3/simple/price"
    data = session.get(url, params={"ids": coin, "vs_currencies": "usd"}, timeout=TIMEOUT).json()
    return {"price": float(data[coin]["usd"]), "volume": None}


def get_prl_price(session, cfg):
    """Return {price, source, live, ts, errors}. price is None if nothing worked.

    live=False means the number is the manual fallback and must not drive renting.
    """
    pcfg = cfg["price"]
    errors = {}
    sources = [("SafeTrade", _safetrade)]
    if pcfg.get("coingecko_id"):
        sources.append(("CoinGecko", _coingecko))
    for name, fn in sources:
        try:
            result = fn(session, pcfg)
            return {**result, "source": name, "live": True, "ts": time.time(), "errors": errors}
        except Exception as exc:  # network, JSON shape, missing market
            errors[name] = f"{type(exc).__name__}: {exc}"
    manual = pcfg.get("manual_usd")
    return {
        "price": float(manual) if manual is not None else None,
        "volume": None,
        "source": "手动" if manual is not None else None,
        "live": False,
        "ts": time.time(),
        "errors": errors,
    }
