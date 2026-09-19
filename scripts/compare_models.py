from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from nifty_mc.walk_forward import ForecastOrigin, evaluate_prediction, log_returns
from nifty_mc.gbm import simulate_terminal_gbm
from nifty_mc.volatility import realized_vol
from nifty_mc.evaluation import summarize_oos

def weekly_expiries(start, end, sessions):
    sessions = pd.DatetimeIndex(sessions).normalize().sort_values().unique()
    out=[]
    for freq, lo, hi in [("W-THU","2019-02-14","2025-04-03"),("W-MON","2025-04-04","2025-08-28"),("W-TUE","2025-08-29",str(end.date()))]:
        for d in pd.date_range(max(start,pd.Timestamp(lo)), min(end,pd.Timestamp(hi)), freq=freq):
            e=sessions[sessions<=d]
            if len(e): out.append(e[-1])
    return sorted(set(out))

def bootstrap_terminal(s0, lr, h, n, rng):
    paths=rng.choice(np.asarray(lr), size=(n,h), replace=True)
    return s0*np.exp(paths.sum(axis=1))

def vol_scaled_bootstrap(s0, lr, h, n, rng, window=20):
    x=np.asarray(lr,dtype=float)
    vols=pd.Series(x).rolling(window).std().to_numpy()
    cur=vols[-1]
    if not np.isfinite(cur) or cur<=0: return bootstrap_terminal(s0,x,h,n,rng)
    scaled=x/np.where(vols>0,vols,np.nan)
    pool=scaled[np.isfinite(scaled)]
    draws=rng.choice(pool,size=(n,h),replace=True)
    return s0*np.exp((draws*cur).sum(axis=1))

def t_terminal(s0, lr, h, n, rng):
    x=np.asarray(lr,dtype=float)
    recent=x[-60:] if len(x)>=60 else x
    df, loc, scale=student_t.fit(recent)
    df=max(float(df),3.0)
    draws=student_t.rvs(df,loc=loc,scale=scale,size=(n,h),random_state=rng)
    return s0*np.exp(draws.sum(axis=1))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--prices",required=True)
    ap.add_argument("--paths",type=int,default=20000)
    ap.add_argument("--out",default="reports/model_comparison.csv")
    ap.add_argument("--summary",default="reports/model_summary.csv")
    args=ap.parse_args()
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(args.prices,parse_dates=["date"]).dropna(subset=["date","close"]).drop_duplicates("date").sort_values("date").set_index("date")
    expiries=weekly_expiries(df.index.min(),df.index.max(),df.index)
    origins=[]
    for e in expiries:
        pre=df.index[df.index<e]
        for nday in (5,3):
            if len(pre)>=nday: origins.append(ForecastOrigin(pre[-nday],e))
    origins=sorted(set(origins),key=lambda o:(o.expiry_date,o.decision_date))
    rows=[]
    for i,o in enumerate(origins):
        hist=df.loc[df.index<=o.decision_date,"close"].dropna()
        fut=df.loc[(df.index>o.decision_date)&(df.index<=o.expiry_date),"close"].dropna()
        if len(hist)<120 or fut.empty: continue
        s0=float(hist.iloc[-1]); actual=float(fut.iloc[-1])
        h=len(df.index[(df.index>o.decision_date)&(df.index<=o.expiry_date)])
        lr=log_returns(hist)
        sigma=realized_vol(lr,window=20)
        if not np.isfinite(sigma) or sigma<=0: continue
        mu=float(lr.tail(60).mean()*252)
        t=max(1,h)/252
        rng=np.random.default_rng(20260918+i)
        gbm=simulate_terminal_gbm(s0,t,mu,sigma,n_paths=args.paths,seed=20260918+i)
        boot=bootstrap_terminal(s0,lr,h,args.paths,rng)
        vsb=vol_scaled_bootstrap(s0,lr,h,args.paths,rng)
        tdist=t_terminal(s0,lr,h,args.paths,rng)
        ens=np.concatenate([gbm,boot,vsb,tdist])
        for name,samp in [("GBM",gbm),("Bootstrap",boot),("VolScaledBootstrap",vsb),("StudentT",tdist),("Ensemble",ens)]:
            m=evaluate_prediction(actual,samp,s0)
            rows.append({"decision_date":o.decision_date,"expiry_date":o.expiry_date,"dte":nday if False else h,"model":name,"s0":s0,**m})
    out=pd.DataFrame(rows)
    out.to_csv(args.out,index=False)
    summary=out.groupby("model").agg(
        forecasts=("actual_st","size"),coverage_50=("coverage_50","mean"),coverage_80=("coverage_80","mean"),
        coverage_90=("coverage_90","mean"),width_50=("width_50","mean"),width_80=("width_80","mean"),
        width_90=("width_90","mean"),crps=("crps","mean"),brier_up=("brier_up","mean")).reset_index()
    summary.to_csv(args.summary,index=False)
    print(summary.to_string(index=False))

if __name__=="__main__": main()
