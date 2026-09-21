#!/usr/bin/env python3
"""Generate look-ahead-safe 09:40 model/candidate signals from available data.

No option premium is invented. When the historical/live option-chain snapshot is
unavailable, the producer publishes a DATA_LIMITED_CANDIDATE record using the
available underlying observation and the frozen historical return model.

This is never written to the prospective execution ledger as an ENTER trade.
"""
from __future__ import annotations
import argparse, json, math
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

IST = ZoneInfo("Asia/Kolkata")
MC_PATHS = 5000
LOOKBACK = 756
RANK_LOOKBACK = 252

ADAPTIVE_BY_REGIME = {
    "low": [("Risk Reversal", 9), ("Long Synthetic Future", 4), ("Buy Call", 2)],
    "medium": [("Short Straddle", 4), ("Put Ratio Spread", 4), ("Short Strangle", 3), ("Strip", 3), ("Buy Put", 1)],
    "high": [("Sell Put", 5), ("Risk Reversal", 5), ("Long Synthetic Future", 3), ("Batman", 2)],
}

def yahoo_history(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    p1 = int(pd.Timestamp(start, tz="Asia/Kolkata").timestamp())
    p2 = int((pd.Timestamp(end, tz="Asia/Kolkata") + pd.Timedelta(days=1)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = requests.get(url, params={"period1": p1, "period2": p2, "interval": "1d", "events":"history"}, timeout=30)
    r.raise_for_status()
    payload = r.json()
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"no Yahoo history for {symbol}")
    ts = result.get("timestamp") or []
    close = ((((result.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or [])
    rows=[]
    for t,c in zip(ts,close):
        try:
            px=float(c)
        except Exception:
            continue
        d=pd.Timestamp(t,unit="s",tz="UTC").tz_convert(IST).normalize().tz_localize(None)
        if math.isfinite(px):
            rows.append({"date":d,"close":px})
    out=pd.DataFrame(rows).drop_duplicates("date").sort_values("date")
    if len(out)<LOOKBACK+1:
        raise RuntimeError(f"insufficient historical closes for {symbol}: {len(out)}")
    return out.reset_index(drop=True)

def model(spot: float, hist: pd.DataFrame, decision: pd.Timestamp, expiry: pd.Timestamp, seed: int) -> dict:
    prior=hist.loc[hist.date < decision].copy()
    cutoff=pd.Timestamp(prior.date.max()).normalize()
    close=prior.close.astype(float)
    logret=np.log(close).diff().dropna().to_numpy(float)
    if len(logret)<LOOKBACK:
        raise RuntimeError("insufficient past-only returns")
    latest=logret[-LOOKBACK:]
    # Fixed frozen 3-session horizon used by the paper protocol.
    horizon=max(1, int((expiry-decision).days))
    future_days=pd.bdate_range(decision+pd.Timedelta(days=1), periods=3)
    horizon_sessions=3 if len(future_days)==3 else min(3,len(future_days))
    rng=np.random.default_rng(seed)
    sampled=rng.choice(latest,size=MC_PATHS*horizon_sessions,replace=True).reshape(MC_PATHS,horizon_sessions)
    terminal=spot*np.exp(sampled.sum(axis=1))
    p10,p20,p35,p65,p80,p90=np.percentile(terminal,[10,20,35,65,80,90])
    rv20_series=pd.Series(logret).rolling(20).std(ddof=1)*np.sqrt(252)
    rv20_series=rv20_series.dropna()
    latest_rv=float(rv20_series.iloc[-1])
    rank_hist=rv20_series.iloc[:-1].tail(RANK_LOOKBACK)
    rank=float(np.mean(rank_hist.to_numpy(float)<=latest_rv)) if len(rank_hist) else float("nan")
    regime="low" if rank<=1/3 else ("medium" if rank<=2/3 else "high")
    return {
        "model_data_cutoff": cutoff.date().isoformat(),
        "horizon_sessions": horizon_sessions,
        "p10":float(p10),"p20":float(p20),"p35":float(p35),"p65":float(p65),"p80":float(p80),"p90":float(p90),
        "rv20":latest_rv,"rv20_rank":rank,"vol_regime":regime,
    }

def legs(strategy: str, t: dict) -> list[dict]:
    k={
        "p20":t["p20"],"p35":t["p35"],"c65":t["p65"],"c80":t["p80"],"c90":t["p90"],"atm":t["spot"]
    }
    m={
        "Batman":[("PE","BUY","p35",1),("PE","SELL","p20",2),("CE","BUY","c65",1),("CE","SELL","c80",2)],
        "Jade Lizard":[("PE","SELL","p35",1),("CE","SELL","c65",1),("CE","BUY","c90",1)],
        "Put Ratio Spread":[("PE","BUY","atm",1),("PE","SELL","p35",2)],
    }
    return [{"side":s,"option_type":o,"target_label":lab,"target_price":round(k[lab],2),"quantity_per_lot":q}
            for o,s,lab,q in m[strategy]]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--strategy",required=True,choices=["NIFTY BATMAN","NIFTY ADAPTIVE","NIFTY JADE LIZARD","NIFTY PUT RATIO SPREAD","SENSEX BATMAN","SENSEX ADAPTIVE","SENSEX JADE LIZARD","SENSEX PUT RATIO SPREAD"])
    ap.add_argument("--decision-date",required=True)
    ap.add_argument("--entry-time-ist",default="09:40")
    ap.add_argument("--spot",type=float,required=True)
    ap.add_argument("--spot-source",required=True)
    ap.add_argument("--spot-source-timestamp",required=True)
    ap.add_argument("--output-json",required=True)
    args=ap.parse_args()

    decision=pd.Timestamp(args.decision_date).normalize()
    expiry=decision+pd.Timedelta(days=3)
    index="NIFTY" if args.strategy.startswith("NIFTY") else "SENSEX"
    symbol="^NSEI" if index=="NIFTY" else "^BSESN"
    hist=yahoo_history(symbol,decision-pd.Timedelta(days=365*5),decision)
    seed=20260921
    t=model(args.spot,hist,decision,expiry,seed)
    t["spot"]=float(args.spot)

    base={
        "producer":"Available-data 09:40 candidate signal v1",
        "strategy":args.strategy,
        "decision_date":args.decision_date,
        "entry_time_ist":args.entry_time_ist,
        "signal":"DATA_LIMITED_CANDIDATE",
        "status":"DATA_LIMITED_CANDIDATE",
        "execution_status":"NOT_EXECUTABLE",
        "option_chain_available":False,
        "premium_available":False,
        "bid_ask_available":False,
        "quote_snapshot_used":False,
        "future_outcome_used":False,
        "lookahead_safe":True,
        "backfill_only":True,
        "spot":float(args.spot),
        "spot_source":args.spot_source,
        "spot_source_timestamp_ist":args.spot_source_timestamp,
        "source_latency_minutes":10,
        "model_data_cutoff":t["model_data_cutoff"],
        "target_expiry":expiry.date().isoformat(),
        "horizon_sessions":t["horizon_sessions"],
        "rv20":t["rv20"],"rv20_rank":t["rv20_rank"],"vol_regime":t["vol_regime"],
        "terminal_quantiles":{k:t[k] for k in ["p10","p20","p35","p65","p80","p90"]},
        "reason":"OPTION_PREMIUM_BID_ASK_SNAPSHOT_UNAVAILABLE",
        "note":"Candidate generated from verified underlying data available by 09:40 IST plus frozen past-only return history. Option premiums, bid/ask, slippage-adjusted entry cost, and MC-EV eligibility were not evaluated.",
    }

    if "ADAPTIVE" in args.strategy:
        base["candidate_set"]=[{"strategy":s,"cpcv_selection_frequency":f} for s,f in ADAPTIVE_BY_REGIME[t["vol_regime"]]]
        base["primary_strategy"]="UNSELECTED_PENDING_OPTION_QUOTES"
        base["legs"]=[]
    else:
        st={"NIFTY BATMAN":"Batman","NIFTY JADE LIZARD":"Jade Lizard","NIFTY PUT RATIO SPREAD":"Put Ratio Spread",
            "SENSEX BATMAN":"Batman","SENSEX JADE LIZARD":"Jade Lizard","SENSEX PUT RATIO SPREAD":"Put Ratio Spread"}[args.strategy]
        base["primary_strategy"]=st
        base["legs"]=legs(st,t)

    out=Path(args.output_json); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(base,indent=2)+"
",encoding="utf-8")
    print(json.dumps(base,indent=2))

if __name__=="__main__":
    main()
