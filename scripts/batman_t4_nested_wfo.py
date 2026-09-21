#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BROKERAGES = (10.0, 20.0, 30.0)
KEYS = ["exit_family", "target_param", "stop_param", "retracement_param"]
OUTER_YEARS = (2022, 2023, 2024)


def norm(v):
    if pd.isna(v):
        return "NA"
    if isinstance(v, (float, np.floating)):
        return f"{float(v):.12g}"
    return str(v)


def variant_id(df: pd.DataFrame) -> pd.Series:
    return (
        df["exit_family"].map(str)
        + "|t=" + df["target_param"].map(norm)
        + "|s=" + df["stop_param"].map(norm)
        + "|r=" + df["retracement_param"].map(norm)
    )


def drawdown(frame: pd.DataFrame) -> float:
    x = frame.sort_values("decision_date")["realized_net_inr"].to_numpy(float)
    if len(x) == 0:
        return 0.0
    eq = np.cumsum(x)
    return float((eq - np.maximum.accumulate(eq)).min())


def select_variant(training: pd.DataFrame):
    d = training.copy()
    d["variant_id"] = variant_id(d)
    grouped = (
        d.groupby(
            ["variant_id", "exit_family", "target_param", "stop_param", "retracement_param", "brokerage_per_order_inr"],
            dropna=False,
            sort=False,
        )["realized_net_inr"]
        .sum()
        .reset_index(name="total_net_inr")
    )

    rows = []
    complexity_map = {
        "expiry_control": 0,
        "fixed_target": 1,
        "fixed_stop": 1,
        "fixed_target_stop": 2,
        "trailing_stop": 1,
        "trailing_target": 2,
        "trailing_target_stop": 3,
    }

    for vid, sub in grouped.groupby("variant_id", sort=False):
        by = {
            float(row.brokerage_per_order_inr): float(row.total_net_inr)
            for _, row in sub.iterrows()
        }
        if any(b not in by for b in BROKERAGES):
            continue

        x = d[d.variant_id.eq(vid)].copy()
        trades = int(x["decision_date"].nunique())
        if trades <= 0:
            continue

        x30 = x[x.brokerage_per_order_inr.eq(30.0)]
        rows.append(
            {
                "variant_id": vid,
                "exit_family": str(sub.exit_family.iloc[0]),
                "target_param": sub.target_param.iloc[0],
                "stop_param": sub.stop_param.iloc[0],
                "retracement_param": sub.retracement_param.iloc[0],
                "worst_brokerage_total": min(by.values()),
                "median_brokerage_total": float(np.median(list(by.values()))),
                "mean_brokerage_total": float(np.mean(list(by.values()))),
                "worst_brokerage_max_dd": drawdown(x30),
                "complexity": complexity_map.get(str(sub.exit_family.iloc[0]), 99),
                "n_training_trades": trades,
            }
        )

    table = pd.DataFrame(rows)
    if table.empty:
        raise RuntimeError("No complete positive-sample variants available for WFO.")

    table = table.sort_values(
        ["worst_brokerage_total", "median_brokerage_total", "worst_brokerage_max_dd", "complexity"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    chosen = table.iloc[0].to_dict()
    return chosen, table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade-level", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(args.trade_level)
    d["decision_date"] = pd.to_datetime(d["decision_date"])
    d["year"] = d["decision_date"].dt.year
    d["brokerage_per_order_inr"] = pd.to_numeric(d["brokerage_per_order_inr"], errors="coerce")

    outer_rows = []
    outer_trade_rows = []
    selection_tables = []

    for year in OUTER_YEARS:
        train = d[d.year < year].copy()
        test = d[d.year == year].copy()
        chosen, table = select_variant(train)
        table["outer_test_year"] = year
        selection_tables.append(table)

        test["variant_id"] = variant_id(test)
        selected = test[test.variant_id.eq(chosen["variant_id"])].copy()
        selected["outer_test_year"] = year
        selected["selected_exit_family"] = chosen["exit_family"]
        selected["selected_target_param"] = chosen["target_param"]
        selected["selected_stop_param"] = chosen["stop_param"]
        selected["selected_retracement_param"] = chosen["retracement_param"]
        outer_trade_rows.append(selected)

        for brokerage in BROKERAGES:
            sx = selected[selected.brokerage_per_order_inr.eq(brokerage)]
            cx = test[
                test.exit_family.eq("expiry_control")
                & test.brokerage_per_order_inr.eq(brokerage)
            ]
            outer_rows.append(
                {
                    "outer_test_year": year,
                    "brokerage_per_order_inr": brokerage,
                    "selected_exit_family": chosen["exit_family"],
                    "selected_target_param": chosen["target_param"],
                    "selected_stop_param": chosen["stop_param"],
                    "selected_retracement_param": chosen["retracement_param"],
                    "selected_trades": int(sx["decision_date"].nunique()),
                    "selected_total_net_inr": float(sx["realized_net_inr"].sum()),
                    "selected_mean_net_inr": float(sx["realized_net_inr"].mean()) if len(sx) else np.nan,
                    "selected_win_rate": float((sx["realized_net_inr"] > 0).mean()) if len(sx) else np.nan,
                    "control_total_net_inr": float(cx["realized_net_inr"].sum()),
                    "control_mean_net_inr": float(cx["realized_net_inr"].mean()) if len(cx) else np.nan,
                    "control_win_rate": float((cx["realized_net_inr"] > 0).mean()) if len(cx) else np.nan,
                    "selected_minus_control_inr": float(sx["realized_net_inr"].sum() - cx["realized_net_inr"].sum()),
                }
            )

    final_choice, final_table = select_variant(d[d.year <= 2024].copy())
    final_table["selection_scope"] = "full_development_2020_2024"

    outer_summary = pd.DataFrame(outer_rows)
    outer_trades = pd.concat(outer_trade_rows, ignore_index=True)

    outer_summary.to_csv(out / "T4_OUTER_OOS_SUMMARY.csv", index=False)
    outer_trades.to_csv(out / "T4_OUTER_OOS_TRADE_LEVEL.csv", index=False)
    pd.concat(selection_tables, ignore_index=True).to_csv(out / "T4_INNER_SELECTION_TABLES.csv", index=False)
    final_table.to_csv(out / "T4_FINAL_DEVELOPMENT_CANDIDATE_MATRIX.csv", index=False)
    pd.DataFrame([final_choice]).to_csv(out / "T4_FINAL_DEVELOPMENT_SELECTION.csv", index=False)
    (out / "T4_FINAL_SELECTION.json").write_text(json.dumps(final_choice, indent=2, allow_nan=True) + "\n")
    report = {
        "outer_years": list(OUTER_YEARS),
        "outer_oos_trades": int(outer_trades["decision_date"].nunique()),
        "final_selection": final_choice,
        "selection_rule": "maximize worst-brokerage total net P&L; tie-break median brokerage total, then least-negative max drawdown, then lower rule complexity",
        "data_scope": "corrected T3 development artifact, 2020-2024",
        "holdout_reserved": "2025-2026",
    }
    (out / "T4_REPORT.json").write_text(json.dumps(report, indent=2, allow_nan=True) + "\n")
    print(json.dumps(report, indent=2, allow_nan=True))
    print(outer_summary.to_string(index=False))


if __name__ == "__main__":
    main()
