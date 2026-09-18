from __future__ import annotations
import numpy as np
import pandas as pd

def realized_vol(log_returns, window=20, annualization=252):
    r = pd.Series(log_returns, dtype=float).dropna()
    if len(r) < window: raise ValueError("not enough returns")
    return float(r.iloc[-window:].std(ddof=1)*np.sqrt(annualization))

def ewma_vol(log_returns, lam=0.94, annualization=252):
    r = pd.Series(log_returns, dtype=float).dropna()
    if len(r) < 2: raise ValueError("not enough returns")
    var = float(r.iloc[0]**2)
    for x in r.iloc[1:]:
        var = lam*var + (1-lam)*float(x**2)
    return float(np.sqrt(var*annualization))
