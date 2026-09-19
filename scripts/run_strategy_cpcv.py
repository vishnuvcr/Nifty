from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import STRATEGY_NAMES, build_strategy


def contract_count(strategy: str) -> int:
    dummy = {
        k: float(i + 100.0)
        for i, k in enumerate(
            ["p10", "p20", "p25", "p35", "p45", "atm", "c55", "c65", "c75", "c80", "c90"]
        )
    }
    return int(sum(abs(int(leg.qty)) for leg in build_strategy(strategy, dummy)))


def summary(x: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "mean": np.nan, "total": 0.0, "win_rate": np.nan,
                "profit_factor": np.nan, "max_drawdown": np.nan, "min_trade": np.nan}
    eq = np.cumsum(x)
    dd = eq - np.maximum.accumulate(eq)
    gains = float(x[x > 0].sum())
    losses = float(-x[x < 0].sum())
    return {
        "n": int(len(x)), "mean": float(np.mean(x)), "total": float(np.sum(x)),
        "win_rate": float(np.mean(x > 0)),
        "profit_factor": float(gains / losses) if losses > 0 else np.inf,
        "max_drawdown": float(np.min(dd)), "min_trade": float(np.min(x)),
    }


def iid_bootstrap_prob_positive(x: np.ndarray, n_iter: int, seed: int) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return np.nan
    rng = np.random.default_rng(seed)
    sims = rng.choice(x, size=(n_iter, len(x)), replace=True).sum(axis=1)
    return float(np.mean(sims > 0))


def moving_block_bootstrap_prob_positive(
    x: np.ndarray, n_iter: int, block_len: int, seed: int
) -> float:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return np.nan
    block_len = max(1, min(int(block_len), n))
    starts = np.arange(n - block_len + 1)
    rng = np.random.default_rng(seed)
    positive = 0
    for _ in range(int(n_iter)):
        sample = []
        while len(sample) < n:
            start = int(rng.choice(starts))
            sample.extend(x[start : start + block_len].tolist())
        positive += int(np.sum(sample[:n]) > 0)
    return positive / float(n_iter)


def main() -> None:
    ap = argparse.ArgumentParser(description="Leakage-resistant all-strategy CPCV screen")
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--cost-per-contract", type=float, default=2.0)
    ap.add_argument("--dev-end-year", type=int, default=2024)
    ap.add_argument("--final-start-year", type=int, default=2025)
    ap.add_argument("--n-groups", type=int, default=6)
    ap.add_argument("--test-groups", type=int, default=2)
    ap.add_argument("--min-train-trades", type=int, default=10)
    ap.add_argument("--bootstrap", type=int, default=10000)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t = pd.read_csv(args.trades, parse_dates=["decision_date"])
    required = {"strategy", "decision_date", "realized_pnl", "mc_ev"}
    missing = required - set(t.columns)
    if missing:
        raise SystemExit(f"missing required columns: {sorted(missing)}")

    t["strategy"] = t["strategy"].astype(str)
    t["year"] = t["decision_date"].dt.year
    t["contracts"] = t["strategy"].map(contract_count)
    if t["contracts"].isna().any():
        raise SystemExit("Unknown strategy found in strategy_trades.csv")

    t["stress_cost"] = t["contracts"] * float(args.cost_per_contract)
    t["net_pnl"] = pd.to_numeric(t["realized_pnl"], errors="coerce") - t["stress_cost"]
    t["mc_ev_net"] = pd.to_numeric(t["mc_ev"], errors="coerce") - t["stress_cost"]
    t["gate_pass"] = t["mc_ev_net"] > 0

    prefinal = t[t.year < args.final_start_year].copy()
    if prefinal.empty:
        raise SystemExit("No pre-final observations available.")
    dates = np.array(sorted(prefinal.decision_date.dt.normalize().unique()))
    if len(dates) < args.n_groups:
        raise SystemExit("Not enough unique decision dates for CPCV grouping.")

    date_groups = np.array_split(dates, args.n_groups)
    group_map = {d: i for i, grp in enumerate(date_groups) for d in grp}
    prefinal["cpcv_group"] = prefinal.decision_date.dt.normalize().map(group_map)

    split_rows = []
    for test_groups in itertools.combinations(range(args.n_groups), args.test_groups):
        test_set = set(test_groups)
        train = prefinal[(~prefinal.cpcv_group.isin(test_set)) & prefinal.gate_pass].copy()
        test = prefinal[prefinal.cpcv_group.isin(test_set) & prefinal.gate_pass].copy()

        candidates = []
        for strategy, g in train.groupby("strategy", sort=True):
            x = g.net_pnl.to_numpy(float)
            if len(x) < args.min_train_trades:
                continue
            mean = float(np.mean(x))
            se = float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0
            candidates.append({"strategy": strategy, "train_n": int(len(x)), "train_mean": mean, "train_score": mean - se})
        cdf = pd.DataFrame(candidates)
        positive = cdf[cdf.train_score > 0].sort_values(["train_score", "train_n"], ascending=[False, False]) if not cdf.empty else cdf

        if positive.empty:
            chosen, chosen_train_n, chosen_train_score = "NO_TRADE", 0, np.nan
        else:
            row = positive.iloc[0]
            chosen, chosen_train_n, chosen_train_score = str(row.strategy), int(row.train_n), float(row.train_score)

        ts = test.loc[test.strategy.eq(chosen), "net_pnl"].to_numpy(float) if chosen != "NO_TRADE" else np.array([], dtype=float)
        s = summary(ts)
        split_rows.append({
            "test_groups": "-".join(map(str, test_groups)),
            "chosen_strategy": chosen,
            "train_n": chosen_train_n,
            "train_score": chosen_train_score,
            "test_n": s["n"], "test_mean": s["mean"], "test_total": s["total"],
            "test_win_rate": s["win_rate"], "test_profit_factor": s["profit_factor"],
        })

    splits = pd.DataFrame(split_rows)
    splits.to_csv(out / "cpcv_splits.csv", index=False)

    selected_splits = splits[splits.chosen_strategy != "NO_TRADE"]
    if selected_splits.empty:
        selection = pd.DataFrame()
    else:
        selection = (
            selected_splits.groupby("chosen_strategy")
            .agg(
                selection_count=("chosen_strategy", "size"),
                cpcv_test_mean=("test_mean", "mean"),
                cpcv_test_median=("test_mean", "median"),
                cpcv_positive_test_rate=("test_mean", lambda x: float(np.mean(x > 0))),
                cpcv_total_mean=("test_total", "mean"),
            )
            .reset_index()
        )
        selection["selection_rate"] = selection.selection_count / max(len(splits), 1)
        selection = selection.sort_values(
            ["selection_count", "cpcv_positive_test_rate", "cpcv_test_median"],
            ascending=[False, False, False],
        )
    selection.to_csv(out / "cpcv_selection_summary.csv", index=False)

    final = t[t.year >= args.final_start_year].copy()
    final_rows = []
    for strategy in STRATEGY_NAMES:
        g = final[(final.strategy == strategy) & final.gate_pass]
        x = g.net_pnl.to_numpy(float)
        final_rows.append({
            "strategy": strategy,
            **{f"final_{k}": v for k, v in summary(x).items()},
            "iid_bootstrap_p_positive": iid_bootstrap_prob_positive(
                x, args.bootstrap, 100000 + abs(hash(strategy)) % 100000
            ),
            "mbb3_p_positive": moving_block_bootstrap_prob_positive(
                x, max(1000, args.bootstrap // 2), 3, 200000 + abs(hash(strategy)) % 100000
            ),
            "mbb5_p_positive": moving_block_bootstrap_prob_positive(
                x, max(1000, args.bootstrap // 2), 5, 300000 + abs(hash(strategy)) % 100000
            ),
            "mbb10_p_positive": moving_block_bootstrap_prob_positive(
                x, max(1000, args.bootstrap // 2), 10, 400000 + abs(hash(strategy)) % 100000
            ),
        })
    final_df = pd.DataFrame(final_rows)
    final_df.to_csv(out / "final_holdout_all_strategies.csv", index=False)

    if selection.empty:
        text = "# All-Strategy MC-EV-Gated CPCV\n\nNo strategy was selected by the CPCV folds.\n"
        (out / "strategy_cpcv_report.md").write_text(text, encoding="utf-8")
        print(text)
        return

    selected = str(selection.iloc[0].chosen_strategy)
    hold = final_df[final_df.strategy.eq(selected)].iloc[0]
    report = f"""# All-Strategy MC-EV-Gated CPCV

Fixed entry gate: net MC EV > 0 after {args.cost_per_contract:.2f} stress points per contract.
CPCV: {args.n_groups} contiguous groups, {args.test_groups} held out per split, {len(splits)} splits.
Training minimum: {args.min_train_trades} gated trades per strategy.

## CPCV selection

Most frequently selected strategy: {selected}
Selection: {int(selection.iloc[0].selection_count)}/{len(splits)} ({selection.iloc[0].selection_rate:.1%})
Positive CPCV test-mean rate: {selection.iloc[0].cpcv_positive_test_rate:.1%}
Median CPCV test mean: {selection.iloc[0].cpcv_test_median:.2f}

## Final holdout ({args.final_start_year}+)

Gated trades: {int(hold.final_n)}
Mean net P&L/trade: {hold.final_mean:.2f}
Total net P&L: {hold.final_total:.2f}
Win rate: {hold.final_win_rate:.1%}
Profit factor: {hold.final_profit_factor:.2f}
Max drawdown: {hold.final_max_drawdown:.2f}
Minimum trade: {hold.final_min_trade:.2f}
IID bootstrap P(total > 0): {hold.iid_bootstrap_p_positive:.3f}
MBB(3) P(total > 0): {hold.mbb3_p_positive:.3f}
MBB(5) P(total > 0): {hold.mbb5_p_positive:.3f}
MBB(10) P(total > 0): {hold.mbb10_p_positive:.3f}

This is a research robustness screen, not a guarantee of future profitability.
"""
    (out / "strategy_cpcv_report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
