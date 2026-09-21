#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from collections import defaultdict
from datetime import date, time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.batman_t2_entry import (
    batman_legs,
    deterministic_seed,
    get_execution_price,
    get_signal_price,
    load_option_day,
    lot_size,
    mc_terminal,
    parse_symbol,
    prepare_maps,
    prepare_spot_and_daily,
    stt_rate,
    unique_strikes,
)

SLIPPAGE = 2.0
BROKERAGES = (10.0, 20.0, 30.0)
FIXED_TARGETS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.75)
FIXED_STOPS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00)
TRAIL_TARGETS = tuple((a, r) for a in (0.20, 0.30, 0.40, 0.50) for r in (0.10, 0.20, 0.30))
TRAIL_STOPS = (0.10, 0.20, 0.30, 0.40, 0.50)


def expiry_exit_marks(day_frames, legs, expiry):
    day = day_frames.get(pd.Timestamp(expiry).normalize())
    if day is None:
        return None
    cut = pd.Timestamp(expiry).normalize() + pd.Timedelta(hours=15, minutes=29)
    exits = []
    for typ, strike, qty, label in legs:
        x = day[
            (day.expiry == pd.Timestamp(expiry).normalize())
            & (day.option_type == typ)
            & (day.strike == float(strike))
            & (day.timestamp <= cut)
            & (day.volume > 0)
            & day.close.notna()
        ].sort_values("timestamp")
        if x.empty:
            return None
        row = x.iloc[-1]
        exits.append((typ, strike, qty, label, float(row.close), pd.Timestamp(row.timestamp)))
    return exits


def next_execution(day_frames, legs, trigger_ts, expiry):
    dates = sorted(d for d in day_frames if pd.Timestamp(d).normalize() >= pd.Timestamp(trigger_ts).normalize())
    exits = []
    for typ, strike, qty, label in legs:
        found = None
        for d in dates:
            day = day_frames[d]
            x = day[
                (day.expiry == pd.Timestamp(expiry).normalize())
                & (day.option_type == typ)
                & (day.strike == float(strike))
                & (day.timestamp > trigger_ts)
                & (day.volume > 0)
                & day.open.notna()
            ].sort_values("timestamp")
            if not x.empty:
                row = x.iloc[0]
                found = (typ, strike, qty, label, float(row.open), pd.Timestamp(row.timestamp))
                break
        if found is None:
            return None
        exits.append(found)
    return exits


def max_profit_reference(legs, entry_cashflow):
    breakpoints = sorted(set([0.0] + [float(x[1]) for x in legs]))
    vals = []
    for spot in breakpoints:
        payoff = 0.0
        for typ, strike, qty, label in legs:
            intrinsic = max(spot - strike, 0.0) if typ == "CE" else max(strike - spot, 0.0)
            payoff += qty * intrinsic
        vals.append(payoff + entry_cashflow)
    return max(0.0, max(vals))


def entry_price_adjusted(raw, qty):
    if qty > 0:
        return raw + SLIPPAGE
    return max(0.0, raw - SLIPPAGE)


def exit_price_adjusted(raw, qty):
    if qty > 0:
        return max(0.0, raw - SLIPPAGE)
    return raw + SLIPPAGE


def realized_net(entry_cashflow, entry_legs, exits, expiry, brokerage):
    lot = lot_size(pd.Timestamp(expiry))
    exit_cashflow = 0.0
    entry_stt = 0.0
    exit_stt = 0.0
    for typ, strike, qty, label, raw_px, ts in entry_legs:
        adj = entry_price_adjusted(raw_px, qty)
        if qty < 0:
            entry_stt += abs(qty) * adj * lot * stt_rate(pd.Timestamp(ts))
    for typ, strike, qty, label, raw_px, ts in exits:
        adj = exit_price_adjusted(raw_px, qty)
        exit_cashflow += qty * adj
        if qty > 0:
            exit_stt += abs(qty) * adj * lot * stt_rate(pd.Timestamp(ts))
    gross_points = entry_cashflow + exit_cashflow
    net = gross_points * lot - 8.0 * brokerage - entry_stt - exit_stt
    return float(gross_points), float(net), float(entry_stt), float(exit_stt)


def marked_path(day_frames, legs, entry_complete, expiry, entry_cashflow):
    rows = []
    for d, day in sorted(day_frames.items()):
        if pd.Timestamp(d).normalize() < pd.Timestamp(entry_complete).normalize():
            continue
        x = day[
            (day.expiry == pd.Timestamp(expiry).normalize())
            & (day.timestamp >= entry_complete)
            & (day.volume > 0)
            & day.close.notna()
        ]
        if x.empty:
            continue
        for typ, strike, qty, label in legs:
            z = x[(x.option_type == typ) & (x.strike == float(strike))][["timestamp", "close"]].copy()
            if not z.empty:
                z["label"] = label
                rows.append(z)
    if not rows:
        return pd.DataFrame(), ["no_mark_rows"]

    allm = pd.concat(rows, ignore_index=True)
    piv = allm.pivot_table(index="timestamp", columns="label", values="close", aggfunc="last").sort_index()
    labels = [x[3] for x in legs]
    missing = [x for x in labels if x not in piv.columns]
    if missing:
        return pd.DataFrame(), missing
    piv = piv.ffill().dropna(subset=labels)
    pnl = np.zeros(len(piv))
    for typ, strike, qty, label in legs:
        pnl += qty * piv[label].to_numpy(float)
    piv["pnl_points"] = pnl + entry_cashflow
    return piv.reset_index().sort_values("timestamp"), []


def exit_variants():
    yield ("expiry_control", None, None, 0)
    for x in FIXED_TARGETS:
        yield ("fixed_target", x, None, 1)
    for x in FIXED_STOPS:
        yield ("fixed_stop", None, x, 1)
    for a, r in TRAIL_TARGETS:
        yield ("trailing_target", a, r, 2)
    for x in TRAIL_STOPS:
        yield ("trailing_stop", None, x, 1)


def complexity(entry_timing, family, offset):
    timing_cost = 1
    exit_cost = {"expiry_control":0,"fixed_target":1,"fixed_stop":1,"trailing_target":2,"trailing_stop":1}[family]
    day_cost = 0
    return timing_cost + exit_cost + day_cost


def evaluate_exit(day_frames, legs, marks, entry_cashflow, max_profit, es95, variant, expiry):
    family, p1, p2, comp = variant
    if family == "expiry_control":
        exits = expiry_exit_marks(day_frames, legs, expiry)
        if exits is None:
            return None, "missing_expiry_exit"
        trigger = None
        mode = "expiry_control"
    else:
        trigger = None
        mode = "expiry_fallback"
        peak = 0.0
        activated = False
        if marks.empty:
            exits = expiry_exit_marks(day_frames, legs, expiry)
            if exits is None:
                return None, "missing_expiry_exit"
        else:
            for row in marks.itertuples(index=False):
                p = float(row.pnl_points)
                ts = pd.Timestamp(row.timestamp)
                if family == "fixed_target":
                    if max_profit > 0 and p >= p1 * max_profit:
                        trigger = ts
                        mode = "fixed_target"
                        break
                elif family == "fixed_stop":
                    if p <= -(p2 * es95):
                        trigger = ts
                        mode = "fixed_stop"
                        break
                elif family == "trailing_target":
                    if not activated and max_profit > 0 and p >= p1 * max_profit:
                        activated = True
                        peak = p
                    elif activated:
                        peak = max(peak, p)
                        if p <= peak - p2 * max_profit:
                            trigger = ts
                            mode = "trailing_target"
                            break
                elif family == "trailing_stop":
                    peak = max(peak, p)
                    if peak > 0 and p <= peak - p1 * max_profit:
                        trigger = ts
                        mode = "trailing_stop"
                        break

            if trigger is not None:
                exits = next_execution(day_frames, legs, trigger, expiry)
                if exits is None:
                    exits = expiry_exit_marks(day_frames, legs, expiry)
                    mode = mode + "_expiry_fallback"
                    if exits is None:
                        return None, "missing_exit_after_trigger_and_expiry"
            else:
                exits = expiry_exit_marks(day_frames, legs, expiry)
                if exits is None:
                    return None, "missing_expiry_fallback"

    exit_time = max(x[5] for x in exits)
    return {
        "trigger_time": str(trigger) if trigger is not None else "",
        "exit_time": str(exit_time),
        "exit_mode": mode,
        "exits": exits,
    }, None


def build_expiry_windows(sessions, expiry):
    pos = sessions.get_loc(pd.Timestamp(expiry).normalize())
    earliest = sessions[max(0, pos - 7):pos + 1]
    return list(earliest)


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
    daily = daily.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
    spot0930["date"] = pd.to_datetime(spot0930.date).dt.normalize()
    spot_map = dict(zip(spot0930.date.dt.date, pd.to_numeric(spot0930.spot_0930, errors="coerce")))

    sessions = pd.DatetimeIndex(daily.date.unique()).sort_values()
    expiry_dates = sorted(pd.to_datetime(cal.expiry).dropna().unique())
    expiry_dates = [pd.Timestamp(x).normalize() for x in expiry_dates if pd.Timestamp("2020-01-01") <= pd.Timestamp(x) <= pd.Timestamp("2024-10-31")]
    file_map = dict(zip(fmap.trade_date.dt.normalize(), fmap.member))

    all_rows = []
    skips = defaultdict(int)

    with zipfile.ZipFile(ayush_zip) as zf:
        day_cache = {}

        for exp_i, expiry in enumerate(expiry_dates, 1):
            if expiry not in sessions:
                continue
            pos = sessions.get_loc(expiry)
            if pos < 1:
                continue

            # Need D0-D6 and one prior signal day for D6 evening.
            window_dates = list(sessions[max(0, pos - 7):pos + 1])
            day_frames = {}
            missing_window = False
            for d in window_dates:
                member = file_map.get(pd.Timestamp(d).normalize())
                if member is None:
                    missing_window = True
                    break
                if d not in day_cache:
                    day_cache[d] = load_option_day(zf, member)
                day_frames[d] = day_cache[d]
            if missing_window:
                skips["missing_window_file"] += 1
                continue

            for offset in range(7):
                if pos - offset < 0:
                    continue
                decision = sessions[pos - offset]
                if decision < pd.Timestamp("2020-01-01") or decision > pd.Timestamp("2024-10-31"):
                    continue
                prior = sessions[pos - offset - 1] if pos - offset - 1 >= 0 else None

                for timing in ("prior_evening_to_open", "same_session_0930"):
                    if timing == "prior_evening_to_open":
                        if prior is None:
                            continue
                        signal_date = prior
                        signal_day = day_frames.get(prior)
                        exec_day = day_frames.get(decision)
                        spot = daily.loc[daily.date == signal_date, "close"].iloc[0]
                        signal_cut = signal_date + pd.Timedelta(hours=15, minutes=30)
                        execution_start = decision + pd.Timedelta(hours=9, minutes=15)
                        strict = False
                        mc_end = signal_date
                        horizon = max(1, offset + 1)
                    else:
                        s0930 = spot_map.get(decision.date())
                        signal_date = decision
                        signal_day = day_frames.get(decision)
                        exec_day = day_frames.get(decision)
                        if s0930 is None or not np.isfinite(s0930):
                            skips["missing_0930_spot"] += 1
                            continue
                        spot = float(s0930)
                        signal_cut = decision + pd.Timedelta(hours=9, minutes=30)
                        execution_start = signal_cut
                        strict = True
                        mc_end = sessions[pos - offset - 1] if pos - offset - 1 >= 0 else sessions[0]
                        horizon = max(1, offset)

                    hist = daily.loc[daily.date <= mc_end, "close"].astype(float)
                    returns = np.log(hist).diff().dropna().tail(756).to_numpy(float)
                    if len(returns) < 756:
                        skips["insufficient_756_returns"] += 1
                        continue

                    key = f"{expiry.date()}|{decision.date()}|{offset}|{timing}"
                    terminals = mc_terminal(spot, returns, horizon, args.paths, deterministic_seed(args.seed_base, key))
                    targets = {
                        "p20": float(np.quantile(terminals, 0.20)),
                        "p35": float(np.quantile(terminals, 0.35)),
                        "c65": float(np.quantile(terminals, 0.65)),
                        "c80": float(np.quantile(terminals, 0.80)),
                    }

                    available = signal_day[
                        (signal_day.expiry == expiry)
                        & (signal_day.timestamp <= signal_cut)
                        & (signal_day.volume > 0)
                        & signal_day.strike.notna()
                    ].strike.unique()
                    strikes = unique_strikes(available, targets)
                    if strikes is None:
                        skips["insufficient_strike_grid"] += 1
                        continue

                    legs = batman_legs(strikes)
                    entry_legs = []
                    entry_cashflow = 0.0
                    entry_complete = None
                    valid = True
                    for typ, strike, qty, label in legs:
                        ep = get_execution_price(exec_day, expiry, typ, strike, execution_start, strict)
                        if ep is None:
                            valid = False
                            skips[f"missing_entry_{label}"] += 1
                            break
                        raw_px, ts = ep
                        entry_legs.append((typ, strike, qty, label, raw_px, ts))
                        entry_cashflow -= qty * entry_price_adjusted(raw_px, qty)
                        entry_complete = ts if entry_complete is None or ts > entry_complete else entry_complete
                    if not valid:
                        continue

                    pnl_mc = np.zeros(args.paths)
                    for typ, strike, qty, label in legs:
                        intrinsic = np.maximum(terminals - strike, 0.0) if typ == "CE" else np.maximum(strike - terminals, 0.0)
                        pnl_mc += qty * intrinsic
                    pnl_mc += entry_cashflow
                    mc_ev = float(pnl_mc.mean())
                    if mc_ev <= 0:
                        skips["gross_mc_gate_failed"] += 1
                        continue

                    q05 = float(np.quantile(pnl_mc, 0.05))
                    es95 = float(max(0.0, -np.mean(pnl_mc[pnl_mc <= q05]))) if np.any(pnl_mc <= q05) else 0.0
                    max_profit = max_profit_reference(legs, entry_cashflow)

                    marks, missing_labels = marked_path(
                        day_frames,
                        legs,
                        entry_complete,
                        expiry,
                        entry_cashflow,
                    )
                    if marks.empty and missing_labels:
                        skips["incomplete_mark_path"] += 1

                    for variant in exit_variants():
                        family, p1, p2, comp = variant
                        exit_result, reason = evaluate_exit(
                            day_frames,
                            legs,
                            marks,
                            entry_cashflow,
                            max_profit,
                            es95,
                            variant,
                            expiry,
                        )
                        if exit_result is None:
                            skips[reason] += 1
                            continue

                        for brokerage in BROKERAGES:
                            gross_points, net_inr, entry_stt, exit_stt = realized_net(
                                entry_cashflow,
                                entry_legs,
                                exit_result["exits"],
                                expiry,
                                brokerage,
                            )
                            all_rows.append(
                                {
                                    "decision_date": decision.date().isoformat(),
                                    "expiry": expiry.date().isoformat(),
                                    "entry_offset": offset,
                                    "entry_timing": timing,
                                    "exit_family": family,
                                    "target_param": p1,
                                    "stop_param": p1 if family == "fixed_stop" or family == "trailing_stop" else None,
                                    "activation_param": p1 if family == "trailing_target" else None,
                                    "retracement_param": p2 if family == "trailing_target" else None,
                                    "brokerage_per_order_inr": brokerage,
                                    "lot_size": lot_size(expiry),
                                    "mc_ev_points": mc_ev,
                                    "mc_es95_points": es95,
                                    "max_profit_reference_points": max_profit,
                                    "entry_complete": str(entry_complete),
                                    "trigger_time": exit_result["trigger_time"],
                                    "exit_time": exit_result["exit_time"],
                                    "exit_mode": exit_result["exit_mode"],
                                    "realized_gross_points": gross_points,
                                    "realized_net_inr": net_inr,
                                    "entry_stt_inr": entry_stt,
                                    "exit_stt_inr": exit_stt,
                                    "gross_gate": 1,
                                }
                            )

            if exp_i % 25 == 0:
                print(f"T7 expiries {exp_i}/{len(expiry_dates)}", flush=True)

    trades = pd.DataFrame(all_rows)
    if trades.empty:
        raise SystemExit("No T7 rows generated.")

    trades["decision_date"] = pd.to_datetime(trades.decision_date)
    trades["expiry"] = pd.to_datetime(trades.expiry)
    trades["year"] = trades.decision_date.dt.year

    summary = (
        trades.groupby(
            ["entry_offset","entry_timing","exit_family","target_param","stop_param","activation_param","retracement_param","brokerage_per_order_inr"],
            dropna=False,
        )
        .agg(
            trades=("realized_net_inr","size"),
            unique_decision_dates=("decision_date","nunique"),
            total_net_inr=("realized_net_inr","sum"),
            mean_net_inr=("realized_net_inr","mean"),
            median_net_inr=("realized_net_inr","median"),
            win_rate=("realized_net_inr", lambda s: float((s>0).mean())),
        )
        .reset_index()
    )

    trades.to_csv(out/"T7_JOINT_TRADE_LEVEL.csv", index=False)
    summary.to_csv(out/"T7_JOINT_SUMMARY.csv", index=False)
    Path(out/"T7_SKIP_COUNTS.json").write_text(json.dumps(skips, indent=2)+"\n")
    print(summary.sort_values("total_net_inr",ascending=False).head(50).to_string(index=False))
    print("SKIPS",json.dumps(skips,indent=2))


if __name__ == "__main__":
    main()
