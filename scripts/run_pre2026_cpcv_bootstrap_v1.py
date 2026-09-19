from __future__ import annotations
import argparse, itertools
from pathlib import Path
import numpy as np, pandas as pd
from nifty_mc.strategy_catalog import STRATEGY_NAMES

MIN_N=30
CONTRACTS={
"Buy Call":1,"Sell Put":1,"Bull Call Spread":2,"Bull Put Spread":2,"Call Ratio Back Spread":3,
"Long Calendar with Calls":2,"Bull Condor":4,"Bull Butterfly":4,"Range Forward":2,"Long Synthetic Future":2,
"Call Ratio Spread":3,"Put Ratio Spread":3,"Long Straddle":2,"Long Iron Butterfly":4,"Long Strangle":2,
"Long Iron Condor":4,"Strip":3,"Strap":3,"Short Straddle":2,"Iron Butterfly":4,"Short Strangle":2,
"Short Iron Condor":4,"Batman":6,"Double Plateau":6,"Jade Lizard":3,"Reverse Jade Lizard":3,
"Buy Put":1,"Sell Call":1,"Bear Put Spread":2,"Bear Call Spread":2,"Put Ratio Back Spread":3,
"Long Calendar with Puts":2,"Bear Condor":4,"Bear Butterfly":4,"Risk Reversal":2,"Short Synthetic Future":2}

def pf(x):
 x=np.asarray(x,float); x=x[np.isfinite(x)]; loss=-x[x<0].sum(); gain=x[x>0].sum()
 return float(gain/loss) if loss>0 else np.inf
def summary(x):
 x=np.asarray(x,float); x=x[np.isfinite(x)]
 if not len(x): return {"n":0,"mean":np.nan,"total":0.0,"pf":np.nan,"win_rate":np.nan}
 return {"n":len(x),"mean":float(x.mean()),"total":float(x.sum()),"pf":pf(x),"win_rate":float(np.mean(x>0))}
def mean_se(x):
 x=np.asarray(x,float); x=x[np.isfinite(x)]
 if not len(x): return np.nan,np.nan,np.nan
 m=float(x.mean()); se=float(x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else 0.
 return m,se,m-se
def trailing_rank(s,w):
 a=pd.to_numeric(s,errors="coerce").to_numpy(float); out=np.full(len(a),np.nan)
 for i,v in enumerate(a):
  h=a[max(0,i-w):i]; h=h[np.isfinite(h)]
  if len(h)>=30 and np.isfinite(v): out[i]=float(np.mean(h<=v))
 return out
def add_vol_regime(df,w,qlo,qhi):
 x=df.copy()
 if "decision_id" not in x: x["decision_id"]=x["decision_date"].astype(str)
 b=x.sort_values(["decision_date","decision_id"]).drop_duplicates("decision_id",keep="first").copy()
 b["rv20_rank"]=trailing_rank(b["rv20"],w)
 b["vol_regime"]=np.where(b.rv20_rank<=qlo,"low",np.where(b.rv20_rank<=qhi,"medium","high"))
 return x.drop(columns=["rv20_rank","vol_regime"],errors="ignore").merge(
  b[["decision_id","rv20_rank","vol_regime"]],on="decision_id",how="left",validate="many_to_one")
def prepare(df,cost):
 x=df.copy()
 x["realized_pnl"]=pd.to_numeric(x.realized_pnl,errors="coerce"); x["mc_ev"]=pd.to_numeric(x.mc_ev,errors="coerce")
 x["contracts"]=x["strategy"].map(CONTRACTS)
 if x.contracts.isna().any(): raise ValueError("Missing contract count for strategy")
 x["net_pnl"]=x.realized_pnl-cost*x.contracts; x["net_mc_ev"]=x.mc_ev-cost*x.contracts
 x["gate"]=np.isfinite(x.net_pnl)&np.isfinite(x.net_mc_ev)&(x.net_mc_ev>0)
 return x
def select_strategy(train,regime):
 g=train[(train.vol_regime==regime)&train.gate]; rows=[]
 for s in STRATEGY_NAMES:
  z=g[g.strategy==s]
  if len(z)<MIN_N: continue
  m,se,score=mean_se(z.net_pnl)
  if score>0: rows.append((score,m,pf(z.net_pnl),len(z),s))
 if not rows: return None
 return max(rows)[-1]
def groups(dates,n):
 u=pd.Series(sorted(pd.to_datetime(dates).drop_duplicates())); out={}
 for gi,idx in enumerate(np.array_split(np.arange(len(u)),n)):
  for j in idx: out[pd.Timestamp(u.iloc[j])]=gi
 return out
def bootstrap(x,block,n,seed):
 x=np.asarray(x,float); x=x[np.isfinite(x)]
 rng=np.random.default_rng(seed); bs=[x[i:i+block] for i in range(0,len(x),block)]; means=[]
 for _ in range(n):
  z=[]
  while len(z)<len(x): z.extend(bs[int(rng.integers(len(bs)))])
  means.append(np.mean(z[:len(x)]))
 b=np.asarray(means)
 return float(np.quantile(b,.025)),float(np.quantile(b,.975)),float(np.mean(b<=0))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--trades",required=True); ap.add_argument("--out-dir",required=True)
 ap.add_argument("--lookback",type=int,default=63); ap.add_argument("--qlo",type=float,default=.20); ap.add_argument("--qhi",type=float,default=.80)
 ap.add_argument("--cost",type=float,default=2); ap.add_argument("--groups",type=int,default=6); ap.add_argument("--test-groups",type=int,default=2)
 ap.add_argument("--block",type=int,default=5); ap.add_argument("--bootstrap",type=int,default=10000); a=ap.parse_args()
 out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
 t=pd.read_csv(a.trades,parse_dates=["decision_date"]); t.decision_date=pd.to_datetime(t.decision_date).dt.normalize()
 t=t[t.decision_date.dt.year<=2025].copy()
 if set(t.strategy.dropna().astype(str).unique())!=set(STRATEGY_NAMES): raise SystemExit("Frozen 36-strategy universe mismatch")
 t=prepare(add_vol_regime(t,a.lookback,a.qlo,a.qhi),a.cost)
 gm=groups(t.decision_date,a.groups); combos=list(itertools.combinations(range(a.groups),a.test_groups))
 rows=[]; pbo=[]; pooled=[]
 for tg in combos:
  train_dates={d for d,g in gm.items() if g not in tg}; test_dates={d for d,g in gm.items() if g in tg}
  tr=t[t.decision_date.isin(train_dates)]; te=t[t.decision_date.isin(test_dates)]
  for reg in ("low","medium","high"):
   choice=select_strategy(tr,reg)
   if choice is None: continue
   _,_,_,_,strategy=choice
   z=te[(te.vol_regime==reg)&(te.strategy==strategy)&te.gate]; s=summary(z.net_pnl)
   rows.append({"test_groups":",".join(map(str,tg)),"regime":reg,"strategy":strategy,"train_n":int(len(tr[(tr.vol_regime==reg)&(tr.strategy==strategy)&tr.gate])),**s})
   scores=[]
   for cand in STRATEGY_NAMES:
    cz=te[(te.vol_regime==reg)&(te.strategy==cand)&te.gate]
    if len(cz)>=3: scores.append(cz.net_pnl.mean())
   pct=float(np.mean(np.asarray(scores)<=s["mean"])) if scores and np.isfinite(s["mean"]) else np.nan
   pbo.append({"test_groups":",".join(map(str,tg)),"regime":reg,"strategy":strategy,"test_rank_percentile":pct,"under_median":bool(np.isfinite(pct) and pct<.5)})
   if len(z): pooled.append(z.net_pnl.to_numpy())
 sel=pd.DataFrame(rows); pbo=pd.DataFrame(pbo)
 if not pooled: raise SystemExit("No CPCV selected returns")
 vals=np.concatenate(pooled); ss=summary(vals); lo,hi,pzero=bootstrap(vals,a.block,a.bootstrap,20260919)
 sel.to_csv(out/"cpcv_selected_paths.csv",index=False); pbo.to_csv(out/"cpcv_selection_bias.csv",index=False)
 rr=[]
 for reg in ("low","medium","high"):
  z=sel[sel.regime==reg]
  rr.append({"regime":reg,"paths":len(z),"positive_mean_fraction":float(np.mean(z["mean"]>0)) if len(z) else 0,"pf_gt1_fraction":float(np.mean(z.pf>1)) if len(z) else 0,"median_test_mean":float(z["mean"].median()) if len(z) else np.nan})
 rdf=pd.DataFrame(rr); rdf.to_csv(out/"cpcv_regime_robustness.csv",index=False); pbo.to_csv(out/"cpcv_selection_bias.csv",index=False)
 freq=sel.groupby(["regime","strategy"]).size().reset_index(name="paths").sort_values(["regime","paths"],ascending=[True,False]); freq.to_csv(out/"cpcv_strategy_frequencies.csv",index=False)
 pbo_rate=float(pbo.under_median.mean()); robust=ss["mean"]>0 and ss["pf"]>1 and lo>0 and pzero<.05 and pbo_rate<.5 and (rdf.positive_mean_fraction>=.5).all() and (rdf.pf_gt1_fraction>=.5).all()
 lines=["# Pre-2026 CPCV + Block Bootstrap Regime Discovery v1","","2026 is completely excluded. All 36 strategies remain candidates.",
 f"Decision-level past-only RV20 rank: lookback={a.lookback}, thresholds={a.qlo:.2f}/{a.qhi:.2f}.",
 f"Correct contract-count stress: {a.cost:.1f} points/contract; gate=net MC EV > 0.",
 f"CPCV: {a.groups} chronological groups, {a.test_groups}-group test combinations = {len(combos)} paths.",
 "Each path selects from training groups only using n>=30 and mean-SE>0.",
 f"Block bootstrap: {a.bootstrap} resamples, block={a.block}.","",
 "## CPCV aggregate",f"- Selected test observations across paths: {ss['n']}",f"- Mean net P&L: {ss['mean']:.2f}",
 f"- Profit factor: {ss['pf']:.2f}",f"- Total net P&L: {ss['total']:.2f}",f"- Win rate: {ss['win_rate']:.2%}",
 f"- Block-bootstrap 95% CI for mean: {lo:.2f} to {hi:.2f}",f"- Bootstrap probability mean <= 0: {pzero:.3f}","",
 "## Selection-bias diagnostic",f"- Selected strategy below median available test strategy: {pbo_rate:.2%} of regime-path selections","",
 "## Regime robustness"]
 for r in rr: lines.append(f"- {r['regime']}: paths={r['paths']}, positive-mean paths={r['positive_mean_fraction']:.1%}, PF>1 paths={r['pf_gt1_fraction']:.1%}, median test mean={r['median_test_mean']:.2f}")
 lines+=["","## Strategy selection frequency"]
 for _,r in freq.iterrows(): lines.append(f"- {r.regime} -> {r.strategy}: {int(r.paths)}/{len(combos)} paths")
 lines+=["","## Decision",f"- Pre-2026 robustness screen: {'PASS' if robust else 'FAIL'}.",
 "This is pre-2026 evidence only. It does not reopen or replace the already-used 2026 holdout."]
 (out/"pre2026_cpcv_bootstrap_report.md").write_text("\n".join(lines)+"\n"); print("\n".join(lines))
if __name__=="__main__": main()
