from __future__ import annotations

import argparse
import itertools
from pathlib import Path
import numpy as np
import pandas as pd
from nifty_mc.strategy_catalog import STRATEGY_NAMES

MIN_N = 30

def pf(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    loss=-x[x<0].sum(); gain=x[x>0].sum()
    return float(gain/loss) if loss>0 else np.inf

def summary(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)==0: return {"n":0,"mean":np.nan,"total":0.0,"pf":np.nan,"win_rate":np.nan}
    return {"n":int(len(x)),"mean":float(x.mean()),"total":float(x.sum()),"pf":pf(x),"win_rate":float(np.mean(x>0))}

def mean_se(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if not len(x): return np.nan,np.nan,np.nan
    m=float(x.mean()); se=float(x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else 0.0
    return m,se,m-se

def trailing_rank(s,window):
    a=pd.to_numeric(s,errors="coerce").to_numpy(float); out=np.full(len(a),np.nan)
    for i,v in enumerate(a):
        h=a[max(0,i-window):i]; h=h[np.isfinite(h)]
        if len(h)>=30 and np.isfinite(v): out[i]=float(np.mean(h<=v))
    return out

def add_vol_regime(df,lookback,qlo,qhi):
    x=df.copy()
    if "decision_id" not in x: x["decision_id"]=x["decision_date"].astype(str)
    base=x.sort_values(["decision_date","decision_id"]).drop_duplicates("decision_id",keep="first").copy()
    if "rv20" not in base: raise ValueError("rv20 is required")
    base["rv20_rank"]=trailing_rank(base.rv20,lookback)
    base["vol_regime"]=np.where(base.rv20_rank<=qlo,"low",np.where(base.rv20_rank<=qhi,"medium","high"))
    return x.drop(columns=["rv20_rank","vol_regime"],errors="ignore").merge(
        base[["decision_id","rv20_rank","vol_regime"]],on="decision_id",how="left",validate="many_to_one")

def prepare(df,cost):
    x=df.copy()
    for c in ["realized_pnl","mc_ev"]: x[c]=pd.to_numeric(x[c],errors="coerce")
    if "contracts" not in x: x["contracts"]=1.0
    x["contracts"]=pd.to_numeric(x["contracts"],errors="coerce").fillna(1.0)
    x["net_pnl"]=x.realized_pnl-cost*x.contracts
    x["net_mc_ev"]=x.mc_ev-cost*x.contracts
    x["gate"]=np.isfinite(x.net_pnl)&np.isfinite(x.net_mc_ev)&(x.net_mc_ev>0)
    return x

def select_strategy(train,regime):
    g=train[(train.vol_regime==regime)&train.gate]; rows=[]
    for strategy in STRATEGY_NAMES:
        z=g[g.strategy==strategy]
        if len(z)<MIN_N: continue
        m,se,score=mean_se(z.net_pnl.to_numpy())
        if score<=0: continue
        rows.append({"regime":regime,"strategy":strategy,"n":len(z),"mean":m,"se":se,"score":score,"pf":pf(z.net_pnl)})
    c=pd.DataFrame(rows)
    if c.empty: return None,c
    return str(c.sort_values(["score","mean","pf","n"],ascending=False).iloc[0].strategy),c

def make_groups(dates,n):
    u=pd.Series(sorted(pd.to_datetime(dates).drop_duplicates()))
    groups=np.array_split(np.arange(len(u)),n); out={}
    for gi,idx in enumerate(groups):
        for j in idx: out[pd.Timestamp(u.iloc[j])]=gi
    return out

def block_bootstrap(x,block,n_boot,seed):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)<2: return {"mean":np.nan,"ci_low":np.nan,"ci_high":np.nan,"p_mean_le_zero":np.nan}
    rng=np.random.default_rng(seed); blocks=[x[i:i+block] for i in range(0,len(x),block)]
    means=[]
    for _ in range(n_boot):
        sample=[]
        while len(sample)<len(x): sample.extend(blocks[int(rng.integers(0,len(blocks)))])
        means.append(float(np.mean(sample[:len(x)])))
    b=np.asarray(means)
    return {"mean":float(x.mean()),"ci_low":float(np.quantile(b,.025)),"ci_high":float(np.quantile(b,.975)),"p_mean_le_zero":float(np.mean(b<=0))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trades",required=True); ap.add_argument("--out-dir",required=True)
    ap.add_argument("--lookback",type=int,default=63); ap.add_argument("--qlo",type=float,default=.20); ap.add_argument("--qhi",type=float,default=.80)
    ap.add_argument("--cost",type=float,default=2.0); ap.add_argument("--groups",type=int,default=6); ap.add_argument("--test-groups",type=int,default=2)
    ap.add_argument("--block",type=int,default=5); ap.add_argument("--bootstrap",type=int,default=10000)
    a=ap.parse_args(); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    t=pd.read_csv(a.trades,parse_dates=["decision_date"]); t.decision_date=pd.to_datetime(t.decision_date).dt.normalize(); t["year"]=t.decision_date.dt.year
    if set(t.strategy.dropna().astype(str).unique())!=set(STRATEGY_NAMES): raise SystemExit("Strategy universe is not exactly the frozen 36-strategy catalog.")
    t=t[t.year<=2025].copy(); t=prepare(add_vol_regime(t,a.lookback,a.qlo,a.qhi),a.cost)
    dates=pd.Series(sorted(t.decision_date.drop_duplicates()))
    if len(dates)<a.groups: raise SystemExit("Not enough pre-2026 decision dates.")
    gm=make_groups(dates,a.groups)
    combos=list(itertools.combinations(range(a.groups),a.test_groups))
    selected_rows=[]; pbo_rows=[]; pooled=[]
    for tg in combos:
        train_dates={d for d,g in gm.items() if g not in set(tg)}; test_dates={d for d,g in gm.items() if g in set(tg)}
        train=t[t.decision_date.isin(train_dates)]; test=t[t.decision_date.isin(test_dates)]
        for regime in ("low","medium","high"):
            strategy,cands=select_strategy(train,regime)
            if strategy is None: continue
            z=test[(test.vol_regime==regime)&(test.strategy==strategy)&test.gate]; s=summary(z.net_pnl.to_numpy())
            selected_rows.append({"test_groups":",".join(map(str,tg)),"regime":regime,"strategy":strategy,
                                  "train_n":int(len(train[(train.vol_regime==regime)&(train.strategy==strategy)&train.gate])),**{f"test_{k}":v for k,v in s.items()}})
            scores=[]
            for cand in STRATEGY_NAMES:
                cz=test[(test.vol_regime==regime)&(test.strategy==cand)&test.gate]
                if len(cz)>=3: scores.append(float(cz.net_pnl.mean()))
            pct=float(np.mean(np.asarray(scores)<=s["mean"])) if scores and np.isfinite(s["mean"]) else np.nan
            pbo_rows.append({"test_groups":",".join(map(str,tg)),"regime":regime,"strategy":strategy,"test_rank_percentile":pct,"under_median":bool(np.isfinite(pct) and pct<.5)})
            if not z.empty: pooled.append(z[["decision_date","net_pnl"]].assign(test_groups=",".join(map(str,tg)),regime=regime,strategy=strategy))
    if not pooled: raise SystemExit("CPCV produced no selected test returns.")
    selected=pd.DataFrame(selected_rows); pbo=pd.DataFrame(pbo_rows); pooled_df=pd.concat(pooled,ignore_index=True)
    selected.to_csv(out/"cpcv_selected_paths.csv",index=False); pbo.to_csv(out/"cpcv_selection_bias.csv",index=False); pooled_df.to_csv(out/"cpcv_pooled_selected_returns.csv",index=False)
    ps=summary(pooled_df.net_pnl); boot=block_bootstrap(pooled_df.net_pnl,a.block,a.bootstrap,20260919); pbo_rate=float(pbo.under_median.mean()) if len(pbo) else np.nan
    rr=[]
    for regime in ("low","medium","high"):
        z=selected[selected.regime==regime]; rr.append({"regime":regime,"paths":len(z),
          "positive_mean_fraction":float(np.mean(z.test_mean>0)) if len(z) else 0.0,
          "pf_gt1_fraction":float(np.mean(z.test_pf>1)) if len(z) else 0.0,
          "median_test_mean":float(z.test_mean.median()) if len(z) else np.nan})
    rdf=pd.DataFrame(rr); rdf.to_csv(out/"cpcv_regime_robustness.csv",index=False)
    robust=(ps["mean"]>0 and ps["pf"]>1 and boot["ci_low"]>0 and pbo_rate<.50 and
            (rdf.positive_mean_fraction>=.50).all() and (rdf.pf_gt1_fraction>=.50).all())
    lines=[
      "# Pre-2026 CPCV + Block Bootstrap Regime Discovery v1","",
      "2026 is completely excluded. All 36 strategies remain candidates.",
      f"Volatility regime: decision-level past-only RV20 rank, lookback={a.lookback}, thresholds={a.qlo:.2f}/{a.qhi:.2f}.",
      f"Cost stress: {a.cost:.1f} points/contract; strategy gate: net MC EV > 0.",
      f"CPCV: {a.groups} chronological groups, {a.test_groups}-group test combinations = {len(combos)} paths.",
      "Each path selects from training groups only using n>=30 and mean-SE>0.",
      f"Block bootstrap: {a.bootstrap} resamples, block length {a.block}.","",
      "## CPCV aggregate",
      f"- Selected test observations across paths: {ps['n']}",
      f"- Mean net P&L: {ps['mean']:.2f}",
      f"- Profit factor: {ps['pf']:.2f}",
      f"- Total net P&L: {ps['total']:.2f}",
      f"- Win rate: {ps['win_rate']:.2%}",
      f"- Block-bootstrap 95% CI for mean: {boot['ci_low']:.2f} to {boot['ci_high']:.2f}",
      f"- Bootstrap probability mean <= 0: {boot['p_mean_le_zero']:.3f}","",
      "## Selection-bias diagnostic",
      f"- Selected strategy below median available test strategy: {pbo_rate:.2%} of regime-path selections","",
      "## Regime robustness"]
    for r in rr: lines.append(f"- {r['regime']}: paths={r['paths']}, positive-mean paths={r['positive_mean_fraction']:.1%}, PF>1 paths={r['pf_gt1_fraction']:.1%}, median test mean={r['median_test_mean']:.2f}")
    lines += ["","## Decision",f"- Pre-2026 robustness screen: {'PASS' if robust else 'FAIL'}.",
              "- PASS permits a separately declared final holdout evaluation; FAIL keeps the router research-only."]
    report="\n".join(lines)+"\n"; (out/"pre2026_cpcv_bootstrap_report.md").write_text(report); print(report)

if __name__=="__main__": main()
