from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nifty_mc.strategy_catalog import build_strategy

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_BY_REGIME = {
    "low": ["Risk Reversal", "Long Synthetic Future", "Buy Call"],
    "medium": ["Short Straddle", "Put Ratio Spread", "Short Strangle", "Strip", "Buy Put"],
    "high": ["Sell Put", "Risk Reversal", "Long Synthetic Future", "Batman"],
}
CPCV_FREQUENCY = {
    "low": {"Risk Reversal": 9, "Long Synthetic Future": 4, "Buy Call": 2},
    "medium": {"Short Straddle": 4, "Put Ratio Spread": 4, "Short Strangle": 3, "Strip": 3, "Buy Put": 1},
    "high": {"Sell Put": 5, "Risk Reversal": 5, "Long Synthetic Future": 3, "Batman": 2},
}
EXIT_MODES = ("expiry_settlement", "15:00:00", "15:10:00")

def load_index_1m(path: Path) -> pd.DataFrame:
    x = pd.read_parquet(path)
    x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce")
    if getattr(x["timestamp"].dt, "tz", None) is not None:
        x["timestamp"] = x["timestamp"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    x["trading_day"] = pd.to_datetime(
        x.get("trading_day", x["timestamp"]), errors="coerce"
    ).dt.normalize()
    for c in ("open", "high", "low", "close"):
        if c in x:
            x[c] = pd.to_numeric(x[c], errors="coerce")
    return x.dropna(subset=["timestamp","trading_day","close"]).sort_values("timestamp").reset_index(drop=True)

def daily_close(index_1m: pd.DataFrame) -> pd.DataFrame:
    return (
        index_1m.sort_values("timestamp")
        .groupby("trading_day", as_index=False)
        .tail(1)[["trading_day","close"]]
        .rename(columns={"trading_day":"date"})
        .sort_values("date")
        .reset_index(drop=True)
    )

def combine_nifty_history(hf_daily: pd.DataFrame, warmup_csv: Path) -> pd.DataFrame:
    legacy = pd.read_csv(warmup_csv)
    lookup = {str(c).strip().lower(): c for c in legacy.columns}
    date_col = lookup.get("date")
    price_col = lookup.get("price") or lookup.get("close")
    if date_col is None or price_col is None:
        raise ValueError("pinned NIFTY source CSV missing Date/Price")
    legacy = pd.DataFrame({
        "date": pd.to_datetime(legacy[date_col], errors="coerce", dayfirst=False).dt.normalize(),
        "close": pd.to_numeric(
            legacy[price_col].astype(str).str.replace(",","",regex=False), errors="coerce"
        ),
    }).dropna()
    out = pd.concat([legacy, hf_daily], ignore_index=True).drop_duplicates("date", keep="last").sort_values("date")
    out["logret"] = np.log(out["close"]).diff()
    return out.reset_index(drop=True)

def load_option_file(path: Path) -> pd.DataFrame:
    x = pd.read_parquet(path)
    cols = ["timestamp","trading_day","expiry","strike","option_type","open","close"]
    for c in cols:
        if c not in x.columns:
            x[c] = np.nan
    x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce")
    if getattr(x["timestamp"].dt, "tz", None) is not None:
        x["timestamp"] = x["timestamp"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    x["trading_day"] = pd.to_datetime(x["trading_day"], errors="coerce").dt.normalize()
    x["expiry"] = pd.to_datetime(x["expiry"], errors="coerce").dt.normalize()
    for c in ("strike","open","close"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["option_type"] = x["option_type"].astype(str).str.upper()
    return x.dropna(subset=["timestamp","trading_day","expiry","strike"]).sort_values("timestamp").reset_index(drop=True)

def parse_expiry(path: Path) -> pd.Timestamp:
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.parquet", path.name)
    if not m:
        raise ValueError(path.name)
    return pd.Timestamp(m.group(1)).normalize()

def compute_regime(daily: pd.DataFrame, cutoff: pd.Timestamp) -> dict[str, float | str]:
    x = daily.loc[daily["date"] <= cutoff, ["date","close"]].drop_duplicates("date").sort_values("date")
    r = np.log(x["close"]).diff()
    rv20 = (r.rolling(20).std(ddof=1) * np.sqrt(252)).dropna()
    if len(rv20) < 61:
        raise ValueError("insufficient past-only RV20 history")
    latest = float(rv20.iloc[-1])
    hist = rv20.iloc[:-1].tail(252)
    rank = float(np.mean(hist.to_numpy(float) <= latest))
    regime = "low" if rank <= 1/3 else ("medium" if rank <= 2/3 else "high")
    return {"rv20": latest, "rv20_rank": rank, "vol_regime": regime}

def mc_terminal(returns: np.ndarray, spot: float, seed: int, horizon_sessions: int = 3, paths: int = 5000) -> np.ndarray:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 756:
        raise ValueError("need at least 756 completed daily log returns")
    rng = np.random.default_rng(seed)
    s = rng.choice(r[-756:], size=paths*horizon_sessions, replace=True).reshape(paths, horizon_sessions)
    return spot * np.exp(s.sum(axis=1))

def strategy_targets(strategy: str, terminal: np.ndarray, spot: float) -> dict[str,float]:
    p20,p35,p65,p80=np.percentile(terminal,[20,35,65,80])
    a={"p20":float(p20),"p35":float(p35),"c65":float(p65),"c80":float(p80),"atm":float(spot)}
    req={
        "Risk Reversal":["c65","p35"],"Long Synthetic Future":["atm"],"Buy Call":["atm"],
        "Short Straddle":["atm"],"Put Ratio Spread":["atm","p35"],"Short Strangle":["p35","c65"],
        "Strip":["atm"],"Buy Put":["atm"],"Sell Put":["atm"],"Batman":["p20","p35","c65","c80"]
    }
    return {k:a[k] for k in req[strategy]}

def map_unique_strikes(chain: pd.DataFrame, targets: dict[str,float]) -> dict[str,float]:
    vals=np.sort(chain["strike"].dropna().unique().astype(float))
    if len(vals)<len(targets): raise ValueError("not enough unique strikes")
    out={}; used=set()
    for label,target in sorted(targets.items(), key=lambda kv:(0 if kv[0]=="atm" else 1,kv[1])):
        for idx in np.argsort(np.abs(vals-target)):
            v=float(vals[idx])
            if v not in used:
                out[label]=v; used.add(v); break
        else: raise ValueError(f"cannot map {label}")
    return out

def timestamp_row(day: pd.DataFrame, ts: str, option_type: str, strike: float) -> pd.Series:
    x=day.loc[
        day["timestamp"].dt.strftime("%H:%M:%S").eq(ts)
        & day["option_type"].eq(option_type)
        & np.isclose(day["strike"].to_numpy(float), float(strike), atol=1e-9)
    ]
    if x.empty: raise ValueError(f"missing {ts} {option_type} {strike}")
    return x.iloc[0]

def entry_and_mc(index_name: str, entry_day: pd.DataFrame, expiry: pd.Timestamp, spot: float, terminal: np.ndarray,
                 strategy: str, entry_cost_points: float, entry_slippage: float) -> dict[str,Any]:
    day=entry_day.loc[entry_day["expiry"].eq(expiry)].copy()
    targets=strategy_targets(strategy,terminal,spot)
    strikes=map_unique_strikes(day,targets)
    legs=build_strategy(strategy,strikes)
    priced=[]; entry_cash=0.0; contracts=0
    for leg in legs:
        row=timestamp_row(day,"09:30:00",leg.option_type,leg.strike)
        raw=float(row["open"])
        if index_name=="SENSEX":
            px=raw+(entry_slippage if leg.qty>0 else -entry_slippage)
        else:
            # Historical NIFTY 1-minute data has OHLC, not point-in-time bid/ask.
            px=raw
        if not np.isfinite(px) or px<=0: raise ValueError("invalid entry price")
        entry_cash-=int(leg.qty)*px
        contracts+=abs(int(leg.qty))
        priced.append({"side":"BUY" if leg.qty>0 else "SELL","option_type":leg.option_type,
                       "strike":float(leg.strike),"qty":int(leg.qty),"premium_points":px})
    gross=np.full(len(terminal),entry_cash,dtype=float)
    for leg in priced:
        intr=(np.maximum(terminal-leg["strike"],0.0) if leg["option_type"]=="CE"
              else np.maximum(leg["strike"]-terminal,0.0))
        gross += int(leg["qty"])*intr
    net=gross-entry_cost_points*contracts
    q05=float(np.quantile(net,0.05)); q01=float(np.quantile(net,0.01))
    es95=float(max(0,-np.mean(net[net<=q05])))
    es99=float(max(0,-np.mean(net[net<=q01])))
    ev=float(np.mean(net)); pop=float(np.mean(net>0))
    risk=max(es95,es99)
    return {"strategy":strategy,"strikes":strikes,"legs":priced,"entry_cashflow":entry_cash,
            "contracts":contracts,"mc_ev":ev,"mc_pop":pop,"es95":es95,"es99":es99,
            "risk_points":risk,"eligible":ev>0,"entry_cost_points":entry_cost_points*contracts}

def nse_exit_pnl(entry:dict[str,Any], exit_day:pd.DataFrame, mode:str, lot_size:int) -> float:
    if mode=="expiry_settlement":
        return None
    cash=0.0
    for leg in entry["legs"]:
        row=timestamp_row(exit_day,mode,leg["option_type"],leg["strike"])
        raw=float(row["open"])
        side="SELL" if leg["qty"]>0 else "BUY"
        cash += -int(leg["qty"])*raw
    # Same 2-point/contract stress is applied to closing execution.
    return float((entry["entry_cashflow"] + cash - entry["entry_cost_points"] - 2.0*entry["contracts"]) * lot_size)

def sensex_exit_costs(exit_date, legs, prices, lot_size):
    if exit_date < pd.Timestamp("2024-10-01"):
        bse=500/10_000_000
    else:
        bse=3250/10_000_000
    stt=0.0015 if exit_date>=pd.Timestamp("2026-04-01") else 0.001
    buy_turn=sum(max(0,-int(l["qty"]))*p for l,p in zip(legs,prices))*lot_size
    sell_turn=sum(max(0,int(l["qty"]))*p for l,p in zip(legs,prices))*lot_size
    turnover=buy_turn+sell_turn
    brokerage=10.0*len(legs); bse_txn=bse*turnover; sebi=0.000001*turnover
    stamp=0.00003*buy_turn; stt_cost=stt*sell_turn; gst=0.18*(brokerage+bse_txn+sebi)
    return brokerage+bse_txn+sebi+stamp+stt_cost+gst

def sensex_expiry_cost(entry_date, expiry_spot, legs, lot_size):
    stt_ex=0.00125 if entry_date<pd.Timestamp("2026-04-01") else 0.0015
    x=0.0
    for leg in legs:
        if int(leg["qty"])<=0: continue
        intrinsic=(max(expiry_spot-leg["strike"],0.0) if leg["option_type"]=="CE" else max(leg["strike"]-expiry_spot,0.0))
        x += stt_ex*int(leg["qty"])*intrinsic*lot_size
    return x

def sensex_exit_pnl(entry:dict[str,Any], exit_day:pd.DataFrame, mode:str, lot_size:int, entry_date:pd.Timestamp, entry_only_cost:float) -> float:
    prices=[]
    for leg in entry["legs"]:
        row=timestamp_row(exit_day,mode,leg["option_type"],leg["strike"])
        raw=float(row["open"])
        side="SELL" if leg["qty"]>0 else "BUY"
        px=raw-0.5 if side=="SELL" else raw+0.5
        prices.append(px)
    cash=-sum(int(l["qty"])*p for l,p in zip(entry["legs"],prices))
    exit_cost=sensex_exit_costs(exit_day["trading_day"].iloc[0],entry["legs"],prices,lot_size)
    return float((entry["entry_cashflow"]+cash-entry_only_cost/lot_size-exit_cost/lot_size)*lot_size)

def bootstrap(values,n=10000,block=3,seed=20260920):
    x=np.asarray(values,dtype=float)
    if len(x)==0:return {"n":0}
    if len(x)==1:return {"n":1,"observed_mean":float(x[0]),"ci_low":float(x[0]),"ci_high":float(x[0]),"p_mean_gt_zero":float(x[0]>0)}
    rng=np.random.default_rng(seed); means=np.empty(n)
    for i in range(n):
        sample=[]
        while len(sample)<len(x):
            st=int(rng.integers(0,len(x)))
            for j in range(block):
                sample.append(x[(st+j)%len(x)])
                if len(sample)>=len(x):break
        means[i]=np.mean(sample[:len(x)])
    return {"n":len(x),"observed_mean":float(x.mean()),
            "ci_low":float(np.quantile(means,0.025)),"ci_high":float(np.quantile(means,0.975)),
            "p_mean_gt_zero":float(np.mean(means>0))}

def summarize(g:pd.DataFrame)->dict[str,Any]:
    if g.empty:return {"trades":0,"total_pnl_inr":0.0,"mean_pnl_inr":0.0,"median_pnl_inr":0.0,"win_rate":0.0,"profit_factor":0.0,"max_drawdown_inr":0.0}
    x=pd.to_numeric(g["pnl_inr"],errors="coerce").dropna().to_numpy(float)
    eq=np.cumsum(x); dd=eq-np.maximum.accumulate(eq)
    gains=float(x[x>0].sum()); losses=float(-x[x<0].sum())
    return {"trades":len(x),"total_pnl_inr":float(x.sum()),"mean_pnl_inr":float(x.mean()),
            "median_pnl_inr":float(np.median(x)),"win_rate":float(np.mean(x>0)),
            "profit_factor":gains/losses if losses>0 else float("inf"),
            "max_drawdown_inr":float(dd.min())}

def run_nifty(paths:int,seed_base:int,data_root:Path):
    idx_hf=load_index_1m(data_root/"index"/"NIFTY.parquet")
    hf_daily=daily_close(idx_hf)
    daily=combine_nifty_history(hf_daily,ROOT/"data/expiry_exit/nifty50_source.csv")
    sessions=pd.DatetimeIndex(hf_daily["date"].unique()).sort_values()
    option_paths=sorted((data_root/"options"/"NIFTY").glob("*.parquet"))
    rows=[]
    for path in option_paths:
        expiry=parse_expiry(path)
        if expiry not in sessions: continue
        pos=int(sessions.get_loc(expiry))
        if pos<4: continue
        entry_date=sessions[pos-3]; cutoff=sessions[pos-4]
        if cutoff not in pd.DatetimeIndex(daily["date"]): continue
        day=load_option_file(path)
        entry_day=day.loc[day["trading_day"].eq(entry_date)].copy()
        expiry_day=day.loc[day["trading_day"].eq(expiry)].copy()
        if entry_day.empty or expiry_day.empty: continue
        spot_rows=idx_hf.loc[idx_hf["timestamp"].dt.strftime("%H:%M:%S").eq("09:30:00") & idx_hf["trading_day"].eq(entry_date)]
        spot=float(spot_rows.iloc[0]["open"]) if not spot_rows.empty else float(daily.loc[daily.date.eq(entry_date),"close"].iloc[0])
        ret=np.log(daily.loc[daily["date"]<=cutoff,"close"]).diff().dropna().to_numpy(float)
        try: terminal=mc_terminal(ret,spot,seed_base+int(expiry.strftime("%Y%m%d")),3,paths)
        except Exception: continue
        regime=compute_regime(daily,cutoff)
        all_candidates=[]
        for strategy in CANDIDATES_BY_REGIME[regime["vol_regime"]]:
            try: all_candidates.append(entry_and_mc("NIFTY",entry_day,expiry,spot,terminal,strategy,2.0,0.0))
            except Exception: pass
        try: all_candidates.append(entry_and_mc("NIFTY",entry_day,expiry,spot,terminal,"Batman",2.0,0.0))
        except Exception: pass
        adaptive=[x for x in all_candidates if x["strategy"] in CANDIDATES_BY_REGIME[regime["vol_regime"]] and x["eligible"]]
        adaptive=sorted(adaptive,key=lambda z:(-z["mc_ev"],-CPCV_FREQUENCY[regime["vol_regime"]][z["strategy"]],z["strategy"]))
        selected={"Batman":next((x for x in all_candidates if x["strategy"]=="Batman" and x["eligible"]),None),
                  "Adaptive":(adaptive[0] if adaptive else None)}
        expiry_spot=float(hf_daily.loc[hf_daily.date.eq(expiry),"close"].iloc[-1])
        for strategy,entry in selected.items():
            if entry is None: continue
            lot_size=75 if expiry<=pd.Timestamp("2025-12-30") else 65
            base_pnl=(entry["entry_cashflow"] + sum(int(l["qty"])*(
                max(expiry_spot-l["strike"],0) if l["option_type"]=="CE" else max(l["strike"]-expiry_spot,0)
            ) for l in entry["legs"]) - entry["entry_cost_points"])*lot_size
            rows.append({"index":"NIFTY","strategy":strategy,"exit":"expiry_settlement","entry_date":entry_date.date(),"expiry":expiry.date(),
                         "split":"development" if expiry.year<=2022 else ("validation" if expiry.year<=2024 else "holdout"),
                         "pnl_inr":base_pnl,"mc_ev":entry["mc_ev"],"regime":regime["vol_regime"]})
            for mode in ("15:00:00","15:10:00"):
                try: p=nse_exit_pnl(entry,expiry_day,mode,lot_size)
                except Exception: continue
                rows.append({"index":"NIFTY","strategy":strategy,"exit":mode[:5],"entry_date":entry_date.date(),"expiry":expiry.date(),
                             "split":"development" if expiry.year<=2022 else ("validation" if expiry.year<=2024 else "holdout"),
                             "pnl_inr":p,"mc_ev":entry["mc_ev"],"regime":regime["vol_regime"]})
    return pd.DataFrame(rows)

def run_sensex(paths:int,seed_base:int,data_root:Path,sensex_mc_daily:Path):
    from scripts.sensex_backtest_v1 import run_backtest, realized_costs
    rows=[]
    idx_path=data_root/"index"/"SENSEX.parquet"; opts=data_root/"options"/"SENSEX"
    for split in ("development","validation","holdout"):
        candidates,adaptive_trades,stats=run_backtest(opts,idx_path,split,0.5,seed_base, sensex_mc_daily, True)
        from scripts.sensex_backtest_v1 import run_batman_from_candidates, load_option_file, realized_costs as rc
        batman=run_batman_from_candidates(candidates,opts,idx_path,split,0.5,seed_base)
        for strat,trade_df in (("Adaptive",adaptive_trades),("Batman",batman)):
            for _,r in trade_df.iterrows():
                expiry=pd.Timestamp(r["expiry"]).normalize(); entry_date=pd.Timestamp(r["entry_date"]).normalize()
                path=opts/f"{expiry.date()}.parquet"
                if not path.exists(): continue
                # Load the full expiry file so both the entry-day quote snapshot and
                # expiry-day 15:00/15:10 bars are available.
                opt=load_option_file(path, entry_date)
                full=pd.read_parquet(path)
                full["timestamp"]=pd.to_datetime(full["timestamp"],errors="coerce")
                if getattr(full["timestamp"].dt,"tz",None) is not None:
                    full["timestamp"]=full["timestamp"].dt.tz_localize(None)
                full["trading_day"]=pd.to_datetime(full["trading_day"],errors="coerce").dt.normalize()
                full["expiry"]=pd.to_datetime(full["expiry"],errors="coerce").dt.normalize()
                for cc in ("strike","open","close"):
                    full[cc]=pd.to_numeric(full[cc],errors="coerce")
                full["option_type"]=full["option_type"].astype(str).str.upper()
                expiry_day=full.loc[full["trading_day"].eq(expiry)].copy()
                legs=json.loads(r["legs_json"])
                entry_cash=float(r["entry_cashflow_points"])
                entry_only=float(r.get("entry_cost_inr_entry_only",np.nan))
                if not np.isfinite(entry_only):
                    entry_only=float(r.get("realized_cost_inr_per_lot",0.0))
                # baseline uses engine's frozen realized result
                base=float(r.get("realized_pnl_inr",0.0))
                rows.append({"index":"SENSEX","strategy":strat,"exit":"expiry_settlement","entry_date":entry_date.date(),"expiry":expiry.date(),
                             "split":split,"pnl_inr":base,"mc_ev":float(r.get("mc_ev_net",np.nan)),"regime":r.get("regime")})
                for mode in ("15:00:00","15:10:00"):
                    try:
                        p=sensex_exit_pnl(r,expiry_day,mode,20,entry_date,entry_only)
                    except Exception: continue
                    rows.append({"index":"SENSEX","strategy":strat,"exit":mode[:5],"entry_date":entry_date.date(),"expiry":expiry.date(),
                                 "split":split,"pnl_inr":p,"mc_ev":float(r.get("mc_ev_net",np.nan)),"regime":r.get("regime")})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",required=True)
    ap.add_argument("--out-dir",default="reports/expiry_exit")
    ap.add_argument("--paths",type=int,default=5000)
    ap.add_argument("--seed-base",type=int,default=20260920)
    args=ap.parse_args()
    data_root=Path(args.data_root)
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    frames=[run_nifty(args.paths,args.seed_base,data_root),run_sensex(args.paths,args.seed_base,data_root)]
    trades=pd.concat(frames,ignore_index=True)
    trades.to_csv(out/"TRADE_LEVEL_RESULTS.csv",index=False)
    summaries=[]
    for (index,strategy,exit_mode,split),g in trades.groupby(["index","strategy","exit","split"]):
        s=summarize(g); s.update({"index":index,"strategy":strategy,"exit":exit_mode,"split":split})
        summaries.append(s)
    summary=pd.DataFrame(summaries)
    summary.to_csv(out/"EXIT_SUMMARY_BY_SPLIT.csv",index=False)
    oos=[]
    for (index,strategy,exit_mode),g in trades.loc[trades["split"].isin(["validation","holdout"])].groupby(["index","strategy","exit"]):
        s=summarize(g); s.update({"index":index,"strategy":strategy,"exit":exit_mode})
        bs=bootstrap(pd.to_numeric(g["pnl_inr"],errors="coerce").dropna().to_numpy(float))
        s.update({f"bootstrap_{k}":v for k,v in bs.items()})
        oos.append(s)
    oos_df=pd.DataFrame(oos); oos_df.to_csv(out/"COMBINED_OOS_SUMMARY.csv",index=False)
    piv=summary.pivot_table(index=["index","strategy","split"],columns="exit",values=["trades","total_pnl_inr","mean_pnl_inr","win_rate","profit_factor"],aggfunc="first")
    piv.to_csv(out/"EXIT_COMPARISON_PIVOT.csv")
    lines=["# Expiry-Day Exit Analysis — NIFTY + SENSEX","","Entry rules were frozen before exit outcomes. Exit scenarios: expiry settlement, 15:00 IST, 15:10 IST.","",
            "Historical minute-bar execution proxy: exact exit-minute OPEN; no same-minute CLOSE look-ahead.",
            "NIFTY: 2 option-point stress at entry and 2 option-point stress at early exit, one strategy unit/one lot for exit comparison.",
            "SENSEX: frozen S5/S6 one-lot transfer-edge entry gate and SENSEX transaction-cost model; early-close turnover costs applied; no exercise STT on early exits.",
            ""]
    for _,row in oos_df.sort_values(["index","strategy","exit"]).iterrows():
        lines.append(f"- {row['index']} {row['strategy']} {row['exit']}: n={int(row['trades'])}, total=₹{row['total_pnl_inr']:,.2f}, mean=₹{row['mean_pnl_inr']:,.2f}, win={row['win_rate']:.1%}, PF={row['profit_factor']:.2f}, bootstrap CI={row.get('bootstrap_ci_low',float('nan'))} to {row.get('bootstrap_ci_high',float('nan'))}.")
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(summary.to_string(index=False))
    print(oos_df.to_string(index=False))

if __name__=="__main__":
    main()
