#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.batman_t2_entry import deterministic_seed, mc_terminal, unique_strikes, batman_legs

BROKERAGES = (10.0, 20.0, 30.0)
SLIPPAGE_CASES = (2.0, 4.0)
HOLDOUT_START = pd.Timestamp("2025-01-01")
HOLDOUT_END = pd.Timestamp("2026-07-21")

RULES = {
    "original_batman_d3_0930_expiry": {"offset": 3, "family": "expiry_control", "activation": None, "retracement": None,
                                        "label": "Original BATMAN control (D3 / 09:30 / expiry)"},
    "d3_0930_trailing_target_20_10": {"offset": 3, "family": "trailing_target", "activation": 0.20, "retracement": 0.10,
                                      "label": "Prior T6 candidate (D3 / 09:30 / trailing 20%→10%)"},
    "t7_d4_0930_trailing_target_30_30": {"offset": 4, "family": "trailing_target", "activation": 0.30, "retracement": 0.30,
                                         "label": "T7 frozen candidate (D4 / 09:30 / trailing 30%→30%)"},
}

def lot_size(expiry):
    return 75 if pd.Timestamp(expiry).date() <= date(2025, 12, 30) else 65

def stt_rate(ts):
    return 0.001 if pd.Timestamp(ts).date() < date(2026, 4, 1) else 0.0015

def adj(raw, qty, side, slippage):
    raw = float(raw)
    if side == "entry":
        return raw + slippage if qty > 0 else max(0.0, raw - slippage)
    return max(0.0, raw - slippage) if qty > 0 else raw + slippage

def load_daily(path):
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    dc = "date" if "date" in df.columns else "datetime"
    cc = "close" if "close" in df.columns else ("price" if "price" in df.columns else "last")
    df["date"] = pd.to_datetime(df[dc], errors="coerce").dt.tz_localize(None).dt.normalize()
    df["close"] = pd.to_numeric(df[cc].astype(str).str.replace(",", "", regex=False), errors="coerce")
    return df.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")[["date","close"]]

def normalize(c):
    c["timestamp"] = pd.to_datetime(c.timestamp, errors="coerce", utc=True)
    c["local_date"] = c["timestamp"].dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    c["expiry_code"] = pd.to_numeric(c.expiry_code, errors="coerce")
    c["option_type"] = c["option_type"].astype(str).str.upper()
    for k in ("open","close","volume","strike_price","spot_price"):
        c[k] = pd.to_numeric(c[k], errors="coerce")
    c["volume"] = c["volume"].fillna(0.0)
    return c.dropna(subset=["timestamp","local_date"])

def expiry_candidates(sessions):
    raw=[]
    d=pd.Timestamp("2025-01-02")
    while d<=pd.Timestamp("2025-08-28"):
        if d.weekday()==3: raw.append(d)
        d+=pd.Timedelta(days=1)
    d=pd.Timestamp("2025-09-02")
    while d<=HOLDOUT_END:
        if d.weekday()==1: raw.append(d)
        d+=pd.Timedelta(days=1)
    out=[]
    for target in raw:
        prior=sessions[sessions<=target]
        if len(prior)==0: continue
        exp=pd.Timestamp(prior[-1]).normalize()
        if exp not in out: out.append(exp)
    return pd.DatetimeIndex(out)

def extend_daily(daily,zf,member):
    option_dates={}
    for ch in pd.read_csv(zf.open(member),usecols=["timestamp","spot_price"],chunksize=500000):
        ch["timestamp"]=pd.to_datetime(ch.timestamp,errors="coerce",utc=True)
        ch["date"]=ch.timestamp.dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
        ch["spot_price"]=pd.to_numeric(ch.spot_price,errors="coerce")
        ch=ch.dropna(subset=["date","spot_price"])
        for d,g in ch.groupby("date"):
            option_dates[pd.Timestamp(d)]=float(g.sort_values("timestamp").iloc[-1].spot_price)
    ext=pd.DataFrame([{"date":d,"close":v} for d,v in option_dates.items()])
    ext=ext[ext.date>=HOLDOUT_START]
    return pd.concat([daily,ext],ignore_index=True).sort_values("date").drop_duplicates("date",keep="last")

def read_chunks(zf,member):
    return pd.read_csv(zf.open(member),usecols=["timestamp","expiry_code","option_type","open","close","volume","strike_price","spot_price"],chunksize=500000)

def build_candidate(day, decision, expiry, daily_series, offset):
    cutoff=decision.tz_localize("Asia/Kolkata")+pd.Timedelta(hours=9,minutes=30)
    cutoff=cutoff.tz_convert("UTC")
    near=day[(day.expiry_code==1)&(day.timestamp<=cutoff)&(day.volume>0)&day.close.notna()&day.strike_price.notna()]
    if near.empty: return None,"missing_pre0930_quotes"
    spot_rows=day[day.timestamp==cutoff].spot_price.dropna()
    if spot_rows.empty: return None,"missing_exact_0930_spot"
    hist=daily_series.loc[daily_series.index <= decision-pd.Timedelta(days=1)].tail(757)
    lr=np.log(hist).diff().dropna().tail(756).to_numpy()
    if len(lr)<756: return None,"insufficient_756_returns"
    terms=mc_terminal(float(spot_rows.iloc[0]),lr,3,5000,deterministic_seed(20260921,f"{decision.date()}|{expiry.date()}|T7_HOLDOUT"))
    qs={"p20":float(np.quantile(terms,.20)),"p35":float(np.quantile(terms,.35)),
        "c65":float(np.quantile(terms,.65)),"c80":float(np.quantile(terms,.80))}
    strikes=unique_strikes(near.strike_price.dropna().unique(),qs)
    if strikes is None: return None,"insufficient_strikes"
    legs=batman_legs(strikes)
    entries=[]; cash=0.0; entry_complete=None
    for typ,strike,qty,label in legs:
        z=day[(day.expiry_code==1)&(day.option_type==typ)&day.strike_price.eq(float(strike))&
              (day.timestamp>cutoff)&(day.volume>0)&day.open.notna()].sort_values("timestamp")
        if z.empty: return None,f"missing_entry_{label}"
        r=z.iloc[0]; raw=float(r.open); ts=pd.Timestamp(r.timestamp)
        cash-=qty*adj(raw,qty,"entry",SLIPPAGE_CASES[0])
        entry_complete=ts if entry_complete is None else max(entry_complete,ts)
        entries.append((typ,float(strike),qty,label,raw,ts))
    pnl=np.zeros(len(terms))
    for typ,strike,qty,_ in legs:
        intrinsic=np.maximum(terms-strike,0.0) if typ=="CE" else np.maximum(strike-terms,0.0)
        pnl+=qty*intrinsic
    pnl+=cash
    mc_ev=float(pnl.mean())
    if mc_ev<=0: return None,"gross_mc_gate_failed"
    q05=float(np.quantile(pnl,.05))
    es95=float(max(0.0,-np.mean(pnl[pnl<=q05]))) if np.any(pnl<=q05) else 0.0
    max_profit=0.0
    for s in sorted(set([0.0]+[float(x[1]) for x in legs])):
        v=cash
        for typ,strike,qty,_ in legs:
            v+=qty*(max(s-strike,0.0) if typ=="CE" else max(strike-s,0.0))
        max_profit=max(max_profit,v)
    if max_profit<=0: return None,"nonpositive_max_profit_reference"
    return {"decision":decision,"expiry":expiry,"offset":offset,"spot":float(spot_rows.iloc[0]),
            "legs":legs,"entries":entries,"entry_cashflow":cash,"entry_complete":entry_complete,
            "mc_ev":mc_ev,"mc_es95":es95,"max_profit":float(max_profit),"targets":qs},None

def build_marks(path,c):
    parts=[]
    for typ,strike,qty,label in c["legs"]:
        g=path[(path.option_type==typ)&path.strike_price.eq(float(strike))&
               (path.timestamp>=c["entry_complete"])&(path.volume>0)&path.close.notna()][["timestamp","close"]].copy()
        if g.empty: return pd.DataFrame(),[label]
        g["label"]=label; parts.append(g)
    allm=pd.concat(parts,ignore_index=True)
    piv=allm.pivot_table(index="timestamp",columns="label",values="close",aggfunc="last").sort_index().ffill()
    labels=[x[3] for x in c["legs"]]
    if any(x not in piv.columns for x in labels): return pd.DataFrame(),[x for x in labels if x not in piv.columns]
    piv=piv.dropna(subset=labels)
    pnl=np.zeros(len(piv))
    for typ,strike,qty,label in c["legs"]: pnl+=qty*piv[label].to_numpy(float)
    piv["pnl_points"]=pnl+c["entry_cashflow"]
    return piv.reset_index(),[]

def expiry_exits(path,c):
    out=[]
    for typ,strike,qty,label in c["legs"]:
        g=path[(path.local_date==c["expiry"])&(path.option_type==typ)&path.strike_price.eq(float(strike))&
               (path.volume>0)&path.close.notna()].sort_values("timestamp")
        if g.empty:return None
        r=g.iloc[-1];out.append((typ,strike,qty,label,float(r.close),pd.Timestamp(r.timestamp)))
    return out

def first_after(path,ts):
    z=path[(path.timestamp>ts)&(path.volume>0)&path.open.notna()].sort_values("timestamp")
    if z.empty:return None
    r=z.iloc[0];return float(r.open),pd.Timestamp(r.timestamp)

def evaluate(path,c,rule):
    if rule["family"]=="expiry_control":
        e=expiry_exits(path,c)
        return (e,"expiry_control",None) if e else (None,"missing_expiry_exit",None)
    marks,missing=build_marks(path,c)
    trigger=None;active=False;peak=0.0
    if not marks.empty:
        for r in marks.itertuples(index=False):
            p=float(r.pnl_points);ts=pd.Timestamp(r.timestamp)
            if not active and p>=rule["activation"]*c["max_profit"]:
                active=True;peak=p
            elif active:
                peak=max(peak,p)
                if p<=peak-rule["retracement"]*c["max_profit"]:
                    trigger=ts;break
    if trigger is not None:
        e=[]
        for typ,strike,qty,label in c["legs"]:
            x=first_after(path[(path.option_type==typ)&path.strike_price.eq(float(strike))],trigger)
            if x is None:e=None;break
            raw,ts=x;e.append((typ,strike,qty,label,raw,ts))
        if e is not None:return e,"trailing_target",trigger
    e=expiry_exits(path,c)
    return (e,"expiry_fallback",trigger) if e else (None,"missing_expiry_fallback",trigger)

def realize(c,exits,slippage):
    rows=[];lot=lot_size(c["expiry"]);ent_stt=0.0;exit_stt=0.0;exit_cash=0.0
    for typ,strike,qty,label,raw,ts in c["entries"]:
        px=adj(raw,qty,"entry",slippage)
        if qty<0:ent_stt+=abs(qty)*px*lot*stt_rate(ts)
    for typ,strike,qty,label,raw,ts in exits:
        px=adj(raw,qty,"exit",slippage);exit_cash+=qty*px
        if qty>0:exit_stt+=abs(qty)*px*lot*stt_rate(ts)
    gross=(c["entry_cashflow"]+exit_cash)*lot
    for b in BROKERAGES:
        rows.append({"brokerage_per_order_inr":b,"lot_size":lot,"realized_gross_points":c["entry_cashflow"]+exit_cash,
                     "realized_net_inr":gross-8*b-ent_stt-exit_stt,"entry_stt_inr":ent_stt,"exit_stt_inr":exit_stt,
                     "exit_time":str(max(x[5] for x in exits))})
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--options-zip",required=True);ap.add_argument("--daily-index",required=True);ap.add_argument("--out-dir",required=True)
    args=ap.parse_args();out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)

    daily=load_daily(args.daily_index)
    with zipfile.ZipFile(args.options_zip) as zf:
        member=[n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        daily=extend_daily(daily,zf,member)
        sessions=pd.DatetimeIndex(daily.date.unique()).sort_values()
        exps=expiry_candidates(sessions);exps=exps[(exps>=HOLDOUT_START)&(exps<=HOLDOUT_END)]
        req=[]
        for exp in exps:
            if exp not in sessions:continue
            pos=sessions.get_loc(exp)
            for off in (3,4):
                if pos>=off:
                    dec=sessions[pos-off]
                    if HOLDOUT_START<=dec<=HOLDOUT_END:req.append((dec,exp,off))
        wanted=set(x[0] for x in req)
        day_parts=defaultdict(list)
        for ch in read_chunks(zf,member):
            ch=normalize(ch);ch=ch[(ch.expiry_code==1)&ch.local_date.isin(wanted)]
            if ch.empty:continue
            for d,g in ch.groupby("local_date"):day_parts[pd.Timestamp(d)].append(g.copy())
        series=daily.set_index("date")["close"].astype(float)
        cands=[];skips=defaultdict(int);stages={"expiry_candidates":int(len(exps)),"requests":int(len(req)),"candidates":0,"gate_pass":0}
        for dec,exp,off in req:
            parts=day_parts.get(dec,[])
            if not parts:skips["missing_decision_0930"]+=1;continue
            c,reason=build_candidate(pd.concat(parts,ignore_index=True),dec,exp,series,off)
            if c is None:skips[reason]+=1;continue
            cands.append(c);stages["candidates"]+=1;stages["gate_pass"]+=1
        marks_store={i:[] for i in range(len(cands))}
        if cands:
            start=min(c["entry_complete"].tz_convert("Asia/Kolkata").normalize().tz_localize(None) for c in cands)
            end=max(c["expiry"] for c in cands)
            for ch in read_chunks(zf,member):
                ch=normalize(ch);ch=ch[(ch.expiry_code==1)&(ch.local_date>=start)&(ch.local_date<=end)]
                if ch.empty:continue
                for i,c in enumerate(cands):
                    active=ch[(ch.timestamp>=c["entry_complete"])&(ch.local_date<=c["expiry"])]
                    if active.empty:continue
                    mask=pd.Series(False,index=active.index)
                    for typ,strike,qty,label in c["legs"]:
                        mask|=(active.option_type==typ)&active.strike_price.eq(float(strike))
                    if mask.any():marks_store[i].append(active.loc[mask,["timestamp","local_date","option_type","strike_price","open","close","volume"]].copy())
        rows=[]
        for i,c in enumerate(cands):
            path=pd.concat(marks_store[i],ignore_index=True) if marks_store[i] else pd.DataFrame()
            if path.empty:skips["missing_exit_path"]+=1;continue
            for rid,rule in RULES.items():
                for slip in SLIPPAGE_CASES:
                    ex,mode,trig=evaluate(path,c,rule)
                    if ex is None:skips[f"{rid}:{mode}"]+=1;continue
                    for r in realize(c,ex,slip):
                        r.update({"rule_id":rid,"rule_label":rule["label"],"decision_date":c["decision"].date().isoformat(),
                                  "expiry":c["expiry"].date().isoformat(),"entry_offset":c["offset"],
                                  "slippage_per_option_leg_points":slip,"mc_ev_points":c["mc_ev"],
                                  "mc_es95_points":c["mc_es95"],"max_profit_reference_points":c["max_profit"],
                                  "p20":c["targets"]["p20"],"p35":c["targets"]["p35"],"c65":c["targets"]["c65"],"c80":c["targets"]["c80"],
                                  "trigger_time":"" if trig is None else str(trig),"exit_mode":mode})
                        rows.append(r)
        if not rows:
            (out/"T7_HOLDOUT_SKIP_COUNTS.json").write_text(json.dumps(skips,indent=2)+"\n")
            (out/"T7_HOLDOUT_STAGE_COUNTS.json").write_text(json.dumps(stages,indent=2)+"\n")
            raise SystemExit("No holdout rows")
    d=pd.DataFrame(rows);d["decision_date"]=pd.to_datetime(d.decision_date);d["expiry"]=pd.to_datetime(d.expiry);d["year"]=d.decision_date.dt.year
    d.to_csv(out/"T7_HOLDOUT_TRADE_LEVEL.csv",index=False)
    s=d.groupby(["rule_id","rule_label","slippage_per_option_leg_points","brokerage_per_order_inr"]).agg(
        trades=("decision_date","nunique"),total_net_inr=("realized_net_inr","sum"),mean_net_inr=("realized_net_inr","mean"),
        median_net_inr=("realized_net_inr","median"),win_rate=("realized_net_inr",lambda x:float((x>0).mean()))).reset_index()
    s.to_csv(out/"T7_HOLDOUT_SUMMARY.csv",index=False)
    y=d.groupby(["rule_id","rule_label","slippage_per_option_leg_points","brokerage_per_order_inr","year"]).agg(
        trades=("decision_date","nunique"),total_net_inr=("realized_net_inr","sum"),mean_net_inr=("realized_net_inr","mean"),
        win_rate=("realized_net_inr",lambda x:float((x>0).mean()))).reset_index()
    y.to_csv(out/"T7_HOLDOUT_YEARLY.csv",index=False)
    base=d[(d.slippage_per_option_leg_points==2.0)&(d.brokerage_per_order_inr==20.0)]
    w=base.pivot_table(index=["decision_date","expiry"],columns="rule_id",values="realized_net_inr",aggfunc="first").reset_index()
    ctl="original_batman_d3_0930_expiry"; comps=[]
    for col in w.columns:
        if col in ("decision_date","expiry",ctl):continue
        if ctl in w.columns:
            m=w[["decision_date","expiry",ctl,col]].dropna().copy();m["candidate_rule_id"]=col;m["candidate_minus_original_batman"]=m[col]-m[ctl];comps.append(m)
    pd.concat(comps,ignore_index=True).to_csv(out/"T7_HOLDOUT_PAIRED_COMPARISON.csv",index=False) if comps else pd.DataFrame().to_csv(out/"T7_HOLDOUT_PAIRED_COMPARISON.csv",index=False)
    report={"holdout_start":str(d.decision_date.min().date()),"holdout_end":str(d.expiry.max().date()),"primary_case":"2-point slippage / ₹20 brokerage",
            "stress_case":"4-point slippage / ₹30 brokerage","frozen_candidate":"D4 / 09:30 / trailing 30% activation / 30% retracement",
            "selection_after_holdout":False}
    (out/"T7_HOLDOUT_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"T7_HOLDOUT_SKIP_COUNTS.json").write_text(json.dumps(skips,indent=2)+"\n")
    (out/"T7_HOLDOUT_STAGE_COUNTS.json").write_text(json.dumps(stages,indent=2)+"\n")
    print(s.to_string(index=False))
    print("STAGES",json.dumps(stages,indent=2))
    print("SKIPS",json.dumps(skips,indent=2))

if __name__=="__main__":main()
