"""Minimal Vast.ai REST client (endpoints as used by the official vast-ai/vast-cli)."""
from pathlib import Path

TIMEOUT = 30
ONSTART = Path(__file__).resolve().parent.parent / "miner" / "onstart.sh"


class VastClient:
    def __init__(self, session, api_key, base_url="https://console.vast.ai"):
        self.s = session
        self.base = base_url.rstrip("/")
        self.has_key = bool(api_key)
        # Without a key only the public offer search is attempted (simulation).
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def _url(self, path):
        return self.base + path

    def search_offers(self, gpu_names, min_reliability, disk_gb, limit=100):
        query = {
            "verified": {"eq": True},
            "external": {"eq": False},
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "gpu_name": {"in": list(gpu_names)},
            "reliability2": {"gte": min_reliability},
            "order": [["dph_total", "asc"]],
            "type": "on-demand",
            "allocated_storage": disk_gb,
            "limit": limit,
        }
        r = self.s.post(self._url("/api/v0/bundles/"), json=query, headers=self.headers, timeout=TIMEOUT)
        if r.status_code in (401, 403) and not self.has_key:
            raise RuntimeError("Vast 要求 API key 才能看报价：注册后把 key 填进 config.yaml 的 vast.api_key")
        r.raise_for_status()
        return [normalize_offer(o) for o in r.json().get("offers", [])]

    def list_instances(self):
        rows, params = [], {"limit": 25}
        while True:
            r = self.s.get(self._url("/api/v1/instances/"), params=params, headers=self.headers, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            rows.extend(data.get("instances") or [])
            if not data.get("next_token"):
                break
            params["after_token"] = data["next_token"]
        return [normalize_instance(i) for i in rows]

    def create_instance(self, offer_id, label, env, image, disk_gb):
        body = {
            "client_id": "me",
            "image": image,
            "env": env,
            "disk": disk_gb,
            "label": label,
            "onstart": ONSTART.read_text(encoding="utf-8"),
            "runtype": "ssh",
        }
        r = self.s.put(self._url(f"/api/v0/asks/{offer_id}/"), json=body, headers=self.headers, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if not data.get("success", True):
            raise RuntimeError(data.get("msg") or data)
        return data.get("new_contract")

    def destroy_instance(self, instance_id):
        r = self.s.delete(self._url(f"/api/v0/instances/{instance_id}/"), json={}, headers=self.headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    def get_balance(self):
        r = self.s.get(self._url("/api/v0/users/current/"), headers=self.headers, timeout=TIMEOUT)
        r.raise_for_status()
        return float(r.json().get("credit") or 0)


def normalize_offer(o):
    num = int(o.get("num_gpus") or 1)
    dph = float(o["dph_total"])
    return {
        "platform": "Vast.ai",
        "id": o["id"],
        "gpu": o.get("gpu_name"),
        "num_gpus": num,
        "usd_per_hr": dph,
        "usd_per_hr_per_gpu": dph / num,
        "reliability": o.get("reliability2", o.get("reliability")),
        "location": o.get("geolocation"),
        "rentable": True,
    }


def normalize_instance(i):
    return {
        "id": i["id"],
        "label": i.get("label") or "",
        "gpu": i.get("gpu_name"),
        "num_gpus": int(i.get("num_gpus") or 1),
        "usd_per_hr": float(i.get("dph_total") or 0),
        "status": i.get("actual_status") or i.get("cur_state"),
        "gpu_util": i.get("gpu_util"),
        "start_date": i.get("start_date"),
        "simulated": False,
    }
