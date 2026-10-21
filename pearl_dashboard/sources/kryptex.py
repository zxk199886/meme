"""Kryptex pool stats. The JSON layout is not pinned down, so parsing is defensive:
any list of objects with a worker name and a hashrate is accepted.
"""
TIMEOUT = 20

NAME_KEYS = ("name", "worker", "worker_name", "rig")
HASH_KEYS = ("hashrate", "hashrate_current", "current_hashrate", "hashrate_10m", "hr")
BALANCE_KEYS = ("balance", "unpaid", "immature_balance", "unpaid_balance")
PAID_KEYS = ("paid", "total_paid", "paid_total")


def _first(d, keys):
    for k in keys:
        if k in d and d[k] is not None:
            try:
                return float(d[k])
            except (TypeError, ValueError):
                continue
    return None


def _walk(obj):
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def parse(data):
    workers = {}
    balance = paid = None
    for node in _walk(data):
        if not isinstance(node, dict):
            continue
        name = next((node[k] for k in NAME_KEYS if isinstance(node.get(k), str)), None)
        hr = _first(node, HASH_KEYS)
        if name and hr is not None:
            workers[name] = hr / 1e12 if hr > 1e9 else hr  # H/s → TH/s if given raw
        if balance is None:
            balance = _first(node, BALANCE_KEYS)
        if paid is None:
            paid = _first(node, PAID_KEYS)
    return {"workers_th": workers, "balance_prl": balance, "paid_prl": paid}


def get_stats(session, cfg):
    url = cfg["pool"].get("stats_url")
    wallet = cfg["pool"].get("wallet")
    if not url or not wallet:
        return None
    data = session.get(url.format(wallet=wallet), timeout=TIMEOUT).json()
    return parse(data)
