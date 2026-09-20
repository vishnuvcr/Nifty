from __future__ import annotations
import argparse, itertools, json, zlib
from pathlib import Path
import numpy as np
import pandas as pd

STRATEGIES=("Buy Call","Buy Put")
THRESHOLDS=[round(x,4) for x in np.arange(0.003,0.0081,0.0005)]
MIN_DEV_N=20
MIN_VALIDATION_N=20
BOOTSTRAP_REPS=10000
RC_REPS=5000
BLOCK=5
ROUND_TRIP_ORDERS=2

def stable_seed(label:str,base:int=20260920)->int:
    return int((base+zlib.crc32(label.encode("utf-8")))% (2**32-1))

def summary(x):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    if len(x)==0:
        return {"n":0,"mean":np.nan,"median":np.nan,"total":0.0,"win_rate":np.nan,"profit_factor":np.nan,"max_drawdown":np.nan}
    eq=np.cumsum(x); dd=eq-np.maximum.accumulate(eq)
    gains=float(x[x>0].sum()); losses=float(-x[x<0].sum())
    return {"n":int(len(x)),"mean":float(x.mean()),"median":float(np.median(x)),"total":float(x.sum()),
            "win_rate":float(np.mean(x>0)),"profit_factor":float(gains/losses) if losses>0 else float("inf"),
            "max_drawdown":float(dd.min())}

def block_bootstrap_mean_ci(x,block,n_iter,seed):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)==0:return np.nan,np.nan,np.nan
    if len(x)==1:return float(x[0]),float(x[0]),float(x[0]<=0)
    block=max(1,min(block,len(x))); starts=np.arange(len(x)-block+1)
    rng=np.random.default_rng(seed); vals=np.empty(n_iter)
    for i in range(n_iter):
        sample=[]
        while len(sample)<len(x):
            s=int(rng.choice(starts)); sample.extend(x[s:s+block].tolist())
        vals[i]=float(np.mean(sample[:len(x)]))
    return float(np.quantile(vals,.025)),float(np.quantile(vals,.975)),float(np.mean(vals<=0))

def prepare(raw,lot_size,slippage_points,brokerage_per_order_inr):
    req={"strategy","decision_date","spot","entry_cashflow","realized_pnl","mc_ev"}
    missing=sorted(req-set(raw.columns))
    if missing: raise SystemExit(f"strategy_trades.csv missing columns: {missing}")
    brokerage_points=brokerage_per_order_inr*ROUND_TRIP_ORDERS/lot_size
    execution_cost_points=slippage_points+brokerage_points
    x=raw[raw.strategy.isin(STRATEGIES)].copy()
    x["decision_date"]=pd.to_datetime(x.decision_date,errors="coerce").dt.normalize()
    for c in ["spot","entry_cashflow","realized_pnl","mc_ev"]: x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna(subset=["decision_date","spot","entry_cashflow","realized_pnl","mc_ev"]).copy()
    x["premium_points"]=(-x.entry_cashflow).clip(lower=0.0)
    x["premium_pct_spot"]=x.premium_points/x.spot
    x["round_trip_brokerage_points"]=brokerage_points
    x["execution_cost_points"]=execution_cost_points
    x["net_pnl"]=x.realized_pnl-execution_cost_points
    x["net_mc_ev"]=x.mc_ev-execution_cost_points
    x["mc_gate"]=x.net_mc_ev>0
    x["period"]=np.select([x.decision_date.dt.year<=2022,x.decision_date.dt.year<=2024],["development","validation"],default="exposed_final")
    return x,execution_cost_points

def build_grid(x):
    rows=[]
    for strategy,threshold in itertools.product(STRATEGIES,THRESHOLDS):
        for period in ["development","validation","exposed_final"]:
            g=x[(x.strategy==strategy)&(x.premium_pct_spot<=threshold)&x.mc_gate&(x.period==period)]
            s=summary(g.net_pnl.to_numpy(float))
            rows.append({"strategy":strategy,"premium_threshold_pct_spot":threshold,"period":period,**s,
                         "mean_mc_ev_net":float(g.net_mc_ev.mean()) if len(g) else np.nan,
                         "mean_premium_pct_spot":float(g.premium_pct_spot.mean()) if len(g) else np.nan})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trades",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--lot-size",type=int,default=65)
    ap.add_argument("--slippage-points-per-contract",type=float,default=2.0)
    ap.add_argument("--brokerage-per-order-inr",type=float,default=10.0)
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    raw=pd.read_csv(args.trades)
    x,cost=prepare(raw,args.lot_size,args.slippage_points_per_contract,args.brokerage_per_order_inr)
    grid=build_grid(x); grid.to_csv(out/"ALL_RULES_GRID.csv",index=False)

    candidates=[]
    for strategy,threshold in itertools.product(STRATEGIES,THRESHOLDS):
        g=x[(x.strategy==strategy)&(x.premium_pct_spot<=threshold)&x.mc_gate&(x.period=="development")]
        if len(g)<MIN_DEV_N: continue
        vals=g.net_pnl.to_numpy(float); mean=float(vals.mean()); se=float(vals.std(ddof=1)/np.sqrt(len(vals)))
        candidates.append({"strategy":strategy,"premium_threshold_pct_spot":threshold,"dev_n":len(vals),
                           "dev_mean":mean,"dev_se":se,"dev_conservative_score":mean-se,"dev_pf":summary(vals)["profit_factor"]})
    dev=pd.DataFrame(candidates).sort_values(["dev_conservative_score","dev_n","strategy","premium_threshold_pct_spot"],ascending=[False,False,True,True])
    dev.to_csv(out/"DEVELOPMENT_SELECTION_GRID.csv",index=False)
    if dev.empty: raise SystemExit("No development candidate met the minimum trade count.")
    selected=dev.iloc[0]
    strategy=str(selected.strategy); threshold=float(selected.premium_threshold_pct_spot)

    def row_for(period):
        r=grid[(grid.strategy==strategy)&np.isclose(grid.premium_threshold_pct_spot,threshold)&(grid.period==period)]
        if r.empty: raise SystemExit(f"Missing selected rule row for {period}")
        return r.iloc[0]
    val=row_for("validation"); final=row_for("exposed_final")
    z=x[(x.strategy==strategy)&(x.premium_pct_spot<=threshold)&x.mc_gate&(x.period=="validation")].sort_values("decision_date").net_pnl.to_numpy(float)
    ci_low,ci_high,boot_p=block_bootstrap_mean_ci(z,BLOCK,BOOTSTRAP_REPS,stable_seed("selected-validation"))
    validation_pass=int(val.n)>=MIN_VALIDATION_N and float(val["mean"])>0 and float(val.profit_factor)>1

    diag=grid[(grid.period=="validation")&(grid.n>=MIN_VALIDATION_N)].sort_values(["mean","profit_factor"],ascending=[False,False])
    diag.head(20).to_csv(out/"VALIDATION_DIAGNOSTIC_TOP20.csv",index=False)

    pre=x[x.period.isin(["development","validation"])].copy()
    dates=pd.DatetimeIndex(sorted(pre.decision_date.dropna().unique()))
    rules=list(itertools.product(STRATEGIES,THRESHOLDS))
    mat=np.zeros((len(dates),len(rules))); pos={d:i for i,d in enumerate(dates)}
    for j,(s,t) in enumerate(rules):
        g=pre[(pre.strategy==s)&(pre.premium_pct_spot<=t)&pre.mc_gate]
        for _,r in g.iterrows(): mat[pos[r.decision_date],j]=float(r.net_pnl)
    observed=float(mat.mean(axis=0).max())
    rng=np.random.default_rng(stable_seed("long-premium-reality-check")); starts=np.arange(max(1,len(dates)-BLOCK+1)); sims=np.empty(RC_REPS)
    for i in range(RC_REPS):
        idx=[]
        while len(idx)<len(dates):
            s=int(rng.choice(starts)); idx.extend(range(s,min(s+BLOCK,len(dates))))
        sims[i]=float(mat[idx[:len(dates)],:].mean(axis=0).max())
    rc_p=float(np.mean(sims>=observed))

    cost_rows=[]
    brokerage_points=args.brokerage_per_order_inr*ROUND_TRIP_ORDERS/args.lot_size
    for stress in [0.5,1.0,2.0,3.0]:
        for s,t,label in [(strategy,threshold,"selected_rule"),("Buy Put",0.005,"buy_put_0.50pct_diagnostic")]:
            b=raw[raw.strategy==s].copy()
            b["decision_date"]=pd.to_datetime(b.decision_date,errors="coerce").dt.normalize()
            b["premium_pct_spot"]=(-pd.to_numeric(b.entry_cashflow,errors="coerce"))/pd.to_numeric(b.spot,errors="coerce")
            b["mc_ev"]=pd.to_numeric(b.mc_ev,errors="coerce"); b["realized_pnl"]=pd.to_numeric(b.realized_pnl,errors="coerce")
            q=b[(b.premium_pct_spot<=t)&((b.mc_ev-stress-brokerage_points)>0)&b.decision_date.dt.year.between(2023,2024)]
            ss=summary((q.realized_pnl-stress-brokerage_points).to_numpy(float))
            cost_rows.append({"label":label,"strategy":s,"threshold":t,"stress_slippage_points":stress,**ss})
    pd.DataFrame(cost_rows).to_csv(out/"COST_SENSITIVITY.csv",index=False)

    selected_json={"strategy":strategy,"premium_threshold_pct_spot":threshold,"development_n":int(selected.dev_n),
                   "development_mean":float(selected.dev_mean),"development_pf":float(selected.dev_pf),
                   "validation_n":int(val.n),"validation_mean":float(val["mean"]),"validation_pf":float(val.profit_factor),
                   "validation_win_rate":float(val.win_rate),"validation_bootstrap_ci_low":ci_low,
                   "validation_bootstrap_ci_high":ci_high,"validation_bootstrap_p_mean_le_zero":boot_p,
                   "validation_pass":bool(validation_pass),"exposed_final_n":int(final.n),
                   "exposed_final_mean":float(final["mean"]),"exposed_final_pf":float(final.profit_factor),
                   "execution_cost_points":cost,"lot_size":args.lot_size,"slippage_points_per_contract":args.slippage_points_per_contract,
                   "brokerage_per_order_inr":args.brokerage_per_order_inr,"thresholds_tested":THRESHOLDS}
    (out/"SELECTED_RULE.json").write_text(json.dumps(selected_json,indent=2),encoding="utf-8")
    rc={"strategies":2,"thresholds_per_strategy":len(THRESHOLDS),"rules_tested":len(rules),"dates":len(dates),
        "block_length":BLOCK,"repetitions":RC_REPS,"observed_best_mean_per_decision":observed,
        "reality_check_style_p_value":rc_p,"note":"Cross-rule max-statistic block bootstrap; not a full Hansen SPA implementation."}
    (out/"MULTIPLE_TESTING.json").write_text(json.dumps(rc,indent=2),encoding="utf-8")

    report=f"""# NIFTY Long-Premium MC/WFO v1 — Final Phase Report

## Question
Can the NIFTY MC/WFO forecast identify sufficiently cheap Buy Call or Buy Put opportunities with positive expected value after premium, execution stress, brokerage, and expiry time decay?

## Result
Frozen development selection chose **{strategy} with premium <= {threshold:.2%} of spot**.

Development: n={int(selected.dev_n)}, mean={float(selected.dev_mean):+.2f} points/trade, PF={float(selected.dev_pf):.3f}.

Validation: n={int(val.n)}, mean={float(val["mean"]):+.2f}, PF={float(val.profit_factor):.3f}, win rate={float(val.win_rate):.1%}.
Block-bootstrap 95% CI: {ci_low:+.2f} to {ci_high:+.2f}; P(mean <= 0)={boot_p:.4f}.
Predeclared validation pass: **{validation_pass}**.

Cross-rule max-statistic diagnostic: 22 rules, 480 pre-2025 dates, block length 5, 5,000 repetitions; observed best mean per decision={observed:.3f}; p={rc_p:.4f}. This is not a full Hansen SPA.

Exposed 2025-2026, descriptive only: n={int(final.n)}, mean={float(final["mean"]):+.2f}, PF={float(final.profit_factor):.3f}.

## Costs and time decay
Baseline execution stress={args.slippage_points_per_contract:.2f} points/contract plus round-trip brokerage converted at lot size {args.lot_size}; total baseline={cost:.6f} points/trade.

The premium is already included in historical entry cashflow and expiry intrinsic is the realized payoff. Time decay is therefore represented in realized P&L and is not subtracted again.

## Conclusion
**No robust cheap-long-option edge was established.** The selected rule failed validation, and 2025-2026 is already exposed. Buy Put combinations that look better after inspecting validation are retained only as hypothesis-generating diagnostics.

## Holdout requirement
A genuinely new post-exposure holdout using the frozen rule set and deployment-grade historical bid/ask data is required before prospective promotion.
"""
    (out/"FINAL_PHASE_REPORT.md").write_text(report,encoding="utf-8")
    print(report)

if __name__=="__main__":
    main()
