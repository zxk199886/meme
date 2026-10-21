"""RunPod GPU prices, for comparison only (not rented automatically)."""

TIMEOUT = 20
QUERY = """query { gpuTypes { id displayName securePrice communityPrice
  lowestPrice(input: {gpuCount: 1}) { minimumBidPrice uninterruptablePrice } } }"""


def fetch_offers(session, api_key, gpu_names):
    r = session.post("https://api.runpod.io/graphql", params={"api_key": api_key},
                     json={"query": QUERY}, timeout=TIMEOUT)
    r.raise_for_status()
    wanted = {g.replace("RTX ", "").lower(): g for g in gpu_names}
    offers = []
    for t in r.json()["data"]["gpuTypes"]:
        name = (t.get("displayName") or t.get("id") or "").replace("RTX ", "").lower()
        gpu = wanted.get(name)
        if not gpu:
            continue
        lowest = t.get("lowestPrice") or {}
        for kind, price in (("Community", t.get("communityPrice")), ("Secure", t.get("securePrice")),
                            ("Spot", lowest.get("minimumBidPrice"))):
            if price:
                offers.append({"platform": f"RunPod {kind}", "id": f"runpod-{t['id']}-{kind}", "gpu": gpu,
                               "num_gpus": 1, "usd_per_hr": float(price), "usd_per_hr_per_gpu": float(price),
                               "reliability": None, "location": None, "rentable": False})
    return offers
