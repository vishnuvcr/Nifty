from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def summarize(x: pd.DataFrame, cost_points: float = 0.0) -> dict:
    if x.empty:
        return {"trades": 0, "win_rate": np.nan, "mean_pnl": np.nan, "median_pnl": np.nan,
                "total_pnl": 0.0, "max_drawdown": np.nan, "profit_factor": np.nan}
    pnl = x["realized_pnl"].to_numpy(float) - cost_points
    eq = np.cumsum(pnl)
    dd = eq - np.maximum.accumulate(eq)
    gains = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    return {
        "trades": len(x),
        "win_rate": float(np.mean(pnl > 0)),
        "mean_pnl": float(np.mean(pnl)),
        "median_pnl": float(np.median(pnl)),
        "total_pnl": float(np.sum(pnl)),
        "max_drawdown": float(np.min(dd)),
        "profit_factor": float(gains / losses) if losses > 0 else np.inf,
    }

def clustered_bootstrap_mean(x: pd.DataFrame, cost_points: float, n: int, seed: int):
    if x.empty:
        return (np.nan,np.nan,np.nan)
    groups=[(g["realized_pnl"].to_numpy(float)-cost_points)
            for _,g in x.assign(cluster=x["actual_expiry"].astype(str)).groupby("cluster",sort=False)]
    if len(groups)<2:
        a=np.concatenate(groups)
        return float(a.mean()),float(a.mean()),float(a.mean())
    rng=np.random.default_rng(seed)
    vals=np.empty(n)
    for i in range(n):
        sample=rng.integers(0,len(groups),size=len(groups))
        vals[i]=np.concatenate([groups[j] for j in sample]).mean()
    return float(vals.mean()),float(np.quantile(vals,.025)),float(np.quantile(vals,.975))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--dev-end-year",type=int,default=2022)
    ap.add_argument("--validation-start-year",type=int,default=2023)
    ap.add_argument("--validation-end-year",type=int,default=2024)
    ap.add_argument("--final-start-year",type=int,default=2025)
    ap.add_argument("--bootstrap",type=int,default=2000)
    args=ap.parse_args()

    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(args.input,parse_dates=["decision_date","actual_expiry","expiry_session"])
    d=d.sort_values("decision_date").reset_index(drop=True)
    d["year"]=d.decision_date.dt.year
    dev=d[d.year<=args.dev_end_year].copy()
    val=d[d.year.between(args.validation_start_year,args.validation_end_year)].copy()
    final=d[d.year>=args.final_start_year].copy()

    ev_thresholds=[-20,-10,0,10,20,30,40,50]
    pop_thresholds=[0.40,0.45,0.50,0.55]
    costs=[0,1,2,3,5,10]
    records=[]
    for signal, thresholds, col in [("mc_ev",ev_thresholds,"mc_ev"),("mc_pop",pop_thresholds,"mc_pop")]:
        for th in thresholds:
            for period,frame in [("development",dev),("validation",val),("final",final)]:
                selected=frame[frame[col]>=th]
                for c in costs:
                    gross=summarize(selected,0)
                    records.append({"signal":signal,"threshold":th,"period":period,"cost_points":c,
                                    **summarize(selected,c),"mean_gross_pnl":gross["mean_pnl"]})
    combined=[(0,.45),(10,.45),(20,.45),(30,.45),(0,.50),(10,.50),(20,.50)]
    for evth,popth in combined:
        for period,frame in [("development",dev),("validation",val),("final",final)]:
            selected=frame[(frame.mc_ev>=evth)&(frame.mc_pop>=popth)]
            for c in costs:
                records.append({"signal":"mc_ev_and_pop","threshold":f"EV>={evth},PoP>={popth}",
                                "period":period,"cost_points":c,**summarize(selected,c),
                                "mean_gross_pnl":summarize(selected,0)["mean_pnl"]})
    res=pd.DataFrame(records)
    res.to_csv(out/"threshold_results.csv",index=False)

    dev0=res[(res.period=="development")&(res.cost_points==0)&(res.trades>=30)&res.signal.isin(["mc_ev","mc_pop"])].copy()
    chosen=dev0.sort_values(["total_pnl","mean_pnl"],ascending=False).iloc[0]
    chosen_signal=chosen.signal
    chosen_threshold=chosen.threshold
    chosen_rows=[]
    for period,frame in [("development",dev),("validation",val),("final",final)]:
        selected=frame[(frame.mc_ev>=float(chosen_threshold))] if chosen_signal=="mc_ev" else frame[(frame.mc_pop>=float(chosen_threshold))]
        for c in costs:
            chosen_rows.append({"signal":chosen_signal,"threshold":chosen_threshold,"period":period,
                                "cost_points":c,**summarize(selected,c)})
    chosen_df=pd.DataFrame(chosen_rows)
    chosen_df.to_csv(out/"frozen_rule_results.csv",index=False)

    bins=[0,.35,.40,.45,.50,.55,.60,1]
    labels=["<35%","35-40%","40-45%","45-50%","50-55%","55-60%",">=60%"]
    d["pop_bucket"]=pd.cut(d.mc_pop,bins=bins,labels=labels,right=False,include_lowest=True)
    cal=d.groupby(["year","pop_bucket"],observed=False).agg(
        trades=("win","size"),predicted_pop=("mc_pop","mean"),actual_win_rate=("win","mean"),
        mean_pnl=("realized_pnl","mean"),mean_mc_ev=("mc_ev","mean")).reset_index()
    cal.to_csv(out/"pop_calibration_by_year.csv",index=False)

    _,ci_lo,ci_hi=clustered_bootstrap_mean(d,0,args.bootstrap,20260918)
    lines=[
        "# Long Iron Condor Phase 2","",
        f"- Development: <= {args.dev_end_year}",
        f"- Validation: {args.validation_start_year}-{args.validation_end_year}",
        f"- Final/untouched test: >= {args.final_start_year}",
        f"- Total trades: {len(d)}","",
        "## Unfiltered gross results","",
        "| Period | Trades | Win rate | Mean P&L | Total P&L | Max DD |",
        "|---|---:|---:|---:|---:|---:|"
    ]
    for name,frame in [("Development",dev),("Validation",val),("Final",final)]:
        s=summarize(frame,0)
        lines.append(f"| {name} | {s['trades']} | {s['win_rate']:.3f} | {s['mean_pnl']:.2f} | {s['total_pnl']:.2f} | {s['max_drawdown']:.2f} |")
    lines += ["","## Frozen development-selected rule","",
              f"- Signal: {chosen_signal}",f"- Threshold: {chosen_threshold}",
              "- Selection: highest development total gross P&L among rules with >=30 trades.",
              "","## Frozen-rule results","",chosen_df.to_markdown(index=False),"",
              "## Cluster bootstrap","",
              f"- Overall mean gross P&L 95% cluster-bootstrap CI: {ci_lo:.2f} to {ci_hi:.2f} points/trade.",
              "","Validation and final periods are reported only after the rule was frozen on development data."]
    (out/"phase2_report.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines[:30]))

if __name__=="__main__":
    main()
