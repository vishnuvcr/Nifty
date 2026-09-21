#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, zipfile
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

SLIPPAGE=2.0
BROKERAGES=(10.0,20.0,30.0)

def lot_size(expiry):
    return 75 if pd.Timestamp(expiry).date() <= date(2025,12,30) else 65

def stt_rate(ts):
    return 0.0015 if pd.Timestamp(ts).date() >= date(2026,4,1) else 0.001

def adj(raw,qty,entry=True):
    if entry:
        return raw+SLIPPAGE if qty>0 else max(0.0,raw-SLIPPAGE)
    return max(0.0,raw-SLIPPAGE) if qty>0 else raw+SLIPPAGE

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--options-zip",required=True)
    ap.add_argument("--trade-level",required=True)
    ap.add_argument("--out-dir",required=True)
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)

    d=pd.read_csv(args.trade_level)
    d20=d[d.brokerage_per_order_inr.eq(20.0)].copy()
    if d20.empty: raise SystemExit("No frozen holdout entries.")

    requests=[]
    for _,r in d20.iterrows():
        requests.append({
            "decision":pd.Timestamp(r.decision_date).normalize(),
            "expiry":pd.Timestamp(r.expiry).normalize(),
            "strikes":{
                "p20":float(r.p20),"p35":float(r.p35),"c65":float(r.c65),"c80":float(r.c80)
            }
        })

    leg_defs=[]
    for q in requests:
        s=q["strikes"]
        leg_defs.append([
            ("PE",s["p35"],1,"p35"),
            ("PE",s["p20"],-2,"p20"),
            ("CE",s["c65"],1,"c65"),
            ("CE",s["c80"],-2,"c80"),
        ])

    members={}
    with zipfile.ZipFile(args.options_zip) as zf:
        member=[n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        with zf.open(member) as fh:
            for chunk in pd.read_csv(
                fh,usecols=["timestamp","expiry_code","option_type","open","close","volume","strike_price"],
                chunksize=500000
            ):
                chunk["timestamp"]=pd.to_datetime(chunk.timestamp,errors="coerce",utc=True)
                chunk["local_date"]=chunk.timestamp.dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
                chunk["expiry_code"]=pd.to_numeric(chunk.expiry_code,errors="coerce")
                chunk["strike_price"]=pd.to_numeric(chunk.strike_price,errors="coerce")
                chunk["open"]=pd.to_numeric(chunk.open,errors="coerce")
                chunk["close"]=pd.to_numeric(chunk.close,errors="coerce")
                chunk["volume"]=pd.to_numeric(chunk.volume,errors="coerce").fillna(0)
                chunk=chunk[chunk.expiry_code.eq(1)]
                for q,legs in zip(requests,leg_defs):
                    dec=q["decision"]; exp=q["expiry"]
                    z=chunk[(chunk.local_date.eq(dec)) | (chunk.local_date.eq(exp))]
                    if z.empty: continue
                    rows=members.setdefault((dec,exp),[])
                    rows.append(z)

    output=[]
    for q,legs in zip(requests,leg_defs):
        key=(q["decision"],q["expiry"])
        parts=members.get(key,[])
        if not parts: continue
        z=pd.concat(parts,ignore_index=True).drop_duplicates(["timestamp","option_type","strike_price"])
        cutoff=(q["decision"]+pd.Timedelta(hours=9,minutes=30)).tz_localize("Asia/Kolkata").tz_convert("UTC")
        entry_cashflow=0.0
        entry_stt={}
        valid=True
        for typ,strike,qty,label in legs:
            g=z[(z.local_date.eq(q["decision"]))&(z.option_type.astype(str).str.upper().eq(typ))&
                z.strike_price.eq(float(strike))&(z.timestamp>cutoff)&(z.volume>0)&z.open.notna()].sort_values("timestamp")
            if g.empty: valid=False; break
            r=g.iloc[0]; px=float(r.open); ts=pd.Timestamp(r.timestamp)
            entry_cashflow -= qty*adj(px,qty,True)
            if qty<0: entry_stt[label]=abs(qty)*adj(px,qty,True)*lot_size(q["expiry"])*stt_rate(ts)
        if not valid: continue

        exit_cashflow=0.0; exit_stt=0.0; valid=True; exit_ts=[]
        for typ,strike,qty,label in legs:
            g=z[(z.local_date.eq(q["expiry"]))&(z.option_type.astype(str).str.upper().eq(typ))&
                z.strike_price.eq(float(strike))&(z.volume>0)&z.close.notna()].sort_values("timestamp")
            if g.empty: valid=False; break
            r=g.iloc[-1]; px=float(r.close); ts=pd.Timestamp(r.timestamp)
            exit_cashflow += qty*adj(px,qty,False)
            if qty>0: exit_stt += abs(qty)*adj(px,qty,False)*lot_size(q["expiry"])*stt_rate(ts)
            exit_ts.append(ts)
        if not valid: continue

        lot=lot_size(q["expiry"])
        gross_points=entry_cashflow+exit_cashflow
        entry_stt_total=sum(entry_stt.values())
        for brokerage in BROKERAGES:
            net=gross_points*lot-8*brokerage-entry_stt_total-exit_stt
            output.append({
                "decision_date":q["decision"].date().isoformat(),
                "expiry":q["expiry"].date().isoformat(),
                "brokerage_per_order_inr":brokerage,
                "lot_size":lot,
                "expiry_control_gross_points":gross_points,
                "expiry_control_net_inr":net,
                "exit_time":str(max(exit_ts))
            })

    res=pd.DataFrame(output)
    if res.empty: raise SystemExit("No control rows")
    comp=res.merge(d[["decision_date","expiry","brokerage_per_order_inr","realized_net_inr"]],on=["decision_date","expiry","brokerage_per_order_inr"],how="inner")
    comp["selected_minus_expiry_control"]=comp.realized_net_inr-comp.expiry_control_net_inr
    comp.to_csv(out/"T5_HOLDOUT_PAIRED_CONTROL.csv",index=False)
    summary=comp.groupby("brokerage_per_order_inr").agg(
        trades=("realized_net_inr","size"),
        selected_total=("realized_net_inr","sum"),
        expiry_control_total=("expiry_control_net_inr","sum"),
        selected_mean=("realized_net_inr","mean"),
        expiry_control_mean=("expiry_control_net_inr","mean"),
        paired_difference_total=("selected_minus_expiry_control","sum"),
        paired_difference_mean=("selected_minus_expiry_control","mean"),
        selected_win_rate=("realized_net_inr",lambda x: float((x>0).mean())),
        control_win_rate=("expiry_control_net_inr",lambda x: float((x>0).mean())),
    ).reset_index()
    summary.to_csv(out/"T5_HOLDOUT_PAIRED_CONTROL_SUMMARY.csv",index=False)
    print(summary.to_string(index=False))
    print(comp.to_string(index=False))

if __name__=="__main__":
    main()
