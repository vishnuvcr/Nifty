#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

BROKERAGES = (10.0, 20.0, 30.0)
CONTROL = ("expiry_control", np.nan, np.nan, np.nan)

KEYS = ["exit_family", "target_param", "stop_param", "retracement_param"]

OUTER_YEARS = (2022, 2023, 2024)


def variant_key(row):
    vals=[]
    for k in KEYS:
        v=row[k]
        if pd.isna(v):
            vals.append(None)
        else:
            vals.append(float(v) if k != "exit_family" else str(v))
    return tuple(vals)


def totals(frame: pd.DataFrame) -> pd.DataFrame:
    g=frame.groupby(KEYS+["brokerage_per_order_inr"],dropna=False).agg(
        trades=("realized_net_inr","size"),
        total_net_inr=("realized_net_inr","sum"),
        mean_net_inr=("realized_net_inr","mean"),
    ).reset_index()
    g["brokerage_per_order_inr"]=g["brokerage_per_order_inr"].astype(float)
    return g


def drawdown(frame: pd.DataFrame) -> float:
    x=frame.sort_values("decision_date").realized_net_inr.to_numpy(float)
    if len(x)==0:
        return 0.0
    eq=np.cumsum(x)
    return float((eq-np.maximum.accumulate(eq)).min())


def select_variant(training: pd.DataFrame) -> dict:
    # Selection criterion is frozen before WFO:
    # primary = worst brokerage total P&L across the pre-outer development years;
    # secondary = median brokerage total P&L;
    # tertiary = worst-brokerage maximum drawdown (closest to zero);
    # quaternary = fewer parameters/rule complexity.
    g=totals(training)
    rows=[]
    for key, sub in g.groupby(KEYS,dropna=False):
        by={float(r.brokerage_per_order_inr):float(r.total_net_inr) for _,r in sub.iterrows()}
        if not all(b in by for b in BROKERAGES):
            continue
        trade_rows=training
        mask=np.ones(len(trade_rows),dtype=bool)
        for k,v in zip(KEYS,key):
            if v is None:
                mask &= trade_rows[k].isna().to_numpy()
            else:
                mask &= trade_rows[k].astype(str).to_numpy()==str(v)
        x=trade_rows.loc[mask]
        dd=drawdown(x[x.brokerage_per_order_inr==30.0])
        complexity=sum(v is not None for v in key[1:])
        rows.append({
            "exit_family":key[0],"target_param":key[1],"stop_param":key[2],"retracement_param":key[3],
            "worst_brokerage_total":min(by.values()),
            "median_brokerage_total":float(np.median(list(by.values()))),
            "mean_brokerage_total":float(np.mean(list(by.values()))),
            "worst_brokerage_max_dd":dd,
            "complexity":complexity,
            "n_training_trades":int(len(x)),
        })
    s=pd.DataFrame(rows)
    if s.empty:
        raise SystemExit("No complete variants available for WFO selection.")
    s=s.sort_values(
        ["worst_brokerage_total","median_brokerage_total","worst_brokerage_max_dd","complexity"],
        ascending=[False,False,False,True]
    ).reset_index(drop=True)
    return s.iloc[0].to_dict(), s


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trade-level",required=True)
    ap.add_argument("--out-dir",required=True)
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(args.trade_level)
    d["decision_date"]=pd.to_datetime(d["decision_date"])
    d["year"]=d.decision_date.dt.year
    d["brokerage_per_order_inr"]=pd.to_numeric(d["brokerage_per_order_inr"],errors="coerce")

    outer_rows=[]; outer_trade_rows=[]; selection_tables=[]
    for year in OUTER_YEARS:
        train=d[d.year < year].copy()
        test=d[d.year == year].copy()
        chosen,table=select_variant(train)
        table["outer_test_year"]=year
        selection_tables.append(table)
        sel_mask=np.ones(len(test),dtype=bool)
        for k in KEYS:
            v=chosen[k]
            if pd.isna(v) or v is None:
                sel_mask &= test[k].isna().to_numpy()
            else:
                sel_mask &= test[k].astype(str).to_numpy()==str(v)
        selected=test.loc[sel_mask].copy()
        selected["outer_test_year"]=year
        selected["selected_exit_family"]=chosen["exit_family"]
        selected["selected_target_param"]=chosen["target_param"]
        selected["selected_stop_param"]=chosen["stop_param"]
        selected["selected_retracement_param"]=chosen["retracement_param"]
        outer_trade_rows.append(selected)

        for b in BROKERAGES:
            sx=selected[selected.brokerage_per_order_inr==b]
            cx=test[
                (test.exit_family=="expiry_control")
                & test.brokerage_per_order_inr.eq(b)
            ]
            outer_rows.append({
                "outer_test_year":year,
                "brokerage_per_order_inr":b,
                "selected_exit_family":chosen["exit_family"],
                "selected_target_param":chosen["target_param"],
                "selected_stop_param":chosen["stop_param"],
                "selected_retracement_param":chosen["retracement_param"],
                "selected_trades":len(sx),
                "selected_total_net_inr":float(sx.realized_net_inr.sum()),
                "selected_mean_net_inr":float(sx.realized_net_inr.mean()) if len(sx) else np.nan,
                "selected_win_rate":float((sx.realized_net_inr>0).mean()) if len(sx) else np.nan,
                "control_total_net_inr":float(cx.realized_net_inr.sum()),
                "control_mean_net_inr":float(cx.realized_net_inr.mean()) if len(cx) else np.nan,
                "control_win_rate":float((cx.realized_net_inr>0).mean()) if len(cx) else np.nan,
                "selected_minus_control_inr":float(sx.realized_net_inr.sum()-cx.realized_net_inr.sum()),
            })

    final_choice, final_table=select_variant(d[d.year <= 2024].copy())
    final_table["selection_scope"]="full_development_2020_2024"
    pd.DataFrame(outer_rows).to_csv(out/"T4_OUTER_OOS_SUMMARY.csv",index=False)
    pd.concat(outer_trade_rows,ignore_index=True).to_csv(out/"T4_OUTER_OOS_TRADE_LEVEL.csv",index=False)
    pd.concat(selection_tables,ignore_index=True).to_csv(out/"T4_INNER_SELECTION_TABLES.csv",index=False)
    final_table.to_csv(out/"T4_FINAL_DEVELOPMENT_CANDIDATE_MATRIX.csv",index=False)
    pd.DataFrame([final_choice]).to_csv(out/"T4_FINAL_DEVELOPMENT_SELECTION.csv",index=False)
    Path(out/"T4_FINAL_SELECTION.json").write_text(json.dumps(final_choice,indent=2,allow_nan=True)+"\n",encoding="utf-8")
    report={
        "outer_years":list(OUTER_YEARS),
        "outer_oos_trades":int(len(pd.concat(outer_trade_rows,ignore_index=True))),
        "final_selection":final_choice,
        "selection_rule":"maximize worst-brokerage total P&L on all prior development years; tie-break median brokerage total, then worst-brokerage max drawdown, then lower rule complexity",
        "data_scope":"T3 corrected development artifact, 2020-2024 only",
        "holdout_reserved":"2025-2026"
    }
    Path(out/"T4_REPORT.json").write_text(json.dumps(report,indent=2,allow_nan=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,allow_nan=True))
    print("\nOUTER OOS")
    print(pd.DataFrame(outer_rows).to_string(index=False))
    print("\nFINAL SELECTION")
    print(pd.DataFrame([final_choice]).to_string(index=False))

if __name__=="__main__":
    main()
