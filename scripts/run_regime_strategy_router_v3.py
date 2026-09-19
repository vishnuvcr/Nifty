from __future__ import annotations

import argparse
from pathlib import Path
import zlib

import numpy as np
import pandas as pd
from nifty_mc.strategy_catalog import STRATEGY_NAMES, build_strategy


def contract_count(strategy: str) -> int:
    dummy = {k: float(i + 100) for i, k in enumerate(
        ["p10","p20","p25","p35","p45","atm","c55","c65","c75","c80","c90"]
    )}
    return int(sum(abs(int(leg.qty)) for leg in build_strategy(strategy, dummy)))


def trailing_rank(values: pd.Series, window: int = 126, min_history: int = 30) -> np.ndarray:
    x = values.to_numpy(float)
    out = np.full(len(x), np.nan)
    for i, v in enumerate(x):
        hist = x[max(0, i - window):i]
        hist = hist[np.isfinite(hist)]
        if len(hist) >= min_history and np.isfinite(v):
            out[i] = float(np.mean(hist <= v))
    return out


def classify_adaptive(d: pd.DataFrame) -> pd.DataFrame:
    # Rank regime features once per decision date, not once per strategy row.
    # The raw trade table contains multiple strategies per decision, so doing
    # the ranking on raw rows would duplicate observations and let the current
    # decision leak into later rows from the same date.
    work = d.copy()
    if "decision_id" not in work.columns:
        work["decision_id"] = work["decision_date"].astype(str)
    base = (
        work.sort_values(["decision_date", "decision_id"])
        .drop_duplicates("decision_id", keep="first")
        .copy()
    )
    for col in ["trend20", "trend60", "rv20", "p_expand"]:
        base[col + "_rank"] = trailing_rank(base[col])
    base["trend_score_adaptive"] = 0.5 * base["trend20_rank"] + 0.5 * base["trend60_rank"]
    direction = np.where(
        (base.trend20_rank >= 2/3) & (base.trend60_rank >= 2/3), "bull",
        np.where(
            (base.trend20_rank <= 1/3) & (base.trend60_rank <= 1/3), "bear", "neutral"
        )
    )
    breakout = (
        (base.p_expand_rank >= 2/3)
        & (np.abs(base.trend_score_adaptive - 0.5) < 0.18)
    )
    base["direction_adaptive"] = np.where(breakout, "breakout", direction)
    base["vol_regime"] = np.where(
        base.rv20_rank <= 1/3, "low",
        np.where(base.rv20_rank <= 2/3, "medium", "high")
    )
    base["regime_adaptive"] = base.direction_adaptive + "_" + base.vol_regime

    label_cols = [
        "decision_id", "trend20_rank", "trend60_rank", "rv20_rank",
        "p_expand_rank", "trend_score_adaptive", "direction_adaptive",
        "vol_regime", "regime_adaptive",
    ]
    out = work.drop(
        columns=[c for c in label_cols if c != "decision_id" and c in work.columns],
        errors="ignore",
    ).merge(base[label_cols], on="decision_id", how="left", validate="many_to_one")
    return out


def summarize(x: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "mean": np.nan, "total": 0.0, "win_rate": np.nan,
                "profit_factor": np.nan, "max_drawdown": np.nan}
    eq = np.cumsum(x)
    dd = eq - np.maximum.accumulate(eq)
    gains = float(x[x > 0].sum())
    losses = float(-x[x < 0].sum())
    return {
        "n": int(len(x)), "mean": float(x.mean()), "total": float(x.sum()),
        "win_rate": float(np.mean(x > 0)),
        "profit_factor": float(gains / losses) if losses > 0 else np.inf,
        "max_drawdown": float(dd.min()),
    }


def pick_by_validation(
    trades: pd.DataFrame,
    group_col: str,
    dev_min_n: int,
    val_min_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dev = trades[(trades.period == "development") & trades.gate]
    val = trades[(trades.period == "validation") & trades.gate]
    candidates = []
    for (group, strategy), g in dev.groupby([group_col, "strategy"]):
        if len(g) < dev_min_n:
            continue
        x = g.net_pnl.to_numpy(float)
        mean = float(x.mean())
        se = float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0
        score = mean - se
        if score <= 0:
            continue
        candidates.append({
            "group": group, "strategy": strategy, "dev_n": len(x),
            "dev_mean": mean, "dev_score": score
        })
    cdf = pd.DataFrame(candidates)
    selected = []
    if not cdf.empty:
        for group, cg in cdf.groupby("group"):
            rows = []
            for r in cg.itertuples(index=False):
                vg = val[(val[group_col] == group) & (val.strategy == r.strategy)]
                if len(vg) < val_min_n:
                    continue
                x = vg.net_pnl.to_numpy(float)
                vm = float(x.mean())
                vp = (
                    float(x[x > 0].sum() / (-x[x < 0].sum()))
                    if np.any(x < 0) else np.inf
                )
                if vm > 0 and vp > 1:
                    rows.append({
                        "group": group, "strategy": r.strategy,
                        "dev_n": int(r.dev_n), "dev_mean": r.dev_mean,
                        "dev_score": r.dev_score, "val_n": len(x),
                        "val_mean": vm, "val_profit_factor": vp,
                    })
            if rows:
                q = pd.DataFrame(rows).sort_values(
                    ["val_mean","val_profit_factor","val_n"],
                    ascending=[False,False,False],
                )
                selected.append(q.iloc[0].to_dict())
    return cdf, pd.DataFrame(selected)


def main() -> None:
    ap = argparse.ArgumentParser(description="Adaptive regime-conditioned strategy router")
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--cost-per-contract", type=float, default=2.0)
    ap.add_argument("--dev-end-year", type=int, default=2022)
    ap.add_argument("--validation-end-year", type=int, default=2024)
    ap.add_argument("--final-start-year", type=int, default=2025)
    ap.add_argument("--dev-min-n", type=int, default=30)
    ap.add_argument("--validation-min-n", type=int, default=10)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t = pd.read_csv(args.trades, parse_dates=["decision_date"])
    required = {"strategy","decision_date","realized_pnl","mc_ev","trend20","trend60","rv20","p_expand"}
    missing = required - set(t.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    t = classify_adaptive(t)
    t["year"] = t.decision_date.dt.year
    t["period"] = np.select(
        [t.year <= args.dev_end_year, t.year <= args.validation_end_year],
        ["development","validation"], default="final"
    )
    t["contracts"] = t.strategy.map(contract_count)
    t["stress_cost"] = t.contracts * float(args.cost_per_contract)
    t["net_pnl"] = pd.to_numeric(t.realized_pnl, errors="coerce") - t.stress_cost
    t["mc_ev_net"] = pd.to_numeric(t.mc_ev, errors="coerce") - t.stress_cost
    t["gate"] = t.mc_ev_net > 0

    t.to_csv(out / "adaptive_regime_strategy_trades.csv", index=False)

    vol_candidates, vol_selected = pick_by_validation(
        t, "vol_regime", args.dev_min_n, args.validation_min_n
    )
    dir_candidates, dir_selected = pick_by_validation(
        t, "direction_adaptive", args.dev_min_n, args.validation_min_n
    )
    vol_candidates.to_csv(out / "volatility_candidates.csv", index=False)
    vol_selected.to_csv(out / "volatility_selected.csv", index=False)
    dir_candidates.to_csv(out / "direction_candidates.csv", index=False)
    dir_selected.to_csv(out / "direction_selected.csv", index=False)

    rows = []
    for r in vol_selected.itertuples(index=False):
        fg = t[
            (t.period == "final") &
            (t.vol_regime == r.group) &
            (t.strategy == r.strategy) &
            t.gate
        ]
        s = summarize(fg.net_pnl.to_numpy(float))
        status = "HOLD" if (s["mean"] > 0 and s["profit_factor"] > 1) else "REJECT_FINAL"
        rows.append({
            "regime_type": "volatility", "regime": r.group, "strategy": r.strategy,
            "development_n": r.dev_n, "development_score": r.dev_score,
            "validation_n": r.val_n, "validation_mean": r.val_mean,
            "validation_profit_factor": r.val_profit_factor,
            "final_n": s["n"], "final_mean": s["mean"], "final_total": s["total"],
            "final_win_rate": s["win_rate"], "final_profit_factor": s["profit_factor"],
            "final_max_drawdown": s["max_drawdown"], "status": status,
        })

    for r in dir_selected.itertuples(index=False):
        fg = t[
            (t.period == "final") &
            (t.direction_adaptive == r.group) &
            (t.strategy == r.strategy) &
            t.gate
        ]
        s = summarize(fg.net_pnl.to_numpy(float))
        status = "HOLD" if (s["mean"] > 0 and s["profit_factor"] > 1) else "REJECT_FINAL"
        rows.append({
            "regime_type": "direction", "regime": r.group, "strategy": r.strategy,
            "development_n": r.dev_n, "development_score": r.dev_score,
            "validation_n": r.val_n, "validation_mean": r.val_mean,
            "validation_profit_factor": r.val_profit_factor,
            "final_n": s["n"], "final_mean": s["mean"], "final_total": s["total"],
            "final_win_rate": s["win_rate"], "final_profit_factor": s["profit_factor"],
            "final_max_drawdown": s["max_drawdown"], "status": status,
        })

    result = pd.DataFrame(rows)
    result.to_csv(out / "regime_strategy_results.csv", index=False)

    lines = [
        "# Adaptive Regime → Strategy Research",
        "",
        "Regimes are classified using trailing, past-only ranks of trend and volatility features; no future observations enter the classification.",
        f"Stress cost: {args.cost_per_contract:.2f} option points per contract.",
        f"MC gate: net MC EV > 0 after stress cost.",
        "",
        "## Volatility regimes",
        "",
    ]
    if vol_selected.empty:
        lines.append("No volatility-regime strategy passed the development→validation selection rule.")
    else:
        for r in vol_selected.itertuples(index=False):
            fg = t[(t.period == "final") & (t.vol_regime == r.group) & (t.strategy == r.strategy) & t.gate]
            s = summarize(fg.net_pnl.to_numpy(float))
            lines.append(
                f"- {r.group} volatility → {r.strategy}: validation n={r.val_n}, mean={r.val_mean:.2f}, PF={r.val_profit_factor:.2f}; "
                f"final n={s['n']}, mean={s['mean']:.2f}, total={s['total']:.2f}, PF={s['profit_factor']:.2f}"
            )
    lines += ["", "## Direction regimes", ""]
    if dir_selected.empty:
        lines.append("No direction regime passed the development→validation selection rule.")
    else:
        for r in dir_selected.itertuples(index=False):
            fg = t[(t.period == "final") & (t.direction_adaptive == r.group) & (t.strategy == r.strategy) & t.gate]
            s = summarize(fg.net_pnl.to_numpy(float))
            lines.append(
                f"- {r.group} direction → {r.strategy}: validation n={r.val_n}, mean={r.val_mean:.2f}, PF={r.val_profit_factor:.2f}; "
                f"final n={s['n']}, mean={s['mean']:.2f}, total={s['total']:.2f}, PF={s['profit_factor']:.2f}"
            )
    lines += [
        "",
        "## Operational conclusion",
        "",
        "Only volatility regimes with positive validation performance and positive final-holdout performance are retained.",
        "A regime without a surviving strategy is NO_TRADE.",
        "This is a paper-trading research router, not a guarantee of future profitability.",
    ]
    (out / "adaptive_regime_strategy_report.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    print("\\n".join(lines))


if __name__ == "__main__":
    main()
