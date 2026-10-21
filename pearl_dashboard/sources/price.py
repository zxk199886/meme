"""PRL/USD price: SafeTrade → CoinGecko → manual value from config."""
import time

TIMEOUT = 15


def _safetrade(session, pcfg):
    url = pcfg["safetrade_url"].format(market=pcfg["safetrade_market"])
    data = session.get(url, timeout=TIMEOUT).json()
    # Peatio: {"at": 1700000000, "ticker": {"last": "1.85", "buy": ..., "sell": ..., "vol": ...}}
    ticker = data.get("ticker", data)
    last = float(ticker["last"])
    if last <= 0:
        raise ValueError("SafeTrade returned non-positive price")
    return {"price": last, "volume": float(ticker.get("vol") or 0)}


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
