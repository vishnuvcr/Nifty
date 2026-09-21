#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BROKERAGES=(10.0,20.0,30.0)
BASE_SLIPPAGE=2.0
ORDERS_PER_ROUND_TRIP=8


def clopper_pearson(k,n,alpha=0.05):
    if k==0:
        lo=0.0
    else:
        lo=float(stats.beta.ppf(alpha/2,k,n-k+1))
    if k==n:
        hi=1.0
    else:
        hi=float(stats.beta.ppf(1-alpha/2,k+1,n-k))
    return lo,hi


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trade-level",required=True)
    ap.add_argument("--out-dir",required=True)
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)

    d=pd.read_csv(args.trade_level)
    d["decision_date"]=pd.to_datetime(d.decision_date)
    d20=d[d.brokerage_per_order_inr.eq(20.0)].copy()
    if d20.empty:
        raise SystemExit("No ₹20/order holdout rows.")

    x=d20.realized_net_inr.to_numpy(float)
    n=len(x); k=int((x>0).sum())
    mean=float(x.mean()); sd=float(x.std(ddof=1))
    tcrit=float(stats.t.ppf(0.975,n-1))
    mean_lo=float(mean-tcrit*sd/np.sqrt(n))
    mean_hi=float(mean+tcrit*sd/np.sqrt(n))
    win_lo,win_hi=clopper_pearson(k,n)

    rng=np.random.default_rng(20260921)
    boots=rng.choice(x,size=(20000,n),replace=True).mean(axis=1)
    boot_ci=(float(np.quantile(boots,0.025)),float(np.quantile(boots,0.975)))

    slippage=[]
    for extra in (0.0,0.5,1.0,2.0,3.0,4.0):
        # Conservative stress: every additional premium point is charged on
        # eight round-trip leg executions; no offsetting reduction in STT is
        # credited.
        stressed=d20.copy()
        stressed["stressed_net_inr"]=stressed.realized_net_inr - ORDERS_PER_ROUND_TRIP*extra*stressed.lot_size
        slippage.append({
            "extra_slippage_points":extra,
            "total_net_inr":float(stressed.stressed_net_inr.sum()),
            "mean_net_inr":float(stressed.stressed_net_inr.mean()),
            "win_rate":float((stressed.stressed_net_inr>0).mean()),
        })

    leave_one_out=[]
    for _,row in d20.iterrows():
        y=d20.loc[d20.index!=row.name,"realized_net_inr"]
        leave_one_out.append({
            "excluded_decision_date":str(row.decision_date.date()),
            "remaining_total_net_inr":float(y.sum()),
            "remaining_mean_net_inr":float(y.mean()),
        })

    yearly=d20.assign(year=d20.decision_date.dt.year).groupby("year").realized_net_inr.agg(["count","sum","mean"]).reset_index()

    summary={
        "trades":n,
        "wins":k,
        "losses":n-k,
        "total_net_inr":float(x.sum()),
        "mean_net_inr":mean,
        "median_net_inr":float(np.median(x)),
        "sample_sd_net_inr":sd,
        "t95_mean_ci":[mean_lo,mean_hi],
        "clopper_pearson_95_win_rate_ci":[win_lo,win_hi],
        "bootstrap_percentile_95_mean_ci":list(boot_ci),
        "largest_trade_share_of_total":float(np.max(x)/np.sum(x)),
        "brokerage_sensitivity":(
            d.groupby("brokerage_per_order_inr")
             .realized_net_inr.agg(["sum","mean","count"])
             .reset_index()
             .to_dict(orient="records")
        ),
        "slippage_stress":slippage,
        "leave_one_out_min_total_inr":float(min(r["remaining_total_net_inr"] for r in leave_one_out)),
        "holdout_start":str(d20.decision_date.min().date()),
        "holdout_end":str(d20.decision_date.max().date()),
    }
    (out/"T5_ROBUSTNESS_SUMMARY.json").write_text(json.dumps(summary,indent=2,allow_nan=True)+"\n")
    pd.DataFrame(slippage).to_csv(out/"T5_SLIPPAGE_STRESS.csv",index=False)
    yearly.to_csv(out/"T5_YEARLY_STABILITY.csv",index=False)
    pd.DataFrame(leave_one_out).to_csv(out/"T5_LEAVE_ONE_OUT.csv",index=False)
    print(json.dumps(summary,indent=2,allow_nan=True))
    print(yearly.to_string(index=False))
    print(pd.DataFrame(slippage).to_string(index=False))


if __name__=="__main__":
    main()
