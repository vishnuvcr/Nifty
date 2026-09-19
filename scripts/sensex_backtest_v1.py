from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import build_strategy

IST = "Asia/Kolkata"
CANDIDATES_BY_REGIME = {
    "low": ["Risk Reversal", "Long Synthetic Future", "Buy Call"],
    "medium": ["Short Straddle", "Put Ratio Spread", "Short Strangle", "Strip", "Buy Put"],
    "high": ["Sell Put", "Risk Reversal", "Long Synthetic Future", "Batman"],
}
CPCV_FREQUENCY = {
    "low": {"Risk Reversal": 9, "Long Synthetic Future": 4, "Buy Call": 2},
    "medium": {"Short Straddle": 4, "Put Ratio Spread": 4, "Short Strangle": 3, "Strip": 3, "Buy Put": 1},
    "high": {"Sell Put": 5, "Risk Reversal": 5, "Long Synthetic Future": 3, "Batman": 2},
}
SPLITS = {
    "development": ("2024-01-01", "2024-12-31"),
    "validation": ("2025-01-01", "2025-12-31"),
    "holdout": ("2026-01-01", "2026-07-31"),
}


def load_index(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["trading_day"] = pd.to_datetime(df["trading_day"], errors="coerce").dt.normalize()
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["timestamp", "trading_day", "close"]).sort_values("timestamp")
    return df


def daily_close(index_1m: pd.DataFrame) -> pd.DataFrame:
    return (
        index_1m.sort_values("timestamp")
        .groupby("trading_day", as_index=False)
        .tail(1)[["trading_day", "close"]]
        .rename(columns={"trading_day": "date"})
        .sort_values("date")
        .reset_index(drop=True)
    )


def log_returns(close_df: pd.DataFrame) -> pd.Series:
    return np.log(close_df["close"]).diff()


def compute_regime(close_df: pd.DataFrame, cutoff: pd.Timestamp, rank_window: int = 252) -> dict[str, float | str]:
    x = close_df.loc[close_df["date"] <= cutoff].copy()
    if len(x) < 100:
        raise ValueError("insufficient index history for regime")
    r = log_returns(x)
    rv20 = r.rolling(20).std(ddof=1) * math.sqrt(252)
    rv20 = rv20.dropna()
    latest = float(rv20.iloc[-1])
    hist = rv20.iloc[:-1].tail(rank_window)
    if len(hist) < min(60, rank_window):
        raise ValueError("insufficient past-only RV20 rank history")
    rank = float(np.mean(hist.to_numpy(float) <= latest))
    regime = "low" if rank <= 1 / 3 else ("medium" if rank <= 2 / 3 else "high")
    return {"rv20": latest, "rv20_rank": rank, "vol_regime": regime}


def mc_terminal(returns: np.ndarray, spot: float, horizon_sessions: int, paths: int, seed: int) -> np.ndarray:
    clean = np.asarray(returns, dtype=float)
    clean = clean[np.isfinite(clean)]
    if len(clean) < 756:
        raise ValueError("need at least 756 historical daily log returns")
    rng = np.random.default_rng(seed)
    sampled = rng.choice(clean[-756:], size=paths * horizon_sessions, replace=True)
    sampled = sampled.reshape(paths, horizon_sessions)
    return spot * np.exp(sampled.sum(axis=1))


def strategy_targets(strategy: str, terminal: np.ndarray, spot: float) -> dict[str, float]:
    p20, p35, p65, p80 = np.percentile(terminal, [20, 35, 65, 80])
    all_targets = {"p20": float(p20), "p35": float(p35), "c65": float(p65), "c80": float(p80), "atm": float(spot)}
    required = {
        "Risk Reversal": ["c65", "p35"],
        "Long Synthetic Future": ["atm"],
        "Buy Call": ["atm"],
        "Short Straddle": ["atm"],
        "Put Ratio Spread": ["atm", "p35"],
        "Short Strangle": ["p35", "c65"],
        "Strip": ["atm"],
        "Buy Put": ["atm"],
        "Sell Put": ["atm"],
        "Batman": ["p20", "p35", "c65", "c80"],
    }
    return {k: all_targets[k] for k in required[strategy]}


def map_unique_strikes(snapshot: pd.DataFrame, targets: dict[str, float]) -> dict[str, float]:
    available = np.sort(snapshot["strike"].dropna().astype(float).unique())
    if len(available) < len(targets):
        raise ValueError("not enough unique strikes")
    out: dict[str, float] = {}
    used: set[float] = set()
    ordered = sorted(targets.items(), key=lambda kv: (0 if kv[0] == "atm" else 1, kv[1]))
    for label, target in ordered:
        found = None
        for idx in np.argsort(np.abs(available - target)):
            v = float(available[idx])
            if v not in used:
                found = v
                break
        if found is None:
            raise ValueError(f"cannot map strike {label}")
        out[label] = found
        used.add(found)
    return out


def parse_expiry(path: Path) -> pd.Timestamp:
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.parquet", path.name)
    if not m:
        raise ValueError(path.name)
    return pd.Timestamp(m.group(1)).normalize()


def load_option_file(path: Path, entry_date: pd.Timestamp) -> pd.DataFrame:
    cols = ["timestamp", "trading_day", "expiry", "strike", "option_type", "open", "close", "volume", "open_interest"]
    x = pd.read_parquet(path)
    for c in cols:
        if c not in x.columns:
            x[c] = np.nan
    x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce")
    x["trading_day"] = pd.to_datetime(x["trading_day"], errors="coerce").dt.normalize()
    x["expiry"] = pd.to_datetime(x["expiry"], errors="coerce").dt.normalize()
    for c in ("strike", "open", "close", "volume", "open_interest"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["option_type"] = x["option_type"].astype(str).str.upper()
    return x.loc[x["trading_day"].eq(entry_date)].dropna(subset=["strike", "open"]).copy()


def entry_row(snapshot: pd.DataFrame, option_type: str, strike: float, entry_ts: str = "09:30:00") -> pd.Series:
    x = snapshot.loc[
        snapshot["option_type"].eq(option_type)
        & np.isclose(snapshot["strike"].to_numpy(float), float(strike), atol=1e-9)
        & snapshot["timestamp"].dt.strftime("%H:%M:%S").eq(entry_ts)
    ]
    if x.empty:
        raise ValueError(f"missing 09:30 bar {option_type} {strike}")
    return x.iloc[0]


def cost_schedule(entry_date: pd.Timestamp) -> dict[str, float]:
    if entry_date < pd.Timestamp("2024-10-01"):
        bse_per_rupee_turnover = 500.0 / 10_000_000.0
    else:
        bse_per_rupee_turnover = 3250.0 / 10_000_000.0
    stt_sell = 0.0015 if entry_date >= pd.Timestamp("2026-04-01") else 0.001
    stt_exercise = 0.0015 if entry_date >= pd.Timestamp("2026-04-01") else 0.00125
    return {
        "brokerage_per_order": 10.0,
        "bse_txn_rate": bse_per_rupee_turnover,
        "stt_sell_rate": stt_sell,
        "stt_exercise_rate": stt_exercise,
        "sebi_rate": 0.000001,
        "stamp_buy_rate": 0.00003,
        "gst_rate": 0.18,
    }


def leg_pricing(
    strategy: str,
    strikes: dict[str, float],
    snapshot: pd.DataFrame,
    expiry: pd.Timestamp,
    lot_size: int,
    slippage_points: float,
) -> tuple[list[dict[str, Any]], float, int]:
    legs = build_strategy(strategy, strikes)
    out = []
    entry_cashflow = 0.0
    contracts = 0
    for leg in legs:
        row = entry_row(snapshot, leg.option_type, leg.strike)
        raw = float(row["open"])
        side = "BUY" if leg.qty > 0 else "SELL"
        if side == "BUY":
            px = raw + slippage_points
        else:
            px = raw - slippage_points
        if px <= 0:
            raise ValueError(f"non-positive executable proxy after slippage: {strategy} {leg.option_type} {leg.strike}")
        entry_cashflow -= float(leg.qty) * px
        q = abs(int(leg.qty))
        contracts += q
        out.append({
            "side": side,
            "option_type": leg.option_type,
            "strike": float(leg.strike),
            "qty": int(leg.qty),
            "quantity_per_lot": q,
            "premium_points": px,
            "raw_open": raw,
            "expiry": str(expiry.date()),
        })
    return out, float(entry_cashflow), contracts


def payoff_distribution(terminal: np.ndarray, legs: list[dict[str, Any]], entry_cashflow: float, lot_size: int) -> np.ndarray:
    pnl = np.full(len(terminal), entry_cashflow, dtype=float)
    for leg in legs:
        intrinsic = (
            np.maximum(terminal - leg["strike"], 0.0)
            if leg["option_type"] == "CE"
            else np.maximum(leg["strike"] - terminal, 0.0)
        )
        pnl += float(leg["qty"]) * intrinsic
    return pnl


def transaction_costs(
    entry_date: pd.Timestamp,
    legs: list[dict[str, Any]],
    lot_size: int,
    entry_cashflow: float,
    terminal: np.ndarray,
) -> tuple[float, float]:
    sched = cost_schedule(entry_date)
    orders = len(legs)
    buy_premium_turnover = sum(max(0, int(l["qty"])) * l["premium_points"] for l in legs) * lot_size
    sell_premium_turnover = sum(max(0, -int(l["qty"])) * l["premium_points"] for l in legs) * lot_size
    total_premium_turnover = buy_premium_turnover + sell_premium_turnover
    brokerage = sched["brokerage_per_order"] * orders
    bse_txn = sched["bse_txn_rate"] * total_premium_turnover
    sebi = sched["sebi_rate"] * total_premium_turnover
    stamp = sched["stamp_buy_rate"] * buy_premium_turnover
    stt_short = sched["stt_sell_rate"] * sell_premium_turnover
    # Long-option exercise STT is stochastic at expiry; compute expected per-lot amount.
    expected_exercise_intrinsic = 0.0
    for leg in legs:
        if int(leg["qty"]) <= 0:
            continue
        intrinsic = (
            np.maximum(terminal - leg["strike"], 0.0)
            if leg["option_type"] == "CE"
            else np.maximum(leg["strike"] - terminal, 0.0)
        )
        expected_exercise_intrinsic += int(leg["qty"]) * float(np.mean(intrinsic)) * lot_size
    stt_exercise_expected = sched["stt_exercise_rate"] * expected_exercise_intrinsic
    gst = sched["gst_rate"] * (brokerage + bse_txn + sebi)
    entry_total = brokerage + bse_txn + sebi + stamp + stt_short + gst
    total_expected = entry_total + stt_exercise_expected
    return float(total_expected), float(entry_total)


def realized_costs(entry_date: pd.Timestamp, legs: list[dict[str, Any]], lot_size: int, expiry_spot: float) -> float:
    sched = cost_schedule(entry_date)
    buy_turn = sum(max(0, int(l["qty"])) * l["premium_points"] for l in legs) * lot_size
    sell_turn = sum(max(0, -int(l["qty"])) * l["premium_points"] for l in legs) * lot_size
    turnover = buy_turn + sell_turn
    brokerage = sched["brokerage_per_order"] * len(legs)
    bse_txn = sched["bse_txn_rate"] * turnover
    sebi = sched["sebi_rate"] * turnover
    stamp = sched["stamp_buy_rate"] * buy_turn
    stt_short = sched["stt_sell_rate"] * sell_turn
    expiry_stt = 0.0
    for leg in legs:
        if int(leg["qty"]) <= 0:
            continue
        intrinsic = (
            max(expiry_spot - leg["strike"], 0.0)
            if leg["option_type"] == "CE"
            else max(leg["strike"] - expiry_spot, 0.0)
        )
        expiry_stt += sched["stt_exercise_rate"] * int(leg["qty"]) * intrinsic * lot_size
    gst = sched["gst_rate"] * (brokerage + bse_txn + sebi)
    return float(brokerage + bse_txn + sebi + stamp + stt_short + gst + expiry_stt)


def summarize_trades(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {"trades": 0, "total_pnl": 0.0, "mean_pnl": 0.0, "median_pnl": 0.0, "win_rate": 0.0, "profit_factor": 0.0, "max_dd": 0.0}
    pnl = pd.to_numeric(trades["realized_pnl_inr"], errors="coerce").fillna(0.0)
    eq = pnl.cumsum()
    dd = eq - eq.cummax()
    gains = float(pnl[pnl > 0].sum())
    losses = float(-pnl[pnl < 0].sum())
    return {
        "trades": int(len(trades)),
        "total_pnl": float(pnl.sum()),
        "mean_pnl": float(pnl.mean()),
        "median_pnl": float(pnl.median()),
        "win_rate": float((pnl > 0).mean()),
        "profit_factor": gains / losses if losses > 0 else math.inf,
        "max_dd": float(dd.min()),
    }


def bootstrap_mean_ci(values: np.ndarray, block: int = 4, n_resamples: int = 20000, seed: int = 20260920) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return (math.nan, math.nan, math.nan)
    if len(values) == 1:
        return (float(values[0]), float(values[0]), 1.0)
    rng = np.random.default_rng(seed)
    means = np.empty(n_resamples, dtype=float)
    starts = np.arange(max(1, len(values) - block + 1))
    for i in range(n_resamples):
        sample = []
        while len(sample) < len(values):
            st = int(rng.choice(starts))
            sample.extend(values[st: st + block].tolist())
        means[i] = float(np.mean(sample[:len(values)]))
    return float(np.mean(values)), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def run_backtest(options_dir: Path, index_path: Path, split_name: str, slippage: float, seed_base: int) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    idx1m = load_index(index_path)
    daily = daily_close(idx1m)
    sessions = pd.DatetimeIndex(daily["date"].unique()).sort_values()
    opt_paths = sorted(options_dir.glob("*.parquet"))
    all_rows: list[dict[str, Any]] = []
    adaptive_primary: list[dict[str, Any]] = []
    start = pd.Timestamp(SPLITS[split_name][0])
    end = pd.Timestamp(SPLITS[split_name][1])
    for path in opt_paths:
        expiry = parse_expiry(path)
        if expiry < start or expiry > end:
            continue
        if expiry not in sessions:
            continue
        idx = int(sessions.get_loc(expiry))
        if idx < 3:
            continue
        entry_date = sessions[idx - 3]
        cutoff = sessions[idx - 4] if idx >= 4 else None
        if cutoff is None or entry_date < start or entry_date > end:
            continue
        try:
            snapshot = load_option_file(path, entry_date)
            entry_ts = pd.Timestamp(f"{entry_date.date()} 09:30:00", tz=IST)
            spot_rows = idx1m.loc[idx1m["timestamp"].eq(entry_ts)]
            if spot_rows.empty:
                # Exact 09:30 is required by the frozen protocol.
                raise ValueError("missing exact 09:30 SENSEX index observation")
            spot = float(spot_rows.iloc[0]["open"])
            cutoff_returns = log_returns(daily.loc[daily["date"] <= cutoff]) .dropna().to_numpy(float)
            if len(cutoff_returns) < 756:
                raise ValueError("insufficient 756-session index history")
            terminal = mc_terminal(cutoff_returns, spot, 3, 5000, seed_base + int(expiry.strftime("%Y%m%d")))
            regime = compute_regime(daily, cutoff, 252)
        except Exception as exc:
            all_rows.append({
                "split": split_name,
                "expiry": str(expiry.date()),
                "entry_date": str(entry_date.date()),
                "strategy": "ALL",
                "status": "NO_TRADE",
                "reason": str(exc),
            })
            continue

        candidate_rows = []
        for strategy in sorted({x for xs in CANDIDATES_BY_REGIME.values() for x in xs}):
            if strategy not in CANDIDATES_BY_REGIME[regime["vol_regime"]]:
                continue
            try:
                targets = strategy_targets(strategy, terminal, spot)
                strikes = map_unique_strikes(snapshot, targets)
                legs, entry_cashflow, contract_count = leg_pricing(strategy, strikes, snapshot, expiry, 20, slippage)
                gross_dist = payoff_distribution(terminal, legs, entry_cashflow, 20)
                expected_cost_inr, entry_cost_inr = transaction_costs(entry_date, legs, 20, entry_cashflow, terminal)
                net_dist = gross_dist - expected_cost_inr / 20.0
                q05 = float(np.quantile(net_dist, 0.05))
                q01 = float(np.quantile(net_dist, 0.01))
                es95 = float(max(0.0, -np.mean(net_dist[net_dist <= q05])))
                es99 = float(max(0.0, -np.mean(net_dist[net_dist <= q01])))
                risk_points = max(es95, es99)
                risk_budget = 100000.0 * 0.02
                est_risk_inr = risk_points * 20
                lots = int(math.floor(risk_budget / est_risk_inr)) if est_risk_inr > 0 else 0
                net_ev = float(np.mean(net_dist))
                eligible = net_ev > 0 and lots >= 1
                reason = "eligible" if eligible else ("negative_net_ev" if net_ev <= 0 else "no_risk_sized_lot")
                candidate_rows.append({
                    "split": split_name,
                    "expiry": str(expiry.date()),
                    "entry_date": str(entry_date.date()),
                    "strategy": strategy,
                    "regime": regime["vol_regime"],
                    "rv20": regime["rv20"],
                    "rv20_rank": regime["rv20_rank"],
                    "spot": spot,
                    "p20": float(np.percentile(terminal,20)),
                    "p35": float(np.percentile(terminal,35)),
                    "p65": float(np.percentile(terminal,65)),
                    "p80": float(np.percentile(terminal,80)),
                    "strikes_json": json.dumps(strikes, sort_keys=True),
                    "entry_cashflow_points": entry_cashflow,
                    "mc_ev_gross": float(np.mean(gross_dist)),
                    "mc_ev_net": net_ev,
                    "mc_pop": float(np.mean(net_dist > 0)),
                    "es95_points": es95,
                    "es99_points": es99,
                    "risk_points_per_lot": risk_points,
                    "risk_budget_inr": risk_budget,
                    "estimated_risk_inr_per_lot": est_risk_inr,
                    "recommended_lots": lots,
                    "contract_count": contract_count,
                    "eligible": eligible,
                    "eligibility_reason": reason,
                    "slippage_points_per_leg": slippage,
                    "entry_cost_inr_expected": expected_cost_inr,
                    "entry_cost_inr_entry_only": entry_cost_inr,
                    "legs_json": json.dumps(legs, sort_keys=True),
                    "cpcv_frequency": CPCV_FREQUENCY[regime["vol_regime"]][strategy],
                    "status": "EVALUATED",
                })
            except Exception as exc:
                candidate_rows.append({
                    "split": split_name,
                    "expiry": str(expiry.date()),
                    "entry_date": str(entry_date.date()),
                    "strategy": strategy,
                    "regime": regime["vol_regime"],
                    "status": "NO_TRADE",
                    "reason": str(exc),
                })
        # Preserve Adaptive candidates exactly as regime-conditioned, while evaluating
        # standalone Batman independently on every eligible expiry/date.
        standalone_batman = [r.copy() for r in candidate_rows if r.get("strategy") == "Batman"]
        if standalone_batman:
            for r in standalone_batman:
                r["universe"] = "Batman_standalone"
        else:
            try:
                targets = strategy_targets("Batman", terminal, spot)
                strikes = map_unique_strikes(snapshot, targets)
                legs, entry_cashflow, contract_count = leg_pricing("Batman", strikes, snapshot, expiry, 20, slippage)
                gross_dist = payoff_distribution(terminal, legs, entry_cashflow, 20)
                expected_cost_inr, entry_cost_inr = transaction_costs(entry_date, legs, 20, entry_cashflow, terminal)
                net_dist = gross_dist - expected_cost_inr / 20.0
                q05 = float(np.quantile(net_dist, 0.05))
                q01 = float(np.quantile(net_dist, 0.01))
                es95 = float(max(0.0, -np.mean(net_dist[net_dist <= q05])))
                es99 = float(max(0.0, -np.mean(net_dist[net_dist <= q01])))
                risk_points = max(es95, es99)
                risk_budget = 100000.0 * 0.02
                est_risk_inr = risk_points * 20
                lots = int(math.floor(risk_budget / est_risk_inr)) if est_risk_inr > 0 else 0
                net_ev = float(np.mean(net_dist))
                standalone_batman = [{
                    "split": split_name,
                    "expiry": str(expiry.date()),
                    "entry_date": str(entry_date.date()),
                    "strategy": "Batman",
                    "regime": regime["vol_regime"],
                    "rv20": regime["rv20"],
                    "rv20_rank": regime["rv20_rank"],
                    "spot": spot,
                    "p20": float(np.percentile(terminal,20)),
                    "p35": float(np.percentile(terminal,35)),
                    "p65": float(np.percentile(terminal,65)),
                    "p80": float(np.percentile(terminal,80)),
                    "strikes_json": json.dumps(strikes, sort_keys=True),
                    "entry_cashflow_points": entry_cashflow,
                    "mc_ev_gross": float(np.mean(gross_dist)),
                    "mc_ev_net": net_ev,
                    "mc_pop": float(np.mean(net_dist > 0)),
                    "es95_points": es95,
                    "es99_points": es99,
                    "risk_points_per_lot": risk_points,
                    "risk_budget_inr": risk_budget,
                    "estimated_risk_inr_per_lot": est_risk_inr,
                    "recommended_lots": lots,
                    "contract_count": contract_count,
                    "eligible": net_ev > 0 and lots >= 1,
                    "eligibility_reason": "eligible" if (net_ev > 0 and lots >= 1) else ("negative_net_ev" if net_ev <= 0 else "no_risk_sized_lot"),
                    "slippage_points_per_leg": slippage,
                    "entry_cost_inr_expected": expected_cost_inr,
                    "entry_cost_inr_entry_only": entry_cost_inr,
                    "legs_json": json.dumps(legs, sort_keys=True),
                    "cpcv_frequency": 0,
                    "status": "STANDALONE_EVALUATED",
                    "universe": "Batman_standalone",
                }]
            except Exception as exc:
                standalone_batman = [{
                    "split": split_name,
                    "expiry": str(expiry.date()),
                    "entry_date": str(entry_date.date()),
                    "strategy": "Batman",
                    "regime": regime["vol_regime"],
                    "status": "NO_TRADE",
                    "reason": str(exc),
                    "universe": "Batman_standalone",
                }]

        all_rows.extend(candidate_rows)
        all_rows.extend(standalone_batman)
        eligible_rows = [r for r in candidate_rows if bool(r.get("eligible"))]
        primary = sorted(eligible_rows, key=lambda r: (-float(r["mc_ev_net"]), -int(r["cpcv_frequency"]), str(r["strategy"])))[0] if eligible_rows else None
        if primary is not None:
            leg_list = json.loads(primary["legs_json"])
            expiry_idx = idx1m.loc[idx1m["trading_day"].eq(expiry)]
            if expiry_idx.empty:
                continue
            expiry_spot = float(expiry_idx.sort_values("timestamp").iloc[-1]["close"])
            net_points = float(sum(int(l["qty"]) * (max(expiry_spot - float(l["strike"]), 0.0) if l["option_type"] == "CE" else max(float(l["strike"]) - expiry_spot, 0.0)) for l in leg_list) + float(primary["entry_cashflow_points"]))
            lots = int(primary["recommended_lots"])
            realized_cost = realized_costs(entry_date, leg_list, 20, expiry_spot)
            realized_net_inr = net_points * 20 * lots - realized_cost * lots
            trade = dict(primary)
            trade.update({
                "exit_spot": expiry_spot,
                "realized_pnl_points_per_unit": net_points,
                "realized_pnl_inr": realized_net_inr,
                "primary_strategy": primary["strategy"],
                "signal": "ENTER",
                "status": "CLOSED",
                "lots": lots,
            })
            adaptive_primary.append(trade)
        else:
            adaptive_primary.append({
                "split": split_name,
                "expiry": str(expiry.date()),
                "entry_date": str(entry_date.date()),
                "regime": regime["vol_regime"],
                "signal": "NO_TRADE",
                "status": "NO_TRADE",
            })
    candidates = pd.DataFrame(all_rows)
    trades = pd.DataFrame(adaptive_primary)
    stats = summarize_trades(trades.loc[trades.get("status", pd.Series(dtype=str)).eq("CLOSED")]) if not trades.empty else summarize_trades(pd.DataFrame())
    if not trades.empty and "realized_pnl_inr" in trades.columns:
        vals = pd.to_numeric(trades["realized_pnl_inr"], errors="coerce").dropna().to_numpy(float)
        m, lo, hi = bootstrap_mean_ci(vals)
        stats.update({"bootstrap_mean": m, "bootstrap_mean_ci_low": lo, "bootstrap_mean_ci_high": hi})
    return candidates, trades, stats


def run_batman_from_candidates(candidates: pd.DataFrame, options_dir: Path, index_path: Path, split_name: str, slippage: float, seed_base: int) -> pd.DataFrame:
    # Batman is part of the high-volatility candidate set. We re-evaluate the frozen Batman gate on every high-regime entry date.
    rows = candidates.loc[(candidates["split"] == split_name) & (candidates["strategy"] == "Batman")].copy()
    if rows.empty:
        return pd.DataFrame()
    idx1m = load_index(index_path)
    out = []
    for _, row in rows.iterrows():
        if row.get("status") != "EVALUATED" or not bool(row.get("eligible")):
            continue
        expiry = pd.Timestamp(row["expiry"])
        entry = pd.Timestamp(row["entry_date"])
        leg_list = json.loads(row["legs_json"])
        expiry_idx = idx1m.loc[idx1m["trading_day"].eq(expiry)]
        if expiry_idx.empty:
            continue
        expiry_spot = float(expiry_idx.sort_values("timestamp").iloc[-1]["close"])
        net_points = float(sum(int(l["qty"]) * (max(expiry_spot - float(l["strike"]), 0.0) if l["option_type"] == "CE" else max(float(l["strike"]) - expiry_spot, 0.0)) for l in leg_list) + float(row["entry_cashflow_points"]))
        lots = int(row["recommended_lots"])
        realized_cost = realized_costs(entry, leg_list, 20, expiry_spot)
        realized_net_inr = net_points * 20 * lots - realized_cost * lots
        rr = dict(row)
        rr.update({"realized_pnl_points_per_unit": net_points, "realized_pnl_inr": realized_net_inr, "lots": lots, "signal": "ENTER", "status": "CLOSED"})
        out.append(rr)
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--options-dir", required=True)
    ap.add_argument("--index-path", required=True)
    ap.add_argument("--split", choices=list(SPLITS), required=True)
    ap.add_argument("--slippage", type=float, default=0.5)
    ap.add_argument("--seed-base", type=int, default=20260920)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates, adaptive_trades, stats = run_backtest(Path(args.options_dir), Path(args.index_path), args.split, args.slippage, args.seed_base)
    candidates.to_csv(out_dir / f"candidates_{args.split}.csv", index=False)
    adaptive_trades.to_csv(out_dir / f"adaptive_trades_{args.split}.csv", index=False)
    batman = run_batman_from_candidates(candidates, Path(args.options_dir), Path(args.index_path), args.split, args.slippage, args.seed_base)
    batman.to_csv(out_dir / f"batman_trades_{args.split}.csv", index=False)
    summary = {"split": args.split, "slippage_points_per_leg": args.slippage, "adaptive": stats, "batman": summarize_trades(batman)}
    (out_dir / f"summary_{args.split}.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
