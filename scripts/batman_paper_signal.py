from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import build_strategy

REQUIRED_COLUMNS = {"timestamp", "expiry", "strike", "option_type", "close"}


def mc_terminal(spot: float, returns: np.ndarray, horizon_sessions: int, paths: int, seed: int) -> np.ndarray:
    r = returns[np.isfinite(returns)]
    if len(r) < 60:
        raise ValueError("At least 60 historical returns are required for Monte Carlo.")
    rng = np.random.default_rng(seed)
    h = max(1, int(horizon_sessions))
    sampled = rng.choice(r, size=paths * h, replace=True).reshape(paths, h)
    return spot * np.exp(sampled.sum(axis=1))


def unique_strikes(strikes: np.ndarray, targets: dict[str, float]) -> dict[str, float]:
    s = np.sort(np.unique(np.asarray(strikes, dtype=float)))
    used: set[float] = set()
    out: dict[str, float] = {}
    for label, target in sorted(targets.items(), key=lambda kv: kv[1]):
        order = np.argsort(np.abs(s - target))
        pick = None
        for i in order:
            v = float(s[i])
            if v not in used:
                pick = v
                break
        if pick is None:
            raise ValueError(f"Unable to assign a unique strike for {label}.")
        out[label] = pick
        used.add(pick)
    return out


def option_price(chain: pd.DataFrame, expiry: pd.Timestamp, typ: str, strike: float) -> float:
    x = chain[
        (chain.expiry == expiry)
        & (chain.option_type == typ)
        & (chain.strike == float(strike))
    ]
    if x.empty:
        raise ValueError(f"Missing {typ} {strike} for expiry {expiry.date()}.")
    px = float(pd.to_numeric(x.iloc[0].close, errors="coerce"))
    if not np.isfinite(px) or px <= 0:
        raise ValueError(f"Invalid premium for {typ} {strike}.")
    return px


def payoff_paths(terminal: np.ndarray, priced: list[tuple[object, float]]) -> tuple[np.ndarray, float]:
    pnl = np.zeros(len(terminal), dtype=float)
    entry = 0.0
    for leg, px in priced:
        intrinsic = np.maximum(
            (terminal - leg.strike) if leg.option_type == "CE" else (leg.strike - terminal),
            0.0,
        )
        pnl += leg.qty * intrinsic
        entry -= leg.qty * px
    return pnl + entry, float(entry)


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper-trading signal generator for the research Batman strategy.")
    ap.add_argument("--index", required=True, help="CSV with date,close columns.")
    ap.add_argument("--chain", required=True, help="CSV with one or more NIFTY option-chain snapshots.")
    ap.add_argument("--decision-date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--expiry", help="Target front expiry YYYY-MM-DD. Defaults to nearest expiry >= decision date.")
    ap.add_argument("--capital", type=float, required=True, help="Paper-trading capital in INR.")
    ap.add_argument("--risk-pct", type=float, default=0.02, help="Risk budget per trade as fraction of capital.")
    ap.add_argument("--lot-size", type=int, default=65, help="NIFTY lot size. Override when contract specifies another lot.")
    ap.add_argument("--paths", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    idx = pd.read_csv(args.index, parse_dates=["date"]).sort_values("date")
    idx["close"] = pd.to_numeric(idx["close"], errors="coerce")
    idx = idx.dropna(subset=["date", "close"]).drop_duplicates("date").reset_index(drop=True)
    idx["date"] = idx.date.dt.normalize()
    decision = pd.Timestamp(args.decision_date).normalize()

    sessions = pd.DatetimeIndex(idx.date.unique()).sort_values()
    prior = sessions[sessions <= decision]
    if len(prior) < 757:
        raise ValueError("Need at least 757 index sessions before the decision date.")
    spot = float(idx.loc[idx.date == decision, "close"].iloc[0])

    chain = pd.read_csv(args.chain, low_memory=False)
    missing = REQUIRED_COLUMNS - set(chain.columns)
    if missing:
        raise ValueError(f"Option chain is missing columns: {sorted(missing)}")
    chain["timestamp"] = pd.to_datetime(chain.timestamp, errors="coerce").dt.normalize()
    chain["expiry"] = pd.to_datetime(chain.expiry, errors="coerce").dt.normalize()
    chain["strike"] = pd.to_numeric(chain.strike, errors="coerce")
    chain["close"] = pd.to_numeric(chain.close, errors="coerce")
    chain["option_type"] = chain.option_type.astype(str).str.upper()
    chain = chain[
        chain.option_type.isin(["CE", "PE"])
        & chain.strike.notna()
        & chain.close.notna()
        & chain.timestamp.eq(decision)
    ].copy()
    if chain.empty:
        raise ValueError("No option-chain rows found for the decision date.")

    expiries = sorted(pd.to_datetime(chain.expiry.dropna().unique()))
    target_expiry = pd.Timestamp(args.expiry).normalize() if args.expiry else None
    if target_expiry is None:
        future = [e for e in expiries if e >= decision]
        if not future:
            raise ValueError("No future expiry is present in the supplied chain.")
        target_expiry = pd.Timestamp(future[0]).normalize()
    if target_expiry not in expiries:
        raise ValueError(f"Expiry {target_expiry.date()} is not present in the supplied chain.")

    future_sessions = sessions[(sessions > decision) & (sessions <= target_expiry)]
    if len(future_sessions) != 3:
        raise ValueError(
            f"This candidate is fixed to 3 trading sessions before expiry; found "
            f"{len(future_sessions)} sessions to {target_expiry.date()}."
        )

    returns = np.log(idx.loc[idx.date <= decision, "close"]).diff().dropna().tail(756).to_numpy(float)
    terminal = mc_terminal(spot, returns, len(future_sessions), args.paths, args.seed)

    qs = np.percentile(terminal, [20, 35, 65, 80])
    targets = {"p20": qs[0], "p35": qs[1], "c65": qs[2], "c80": qs[3]}
    strikes = unique_strikes(chain[chain.expiry == target_expiry].strike.dropna().unique(), targets)

    chain_exp = chain[chain.expiry == target_expiry]
    # The research strategy is:
    # +1 PE(p35), -2 PE(p20), +1 CE(c65), -2 CE(c80)
    legs = build_strategy(
        "Batman",
        {
            "p20": strikes["p20"],
            "p35": strikes["p35"],
            "p45": strikes["p35"],
            "atm": spot,
            "c55": strikes["c65"],
            "c65": strikes["c65"],
            "c75": strikes["c80"],
            "c80": strikes["c80"],
            "p10": strikes["p20"],
            "c90": strikes["c80"],
        },
    )

    priced: list[tuple[object, float]] = []
    for leg in legs:
        priced.append((leg, option_price(chain_exp, target_expiry, leg.option_type, leg.strike)))

    pnl_paths, entry_cashflow = payoff_paths(terminal, priced)
    mc_ev = float(np.mean(pnl_paths))
    mc_pop = float(np.mean(pnl_paths > 0))
    es95 = float(max(0.0, -np.mean(pnl_paths[pnl_paths <= np.quantile(pnl_paths, 0.05)])))
    es99 = float(max(0.0, -np.mean(pnl_paths[pnl_paths <= np.quantile(pnl_paths, 0.01)])))
    entry_contracts = int(sum(abs(leg.qty) for leg, _ in priced))
    risk_points = max(es95, es99)
    risk_per_lot = risk_points * int(args.lot_size)
    risk_budget = float(args.capital) * float(args.risk_pct)
    lots = int(np.floor(risk_budget / risk_per_lot)) if risk_per_lot > 0 else 0
    required_capital = risk_per_lot / float(args.risk_pct) if args.risk_pct > 0 else np.inf

    signal = "ENTER" if mc_ev > 0 and lots >= 1 else "NO_TRADE"

    legs_out = []
    for leg, px in priced:
        legs_out.append(
            {
                "side": "BUY" if leg.qty > 0 else "SELL",
                "option_type": leg.option_type,
                "strike": float(leg.strike),
                "quantity_per_lot": abs(int(leg.qty)),
                "expiry": str(target_expiry.date()),
                "premium_points": float(px),
            }
        )

    result = {
        "strategy": "Batman",
        "decision_date": str(decision.date()),
        "entry_rule": "3 trading sessions before nearest eligible expiry",
        "target_expiry": str(target_expiry.date()),
        "spot": spot,
        "strikes": strikes,
        "mc_expected_pnl_points_per_lot_unit": mc_ev,
        "mc_probability_profit": mc_pop,
        "mc_es95_points": es95,
        "mc_es99_points": es99,
        "contract_lot_size": int(args.lot_size),
        "contracts_per_strategy_lot": entry_contracts,
        "risk_points_per_lot": risk_points,
        "risk_budget_inr": risk_budget,
        "estimated_risk_inr_per_strategy_lot": risk_per_lot,
        "minimum_capital_for_one_strategy_lot_inr": required_capital,
        "recommended_lots": lots,
        "signal": signal,
        "entry_cashflow_points_per_strategy_unit": entry_cashflow,
        "legs": legs_out,
        "risk_note": "Batman has unbounded theoretical tail loss; ES95/ES99 sizing is a risk-control proxy, not a hard maximum-loss guarantee.",
    }
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
