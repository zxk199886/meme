"""Emergency stop: destroy every Vast instance whose label starts with the configured prefix.

    python -m pearl_dashboard.stop_all
"""
import requests

from . import config as config_mod
from .sources.vast import VastClient


def main():
    cfg = config_mod.load()
    if not cfg["vast"]["api_key"]:
        raise SystemExit("没有 Vast API key")
    vast = VastClient(requests.Session(), cfg["vast"]["api_key"], cfg["vast"]["base_url"])
    prefix = cfg["instance"]["label_prefix"]
    targets = [i for i in vast.list_instances() if i["label"].startswith(prefix)]
    if not targets:
        print("没有需要退租的实例。")
    for inst in targets:
        vast.destroy_instance(inst["id"])
        print(f"已退租 {inst['id']} {inst['gpu']} ${inst['usd_per_hr']:.3f}/h")


if __name__ == "__main__":
    main()
