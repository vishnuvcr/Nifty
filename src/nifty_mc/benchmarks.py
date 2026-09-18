from __future__ import annotations
import numpy as np

def historical_bootstrap_terminal(s0, log_returns, horizon_days, n_paths=50000, seed=0):
    r = np.asarray(log_returns, dtype=float)
    if len(r) < 30: raise ValueError("need at least 30 historical returns")
    rng = np.random.default_rng(seed)
    draws = rng.choice(r, size=(n_paths, horizon_days), replace=True)
    return s0 * np.exp(draws.sum(axis=1))

def summarize_forecast(samples):
    x = np.asarray(samples, dtype=float)
    return {f"p{p:02d}": float(np.quantile(x,p/100)) for p in [1,5,10,25,50,75,90,95,99]}
