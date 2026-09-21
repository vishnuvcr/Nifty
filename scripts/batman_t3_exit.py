#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.batman_t2_entry import (
    batman_legs,
    deterministic_seed,
    get_execution_price,
    load_option_day,
    lot_size,
    mc_terminal,
    prepare_maps,
    prepare_spot_and_daily,
    stt_rate,
    unique_strikes,
)

SLIPPAGE_POINTS = 2.0
BROKERAGES = (10.0, 20.0, 30.0)

EXIT_FAMILIES = ["expiry_control", "fixed_target", "fixed_stop", "fixed_target_stop",
                 "trailing_stop", "trailing_target", "trailing_target_stop"]

FIXED_TARGETS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.75)
FIXED_STOPS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00)
TRAIL_STOPS = (0.10, 0.20, 0.30, 0.40, 0.50)
TT_ACTIVATIONS = (0.20, 0.30, 0.40, 0.50)
TT_RETRACEMENTS = (0.10, 0.20, 0.30)


@dataclass
class LegInfo:
    typ: str
    strike: float
    qty: int
    label: str
    entry_price: float
    entry_ts: pd.Timestamp


def entry_reference_max_profit(legs: list[LegInfo], entry_cashflow: float) -> float:
    strikes = sorted({0.0} | {float(x.strike) for x in legs})
    values = []
    for spot in strikes:
        intrinsic = 0.0
        for leg in legs:
            val = max(spot - leg.strike, 0.0) if leg.typ == "CE" else max(leg.strike - spot, 0.0)
            intrinsic += leg.qty * val
        values.append(intrinsic + entry_cashflow)
    return float(max(values)) if values else 0.0


def portfolio_mark(df: pd.DataFrame, legs: list[LegInfo], entry_cashflow: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.pivot_table(index="timestamp", columns="leg_id", values="close", aggfunc="last").sort_index()
    for leg in legs:
        col = leg.label
        if col not in out.columns:
            return pd.DataFrame()
    out = out.ffill().dropna(subset=[x.label for x in legs], how="any")
    pnl = np.zeros(len(out), dtype=float)
    for leg in legs:
        pnl += leg.qty * out[leg.label].to_numpy(float)
    out["pnl_points"] = pnl + entry_cashflow
    return out.reset_index()


def build_day_series(zf, file_map, dates, legs, entry_complete: pd.Timestamp, expiry: pd.Timestamp, cache):
    rows = []
    for d in dates:
        d = pd.Timestamp(d).normalize()
        member = file_map.get(d)
        if member is None:
            continue
        if d not in cache:
            cache[d] = load_option_day(zf, member)
        day = cache[d]
        for leg in legs:
            x = day[
                (day.expiry == expiry)
                & (day.option_type == leg.typ)
                & (day.strike == float(leg.strike))
                & (day.timestamp >= entry_complete)
                & (day.volume > 0)
                & day.close.notna()
            ][["timestamp","close"]].copy()
            x["leg_id"] = leg.label
            rows.append(x)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values(["timestamp","leg_id"])


def last_or_next_execution(zf, file_map, all_sessions, legs, trigger_ts, expiry, cache, use_open=True):
    exit_rows = []
    trigger_day = pd.Timestamp(trigger_ts).normalize()
    later_dates = all_sessions[all_sessions >= trigger_day]
    for leg in legs:
        chosen = None
        for d in later_dates:
            member = file_map.get(pd.Timestamp(d).normalize())
            if member is None:
                continue
            if d not in cache:
                cache[d] = load_option_day(zf, member)
            day = cache[d]
            cmp = day.timestamp > trigger_ts
            x = day[
                (day.expiry == expiry)
                & (day.option_type == leg.typ)
                & (day.strike == float(leg.strike))
                & cmp
                & (day.volume > 0)
                & (day.open.notna() if use_open else day.close.notna())
            ].sort_values("timestamp")
            if not x.empty:
                row = x.iloc[0]
                px = float(row.open if use_open else row.close)
                chosen = (px, pd.Timestamp(row.timestamp), "next_open" if use_open else "close")
                break
        if chosen is None:
            return None
        exit_rows.append((leg, chosen[0], chosen[1], chosen[2]))
    return exit_rows


def expiry_exit(zf, file_map, all_sessions, legs, expiry, cache):
    expiry_date = pd.Timestamp(expiry).normalize()
    member = file_map.get(expiry_date)
    if member is None:
        return None
    if expiry_date not in cache:
        cache[expiry_date] = load_option_day(zf, member)
    day = cache[expiry_date]
    end_cut = expiry_date + pd.Timedelta(hours=15, minutes=29)
    rows = []
    for leg in legs:
        x = day[
            (day.expiry == expiry)
            & (day.option_type == leg.typ)
            & (day.strike == float(leg.strike))
            & (day.timestamp <= end_cut)
            & (day.volume > 0)
            & day.close.notna()
        ].sort_values("timestamp")
        if x.empty:
            return None
        row = x.iloc[-1]
        rows.append((leg, float(row.close), pd.Timestamp(row.timestamp), "expiry_close"))
    return rows


def realized_exit(entry_cashflow, exits, expiry_date, brokerage, entry_brokerage, entry_stt, lot):
    exit_cashflow = 0.0
    exit_stt = 0.0
    for leg, px, ts, _mode in exits:
        adj = max(0.0, px - SLIPPAGE_POINTS) if leg.qty > 0 else px + SLIPPAGE_POINTS
        exit_cashflow += leg.qty * adj
        if leg.qty > 0:
            exit_stt += abs(leg.qty) * adj * lot * stt_rate(pd.Timestamp(ts))
    gross_points = float(entry_cashflow + exit_cashflow)
    exit_brokerage = 4.0 * brokerage
    costs = float(entry_brokerage + exit_brokerage + exit_stt)
    net_inr = gross_points * lot - costs
    return gross_points, net_inr, exit_stt


def rule_candidates():
    yield ("expiry_control", None, None, None)
    for x in FIXED_TARGETS:
        yield ("fixed_target", x, None, None)
    for x in FIXED_STOPS:
        yield ("fixed_stop", None, x, None)
    for t in FIXED_TARGETS:
        for s in FIXED_STOPS:
            yield ("fixed_target_stop", t, s, None)
    for x in TRAIL_STOPS:
        yield ("trailing_stop", None, x, None)
    for a in TT_ACTIVATIONS:
        for r in TT_RETRACEMENTS:
            yield ("trailing_target", a, r, None)
    for s in FIXED_STOPS:
        for a in TT_ACTIVATIONS:
            for r in TT_RETRACEMENTS:
                yield ("trailing_target_stop", a, s, r)


def trigger_exit(family, p, max_profit, risk_ref, target=None, stop=None, retrace=None):
    if family == "expiry_control":
        return None
    if family in {"fixed_target","fixed_target_stop"} and target is not None and max_profit > 0 and p >= target * max_profit:
        return "fixed_target"
    if family in {"fixed_stop","fixed_target_stop","trailing_target_stop"} and stop is not None and p <= -stop * risk_ref:
        return "fixed_stop"
    return None


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
    daily,spot0930=prepare_spot_and_daily(raw,ayush,longz)
    daily["date"]=pd.to_datetime(daily.date).dt.normalize()
    daily["close"]=pd.to_numeric(daily.close,errors="coerce")
    daily=daily.dropna(subset=["date","close"]).sort_values("date").drop_duplicates("date")
    spot0930["date"]=pd.to_datetime(spot0930.date).dt.normalize()
    spot_map=dict(zip(spot0930.date.dt.date,pd.to_numeric(spot0930.spot_0930,errors="coerce")))
    sessions=pd.DatetimeIndex(daily.date.unique()).sort_values()
    file_map=dict(zip(fmap.trade_date.dt.normalize(),fmap.member))

    expiry_list=sorted(pd.to_datetime(cal.expiry).dropna().unique())
    opportunities=[]
    for exp in expiry_list:
        exp=pd.Timestamp(exp).normalize()
        if exp not in sessions: continue
        pos=sessions.get_loc(exp)
        if pos<3: continue
        decision=sessions[pos-3]
        if decision < pd.Timestamp("2020-01-01") or decision > pd.Timestamp("2024-10-31"): continue
        spot=spot_map.get(decision.date())
        if spot is None or not np.isfinite(spot):
            continue
        opportunities.append((decision,exp,float(spot)))

    day_cache={}
    exit_cache={}
    results=[]; trade_meta=[]; skips=defaultdict(int)

    with zipfile.ZipFile(ayush) as zf:
        for i,(decision,expiry,spot) in enumerate(opportunities,1):
            member=file_map.get(decision)
            if member is None:
                skips["missing_decision_file"]+=1; continue
            if decision not in day_cache: day_cache[decision]=load_option_day(zf,member)
            day=day_cache[decision]
            signal_cut=decision+pd.Timedelta(hours=9,minutes=30)
            future=sessions[(sessions>decision)&(sessions<=expiry)]
            if len(future)!=3:
                skips["bad_horizon"]+=1; continue
            hist=np.log(daily.loc[daily.date<=decision,"close"].astype(float)).diff().dropna().tail(756).to_numpy()
            if len(hist)<756:
                skips["short_lookback"]+=1; continue
            terminals=mc_terminal(spot,hist,3,args.paths,deterministic_seed(args.seed_base,f"{decision.date()}|{expiry.date()}|T3"))
            targets={"p20":float(np.quantile(terminals,.20)),"p35":float(np.quantile(terminals,.35)),
                     "c65":float(np.quantile(terminals,.65)),"c80":float(np.quantile(terminals,.80))}
            chain=day[(day.expiry==expiry)&(day.timestamp<=signal_cut)&(day.volume>0)]
            if chain.empty:
                skips["missing_signal_chain"]+=1; continue
            strikes=unique_strikes(chain.strike.dropna().unique(),targets)
            if strikes is None:
                skips["insufficient_strikes"]+=1; continue
            legs_raw=batman_legs(strikes)
            legs=[]
            valid=True
            entry_cashflow=0.0
            execution_timestamps=[]
            for typ,strike,qty,label in legs_raw:
                ep=get_execution_price(day,expiry,typ,strike,signal_cut,True)
                if ep is None:
                    valid=False; skips[f"missing_entry_{label}"]+=1; break
                px,ts=ep
                legs.append(LegInfo(typ,strike,qty,label,px,ts))
                adj=px+SLIPPAGE_POINTS if qty>0 else px-SLIPPAGE_POINTS
                entry_cashflow-=qty*adj
                execution_timestamps.append(pd.Timestamp(ts))
            if not valid: continue
            entry_complete=max(execution_timestamps)
            # Recreate the frozen gross gate exactly.
            pnl_mc=np.zeros(args.paths)
            for leg in legs:
                intrinsic=np.maximum(terminals-leg.strike,0.0) if leg.typ=="CE" else np.maximum(leg.strike-terminals,0.0)
                pnl_mc+=leg.qty*intrinsic
            pnl_mc+=entry_cashflow
            mc_ev=float(pnl_mc.mean())
            if mc_ev <= 0:
                continue
            q05=float(np.quantile(pnl_mc,.05))
            es95=float(max(0.0,-np.mean(pnl_mc[pnl_mc<=q05]))) if np.any(pnl_mc<=q05) else 0.0
            risk_ref=max(es95,1e-6)
            max_profit=max(0.0,entry_reference_max_profit(legs,entry_cashflow))
            # Build minute marks from the completed entry time to expiry.
            date_span=sessions[(sessions>=entry_complete.normalize())&(sessions<=expiry)]
            series=build_day_series(zf,file_map,date_span,legs,entry_complete,expiry,day_cache)
            marks=portfolio_mark(series,legs,entry_cashflow)
            if marks.empty:
                skips["empty_mark_path"]+=1; continue
            marks=marks.sort_values("timestamp").reset_index(drop=True)
            marks["pnl_points"]=pd.to_numeric(marks.pnl_points,errors="coerce")
            mae=float(marks.pnl_points.min()); mfe=float(marks.pnl_points.max())
            lot=lot_size(expiry)
            entry_brokerage_base=4.0
                    # Entry STT uses adjusted execution premiums on option sales.
            entry_stt_base=sum(abs(l.qty)*(l.entry_price-SLIPPAGE_POINTS)*lot*stt_rate(l.entry_ts) for l in legs if l.qty<0)
            trade_meta.append({
                "decision_date":decision.date().isoformat(),"expiry":expiry.date().isoformat(),
                "spot_0930":spot,"entry_complete":str(entry_complete),
                "p20":strikes["p20"],"p35":strikes["p35"],"c65":strikes["c65"],"c80":strikes["c80"],
                "mc_ev_points":mc_ev,"mc_es95_points":es95,"max_profit_reference_points":max_profit,
                "mfe_points":mfe,"mae_points":mae,"lot_size":lot
            })

            path_rows=marks[["timestamp","pnl_points"]].copy()
            pvals=path_rows.pnl_points.to_numpy(float)
            tsvals=pd.to_datetime(path_rows.timestamp).to_numpy()

            for family,param_a,param_b,param_r in rule_candidates():
                trigger=None; reason="expiry"
                peak=0.0; activated=False
                for j,(ts,p) in enumerate(zip(tsvals,pvals)):
                    p=float(p); ts=pd.Timestamp(ts)
                    trig=trigger_exit(family,p,max_profit,risk_ref,param_a,param_b,param_r)
                    if trig is not None:
                        trigger=ts; reason=trig; break
                    if family=="trailing_stop" and max_profit>0:
                        peak=max(peak,p)
                        if peak>0 and p <= peak-param_b*max_profit:
                            trigger=ts; reason="trailing_stop"; break
                    elif family in {"trailing_target","trailing_target_stop"} and max_profit>0:
                        if not activated and p >= param_a*max_profit:
                            activated=True
                            peak=p
                        elif activated:
                            peak=max(peak,p)
                            retracement = param_r if family == "trailing_target_stop" else param_b
                            if p <= peak-retracement*max_profit:
                                trigger=ts; reason="trailing_target"; break
                if trigger is None and family!="expiry_control" and len(pvals)==0:
                    skips["no_path"]+=1; continue
                if family=="expiry_control":
                    exits=expiry_exit(zf,file_map,sessions,legs,expiry,exit_cache)
                    if exits is None:
                        skips["expiry_exit_missing"]+=1; continue
                    exit_time=max(x[2] for x in exits)
                else:
                    exits=last_or_next_execution(zf,file_map,sessions,legs,trigger,expiry,exit_cache,use_open=True) if trigger is not None else None
                    if exits is None:
                        skips["trigger_unexecutable"]+=1; continue
                    exit_time=max(x[2] for x in exits)
                for brokerage in BROKERAGES:
                    entry_brokerage=4*brokerage
                    gross_points,net_inr,exit_stt=realized_exit(entry_cashflow,exits,expiry,brokerage,entry_brokerage,entry_stt_base,lot)
                    # realized_exit includes entry_brokerage in costs; entry STT base was not included there.
                    net_inr -= entry_stt_base
                    results.append({
                        "decision_date":decision.date().isoformat(),"expiry":expiry.date().isoformat(),
                        "entry_rule":"D3_same_session_0930_gross_gate",
                        "exit_family":family,"target_param":param_a,"stop_param":param_b,"retracement_param":param_r,
                        "brokerage_per_order_inr":brokerage,"lot_size":lot,
                        "mc_ev_points":mc_ev,"mc_es95_points":es95,"max_profit_reference_points":max_profit,
                        "entry_complete":str(entry_complete),"exit_trigger":str(trigger) if trigger is not None else "",
                        "exit_time":str(exit_time),"exit_reason":reason,
                        "holding_minutes":float((pd.Timestamp(exit_time)-entry_complete).total_seconds()/60.0),
                        "mae_points":mae,"mfe_points":mfe,
                        "realized_gross_points":gross_points,"realized_net_inr":net_inr,
                        "entry_stt_inr":entry_stt_base,"exit_stt_inr":exit_stt,
                        "exit_brokerage_inr":entry_brokerage,
                    })
            if i%25==0: print(f"T3 opportunities {i}/{len(opportunities)}",flush=True)

    out_results=pd.DataFrame(results)
    out_meta=pd.DataFrame(trade_meta)
    if out_results.empty:
        raise SystemExit("No T3 exit rows generated")
    out_results.to_csv(out/"T3_EXIT_TRADE_LEVEL.csv",index=False)
    out_meta.to_csv(out/"T3_ENTRY_CONTROL_TRADES.csv",index=False)
    summary=[]
    for (fam,a,b,r,brokerage),g in out_results.groupby(["exit_family","target_param","stop_param","retracement_param","brokerage_per_order_inr"],dropna=False):
        x=g.realized_net_inr.to_numpy(float)
        gains=x[x>0].sum(); losses=-x[x<0].sum()
        eq=np.cumsum(x); dd=eq-np.maximum.accumulate(eq)
        summary.append({
            "exit_family":fam,"target_param":a,"stop_param":b,"retracement_param":r,
            "brokerage_per_order_inr":brokerage,"trades":len(g),
            "win_rate":float(np.mean(x>0)),"mean_net_inr":float(x.mean()),
            "median_net_inr":float(np.median(x)),"total_net_inr":float(x.sum()),
            "profit_factor":float(gains/losses) if losses>0 else np.inf,
            "max_drawdown_inr":float(dd.min()),
            "mean_holding_minutes":float(g.holding_minutes.mean()),
            "mean_mae_points":float(g.mae_points.mean()),
            "mean_mfe_points":float(g.mfe_points.mean())
        })
    pd.DataFrame(summary).sort_values(["brokerage_per_order_inr","total_net_inr"],ascending=[True,False]).to_csv(out/"T3_EXIT_SUMMARY.csv",index=False)
    pd.DataFrame([dict(skips)]).to_json(out/"T3_SKIP_COUNTS.json",orient="records",indent=2)
    print("T3 COMPLETE"); print(pd.DataFrame(summary).sort_values(["brokerage_per_order_inr","total_net_inr"],ascending=[True,False]).head(40).to_string(index=False)); print("SKIPS",dict(skips))

if __name__=="__main__":
    main()
