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

def fetch_nifty_history(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Fetch past-only NIFTY closes from NSE."""
    from curl_cffi import requests as curl_requests
    sess = curl_requests.Session(impersonate="chrome")
    sess.headers.update({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/136.0 Safari/537.36", "Accept":"application/json,text/plain,*/*", "Accept-Language":"en-IN,en;q=0.9", "Referer":"https://www.nseindia.com/"})
    sess.get("https://www.nseindia.com/option-chain", timeout=30)
    chunks=[]; cur=pd.Timestamp(start).normalize(); end=pd.Timestamp(end).normalize()
    while cur<=end:
        ce=min(cur+pd.Timedelta(days=349),end)
        rr=sess.get("https://www.nseindia.com/api/historical/indicesHistory", params={"indexType":"NIFTY 50","from":cur.strftime("%d-%m-%Y"),"to":ce.strftime("%d-%m-%Y")}, timeout=30)
        rr.raise_for_status(); payload=rr.json()
        rows=(payload.get("data") or {}).get("indexCloseOnlineRecords") or []
        if rows:
            df=pd.DataFrame(rows); dc="EOD_TIMESTAMP" if "EOD_TIMESTAMP" in df.columns else "TIMESTAMP"; cc="EOD_CLOSE_INDEX_VAL" if "EOD_CLOSE_INDEX_VAL" in df.columns else "CLOSE"
            if dc in df.columns and cc in df.columns:
                chunks.append(pd.DataFrame({"date":pd.to_datetime(df[dc],errors="coerce").dt.normalize(),"close":pd.to_numeric(df[cc],errors="coerce")}).dropna())
        cur=ce+pd.Timedelta(days=1)
    if not chunks: raise RuntimeError("NSE returned no NIFTY history")
    return pd.concat(chunks,ignore_index=True).drop_duplicates("date").sort_values("date").reset_index(drop=True)

def fetch_sensex_history(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Fetch past-only SENSEX closes from BSE."""
    import io
    rr=requests.get("https://api.bseindia.com/BseIndiaAPI/api/ProduceCSVForDate/w", params={"strIndex":"SENSEX","dtFromDate":start.strftime("%d/%m/%Y"),"dtToDate":end.strftime("%d/%m/%Y"),"period":"D"}, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.bseindia.com/"}, timeout=30)
    rr.raise_for_status()
    try: payload=rr.json()
    except Exception: payload=None
    df=None
    if isinstance(payload,dict):
        data=payload.get("Data") or payload.get("data") or payload.get("Table")
        if isinstance(data,list): df=pd.DataFrame(data)
        elif isinstance(data,str): df=pd.read_csv(io.StringIO(data))
    if df is None:
        raw=rr.text.strip()
        if not raw or "<" in raw[:100]: raise RuntimeError("BSE SENSEX history endpoint returned non-tabular data")
        df=pd.read_csv(io.StringIO(raw))
    lookup={str(c).strip().lower():c for c in df.columns}
    dc=next((lookup[k] for k in ("date","dt","trading date") if k in lookup),None)
    cc=next((lookup[k] for k in ("close","close price","closing price") if k in lookup),None)
    if not dc or not cc: raise RuntimeError(f"unrecognized BSE SENSEX history schema: {list(df.columns)}")
    out=pd.DataFrame({"date":pd.to_datetime(df[dc],errors="coerce",dayfirst=True).dt.normalize(),"close":pd.to_numeric(df[cc],errors="coerce")}).dropna()
    return out.drop_duplicates("date").sort_values("date").reset_index(drop=True)

def history(index: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return fetch_nifty_history(start,end) if index=="NIFTY" else fetch_sensex_history(start,end)

def model(spot: float, hist: pd.DataFrame, decision: pd.Timestamp, expiry: pd.Timestamp, seed: int) -> dict:
    prior=hist.loc[hist.date < decision].copy()
    cutoff=pd.Timestamp(prior.date.max()).normalize()
    close=prior.close.astype(float)
    logret=np.log(close).diff().dropna().to_numpy(float)
    if len(logret)<LOOKBACK:
        raise RuntimeError("insufficient past-only returns")
    latest=logret[-LOOKBACK:]
    # Fixed frozen 3-session horizon used by the paper protocol.
    future_days=pd.bdate_range(decision+pd.Timedelta(days=1), periods=3)
    horizon_sessions=len(pd.bdate_range(decision+pd.Timedelta(days=1), expiry))
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
    index="NIFTY" if args.strategy.startswith("NIFTY") else "SENSEX"
    expiry=decision + pd.Timedelta(days=1 if index=="NIFTY" else 3)
    symbol="^NSEI" if index=="NIFTY" else "^BSESN"
    hist=history(index,decision-pd.Timedelta(days=365*5),decision)
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
        "entry_timing_rule":"3 future trading sessions before target expiry",
        "timing_gate":"PASS" if t["horizon_sessions"]==3 else "NOT_ENTRY_DAY",
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
    out.write_text(json.dumps(base,indent=2)+"\\n",encoding="utf-8")
    print(json.dumps(base,indent=2))

if __name__=="__main__":
    main()
