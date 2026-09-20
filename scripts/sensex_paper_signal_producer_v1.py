from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from scripts.sensex_backtest_v1 import (
    CANDIDATES_BY_REGIME,
    compute_regime,
    cost_schedule,
    map_unique_strikes,
    mc_terminal,
    strategy_targets,
    transaction_costs,
)
from src.nifty_mc.strategy_catalog import build_strategy

IST = timezone(timedelta(hours=5, minutes=30))
LOT_SIZE = 20
CAPITAL_INR = 100_000.0
RISK_BUDGET_INR = CAPITAL_INR * 0.02
SLIPPAGE_POINTS = 0.50
MC_PATHS = 5000
LOOKBACK = 756
RANK_LOOKBACK = 252
BSE_BASE = "https://api.bseindia.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/134 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}
INDEX_HISTORY_URL = f"{BSE_BASE}/BseIndiaAPI/api/ProduceCSVForDate/w"
LIVE_SENSEX_URL = f"{BSE_BASE}/RealTimeBseIndiaAPI/api/GetSensexData/w"
OPTION_CHAIN_TEMPLATES = [
    f"{BSE_BASE}/BseIndiaAPI/api/DerivOptionChain/w",
    f"{BSE_BASE}/BseIndiaAPI/api/DerivativesChain/w",
]
DEFAULT_SEED = 20260920

def now_ist() -> datetime:
    return datetime.now(IST)

def is_trading_weekday(d: datetime) -> bool:
    return d.weekday() < 5

def third_future_weekday(entry_date: pd.Timestamp) -> pd.Timestamp:
    d = entry_date.date()
    n = 0
    while n < 3:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return pd.Timestamp(d)

def request_json(url: str, params: dict[str, Any] | None = None) -> Any:
    r = requests.get(url, params=params or {}, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.json()

def fetch_index_history(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    params = {
        "strIndex": "SENSEX",
        "dtFromDate": start.strftime("%d/%m/%Y"),
        "dtToDate": end.strftime("%d/%m/%Y"),
        "period": "D",
    }
    r = requests.get(INDEX_HISTORY_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    text = r.text.strip()
    rows: list[dict[str, Any]]
    try:
        payload = r.json()
        if isinstance(payload, dict):
            data = payload.get("Data") or payload.get("data") or payload.get("Table") or []
            if isinstance(data, str):
                text = data
            elif isinstance(data, list):
                rows = data
                return normalize_history(pd.DataFrame(rows))
    except ValueError:
        pass
    if "<" in text[:100]:
        raise ValueError("BSE index-history endpoint returned HTML instead of data")
    df = pd.read_csv(io.StringIO(text))
    return normalize_history(df)

def normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = next((cols[k] for k in ("date", "dt", "trading date") if k in cols), None)
    close_col = next((cols[k] for k in ("close", "close price", "closing price") if k in cols), None)
    if date_col is None or close_col is None:
        raise ValueError(f"unrecognized BSE SENSEX history schema: {list(df.columns)}")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True).dt.normalize(),
        "close": pd.to_numeric(df[close_col], errors="coerce"),
    }).dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)
    return out

def fetch_live_sensex() -> dict[str, Any]:
    for url in (LIVE_SENSEX_URL, f"{BSE_BASE}/BseIndiaAPI/api/GetSensexDataN/w?code=84"):
        try:
            data = request_json(url)
            if isinstance(data, dict):
                if "Data" in data and isinstance(data["Data"], list) and data["Data"]:
                    data = data["Data"][0]
                return data
        except Exception:
            continue
    raise RuntimeError("BSE live SENSEX endpoint unavailable")

def recursive_records(obj: Any, inherited: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    inherited = dict(inherited or {})
    out: list[dict[str, Any]] = []
    if isinstance(obj, list):
        for item in obj:
            out.extend(recursive_records(item, inherited))
        return out
    if not isinstance(obj, dict):
        return out
    merged = dict(inherited)
    for k, v in obj.items():
        lk = str(k).lower()
        if lk in {"strike_price","strikeprice","strike","strikepricevalue"}:
            merged["strike"] = v
        elif lk in {"expiry_date","expirydate","expiry"}:
            merged["expiry"] = v
        elif lk in {"option_type","optiontype","putorcall"}:
            merged["option_type"] = v
    keys = {str(k).lower() for k in obj}
    if any("strike" in k for k in keys) and (
        any("bid" in k for k in keys)
        or any("offer" in k for k in keys)
        or any("ask" in k for k in keys)
        or "ce" in keys or "pe" in keys
    ):
        row = dict(merged)
        row.update({str(k): v for k, v in obj.items() if not isinstance(v, (dict, list))})
        if isinstance(obj.get("CE"), dict):
            ce = dict(merged); ce.update({str(k): v for k, v in obj["CE"].items()}); ce["option_type"] = "CE"; out.append(ce)
        if isinstance(obj.get("PE"), dict):
            pe = dict(merged); pe.update({str(k): v for k, v in obj["PE"].items()}); pe["option_type"] = "PE"; out.append(pe)
        if not (isinstance(obj.get("CE"), dict) or isinstance(obj.get("PE"), dict)):
            out.append(row)
    for k, v in obj.items():
        if isinstance(v, (dict, list)):
            child = dict(merged)
            lk = str(k).lower()
            if lk in {"ce", "call"}:
                child["option_type"] = "CE"
            elif lk in {"pe", "put"}:
                child["option_type"] = "PE"
            out.extend(recursive_records(v, child))
    return out

def canonical_option_rows(payload: Any) -> pd.DataFrame:
    rows = recursive_records(payload)
    if not rows:
        raise ValueError("BSE option-chain response contained no option records")
    df = pd.DataFrame(rows)
    lowmap = {c.lower().replace(" ", "").replace("_",""): c for c in df.columns}
    def pick(*names: str) -> str | None:
        for n in names:
            if n.lower().replace(" ","").replace("_","") in lowmap:
                return lowmap[n.lower().replace(" ","").replace("_","")]
        return None
    strike_col = pick("strike","strikeprice","strike_price")
    exp_col = pick("expiry","expirydate","expiry_date")
    typ_col = pick("option_type","optiontype","putorcall")
    bid_col = pick("bidprice","bid_price","bid","b_idprice")
    ask_col = pick("offerprice","offer_price","askprice","ask_price","ask")
    if not all([strike_col, exp_col, typ_col, bid_col, ask_col]):
        raise ValueError(f"BSE option-chain schema missing strike/expiry/type/bid/ask: {list(df.columns)}")
    out = pd.DataFrame({
        "strike": pd.to_numeric(df[strike_col], errors="coerce"),
        "expiry": pd.to_datetime(df[exp_col], errors="coerce", dayfirst=True).dt.normalize(),
        "option_type": df[typ_col].astype(str).str.upper().replace({"CALL":"CE","PUT":"PE","1":"CE","0":"PE"}),
        "bid": pd.to_numeric(df[bid_col], errors="coerce"),
        "ask": pd.to_numeric(df[ask_col], errors="coerce"),
    })
    out = out.loc[out["option_type"].isin(["CE","PE"])].dropna(subset=["strike","expiry"]).copy()
    out = out.loc[(out["bid"] > 0) & (out["ask"] > 0) & (out["ask"] >= out["bid"])]
    out = out.drop_duplicates(["expiry","option_type","strike"]).sort_values(["expiry","strike","option_type"])
    if out.empty:
        raise ValueError("BSE option-chain contained no executable bid/ask quotes")
    return out.reset_index(drop=True)

def fetch_option_chain(expiry: pd.Timestamp) -> pd.DataFrame:
    explicit = os.getenv("BSE_OPTION_CHAIN_URL")
    urls = [explicit] if explicit else OPTION_CHAIN_TEMPLATES
    params_variants = [
        {"flag":"0","expirydate":expiry.strftime("%d-%b-%Y").upper(),"scripcode":"84"},
        {"flag":"0","expiryDate":expiry.strftime("%d-%b-%Y").upper(),"scripcode":"84"},
        {"flag":"0","expirydate":expiry.strftime("%d-%b-%Y").upper(),"scripcode":"16"},
    ]
    errors = []
    for url in urls:
        for params in params_variants:
            try:
                payload = request_json(url, params=params)
                df = canonical_option_rows(payload)
                scoped = df.loc[df["expiry"].eq(expiry)].copy()
                if not scoped.empty:
                    return scoped
            except Exception as exc:
                errors.append(f"{url} {params}: {exc}")
    raise RuntimeError("no executable BSE option-chain snapshot found; " + " | ".join(errors[-4:]))

def quote_for_leg(chain: pd.DataFrame, option_type: str, strike: float, side: str) -> float:
    x = chain.loc[
        chain["option_type"].eq(option_type)
        & np.isclose(chain["strike"].to_numpy(float), float(strike), atol=1e-9)
    ]
    if x.empty:
        raise ValueError(f"missing live quote {option_type} {strike}")
    row = x.iloc[0]
    raw = float(row["ask"] if side == "BUY" else row["bid"])
    if raw <= 0:
        raise ValueError(f"non-positive live executable quote {option_type} {strike}")
    px = raw + SLIPPAGE_POINTS if side == "BUY" else raw - SLIPPAGE_POINTS
    if px <= 0:
        raise ValueError(f"quote becomes non-positive after slippage {option_type} {strike}")
    return px

def live_strategy_eval(strategy: str, terminal: np.ndarray, spot: float, chain: pd.DataFrame, expiry: pd.Timestamp, entry_date: pd.Timestamp, seed: int) -> dict[str, Any]:
    targets = strategy_targets(strategy, terminal, spot)
    strikes = map_unique_strikes(chain.rename(columns={"bid":"open","ask":"close"}), targets)
    legs = build_strategy(strategy, strikes)
    priced = []
    entry_cashflow = 0.0
    contracts = 0
    for leg in legs:
        side = "BUY" if leg.qty > 0 else "SELL"
        px = quote_for_leg(chain, leg.option_type, float(leg.strike), side)
        entry_cashflow -= float(leg.qty) * px
        contracts += abs(int(leg.qty))
        priced.append({
            "side": side, "option_type": leg.option_type, "strike": float(leg.strike),
            "qty": int(leg.qty), "quantity_per_lot": abs(int(leg.qty)),
            "premium_points": px, "bid": float(chain.loc[(chain.option_type==leg.option_type)&np.isclose(chain.strike,leg.strike), "bid"].iloc[0]),
            "ask": float(chain.loc[(chain.option_type==leg.option_type)&np.isclose(chain.strike,leg.strike), "ask"].iloc[0]),
            "expiry": str(expiry.date()),
        })
    gross = np.zeros_like(terminal, dtype=float) + entry_cashflow
    for leg in priced:
        intrinsic = np.maximum(terminal-leg["strike"],0) if leg["option_type"]=="CE" else np.maximum(leg["strike"]-terminal,0)
        gross += float(leg["qty"]) * intrinsic
    expected_cost_inr, entry_cost_inr = transaction_costs(entry_date, priced, LOT_SIZE, entry_cashflow, terminal)
    net = gross - expected_cost_inr / LOT_SIZE
    q05 = float(np.quantile(net,0.05)); q01 = float(np.quantile(net,0.01))
    es95 = float(max(0.0,-np.mean(net[net<=q05]))); es99 = float(max(0.0,-np.mean(net[net<=q01])))
    risk_points = max(es95,es99)
    ev = float(np.mean(net))
    eligible = ev > 0
    return {
        "strategy": strategy, "strikes_json": json.dumps(strikes, sort_keys=True),
        "legs_json": json.dumps(priced, sort_keys=True),
        "entry_cashflow_points_per_unit": float(entry_cashflow),
        "mc_ev_points_net": ev, "mc_pop": float(np.mean(net>0)),
        "es95_points": es95, "es99_points": es99, "risk_points_per_lot": risk_points,
        "recommended_lots": 1 if eligible else 0,
        "contract_count": contracts, "eligible": eligible,
        "entry_cost_inr_expected": float(expected_cost_inr),
        "entry_cost_inr_entry_only": float(entry_cost_inr),
        "mc_seed": int(seed),
    }

def signal_row(strategy: str, evaluation: dict[str,Any], decision_date: pd.Timestamp, expiry: pd.Timestamp, regime: dict[str,Any], spot: float, timestamp: datetime, model_cutoff: pd.Timestamp) -> dict[str,Any]:
    signal = "ENTER" if evaluation["eligible"] else "NO_TRADE"
    return {
        "signal_id": f"{decision_date.date()}|{expiry.date()}|{strategy}",
        "decision_date": str(decision_date.date()), "expiry": str(expiry.date()),
        "strategy": strategy, "signal": signal, "regime": regime["vol_regime"],
        "spot": spot, "lot_size": LOT_SIZE, "lots": evaluation["recommended_lots"],
        "risk_budget_inr": RISK_BUDGET_INR, "mc_ev_points_net": evaluation["mc_ev_points_net"],
        "mc_pop": evaluation["mc_pop"], "es95_points": evaluation["es95_points"],
        "es99_points": evaluation["es99_points"], "entry_slippage_points": SLIPPAGE_POINTS,
        "entry_cost_inr_expected": evaluation["entry_cost_inr_expected"],
        "entry_cashflow_points_per_unit": evaluation["entry_cashflow_points_per_unit"],
        "legs_json": evaluation["legs_json"], "entry_timestamp_ist": timestamp.isoformat(),
        "model_data_cutoff": str(model_cutoff.date()), "quote_retrieved_at_ist": timestamp.isoformat(),
        "status": "OPEN" if signal == "ENTER" else "NO_TRADE",
        "notes": "Prospective S7 paper trade; one-lot transfer-edge mode; no broker order.",
    }

def append_unique(path: Path, row: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()
    if not existing.empty and row["signal_id"] in existing.get("signal_id", pd.Series(dtype=str)).astype(str).tolist():
        return
    pd.DataFrame([row]).to_csv(path, mode="a", header=not path.exists() or path.stat().st_size==0, index=False)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["Batman","Adaptive"], required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()

    ts = now_ist()
    if not is_trading_weekday(ts):
        payload={"status":"NO_TRADE","reason":"non_trading_weekday","timestamp_ist":ts.isoformat()}
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(payload,indent=2),encoding="utf-8")
        return

    decision_date = pd.Timestamp(ts.date()).normalize()
    history = fetch_index_history(decision_date - pd.Timedelta(days=2200), decision_date - pd.Timedelta(days=1))
    if len(history) < LOOKBACK + 1:
        raise RuntimeError(f"insufficient SENSEX history for prospective MC: {len(history)} rows")
    cutoff = pd.Timestamp(history["date"].max())
    returns = np.log(history["close"]).diff().dropna().to_numpy(float)
    live = fetch_live_sensex()
    spot = next((float(live[k]) for k in ("LTP","CurrValue","ltp","Currvalue") if k in live and str(live[k]) not in {"","None"}), None)
    if spot is None or not np.isfinite(spot):
        raise RuntimeError(f"could not parse live SENSEX spot from keys: {list(live)}")
    expiry = third_future_weekday(decision_date)
    chain = fetch_option_chain(expiry)
    terminal = mc_terminal(returns, spot, 3, MC_PATHS, args.seed)
    regime = compute_regime(history, cutoff, RANK_LOOKBACK)

    candidates = []
    for strategy in CANDIDATES_BY_REGIME[regime["vol_regime"]]:
        try:
            candidates.append(live_strategy_eval(strategy, terminal, spot, chain, expiry, decision_date, args.seed))
        except Exception as exc:
            candidates.append({"strategy":strategy,"eligible":False,"error":str(exc)})

    if args.strategy == "Batman":
        chosen = live_strategy_eval("Batman", terminal, spot, chain, expiry, decision_date, args.seed)
    else:
        eligible = [x for x in candidates if x.get("eligible")]
        if not eligible:
            chosen = {"strategy":"Adaptive","eligible":False,"error":"no eligible candidate in frozen regime candidate set","candidate_screen":candidates}
        else:
            chosen = sorted(eligible,key=lambda x:(-float(x["mc_ev_points_net"]),x["strategy"]))[0]
            chosen["strategy"]="Adaptive"
            chosen["selected_candidate"]=chosen.get("strategy")

    row = signal_row(args.strategy, chosen, decision_date, expiry, regime, spot, ts, cutoff)
    row["candidate_screen_json"] = json.dumps(candidates, sort_keys=True, default=str)
    append_unique(Path(args.ledger), row)
    payload = {"status": row["status"], "signal": row, "candidate_screen": candidates, "retrieval": {"timestamp_ist":ts.isoformat(),"model_cutoff":str(cutoff.date()),"expiry":str(expiry.date())}}
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_json).write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    print(json.dumps(payload,indent=2,default=str))

if __name__ == "__main__":
    main()
