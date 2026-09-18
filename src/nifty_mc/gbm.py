from __future__ import annotations
import numpy as np

def simulate_terminal_gbm(s0, horizon_years, mu, sigma, n_paths=50000, seed=None):
    if s0 <= 0 or horizon_years < 0 or sigma < 0 or n_paths < 1:
        raise ValueError("invalid GBM inputs")
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths)
    return s0 * np.exp((mu - 0.5*sigma**2)*horizon_years + sigma*np.sqrt(horizon_years)*z)

def summarize(samples):
    x = np.asarray(samples, dtype=float)
    qs = [0.01,0.05,0.10,0.25,0.50,0.75,0.90,0.95,0.99]
    return {
        "quantiles": {f"p{int(q*100):02d}": float(v) for q,v in zip(qs,np.quantile(x,qs))},
        "mean": float(np.mean(x)),
        "std": float(np.std(x,ddof=1)),
    }
