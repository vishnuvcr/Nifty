from __future__ import annotations
import numpy as np
import pandas as pd

def select_condor_strikes(
    spot: float,
    strikes: pd.Series,
    lower_offset: float,
    upper_offset: float,
    wing_width: float,
):
    """Select symmetric-ish strikes around spot from an available chain."""
    ks = np.sort(pd.Series(strikes).dropna().astype(float).unique())
    if len(ks) < 4:
        raise ValueError("need at least four strikes")
    k2 = ks[np.argmin(np.abs(ks - (spot - lower_offset)))]
    k3 = ks[np.argmin(np.abs(ks - (spot + upper_offset)))]
    below = ks[ks < k2]
    above = ks[ks > k3]
    if len(below) == 0 or len(above) == 0:
        raise ValueError("insufficient wing strikes")
    k1 = below[np.argmin(np.abs(below - (k2-wing_width)))]
    k4 = above[np.argmin(np.abs(above - (k3+wing_width)))]
    return float(k1), float(k2), float(k3), float(k4)

def four_leg_debit(chain: pd.DataFrame, k1, k2, k3, k4):
    """Conservative executable debit using asks for longs and bids for shorts."""
    required = {"strike","option_type","bid","ask"}
    if not required.issubset(chain.columns):
        raise ValueError(f"chain must contain {required}")
    def px(k, typ, side):
        row = chain[(chain.strike==k) & (chain.option_type.str.upper()==typ)]
        if row.empty:
            raise ValueError(f"missing {typ} {k}")
        return float(row.iloc[0]["ask" if side=="BUY" else "bid"])
    # short put K1 + long put K2 + long call K3 + short call K4
    return px(k2,"PE","BUY") + px(k3,"CE","BUY") - px(k1,"PE","SELL") - px(k4,"CE","SELL")
