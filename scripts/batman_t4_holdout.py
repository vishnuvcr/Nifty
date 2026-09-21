#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.batman_t2_entry import deterministic_seed, mc_terminal, unique_strikes, batman_legs, get_execution_price

BROKERAGES = (10.0, 20.0, 30.0)
SLIPPAGE_POINTS = 2.0


def lot_size(expiry):
    return 75 if pd.Timestamp(expiry).date() <= date(2025, 12, 30) else 65


def stt_rate(ts):
    return 0.0015 if pd.Timestamp(ts).date() >= date(2026, 4, 1) else 0.001


def expiry_candidates(sessions):
    sessions = pd.DatetimeIndex(sessions).sort_values()
    raw = []
    d = pd.Timestamp("2025-01-02")
    while d <= pd.Timestamp("2025-08-28"):
        if d.weekday() == 3:
            raw.append(d)
        d += pd.Timedelta(days=1)
    d = pd.Timestamp("2025-09-02")
    while d <= pd.Timestamp("2026-07-21"):
        if d.weekday() == 1:
            raw.append(d)
        d += pd.Timedelta(days=1)

    out = []
    for target in raw:
        prior = sessions[sessions <= target]
        if len(prior) == 0:
            continue
        exp = pd.Timestamp(prior[-1]).normalize()
        if exp not in out and exp <= sessions.max():
            out.append(exp)
    return pd.DatetimeIndex(out)


def load_daily(path):
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    date_col = "date" if "date" in df.columns else ("datetime" if "datetime" in df.columns else "Date".lower())
    close_col = "close" if "close" in df.columns else ("price" if "price" in df.columns else "last")
    df["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.tz_localize(None).dt.normalize()
    df["close"] = pd.to_numeric(df[close_col].astype(str).str.replace(",", "", regex=False), errors="coerce")
    return df.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")[["date", "close"]]


def prepare_option_csv(zf, name):
    return name


def mc_reference(spot, returns, seed, decision, expiry):
    terminals = mc_terminal(
        float(spot),
        returns,
        3,
        5000,
        deterministic_seed(20260921, f"{decision.date()}|{expiry.date()}|T4_HOLDOUT"),
    )
    return terminals


def portfolio_max_profit(strikes, entry_cashflow):
    legs = batman_legs(strikes)
    points = sorted(set([0.0] + [float(x[1]) for x in legs]))
    vals = []
    for s in points:
        intrinsic = 0.0
        for typ, strike, qty, _ in legs:
            v = max(s - strike, 0.0) if typ == "CE" else max(strike - s, 0.0)
            intrinsic += qty * v
        vals.append(intrinsic + entry_cashflow)
    return max(0.0, max(vals))


def adjusted_price(raw, qty, side):
    # side='entry': qty>0 buy, qty<0 sell
    # side='exit' : qty>0 sell, qty<0 buy
    if side == "entry":
        return raw + SLIPPAGE_POINTS if qty > 0 else max(0.0, raw - SLIPPAGE_POINTS)
    return max(0.0, raw - SLIPPAGE_POINTS) if qty > 0 else raw + SLIPPAGE_POINTS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--options-zip", required=True)
    ap.add_argument("--daily-index", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    daily = load_daily(args.daily_index)

    option_dates = {}
    with zipfile.ZipFile(args.options_zip) as zf:
        member = [n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        with zf.open(member) as fh:
            for chunk in pd.read_csv(fh, usecols=['timestamp','spot_price'], chunksize=500000):
                chunk['timestamp'] = pd.to_datetime(chunk.timestamp, errors='coerce', utc=True)
                chunk['local_date'] = chunk.timestamp.dt.tz_convert('Asia/Kolkata').dt.normalize().dt.tz_localize(None)
                chunk['spot_price'] = pd.to_numeric(chunk.spot_price, errors='coerce')
                chunk = chunk.dropna(subset=['timestamp','local_date','spot_price'])
                if chunk.empty:
                    continue
                for d, g in chunk.groupby('local_date'):
                    row = g.sort_values('timestamp').iloc[-1]
                    option_dates[pd.Timestamp(d)] = (pd.Timestamp(row.timestamp), float(row.spot_price))

    extension = pd.DataFrame([{'date': d, 'close': v[1]} for d, v in option_dates.items()])
    extension = extension[extension['date'] >= pd.Timestamp('2025-01-01')]
    daily = pd.concat([daily, extension], ignore_index=True).sort_values('date')
    daily = daily.drop_duplicates('date', keep='last')
    sessions = pd.DatetimeIndex(daily.date.unique()).sort_values()
    expiry_list = expiry_candidates(sessions)
    expiry_list = expiry_list[(expiry_list >= pd.Timestamp("2025-01-02")) & (expiry_list <= pd.Timestamp("2026-07-21"))]

    requests = []
    for expiry in expiry_list:
        if expiry not in sessions:
            continue
        pos = sessions.get_loc(expiry)
        if pos < 3:
            continue
        decision = sessions[pos - 3]
        if decision < pd.Timestamp("2025-01-01"):
            continue
        requests.append((decision, expiry))

    request_by_date = {}
    for decision, expiry in requests:
        request_by_date.setdefault(decision.normalize(), []).append(expiry)

    daily_map = dict(zip(daily.date, daily.close))

    # First pass: retain only the near-expiry (expiry_code=1) decision-day rows,
    # which is enough to reconstruct the point-in-time strike grid and 09:30 entry.
    decision_rows = {}
    entry_rows = {}

    with zipfile.ZipFile(args.options_zip) as zf:
        member = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        with zf.open(member) as fh:
            for chunk in pd.read_csv(
                fh,
                usecols=["timestamp","expiry_code","option_type","open","close","volume","strike_price","spot_price"],
                chunksize=500000,
            ):
                chunk["timestamp"] = pd.to_datetime(chunk.timestamp, errors="coerce", utc=True)
                # Dataset timestamps are UTC; NSE 09:30 IST = 04:00 UTC.
                chunk["local_date"] = chunk["timestamp"].dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
                chunk = chunk[chunk["expiry_code"].eq(1)]
                needed_dates = set(request_by_date.keys())
                chunk = chunk[chunk.local_date.isin(needed_dates)]
                if chunk.empty:
                    continue
                chunk["strike_price"] = pd.to_numeric(chunk.strike_price, errors="coerce")
                chunk["volume"] = pd.to_numeric(chunk.volume, errors="coerce").fillna(0)
                chunk["open"] = pd.to_numeric(chunk.open, errors="coerce")
                chunk["close"] = pd.to_numeric(chunk.close, errors="coerce")
                chunk["spot_price"] = pd.to_numeric(chunk.spot_price, errors="coerce")

                for d, g in chunk.groupby("local_date"):
                    cutoff = pd.Timestamp(d, tz="Asia/Kolkata") + pd.Timedelta(hours=9, minutes=30)
                    before = g[(g.timestamp <= cutoff) & (g.volume > 0) & g.strike_price.notna() & g.close.notna()]
                    if before.empty:
                        continue
                    strikes = before.strike_price.unique()
                    exact_spot = g[g.timestamp == cutoff].spot_price.dropna()
                    if exact_spot.empty:
                        continue
                    spot = float(exact_spot.iloc[0])
                    signal_marks = {}
                    for typ in ("CE", "PE"):
                        gg = before[before.option_type.astype(str).str.upper().eq(typ)]
                        for strike in gg.strike_price.unique():
                            z = gg[gg.strike_price.eq(strike)].sort_values("timestamp")
                            signal_marks[(typ, float(strike))] = (float(z.iloc[-1].close), pd.Timestamp(z.iloc[-1].timestamp))
                    execution = {}
                    after = g[(g.timestamp > cutoff) & (g.volume > 0) & g.open.notna()]
                    for typ in ("CE", "PE"):
                        gg = after[after.option_type.astype(str).str.upper().eq(typ)]
                        for strike in gg.strike_price.unique():
                            z = gg[gg.strike_price.eq(strike)].sort_values("timestamp")
                            execution[(typ, float(strike))] = (float(z.iloc[0].open), pd.Timestamp(z.iloc[0].timestamp))
                    decision_rows[pd.Timestamp(d)] = {"spot":spot,"strikes":strikes,"signal_marks":signal_marks}
                    entry_rows[pd.Timestamp(d)] = execution

    rows = []
    skips = {}
    stages = {
        "daily_rows_after_parse": int(len(daily)),
        "daily_start": str(daily.date.min()) if len(daily) else "",
        "daily_end": str(daily.date.max()) if len(daily) else "",
        "daily_rows_before_first_holdout_decision": 0,
        "expiry_candidates": int(len(expiry_list)),
        "requests": int(len(requests)),
        "decision_dates_present": 0,
        "exact_0930_spot": 0,
        "mc_ready_756": 0,
        "strike_grid_ready": 0,
        "all_four_entry_legs_ready": 0,
        "gross_mc_gate_pass": 0,
        "positive_max_profit_reference": 0,
        "final_entry_candidates": 0,
        "final_exit_candidates": 0,
    }

    with zipfile.ZipFile(args.options_zip) as zf:
        member = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]

        # Build candidate definitions from the point-in-time first pass.
        candidates = []
        for decision, expiry in requests:
            if decision not in decision_rows:
                skips["missing_decision_0930"] = skips.get("missing_decision_0930", 0) + 1
                continue
            stages["decision_dates_present"] += 1

            spot = decision_rows[decision]["spot"]
            if not np.isfinite(spot):
                skips["nonfinite_0930_spot"] = skips.get("nonfinite_0930_spot", 0) + 1
                continue
            stages["exact_0930_spot"] += 1
            hist = daily.loc[daily.date <= (decision - pd.Timedelta(days=1)), "close"].astype(float)
            if decision == requests[0][0]:
                stages["daily_rows_before_first_holdout_decision"] = int(len(hist))
            returns = np.log(hist).diff().dropna().tail(756).to_numpy()
            if len(returns) < 756:
                skips["insufficient_756_returns"] = skips.get("insufficient_756_returns", 0) + 1
                continue
            stages["mc_ready_756"] += 1

            terminals = mc_reference(spot, returns, 20260921, decision, expiry)
            targets = {
                "p20": float(np.quantile(terminals, 0.20)),
                "p35": float(np.quantile(terminals, 0.35)),
                "c65": float(np.quantile(terminals, 0.65)),
                "c80": float(np.quantile(terminals, 0.80)),
            }
            strikes = unique_strikes(decision_rows[decision]["strikes"], targets)
            if strikes is None:
                skips["insufficient_strikes"] = skips.get("insufficient_strikes", 0) + 1
                continue
            stages["strike_grid_ready"] += 1

            legs = batman_legs(strikes)
            execution = entry_rows.get(decision, {})
            leg_entries = []
            valid = True
            entry_complete = pd.Timestamp.min
            entry_cashflow = 0.0
            entry_stt = {}

            for typ, strike, qty, label in legs:
                px_ts = execution.get((typ, float(strike)))
                if px_ts is None:
                    valid = False
                    skips[f"missing_entry_{label}"] = skips.get(f"missing_entry_{label}", 0) + 1
                    break
                raw_px, ts = px_ts
                adj = adjusted_price(raw_px, qty, "entry")
                entry_cashflow -= qty * adj
                entry_complete = max(entry_complete, ts)
                leg_entries.append((typ, strike, qty, label, raw_px, ts))
                if qty < 0:
                    entry_stt[label] = abs(qty) * adj

            if not valid or entry_complete == pd.Timestamp.min:
                continue
            stages["all_four_entry_legs_ready"] += 1

            mc_pnl = np.zeros(len(terminals))
            for typ, strike, qty, _ in legs:
                intrinsic = np.maximum(terminals - strike, 0.0) if typ == "CE" else np.maximum(strike - terminals, 0.0)
                mc_pnl += qty * intrinsic
            mc_pnl += entry_cashflow
            mc_ev = float(mc_pnl.mean())
            if mc_ev <= 0:
                skips["gross_mc_gate_failed"] = skips.get("gross_mc_gate_failed", 0) + 1
                continue
            stages["gross_mc_gate_pass"] += 1

            q05 = float(np.quantile(mc_pnl, 0.05))
            es95 = float(max(0.0, -np.mean(mc_pnl[mc_pnl <= q05]))) if np.any(mc_pnl <= q05) else 0.0
            max_profit = portfolio_max_profit(strikes, entry_cashflow)
            if max_profit <= 0:
                skips["nonpositive_max_profit_reference"] = skips.get("nonpositive_max_profit_reference", 0) + 1
                continue
            stages["positive_max_profit_reference"] += 1
            stages["final_entry_candidates"] += 1

            candidates.append(
                {
                    "decision":decision,
                    "expiry":expiry,
                    "spot":spot,
                    "strikes":strikes,
                    "legs":legs,
                    "leg_entries":leg_entries,
                    "entry_cashflow":entry_cashflow,
                    "entry_complete":entry_complete,
                    "entry_stt":entry_stt,
                    "mc_ev":mc_ev,
                    "mc_es95":es95,
                    "max_profit":max_profit,
                }
            )

        # Second pass: collect selected-leg minute marks only for accepted candidates.
        candidate_keys = []
        for c in candidates:
            candidate_keys.append(c)

        mark_store = {i: [] for i in range(len(candidate_keys))}
        if candidate_keys:
            min_date = min(c["entry_complete"].tz_convert("Asia/Kolkata").date() for c in candidate_keys)
            max_date = max(c["expiry"].date() for c in candidate_keys)
        else:
            min_date = date(2099,1,1); max_date = date(2000,1,1)

        with zf.open(member) as fh:
            for chunk in pd.read_csv(
                fh,
                usecols=["timestamp","expiry_code","option_type","open","close","volume","strike_price","spot_price"],
                chunksize=500000,
            ):
                chunk["timestamp"] = pd.to_datetime(chunk.timestamp, errors="coerce", utc=True)
                chunk["local_date"] = chunk.timestamp.dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
                chunk = chunk[chunk.expiry_code.eq(1)]
                chunk = chunk[(chunk.local_date >= pd.Timestamp(min_date)) & (chunk.local_date <= pd.Timestamp(max_date))]
                if chunk.empty:
                    continue
                chunk["strike_price"] = pd.to_numeric(chunk.strike_price, errors="coerce")
                chunk["volume"] = pd.to_numeric(chunk.volume, errors="coerce").fillna(0)
                chunk["close"] = pd.to_numeric(chunk.close, errors="coerce")
                for i,c in enumerate(candidate_keys):
                    active = chunk[
                        (chunk.timestamp >= c["entry_complete"])
                        & (chunk.local_date <= c["expiry"])
                        & (chunk.volume > 0)
                        & chunk.close.notna()
                    ]
                    if active.empty:
                        continue
                    mask = pd.Series(False, index=active.index)
                    for typ,strike,qty,label in c["legs"]:
                        mask |= (
                            active.option_type.astype(str).str.upper().eq(typ)
                            & active.strike_price.eq(float(strike))
                        )
                    z = active[mask]
                    if not z.empty:
                        z = z.assign(option_type=z.option_type.astype(str).str.upper())
                        mark_store[i].append(z[["timestamp","option_type","strike_price","close","volume"]])

        for i,c in enumerate(candidate_keys):
            zparts = mark_store[i]
            if not zparts:
                skips["missing_exit_marks"] = skips.get("missing_exit_marks", 0) + 1
                continue
            z = pd.concat(zparts, ignore_index=True).sort_values("timestamp")
            # Construct synchronized portfolio marks with last available price per leg.
            frames = []
            for typ,strike,qty,label in c["legs"]:
                g = z[(z.option_type.eq(typ)) & z.strike_price.eq(float(strike))][["timestamp","close"]].copy()
                g["label"] = label
                frames.append(g)
            allm = pd.concat(frames, ignore_index=True)
            piv = allm.pivot_table(index="timestamp", columns="label", values="close", aggfunc="last").sort_index()
            needed = [x[3] for x in c["legs"]]
            piv = piv.ffill().dropna(subset=needed)
            pnl = np.zeros(len(piv))
            for typ,strike,qty,label in c["legs"]:
                pnl += qty * piv[label].to_numpy(float)
            piv["pnl_points"] = pnl + c["entry_cashflow"]
            piv = piv.reset_index().sort_values("timestamp")

            peak = 0.0
            activated = False
            trigger_ts = None
            for _,row in piv.iterrows():
                p=float(row.pnl_points)
                if not activated and p >= 0.20 * c["max_profit"]:
                    activated=True
                    peak=p
                elif activated:
                    peak=max(peak,p)
                    if p <= peak - 0.10 * c["max_profit"]:
                        trigger_ts=pd.Timestamp(row.timestamp)
                        break

            # Always retain the trade: trigger exit or expiry fallback.
            if trigger_ts is None:
                exit_rows = piv.iloc[-1]
                exit_mode="expiry_fallback"
                exit_time=pd.Timestamp(exit_rows.timestamp)
                exits=[]
                for typ,strike,qty,label in c["legs"]:
                    g=z[(z.option_type.eq(typ))&z.strike_price.eq(float(strike))&(z.timestamp<=exit_time)&(z.volume>0)].sort_values("timestamp")
                    if g.empty:
                        exits=[]; break
                    r=g.iloc[-1]
                    exits.append((typ,strike,qty,label,float(r.close),pd.Timestamp(r.timestamp)))
                if not exits:
                    skips["expiry_exit_missing"] = skips.get("expiry_exit_missing",0)+1
                    continue
            else:
                exits=[]
                exit_mode="trailing_target"
                for typ,strike,qty,label in c["legs"]:
                    g=z[(z.option_type.eq(typ))&z.strike_price.eq(float(strike))&(z.timestamp>trigger_ts)&(z.volume>0)].sort_values("timestamp")
                    if g.empty:
                        exits=[]; break
                    r=g.iloc[0]
                    exits.append((typ,strike,qty,label,float(r.close),pd.Timestamp(r.timestamp)))
                if not exits:
                    # Trigger happened but next executable quote was unavailable; use expiry fallback.
                    exit_mode="expiry_fallback_after_unexecutable_trigger"
                    exits=[]
                    expiry_ts=piv.iloc[-1].timestamp
                    for typ,strike,qty,label in c["legs"]:
                        g=z[(z.option_type.eq(typ))&z.strike_price.eq(float(strike))&(z.timestamp<=expiry_ts)&(z.volume>0)].sort_values("timestamp")
                        if g.empty:
                            exits=[]; break
                        r=g.iloc[-1]
                        exits.append((typ,strike,qty,label,float(r.close),pd.Timestamp(r.timestamp)))
                if not exits:
                    skips["exit_missing_after_trigger"] = skips.get("exit_missing_after_trigger",0)+1
                    continue

            lot=lot_size(c["expiry"])
            for brokerage in BROKERAGES:
                exit_cashflow=0.0
                entry_stt_inr=sum(v*lot*c["leg_entries"][0][5].strftime("%s")*0 for v in [])  # explicit zero; computed below
                entry_stt_inr=0.0
                for typ,strike,qty,label,raw_px,ts in c["leg_entries"]:
                    adj=adjusted_price(raw_px,qty,"entry")
                    if qty<0:
                        entry_stt_inr += abs(qty)*adj*lot*stt_rate(ts)

                exit_stt_inr=0.0
                for typ,strike,qty,label,raw_px,ts in exits:
                    adj=adjusted_price(raw_px,qty,"exit")
                    exit_cashflow += qty*adj
                    if qty>0:
                        exit_stt_inr += abs(qty)*adj*lot*stt_rate(ts)

                gross_points=c["entry_cashflow"]+exit_cashflow
                net_inr=gross_points*lot - 8.0*brokerage - entry_stt_inr - exit_stt_inr
                rows.append(
                    {
                        "decision_date":c["decision"].date().isoformat(),
                        "expiry":c["expiry"].date().isoformat(),
                        "entry_rule":"D3_same_session_0930_gross_gate",
                        "exit_rule":"trailing_target_activation20_retracement10",
                        "brokerage_per_order_inr":brokerage,
                        "lot_size":lot,
                        "spot_0930":c["spot"],
                        "p20":c["strikes"]["p20"],"p35":c["strikes"]["p35"],
                        "c65":c["strikes"]["c65"],"c80":c["strikes"]["c80"],
                        "mc_ev_points":c["mc_ev"],"mc_es95_points":c["mc_es95"],
                        "max_profit_reference_points":c["max_profit"],
                        "entry_complete":str(c["entry_complete"]),
                        "trigger_time":str(trigger_ts) if trigger_ts is not None else "",
                        "exit_time":str(max(x[5] for x in exits)),
                        "exit_mode":exit_mode,
                        "holding_minutes":(max(x[5] for x in exits)-c["entry_complete"]).total_seconds()/60,
                        "realized_gross_points":gross_points,
                        "realized_net_inr":net_inr,
                        "entry_stt_inr":entry_stt_inr,
                        "exit_stt_inr":exit_stt_inr,
                        "brokerage_total_inr":8.0*brokerage,
                    }
                )

    result=pd.DataFrame(rows)
    stages["final_exit_candidates"] = int(result["decision_date"].nunique()) if not result.empty else 0
    (out/"T4_HOLDOUT_STAGE_COUNTS.json").write_text(
        json.dumps({"stages": stages, "skips": skips}, indent=2) + "\n"
    )
    print("HOLDOUT STAGES", json.dumps(stages, indent=2))
    print("HOLDOUT SKIPS", json.dumps(skips, indent=2))
    if result.empty:
        raise SystemExit("No holdout trades generated; diagnostics written to T4_HOLDOUT_STAGE_COUNTS.json")

    summary=[]
    for brokerage,g in result.groupby("brokerage_per_order_inr"):
        x=g.realized_net_inr.to_numpy(float)
        gains=x[x>0].sum(); losses=-x[x<0].sum()
        eq=np.cumsum(x)
        dd=eq-np.maximum.accumulate(eq)
        summary.append(
            {
                "brokerage_per_order_inr":float(brokerage),
                "trades":int(len(g)),
                "total_net_inr":float(x.sum()),
                "mean_net_inr":float(x.mean()),
                "median_net_inr":float(np.median(x)),
                "win_rate":float((x>0).mean()),
                "profit_factor":float(gains/losses) if losses>0 else np.inf,
                "max_drawdown_inr":float(dd.min()),
                "positive_months":int((g.assign(month=pd.to_datetime(g.decision_date).dt.to_period("M")).groupby("month").realized_net_inr.sum()>0).sum()),
            }
        )

    yearly=result.assign(year=pd.to_datetime(result.decision_date).dt.year).groupby(["year","brokerage_per_order_inr"]).agg(
        trades=("realized_net_inr","size"),
        total_net_inr=("realized_net_inr","sum"),
        mean_net_inr=("realized_net_inr","mean"),
        win_rate=("realized_net_inr",lambda x: float((x>0).mean())),
    ).reset_index()

    result.to_csv(out/"T4_HOLDOUT_TRADE_LEVEL.csv",index=False)
    pd.DataFrame(summary).to_csv(out/"T4_HOLDOUT_SUMMARY.csv",index=False)
    yearly.to_csv(out/"T4_HOLDOUT_YEARLY.csv",index=False)
    Path(out/"T4_HOLDOUT_SKIP_COUNTS.json").write_text(json.dumps(skips,indent=2)+"\n")
    Path(out/"T4_HOLDOUT_REPORT.json").write_text(json.dumps(
        {"frozen_rule":"trailing_target activation 20%, retracement 10%",
         "entry":"D3 same-session 09:30 gross MC-EV > 0",
         "brokers":[10,20,30],
         "holdout_start":str(result.decision_date.min()),
         "holdout_end":str(result.decision_date.max()),
         "trades":int(result.decision_date.nunique()),
         "source_expiry_code":1,
         "source_expiry_code_semantics":"near/current expiry per Dhan expired-options documentation",
         "summary":summary},
        indent=2)+"\n"
    )
    print(pd.DataFrame(summary).to_string(index=False))
    print(yearly.to_string(index=False))
    print("SKIPS",json.dumps(skips,indent=2))


if __name__=="__main__":
    main()
