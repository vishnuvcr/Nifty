from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import STRATEGY_NAMES, build_strategy

MIN_DEV_N = 30
MIN_VAL_N = 10
OPERATING_COST = 2.0
OUTER_YEARS = (2023, 2024, 2025)
FINAL_HOLDOUT_YEAR = 2026


def contract_count(strategy: str) -> int:
    dummy = {
        "p10": 100.0, "p20": 101.0, "p25": 102.0, "p35": 103.0,
        "p45": 104.0, "atm": 105.0, "c55": 106.0, "c65": 107.0,
        "c75": 108.0, "c80": 109.0, "c90": 110.0,
    }
    return int(sum(abs(int(leg.qty)) for leg in build_strategy(strategy, dummy)))


CONTRACTS = {name: contract_count(name) for name in STRATEGY_NAMES}


def profit_factor(values: np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    gains = float(x[x > 0].sum())
    losses = float(-x[x < 0].sum())
    return gains / losses if losses > 0 else np.inf


def summary(values: np.ndarray) -> dict[str, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {
            "n": 0, "mean": np.nan, "total": 0.0, "pf": np.nan,
            "win_rate": np.nan, "max_drawdown": np.nan,
        }
    eq = np.cumsum(x)
    dd = eq - np.maximum.accumulate(eq)
    return {
        "n": int(len(x)),
        "mean": float(x.mean()),
        "total": float(x.sum()),
        "pf": float(profit_factor(x)),
        "win_rate": float(np.mean(x > 0)),
        "max_drawdown": float(dd.min()),
    }


def trailing_rank(values: pd.Series, window: int, min_history: int = 30) -> np.ndarray:
    arr = values.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)
    for i, value in enumerate(arr):
        hist = arr[max(0, i - window):i]
        hist = hist[np.isfinite(hist)]
        if len(hist) >= min_history and np.isfinite(value):
            out[i] = float(np.mean(hist <= value))
    return out


def add_regimes(df: pd.DataFrame, lookback: int, qlo: float, qhi: float) -> pd.DataFrame:
    work = df.copy()
    if "decision_id" not in work.columns:
        work["decision_id"] = work["decision_date"].astype(str)

    required = ["decision_id", "decision_date", "trend20", "trend60", "rv20", "p_expand"]
    missing = [c for c in required if c not in work.columns]
    if missing:
        raise ValueError(f"Missing regime columns: {missing}")

    base = (
        work.sort_values(["decision_date", "decision_id"])
        .drop_duplicates("decision_id", keep="first")
        .copy()
    )
    for col in ["trend20", "trend60", "rv20", "p_expand"]:
        base[f"{col}_rank"] = trailing_rank(base[col], lookback)

    base["trend_score_rank"] = 0.5 * base["trend20_rank"] + 0.5 * base["trend60_rank"]
    base["direction_regime"] = np.where(
        (base["trend20_rank"] >= qhi) & (base["trend60_rank"] >= qhi),
        "bull",
        np.where(
            (base["trend20_rank"] <= qlo) & (base["trend60_rank"] <= qlo),
            "bear",
            "neutral",
        ),
    )
    breakout = (
        (base["p_expand_rank"] >= qhi)
        & (np.abs(base["trend_score_rank"] - 0.5) < 0.18)
    )
    base.loc[breakout, "direction_regime"] = "breakout"
    base["vol_regime"] = np.where(
        base["rv20_rank"] <= qlo,
        "low",
        np.where(base["rv20_rank"] <= qhi, "medium", "high"),
    )

    label_cols = [
        "decision_id", "trend20_rank", "trend60_rank", "rv20_rank",
        "p_expand_rank", "trend_score_rank", "direction_regime", "vol_regime",
    ]
    return (
        work.drop(
            columns=[c for c in label_cols if c != "decision_id" and c in work.columns],
            errors="ignore",
        )
        .merge(base[label_cols], on="decision_id", how="left", validate="many_to_one")
    )


def prepare_panel(df: pd.DataFrame, regime_col: str, cost: float) -> pd.DataFrame:
    x = df.copy()
    x["contracts"] = x["strategy"].map(CONTRACTS).astype(float)
    x["stress_cost"] = x["contracts"] * float(cost)
    x["net_pnl"] = pd.to_numeric(x["realized_pnl"], errors="coerce") - x["stress_cost"]
    x["net_mc_ev"] = pd.to_numeric(x["mc_ev"], errors="coerce") - x["stress_cost"]
    x["gate"] = np.isfinite(x["net_pnl"]) & np.isfinite(x["net_mc_ev"]) & (x["net_mc_ev"] > 0)
    x["regime"] = x[regime_col]
    return x


def select_mapping(dev: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    dev = dev[dev["gate"]].copy()
    validation = validation[validation["gate"]].copy()
    rows: list[dict] = []

    for regime, rg in dev.groupby("regime"):
        candidates = []
        for strategy, g in rg.groupby("strategy"):
            if len(g) < MIN_DEV_N:
                continue
            vals = g["net_pnl"].to_numpy(float)
            se = float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            dev_mean = float(vals.mean())
            dev_score = dev_mean - se
            if dev_score <= 0:
                continue

            vg = validation[
                (validation["regime"] == regime)
                & (validation["strategy"] == strategy)
                & validation["gate"]
            ]
            if len(vg) < MIN_VAL_N:
                continue
            v = vg["net_pnl"].to_numpy(float)
            vmean = float(v.mean())
            vpf = float(profit_factor(v))
            if vmean <= 0 or vpf <= 1:
                continue

            candidates.append(
                {
                    "regime": str(regime),
                    "strategy": str(strategy),
                    "dev_n": int(len(vals)),
                    "dev_mean": dev_mean,
                    "dev_score": dev_score,
                    "validation_n": int(len(v)),
                    "validation_mean": vmean,
                    "validation_pf": vpf,
                }
            )

        if candidates:
            q = pd.DataFrame(candidates).sort_values(
                ["validation_mean", "validation_pf", "validation_n", "dev_score"],
                ascending=[False, False, False, False],
            )
            rows.append(q.iloc[0].to_dict())

    return pd.DataFrame(rows)


def apply_mapping(test: pd.DataFrame, mapping: pd.DataFrame, cost: float) -> pd.DataFrame:
    x = prepare_panel(test, "vol_regime", cost)  # regime is overwritten below
    if "regime" not in mapping.columns or mapping.empty:
        return pd.DataFrame()
    parts = []
    for row in mapping.itertuples(index=False):
        z = x[
            (x["regime"] == row.regime)
            & (x["strategy"] == row.strategy)
            & x["gate"]
        ].copy()
        if z.empty:
            continue
        z["selected_regime"] = row.regime
        z["selected_strategy"] = row.strategy
        parts.append(z)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def test_mapping(panel: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for row in mapping.itertuples(index=False):
        z = panel[
            (panel["regime"] == row.regime)
            & (panel["strategy"] == row.strategy)
            & panel["gate"]
        ].copy()
        if z.empty:
            continue
        z["selected_regime"] = row.regime
        z["selected_strategy"] = row.strategy
        parts.append(z)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def mapping_stability(selections: list[pd.DataFrame]) -> pd.DataFrame:
    regimes = ["low", "medium", "high"]
    rows = []
    for regime in regimes:
        seen = []
        for fold_no, sel in enumerate(selections, start=1):
            hit = sel[sel["regime"] == regime]
            if not hit.empty:
                seen.append((fold_no, str(hit.iloc[0]["strategy"])))
        counts = Counter(strategy for _, strategy in seen)
        stable_strategy = "NO_TRADE"
        stable_count = 0
        if counts:
            stable_strategy, stable_count = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
        rows.append(
            {
                "regime": regime,
                "stable_strategy": stable_strategy,
                "selected_folds": len(seen),
                "stable_count": int(stable_count),
                "detail": ";".join(f"fold{f}:{s}" for f, s in seen),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_ci(values: np.ndarray, seed: int = 12345, n_boot: int = 10000) -> dict[str, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return {"boot_mean": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    rng = np.random.default_rng(seed)
    means = np.mean(rng.choice(x, size=(n_boot, len(x)), replace=True), axis=1)
    return {
        "boot_mean": float(means.mean()),
        "ci_low": float(np.quantile(means, 0.025)),
        "ci_high": float(np.quantile(means, 0.975)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--lookbacks", nargs="+", type=int, default=[63, 126, 252])
    ap.add_argument(
        "--quantile-pairs",
        nargs="+",
        default=["0.25,0.75", "0.3333333333,0.6666666667", "0.20,0.80"],
    )
    ap.add_argument("--outer-years", nargs="+", type=int, default=list(OUTER_YEARS))
    ap.add_argument("--holdout-year", type=int, default=FINAL_HOLDOUT_YEAR)
    ap.add_argument("--operating-cost", type=float, default=OPERATING_COST)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t = pd.read_csv(args.trades, parse_dates=["decision_date"])
    t["decision_date"] = pd.to_datetime(t["decision_date"]).dt.normalize()
    t["year"] = t["decision_date"].dt.year
    expected = set(STRATEGY_NAMES)
    actual = set(t["strategy"].dropna().astype(str).unique())
    if actual != expected:
        raise SystemExit(
            f"Strategy universe mismatch: expected {len(expected)}, found {len(actual)}, "
            f"missing={sorted(expected-actual)}, extra={sorted(actual-expected)}"
        )

    t = t.sort_values(["decision_date", "decision_id", "strategy"]).reset_index(drop=True)

    all_param_rows = []
    all_fold_rows = []
    all_selection_rows = []

    for lookback in args.lookbacks:
        for pair in args.quantile_pairs:
            qlo, qhi = map(float, pair.split(","))
            if not 0 < qlo < qhi < 1:
                raise SystemExit(f"Invalid quantile pair: {pair}")

            x = add_regimes(t, lookback, qlo, qhi)
            panel = prepare_panel(x, "vol_regime", args.operating_cost)

            fold_selections = []
            fold_metrics = []
            for test_year in args.outer_years:
                dev = panel[panel["year"] <= test_year - 2]
                val = panel[panel["year"] == test_year - 1]
                test = panel[panel["year"] == test_year]

                mapping = select_mapping(dev, val)
                fold_selections.append(mapping)

                if mapping.empty:
                    fold_metrics.append(
                        {
                            "lookback": lookback, "qlo": qlo, "qhi": qhi,
                            "test_year": test_year, "selected_regimes": 0,
                            "stable_mapping_placeholder": "",
                            "test_n": 0, "test_mean": np.nan, "test_pf": np.nan,
                            "test_total": 0.0, "positive_regime_count": 0,
                        }
                    )
                    continue

                for r in mapping.itertuples(index=False):
                    all_selection_rows.append(
                        {
                            "lookback": lookback, "qlo": qlo, "qhi": qhi,
                            "test_year": test_year, **r._asdict()
                        }
                    )

                selected = test_mapping(test, mapping)
                s = summary(selected["net_pnl"].to_numpy(float) if not selected.empty else np.array([]))
                positive = 0
                regime_parts = []
                for regime, rg in selected.groupby("selected_regime"):
                    rs = summary(rg["net_pnl"].to_numpy(float))
                    positive += int(rs["mean"] > 0 and rs["pf"] > 1)
                    regime_parts.append(
                        {
                            "lookback": lookback, "qlo": qlo, "qhi": qhi,
                            "test_year": test_year, "regime": regime,
                            "strategy": str(rg["selected_strategy"].iloc[0]),
                            **{f"test_{k}": v for k, v in rs.items()},
                        }
                    )
                all_fold_rows.extend(regime_parts)

                fold_metrics.append(
                    {
                        "lookback": lookback, "qlo": qlo, "qhi": qhi,
                        "test_year": test_year,
                        "selected_regimes": int(len(mapping)),
                        "test_n": int(s["n"]), "test_mean": s["mean"],
                        "test_pf": s["pf"], "test_total": s["total"],
                        "positive_regime_count": int(positive),
                    }
                )

            m = mapping_stability(fold_selections)
            stable_active = int((m["stable_count"] >= 2).sum())
            flat_metrics = pd.DataFrame(fold_metrics)
            finite = flat_metrics.dropna(subset=["test_mean"])
            aggregate_n = int(finite["test_n"].sum()) if not finite.empty else 0

            # The outer 2023-2025 test folds are model-selection data for the
            # final 2026 holdout. They may choose hyperparameters, but 2026 is
            # never used below until the final frozen evaluation.
            pooled = []
            for test_year in args.outer_years:
                dev = panel[panel["year"] <= test_year - 2]
                val = panel[panel["year"] == test_year - 1]
                mapping = select_mapping(dev, val)
                if mapping.empty:
                    continue
                z = test_mapping(panel[panel["year"] == test_year], mapping)
                if not z.empty:
                    pooled.append(z["net_pnl"].to_numpy(float))
            pooled_values = np.concatenate(pooled) if pooled else np.array([])
            pooled_summary = summary(pooled_values)

            positive_years = int(
                sum(
                    row["test_n"] >= 1 and np.isfinite(row["test_mean"]) and row["test_mean"] > 0
                    for row in fold_metrics
                )
            )
            pass_filter = (
                aggregate_n >= 15
                and pooled_summary["mean"] > 0
                and pooled_summary["pf"] > 1
                and positive_years >= 2
                and stable_active >= 1
            )

            all_param_rows.append(
                {
                    "lookback": lookback, "qlo": qlo, "qhi": qhi,
                    "pooled_n": pooled_summary["n"],
                    "pooled_mean": pooled_summary["mean"],
                    "pooled_pf": pooled_summary["pf"],
                    "pooled_total": pooled_summary["total"],
                    "positive_outer_years": positive_years,
                    "stable_active_regimes": stable_active,
                    "aggregate_n": aggregate_n,
                    "passes_pre2026_selection": bool(pass_filter),
                }
            )

            with open(out / "selection_trace.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"setting lookback={lookback} qlo={qlo:.6f} qhi={qhi:.6f} "
                    f"pooled_n={pooled_summary['n']} pooled_mean={pooled_summary['mean']:.6f} "
                    f"pooled_pf={pooled_summary['pf']:.6f} stable_active={stable_active} "
                    f"pass={pass_filter}\n"
                )

    params = pd.DataFrame(all_param_rows)
    folds = pd.DataFrame(all_fold_rows)
    selections = pd.DataFrame(all_selection_rows)
    params.to_csv(out / "nested_parameter_results.csv", index=False)
    folds.to_csv(out / "nested_outer_fold_results.csv", index=False)
    selections.to_csv(out / "nested_outer_fold_selections.csv", index=False)

    eligible = params[params["passes_pre2026_selection"]].copy()
    if eligible.empty:
        # Preserve an explicit no-candidate result and still evaluate a
        # pre-declared reference setting so the workflow ends with useful data.
        chosen = params.sort_values(
            ["pooled_mean", "pooled_pf", "stable_active_regimes"],
            ascending=[False, False, False],
        ).iloc[0]
        selection_status = "NO_PRE2026_ROBUST_SETTING"
    else:
        chosen = eligible.sort_values(
            ["pooled_mean", "pooled_pf", "stable_active_regimes", "pooled_n"],
            ascending=[False, False, False, False],
        ).iloc[0]
        selection_status = "PRE2026_SETTING_SELECTED"

    best_lookback = int(chosen["lookback"])
    best_qlo = float(chosen["qlo"])
    best_qhi = float(chosen["qhi"])

    final_regime_panel = prepare_panel(
        add_regimes(t, best_lookback, best_qlo, best_qhi),
        "vol_regime",
        args.operating_cost,
    )
    final_dev = final_regime_panel[final_regime_panel["year"] <= args.holdout_year - 2]
    final_val = final_regime_panel[final_regime_panel["year"] == args.holdout_year - 1]
    final_holdout = final_regime_panel[final_regime_panel["year"] == args.holdout_year]

    final_mapping = select_mapping(final_dev, final_val)
    final_mapping = final_mapping.copy()
    if not final_mapping.empty:
        final_mapping["lookback"] = best_lookback
        final_mapping["qlo"] = best_qlo
        final_mapping["qhi"] = best_qhi
    final_mapping.to_csv(out / "final_frozen_mapping.csv", index=False)

    final_test = test_mapping(final_holdout, final_mapping)
    holdout_summary = summary(
        final_test["net_pnl"].to_numpy(float) if not final_test.empty else np.array([])
    )
    ci = bootstrap_ci(
        final_test["net_pnl"].to_numpy(float) if not final_test.empty else np.array([])
    )

    holdout_by_regime = []
    for regime in ["low", "medium", "high"]:
        z = final_test[final_test["selected_regime"] == regime] if not final_test.empty else pd.DataFrame()
        s = summary(z["net_pnl"].to_numpy(float) if not z.empty else np.array([]))
        strategy = (
            str(z["selected_strategy"].iloc[0]) if not z.empty else
            (str(final_mapping.loc[final_mapping["regime"] == regime, "strategy"].iloc[0])
             if not final_mapping.loc[final_mapping["regime"] == regime].empty else "NO_TRADE")
        )
        holdout_by_regime.append({"regime": regime, "strategy": strategy, **s})

    stress_rows = []
    stress_panel_base = add_regimes(t, best_lookback, best_qlo, best_qhi)
    for cost in [1.0, 2.0, 3.0, 4.0]:
        stress_panel = prepare_panel(stress_panel_base, "vol_regime", cost)
        z = test_mapping(stress_panel[stress_panel["year"] == args.holdout_year], final_mapping)
        s = summary(z["net_pnl"].to_numpy(float) if not z.empty else np.array([]))
        stress_rows.append({"cost": cost, **s})
    stress = pd.DataFrame(stress_rows)
    stress.to_csv(out / "holdout_cost_stress.csv", index=False)
    pd.DataFrame(holdout_by_regime).to_csv(out / "final_holdout_by_regime.csv", index=False)

    stability = mapping_stability(
        [
            select_mapping(
                prepare_panel(
                    add_regimes(t[t["year"] <= y - 2], best_lookback, best_qlo, best_qhi),
                    "vol_regime",
                    args.operating_cost,
                ),
                prepare_panel(
                    add_regimes(t[t["year"] == y - 1], best_lookback, best_qlo, best_qhi),
                    "vol_regime",
                    args.operating_cost,
                ),
            )
            for y in args.outer_years
        ]
    )
    stability.to_csv(out / "chosen_setting_mapping_stability.csv", index=False)

    # Also test a direction-only lens using the exact same frozen parameter
    # setting, with no parameter re-selection on 2026.
    direction_panel = prepare_panel(
        add_regimes(t, best_lookback, best_qlo, best_qhi),
        "direction_regime",
        args.operating_cost,
    )
    direction_dev = direction_panel[direction_panel["year"] <= args.holdout_year - 2]
    direction_val = direction_panel[direction_panel["year"] == args.holdout_year - 1]
    direction_mapping = select_mapping(direction_dev, direction_val)
    direction_mapping.to_csv(out / "final_direction_mapping.csv", index=False)
    direction_holdout = test_mapping(
        direction_panel[direction_panel["year"] == args.holdout_year],
        direction_mapping,
    )
    direction_summary = summary(
        direction_holdout["net_pnl"].to_numpy(float)
        if not direction_holdout.empty else np.array([])
    )

    lines = [
        "# Nested Regime-Strategy Discovery v1",
        "",
        f"Source: strategy-regime-lab-v2 run 35425922439 (all 36 strategies).",
        "",
        "Protocol:",
        "- Decision-level, past-only trailing ranks; no strategy-row duplication in regime features.",
        "- All 36 strategies remain in the candidate pool.",
        "- Outer 2023/2024/2025 folds are used for model-selection of regime parameters.",
        "- For each outer fold: development <= test_year-2; validation = test_year-1; test = test_year.",
        "- Candidate strategy gate: net MC EV > 0 after operating transaction-cost stress.",
        f"- Strategy selection: development n >= {MIN_DEV_N}, development mean-SE > 0; validation n >= {MIN_VAL_N}, validation mean > 0 and PF > 1.",
        "- 2026 is untouched until the final frozen evaluation.",
        "",
        "## Pre-2026 nested selection",
        "",
        f"- Operating stress cost: {args.operating_cost:.1f} points/contract.",
        f"- Selected lookback: {best_lookback}.",
        f"- Selected quantiles: {best_qlo:.3f} / {best_qhi:.3f}.",
        f"- Selection status: {selection_status}.",
        f"- Pre-2026 pooled outer-fold mean: {chosen['pooled_mean']:.2f}.",
        f"- Pre-2026 pooled outer-fold PF: {chosen['pooled_pf']:.2f}.",
        f"- Pre-2026 pooled outer-fold trades: {int(chosen['pooled_n'])}.",
        f"- Pre-2026 positive outer years: {int(chosen['positive_outer_years'])}/3.",
        f"- Stable active regimes (same strategy in >=2/3 folds): {int(chosen['stable_active_regimes'])}.",
        "",
        "## Final mapping frozen without 2026",
        "",
    ]

    if final_mapping.empty:
        lines.append("No regime passed the development/2025 validation criteria; the final router is NO_TRADE.")
    else:
        for _, r in final_mapping.iterrows():
            lines.append(
                f"- {r['regime']} -> {r['strategy']} "
                f"(dev n={int(r['dev_n'])}, validation n={int(r['validation_n'])}, "
                f"validation mean={r['validation_mean']:.2f}, validation PF={r['validation_pf']:.2f})"
            )

    lines += [
        "",
        "## Untouched 2026 holdout",
        "",
        f"- Trades: {holdout_summary['n']}",
        f"- Mean: {holdout_summary['mean']:.2f}",
        f"- PF: {holdout_summary['pf']:.2f}",
        f"- Total: {holdout_summary['total']:.2f}",
        f"- Win rate: {holdout_summary['win_rate']:.2%}",
        f"- Max drawdown: {holdout_summary['max_drawdown']:.2f}",
        f"- Bootstrap mean 95% CI: {ci['ci_low']:.2f} to {ci['ci_high']:.2f}",
        "",
        "### 2026 by volatility regime",
        "",
    ]
    for r in holdout_by_regime:
        lines.append(
            f"- {r['regime']} -> {r['strategy']}: n={int(r['n'])}, mean={r['mean']:.2f}, "
            f"PF={r['pf']:.2f}, total={r['total']:.2f}"
        )

    lines += [
        "",
        "### Cost stress on the same frozen 2026 mapping",
        "",
    ]
    for _, r in stress.iterrows():
        lines.append(
            f"- cost={r.cost:.0f}: n={int(r.n)}, mean={r.mean:.2f}, PF={r.pf:.2f}, total={r.total:.2f}"
        )

    lines += [
        "",
        "## Direction-only secondary lens",
        "",
        f"- 2026 trades: {direction_summary['n']}",
        f"- Mean: {direction_summary['mean']:.2f}",
        f"- PF: {direction_summary['pf']:.2f}",
        f"- Total: {direction_summary['total']:.2f}",
        "",
        "Interpretation:",
        "- A 2026 result is descriptive holdout evidence, not a prediction.",
        "- A router is not promoted unless the strategy mapping is supported by pre-2026 nested selection and the untouched holdout remains positive under the declared gate.",
        "- If the holdout fails these checks, keep the producer observation-only and continue research rather than changing rules after seeing 2026.",
    ]

    (out / "nested_regime_strategy_discovery_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
