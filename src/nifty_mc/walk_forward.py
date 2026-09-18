from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
import numpy as np
import pandas as pd

from .gbm import simulate_terminal_gbm
from .volatility import realized_vol
from .trend import classify_trend
from .iron_condor import long_iron_condor_profit, metrics


@dataclass(frozen=True)
class ForecastOrigin:
    decision_date: pd.Timestamp
    expiry_date: pd.Timestamp


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close.astype(float)).diff().dropna()


def make_forecast(
    s0: float,
    horizon_days: int,
    returns_history: pd.Series,
    vol_window: int = 20,
    drift_window: int = 60,
    n_paths: int = 50_000,
    seed: int = 0,
):
    lr = log_returns(returns_history) if not isinstance(returns_history.index, pd.RangeIndex) else pd.Series(returns_history)
    sigma = realized_vol(lr, window=vol_window)
    mu = float(lr.tail(drift_window).mean() * 252) if len(lr) >= drift_window else float(lr.mean() * 252)
    t = horizon_days / 252.0
    samples = simulate_terminal_gbm(s0, t, mu, sigma, n_paths=n_paths, seed=seed)
    trend = classify_trend(samples, s0)
    q = np.quantile(samples, [0.01,0.05,0.10,0.25,0.50,0.75,0.90,0.95,0.99])
    out = {"s0":s0, "sigma":sigma, "mu":mu, "horizon_days":horizon_days}
    out.update({f"p{int(p*100):02d}":float(v) for p,v in zip([.01,.05,.10,.25,.50,.75,.90,.95,.99],q)})
    out.update(trend)
    return out, samples


def evaluate_prediction(actual_st: float, samples: np.ndarray, s0: float) -> dict:
    x = np.asarray(samples)
    intervals = {}
    for level in (0.50,0.80,0.90):
        alpha = 1.0 - level
        lo, hi = np.quantile(x, [alpha/2, 1-alpha/2])
        intervals[f"coverage_{int(level*100)}"] = float(lo <= actual_st <= hi)
        intervals[f"width_{int(level*100)}"] = float(hi-lo)
    intervals["actual_st"] = float(actual_st)
    intervals["realized_move"] = float(actual_st/s0 - 1.0)
    return intervals


def walk_forward(
    prices: pd.DataFrame,
    expiry_schedule: Iterable[ForecastOrigin],
    price_col: str = "close",
    min_history: int = 120,
    vol_window: int = 20,
    drift_window: int = 60,
    n_paths: int = 50_000,
    seed: int = 20260918,
):
    df = prices.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    rows = []

    for i, origin in enumerate(expiry_schedule):
        decision = pd.Timestamp(origin.decision_date)
        expiry = pd.Timestamp(origin.expiry_date)
        hist = df.loc[df.index <= decision, price_col].dropna()
        future = df.loc[(df.index > decision) & (df.index <= expiry), price_col].dropna()
        if len(hist) < min_history or future.empty:
            continue
        s0 = float(hist.iloc[-1])
        actual = float(future.iloc[-1])
        horizon = max(1, int((expiry - decision).days))
        forecast, samples = make_forecast(
            s0, horizon, hist, vol_window, drift_window, n_paths=n_paths,
            seed=seed+i
        )
        score = evaluate_prediction(actual, samples, s0)
        rows.append({
            "decision_date": decision,
            "expiry_date": expiry,
            "s0": s0,
            "actual_st": actual,
            **{k:v for k,v in forecast.items() if k not in {"s0"}},
            **score,
        })
    return pd.DataFrame(rows)
