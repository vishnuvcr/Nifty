from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import STRATEGY_NAMES, STRATEGY_META, build_strategy

def nearest_unique_strikes(strikes: np.ndarray, targets: dict[str, float]) -> dict[str, float] | None:
    strikes=np.sort(np.unique(strikes.astype(float)))
    if len(strikes)<12:
        return None
    items=sorted(targets.items(), key=lambda kv: kv[1])
    used=set()
    out={}
    for label,target in items:
        order=np.argsort(np.abs(strikes-target))
        pick=None
        for ix in order:
            v=float(strikes[ix])
            if v not in used:
                pick=v
                break
        if pick is None:
            return None
        out[label]=pick
        used.add(pick)
    return out

def option_price(chain: pd.DataFrame, expiry: pd.Timestamp, typ: str, strike: float):
    x=chain[(chain["expiry"]==expiry)&(chain["option_type"]==typ)&(chain["strike"]==float(strike))]
    if x.empty:
        return None
    v=float(pd.to_numeric(x.iloc[0]["close"],errors="coerce"))
    return None if not np.isfinite(v) or v<=0 else v

def payoff_terminal(terminal: np.ndarray, legs):
    total=np.zeros(len(terminal),dtype=float)
    for leg,price in legs:
        intrinsic=np.maximum((terminal-leg.strike) if leg.option_type=="CE" else (leg.strike-terminal),0.0)
        total += leg.qty*intrinsic
    entry=-sum(leg.qty*price for leg,price in legs)
    return total+entry, float(entry)

def realized_calendar_pnl(front_spot: float, front_chain: pd.DataFrame, next_chain_at_front: pd.DataFrame,
                          legs, front_expiry: pd.Timestamp, next_expiry: pd.Timestamp):
    entry=0.0
    pnl=0.0
    for leg in legs:
        chain = front_chain if leg.expiry=="front" else next_chain_at_front
        exp = front_expiry if leg.expiry=="front" else next_expiry
        px=option_price(chain,exp,leg.option_type,leg.strike)
        if px is None:
            return None
        entry -= leg.qty*px
        if leg.expiry=="front":
            intrinsic=max(front_spot-leg.strike,0.0) if leg.option_type=="CE" else max(leg.strike-front_spot,0.0)
            pnl += leg.qty*intrinsic
        else:
            pnl += leg.qty*px
    return pnl+entry, entry

def mc_terminal(spot: float, returns: np.ndarray, horizon_days: int, n: int, seed: int):
    r=returns[np.isfinite(returns)]
    if len(r)<60:
        return None
    rng=np.random.default_rng(seed)
    h=max(1,int(horizon_days))
    sampled=rng.choice(r,size=n*h,replace=True).reshape(n,h)
    return spot*np.exp(sampled.sum(axis=1))

def decision_features(idx: pd.DataFrame, decision: pd.Timestamp, terminal: np.ndarray, spot: float):
    s=idx[idx["date"]<=decision]["close"].to_numpy(float)
    r=idx[idx["date"]<=decision]["logret"].dropna().to_numpy(float)
    if len(s)<80 or len(r)<60:
        return None
    rv20=float(np.std(r[-20:],ddof=1)*np.sqrt(252))
    rv60=float(np.std(r[-60:],ddof=1)*np.sqrt(252))
    trend20=float(s[-1]/s[-21]-1)
    trend60=float(s[-1]/s[-61]-1)
    tail=r[-60:]
    skew=float(pd.Series(tail).skew())
    kurt=float(pd.Series(tail).kurt())
    ac=float(pd.Series(tail).autocorr(lag=1))
    jump=float(np.mean(np.abs(tail) > 2*np.std(tail,ddof=1)))
    p_up=float(np.mean(terminal>spot*1.005))
    p_down=float(np.mean(terminal<spot*0.995))
    p_range=float(np.mean((terminal>=spot*0.995)&(terminal<=spot*1.005)))
    p_expand=float(np.mean(np.abs(terminal/spot-1)>=0.015))
    med_ret=float(np.median(terminal)/spot-1)
    if p_up>p_down+0.08 and med_ret>0:
        pred="bull"
    elif p_down>p_up+0.08 and med_ret<0:
        pred="bear"
    elif p_range>=max(p_up,p_down):
        pred="range"
    else:
        pred="breakout"
    return dict(rv20=rv20,rv60=rv60,trend20=trend20,trend60=trend60,skew60=skew,
                kurt60=kurt,autocorr60=ac,jump_rate60=jump,p_up=p_up,p_down=p_down,
                p_range=p_range,p_expand=p_expand,mc_median_return=med_ret,
                direction_prediction=pred)

def summarize(frame: pd.DataFrame, cost_per_leg: float=0.0):
    if frame.empty:
        return dict(trades=0,win_rate=np.nan,mean_pnl=np.nan,median_pnl=np.nan,total_pnl=0.0,
                    max_drawdown=np.nan,profit_factor=np.nan)
    pnl=frame["realized_pnl"].to_numpy(float)-frame["n_legs"].to_numpy(float)*cost_per_leg
    eq=np.cumsum(pnl)
    dd=eq-np.maximum.accumulate(eq)
    gains=pnl[pnl>0].sum()
    losses=-pnl[pnl<0].sum()
    return dict(trades=len(frame),win_rate=float(np.mean(pnl>0)),mean_pnl=float(np.mean(pnl)),
                median_pnl=float(np.median(pnl)),total_pnl=float(np.sum(pnl)),
                max_drawdown=float(np.min(dd)),profit_factor=float(gains/losses) if losses>0 else np.inf)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--index",required=True)
    ap.add_argument("--options-dir",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--paths",type=int,default=5000)
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)

    idx=pd.read_csv(args.index,parse_dates=["date"]).sort_values("date")
    idx["close"]=pd.to_numeric(idx["close"],errors="coerce")
    idx=idx.dropna(subset=["date","close"]).drop_duplicates("date").reset_index(drop=True)
    idx["logret"]=np.log(idx["close"]).diff()
    price_by_date=dict(zip(idx["date"].dt.normalize(),idx["close"]))

    opt_parts=[]; target_files=[]
    for p in sorted(Path(args.options_dir).rglob("nifty_options_*.csv.gz")):
        d=pd.read_csv(p,parse_dates=["timestamp","expiry"],low_memory=False)
        d["timestamp"]=pd.to_datetime(d["timestamp"]).dt.normalize()
        d["expiry"]=pd.to_datetime(d["expiry"]).dt.normalize()
        d["strike"]=pd.to_numeric(d["strike"],errors="coerce")
        d["close"]=pd.to_numeric(d["close"],errors="coerce")
        d["option_type"]=d["option_type"].astype(str).str.upper()
        d=d[(d["symbol"].astype(str).str.upper()=="NIFTY")&d["option_type"].isin(["CE","PE"])&
            d["strike"].notna()&d["close"].notna()]
        opt_parts.append(d)
        y=p.name.split("_")[-1].split(".")[0]
        target_files.extend(Path(args.options_dir).rglob(f"targets_{y}.csv"))
    opt=pd.concat(opt_parts,ignore_index=True)
    by_day={k:g for k,g in opt.groupby("timestamp",sort=False)}
    targets=[]
    for p in sorted(set(target_files)):
        t=pd.read_csv(p)
        col="target_expiry" if "target_expiry" in t.columns else "expiry"
        t["decision_date"]=pd.to_datetime(t["decision_date"]).dt.normalize()
        t["target_expiry"]=pd.to_datetime(t[col]).dt.normalize()
        targets.append(t[["decision_date","target_expiry"]])
    targ=pd.concat(targets,ignore_index=True).drop_duplicates().sort_values("decision_date")

    rows=[]; decisions=[]
    for i,t in enumerate(targ.itertuples(index=False)):
        decision=t.decision_date; target_exp=t.target_expiry
        spot=price_by_date.get(decision); day=by_day.get(decision)
        if spot is None or day is None:
            continue
        exps=sorted(pd.to_datetime(day["expiry"].dropna().unique()))
        actual=[e for e in exps if e>=target_exp]
        if not actual:
            continue
        front_exp=pd.Timestamp(actual[0]).normalize()
        nexts=[e for e in exps if e>front_exp]
        next_exp=pd.Timestamp(nexts[0]).normalize() if nexts else None
        sessions=idx[(idx["date"]>decision)&(idx["date"]<=front_exp)]
        if sessions.empty:
            continue
        exp_session=sessions.iloc[-1]["date"].normalize()
        horizon=len(sessions)
        hist=idx[idx["date"]<=decision]["logret"].dropna().tail(756).to_numpy()
        terminal=mc_terminal(float(spot),hist,horizon,args.paths,100000+i)
        if terminal is None:
            continue
        qs=np.percentile(terminal,[10,20,25,35,45,55,65,75,80,90])
        targets_map={"p10":qs[0],"p20":qs[1],"p25":qs[2],"p35":qs[3],"p45":qs[4],
                     "atm":float(spot),"c55":qs[5],"c65":qs[6],"c75":qs[7],"c80":qs[8],"c90":qs[9]}
        strikes=nearest_unique_strikes(day["strike"].dropna().unique(),targets_map)
        if strikes is None:
            continue
        chain=day[day["expiry"]==front_exp]
        if chain.empty:
            continue
        feats=decision_features(idx,decision,terminal,float(spot))
        if feats is None:
            continue
        decision_id=f"{decision.date()}|{front_exp.date()}"
        decisions.append({"decision_id":decision_id,"decision_date":decision,"actual_expiry":front_exp,
                          "expiry_session":exp_session,"spot":float(spot),**feats})
        for name in STRATEGY_NAMES:
            legs=build_strategy(name,strikes)
            priced=[]; ok=True
            for leg in legs:
                exp=front_exp if leg.expiry=="front" else next_exp
                if exp is None:
                    ok=False; break
                px=option_price(chain if leg.expiry=="front" else day,exp,leg.option_type,leg.strike)
                if px is None:
                    ok=False; break
                priced.append((leg,px))
            if not ok:
                continue
            meta=STRATEGY_META[name]
            if any(leg.expiry=="next" for leg in legs):
                next_chain=by_day.get(exp_session)
                if next_chain is None:
                    continue
                next_chain=next_chain[next_chain["expiry"]==next_exp]
                if next_chain.empty:
                    continue
                realized=realized_calendar_pnl(float(price_by_date[exp_session]),chain,next_chain,legs,front_exp,next_exp)
                if realized is None:
                    continue
                realized_pnl,entry_cash=realized
                mc_ev=np.nan; mc_pop=np.nan; settlement="front_expiry_mtm"
            else:
                pnl_paths,entry_cash=payoff_terminal(terminal,priced)
                mc_ev=float(np.mean(pnl_paths)); mc_pop=float(np.mean(pnl_paths>0))
                realized_spot=float(price_by_date[exp_session]); realized=0.0
                for leg,_ in priced:
                    intrinsic=max(realized_spot-leg.strike,0.0) if leg.option_type=="CE" else max(leg.strike-realized_spot,0.0)
                    realized += leg.qty*intrinsic
                realized_pnl=float(realized+entry_cash); settlement="expiry"
            rows.append({"decision_id":decision_id,"decision_date":decision.date(),"actual_expiry":front_exp.date(),
                         "expiry_session":exp_session.date(),"spot":float(spot),"strategy":name,
                         "family":meta[1],"bias":meta[0],"n_legs":len(legs),"entry_cashflow":float(entry_cash),
                         "realized_pnl":float(realized_pnl),"win":int(realized_pnl>0),"mc_ev":mc_ev,"mc_pop":mc_pop,
                         "settlement":settlement,**feats,**{f"strike_{x}":v for x,v in strikes.items()}})
    trades=pd.DataFrame(rows)
    if trades.empty:
        raise SystemExit("no strategy trades generated")
    decisions_df=pd.DataFrame(decisions).drop_duplicates("decision_id").sort_values("decision_date")
    trades["year"]=pd.to_datetime(trades["decision_date"]).dt.year

    dev_feats=decisions_df[pd.to_datetime(decisions_df["decision_date"]).dt.year<=2022]
    v1=float(dev_feats["rv20"].quantile(1/3)); v2=float(dev_feats["rv20"].quantile(2/3))
    decisions_df["vol_regime"]=np.select([decisions_df.rv20<=v1,decisions_df.rv20<=v2],["low","medium"],default="high")
    decisions_df["regime"]=decisions_df.direction_prediction.astype(str)+"_"+decisions_df.vol_regime.astype(str)
    trades=trades.drop(columns=["regime","vol_regime"],errors="ignore").merge(
        decisions_df[["decision_id","vol_regime","regime"]],on="decision_id",how="left")

    summaries=[]
    periods=np.select([trades.year<=2022,trades.year<=2024],["development","validation"],default="final")
    trades["period"]=periods
    for (period,strategy),g in trades.groupby(["period","strategy"]):
        s=summarize(g,0)
        summaries.append({"period":period,"strategy":strategy,**s,
                          "mean_mc_ev":float(g.mc_ev.dropna().mean()) if g.mc_ev.notna().any() else np.nan})
    pd.DataFrame(summaries).to_csv(out/"strategy_summary.csv",index=False)

    dev=trades[trades.year<=2022]
    mapping=[]
    for regime in sorted(dev.regime.dropna().unique()):
        g=dev[dev.regime==regime]
        for strategy in sorted(g.strategy.unique()):
            x=g[g.strategy==strategy]
            if len(x)<20:
                continue
            mean=float(x.realized_pnl.mean())
            se=float(x.realized_pnl.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else np.inf
            mapping.append({"regime":regime,"strategy":strategy,"n":len(x),"mean_pnl":mean,
                            "win_rate":float(x.win.mean()),"std_pnl":float(x.realized_pnl.std(ddof=1)),
                            "conservative_score":mean-se})
    mapping_df=pd.DataFrame(mapping)
    if mapping_df.empty:
        raise SystemExit("no regime/strategy cells met minimum development sample")
    mapping_df=mapping_df.sort_values(["regime","conservative_score"],ascending=[True,False])
    mapping_df.to_csv(out/"regime_strategy_ranking.csv",index=False)
    frozen=mapping_df.groupby("regime",as_index=False).head(3)
    frozen.to_csv(out/"frozen_regime_router.csv",index=False)

    rank_map={regime:g.sort_values("conservative_score",ascending=False)["strategy"].tolist()
              for regime,g in mapping_df.groupby("regime",sort=False)}
    routed=[]
    for period,frame in [("development",trades[trades.year<=2022]),
                         ("validation",trades[trades.year.between(2023,2024)]),
                         ("final",trades[trades.year>=2025])]:
        for did,dayg in frame.groupby("decision_id",sort=False):
            regime=str(dayg.iloc[0]["regime"]); chosen=None
            for s in rank_map.get(regime,[]):
                z=dayg[dayg.strategy==s]
                if not z.empty:
                    chosen=z.iloc[0]; break
            if chosen is None: continue
            routed.append({"period":period,"decision_id":did,"decision_date":chosen.decision_date,
                           "regime":regime,"strategy":chosen.strategy,"realized_pnl":float(chosen.realized_pnl),
                           "n_legs":int(chosen.n_legs),"mc_ev":float(chosen.mc_ev) if pd.notna(chosen.mc_ev) else np.nan,
                           "mc_pop":float(chosen.mc_pop) if pd.notna(chosen.mc_pop) else np.nan})
    routed=pd.DataFrame(routed)
    routed.to_csv(out/"regime_router_trades.csv",index=False)

    decision_years=pd.to_datetime(decisions_df.decision_date).dt.year
    denom={"development":int((decision_years<=2022).sum()),
           "validation":int(decision_years.between(2023,2024).sum()),
           "final":int((decision_years>=2025).sum())}
    router_rows=[]
    for period,g in routed.groupby("period"):
        for c in [0,0.1,0.25,0.5,1.0]:
            pnl=g.realized_pnl.to_numpy(float)-g.n_legs.to_numpy(float)*c
            eq=np.cumsum(pnl); dd=eq-np.maximum.accumulate(eq)
            router_rows.append({"period":period,"cost_per_leg_points":c,"trades":len(g),
                                "coverage":len(g)/max(1,denom[period]),"win_rate":float(np.mean(pnl>0)),
                                "mean_pnl":float(np.mean(pnl)),"total_pnl":float(np.sum(pnl)),
                                "max_drawdown":float(np.min(dd))})
    router_summary=pd.DataFrame(router_rows)
    router_summary.to_csv(out/"regime_router_summary.csv",index=False)

    oracle=[]
    for period,frame in [("validation",trades[trades.year.between(2023,2024)]),
                         ("final",trades[trades.year>=2025])]:
        for did,g in frame.groupby("decision_id",sort=False):
            best=g.loc[g.realized_pnl.idxmax()]
            oracle.append({"period":period,"decision_id":did,"oracle_strategy":best.strategy,
                           "oracle_pnl":float(best.realized_pnl),"regime":best.regime})
    pd.DataFrame(oracle).to_csv(out/"oracle_diagnostic.csv",index=False)

    predictions=decisions_df[["decision_id","decision_date","actual_expiry","spot","rv20","trend20","trend60",
                              "p_up","p_down","p_range","p_expand","mc_median_return",
                              "direction_prediction","vol_regime","regime"]].copy()
    predictions.to_csv(out/"nifty_regime_predictions.csv",index=False)
    trades.to_csv(out/"strategy_trades.csv",index=False)

    lines=["# NIFTY Multi-Strategy Regime Lab","",
           f"- Strategies tested: {len(STRATEGY_NAMES)}",
           f"- Decision observations: {len(decisions_df)}",
           f"- Strategy trades generated: {len(trades)}",
           "- Development: 2020-2022; validation: 2023-2024; final: 2025-2026.",
           "- Regime mapping is frozen from development only and uses a conservative mean-minus-standard-error score.",
           "","## Frozen regime router",""]
    for _,r in frozen.iterrows():
        lines.append(f"- {r.regime} -> {r.strategy} (development n={int(r.n)}, mean={r.mean_pnl:.2f}, score={r.conservative_score:.2f})")
    lines += ["","## Router summary","",router_summary.to_csv(index=False),
              "","The oracle diagnostic is look-ahead only and is not deployable."]
    (out/"strategy_regime_report.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines[:50]))

if __name__=="__main__":
    main()
