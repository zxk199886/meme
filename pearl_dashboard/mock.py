"""Fake HTTP session that imitates SafeTrade / Vast / RunPod / Kryptex (MOCK=1 and tests)."""
import random
import time


class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, price=2.0, balance=50.0, seed=1, clock=time.time):
        self.clock = clock
        self.rng = random.Random(seed)
        self.price = price
        self.balance = balance
        self.fail = set()          # e.g. {"safe.trade"} to simulate an outage
        self.calls = []            # (method, url) log for tests
        self.instances = {}
        self.next_id = 1000
        self.offers = [
            {"id": 1, "gpu_name": "RTX 5090", "num_gpus": 1, "dph_total": 0.38, "reliability2": 0.99, "geolocation": "US"},
            {"id": 2, "gpu_name": "RTX 5090", "num_gpus": 1, "dph_total": 0.42, "reliability2": 0.985, "geolocation": "DE"},
            {"id": 3, "gpu_name": "RTX 5090", "num_gpus": 2, "dph_total": 0.90, "reliability2": 0.99, "geolocation": "CA"},
            {"id": 4, "gpu_name": "RTX 5090", "num_gpus": 1, "dph_total": 0.55, "reliability2": 0.99, "geolocation": "SE"},
            {"id": 5, "gpu_name": "RTX 5090", "num_gpus": 1, "dph_total": 0.31, "reliability2": 0.93, "geolocation": "VN"},
            {"id": 6, "gpu_name": "RTX 5090", "num_gpus": 1, "dph_total": 0.69, "reliability2": 0.999, "geolocation": "US"},
        ]

    def _route(self, method, url, params=None, json=None):
        self.calls.append((method, url))
        for host in self.fail:
            if host in url:
                raise ConnectionError(f"mock outage {host}")
        if "safe.trade" in url:
            return {"at": int(time.time()), "ticker": {"last": f"{self.price:.4f}", "vol": "123456"}}
        if "/api/v0/bundles/" in url:
            taken = {i["_offer"] for i in self.instances.values()}
            return {"offers": [o for o in self.offers if o["id"] not in taken]}
        if "/api/v0/asks/" in url and method == "PUT":
            offer_id = int(url.rstrip("/").split("/")[-1])
            offer = next(o for o in self.offers if o["id"] == offer_id)
            iid = self.next_id
            self.next_id += 1
            self.instances[iid] = {"id": iid, "label": json["label"], "gpu_name": offer["gpu_name"],
                                   "num_gpus": offer["num_gpus"], "dph_total": offer["dph_total"],
                                   "actual_status": "running", "gpu_util": 99.0, "start_date": self.clock(),
                                   "_offer": offer_id, "_env": json["env"]}
            return {"success": True, "new_contract": iid}
        if "/api/v1/instances/" in url:
            return {"instances": [{k: v for k, v in i.items()} for i in self.instances.values()], "next_token": None}
        if "/api/v0/instances/" in url and method == "DELETE":
            self.instances.pop(int(url.rstrip("/").split("/")[-1]), None)
            return {"success": True}
        if "/api/v0/users/current/" in url:
            return {"credit": self.balance}
        if "runpod.io" in url:
            return {"data": {"gpuTypes": [
                {"id": "NVIDIA GeForce RTX 5090", "displayName": "RTX 5090", "securePrice": 0.94,
                 "communityPrice": 0.69, "lowestPrice": {"minimumBidPrice": 0.5}}]}}
        if "kryptex" in url:
            return {"balance": 1.234, "paid": 0, "workers": [
                {"name": f"vast{iid}", "hashrate": 338.0} for iid in self.instances]}
        return FakeResponse({}, 404)

    def _wrap(self, method, url, **kw):
        data = self._route(method, url, kw.get("params"), kw.get("json"))
        return data if isinstance(data, FakeResponse) else FakeResponse(data)

    def get(self, url, **kw):
        return self._wrap("GET", url, **kw)

    def post(self, url, **kw):
        return self._wrap("POST", url, **kw)

    def put(self, url, **kw):
        return self._wrap("PUT", url, **kw)

    def delete(self, url, **kw):
        return self._wrap("DELETE", url, **kw)

    def wiggle(self):
        """Random-walk the price a little (demo mode)."""
        self.price = max(0.5, self.price * (1 + self.rng.uniform(-0.03, 0.03)))
