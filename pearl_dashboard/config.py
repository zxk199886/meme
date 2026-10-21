"""Load config.yaml on top of the defaults in config.example.yaml."""
import os
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE / "config.example.yaml"


def _merge(base, override):
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load(path=None):
    cfg = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    path = Path(path) if path else HERE / "config.yaml"
    if path.exists():
        cfg = _merge(cfg, yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    if os.environ.get("VAST_API_KEY"):
        cfg["vast"]["api_key"] = os.environ["VAST_API_KEY"]
    if os.environ.get("RUNPOD_API_KEY"):
        cfg["runpod"]["api_key"] = os.environ["RUNPOD_API_KEY"]
    cfg["_path"] = str(path)
    return cfg


def total_fee(cfg):
    """Combined pool + miner dev fee as a fraction of gross output."""
    return 1 - (1 - float(cfg["pool"]["fee"])) * (1 - float(cfg["instance"]["miner_fee"]))
