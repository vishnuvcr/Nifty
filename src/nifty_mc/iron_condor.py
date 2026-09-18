from __future__ import annotations
import numpy as np


def long_iron_condor_profit(terminal, k1, k2, k3, k4, debit):
    """
    Expiration P&L for a long iron condor:

      - short put  K1
      + long put   K2
      + long call  K3
      - short call K4
      - net debit

    with k1 < k2 < k3 < k4.
    """
    if not (k1 < k2 < k3 < k4) or debit < 0:
        raise ValueError("require k1 < k2 < k3 < k4 and non-negative debit")

    st = np.asarray(terminal, dtype=float)
    put_spread = np.maximum(k2 - st, 0) - np.maximum(k1 - st, 0)
    call_spread = np.maximum(st - k3, 0) - np.maximum(st - k4, 0)
    return put_spread + call_spread - debit


def metrics(profits):
    p = np.asarray(profits, dtype=float)
    return {
        "pop": float(np.mean(p > 0)),
        "ev": float(np.mean(p)),
        "p01": float(np.quantile(p, 0.01)),
        "p05": float(np.quantile(p, 0.05)),
        "p50": float(np.quantile(p, 0.50)),
        "p95": float(np.quantile(p, 0.95)),
        "p99": float(np.quantile(p, 0.99)),
    }
