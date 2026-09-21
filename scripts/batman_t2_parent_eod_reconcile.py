#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.batman_t2_entry import load_option_day, mc_terminal, prepare_maps, prepare_spot_and_daily, unique_strikes, batman_legs, deterministic_seed, SLIPPAGE_POINTS, lot_size

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--options-zip",required=True)
    ap.add_argument("--long-index-zip",required=True)
    ap.add_argument("--raw-cache",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--paths",type=int,default=5000)
    ap.add_argument("--seed-base",type=int,default=20260921)
    args=ap.parse_args()
    raw=Path(args.raw_cache); out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    ayush=Path(args.options_zip); longz=Path(args.long_index_zip)
    cal,fmap=prepare_maps(raw,ayush)
    daily,_=prepare_spot_and_daily(raw,ayush,longz)
    daily["date"]=pd.to_datetime(daily.date).dt.normalize()
    daily["close"]=pd.to_numeric(daily.close,errors="coerce")
    daily=daily.dropna(subset=["date","close"]).sort_values("date").drop_duplicates("date")
    sessions=pd.DatetimeIndex(daily.date.unique()).sort_values()
    file_map=dict(zip(fmap.trade_date.dt.normalize(),fmap.member))
    requests=[]
    for exp in sorted(pd.to_datetime(cal.expiry).dropna().unique()):
        exp=pd.Timestamp(exp).normalize()
        if exp not in sessions: continue
        pos=sessions.get_loc(exp)
        if pos<3: continue
        decision=sessions[pos-3]
        if not (pd.Timestamp("2020-01-01") <= decision <= pd.Timestamp("2024-10-31")): continue
        requests.append((decision,exp))
    rows=[]; skips=defaultdict(int); cache={}
    with zipfile.ZipFile(ayush) as zf:
        for decision,expiry in requests:
            member=file_map.get(decision)
            if member is None: skips["missing_option_file"]+=1; continue
            if decision not in cache: cache[decision]=load_option_day(zf,member)
            day=cache[decision]
            spot=float(daily.loc[daily.date==decision,"close"].iloc[0])
            hist=np.log(daily.loc[daily.date<=decision,"close"].astype(float)).diff().dropna().tail(756).to_numpy()
            if len(hist)<756: skips["insufficient_756_returns"]+=1; continue
            if len(sessions[(sessions>decision)&(sessions<=expiry)])!=3: skips["unexpected_horizon"]+=1; continue
            terminals=mc_terminal(spot,hist,3,args.paths,deterministic_seed(args.seed_base,f"{decision.date()}|{expiry.date()}|EOD"))
            targets={"p20":float(np.quantile(terminals,.20)),"p35":float(np.quantile(terminals,.35)),"c65":float(np.quantile(terminals,.65)),"c80":float(np.quantile(terminals,.80))}
            chain=day[day.expiry==expiry]
            if chain.empty: skips["missing_expiry_chain"]+=1; continue
            strikes=unique_strikes(chain.strike.dropna().unique(),targets)
            if strikes is None: skips["insufficient_strike_grid"]+=1; continue
            legs=batman_legs(strikes)
            entry=0.0; valid=True
            for typ,strike,qty,label in legs:
                x=chain[(chain.option_type==typ)&(chain.strike==float(strike))&(chain.volume>0)&chain.close.notna()].sort_values("timestamp")
                if x.empty: valid=False; skips[f"missing_{label}"]+=1; break
                px=float(x.iloc[-1].close)
                adj=px+SLIPPAGE_POINTS if qty>0 else px-SLIPPAGE_POINTS
                entry-=qty*adj
            if not valid: continue
            pnl=np.zeros(len(terminals))
            for typ,strike,qty,_ in legs:
                intrinsic=np.maximum(terminals-strike,0.0) if typ=="CE" else np.maximum(strike-terminals,0.0)
                pnl+=qty*intrinsic
            pnl+=entry
            expiry_spot=float(daily.loc[daily.date==expiry,"close"].iloc[0])
            realized_intrinsic=sum(qty*(max(expiry_spot-strike,0.0) if typ=="CE" else max(strike-expiry_spot,0.0)) for typ,strike,qty,_ in legs)
            realized=float(realized_intrinsic+entry)
            rows.append({
                "decision_date":decision.date().isoformat(),"expiry":expiry.date().isoformat(),"spot_eod":spot,
                "p20":strikes["p20"],"p35":strikes["p35"],"c65":strikes["c65"],"c80":strikes["c80"],
                "mc_ev_points":float(pnl.mean()),"mc_pop":float(np.mean(pnl>0)),"gate_gross":int(pnl.mean()>0),
                "realized_points":realized,"realized_inr":realized*lot_size(expiry),"lot_size":lot_size(expiry),
                "execution_stress_points":SLIPPAGE_POINTS
            })
    d=pd.DataFrame(rows).sort_values("decision_date")
    d.to_csv(out/"BATMAN_PARENT_EOD_CONTROL.csv",index=False)
    pd.DataFrame([dict(skips)]).to_json(out/"BATMAN_PARENT_EOD_SKIP_COUNTS.json",orient="records",indent=2)
    active=d[d.gate_gross.astype(bool)]
    gains=active.loc[active.realized_points>0,"realized_points"].sum()
    losses=-active.loc[active.realized_points<0,"realized_points"].sum()
    summary={
        "opportunities":int(len(d)),"entered":int(len(active)),
        "entry_rate":float(len(active)/len(d)) if len(d) else np.nan,
        "mean_realized_points":float(active.realized_points.mean()) if len(active) else np.nan,
        "total_realized_points":float(active.realized_points.sum()) if len(active) else 0.0,
        "win_rate":float((active.realized_points>0).mean()) if len(active) else np.nan,
        "profit_factor":float(gains/losses) if losses>0 else np.inf,
        "mean_mc_ev_points":float(d.mc_ev_points.mean()) if len(d) else np.nan
    }
    (out/"BATMAN_PARENT_EOD_CONTROL_SUMMARY.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2)); print("SKIPS",dict(skips))

if __name__=="__main__":
    main()
