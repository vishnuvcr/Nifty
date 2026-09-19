from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from run_regime_robustness_v1 import CONTRACTS, add_adaptive_regime, profit_factor, summary


BASE_STRATEGIES = {
    "high": "Short Strangle",
    "medium": "Sell Put",
}

DEFAULT_LOOKBACKS = [63, 126, 252]
DEFAULT_P_EXPAND_MAX = [0.40, 0.50, 0.60, 0.67, 0.75, 0.90, 1.00]
DEFAULT_TREND60_MIN = [0.00, 0.20, 0.25, 0.33, 0.50]


def apply_filter(df: pd.DataFrame, p_expand_max: float, trend60_min: float) -> pd.DataFrame:
    return df[
        (
            (df["vol_regime"] == "high")
            & (df["strategy"] == BASE_STRATEGIES["high"])
            & (df["p_expand_rank"] < p_expand_max)
        )
        | (
            (df["vol_regime"] == "medium")
            & (df["strategy"] == BASE_STRATEGIES["medium"])
            & (df["trend60_rank"] > trend60_min)
        )
    ].copy()


def evaluate(
    df: pd.DataFrame,
    cost: float,
    p_expand_max: float,
    trend60_min: float,
    years: list[int],
) -> dict:
    x = apply_filter(df, p_expand_max, trend60_min)
    x["net_pnl"] = x["realized_pnl"] - x["strategy"].map(CONTRACTS) * cost
    x["net_mc_ev"] = x["mc_ev"] - x["strategy"].map(CONTRACTS) * cost
    x["gate"] = x["net_mc_ev"] > 0

    annual = {}
    chunks = []
    for year in years:
        z = x[(x["year"] == year) & x["gate"]].sort_values("decision_date")
        s = summary(z["net_pnl"].to_numpy(float))
        annual[year] = s
        if not z.empty:
            chunks.append(z)
    pooled = pd.concat(chunks, ignore_index=True) if chunks else x.iloc[0:0]
    ps = summary(pooled["net_pnl"].to_numpy(float))
    return {
        "annual": annual,
        "pooled": ps,
        "trades": pooled,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Risk-filtered regime router research")
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--selection-years", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--holdout-year", type=int, default=2026)
    ap.add_argument("--costs", nargs="+", type=float, default=[1, 2, 3, 4])
    ap.add_argument("--lookbacks", nargs="+", type=int, default=DEFAULT_LOOKBACKS)
    ap.add_argument("--p-expand-max", nargs="+", type=float, default=DEFAULT_P_EXPAND_MAX)
    ap.add_argument("--trend60-min", nargs="+", type=float, default=DEFAULT_TREND60_MIN)
    ap.add_argument("--min-trades-per-selection-year", type=int, default=10)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(args.trades, parse_dates=["decision_date"])
    required = {
        "decision_id", "decision_date", "strategy", "realized_pnl", "mc_ev",
        "trend20", "trend60", "rv20", "p_expand",
    }
    missing = required - set(raw.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")
    raw["year"] = raw["decision_date"].dt.year

    candidate_rows = []
    holdout_rows = []
    annual_rows = []

    for lookback in args.lookbacks:
        d = add_adaptive_regime(raw, lookback, 1 / 3, 2 / 3)
        for cost in args.costs:
            for pmax in args.p_expand_max:
                for tmin in args.trend60_min:
                    ev = evaluate(d, cost, pmax, tmin, args.selection_years)
                    ok = True
                    for year in args.selection_years:
                        s = ev["annual"][year]
                        if (
                            s["n"] < args.min_trades_per_selection_year
                            or not np.isfinite(s["mean"])
                            or s["mean"] <= 0
                            or not np.isfinite(s["pf"])
                            or s["pf"] <= 1
                        ):
                            ok = False
                            break
                    if not ok:
                        continue

                    candidate_rows.append({
                        "lookback": lookback,
                        "cost": cost,
                        "p_expand_max": pmax,
                        "trend60_min": tmin,
                        "selection_trades": ev["pooled"]["n"],
                        "selection_total": ev["pooled"]["total"],
                        "selection_mean": ev["pooled"]["mean"],
                        "selection_pf": ev["pooled"]["pf"],
                        "selection_min_year_mean": min(
                            ev["annual"][year]["mean"] for year in args.selection_years
                        ),
                    })

                    hold = evaluate(d, cost, pmax, tmin, [args.holdout_year])["annual"][args.holdout_year]
                    holdout_rows.append({
                        "lookback": lookback,
                        "cost": cost,
                        "p_expand_max": pmax,
                        "trend60_min": tmin,
                        **{f"holdout_{k}": v for k, v in hold.items()},
                    })

    candidates = pd.DataFrame(candidate_rows)
    holdouts = pd.DataFrame(holdout_rows)
    if candidates.empty:
        raise SystemExit("No risk-filter candidate passed the pre-holdout selection criteria")

    candidates = candidates.sort_values(
        ["cost", "selection_total", "selection_mean", "selection_min_year_mean", "selection_trades"],
        ascending=[True, False, False, False, False],
    )
    candidates.to_csv(out / "risk_filter_candidates.csv", index=False)
    holdouts.to_csv(out / "risk_filter_candidate_holdouts.csv", index=False)

    selected_rows = []
    for cost in args.costs:
        c = candidates[candidates["cost"] == cost]
        if c.empty:
            continue
        best = c.iloc[0]
        h = holdouts[
            (holdouts["cost"] == cost)
            & (holdouts["lookback"] == best["lookback"])
            & (holdouts["p_expand_max"] == best["p_expand_max"])
            & (holdouts["trend60_min"] == best["trend60_min"])
        ]
        selected_rows.append({
            **best.to_dict(),
            "holdout_n": int(h.iloc[0]["holdout_n"]) if not h.empty else 0,
            "holdout_mean": float(h.iloc[0]["holdout_mean"]) if not h.empty else np.nan,
            "holdout_total": float(h.iloc[0]["holdout_total"]) if not h.empty else 0.0,
            "holdout_pf": float(h.iloc[0]["holdout_pf"]) if not h.empty else np.nan,
            "holdout_win_rate": float(h.iloc[0]["holdout_win_rate"]) if not h.empty else np.nan,
            "holdout_max_drawdown": float(h.iloc[0]["holdout_max_drawdown"]) if not h.empty else np.nan,
        })
    selected = pd.DataFrame(selected_rows)
    selected.to_csv(out / "risk_filter_selected_by_cost.csv", index=False)

    # Operational candidate is the selection under the frozen 2-point stress cost.
    op = selected[selected["cost"] == 2]
    if op.empty:
        raise SystemExit("No cost=2 risk-filter candidate survived selection")
    op = op.iloc[0]

    d = add_adaptive_regime(raw, int(op["lookback"]), 1 / 3, 2 / 3)
    years = sorted(raw["year"].dropna().astype(int).unique().tolist())
    ev_all = evaluate(
        d, 2.0, float(op["p_expand_max"]), float(op["trend60_min"]), years
    )
    baseline = apply_filter(
        d, p_expand_max=1.01, trend60_min=-1.0
    )
    baseline["net_pnl"] = baseline["realized_pnl"] - baseline["strategy"].map(CONTRACTS) * 2.0
    baseline["net_mc_ev"] = baseline["mc_ev"] - baseline["strategy"].map(CONTRACTS) * 2.0
    baseline["gate"] = baseline["net_mc_ev"] > 0

    compare_rows = []
    for year in [2024, 2025, 2026]:
        filtered_s = ev_all["annual"].get(year, summary(np.array([])))
        z = baseline[(baseline["year"] == year) & baseline["gate"]]
        base_s = summary(z["net_pnl"].to_numpy(float))
        compare_rows.append({
            "year": year,
            "filtered_n": filtered_s["n"],
            "filtered_mean": filtered_s["mean"],
            "filtered_pf": filtered_s["pf"],
            "filtered_total": filtered_s["total"],
            "baseline_n": base_s["n"],
            "baseline_mean": base_s["mean"],
            "baseline_pf": base_s["pf"],
            "baseline_total": base_s["total"],
        })
    pd.DataFrame(compare_rows).to_csv(out / "risk_filter_vs_baseline.csv", index=False)

    status = (
        "RESEARCH_CANDIDATE"
        if op["holdout_n"] >= 5 and op["holdout_mean"] > 0 and op["holdout_pf"] > 1
        else "REJECT_HOLDOUT"
    )

    lines = [
        "# Risk-Filtered Regime Router — V2 Run 9",
        "",
        "The previous regime map was robustly tested and did not survive rolling selection. This phase keeps the strategy identities frozen and searches only for a simple, past-only risk filter.",
        "",
        "Frozen base strategies:",
        "- High volatility: Short Strangle",
        "- Medium volatility: Sell Put",
        "- Low volatility: NO_TRADE",
        "",
        "Filter:",
        "- High volatility requires trailing MC expansion probability rank below the selected threshold.",
        "- Medium volatility requires trailing 60-session trend rank above the selected threshold.",
        "- Regime ranks are past-only; 2026 is untouched during filter selection.",
        "",
        f"Selection years: {args.selection_years}",
        f"Holdout year: {args.holdout_year}",
        "Selection requires positive mean P&L and PF > 1 in every selection year, with at least "
        f"{args.min_trades_per_selection_year} gated trades per year.",
        "",
        "## Cost-stress selections",
        "",
    ]
    for _, r in selected.sort_values("cost").iterrows():
        lines.append(
            f"- cost={r.cost:.0f}: lookback={int(r.lookback)}, p_expand<{r.p_expand_max:.2f}, "
            f"trend60>{r.trend60_min:.2f}; selection total={r.selection_total:.2f}; "
            f"2026 n={int(r.holdout_n)}, mean={r.holdout_mean:.2f}, PF={r.holdout_pf:.2f}, total={r.holdout_total:.2f}"
        )

    lines += [
        "",
        "## Frozen 2-point operational research candidate",
        "",
        f"- Lookback: {int(op.lookback)} sessions",
        f"- High-vol filter: p_expand rank < {op.p_expand_max:.2f}",
        f"- Medium-vol filter: trend60 rank > {op.trend60_min:.2f}",
        f"- 2024: n={int(ev_all['annual'][2024]['n'])}, mean={ev_all['annual'][2024]['mean']:.2f}, PF={ev_all['annual'][2024]['pf']:.2f}, total={ev_all['annual'][2024]['total']:.2f}",
        f"- 2025: n={int(ev_all['annual'][2025]['n'])}, mean={ev_all['annual'][2025]['mean']:.2f}, PF={ev_all['annual'][2025]['pf']:.2f}, total={ev_all['annual'][2025]['total']:.2f}",
        f"- 2026 holdout: n={int(op.holdout_n)}, mean={op.holdout_mean:.2f}, PF={op.holdout_pf:.2f}, total={op.holdout_total:.2f}",
        f"- Status: {status}",
        "",
        "This is a paper-trading research candidate only. The strategy identities are short-premium structures, so every entry must still pass the MC EV gate and existing ES95/ES99 sizing/risk-budget controls.",
    ]
    (out / "risk_filtered_regime_router_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
