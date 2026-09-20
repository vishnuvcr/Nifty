from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nifty_mc.strategy_catalog import build_strategy

REGIMES = {
    "low": ["Risk Reversal", "Long Synthetic Future", "Buy Call"],
    "medium": ["Short Straddle", "Put Ratio Spread", "Short Strangle", "Strip", "Buy Put"],
    "high": ["Sell Put", "Risk Reversal", "Long Synthetic Future", "Batman"],
}
CPCV_FREQ = {
    "low": {"Risk Reversal": 9, "Long Synthetic Future": 4, "Buy Call": 2},
    "medium": {"Short Straddle": 4, "Put Ratio Spread": 4, "Short Strangle": 3, "Strip": 3, "Buy Put": 1},
    "high": {"Sell Put": 5, "Risk Reversal": 5, "Long Synthetic Future": 3, "Batman": 2},
}

CONFIG = {
    "NIFTY": {
        "index_path": "data/expiry_exit/index_NIFTY.parquet",
        "options_dir": "data/expiry_exit/options_NIFTY",
        "lot_mode": "nse_historical",
        "entry_stress_points_per_contract": 2.0,
        "exit_stress_points_per_contract": 2.0,
        "sleeve": "NSE",
        "split_bounds": {
            "development": ("2020-01-01", "2022-12-31"),
            "validation": ("2023-01-01", "2024-12-31"),
            "holdout": ("2025-01-01", "2026-03-30"),
        },
    },
    "SENSEX": {
        "index_path": "data/expiry_exit/index_SENSEX.parquet",
        "options_dir": "data/expiry_exit/options_SENSEX",
        "lot_mode": "fixed_20",
        "entry_stress_points_per_contract": 0.50,
        "exit_stress_points_per_contract": 0.50,
        "sleeve": "BSE",
        "split_bounds": {
            "development": ("2024-01-01", "2024-12-31"),
            "validation": ("2025-01-01", "2025-12-31"),
            "holdout": ("2026-01-01", "2026-12-31"),
        },
    },
}

def load_index(path: Path) -> pd.DataFrame:
    x = pd.read_parquet(path)
    x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce")
    x["trading_day"] = pd.to_datetime(x.get("trading_day", x["timestamp"]), errors="coerce").dt.normalize()
    for c in ("open", "high", "low", "close"):
        if c in x:
            x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["timestamp", "trading_day", "close"]).sort_values("timestamp")
    return x.reset_index(drop=True)

def daily_close(index_1m: pd.DataFrame) -> pd.DataFrame:
    return (
        index_1m.sort_values("timestamp")
        .groupby("trading_day", as_index=False)
        .tail(1)[["trading_day", "close"]]
        .rename(columns={"trading_day": "date"})
        .sort_values("date")
        .reset_index(drop=True)
    )

def log_returns(close_df: pd.DataFrame) -> pd.Series:
    return np.log(close_df["close"]).diff()

def compute_regime(daily: pd.DataFrame, cutoff: pd.Timestamp) -> dict[str, float | str]:
    x = daily.loc[daily["date"] <= cutoff].copy()
    r = log_returns(x)
    rv20 = (r.rolling(20).std(ddof=1) * math.sqrt(252)).dropna()
    if len(rv20) < 61:
        raise ValueError("insufficient RV20 regime history")
    latest = float(rv20.iloc[-1])
    hist = rv20.iloc[:-1].tail(252)
    rank = float(np.mean(hist.to_numpy(float) <= latest))
    regime = "low" if rank <= 1/3 else ("medium" if rank <= 2/3 else "high")
    return {"rv20": latest, "rv20_rank": rank, "vol_regime": regime}

def mc_terminal(returns: np.ndarray, spot: float, paths: int, horizon_sessions: int, seed: int) -> np.ndarray:
    clean = np.asarray(returns, dtype=float)
    clean = clean[np.isfinite(clean)]
    if len(clean) < 756:
        raise ValueError("need at least 756 historical daily log returns")
    rng = np.random.default_rng(seed)
    sampled = rng.choice(clean[-756:], size=paths * horizon_sessions, replace=True).reshape(paths, horizon_sessions)
    return spot * np.exp(sampled.sum(axis=1))

def strategy_targets(strategy: str, terminal: np.ndarray, spot: float) -> dict[str, float]:
    p20, p35, p65, p80 = np.percentile(terminal, [20, 35, 65, 80])
    all_targets = {"p20": float(p20), "p35": float(p35), "c65": float(p65), "c80": float(p80), "atm": float(spot)}
    required = {
        "Risk Reversal": ["c65", "p35"],
        "Long Synthetic Future": ["atm"],
        "Buy Call": ["atm"],
        "Short Straddle": ["atm"],
        "Put Ratio Spread": ["atm", "p35"],
        "Short Strangle": ["p35", "c65"],
        "Strip": ["atm"],
        "Buy Put": ["atm"],
        "Sell Put": ["atm"],
        "Batman": ["p20", "p35", "c65", "c80"],
    }
    return {k: all_targets[k] for k in required[strategy]}

def map_unique_strikes(snapshot: pd.DataFrame, targets: dict[str, float]) -> dict[str, float]:
    available = np.sort(snapshot["strike"].dropna().astype(float).unique())
    if len(available) < len(targets):
        raise ValueError("not enough unique strikes")
    used: set[float] = set()
    out: dict[str, float] = {}
    for label, target in sorted(targets.items(), key=lambda kv: (0 if kv[0] == "atm" else 1, kv[1])):
        for idx in np.argsort(np.abs(available - target)):
            strike = float(available[idx])
            if strike not in used:
                out[label] = strike
                used.add(strike)
                break
        else:
            raise ValueError(f"cannot map {label} to unique strike")
    return out

def parse_expiry(path: Path) -> pd.Timestamp:
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.parquet", path.name)
    if not m:
        raise ValueError(path.name)
    return pd.Timestamp(m.group(1)).normalize()

def load_option_file(path: Path) -> pd.DataFrame:
    x = pd.read_parquet(path)
    for c in ("timestamp", "trading_day", "expiry", "strike", "option_type", "open", "close"):
        if c not in x.columns:
            x[c] = np.nan
    x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce")
    x["trading_day"] = pd.to_datetime(x["trading_day"], errors="coerce").dt.normalize()
    x["expiry"] = pd.to_datetime(x["expiry"], errors="coerce").dt.normalize()
    x["strike"] = pd.to_numeric(x["strike"], errors="coerce")
    x["open"] = pd.to_numeric(x["open"], errors="coerce")
    x["close"] = pd.to_numeric(x["close"], errors="coerce")
    x["option_type"] = x["option_type"].astype(str).str.upper()
    return x.dropna(subset=["timestamp","trading_day","expiry","strike","open"]).sort_values("timestamp").reset_index(drop=True)

def lot_size(index_name: str, expiry: pd.Timestamp) -> int:
    if index_name == "SENSEX":
        return 20
    # NSE circular FAOP70616: NIFTY 75 -> 65, with existing weekly/monthly lot size
    # remaining applicable through 30-Dec-2025 expiry.
    return 75 if expiry <= pd.Timestamp("2025-12-30") else 65

def nse_cost_exit_points(contract_count: int) -> float:
    return 2.0 * contract_count

def sensex_cost_schedule(entry_date: pd.Timestamp) -> dict[str, float]:
    bse_per_rupee_turnover = 500.0/10_000_000.0 if entry_date < pd.Timestamp("2024-10-01") else 3250.0/10_000_000.0
    stt_sell = 0.0015 if entry_date >= pd.Timestamp("2026-04-01") else 0.001
    return {
        "brokerage_per_order": 10.0,
        "bse_txn_rate": bse_per_rupee_turnover,
        "stt_sell_rate": stt_sell,
        "sebi_rate": 0.000001,
        "stamp_buy_rate": 0.00003,
        "gst_rate": 0.18,
    }

def sensex_entry_costs(entry_date, priced_legs, lot_size, entry_cashflow, terminal):
    sched = sensex_cost_schedule(entry_date)
    buy_turn = sum(max(0,int(l["qty"])) * l["premium_points"] for l in priced_legs) * lot_size
    sell_turn = sum(max(0,-int(l["qty"])) * l["premium_points"] for l in priced_legs) * lot_size
    turnover = buy_turn + sell_turn
    brokerage = sched["brokerage_per_order"] * len(priced_legs)
    bse_txn = sched["bse_txn_rate"] * turnover
    sebi = sched["sebi_rate"] * turnover
    stamp = sched["stamp_buy_rate"] * buy_turn
    stt_short = sched["stt_sell_rate"] * sell_turn
    # Preserve S5/S6 historical entry gate logic; expected exercise STT remains in the gate.
    expected_exercise = 0.0
    for leg in priced_legs:
        if int(leg["qty"]) <= 0:
            continue
        intrinsic = np.maximum(terminal-leg["strike"],0.0) if leg["option_type"]=="CE" else np.maximum(leg["strike"]-terminal,0.0)
        expected_exercise += int(leg["qty"]) * float(np.mean(intrinsic)) * lot_size
    stt_exercise = 0.00125 if entry_date < pd.Timestamp("2026-04-01") else 0.0015
    expected_exercise_cost = stt_exercise * expected_exercise
    gst = sched["gst_rate"] * (brokerage + bse_txn + sebi)
    total = brokerage+bse_txn+sebi+stamp+stt_short+gst+expected_exercise_cost
    entry_only = brokerage+bse_txn+sebi+stamp+stt_short+gst
    return float(total), float(entry_only)

def sensex_exit_costs(exit_date, open_positions, exit_prices, lot_size):
    sched=sensex_cost_schedule(exit_date)
    buy_turn = sum(max(0,-int(l["qty"])) * p for l,p in zip(open_positions,exit_prices)) * lot_size
    sell_turn = sum(max(0,int(l["qty"])) * p for l,p in zip(open_positions,exit_prices)) * lot_size
    turnover=buy_turn+sell_turn
    brokerage=sched["brokerage_per_order"]*len(open_positions)
    bse_txn=sched["bse_txn_rate"]*turnover
    sebi=sched["sebi_rate"]*turnover
    stamp=sched["stamp_buy_rate"]*buy_turn
    stt_sell=sched["stt_sell_rate"]*sell_turn
    gst=sched["gst_rate"]*(brokerage+bse_txn+sebi)
    return float(brokerage+bse_txn+sebi+stamp+stt_sell+gst)

def price_entry(index_name: str, snapshot: pd.DataFrame, expiry: pd.Timestamp, strategy: str, strikes: dict[str,float]):
    legs=build_strategy(strategy,strikes)
    rows=[]
    cashflow=0.0
    contracts=0
    ts = snapshot["timestamp"].dt.strftime("%H:%M:%S")
    entry=snapshot.loc[ts.eq("09:30:00") & snapshot["trading_day"].eq(snapshot["trading_day"].iloc[0])]
    for leg in legs:
        x=entry.loc[entry["option_type"].eq(leg.option_type)&np.isclose(entry["strike"],leg.strike,atol=1e-9)]
        if x.empty: raise ValueError(f"missing 09:30 {leg.option_type} {leg.strike}")
        raw=float(x.iloc[0]["open"])
        side="BUY" if leg.qty>0 else "SELL"
        slip=0.5 if index_name=="SENSEX" else 0.0
        px=raw+slip if side=="BUY" else raw-slip
        if px<=0: raise ValueError("non-positive entry price")
        cashflow -= float(leg.qty)*px
        contracts += abs(int(leg.qty))
        rows.append({"option_type":leg.option_type,"strike":float(leg.strike),"qty":int(leg.qty),"premium_points":px,"raw_entry":raw})
    return rows,float(cashflow),contracts

def price_at_timestamp(snapshot: pd.DataFrame, expiry: pd.Timestamp, legs: list[dict[str,Any]], timestamp: str, index_name: str):
    x = snapshot.loc[snapshot["trading_day"].eq(expiry) & snapshot["timestamp"].dt.strftime("%H:%M:%S").eq(timestamp)]
    if x.empty:
        raise ValueError(f"missing exit bar {timestamp}")
    prices=[]
    for leg in legs:
        row=x.loc[x["option_type"].eq(leg["option_type"]) & np.isclose(x["strike"],leg["strike"],atol=1e-9)]
        if row.empty: raise ValueError(f"missing exit {timestamp} {leg['option_type']} {leg['strike']}")
        raw=float(row.iloc[0]["open"])
        side="SELL" if leg["qty"]>0 else "BUY"
        slip=0.5 if index_name=="SENSEX" else 0.0
        px=raw-slip if side=="SELL" else raw+slip
        if px<=0: raise ValueError("non-positive exit price")
        prices.append(px)
    return prices

def evaluate_exit(index_name, entry_date, expiry, spot, terminal, strategy, strikes, legs, entry_cashflow, contracts, entry_cost, lot_sz, snapshot, exit_mode):
    if exit_mode=="expiry_settlement":
        expiry_spot=float(spot)
        # spot here is overridden below by actual expiry index close by caller
        raise RuntimeError("expiry settlement requires explicit expiry spot")
    exit_prices=price_at_timestamp(snapshot,expiry,legs,exit_mode,index_name)
    exit_cashflow=-sum(int(l["qty"])*p for l,p in zip(legs,exit_prices))
    gross_points=entry_cashflow + exit_cashflow
    if index_name=="NIFTY":
        total_cost_points=entry_cost + nse_cost_exit_points(contracts)
        net_points=gross_points-total_cost_points
        exit_cost_inr=nse_cost_exit_points(contracts)*lot_sz
    else:
        exit_cost_inr=sensex_exit_costs(expiry,legs,exit_prices,lot_sz)
        net_points=gross_points-entry_cost/lot_sz-exit_cost_inr/lot_sz
    return float(net_points), float(exit_cost_inr), exit_prices

def expiry_settlement_points(index_name, expiry_spot, legs, entry_cashflow, entry_cost, lot_sz, contracts, entry_date):
    intrinsic=0.0
    for leg in legs:
        intrinsic += int(leg["qty"])*(
            max(expiry_spot-float(leg["strike"]),0.0) if leg["option_type"]=="CE" else max(float(leg["strike"])-expiry_spot,0.0)
        )
    gross=entry_cashflow+intrinsic
    if index_name=="NIFTY":
        net=gross-entry_cost-nse_cost_exit_points(contracts)
    else:
        # Historical S5/S6 expiry settlement charges; retain for baseline.
        sched=sensex_cost_schedule(entry_date)
        buy_turn=sum(max(0,int(l["qty"])*1.0) for l in legs)
        sell_turn=sum(max(0,-int(l["qty"])*1.0) for l in legs)
        # No additional pre-expiry close turnover; exercise STT approximated on positive legs.
        exercise=0.0
        for leg in legs:
            if int(leg["qty"])<=0: continue
            intrinsic_leg=max(expiry_spot-float(leg["strike"]),0.0) if leg["option_type"]=="CE" else max(float(leg["strike"])-expiry_spot,0.0)
            stt_ex=0.00125 if entry_date < pd.Timestamp("2026-04-01") else 0.0015
            exercise += int(leg["qty"])*intrinsic_leg*lot_sz*stt_ex
        net=gross-entry_cost/lot_sz-exercise/lot_sz
    return float(net)

def summarize(df: pd.DataFrame) -> dict[str,Any]:
    if df.empty:
        return {"trades":0,"total_pnl_inr":0.0,"mean_pnl_inr":0.0,"median_pnl_inr":0.0,"win_rate":0.0,"profit_factor":0.0,"max_drawdown_inr":0.0}
    pnl=pd.to_numeric(df["realized_pnl_inr"],errors="coerce").dropna()
    eq=pnl.cumsum(); dd=eq-eq.cummax()
    gains=float(pnl[pnl>0].sum()); losses=float(-pnl[pnl<0].sum())
    return {
        "trades":int(len(pnl)),
        "total_pnl_inr":float(pnl.sum()),
        "mean_pnl_inr":float(pnl.mean()),
        "median_pnl_inr":float(pnl.median()),
        "win_rate":float((pnl>0).mean()),
        "profit_factor":(gains/losses if losses>0 else math.inf),
        "max_drawdown_inr":float(dd.min()),
    }

def block_bootstrap(values,n=10000,block=3,seed=20260920):
    values=np.asarray(values,dtype=float)
    if len(values)<2:return {"n":len(values),"ci_low":float(values[0]) if len(values)==1 else math.nan,"ci_high":float(values[0]) if len(values)==1 else math.nan,"p_mean_gt_zero":float(values[0]>0) if len(values)==1 else math.nan}
    rng=np.random.default_rng(seed)
    means=np.empty(n)
    starts=np.arange(len(values))
    for i in range(n):
        sample=[]
        while len(sample)<len(values):
            st=int(rng.choice(starts))
            for j in range(block):
                sample.append(values[(st+j)%len(values)])
                if len(sample)>=len(values):break
        means[i]=np.mean(sample)
    return {"n":len(values),"observed_mean":float(values.mean()),"ci_low":float(np.quantile(means,0.025)),"ci_high":float(np.quantile(means,0.975)),"p_mean_gt_zero":float(np.mean(means>0))}

def run(index_name: str, exit_mode: str, out_dir: Path, paths: int, seed_base: int):
    cfg=CONFIG[index_name]
    idx=load_index(ROOT/cfg["index_path"])
    daily=daily_close(idx)
    sessions=pd.DatetimeIndex(daily["date"].unique()).sort_values()
    opt_dir=ROOT/cfg["options_dir"]
    exit_time = exit_mode if exit_mode in {"15:00:00","15:10:00"} else None
    rows=[]
    cohort_rows=[]
    for path in sorted(opt_dir.glob("*.parquet")):
        expiry=parse_expiry(path)
        split=None
        for name,(a,b) in cfg["split_bounds"].items():
            if pd.Timestamp(a)<=expiry<=pd.Timestamp(b):
                split=name;break
        if split is None:continue
        if expiry not in sessions: continue
        idxpos=int(sessions.get_loc(expiry))
        if idxpos<4:continue
        entry_date=sessions[idxpos-3]
        cutoff=sessions[idxpos-4]
        if not (pd.Timestamp(cfg["split_bounds"][split][0])<=entry_date<=pd.Timestamp(cfg["split_bounds"][split][1])):continue
        snapshot=load_option_file(path)
        entry_snapshot=snapshot.loc[snapshot["trading_day"].eq(entry_date)].copy()
        if entry_snapshot.empty:continue
        spot_row=idx.loc[(idx["trading_day"].eq(entry_date)) & idx["timestamp"].dt.strftime("%H:%M:%S").eq("09:30:00")]
        if spot_row.empty:continue
        spot=float(spot_row.iloc[0]["open"])
        ret=log_returns(daily.loc[daily["date"]<=cutoff]).dropna().to_numpy(float)
        if len(ret)<756:continue
        seed=seed_base+int(expiry.strftime("%Y%m%d"))
        terminal=mc_terminal(ret,spot,paths,3,seed)
        regime=compute_regime(daily,cutoff)
        lot_sz=lot_size(index_name,expiry)
        strategies=["Batman"] if index_name=="NIFTY" else []
        candidates=list(REGIMES[regime["vol_regime"]])
        if index_name=="NIFTY":
            candidates=sorted(set(candidates)|{"Batman"})
        else:
            candidates=sorted(set(candidates)|{"Batman"})
        evaluated=[]
        for strategy in candidates:
            if strategy!="Batman" and strategy not in REGIMES[regime["vol_regime"]]:
                continue
            try:
                targets=strategy_targets(strategy,terminal,spot)
                strikes=map_unique_strikes(entry_snapshot.loc[entry_snapshot["timestamp"].dt.strftime("%H:%M:%S").eq("09:30:00")].copy(),targets)
                legs=build_strategy(strategy,strikes)
                entry_legs=[]
                entry_cash=0.0
                contracts=0
                for leg in legs:
                    match=entry_snapshot.loc[
                        entry_snapshot["timestamp"].dt.strftime("%H:%M:%S").eq("09:30:00")
                        & entry_snapshot["option_type"].eq(leg.option_type)
                        & np.isclose(entry_snapshot["strike"],leg.strike,atol=1e-9)
                    ]
                    if match.empty:raise ValueError(f"missing entry quote {strategy} {leg.option_type} {leg.strike}")
                    raw=float(match.iloc[0]["open"])
                    if index_name=="SENSEX":
                        px=raw+(0.5 if leg.qty>0 else -0.5)
                    else:
                        px=raw
                    if px<=0:raise ValueError("non-positive entry")
                    entry_cash-=int(leg.qty)*px
                    contracts+=abs(int(leg.qty))
                    entry_legs.append({"option_type":leg.option_type,"strike":float(leg.strike),"qty":int(leg.qty),"premium_points":px})
                # MC entry gate
                gross=np.full(len(terminal),entry_cash)
                for leg in entry_legs:
                    intrinsic=np.maximum(terminal-leg["strike"],0.0) if leg["option_type"]=="CE" else np.maximum(leg["strike"]-terminal,0.0)
                    gross+=int(leg["qty"])*intrinsic
                if index_name=="NIFTY":
                    entry_cost_points=cfg["entry_stress_points_per_contract"]*contracts
                    net=gross-entry_cost_points
                    entry_cost_inr=entry_cost_points*lot_sz
                else:
                    entry_cost_inr,entry_entry_only=sensex_entry_costs(entry_date,entry_legs,lot_sz,entry_cash,terminal)
                    net=gross-entry_cost_inr/lot_sz
                ev=float(np.mean(net)); pop=float(np.mean(net>0))
                q05=float(np.quantile(net,0.05));q01=float(np.quantile(net,0.01))
                es95=float(max(0,-np.mean(net[net<=q05])));es99=float(max(0,-np.mean(net[net<=q01])))
                risk=max(es95,es99)
                risk_budget_inr = 2000.0
                risk_points = max(es95, es99)
                risk_inr_per_lot = risk_points * lot_sz
                if index_name=="NIFTY":
                    lots = int(math.floor(risk_budget_inr / risk_inr_per_lot)) if risk_inr_per_lot > 0 else 0
                    eligible = ev > 0 and lots >= 1
                else:
                    lots = 1 if ev > 0 else 0
                    eligible = ev > 0
                evaluated.append({
                    "strategy":strategy,"eligible":eligible,"mc_ev_points_net":ev,"mc_pop":pop,
                    "es95_points":es95,"es99_points":es99,"risk_points":risk,
                    "strikes_json":json.dumps(strikes,sort_keys=True),
                    "legs_json":json.dumps(entry_legs,sort_keys=True),
                    "entry_cashflow":entry_cash,"contracts":contracts,
                    "entry_cost_inr":entry_cost_inr,"entry_only_cost_inr":(entry_entry_only if index_name=="SENSEX" else entry_cost_inr),"lot_size":lot_sz,
                    "risk_budget_inr":2000.0,"risk_inr_per_lot":risk_inr_per_lot,
                    "regime":regime["vol_regime"],"rv20_rank":regime["rv20_rank"],
                    "entry_date":str(entry_date.date()),"expiry":str(expiry.date()),"split":split,
                })
            except Exception as exc:
                evaluated.append({"strategy":strategy,"eligible":False,"error":str(exc)})
        if not evaluated:continue
        bat=[r for r in evaluated if r.get("strategy")=="Batman" and "error" not in r]
        adaptive_pool=[r for r in evaluated if r.get("strategy") in REGIMES[regime["vol_regime"]] and "error" not in r]
        adaptive_eligible=[r for r in adaptive_pool if r.get("eligible")]
        adaptive=sorted(adaptive_eligible,key=lambda r:(-float(r["mc_ev_points_net"]),str(r["strategy"])))[0] if adaptive_eligible else None
        chosen_map={"Batman":bat[0] if bat else None,"Adaptive":adaptive}
        # expiry spot
        exp_idx=idx.loc[idx["trading_day"].eq(expiry)]
        expiry_spot=float(exp_idx.sort_values("timestamp").iloc[-1]["close"]) if not exp_idx.empty else math.nan
        for strat,chosen in chosen_map.items():
            if chosen is None:
                continue
            try:
                entry_legs=json.loads(chosen["legs_json"])
                        baseline_cost = chosen.get("entry_only_cost_inr", chosen["entry_cost_inr"])
                baseline_points=expiry_settlement_points(index_name,expiry_spot,entry_legs,chosen["entry_cashflow"],baseline_cost,lot_sz,chosen["contracts"],entry_date)
                baseline_inr=baseline_points*lot_sz
                row_base={**chosen,"exit":"expiry_settlement","strategy_report":strat,"realized_pnl_inr":baseline_inr,"realized_pnl_points_per_unit":baseline_points}
                rows.append(row_base)
                if exit_time:
                    # Reprice only once the trade is already fixed by the entry gate.
                    exit_prices=price_at_timestamp(snapshot,expiry,entry_legs,exit_time,index_name)
                    exit_cash=-sum(int(l["qty"])*p for l,p in zip(entry_legs,exit_prices))
                    gross_points=chosen["entry_cashflow"]+exit_cash
                    if index_name=="NIFTY":
                        net_points=gross_points-chosen["entry_cost_inr"]/lot_sz-nse_cost_exit_points(chosen["contracts"])
                        exit_cost_inr=nse_cost_exit_points(chosen["contracts"])*lot_sz
                    else:
                        exit_cost_inr=sensex_exit_costs(expiry,entry_legs,exit_prices,lot_sz)
                        net_points=gross_points-chosen.get("entry_only_cost_inr",chosen["entry_cost_inr"])/lot_sz-exit_cost_inr/lot_sz
                    rr={**chosen,"exit":exit_time[:5],"strategy_report":strat,"exit_prices_json":json.dumps(exit_prices),"realized_pnl_points_per_unit":net_points,"realized_pnl_inr":net_points*lot_sz,"exit_cost_inr":exit_cost_inr}
                    rows.append(rr)
                    if "baseline_points" not in chosen:
                        pass
            except Exception as exc:
                rows.append({**chosen,"exit":exit_time[:5] if exit_time else "expiry_settlement","strategy_report":strat,"status":"EXIT_UNAVAILABLE","error":str(exc)})
    trades=pd.DataFrame(rows)
    out_dir.mkdir(parents=True,exist_ok=True)
    trades.to_csv(out_dir/f"{index_name}_{exit_mode.replace(':','')}.csv",index=False)
    if trades.empty:
        return {"index":index_name,"exit":exit_mode,"trades":0}
    summary=[]
    for strat in ("Batman","Adaptive"):
        g=trades.loc[(trades["strategy_report"]==strat)&(trades["exit"]==(exit_mode[:5] if exit_mode!="expiry_settlement" else "expiry_settlement"))&(trades.get("status","").ne("EXIT_UNAVAILABLE"))].copy()
        s=summarize(g)
        s.update({"index":index_name,"strategy":strat,"exit":exit_mode,"first_entry":g["entry_date"].min() if not g.empty else None,"last_entry":g["entry_date"].max() if not g.empty else None})
        summary.append(s)
    pd.DataFrame(summary).to_csv(out_dir/f"{index_name}_{exit_mode.replace(':','')}_SUMMARY.csv",index=False)
    # Combined OOS bootstrap on validation + holdout only.
    for strat in ("Batman","Adaptive"):
        g=trades.loc[(trades["strategy_report"]==strat)&(trades["split"].isin(["validation","holdout"]))&(trades["exit"]==(exit_mode[:5] if exit_mode!="expiry_settlement" else "expiry_settlement"))&(trades.get("status","").ne("EXIT_UNAVAILABLE"))]
        if not g.empty:
            bs=block_bootstrap(pd.to_numeric(g["realized_pnl_inr"],errors="coerce").dropna().to_numpy(float))
            (out_dir/f"{index_name}_{strat}_{exit_mode.replace(':','')}_BOOTSTRAP.json").write_text(json.dumps(bs,indent=2),encoding="utf-8")
    return {"index":index_name,"exit":exit_mode,"summaries":summary}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--paths",type=int,default=5000)
    ap.add_argument("--seed-base",type=int,default=20260920)
    ap.add_argument("--out-dir",default="reports/expiry_exit")
    args=ap.parse_args()
    root=ROOT/args.out_dir
    all_summaries=[]
    for index_name in ("NIFTY","SENSEX"):
        for exit_mode in ("expiry_settlement","15:00:00","15:10:00"):
            all_summaries.append(run(index_name,exit_mode,root/exit_mode.replace(":",""),args.paths,args.seed_base))
    (root/"MASTER_SUMMARY.json").write_text(json.dumps(all_summaries,indent=2,default=str),encoding="utf-8")
    rows=[]
    for p in sorted(root.glob("*/NIFTY_*_SUMMARY.csv"))+sorted(root.glob("*/SENSEX_*_SUMMARY.csv")):
        try: rows.append(pd.read_csv(p))
        except Exception: pass
    if rows: pd.concat(rows,ignore_index=True).to_csv(root/"MASTER_SUMMARY.csv",index=False)
    print(json.dumps(all_summaries,indent=2,default=str))

if __name__=="__main__":
    main()
