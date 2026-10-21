"""Profit math. All money in USD, hashrate in TH/s."""


def evaluate(usd_per_hr, hashrate_th, prl_per_th_day, price_usd, fee):
    """Expected daily economics of one rental.

    usd_per_hr is the total hourly price of the rental (all its GPUs),
    hashrate_th the total hashrate of the rental.
    """
    prl_day = hashrate_th * prl_per_th_day * (1 - fee)
    cost = usd_per_hr * 24
    revenue = prl_day * price_usd if price_usd is not None else None
    profit = revenue - cost if revenue is not None else None
    return {
        "prl_day": prl_day,
        "cost_day": cost,
        "revenue_day": revenue,
        "profit_day": profit,
        "margin": profit / cost if profit is not None and cost > 0 else None,
        "breakeven_price": cost / prl_day if prl_day > 0 else None,
    }
