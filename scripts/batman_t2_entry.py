#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOL_RE = re.compile(r"^NIFTY(\d{2})([A-Z]{3})(\d{2})(\d+)(CE|PE)$", re.I)
MONTHS = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,"JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}

SLIPPAGE_POINTS = 2.0
BROKERAGES = (10.0, 20.0, 30.0)

def parse_symbol(value: str):
    m = SYMBOL_RE.match(str(value).strip().upper())
    if not m:
        return None
    dd, mmm, yy, strike, typ = m.groups()
    try:
        exp = date(2000 + int(yy), MONTHS[mmm], int(dd))
        return exp, float(strike), typ.upper()
    except Exception:
        return None

def lot_size(expiry: pd.Timestamp) -> int:
    d = expiry.date()
    if d <= date(2021, 6, 30):
        return 75
    if d <= date(2024, 4, 25):
        return 50
    if d <= date(2024, 11, 19):
        return 25
    return 75

def stt_rate(execution_date: pd.Timestamp) -> float:
    return 0.001 if execution_date.date() >= date(2024, 10, 1) else 0.000625

def deterministic_seed(base: int, key: str) -> int:
    digest = hashlib.sha256(f"{base}|{key}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)

def mc_terminal(spot: float, returns: np.ndarray, horizon: int, paths: int, seed: int) -> np.ndarray:
    r = returns[np.isfinite(returns)]
    if len(r) < 60:
        raise ValueError("Insufficient completed daily returns for Monte Carlo.")
    h = max(1, int(horizon))
    rng = np.random.default_rng(seed)
    sampled = rng.choice(r, size=paths * h, replace=True).reshape(paths, h)
    return spot * np.exp(sampled.sum(axis=1))

def unique_strikes(available: np.ndarray, targets: dict[str, float]) -> dict[str, float] | None:
    s = np.sort(np.unique(np.asarray(available, dtype=float)))
    if len(s) < 4:
        return None
    used = set()
    out = {}
    for label, target in sorted(targets.items(), key=lambda kv: kv[1]):
        order = np.argsort(np.abs(s - target))
        pick = None
        for idx in order:
            candidate = float(s[idx])
            if candidate not in used:
                pick = candidate
                break
        if pick is None:
            return None
        out[label] = pick
        used.add(pick)
    return out

def batman_legs(strikes: dict[str, float]):
    return [
        ("PE", strikes["p35"], +1, "p35"),
        ("PE", strikes["p20"], -2, "p20"),
        ("CE", strikes["c65"], +1, "c65"),
        ("CE", strikes["c80"], -2, "c80"),
    ]

def expiry_from_filename(name: str):
    m = re.search(r"nifty_options_(\d{2})_(\d{2})_(\d{4})\.csv$", name, re.I)
    if not m:
        return None
    dd, mm, yyyy = map(int, m.groups())
    return date(yyyy, mm, dd)

def prepare_maps(raw_root: Path, ayush_zip: Path):
    expiry_map_path = raw_root / "t2_ayush_expiry_calendar.csv"
    file_map_path = raw_root / "t2_ayush_daily_file_map.csv"
    if expiry_map_path.exists() and file_map_path.exists():
        return pd.read_csv(expiry_map_path, parse_dates=["trade_date","expiry"]), pd.read_csv(file_map_path, parse_dates=["trade_date"])

    expiries = defaultdict(set)
    file_rows = []
    with zipfile.ZipFile(ayush_zip) as zf:
        members = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".csv")
            and n.lower().startswith("nifty_data/nifty_options/")
        )
        total = len(members)
        for i, member in enumerate(members, 1):
            td = expiry_from_filename(member)
            if td is None:
                continue
            file_rows.append({"trade_date": td.isoformat(), "member": member})
            with zf.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                seen = set()
                for row in reader:
                    parsed = parse_symbol(row.get("symbol", ""))
                    if parsed is None:
                        continue
                    exp, _strike, _typ = parsed
                    if exp >= td and exp not in seen:
                        expiries[td].add(exp)
                        seen.add(exp)
            if i % 250 == 0:
                print(f"T2 expiry scan {i}/{total}")

    rows = [{"trade_date": td.isoformat(), "expiry": exp.isoformat()}
            for td, exps in sorted(expiries.items()) for exp in sorted(exps)]
    cal = pd.DataFrame(rows).drop_duplicates()
    fmap = pd.DataFrame(file_rows).drop_duplicates().sort_values("trade_date")
    cal.to_csv(expiry_map_path, index=False)
    fmap.to_csv(file_map_path, index=False)
    return cal.assign(trade_date=pd.to_datetime(cal.trade_date), expiry=pd.to_datetime(cal.expiry)), fmap.assign(trade_date=pd.to_datetime(fmap.trade_date))

def prepare_spot_and_daily(raw_root: Path, ayush_zip: Path, long_index_zip: Path):
    daily_path = raw_root / "t2_nifty_daily.csv"
    spot0930_path = raw_root / "t2_nifty_spot_0930.csv"
    if daily_path.exists() and spot0930_path.exists():
        return pd.read_csv(daily_path, parse_dates=["date"]), pd.read_csv(spot0930_path, parse_dates=["date"])

    # Pre-2020 daily close from long NIFTY minute archive.
    with zipfile.ZipFile(long_index_zip) as zf:
        member = "NIFTY_data/NIFTY_2008_2020.csv"
        with zf.open(member) as raw:
            long_df = pd.read_csv(raw, usecols=["Date","Time","Close"])
    long_df["date"] = pd.to_datetime(long_df["Date"].astype(str), format="%Y%m%d", errors="coerce").dt.normalize()
    long_df["close"] = pd.to_numeric(long_df["Close"], errors="coerce")
    long_df = long_df.dropna(subset=["date","close"]).sort_values(["date","Time"])
    long_daily = long_df[long_df.date < pd.Timestamp("2020-01-01")].groupby("date", as_index=False).tail(1)[["date","close"]]

    spot_rows = []
    with zipfile.ZipFile(ayush_zip) as zf:
        members = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".csv")
            and n.lower().startswith("nifty_data/nifty_spot/")
        )
        for i, member in enumerate(members, 1):
            with zf.open(member) as raw:
                df = pd.read_csv(raw, usecols=["date","time","symbol","open","high","low","close"])
            if df.empty:
                continue
            df["date_only"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
            df["ts"] = pd.to_datetime(df["date"].astype(str)+" "+df["time"].astype(str), errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df[(df.symbol.astype(str).str.upper()=="NIFTY") & df.close.notna()].sort_values("ts")
            if df.empty:
                continue
            d = df["date_only"].iloc[0]
            day = df[df.date_only == d]
            daily_close = float(day.iloc[-1].close)
            exact = day[day["ts"].dt.time == time(9,30)]
            if exact.empty:
                spot0930 = np.nan
            else:
                spot0930 = float(exact.iloc[0].close)
            spot_rows.append({"date": d, "close": daily_close, "spot_0930": spot0930})
            if i % 250 == 0:
                print(f"T2 spot scan {i}/{len(members)}")

    ayush_spot = pd.DataFrame(spot_rows).drop_duplicates("date").sort_values("date")
    daily = pd.concat([long_daily.assign(source="long_index"), ayush_spot[["date","close"]].assign(source="ayush_spot")],
                      ignore_index=True).sort_values("date").drop_duplicates("date", keep="last")
    daily.to_csv(daily_path, index=False)
    ayush_spot[["date","spot_0930"]].to_csv(spot0930_path, index=False)
    return daily[["date","close"]], ayush_spot[["date","spot_0930"]]

def load_option_day(zf: zipfile.ZipFile, member: str) -> pd.DataFrame:
    with zf.open(member) as raw:
        df = pd.read_csv(raw, usecols=["date","time","symbol","open","high","low","close","volume"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["timestamp"] = pd.to_datetime(df["date"].astype(str)+" "+df["time"].astype(str), errors="coerce")
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    parts = df["symbol"].map(parse_symbol)
    df["expiry"] = parts.map(lambda x: x[0] if x else pd.NaT)
    df["strike"] = parts.map(lambda x: x[1] if x else np.nan)
    df["option_type"] = parts.map(lambda x: x[2] if x else None)
    df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
    df = df[df.option_type.isin(["CE","PE"]) & df.strike.notna() & df.expiry.notna()].copy()
    df["volume"] = df["volume"].fillna(0)
    return df.sort_values("timestamp")

def get_signal_price(day: pd.DataFrame, expiry: pd.Timestamp, typ: str, strike: float, cutoff: pd.Timestamp):
    x = day[(day.expiry == expiry) & (day.option_type == typ) & (day.strike == float(strike)) &
            (day.timestamp <= cutoff) & (day.volume > 0) & day.close.notna()]
    if x.empty:
        return None
    row = x.iloc[-1]
    return float(row.close), row.timestamp

def get_execution_price(day: pd.DataFrame, expiry: pd.Timestamp, typ: str, strike: float, start: pd.Timestamp, strict: bool):
    cmp = day.timestamp > start if strict else day.timestamp >= start
    x = day[(day.expiry == expiry) & (day.option_type == typ) & (day.strike == float(strike)) &
            cmp & (day.volume > 0) & day.open.notna()]
    if x.empty:
        return None
    row = x.iloc[0]
    return float(row.open), row.timestamp

def compute_costs(signal_prices, actual_prices, execution_date, lot):
    rate = stt_rate(execution_date)
    sold_signal_premium = sum(abs(qty) * signal_prices[(typ, strike)] for typ, strike, qty, _ in batman_legs(signal_prices["__strikes"])) if False else 0.0
    return rate

def contract_cost_points(prices: dict, legs, brokerage_rupees: float, execution_date: pd.Timestamp, lot: int):
    sell_premium_points = sum(abs(qty) * prices[(typ, strike)] for typ, strike, qty, _ in legs if qty < 0)
    brokerage_points = (4.0 * brokerage_rupees) / lot
    stt_points = sell_premium_points * stt_rate(execution_date)
    return brokerage_points + stt_points

def run_candidate(request, signal_day, exec_day, daily, spot0930_map, paths, seed_base, slippage):
    expiry = pd.Timestamp(request["expiry"]).normalize()
    decision = pd.Timestamp(request["decision"]).normalize()
    offset = int(request["offset"])
    timing = request["timing"]
    signal_date = pd.Timestamp(request["signal_date"]).normalize()
    if timing == "same_session_0930":
        spot_row = spot0930_map.get(decision.date())
        if spot_row is None or not np.isfinite(spot_row):
            return None, "missing_0930_spot"
        spot = float(spot_row)
        signal_cutoff = decision + pd.Timedelta(hours=9, minutes=30)
        execution_start = signal_cutoff
        strict = True
        mc_hist_end = decision - pd.Timedelta(days=1)
        horizon = max(1, offset)
    else:
        spot = float(daily.loc[daily.date == signal_date, "close"].iloc[0])
        signal_cutoff = signal_date + pd.Timedelta(hours=15, minutes=30)
        execution_start = decision + pd.Timedelta(hours=9, minutes=15)
        strict = False
        mc_hist_end = signal_date
        horizon = max(1, offset + 1)

    hist = daily.loc[daily.date <= mc_hist_end, "close"].astype(float)
    returns = np.log(hist).diff().dropna().tail(756).to_numpy(float)
    if len(returns) < 756:
        return None, "insufficient_756_returns"
    key = f"{decision.date()}|{expiry.date()}|{offset}|{timing}"
    terminals = mc_terminal(spot, returns, horizon, paths, deterministic_seed(seed_base, key))

    available = signal_day[(signal_day.expiry == expiry) & (signal_day.timestamp <= signal_cutoff) &
                           (signal_day.volume > 0) & signal_day.strike.notna()].strike.unique()
    targets = {
        "p20": float(np.quantile(terminals, 0.20)),
        "p35": float(np.quantile(terminals, 0.35)),
        "c65": float(np.quantile(terminals, 0.65)),
        "c80": float(np.quantile(terminals, 0.80)),
    }
    strikes = unique_strikes(available, targets)
    if strikes is None:
        return None, "insufficient_strike_grid"

    legs = batman_legs(strikes)
    signal_prices = {}
    actual_prices = {}
    signal_ts = {}
    exec_ts = {}
    for typ, strike, qty, label in legs:
        sp = get_signal_price(signal_day, expiry, typ, strike, signal_cutoff)
        if sp is None:
            return None, f"missing_signal_price_{label}"
        ep = get_execution_price(exec_day, expiry, typ, strike, execution_start, strict)
        if ep is None:
            return None, f"missing_execution_price_{label}"
        signal_prices[(typ,strike)] = sp[0]
        actual_prices[(typ,strike)] = ep[0]
        signal_ts[label] = str(sp[1])
        exec_ts[label] = str(ep[1])

    lot = lot_size(expiry)
    signal_entry = 0.0
    actual_entry = 0.0
    for typ, strike, qty, label in legs:
        raw_sig = signal_prices[(typ,strike)]
        raw_act = actual_prices[(typ,strike)]
        signal_adj = raw_sig + slippage if qty > 0 else raw_sig - slippage
        actual_adj = raw_act + slippage if qty > 0 else raw_act - slippage
        signal_entry -= qty * signal_adj
        actual_entry -= qty * actual_adj

    pnl_paths = np.zeros(paths, dtype=float)
    for typ, strike, qty, label in legs:
        intrinsic = np.maximum(terminals - strike, 0.0) if typ == "CE" else np.maximum(strike - terminals, 0.0)
        pnl_paths += qty * intrinsic
    pnl_paths += signal_entry

    expiry_row = daily.loc[daily.date == expiry, "close"]
    if expiry_row.empty:
        return None, "missing_expiry_close"
    expiry_spot = float(expiry_row.iloc[0])
    realized_intrinsic = 0.0
    for typ, strike, qty, label in legs:
        intrinsic = max(expiry_spot - strike, 0.0) if typ == "CE" else max(strike - expiry_spot, 0.0)
        realized_intrinsic += qty * intrinsic
    realized_gross = realized_intrinsic + actual_entry

    mc_ev_gross = float(np.mean(pnl_paths))
    mc_pop = float(np.mean(pnl_paths > 0))
    q05 = float(np.quantile(pnl_paths, 0.05))
    q01 = float(np.quantile(pnl_paths, 0.01))
    es95 = float(max(0.0, -np.mean(pnl_paths[pnl_paths <= q05]))) if np.any(pnl_paths <= q05) else 0.0
    es99 = float(max(0.0, -np.mean(pnl_paths[pnl_paths <= q01]))) if np.any(pnl_paths <= q01) else 0.0

    rows = []
    for brokerage in BROKERAGES:
        gate_cost_points = contract_cost_points(signal_prices, legs, brokerage, decision, lot)
        mc_net = mc_ev_gross - gate_cost_points
        actual_cost_points = contract_cost_points(actual_prices, legs, brokerage, decision, lot)
        realized_net = realized_gross - actual_cost_points
        rows.append({
            "decision_date": decision.date().isoformat(),
            "expiry": expiry.date().isoformat(),
            "offset": offset,
            "timing": timing,
            "signal_date": signal_date.date().isoformat(),
            "spot_signal": spot,
            "p20_strike": strikes["p20"],
            "p35_strike": strikes["p35"],
            "c65_strike": strikes["c65"],
            "c80_strike": strikes["c80"],
            "lot_size": lot,
            "mc_paths": paths,
            "mc_horizon_sessions": horizon,
            "mc_seed": deterministic_seed(seed_base,key),
            "mc_ev_gross_points": mc_ev_gross,
            "mc_ev_net_points": mc_net,
            "mc_pop": mc_pop,
            "mc_es95_points": es95,
            "mc_es99_points": es99,
            "realized_gross_points": realized_gross,
            "realized_net_points": realized_net,
            "realized_gross_inr": realized_gross * lot,
            "realized_net_inr": realized_net * lot,
            "brokerage_per_order_inr": brokerage,
            "brokerage_total_inr": 4*brokerage,
            "stt_rate": stt_rate(decision),
            "gate_enter": int(mc_net > 0),
            "signal_timestamps": json.dumps(signal_ts, sort_keys=True),
            "execution_timestamps": json.dumps(exec_ts, sort_keys=True),
            "execution_delay_rule": "first positive-volume observation after signal",
            "d0_model_flag": int(offset == 0 and timing == "same_session_0930"),
        })
    return rows, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--options-zip", required=True)
    ap.add_argument("--long-index-zip", required=True)
    ap.add_argument("--raw-cache", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--paths", type=int, default=5000)
    ap.add_argument("--seed-base", type=int, default=20260921)
    args = ap.parse_args()

    raw_root = Path(args.raw_cache)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ayush_zip = Path(args.options_zip)
    long_zip = Path(args.long_index_zip)

    cal, fmap = prepare_maps(raw_root, ayush_zip)
    daily, spot0930 = prepare_spot_and_daily(raw_root, ayush_zip, long_zip)
    daily["date"] = pd.to_datetime(daily.date).dt.normalize()
    daily["close"] = pd.to_numeric(daily.close, errors="coerce")
    daily = daily.dropna(subset=["date","close"]).sort_values("date").drop_duplicates("date")
    spot0930["date"] = pd.to_datetime(spot0930.date).dt.normalize()
    spot0930_map = dict(zip(spot0930.date.dt.date, pd.to_numeric(spot0930.spot_0930, errors="coerce")))

    sessions = pd.DatetimeIndex(daily.date.unique()).sort_values()
    exp_dates = sorted(pd.to_datetime(cal.expiry).dropna().unique())
    requests = []
    for exp in exp_dates:
        exp = pd.Timestamp(exp).normalize()
        matches = sessions[sessions == exp]
        if len(matches) != 1:
            continue
        pos = sessions.get_loc(exp)
        for offset in range(7):
            if pos - offset < 0:
                continue
            decision = sessions[pos-offset]
            if decision < pd.Timestamp("2020-01-01") or decision > pd.Timestamp("2024-10-31"):
                continue
            prior_pos = pos-offset-1
            if prior_pos < 0:
                continue
            prior = sessions[prior_pos]
            requests.append({"expiry":exp,"offset":offset,"decision":decision,"timing":"prior_evening_to_open","signal_date":prior})
            requests.append({"expiry":exp,"offset":offset,"decision":decision,"timing":"same_session_0930","signal_date":decision})
    req_df = pd.DataFrame(requests).drop_duplicates().sort_values(["signal_date","decision","expiry","offset","timing"]).reset_index(drop=True)
    file_map = dict(zip(fmap.trade_date.dt.normalize(), fmap.member))

    rows = []
    skips = defaultdict(int)
    day_cache = {}
    with zipfile.ZipFile(ayush_zip) as zf:
        for i, req in enumerate(req_df.itertuples(index=False), 1):
            sdate = pd.Timestamp(req.signal_date).normalize()
            edate = pd.Timestamp(req.decision).normalize()
            smember = file_map.get(sdate)
            emember = file_map.get(edate)
            if smember is None or emember is None:
                skips["missing_option_file"] += 1
                continue
            if sdate not in day_cache:
                day_cache[sdate] = load_option_day(zf, smember)
            if edate not in day_cache:
                day_cache[edate] = load_option_day(zf, emember)
            # Keep memory bounded while preserving nearby-date reuse.
            if len(day_cache) > 8:
                oldest = sorted(day_cache)[0]
                if oldest not in {sdate, edate}:
                    day_cache.pop(oldest, None)
            result, reason = run_candidate(req._asdict(), day_cache[sdate], day_cache[edate], daily, spot0930_map,
                                           args.paths, args.seed_base, SLIPPAGE_POINTS)
            if result is None:
                skips[reason] += 1
            else:
                rows.extend(result)
            if i % 200 == 0:
                print(f"T2 candidates {i}/{len(req_df)}")

    trades = pd.DataFrame(rows)
    if trades.empty:
        raise SystemExit("No T2 candidate rows generated.")
    trades["decision_date"] = pd.to_datetime(trades.decision_date)
    trades["expiry"] = pd.to_datetime(trades.expiry)
    trades["entered"] = trades.gate_enter.astype(bool)

    # Candidate summary is evaluated for each brokerage scenario separately.
    summary = []
    for (offset, timing, brokerage), g in trades.groupby(["offset","timing","brokerage_per_order_inr"], dropna=False):
        active = g[g.entered]
        x = active.realized_net_inr.to_numpy(float)
        gains = x[x > 0].sum()
        losses = -x[x < 0].sum()
        eq = np.cumsum(x) if len(x) else np.array([])
        dd = eq - np.maximum.accumulate(eq) if len(eq) else np.array([0.0])
        summary.append({
            "offset": int(offset), "timing": timing, "brokerage_per_order_inr": float(brokerage),
            "opportunities": int(len(g)), "entered": int(len(active)),
            "entry_rate": float(len(active)/len(g)) if len(g) else np.nan,
            "win_rate": float(np.mean(x>0)) if len(x) else np.nan,
            "mean_net_inr_per_trade": float(np.mean(x)) if len(x) else np.nan,
            "median_net_inr_per_trade": float(np.median(x)) if len(x) else np.nan,
            "total_net_inr": float(np.sum(x)) if len(x) else 0.0,
            "profit_factor": float(gains/losses) if losses > 0 else np.inf,
            "max_drawdown_inr": float(dd.min()) if len(eq) else 0.0,
            "mean_mc_ev_net_points": float(g.mc_ev_net_points.mean()),
        })
    summary = pd.DataFrame(summary).sort_values(["brokerage_per_order_inr","offset","timing"])

    # Control and paired descriptive comparison.
    control_key = {"offset":3,"timing":"same_session_0930"}
    control = trades[(trades.offset==3)&(trades.timing==control_key["timing"])][
        ["expiry","brokerage_per_order_inr","realized_net_inr","entered"]
    ].rename(columns={"realized_net_inr":"control_pnl","entered":"control_entered"})
    pairs=[]
    for (offset,timing,brokerage), g in trades.groupby(["offset","timing","brokerage_per_order_inr"]):
        merged=g[["expiry","decision_date","realized_net_inr","entered"]].merge(
            control[control.brokerage_per_order_inr==brokerage] if "brokerage_per_order_inr" in control.columns else control,
            on="expiry", how="inner"
        )
        both=merged[(merged.entered)&(merged.control_entered)]
        pairs.append({
            "offset":int(offset),"timing":timing,"brokerage_per_order_inr":float(brokerage),
            "matched_both_trade":int(len(both)),
            "paired_mean_net_inr":float((both.realized_net_inr-both.control_pnl).mean()) if len(both) else np.nan,
            "paired_median_net_inr":float((both.realized_net_inr-both.control_pnl).median()) if len(both) else np.nan,
        })
    paired=pd.DataFrame(pairs)

    trades.to_csv(out/"T2_ENTRY_TRADE_LEVEL.csv",index=False)
    summary.to_csv(out/"T2_ENTRY_SUMMARY.csv",index=False)
    paired.to_csv(out/"T2_ENTRY_PAIRED_CONTROL.csv",index=False)
    pd.DataFrame([dict(skips)]).to_json(out/"T2_SKIP_COUNTS.json",orient="records",indent=2)
    req_df.to_csv(out/"T2_OPPORTUNITY_MATRIX.csv",index=False)

    print("T2 COMPLETE")
    print(summary.to_string(index=False))
    print("SKIPS", dict(skips))

if __name__ == "__main__":
    main()
