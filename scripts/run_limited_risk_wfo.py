from __future__ import annotations
import argparse, itertools, json, zlib
from pathlib import Path
import numpy as np
import pandas as pd
from nifty_mc.strategy_catalog import STRATEGY_NAMES, STRATEGY_META, build_strategy

DUMMY={"p10":80.0,"p20":85.0,"p25":90.0,"p35":95.0,"p45":98.0,"atm":100.0,"c55":102.0,"c65":105.0,"c75":110.0,"c80":115.0,"c90":120.0}

def contract_count(strategy):
    return int(sum(abs(int(leg.qty)) for leg in build_strategy(strategy,DUMMY)))

def risk_audit(strategy):
    legs=build_strategy(strategy,DUMMY)
    call_slope=sum(leg.qty for leg in legs if leg.option_type=="CE")
    all_front=all(leg.expiry=="front" for leg in legs)
    loss_unbounded=call_slope<0
    profit_unbounded=call_slope>0
    grid=np.linspace(0.0,200.0,20001)
    payoff=np.zeros_like(grid)
    for leg in legs:
        intrinsic=np.maximum(grid-leg.strike if leg.option_type=="CE" else leg.strike-grid,0.0)
        payoff+=leg.qty*intrinsic
    core=(not loss_unbounded) and all_front
    if core:
        risk_class="R1" if profit_unbounded else "R2"
        status="PASS"
    elif (not all_front) and (not loss_unbounded):
        risk_class="R3"; status="SEPARATE_PATH_STUDY"
    else:
        risk_class="X"; status="FAIL"
    return {"strategy":strategy,"family":STRATEGY_META[strategy][1],"bias":STRATEGY_META[strategy][0],
            "contracts_per_unit":contract_count(strategy),"all_front_expiry":all_front,
            "call_tail_slope":int(call_slope),"loss_unbounded":bool(loss_unbounded),
            "profit_unbounded":bool(profit_unbounded),"risk_class":risk_class,
            "core_limited_risk":bool(core),"intrinsic_payoff_min":float(payoff.min()),
            "intrinsic_payoff_max":float(payoff.max()),"audit_status":status,
            "legs":[leg.__dict__ for leg in legs]}

def summary(x):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    if len(x)==0:return {"n":0,"mean":np.nan,"median":np.nan,"total":0.0,"win_rate":np.nan,"profit_factor":np.nan,"max_drawdown":np.nan,"min_trade":np.nan,"sharpe_trade":np.nan}
    eq=np.cumsum(x); dd=eq-np.maximum.accumulate(eq)
    gains=float(x[x>0].sum()); losses=float(-x[x<0].sum())
    sd=float(np.std(x,ddof=1)) if len(x)>1 else np.nan
    return {"n":int(len(x)),"mean":float(x.mean()),"median":float(np.median(x)),"total":float(x.sum()),
            "win_rate":float(np.mean(x>0)),"profit_factor":float(gains/losses) if losses>0 else np.inf,
            "max_drawdown":float(dd.min()),"min_trade":float(x.min()),
            "sharpe_trade":float(x.mean()/sd*np.sqrt(len(x))) if np.isfinite(sd) and sd>0 else np.nan}

def stable_seed(label,base=20260920):
    return int((base+zlib.crc32(label.encode("utf-8")))% (2**32-1))

def block_bootstrap_mean_ci(x,block,n_iter,seed):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)==0:return np.nan,np.nan,np.nan
    block=max(1,min(int(block),len(x))); starts=np.arange(len(x)-block+1); rng=np.random.default_rng(seed); vals=np.empty(n_iter)
    for i in range(n_iter):
        sample=[]
        while len(sample)<len(x):
            s=int(rng.choice(starts)); sample.extend(x[s:s+block].tolist())
        vals[i]=np.mean(sample[:len(x)])
    return float(np.quantile(vals,.025)),float(np.quantile(vals,.975)),float(np.mean(vals<=0))

def cpcv_pre2025(t,eligible,groups_n=6,test_groups=2):
    pre=t[t.year<=2024].copy(); dates=pd.Series(sorted(pre.decision_date.dropna().unique()))
    if len(dates)<groups_n:return pd.DataFrame()
    chunks=np.array_split(dates.to_numpy(),groups_n); gm={d:i for i,c in enumerate(chunks) for d in c}; pre["cpcv_group"]=pre.decision_date.map(gm); rows=[]
    for tg in itertools.combinations(range(groups_n),test_groups):
        tgset=set(tg); train=pre[(~pre.cpcv_group.isin(tgset))&pre.gate]; test=pre[pre.cpcv_group.isin(tgset)&pre.gate]
        cand=[]
        for s in eligible:
            x=train.loc[train.strategy.eq(s),"net_pnl"].to_numpy(float)
            if len(x)<20: continue
            m=float(x.mean()); se=float(x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else 0.0
            if m-se>0:cand.append((m-se,s,len(x)))
        if cand: score,chosen,tn=max(cand)
        else: score,chosen,tn=np.nan,"NO_TRADE",0
        z=test.loc[test.strategy.eq(chosen),"net_pnl"].to_numpy(float) if chosen!="NO_TRADE" else np.array([])
        ss=summary(z); rows.append({"test_groups":"-".join(map(str,tg)),"chosen_strategy":chosen,"train_n":tn,"train_score":score,
                                    "test_n":ss["n"],"test_mean":ss["mean"],"test_total":ss["total"],"test_pf":ss["profit_factor"],"test_win_rate":ss["win_rate"]})
    return pd.DataFrame(rows)

def reality_check_style(t,eligible,block=5,n_iter=5000):
    pre=t[t.year<=2024].copy(); dates=pd.DatetimeIndex(sorted(pre.decision_date.dropna().unique()))
    if len(dates)==0:return {}
    pnl=pre.pivot_table(index="decision_date",columns="strategy",values="net_pnl",aggfunc="first").reindex(index=dates,columns=eligible)
    gate=pre.pivot_table(index="decision_date",columns="strategy",values="gate",aggfunc="first").reindex(index=dates,columns=eligible).fillna(False)
    mat=pnl.where(gate,0.0).fillna(0.0).to_numpy(float); observed=float(mat.mean(axis=0).max())
    b=max(1,min(block,len(dates))); starts=np.arange(len(dates)-b+1); rng=np.random.default_rng(stable_seed("limited-risk-reality-check")); sims=np.empty(n_iter)
    for i in range(n_iter):
        idx=[]
        while len(idx)<len(dates):
            s=int(rng.choice(starts)); idx.extend(range(s,min(s+b,len(dates))))
        sims[i]=mat[idx[:len(dates)]].mean(axis=0).max()
    return {"observed_best_mean_per_decision":observed,"bootstrap_p_value":float(np.mean(sims>=observed)),
            "strategies_tested":len(eligible),"dates":len(dates),"block_length":b,"bootstrap_repetitions":n_iter,
            "interpretation":"Reality-check-style max-statistic block bootstrap; not a claim of a full Hansen SPA implementation."}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--trades",required=True); ap.add_argument("--out-dir",required=True)
    ap.add_argument("--cost-per-contract",type=float,default=2.0); ap.add_argument("--lot-size",type=int,default=65)
    ap.add_argument("--bootstrap",type=int,default=10000); args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)

    risk=[risk_audit(s) for s in STRATEGY_NAMES]; rdf=pd.DataFrame(risk)
    rdf.to_json(out/"risk_audit_full.json",orient="records",indent=2); rdf.drop(columns=["legs"]).to_csv(out/"risk_audit_full.csv",index=False)
    eligible=rdf.loc[rdf.core_limited_risk,"strategy"].tolist()

    t=pd.read_csv(args.trades,parse_dates=["decision_date"])
    req={"strategy","decision_date","realized_pnl","mc_ev","vol_regime"}; missing=req-set(t.columns)
    if missing: raise SystemExit(f"strategy_trades.csv missing columns: {sorted(missing)}")
    cmap=dict(zip(rdf.strategy,rdf.contracts_per_unit)); t["decision_date"]=pd.to_datetime(t.decision_date).dt.normalize(); t["year"]=t.decision_date.dt.year
    t=t[t.strategy.isin(eligible)].copy(); t["contracts"]=t.strategy.map(cmap); t["stress_cost_points"]=t.contracts*args.cost_per_contract
    t["net_pnl"]=pd.to_numeric(t.realized_pnl,errors="coerce")-t.stress_cost_points; t["net_mc_ev"]=pd.to_numeric(t.mc_ev,errors="coerce")-t.stress_cost_points; t["gate"]=np.isfinite(t.net_mc_ev)&(t.net_mc_ev>0)
    t["period"]=np.select([t.year<=2022,t.year<=2024],["development","validation"],default="exposed_final")

    broad=[]
    for period,frame in t.groupby("period",sort=False):
        for strategy,g in frame.groupby("strategy"):
            a=summary(g.net_pnl.to_numpy(float)); b=summary(g.loc[g.gate,"net_pnl"].to_numpy(float))
            broad.append({"period":period,"strategy":strategy,"risk_class":rdf.loc[rdf.strategy.eq(strategy),"risk_class"].iloc[0],
                           "all_n":a["n"],"all_mean":a["mean"],"all_total":a["total"],"all_pf":a["profit_factor"],"all_win_rate":a["win_rate"],"all_dd":a["max_drawdown"],
                           "gated_n":b["n"],"gated_mean":b["mean"],"gated_total":b["total"],"gated_pf":b["profit_factor"],"gated_win_rate":b["win_rate"],"gated_dd":b["max_drawdown"]})
    broad_df=pd.DataFrame(broad); broad_df.to_csv(out/"broad_limited_risk_summary.csv",index=False)

    sel=[]
    for s in eligible:
        vals={}
        for p in ("development","validation","exposed_final"):
            g=t[(t.strategy==s)&(t.period==p)&t.gate]; vals[p]=summary(g.net_pnl.to_numpy(float))
        sd,sv,sf=vals["development"],vals["validation"],vals["exposed_final"]; se=sd["mean"]/np.sqrt(sd["n"]) if sd["n"] else np.nan
        sel.append({"strategy":s,"dev_n":sd["n"],"dev_mean":sd["mean"],"dev_pf":sd["profit_factor"],"dev_score":sd["mean"]-se if sd["n"] else np.nan,
                    "validation_n":sv["n"],"validation_mean":sv["mean"],"validation_pf":sv["profit_factor"],
                    "exposed_final_n":sf["n"],"exposed_final_mean":sf["mean"],"exposed_final_pf":sf["profit_factor"]})
    sel=pd.DataFrame(sel); sel["validation_pass"]=(sel.dev_n>=20)&(sel.dev_score>0)&(sel.validation_n>=10)&(sel.validation_mean>0)&(sel.validation_pf>1)
    frozen=sel[sel.validation_pass].sort_values(["validation_mean","dev_score"],ascending=False).copy()
    sel["rank"]=np.nan
    for i,idx in enumerate(frozen.index,start=1): sel.loc[idx,"rank"]=i
    sel.to_csv(out/"nested_selection_summary.csv",index=False)

    rr=[]
    for reg in sorted(t.vol_regime.dropna().unique()):
        for s in eligible:
            dev=t[(t.strategy==s)&(t.vol_regime==reg)&(t.period=="development")&t.gate]
            if len(dev)<15: continue
            x=dev.net_pnl.to_numpy(float); m=float(x.mean()); se=float(x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else 0.0; score=m-se
            if score<=0: continue
            val=t[(t.strategy==s)&(t.vol_regime==reg)&(t.period=="validation")&t.gate]; fin=t[(t.strategy==s)&(t.vol_regime==reg)&(t.period=="exposed_final")&t.gate]
            sv,sf=summary(val.net_pnl.to_numpy(float)),summary(fin.net_pnl.to_numpy(float))
            rr.append({"regime":reg,"strategy":s,"dev_n":len(dev),"dev_mean":m,"dev_score":score,
                       "validation_n":sv["n"],"validation_mean":sv["mean"],"validation_pf":sv["profit_factor"],
                       "exposed_final_n":sf["n"],"exposed_final_mean":sf["mean"],"exposed_final_pf":sf["profit_factor"]})
    regdf=pd.DataFrame(rr); regdf.to_csv(out/"vol_regime_selection.csv",index=False); fmap={}
    for reg in sorted(t.vol_regime.dropna().unique()):
        g=regdf[regdf.regime==reg] if not regdf.empty else pd.DataFrame()
        g=g[(g.validation_n>=10)&(g.validation_mean>0)&(g.validation_pf>1)] if not g.empty else g
        if not g.empty:fmap[reg]=str(g.sort_values(["validation_mean","dev_score"],ascending=False).iloc[0].strategy)

    routes=[]
    for d,g in t.groupby("decision_date"):
        reg=str(g.iloc[0].vol_regime); s=fmap.get(reg)
        if s is None: continue
        z=g[(g.strategy==s)&g.gate]
        if z.empty: routes.append({"decision_date":d,"regime":reg,"strategy":"NO_TRADE","net_pnl":0.0})
        else: routes.append({"decision_date":d,"regime":reg,"strategy":s,"net_pnl":float(z.iloc[0].net_pnl)})
    route=pd.DataFrame(routes)
    route.to_csv(out/"vol_regime_router_trades.csv",index=False)
    rs=[]
    if not route.empty:
        for p,mask in [("development",route.decision_date.dt.year<=2022),("validation",route.decision_date.dt.year.between(2023,2024)),("exposed_final",route.decision_date.dt.year>=2025)]:
            g=route.loc[mask]; active=g[g.strategy!="NO_TRADE"]; s=summary(active.net_pnl.to_numpy(float)); rs.append({"period":p,"decisions":len(g),"trades":len(active),"coverage":len(active)/len(g) if len(g) else np.nan,**s})
    pd.DataFrame(rs).to_csv(out/"vol_regime_router_summary.csv",index=False)

    cpcv=cpcv_pre2025(t,eligible); cpcv.to_csv(out/"cpcv_pre2025.csv",index=False)
    ci=block_bootstrap_mean_ci(cpcv.loc[cpcv.chosen_strategy!="NO_TRADE","test_mean"].to_numpy(float),2,args.bootstrap,stable_seed("cpcv-pre2025")) if not cpcv.empty else (np.nan,np.nan,np.nan)
    rc=reality_check_style(t,eligible,5,max(2000,args.bootstrap//2))

    candidate=frozen.iloc[0].strategy if not frozen.empty else None; stress=[]
    if candidate:
        for cost in (0.0,0.5,1.0,2.0,3.0):
            g=t[(t.strategy==candidate)&(t.year>=2025)].copy(); g=g[g.mc_ev-g.contracts*cost>0]; s=summary((g.realized_pnl-g.contracts*cost).to_numpy(float))
            stress.append({"strategy":candidate,"stress_cost_points_per_contract":cost,**s})
    pd.DataFrame(stress).to_csv(out/"candidate_cost_stress.csv",index=False)

    lines=["# Limited-Risk Option WFO — Results","","## Risk audit",f"Mechanically core-eligible strategies: {len(eligible)} / {len(STRATEGY_NAMES)}",""]
    lines.append(rdf[["strategy","risk_class","loss_unbounded","profit_unbounded","core_limited_risk","audit_status"]].sort_values("strategy").to_string(index=False))
    lines += ["","## Validation comparison"]
    top=broad_df[(broad_df.period=="validation")&(broad_df.gated_n>=10)].sort_values("gated_mean",ascending=False).head(15) if not broad_df.empty else pd.DataFrame()
    lines.append(top.to_string(index=False) if not top.empty else "No strategy met the validation reporting floor.")
    lines += ["","## Global nested selection"]
    lines.append("No limited-risk strategy passed the predeclared development-to-validation gate." if frozen.empty else frozen[["strategy","dev_n","dev_mean","dev_pf","validation_n","validation_mean","validation_pf","exposed_final_n","exposed_final_mean","exposed_final_pf"]].to_string(index=False))
    lines += ["","## Volatility-regime selection",f"Frozen validation-qualified map: {json.dumps(fmap,sort_keys=True)}"]
    if rs: lines.append(pd.DataFrame(rs).to_string(index=False))
    lines += ["","## Pre-2025 CPCV"]
    lines.append(cpcv.to_string(index=False) if not cpcv.empty else "No CPCV selections.")
    lines.append(f"Block-bootstrap CI of selected CPCV path means: {ci[0]:.2f} to {ci[1]:.2f}; P(mean<=0)={ci[2]:.3f}.")
    lines += ["","## Multiple-testing diagnostic",json.dumps(rc,indent=2)]
    lines += ["","## Holdout status","The 2025-2026 sample is EXPOSED because the parent NIFTY MC-WFO research already reported this period. It is not a clean fresh holdout for this branch.","Fresh-holdout inference remains HOLD until genuinely new, previously unexposed option data are available."]
    lines += ["","## Execution-data limitation","The historical archive supplies EOD option close prices rather than a verified historical bid/ask stream. Results are therefore EOD reconstruction plus explicit adverse cost stress, not a bid/ask-executable backtest."]
    lines += ["","## Research conclusion","No strategy is promoted to paper/live trading by this run. Any positive historical candidate remains provisional until a fresh holdout and deployment-grade bid/ask execution data are available."]
    (out/"LIMITED_RISK_WFO_RESULTS.md").write_text("\\n".join(lines)+"\\n",encoding="utf-8")
    print("\\n".join(lines))

if __name__=="__main__": main()
