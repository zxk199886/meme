"""Daily PRL per TH/s: WhatToMine (optional) → config value."""

TIMEOUT = 15


def get_prl_per_th_day(session, cfg):
    url = cfg.get("whattomine_url")
    if url:
        try:
            data = session.get(url, timeout=TIMEOUT).json()
            rewards = float(data["estimated_rewards"])
            per_th = rewards / float(cfg["whattomine_hashrate_th"])
            if per_th > 0:
                return {"value": per_th, "source": "WhatToMine", "error": None}
        except Exception as exc:
            return {"value": float(cfg["prl_per_th_day"]), "source": "配置",
                    "error": f"WhatToMine: {type(exc).__name__}: {exc}"}
    return {"value": float(cfg["prl_per_th_day"]), "source": "配置", "error": None}
