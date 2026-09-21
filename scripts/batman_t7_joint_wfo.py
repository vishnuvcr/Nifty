#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BROKERAGES = (10.0, 20.0, 30.0)
OUTER_YEARS = (2022, 2023, 2024)
MIN_TRAIN_TRADES = 25


def norm(v):
    if pd.isna(v):
        return "NA"
    if isinstance(v, (float, np.floating)):
        return f"{float(v):.12g}"
    return str(v)


def variant_id(df: pd.DataFrame) -> pd.Series:
    return (
        "D"+df["entry_offset"].astype(int).astype(str)
        +"|"+df["entry_timing"].astype(str)
        +"|"+df["exit_family"].astype(str)
        +"|t="+df["target_param"].map(norm)
        +"|s="+df["stop_param"].map(norm)
        +"|a="+df["activation_param"].map(norm)
        +"|r="+df["retracement_param"].map(norm)
    )


def max_dd(x):
    arr=x.sort_values("decision_date").realized_net_inr.to_numpy(float)
    if len(arr)==0:
        return 0.0
    eq=np.cumsum(arr)
    return float((eq-np.maximum.accumulate(eq)).min())


def complexity(row):
    return (
        {"expiry_control":0,"fixed_target":1,"fixed_stop":1,"trailing_target":2,"trailing_stop":1}[row.exit_family]
        + (0 if row.entry_timing=="same_session_0930" else 1)
    )


def select(training: pd.DataFrame):
    d=training.copy()
    d["variant_id"]=variant_id(d)

    g=(
        d.groupby(["variant_id","entry_offset","entry_timing","exit_family",
                   "target_param","stop_param","activation_param","retracement_param",
                   "brokerage_per_order_inr"],dropna=False,sort=False)
         .agg(total_net_inr=("realized_net_inr","sum"),
              mean_net_inr=("realized_net_inr","mean"),
              unique_trades=("decision_date","nunique"))
         .reset_index()
    )

    rows=[]
    for vid, sub in g.groupby("variant_id",sort=False):
        total={float(r.brokerage_per_order_inr):float(r.total_net_inr) for _,r in sub.iterrows()}
        mean={float(r.brokerage_per_order_inr):float(r.mean_net_inr) for _,r in sub.iterrows()}
        if any(b not in total for b in BROKERAGES):
            continue
        x=d[d.variant_id.eq(vid)].copy()
        trades=int(x.decision_date.nunique())
        if trades<MIN_TRAIN_TRADES:
            continue
        x30=x[x.brokerage_per_order_inr.eq(30.0)]
        rows.append({
            "variant_id":vid,
            "entry_offset":int(sub.entry_offset.iloc[0]),
            "entry_timing":str(sub.entry_timing.iloc[0]),
            "exit_family":str(sub.exit_family.iloc[0]),
            "target_param":sub.target_param.iloc[0],
            "stop_param":sub.stop_param.iloc[0],
            "activation_param":sub.activation_param.iloc[0],
            "retracement_param":sub.retracement_param.iloc[0],
            "worst_brokerage_total":min(total.values()),
            "worst_brokerage_mean":min(mean.values()),
            "median_brokerage_mean":float(np.median(list(mean.values()))),
            "worst_brokerage_max_dd":max_dd(x30),
            "complexity":complexity(sub.iloc[0]),
            "training_unique_trades":trades,
        })

    table=pd.DataFrame(rows)
    if table.empty:
        raise RuntimeError("No joint configuration met the minimum training-trade requirement.")

    table=table.sort_values(
        ["worst_brokerage_mean","worst_brokerage_total","worst_brokerage_max_dd","complexity","training_unique_trades"],
        ascending=[False,False,False,True,False]
    ).reset_index(drop=True)
    return table.iloc[0].to_dict(), table


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trade-level",required=True)
    ap.add_argument("--out-dir",required=True)
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)

    d=pd.read_csv(args.trade_level)
    d["decision_date"]=pd.to_datetime(d.decision_date)
    d["year"]=d.decision_date.dt.year
    d["brokerage_per_order_inr"]=pd.to_numeric(d.brokerage_per_order_inr,errors="coerce")

    outer=[]; outer_trades=[]; selections=[]

    for year in OUTER_YEARS:
        train=d[d.year<year].copy()
        test=d[d.year==year].copy()
        chosen,table=select(train)
        table["outer_test_year"]=year
        selections.append(table)

        test["variant_id"]=variant_id(test)
        selected=test[test.variant_id.eq(chosen["variant_id"])].copy()
        selected["outer_test_year"]=year
        outer_trades.append(selected)

        for b in BROKERAGES:
            sx=selected[selected.brokerage_per_order_inr.eq(b)]
            cx=test[
                (test.entry_offset.eq(3))
                & (test.entry_timing.eq("same_session_0930"))
                & (test.exit_family.eq("expiry_control"))
                & test.brokerage_per_order_inr.eq(b)
            ]
            outer.append({
                "outer_test_year":year,
                "brokerage_per_order_inr":b,
                "selected_variant_id":chosen["variant_id"],
                "selected_entry_offset":chosen["entry_offset"],
                "selected_entry_timing":chosen["entry_timing"],
                "selected_exit_family":chosen["exit_family"],
                "selected_target_param":chosen["target_param"],
                "selected_stop_param":chosen["stop_param"],
                "selected_activation_param":chosen["activation_param"],
                "selected_retracement_param":chosen["retracement_param"],
                "selected_trades":int(sx.decision_date.nunique()),
                "selected_total_net_inr":float(sx.realized_net_inr.sum()),
                "selected_mean_net_inr":float(sx.realized_net_inr.mean()) if len(sx) else np.nan,
                "selected_win_rate":float((sx.realized_net_inr>0).mean()) if len(sx) else np.nan,
                "control_trades":int(cx.decision_date.nunique()),
                "control_total_net_inr":float(cx.realized_net_inr.sum()),
                "control_mean_net_inr":float(cx.realized_net_inr.mean()) if len(cx) else np.nan,
                "control_win_rate":float((cx.realized_net_inr>0).mean()) if len(cx) else np.nan,
                "selected_minus_control_inr":float(sx.realized_net_inr.sum()-cx.realized_net_inr.sum()),
            })

    final_choice, final_table=select(d[d.year<=2024].copy())
    final_table["selection_scope"]="full_development_2020_2024"

    outer_df=pd.DataFrame(outer)
    outer_trade_df=pd.concat(outer_trades,ignore_index=True)
    selection_df=pd.concat(selections,ignore_index=True)

    outer_df.to_csv(out/"T7_OUTER_OOS_SUMMARY.csv",index=False)
    outer_trade_df.to_csv(out/"T7_OUTER_OOS_TRADE_LEVEL.csv",index=False)
    selection_df.to_csv(out/"T7_INNER_SELECTION_TABLE.csv",index=False)
    final_table.to_csv(out/"T7_FINAL_CANDIDATE_MATRIX.csv",index=False)
    pd.DataFrame([final_choice]).to_csv(out/"T7_FINAL_SELECTION.csv",index=False)
    (out/"T7_FINAL_SELECTION.json").write_text(json.dumps(final_choice,indent=2,allow_nan=True)+"\n")
    report={
        "outer_years":list(OUTER_YEARS),
        "minimum_training_trades":MIN_TRAIN_TRADES,
        "final_selection":final_choice,
        "selection_rule":"maximize worst-brokerage mean net P&L per unique trade; then worst-brokerage total, least-negative drawdown, lower complexity, higher training-trade count",
        "baseline":"D3 same-session 09:30 expiry control",
        "holdout_reserved":"2025-2026",
    }
    (out/"T7_REPORT.json").write_text(json.dumps(report,indent=2,allow_nan=True)+"\n")
    print(json.dumps(report,indent=2,allow_nan=True))
    print(outer_df.to_string(index=False))

if __name__=="__main__":
    main()
