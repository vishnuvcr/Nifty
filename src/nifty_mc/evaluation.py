from __future__ import annotations

import numpy as np
import pandas as pd


def interval_metrics(actual: float, samples: np.ndarray) -> dict[str, float]:
    """Out-of-sample interval coverage and width for one forecast."""
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or len(x) < 2:
        raise ValueError("samples must be a non-empty 1D array")
    out: dict[str, float] = {}
    for level in (0.50, 0.80, 0.90):
        alpha = 1.0 - level
        lo, hi = np.quantile(x, [alpha / 2.0, 1.0 - alpha / 2.0])
        out[f"coverage_{int(level * 100)}"] = float(lo <= actual <= hi)
        out[f"width_{int(level * 100)}"] = float(hi - lo)
    return out


def crps_empirical(actual: float, samples: np.ndarray) -> float:
    """CRPS for an empirical predictive distribution.

    CRPS(F,y) = E|X-y| - 0.5 E|X-X'|.
    Uses a sorted-sample identity for O(n log n) computation.
    """
    x = np.sort(np.asarray(samples, dtype=float))
    if x.ndim != 1 or len(x) == 0:
        raise ValueError("samples must be a non-empty 1D array")
    n = len(x)
    term1 = float(np.mean(np.abs(x - actual)))
    # E|X-X'| = 2/n^2 * sum_i (2i-n-1) x_i, with i=1..n.
    idx = np.arange(1, n + 1, dtype=float)
    pairwise_mean = (2.0 / (n * n)) * float(np.sum((2.0 * idx - n - 1.0) * x))
    return term1 - 0.5 * pairwise_mean


def directional_brier(actual: float, samples: np.ndarray, s0: float) -> float:
    """Brier score for the event ST > S0; lower is better."""
    x = np.asarray(samples, dtype=float)
    if s0 <= 0:
        raise ValueError("s0 must be positive")
    p_up = float(np.mean(x > s0))
    outcome = float(actual > s0)
    return (p_up - outcome) ** 2


def summarize_oos(results: pd.DataFrame) -> dict[str, float]:
    """Aggregate walk-forward calibration metrics without tuning on OOS data."""
    if results.empty:
        return {}
    keys = [c for c in ("coverage_50", "coverage_80", "coverage_90",
                        "width_50", "width_80", "width_90", "crps", "brier_up")
            if c in results]
    return {f"mean_{k}": float(results[k].mean()) for k in keys}
