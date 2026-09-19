from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import build_strategy


DEFINED_RISK = {
    "Buy Call", "Buy Put",
    "Bull Call Spread", "Bull Put Spread",
    "Bear Put Spread", "Bear Call Spread",
    "Bull Condor", "Bear Condor",
    "Bull Butterfly", "Bear Butterfly",
    "Long Straddle", "Long Strangle",
    "Long Iron Butterfly", "Long Iron Condor",
    "Long Calendar with Calls", "Long Calendar with Puts",
    "Strip", "Strap",
    "Iron Butterfly", "Short Iron Condor",
    "Call Ratio Back Spread", "Put Ratio Back Spread",
}


def summarize(x: pd.Series) -> dict[str, float]:
    x = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(x) == 0:
        return {"n": 0, "mean": np.nan, "total": 0.0, "win_rate": np.nan, "profit_factor": np.nan}
    gains = x[x > 0].sum()
    losses = -x[x < 0].sum()
    return {
        "n": len(x),
        "mean": float(np.mean(x)),
        "total": float(np.sum(x)),
        "win_rate": float(np.mean(x > 0)),
        "profit_factor": float(gains / losses) if losses > 0 else np.inf,
    }




def contract_count(strategy: str) -> int:
    dummy = {k: float(i + 100.0) for i, k in enumerate(
        ["p10", "p20", "p25", "p35", "p45", "atm", "c55", "c65", "c75", "c80", "c90"]
    )}
    return int(sum(abs(int(leg.qty)) for leg in build_strategy(strategy, dummy)))


def bootstrap_prob_positive(x: np.ndarray, n_iter: int, seed: int) -> tuple[float, float, float]:
    if len(x) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    sims = rng.choice(x, size=(n_iter, len(x)), replace=True).sum(axis=1)
    return float(np.mean(sims > 0)), float(np.quantile(sims, 0.05)), float(np.quantile(sims, 0.50))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--cost-per-leg", type=float, default=2.0)
    ap.add_argument("--bootstrap", type=int, default=20000)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t = pd.read_csv(args.trades, parse_dates=["decision_date"])
    required = {"strategy", "decision_date", "realized_pnl", "n_legs"}
    missing = required - set(t.columns)
    if missing:
        raise SystemExit(f"missing columns: {sorted(missing)}")

    t["year"] = t.decision_date.dt.year
    t["contract_count"] = t["strategy"].map(contract_count)
    t["net_pnl_after_cost"] = t.realized_pnl - t.contract_count * float(args.cost_per_leg)

    rows = []
    for strategy, g in t.groupby("strategy", sort=True):
        dev = g[g.year <= 2022]
        val = g[g.year.between(2023, 2024)]
        final = g[g.year >= 2025]
        pooled = g[g.year >= 2023]

        sdev = summarize(dev.net_pnl_after_cost)
        sval = summarize(val.net_pnl_after_cost)
        sfinal = summarize(final.net_pnl_after_cost)
        spo = summarize(pooled.net_pnl_after_cost)

        pboot, p05, p50 = bootstrap_prob_positive(
            pooled.net_pnl_after_cost.to_numpy(float),
            args.bootstrap,
            100000 + abs(hash(strategy)) % 100000,
        )

        passes = (
            sval["n"] >= 50
            and sfinal["n"] >= 20
            and sval["mean"] > 0
            and sfinal["mean"] > 0
            and sval["profit_factor"] > 1
            and sfinal["profit_factor"] > 1
            and pboot >= 0.95
        )
        rows.append({
            "strategy": strategy,
            "risk_class": "defined-risk" if strategy in DEFINED_RISK else "requires_strict_risk_cap",
            "contracts_per_strategy_unit": int(contract_count(strategy)),
            "dev_n": sdev["n"], "dev_mean": sdev["mean"], "dev_total": sdev["total"],
            "validation_n": sval["n"], "validation_mean": sval["mean"],
            "validation_total": sval["total"], "validation_win_rate": sval["win_rate"],
            "validation_profit_factor": sval["profit_factor"],
            "final_n": sfinal["n"], "final_mean": sfinal["mean"],
            "final_total": sfinal["total"], "final_win_rate": sfinal["win_rate"],
            "final_profit_factor": sfinal["profit_factor"],
            "oos_n": spo["n"], "oos_mean": spo["mean"], "oos_total": spo["total"],
            "bootstrap_p_positive": pboot, "bootstrap_p05_total": p05,
            "bootstrap_median_total": p50, "passes_screen": bool(passes),
            "cost_per_leg_points": float(args.cost_per_leg),
        })

    report = pd.DataFrame(rows).sort_values(
        ["passes_screen", "oos_mean", "oos_total"], ascending=[False, False, False]
    )
    report.to_csv(out / "candidate_screen.csv", index=False)

    passing = report[report.passes_screen].copy()
    if passing.empty:
        headline = "No strategy currently passes the conservative OOS candidate screen."
        (out / "candidate_strategy.md").write_text(headline + "\n", encoding="utf-8")
        print(headline)
        return

    chosen = passing.iloc[0]
    text = [
        "# Candidate strategy screen",
        "",
        f"Selected research candidate: {chosen.strategy}",
        f"Risk class: {chosen.risk_class}",
        f"Stress cost: {args.cost_per_leg:.2f} points/leg",
        "",
        "The candidate passes validation and final-period tests under the fixed screen.",
        "This is a research candidate for prospective paper trading, not a guarantee of future profitability.",
        "",
        "## OOS statistics after stressed costs",
        "",
        f"- Validation: n={int(chosen.validation_n)}, mean={chosen.validation_mean:.2f}, total={chosen.validation_total:.2f}, PF={chosen.validation_profit_factor:.2f}",
        f"- Final: n={int(chosen.final_n)}, mean={chosen.final_mean:.2f}, total={chosen.final_total:.2f}, PF={chosen.final_profit_factor:.2f}",
        f"- Pooled OOS bootstrap P(total > 0): {chosen.bootstrap_p_positive:.3f}",
        f"- 5th percentile bootstrap total: {chosen.bootstrap_p05_total:.2f}",
        "",
        "## Operational construction",
        "",
        'Use the strategy definition already implemented in "src/nifty_mc/strategy_catalog.py".',
        "Entry is generated only when the research target-date engine produces a valid option chain and all required strikes are available.",
        "Position sizing must be based on a predefined risk budget; do not size from raw index points alone.",
    ]
    (out / "candidate_strategy.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))


if __name__ == "__main__":
    main()
