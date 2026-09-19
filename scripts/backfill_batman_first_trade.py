from __future__ import annotations

import json
import math
import re
from pathlib import Path
from datetime import date
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from curl_cffi import requests

from batman_signal_producer import (
    LEDGER_COLUMNS,
    SIGNAL_COLUMNS,
    build_batman_signal,
    build_site,
    read_csv_or_empty,
)

IST = ZoneInfo("Asia/Kolkata")
CUTOFF = pd.Timestamp("2026-09-16")
ENTRY = pd.Timestamp("2026-09-17")
EXPIRY = pd.Timestamp("2026-09-22")
LOT_SIZE = 65
CAPITAL = 100000.0
RISK_PCT = 0.02
PATHS = 5000
LOOKBACK = 756
COST_PER_CONTRACT = 2.0
SEED = 20260919

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/136.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.indiainfoline.com/",
}

def fetch_nifty_history() -> pd.DataFrame:
    s = requests.Session(impersonate="chrome")
    period1 = int(pd.Timestamp("2018-01-01", tz=IST).timestamp())
    period2 = int(pd.Timestamp("2026-09-17", tz=IST).timestamp())
    r = s.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI",
        params={"period1": period1, "period2": period2, "interval": "1d", "events": "history", "includeAdjustedClose": "true"},
        timeout=45,
    )
    r.raise_for_status()
    payload = r.json()
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError("Yahoo returned no NIFTY history")
    timestamps = result.get("timestamp") or []
    closes = (((result.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
    rows = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        d = pd.Timestamp(ts, unit="s", tz="UTC").tz_convert(IST).normalize().tz_localize(None)
        rows.append({"date": d, "close": float(close)})
    df = pd.DataFrame(rows).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    df = df[df["date"] <= CUTOFF].copy()
    if len(df) < LOOKBACK + 1:
        raise RuntimeError(f"Need at least {LOOKBACK+1} NIFTY closes through {CUTOFF.date()}, found {len(df)}")
    return df

def mc_paths(spot: float, returns: np.ndarray, horizon_sessions: int, paths: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sampled = rng.choice(returns, size=paths * horizon_sessions, replace=True).reshape(paths, horizon_sessions)
    return spot * np.exp(sampled.sum(axis=1))

def fetch_prev_close(option_type: str, strike: float) -> tuple[float, str]:
    strike_int = int(round(strike))
    url = f"https://www.indiainfoline.com/markets/derivatives/option-chain/nifty/22-09-2026-{option_type.lower()}-{strike_int}"
    s = requests.Session(impersonate="chrome")
    s.headers.update(HEADERS)
    r = s.get(url, timeout=45)
    r.raise_for_status()
    text = re.sub(r"\\s+", " ", r.text)
    m = re.search(r"Prev\\. Close.*?₹\\s*([0-9,]+(?:\\.[0-9]+)?)", text, flags=re.I)
    if not m:
        # Fallback: search HTML text around the label after stripping tags.
        stripped = re.sub(r"<[^>]+>", " ", r.text)
        stripped = re.sub(r"\\s+", " ", stripped)
        m = re.search(r"Prev\\. Close\\s+₹\\s*([0-9,]+(?:\\.[0-9]+)?)", stripped, flags=re.I)
    if not m:
        raise RuntimeError(f"Unable to parse previous close from {url}")
    px = float(m.group(1).replace(",", ""))
    return px, url

def main():
    history = fetch_nifty_history()
    cutoff_spot = float(history.loc[history["date"].eq(CUTOFF), "close"].iloc[-1])
    returns = np.log(history["close"]).diff().dropna().tail(LOOKBACK).to_numpy(float)
    terminal = mc_paths(cutoff_spot, returns, 3, PATHS, SEED)

    qs = np.percentile(terminal, [20, 35, 65, 80])
    # NIFTY strikes are 50-point spaced in this series; map to nearest listed-like levels.
    raw_targets = {"p20": qs[0], "p35": qs[1], "c65": qs[2], "c80": qs[3]}
    available = np.arange(21000.0, 25501.0, 50.0)
    used = set()
    strikes = {}
    for label, target in sorted(raw_targets.items(), key=lambda kv: kv[1]):
        for candidate in available[np.argsort(np.abs(available - target))]:
            if float(candidate) not in used:
                strikes[label] = float(candidate)
                used.add(float(candidate))
                break

    rows = []
    print(json.dumps({"cutoff_spot": cutoff_spot, "terminal_quantiles": qs.tolist(), "raw_targets": raw_targets, "mapped_strikes": strikes}, indent=2))
    for label, typ in [("p20", "PE"), ("p35", "PE"), ("c65", "CE"), ("c80", "CE")]:
        px, url = fetch_prev_close(typ, strikes[label])
        rows.append({
            "expiry": EXPIRY,
            "strike": strikes[label],
            "option_type": typ,
            "last_price": px,
            "bid": np.nan,
            "ask": np.nan,
            "open_interest": np.nan,
            "volume": np.nan,
            "source_url": url,
        })
    chain = pd.DataFrame(rows)

    metrics = build_batman_signal(
        cutoff_spot,
        terminal,
        chain[["expiry","strike","option_type","last_price","bid","ask","open_interest","volume"]],
        EXPIRY,
        LOT_SIZE,
        CAPITAL,
        RISK_PCT,
        COST_PER_CONTRACT,
    )

    ledger_path = Path("paper_trading/batman_ledger.csv")
    signals_path = Path("paper_trading/batman_signals.csv")
    ledger = read_csv_or_empty(ledger_path, LEDGER_COLUMNS)
    signals = read_csv_or_empty(signals_path, SIGNAL_COLUMNS)

    signal_id = f"{ENTRY.date().isoformat()}|{EXPIRY.date().isoformat()}|Batman"
    signal_row = {
        "run_timestamp_ist": pd.Timestamp.now(tz=IST).isoformat(),
        "decision_date": ENTRY.date().isoformat(),
        "target_expiry": EXPIRY.date().isoformat(),
        "status": "BACKFILL_ENTRY_DAY",
        "signal": metrics["signal"],
        "spot": cutoff_spot,
        "spot_source": "Yahoo Finance ^NSEI; data cutoff 2026-09-16",
        "mc_paths": PATHS,
        "lookback_sessions": LOOKBACK,
        "horizon_sessions": 3,
        "p20_terminal": metrics["p20_terminal"],
        "p35_terminal": metrics["p35_terminal"],
        "p65_terminal": metrics["p65_terminal"],
        "p80_terminal": metrics["p80_terminal"],
        "p20_strike": strikes["p20"],
        "p35_strike": strikes["p35"],
        "c65_strike": strikes["c65"],
        "c80_strike": strikes["c80"],
        "mc_ev_points_gross": metrics["mc_expected_pnl_points_gross"],
        "entry_cost_points": metrics["entry_cost_points"],
        "mc_ev_points_net": metrics["mc_expected_pnl_points_net"],
        "mc_pop": metrics["mc_probability_profit"],
        "mc_es95_points": metrics["mc_es95_points"],
        "mc_es99_points": metrics["mc_es99_points"],
        "lot_size": LOT_SIZE,
        "contracts_per_strategy_lot": metrics["contracts_per_strategy_lot"],
        "risk_points_per_lot": metrics["risk_points_per_lot"],
        "risk_budget_inr": metrics["risk_budget_inr"],
        "estimated_risk_inr_per_lot": metrics["estimated_risk_inr_per_lot"],
        "minimum_capital_for_one_lot_inr": metrics["minimum_capital_for_one_lot_inr"],
        "recommended_lots": metrics["recommended_lots"],
        "entry_cashflow_points_per_unit": metrics["entry_cashflow_points_per_unit"],
        "entry_price_source": "IIFL previous close (2026-09-17 entry proxy)",
        "signal_id": signal_id,
        "notes": "RETROACTIVE PAPER-TRADE BACKFILL: MC data cutoff 2026-09-16; expiry 2026-09-22; 3 future trading sessions from 2026-09-17. Entry option prices use 2026-09-17 close via IIFL Friday pages' Prev. Close fields; this is a reconstructed paper entry, not an executable historical quote.",
    }

    if signal_id not in set(signals.get("signal_id", pd.Series(dtype=str)).astype(str)):
        signals = pd.concat([signals, pd.DataFrame([signal_row])], ignore_index=True)
        signals.to_csv(signals_path, index=False)

    if signal_id not in set(ledger.get("signal_id", pd.Series(dtype=str)).astype(str)):
        ledger_row = {
            "signal_id": signal_id,
            "decision_date": ENTRY.date().isoformat(),
            "expiry": EXPIRY.date().isoformat(),
            "strategy": "Batman",
            "signal": metrics["signal"],
            "spot": cutoff_spot,
            "lot_size": LOT_SIZE,
            "lots": metrics["recommended_lots"],
            "risk_budget_inr": metrics["risk_budget_inr"],
            "mc_ev_points_net": metrics["mc_expected_pnl_points_net"],
            "mc_pop": metrics["mc_probability_profit"],
            "es95_points": metrics["mc_es95_points"],
            "es99_points": metrics["mc_es99_points"],
            "entry_cost_points": metrics["entry_cost_points"],
            "entry_cashflow_points_per_unit": metrics["entry_cashflow_points_per_unit"],
            "legs_json": json.dumps(metrics["legs"], separators=(",", ":")),
            "status": "OPEN" if metrics["signal"] == "ENTER" and metrics["recommended_lots"] >= 1 else "NO_TRADE",
            "exit_date": "",
            "exit_spot": "",
            "exit_intrinsic_points_per_unit": "",
            "realized_pnl_points_per_unit": "",
            "realized_pnl_inr": "",
            "notes": signal_row["notes"],
        }
        ledger = pd.concat([ledger, pd.DataFrame([ledger_row])], ignore_index=True)
        ledger.to_csv(ledger_path, index=False)

    latest = {
        "producer": "Batman Signal Producer — retrospective first-trade backfill",
        "strategy": "Batman",
        "run_timestamp_ist": signal_row["run_timestamp_ist"],
        "decision_date": ENTRY.date().isoformat(),
        "target_expiry": EXPIRY.date().isoformat(),
        "status": signal_row["status"],
        **metrics,
        "spot": cutoff_spot,
        "spot_source": signal_row["spot_source"],
        "mc_paths": PATHS,
        "lookback_sessions": LOOKBACK,
        "horizon_sessions": 3,
        "data_cutoff": CUTOFF.date().isoformat(),
        "entry_price_source": signal_row["entry_price_source"],
        "notes": signal_row["notes"],
    }
    build_site(Path("site"), latest, signals, ledger)
    Path("site/data/producer_metadata.json").write_text(
        json.dumps({
            "mode": "retrospective-first-trade-backfill",
            "model_data_cutoff": CUTOFF.date().isoformat(),
            "paper_entry_date": ENTRY.date().isoformat(),
            "expiry": EXPIRY.date().isoformat(),
            "paths": PATHS,
            "lookback": LOOKBACK,
            "seed": SEED,
            "option_price_source": "IIFL previous close fields representing 2026-09-17 close",
        }, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "signal": metrics["signal"],
        "recommended_lots": metrics["recommended_lots"],
        "spot_cutoff": cutoff_spot,
        "terminal_quantiles": qs.tolist(),
        "strikes": strikes,
        "legs": metrics["legs"],
        "mc_ev_net": metrics["mc_expected_pnl_points_net"],
        "mc_pop": metrics["mc_probability_profit"],
        "es95": metrics["mc_es95_points"],
        "es99": metrics["mc_es99_points"],
    }, indent=2, default=str))

if __name__ == "__main__":
    main()
