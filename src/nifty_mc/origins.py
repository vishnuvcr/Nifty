from __future__ import annotations

import pandas as pd

from .walk_forward import ForecastOrigin


def build_expiry_schedule(
    prices: pd.DataFrame,
    expiry_dates: pd.Series | list,
    entry_days_to_expiry: tuple[int, ...] = (5, 3),
) -> list[ForecastOrigin]:
    """Build historical decision origins using observed trading sessions.

    A decision date is selected as the Nth observed session before each expiry.
    This avoids hard-coding weekday expiry rules that changed historically.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(prices.index)).normalize().drop_duplicates().sort_values()
    if len(idx) == 0:
        raise ValueError("prices must contain at least one trading date")
    out: list[ForecastOrigin] = []
    for raw_expiry in pd.to_datetime(pd.Series(expiry_dates)).dropna().sort_values().unique():
        expiry = pd.Timestamp(raw_expiry).normalize()
        eligible = idx[idx < expiry]
        if expiry not in idx:
            # If the supplied expiry is not a trading session, use the last
            # observed session on/before the supplied date.
            on_or_before = idx[idx <= expiry]
            if len(on_or_before) == 0:
                continue
            expiry_session = on_or_before[-1]
        else:
            expiry_session = expiry
        eligible = idx[idx < expiry_session]
        for n in entry_days_to_expiry:
            if n < 1 or len(eligible) < n:
                continue
            decision = eligible[-n]
            out.append(ForecastOrigin(decision, expiry_session))
    return sorted(set(out), key=lambda x: (x.expiry_date, x.decision_date))
