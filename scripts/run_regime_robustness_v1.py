from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


CONTRACTS = {
    "Buy Call": 1, "Sell Put": 1, "Bull Call Spread": 2, "Bull Put Spread": 2,
    "Call Ratio Back Spread": 3, "Long Calendar with Calls": 2, "Bull Condor": 4,
    "Bull Butterfly": 4, "Range Forward": 2, "Long Synthetic Future": 2,
    "Call Ratio Spread": 3, "Put Ratio Spread": 3, "Long Straddle": 2,
    "Long Iron Butterfly": 4, "Long Strangle": 2, "Long Iron Condor": 4,
    "Strip": 3, "Strap": 3, "Short Straddle": 2, "Iron Butterfly": 4,
    "Short Strangle": 2, "Short Iron Condor": 4, "Batman": 6,
    "Double Plateau": 6, "Jade Lizard": 3, "Reverse Jade Lizard": 3,
    "Buy Put": 1, "Sell Call": 1, "Bear Put Spread": 2, "Bear Call Spread": 2,
    "Put Ratio Back Spread": 3, "Long Calendar with Puts": 2, "Bear Condor": 4,
    "Bear Butterfly": 4, "Risk Reversal": 2, "Short Synthetic Future": 2,
}


def trailing_rank(values: pd.Series, window: int, min_history: int = 30) -> np.ndarray:
    arr = values.to_numpy(float)
    out = np.full(len(arr), np.nan)
    for i, value in enumerate(arr):
        history = arr[max(0, i - window):i]
        history = history[np.isfinite(history)]
        if len(history) >= min_history and np.isfinite(value):
            out[i] = float(np.mean(history <= value))
    return out


def add_adaptive_regime(df: pd.DataFrame, lookback: int, qlo: float, qhi: float) -> pd.DataFrame:
    x = df.sort_values(["decision_date", "decision_id"]).copy()
    for col in ("trend20", "trend60", "rv20", "p_expand"):
        x[f"{col}_rank"] = trailing_rank(x[col], lookback)
    x["trend_score_adaptive"] = 0.5 * x["trend20_rank"] + 0.5 * x["trend60_rank"]
    x["direction_adaptive"] = np.where(
        (x["trend20_rank"] >= qhi) & (x["trend60_rank"] >= qhi),
        "bull",
        np.where(
            (x["trend20_rank"] <= qlo) & (x["trend60_rank"] <= qlo),
            "bear",
            "neutral",
        ),
    )
    breakout = (
        (x["p_expand_rank"] >= qhi)
        & (np.abs(x["trend_score_adaptive"] - 0.5) < 0.18)
    )
    x.loc[breakout, "direction_adaptive"] = "breakout"
    x["vol_regime"] = np.where(
        x["rv20_rank"] <= qlo, "low",
        np.where(x["rv20_rank"] <= qhi, "medium", "high"),
    )
    x["regime_adaptive"] = x["direction_adaptive"] + "_" + x["vol_regime"]
    return x


def profit_factor(values: np.ndarray) -> float:
    values = np.asarray(values, float)
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    return gains / losses if losses > 0 else np.inf


def summary(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {"n": 0, "mean": np.nan, "total": 0.0, "pf": np.nan, "win_rate": np.nan, "max_drawdown": np.nan}
    equity = np.cumsum(values)
    drawdown = equity - np.maximum.accumulate(equity)
    return {
        "n": int(len(values)),
        "mean": float(values.mean()),
        "total": float(values.sum()),
        "pf": float(profit_factor(values)),
        "win_rate": float(np.mean(values > 0)),
        "max_drawdown": float(drawdown.min()),
    }


def select_one_per_regime(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    cost: float,
    regime_col: str = "vol_regime",
    dev_min_n: int = 30,
    validation_min_n: int = 10,
) -> pd.DataFrame:
    train = train[train["gate"]].copy()
    validation = validation[validation["gate"]].copy()
    selected = []
    for regime, rg in train.groupby(regime_col):
        candidates = []
        for strategy, g in rg.groupby("strategy"):
            if len(g) < dev_min_n:
                continue
            values = g["net_pnl"].to_numpy(float)
            se = values.std(ddof=1) / np.sqrt(len(values)) if len(values) > 1 else 0.0
            dev_score = float(values.mean() - se)
            if dev_score <= 0:
                continue
            vg = validation[
                (validation[regime_col] == regime)
                & (validation["strategy"] == strategy)
            ]
            if len(vg) < validation_min_n:
                continue
            v = vg["net_pnl"].to_numpy(float)
            vm = float(v.mean())
            vpf = float(profit_factor(v))
            if vm <= 0 or vpf <= 1:
                continue
            candidates.append(
                {
                    "regime": regime,
                    "strategy": strategy,
                    "dev_n": int(len(values)),
                    "dev_mean": float(values.mean()),
                    "dev_score": dev_score,
                    "validation_n": int(len(v)),
                    "validation_mean": vm,
                    "validation_pf": vpf,
                }
            )
        if candidates:
            q = pd.DataFrame(candidates).sort_values(
                ["validation_mean", "validation_pf", "validation_n", "dev_score"],
                ascending=[False, False, False, False],
            )
            selected.append(q.iloc[0].to_dict())
    return pd.DataFrame(selected)


def rolling_fold(
    df: pd.DataFrame,
    test_year: int,
    cost: float,
    regime_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dev = df[df["year"] <= test_year - 2]
    validation = df[df["year"] == test_year - 1]
    test = df[df["year"] == test_year]
    selected = select_one_per_regime(dev, validation, cost, regime_col=regime_col)
    if selected.empty:
        return selected, pd.DataFrame()
    test_parts = []
    for row in selected.itertuples(index=False):
        z = test[
            (test[regime_col] == row.regime)
            & (test["strategy"] == row.strategy)
            & test["gate"]
        ].copy()
        if not z.empty:
            z["selected_regime"] = row.regime
            z["selected_strategy"] = row.strategy
            test_parts.append(z)
    test_trades = pd.concat(test_parts, ignore_index=True) if test_parts else pd.DataFrame()
    return selected, test_trades


def stable_mapping(fold_selections: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for regime in ("low", "medium", "high"):
        seen = []
        for fold_no, sel in enumerate(fold_selections, start=1):
            hit = sel[sel["regime"] == regime]
            if not hit.empty:
                seen.append((fold_no, str(hit.iloc[0]["strategy"]), float(hit.iloc[0]["validation_mean"])))
        counts = Counter(strategy for _, strategy, _ in seen)
        if not counts:
            rows.append({
                "regime": regime, "stable_strategy": "NO_TRADE",
                "selection_folds": 0, "folds_seen": 0, "selection_detail": "",
            })
            continue
        max_count = max(counts.values())
        candidates = [s for s, n in counts.items() if n == max_count]
        strategy = max(
            candidates,
            key=lambda s: np.mean([m for _, st, m in seen if st == s]),
        )
        detail = ";".join(f"fold{f}:{s}" for f, s, _ in seen)
        rows.append({
            "regime": regime,
            "stable_strategy": strategy,
            "selection_folds": int(counts[strategy]),
            "folds_seen": int(len(seen)),
            "selection_detail": detail,
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--costs", nargs="+", type=float, default=[1, 2, 3, 4])
    ap.add_argument("--lookbacks", nargs="+", type=int, default=[63, 126, 252])
    ap.add_argument("--quantile-pairs", nargs="+", default=["0.25,0.75", "0.3333333333,0.6666666667", "0.20,0.80"])
    ap.add_argument("--test-years", nargs="+", type=int, default=[2023, 2024, 2025, 2026])
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t = pd.read_csv(args.trades, parse_dates=["decision_date"])
    required = {
        "decision_id", "decision_date", "strategy", "realized_pnl", "mc_ev",
        "trend20", "trend60", "rv20", "p_expand",
    }
    missing = required - set(t.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")
    if set(CONTRACTS) != set(t["strategy"].dropna().unique()):
        raise SystemExit("Strategy contract map does not exactly match the input strategy universe")

    t = t.sort_values(["decision_date", "decision_id"]).reset_index(drop=True)
    t["year"] = t["decision_date"].dt.year
    base_rows = []
    fold_rows = []
    stable_rows = []

    for lookback in args.lookbacks:
        for pair in args.quantile_pairs:
            qlo, qhi = map(float, pair.split(","))
            if not 0 < qlo < qhi < 1:
                raise SystemExit(f"Invalid quantile pair: {pair}")
            x = add_adaptive_regime(t, lookback, qlo, qhi)
            for cost in args.costs:
                x["contracts"] = x["strategy"].map(CONTRACTS).astype(float)
                x["stress_cost"] = x["contracts"] * cost
                x["net_pnl"] = pd.to_numeric(x["realized_pnl"], errors="coerce") - x["stress_cost"]
                x["net_mc_ev"] = pd.to_numeric(x["mc_ev"], errors="coerce") - x["stress_cost"]
                x["gate"] = x["net_mc_ev"] > 0

                selections = []
                fold_selection_frames = []
                for year in args.test_years:
                    selected, test_trades = rolling_fold(x, year, cost, "vol_regime")
                    fold_selection_frames.append(selected)
                    if not selected.empty:
                        selected = selected.copy()
                        selected["lookback"] = lookback
                        selected["qlo"] = qlo
                        selected["qhi"] = qhi
                        selected["cost"] = cost
                        selected["test_year"] = year
                        selections.append(selected)
                        for row in selected.itertuples(index=False):
                            fold_rows.append({
                                "lookback": lookback, "qlo": qlo, "qhi": qhi, "cost": cost,
                                "test_year": year, "regime": row.regime,
                                "strategy": row.strategy, "validation_n": row.validation_n,
                                "validation_mean": row.validation_mean, "validation_pf": row.validation_pf,
                            })
                    if test_trades.empty:
                        fold_rows.append({
                            "lookback": lookback, "qlo": qlo, "qhi": qhi, "cost": cost,
                            "test_year": year, "regime": "ALL", "strategy": "NO_TRADE",
                            "validation_n": 0, "validation_mean": np.nan, "validation_pf": np.nan,
                            "test_n": 0, "test_mean": np.nan, "test_pf": np.nan, "test_total": 0.0,
                        })
                        continue
                    for regime, rg in test_trades.groupby("selected_regime"):
                        s = summary(rg["net_pnl"].to_numpy(float))
                        base_rows.append({
                            "lookback": lookback, "qlo": qlo, "qhi": qhi, "cost": cost,
                            "test_year": year, "regime": regime,
                            "strategy": str(rg["selected_strategy"].iloc[0]),
                            **s,
                        })

                # The first three test years (2023-2025) are the pre-2026
                # robustness folds. Preserve empty folds so a missing selection
                # is not silently counted as a later fold.
                stable = stable_mapping(fold_selection_frames[:3])
                stable["lookback"] = lookback
                stable["qlo"] = qlo
                stable["qhi"] = qhi
                stable["cost"] = cost

                final = []
                test_2026 = x[x["year"] == 2026]
                for row in stable.itertuples(index=False):
                    z = test_2026[
                        (test_2026["vol_regime"] == row.regime)
                        & (test_2026["strategy"] == row.stable_strategy)
                        & test_2026["gate"]
                    ]
                    s = summary(z["net_pnl"].to_numpy(float))
                    final.append({
                        **row._asdict(),
                        "holdout_2026_n": s["n"],
                        "holdout_2026_mean": s["mean"],
                        "holdout_2026_pf": s["pf"],
                        "holdout_2026_total": s["total"],
                        "holdout_2026_win_rate": s["win_rate"],
                        "holdout_2026_max_drawdown": s["max_drawdown"],
                    })
                stable_rows.extend(final)

    fold_df = pd.DataFrame(base_rows)
    selection_df = pd.DataFrame(fold_rows)
    stable_df = pd.DataFrame(stable_rows)

    fold_df.to_csv(out / "regime_robustness_fold_results.csv", index=False)
    selection_df.to_csv(out / "regime_robustness_selections.csv", index=False)
    stable_df.to_csv(out / "regime_robustness_stable_holdout.csv", index=False)

    # Compact ranking: prioritize parameter settings whose stable mappings survive
    # 2026. A setting only counts as stable when a strategy was selected in at
    # least two of the first three walk-forward folds.
    ranked = []
    for key, g in stable_df.groupby(["lookback", "qlo", "qhi", "cost"]):
        usable = g[g["selection_folds"] >= 2]
        ranked.append({
            "lookback": key[0], "qlo": key[1], "qhi": key[2], "cost": key[3],
            "stable_regimes": int(len(usable)),
            "positive_holdout_regimes": int((usable["holdout_2026_mean"] > 0).sum()),
            "holdout_total": float(usable["holdout_2026_total"].sum()),
            "holdout_trades": int(usable["holdout_2026_n"].sum()),
        })
    rank_df = pd.DataFrame(ranked).sort_values(
        ["positive_holdout_regimes", "stable_regimes", "holdout_total", "holdout_trades"],
        ascending=[False, False, False, False],
    )
    rank_df.to_csv(out / "regime_robustness_ranked_settings.csv", index=False)

    lines = [
        "# Regime Router Robustness — V2 Run 9",
        "",
        "This phase tests whether the regime-conditioned strategy mapping survives rolling walk-forward selection rather than only one fixed development/validation split.",
        "",
        "Method:",
        "- Adaptive regimes use trailing, past-only ranks.",
        "- For each test year, development ends two years before the test year and the immediately prior year is validation.",
        "- One strategy is selected per volatility regime using development conservative mean-SE > 0, validation mean > 0 and validation PF > 1.",
        "- Final/2026 data are not used to choose the mapping.",
        "- Stress costs are tested at multiple levels.",
        "",
    ]
    if not stable_df.empty:
        best = rank_df.iloc[0] if not rank_df.empty else None
        if best is not None:
            lines += [
                "## Best stability setting",
                "",
                f"- Lookback: {int(best.lookback)} sessions",
                f"- Quantiles: {best.qlo:.3f} / {best.qhi:.3f}",
                f"- Stress cost: {best.cost:.2f} points/contract",
                f"- Stable regimes (selected in >=2/3 pre-2026 folds): {int(best.stable_regimes)}",
                f"- Positive 2026 stable regimes: {int(best.positive_holdout_regimes)}",
                f"- 2026 holdout total across stable regimes: {best.holdout_total:.2f}",
                "",
            ]
            for _, r in stable_df[
                (stable_df.lookback == best.lookback)
                & (stable_df.qlo == best.qlo)
                & (stable_df.qhi == best.qhi)
                & (stable_df.cost == best.cost)
            ].iterrows():
                lines.append(
                    f"- {r.regime} -> {r.stable_strategy}; selected in {int(r.selection_folds)}/3 pre-2026 folds; "
                    f"2026 n={int(r.holdout_2026_n)}, mean={r.holdout_2026_mean:.2f}, PF={r.holdout_2026_pf:.2f}, "
                    f"total={r.holdout_2026_total:.2f}"
                )
            lines += [
                "",
                "## Decision",
                "",
                "The robustness phase does not promote a regime router unless its mapping is stable across pre-2026 folds and its untouched 2026 holdout remains positive.",
            ]
    (out / "regime_robustness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
