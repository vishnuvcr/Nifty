from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def payoff(st, k1, k2, k3, k4, debit):
    return (np.maximum(k2-st,0)-np.maximum(k1-st,0)
            +np.maximum(st-k3,0)-np.maximum(st-k4,0)-debit)

def nearest_distinct(ks, target, used, side=None):
    arr=np.asarray(ks,dtype=float)
    if side=="lt": arr=arr[arr<target]
    if side=="gt": arr=arr[arr>target]
    arr=np.array([x for x in arr if x not in used])
    if len(arr)==0: return None
    return float(arr[np.argmin(np.abs(arr-target))])

def choose_strikes(chain, q10,q35,q65,q90):
    ks=np.sort(chain["strike"].dropna().unique().astype(float))
    if len(ks)<4: return None
    k2=nearest_distinct(ks,q35,set())
    k3=nearest_distinct(ks,q65,{k2},"gt")
    if k3 is None: return None
    k1=nearest_distinct(ks,q10,{k2,k3},"lt")
    k4=nearest_distinct(ks,q90,{k1,k2,k3},"gt")
    if None in (k1,k2,k3,k4) or not (k1<k2<k3<k4): return None
    return k1,k2,k3,k4

def row_close(chain,k,typ):
    x=chain[(chain["strike"].astype(float)==float(k)) & (chain["option_type"].str.upper()==typ)]
    if x.empty: return None
    v=pd.to_numeric(x.iloc[0]["close"],errors="coerce")
    return None if pd.isna(v) or v<=0 else float(v)

def mc_terminal(spot, returns, horizon_days, n=20000, seed=0):
    r=np.asarray(returns,dtype=float)
    r=r[np.isfinite(r)]
    if len(r)<60: return None
    rng=np.random.default_rng(seed)
    h=max(1,int(horizon_days))
    sampled=rng.choice(r,size=n*h,replace=True).reshape(n,h)
    return spot*np.exp(sampled.sum(axis=1))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--index",required=True)
    ap.add_argument("--options-dir",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--paths",type=int,default=20000)
    args=ap.parse_args()

    idx=pd.read_csv(args.index,parse_dates=["date"]).sort_values("date")
    idx["close"]=pd.to_numeric(idx["close"],errors="coerce")
    idx=idx.dropna(subset=["date","close"]).drop_duplicates("date").reset_index(drop=True)
    idx["logret"]=np.log(idx["close"]).diff()
    price_by_date=dict(zip(idx["date"].dt.normalize(),idx["close"]))

    targets=[]; chains=[]
    for p in sorted(Path(args.options_dir).rglob("nifty_options_*.csv.gz")):
        y=p.name.split("_")[-1].split(".")[0]
        d=pd.read_csv(p,parse_dates=["timestamp","expiry"])
        d["timestamp"]=pd.to_datetime(d["timestamp"]).dt.normalize()
        d["expiry"]=pd.to_datetime(d["expiry"]).dt.normalize()
        d["strike"]=pd.to_numeric(d["strike"],errors="coerce")
        d["close"]=pd.to_numeric(d["close"],errors="coerce")
        d["option_type"]=d["option_type"].astype(str).str.upper()
        d=d[(d["symbol"].astype(str).str.upper()=="NIFTY") &
            d["option_type"].isin(["CE","PE"]) & d["strike"].notna() & d["close"].notna()]
        chains.append(d)
        matches=list(Path(args.options_dir).rglob(f"targets_{y}.csv"))
        if matches:
            targets.append(pd.read_csv(matches[0],parse_dates=["decision_date","expiry"]))
    if not chains: raise SystemExit("no option artifacts")
    opt=pd.concat(chains,ignore_index=True)
    targ=pd.concat(targets,ignore_index=True).drop_duplicates(["decision_date","expiry"]).sort_values("decision_date")
    by_ts={k:g for k,g in opt.groupby("timestamp",sort=False)}

    rows=[]
    for i,t in enumerate(targ.itertuples(index=False)):
        decision=pd.Timestamp(t.decision_date).normalize()
        target_exp=pd.Timestamp(t.expiry).normalize()
        spot=price_by_date.get(decision)
        day=by_ts.get(decision)
        if spot is None or day is None: continue
        exps=sorted(pd.to_datetime(day["expiry"].dropna().unique()))
        actual=[e for e in exps if e>=target_exp]
        if not actual: continue
        expiry=pd.Timestamp(actual[0]).normalize()
        if expiry<=decision: continue
        future_sessions=idx[idx["date"].dt.normalize()<=expiry]
        if future_sessions.empty: continue
        exp_session=future_sessions.iloc[-1]["date"].normalize()
        if exp_session<=decision: continue
        hist=idx.loc[idx["date"].dt.normalize()<=decision,"logret"].dropna().tail(756).to_numpy()
        horizon=len(idx[(idx["date"].dt.normalize()>decision)&(idx["date"].dt.normalize()<=exp_session)])
        terminal=mc_terminal(float(spot),hist,horizon,args.paths,seed=100000+i)
        if terminal is None: continue
        q=np.percentile(terminal,[10,35,65,90])
        chain=day[day["expiry"].dt.normalize()==expiry]
        strikes=choose_strikes(chain,*q)
        if strikes is None: continue
        k1,k2,k3,k4=strikes
        p1=row_close(chain,k1,"PE"); p2=row_close(chain,k2,"PE")
        c3=row_close(chain,k3,"CE"); c4=row_close(chain,k4,"CE")
        if None in (p1,p2,c3,c4): continue
        debit=p2+c3-p1-c4
        wing=min(k2-k1,k4-k3)
        if debit<=0 or debit>=wing: continue
        mc_pnl=payoff(terminal,k1,k2,k3,k4,debit)
        realized_spot=float(price_by_date.get(exp_session,np.nan))
        if not np.isfinite(realized_spot): continue
        realized_pnl=float(payoff(np.array([realized_spot]),k1,k2,k3,k4,debit)[0])
        lower_be=k2-debit; upper_be=k3+debit
        rows.append({
            "decision_date":decision.date(),"target_expiry":target_exp.date(),"actual_expiry":expiry.date(),
            "expiry_session":exp_session.date(),"spot":spot,"horizon_days":horizon,
            "k1":k1,"k2":k2,"k3":k3,"k4":k4,"debit":debit,"wing_width":wing,
            "lower_be":lower_be,"upper_be":upper_be,
            "mc_p10":q[0],"mc_p35":q[1],"mc_p65":q[2],"mc_p90":q[3],
            "mc_pop":float(np.mean(mc_pnl>0)),"mc_ev":float(mc_pnl.mean()),
            "realized_spot":realized_spot,"realized_pnl":realized_pnl,
            "win":int(realized_pnl>0),"max_profit":wing-debit,"max_loss":debit,
            "mc_below_lower_be":float(np.mean(terminal<lower_be)),
            "mc_above_upper_be":float(np.mean(terminal>upper_be)),
        })
    out=pd.DataFrame(rows)
    if out.empty: raise SystemExit("no valid condor trades")
    out.to_csv(args.out,index=False)
    print("TRADES",len(out))
    print("WIN_RATE",out.win.mean())
    print("MEAN_PNL_POINTS",out.realized_pnl.mean())
    print("MEDIAN_PNL_POINTS",out.realized_pnl.median())
    print("MC_MEAN_EV_POINTS",out.mc_ev.mean())
    print("MC_POP_MEAN",out.mc_pop.mean())
    print("TOTAL_POINTS",out.realized_pnl.sum())

if __name__=="__main__": main()
