from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import numpy as np
import pandas as pd

from .gbm import simulate_terminal_gbm
from .volatility import realized_vol
from .trend import classify_trend
from .evaluation import interval_metrics, crps_empirical, directional_brier


@dataclass(frozen=True)
class ForecastOrigin:
    decision_date: pd.Timestamp
    expiry_date: pd.Timestamp


def log_returns(close: pd.Series) -> pd.Series:
    s = pd.Series(close, dtype=float).sort_index().dropna()
    if (s <= 0).any():
        raise ValueError("close prices must be positive")
    return np.log(s).diff().dropna()


def make_forecast(
    s0: float,
    horizon_trading_days: int,
    returns_history: pd.Series,
    vol_window: int = 20,
    drift_window: int = 60,
    n_paths: int = 50_000,
    seed: int = 0,
    history_is_log_returns: bool = False,
):
    """Forecast from a history of closes or explicitly supplied log returns."""
    lr = (
        pd.Series(returns_history, dtype=float).dropna()
        if history_is_log_returns
        else log_returns(returns_history)
    )
    if len(lr) < 2:
        raise ValueError("insufficient return history")
    sigma = realized_vol(lr, window=vol_window)
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("estimated volatility must be positive")
    recent = lr.tail(drift_window)
    mu = float(recent.mean() * 252.0)
    t = max(1, int(horizon_trading_days)) / 252.0
    samples = simulate_terminal_gbm(s0, t, mu, sigma, n_paths=n_paths, seed=seed)
    trend = classify_trend(samples, s0)
    q_levels = [.01, .05, .10, .25, .50, .75, .90, .95, .99]
    q = np.quantile(samples, q_levels)
    out = {"s0": float(s0), "sigma": float(sigma), "mu": float(mu),
           "horizon_trading_days": int(horizon_trading_days)}
    out.update({f"p{int(p*100):02d}": float(v) for p, v in zip(q_levels, q)})
    out.update(trend)
    return out, samples


def evaluate_prediction(actual_st: float, samples: np.ndarray, s0: float) -> dict:
    out = interval_metrics(actual_st, samples)
    out["actual_st"] = float(actual_st)
    out["realized_move"] = float(actual_st / s0 - 1.0)
    out["crps"] = crps_empirical(actual_st, samples)
    out["brier_up"] = directional_brier(actual_st, samples, s0)
    return out


def trading_days_to_expiry(index: pd.DatetimeIndex, decision: pd.Timestamp,
                           expiry: pd.Timestamp) -> int:
    """Count observed market sessions strictly after decision through expiry."""
    idx = pd.DatetimeIndex(index).normalize()
    d, e = pd.Timestamp(decision).normalize(), pd.Timestamp(expiry).normalize()
    return int(((idx > d) & (idx <= e)).sum())


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
    """Chronological OOS evaluation. Each forecast only sees data <= decision."""
    df = prices.copy()
    df.index = pd.to_datetime(df.index).normalize()
    df = df.sort_index()
    rows = []

    for i, origin in enumerate(expiry_schedule):
        decision = pd.Timestamp(origin.decision_date).normalize()
        expiry = pd.Timestamp(origin.expiry_date).normalize()
        if expiry <= decision:
            continue
        hist = df.loc[df.index <= decision, price_col].dropna()
        future = df.loc[(df.index > decision) & (df.index <= expiry), price_col].dropna()
        if len(hist) < min_history or future.empty:
            continue
        s0 = float(hist.iloc[-1])
        actual = float(future.iloc[-1])
        horizon = trading_days_to_expiry(df.index, decision, expiry)
        if horizon < 1:
            continue
        forecast, samples = make_forecast(
            s0, horizon, hist, vol_window, drift_window,
            n_paths=n_paths, seed=seed + i,
        )
        score = evaluate_prediction(actual, samples, s0)
        rows.append({
            "decision_date": decision,
            "expiry_date": expiry,
            "s0": s0,
            "actual_st": actual,
            **{k: v for k, v in forecast.items() if k != "s0"},
            **score,
        })
    return pd.DataFrame(rows)
