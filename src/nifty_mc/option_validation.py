from __future__ import annotations

import pandas as pd


def nearest_actual_expiry(chain: pd.DataFrame, decision_date, target_expiry=None) -> pd.Timestamp:
    """Return the nearest expiry strictly after the decision date.

    If a target expiry is supplied and is present in the chain, prefer it;
    otherwise fall back to the nearest actual listed expiry. This prevents
    treating a calendar-generated expiry as authoritative when the exchange
    did not list that contract.
    """
    required = {"timestamp", "expiry", "strike", "option_type"}
    missing = required - set(chain.columns)
    if missing:
        raise ValueError(f"chain missing columns: {sorted(missing)}")

    d = pd.Timestamp(decision_date).normalize()
    x = chain.copy()
    x["expiry"] = pd.to_datetime(x["expiry"], errors="coerce").dt.normalize()
    expiries = pd.DatetimeIndex(x.loc[x["expiry"] > d, "expiry"].dropna().unique()).sort_values()
    if len(expiries) == 0:
        raise ValueError("no actual expiry strictly after decision date")

    if target_expiry is not None:
        target = pd.Timestamp(target_expiry).normalize()
        if target in expiries:
            return target
    return expiries[0]


def validate_condor_chain(chain: pd.DataFrame, expiry, strikes) -> dict:
    """Validate that all four Long Iron Condor legs exist and have usable EOD prices."""
    if len(strikes) != 4:
        raise ValueError("exactly four strikes are required")
    k1, k2, k3, k4 = map(float, strikes)
    if not (k1 < k2 < k3 < k4):
        raise ValueError("strikes must satisfy K1 < K2 < K3 < K4")

    e = pd.Timestamp(expiry).normalize()
    x = chain[pd.to_datetime(chain["expiry"]).dt.normalize() == e].copy()
    if "symbol" in x.columns:
        x = x[x["symbol"].astype(str).str.upper().eq("NIFTY")]

    required_legs = [(k1, "PE"), (k2, "PE"), (k3, "CE"), (k4, "CE")]
    missing = []
    usable = []
    for strike, typ in required_legs:
        row = x[(x["strike"].astype(float) == strike) & (x["option_type"].astype(str).str.upper() == typ)]
        if row.empty:
            missing.append((strike, typ))
            continue
        r = row.iloc[0]
        px = r.get("close")
        if pd.isna(px) or float(px) <= 0:
            missing.append((strike, typ))
            continue
        usable.append((strike, typ, float(px)))

    return {
        "expiry": e,
        "valid": len(missing) == 0,
        "missing_legs": missing,
        "legs": usable,
    }
