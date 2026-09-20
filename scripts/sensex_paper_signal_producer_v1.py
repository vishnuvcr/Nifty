from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nifty_mc.strategy_catalog import build_strategy
from scripts.sensex_backtest_v1 import (
    CANDIDATES_BY_REGIME,
    compute_regime,
    map_unique_strikes,
    mc_terminal,
    strategy_targets,
    transaction_costs,
)

IST = timezone(timedelta(hours=5, minutes=30))
LOT_SIZE = 20
CAPITAL_INR = 100_000.0
RISK_BUDGET_INR = CAPITAL_INR * 0.02
SLIPPAGE_POINTS = 0.50
MC_PATHS = 5000
LOOKBACK = 756
RANK_LOOKBACK = 252
DEFAULT_SEED = 20260920

BSE_BASE = "https://api.bseindia.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/134 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}
INDEX_HISTORY_URL = f"{BSE_BASE}/BseIndiaAPI/api/ProduceCSVForDate/w"
LIVE_SENSEX_URLS = (
    f"{BSE_BASE}/RealTimeBseIndiaAPI/api/GetSensexData/w",
    f"{BSE_BASE}/BseIndiaAPI/api/GetSensexDataN/w?code=84",
)
OPTION_CHAIN_TEMPLATES = (
    f"{BSE_BASE}/BseIndiaAPI/api/DerivOptionChain/w",
    f"{BSE_BASE}/BseIndiaAPI/api/DerivativesChain/w",
)

def now_ist() -> datetime:
    return datetime.now(IST)

def is_trading_weekday(d: datetime) -> bool:
    return d.weekday() < 5

def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

def append_unique(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()
    ids = existing["signal_id"].astype(str).tolist() if "signal_id" in existing.columns else []
    if str(row["signal_id"]) in ids:
        return
    pd.DataFrame([row]).to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)

def append_error(message: str, timestamp: datetime) -> None:
    log = ROOT / "docs/sensex_options/ERROR_LOG.md"
    text = log.read_text(encoding="utf-8") if log.exists() else "# SENSEX Options Research Error Log\n"
    stamp = timestamp.isoformat()
    entry = (
        f"\n### S7 runtime scanner event — {stamp}\n"
        f"Type: prospective scanner\n"
        f"Observation: {message}\n"
        f"Resolution: emitted NO_TRADE paper-trading state; no broker order was attempted.\n"
        f"Prevention: live-data/schema failures remain hard stops for entry eligibility; no LTP fallback is used.\n"
    )
    if stamp not in text:
        log.write_text(text.rstrip() + entry + "\n", encoding="utf-8")

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
    raw = r.text.strip()
    try:
        payload = r.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        data = payload.get("Data") or payload.get("data") or payload.get("Table")
        if isinstance(data, list):
            return normalize_history(pd.DataFrame(data))
        if isinstance(data, str):
            raw = data
    if not raw or "<" in raw[:100]:
        raise ValueError("BSE SENSEX history endpoint returned non-tabular data")
    return normalize_history(pd.read_csv(io.StringIO(raw)))

def normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    lookup = {str(c).strip().lower(): c for c in df.columns}
    date_col = next((lookup[k] for k in ("date", "dt", "trading date") if k in lookup), None)
    close_col = next((lookup[k] for k in ("close", "close price", "closing price") if k in lookup), None)
    if date_col is None or close_col is None:
        raise ValueError(f"unrecognized BSE SENSEX history schema: {list(df.columns)}")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True).dt.normalize(),
        "close": pd.to_numeric(df[close_col], errors="coerce"),
    })
    return out.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)

def future_session_expiry(history: pd.DataFrame, decision_date: pd.Timestamp) -> pd.Timestamp:
    sessions = pd.DatetimeIndex(history.loc[history["date"] > decision_date, "date"].sort_values().unique())
    if len(sessions) < 3:
        raise RuntimeError("fewer than three future SENSEX trading sessions available")
    return pd.Timestamp(sessions[2]).normalize()

def fetch_live_sensex() -> dict[str, Any]:
    errors: list[str] = []
    for url in LIVE_SENSEX_URLS:
        try:
            data = request_json(url)
            if isinstance(data, dict):
                if isinstance(data.get("Data"), list) and data["Data"]:
                    data = data["Data"][0]
                return data
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("BSE live SENSEX endpoint unavailable; " + " | ".join(errors))

def recursive_records(obj: Any, inherited: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    inherited = dict(inherited or {})
    if isinstance(obj, list):
        out: list[dict[str, Any]] = []
        for item in obj:
            out.extend(recursive_records(item, inherited))
        return out
    if not isinstance(obj, dict):
        return []
    out: list[dict[str, Any]] = []
    merged = dict(inherited)
    for key, value in obj.items():
        lk = str(key).lower().replace("_", "")
        if lk in {"strike", "strikeprice", "strikepricevalue"}:
            merged["strike"] = value
        elif lk in {"expiry", "expirydate"}:
            merged["expiry"] = value
        elif lk in {"optiontype", "putorcall"}:
            merged["option_type"] = value

    scalar = {str(k): v for k, v in obj.items() if not isinstance(v, (dict, list))}
    keys = {str(k).lower() for k in obj}
    if any("strike" in k for k in keys):
        if any("bid" in k or "offer" in k or "ask" in k for k in keys) or "ce" in keys or "pe" in keys:
            row = dict(merged)
            row.update(scalar)
            emitted = False
            for side_key, option_type in (("CE", "CE"), ("PE", "PE")):
                if isinstance(obj.get(side_key), dict):
                    child = dict(merged)
                    child.update({str(k): v for k, v in obj[side_key].items() if not isinstance(v, (dict, list))})
                    child["option_type"] = option_type
                    out.append(child)
                    emitted = True
            if not emitted:
                out.append(row)

    for key, value in obj.items():
        if isinstance(value, (dict, list)):
            child = dict(merged)
            lk = str(key).lower()
            if lk in {"ce", "call"}:
                child["option_type"] = "CE"
            elif lk in {"pe", "put"}:
                child["option_type"] = "PE"
            out.extend(recursive_records(value, child))
    return out

def canonical_option_rows(payload: Any) -> pd.DataFrame:
    raw = recursive_records(payload)
    if not raw:
        raise ValueError("BSE option-chain response contained no option records")
    df = pd.DataFrame(raw)
    normalized = {str(c).lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    def pick(*names: str) -> str | None:
        for name in names:
            key = name.lower().replace(" ", "").replace("_", "")
            if key in normalized:
                return normalized[key]
        return None
    strike_col = pick("strike", "strikeprice")
    expiry_col = pick("expiry", "expirydate")
    type_col = pick("option_type", "optiontype", "putorcall")
    bid_col = pick("bid", "bidprice")
    ask_col = pick("ask", "askprice", "offerprice", "offer")
    if not all([strike_col, expiry_col, type_col, bid_col, ask_col]):
        raise ValueError(f"BSE option-chain schema missing strike/expiry/type/bid/ask: {list(df.columns)}")
    out = pd.DataFrame({
        "strike": pd.to_numeric(df[strike_col], errors="coerce"),
        "expiry": pd.to_datetime(df[expiry_col], errors="coerce", dayfirst=True).dt.normalize(),
        "option_type": df[type_col].astype(str).str.upper().replace({"CALL": "CE", "PUT": "PE", "1": "CE", "0": "PE"}),
        "bid": pd.to_numeric(df[bid_col], errors="coerce"),
        "ask": pd.to_numeric(df[ask_col], errors="coerce"),
    })
    out = out.loc[out["option_type"].isin(["CE", "PE"])].dropna(subset=["strike", "expiry"])
    out = out.loc[(out["bid"] > 0) & (out["ask"] > 0) & (out["ask"] >= out["bid"])]
    out = out.drop_duplicates(["expiry", "option_type", "strike"]).sort_values(["expiry", "strike", "option_type"])
    if out.empty:
        raise ValueError("BSE option-chain contained no executable bid/ask quotes")
    return out.reset_index(drop=True)

def fetch_option_chain(expiry: pd.Timestamp) -> pd.DataFrame:
    explicit = os.getenv("BSE_OPTION_CHAIN_URL")
    urls = (explicit,) if explicit else OPTION_CHAIN_TEMPLATES
    param_variants = [
        {"flag": "0", "expirydate": expiry.strftime("%d-%b-%Y").upper(), "scripcode": "84"},
        {"flag": "0", "expiryDate": expiry.strftime("%d-%b-%Y").upper(), "scripcode": "84"},
        {"flag": "0", "expirydate": expiry.strftime("%d-%b-%Y").upper(), "scripcode": "16"},
    ]
    errors: list[str] = []
    for url in urls:
        for params in param_variants:
            try:
                payload = request_json(url, params=params)
                chain = canonical_option_rows(payload)
                scoped = chain.loc[chain["expiry"].eq(expiry)].copy()
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

def live_strategy_eval(
    strategy: str,
    terminal: np.ndarray,
    spot: float,
    chain: pd.DataFrame,
    expiry: pd.Timestamp,
    entry_date: pd.Timestamp,
    seed: int,
) -> dict[str, Any]:
    targets = strategy_targets(strategy, terminal, spot)
    strikes = map_unique_strikes(chain.rename(columns={"bid": "open", "ask": "close"}), targets)
    legs = build_strategy(strategy, strikes)
    priced: list[dict[str, Any]] = []
    entry_cashflow = 0.0
    contracts = 0
    for leg in legs:
        side = "BUY" if leg.qty > 0 else "SELL"
        px = quote_for_leg(chain, leg.option_type, float(leg.strike), side)
        match = chain.loc[
            chain["option_type"].eq(leg.option_type)
            & np.isclose(chain["strike"].to_numpy(float), float(leg.strike), atol=1e-9)
        ].iloc[0]
        entry_cashflow -= float(leg.qty) * px
        contracts += abs(int(leg.qty))
        priced.append({
            "side": side,
            "option_type": leg.option_type,
            "strike": float(leg.strike),
            "qty": int(leg.qty),
            "quantity_per_lot": abs(int(leg.qty)),
            "premium_points": px,
            "bid": float(match["bid"]),
            "ask": float(match["ask"]),
            "expiry": str(expiry.date()),
        })

    gross = np.zeros_like(terminal, dtype=float) + entry_cashflow
    for leg in priced:
        intrinsic = (
            np.maximum(terminal - leg["strike"], 0.0)
            if leg["option_type"] == "CE"
            else np.maximum(leg["strike"] - terminal, 0.0)
        )
        gross += float(leg["qty"]) * intrinsic

    expected_cost_inr, entry_cost_inr = transaction_costs(
        entry_date, priced, LOT_SIZE, entry_cashflow, terminal
    )
    net = gross - expected_cost_inr / LOT_SIZE
    q05 = float(np.quantile(net, 0.05))
    q01 = float(np.quantile(net, 0.01))
    es95 = float(max(0.0, -np.mean(net[net <= q05])))
    es99 = float(max(0.0, -np.mean(net[net <= q01])))
    risk_points = max(es95, es99)
    ev = float(np.mean(net))
    eligible = ev > 0
    return {
        "strategy": strategy,
        "strikes_json": json.dumps(strikes, sort_keys=True),
        "legs_json": json.dumps(priced, sort_keys=True),
        "entry_cashflow_points_per_unit": float(entry_cashflow),
        "mc_ev_points_net": ev,
        "mc_pop": float(np.mean(net > 0)),
        "es95_points": es95,
        "es99_points": es99,
        "risk_points_per_lot": risk_points,
        "recommended_lots": 1 if eligible else 0,
        "contract_count": contracts,
        "eligible": eligible,
        "entry_cost_inr_expected": float(expected_cost_inr),
        "entry_cost_inr_entry_only": float(entry_cost_inr),
        "mc_seed": int(seed),
    }

def make_signal_row(
    requested_strategy: str,
    evaluation: dict[str, Any],
    decision_date: pd.Timestamp,
    expiry: pd.Timestamp,
    regime: dict[str, Any],
    spot: float,
    timestamp: datetime,
    model_cutoff: pd.Timestamp,
) -> dict[str, Any]:
    signal = "ENTER" if evaluation.get("eligible") else "NO_TRADE"
    return {
        "signal_id": f"{decision_date.date()}|{expiry.date()}|{requested_strategy}",
        "decision_date": str(decision_date.date()),
        "expiry": str(expiry.date()),
        "strategy": requested_strategy,
        "signal": signal,
        "regime": regime["vol_regime"],
        "spot": spot,
        "lot_size": LOT_SIZE,
        "lots": int(evaluation.get("recommended_lots", 0)),
        "risk_budget_inr": RISK_BUDGET_INR,
        "mc_ev_points_net": float(evaluation.get("mc_ev_points_net", np.nan)),
        "mc_pop": float(evaluation.get("mc_pop", np.nan)),
        "es95_points": float(evaluation.get("es95_points", np.nan)),
        "es99_points": float(evaluation.get("es99_points", np.nan)),
        "entry_slippage_points": SLIPPAGE_POINTS,
        "entry_cost_inr_expected": float(evaluation.get("entry_cost_inr_expected", np.nan)),
        "entry_cashflow_points_per_unit": float(evaluation.get("entry_cashflow_points_per_unit", np.nan)),
        "legs_json": evaluation.get("legs_json", "[]"),
        "entry_timestamp_ist": timestamp.isoformat(),
        "model_data_cutoff": str(model_cutoff.date()),
        "quote_retrieved_at_ist": timestamp.isoformat(),
        "status": "OPEN" if signal == "ENTER" else "NO_TRADE",
        "notes": "Prospective S7 paper trade; one-lot transfer-edge mode; no broker order.",
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["Batman", "Adaptive"], required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()

    ts = now_ist()
    ledger = Path(args.ledger)
    output = Path(args.output_json)

    if not is_trading_weekday(ts):
        write_json(output, {
            "status": "NO_TRADE",
            "reason": "non_trading_weekday",
            "timestamp_ist": ts.isoformat(),
        })
        return 0

    decision_date = pd.Timestamp(ts.date()).normalize()
    try:
        history = fetch_index_history(
            decision_date - pd.Timedelta(days=2200),
            decision_date - pd.Timedelta(days=1),
        )
        if len(history) < LOOKBACK + 1:
            raise RuntimeError(f"insufficient SENSEX history for prospective MC: {len(history)} rows")

        cutoff = pd.Timestamp(history["date"].max())
        returns = np.log(history["close"]).diff().dropna().to_numpy(float)
        live = fetch_live_sensex()
        spot = next(
            (
                float(live[key])
                for key in ("LTP", "CurrValue", "ltp", "Currvalue")
                if key in live and str(live[key]) not in {"", "None"}
            ),
            None,
        )
        if spot is None or not np.isfinite(spot):
            raise RuntimeError(f"could not parse live SENSEX spot from keys: {list(live)}")

        expiry = future_session_expiry(history, decision_date)
        chain = fetch_option_chain(expiry)
        terminal = mc_terminal(returns, spot, 3, MC_PATHS, args.seed)
        regime = compute_regime(history, cutoff, RANK_LOOKBACK)

        candidates: list[dict[str, Any]] = []
        for candidate in CANDIDATES_BY_REGIME[regime["vol_regime"]]:
            try:
                candidates.append(
                    live_strategy_eval(candidate, terminal, spot, chain, expiry, decision_date, args.seed)
                )
            except Exception as exc:
                candidates.append({
                    "strategy": candidate,
                    "eligible": False,
                    "error": str(exc),
                })

        if args.strategy == "Batman":
            chosen = live_strategy_eval("Batman", terminal, spot, chain, expiry, decision_date, args.seed)
            selected_candidate = "Batman"
        else:
            eligible = [x for x in candidates if x.get("eligible")]
            if not eligible:
                chosen = {
                    "strategy": "Adaptive",
                    "eligible": False,
                    "recommended_lots": 0,
                    "error": "no eligible candidate in frozen regime candidate set",
                    "candidate_screen": candidates,
                    "mc_ev_points_net": np.nan,
                    "mc_pop": np.nan,
                    "es95_points": np.nan,
                    "es99_points": np.nan,
                    "entry_cost_inr_expected": np.nan,
                    "entry_cashflow_points_per_unit": np.nan,
                    "legs_json": "[]",
                }
                selected_candidate = "NONE"
            else:
                chosen = sorted(
                    eligible,
                    key=lambda x: (-float(x["mc_ev_points_net"]), str(x["strategy"]))
                )[0]
                selected_candidate = str(chosen["strategy"])
                chosen = dict(chosen)
                chosen["strategy"] = "Adaptive"

        row = make_signal_row(
            args.strategy, chosen, decision_date, expiry, regime, spot, ts, cutoff
        )
        row["selected_candidate"] = selected_candidate
        row["candidate_screen_json"] = json.dumps(candidates, sort_keys=True, default=str)
        append_unique(ledger, row)
        payload = {
            "status": row["status"],
            "signal": row,
            "candidate_screen": candidates,
            "retrieval": {
                "timestamp_ist": ts.isoformat(),
                "model_cutoff": str(cutoff.date()),
                "expiry": str(expiry.date()),
            },
        }
        write_json(output, payload)
        return 0
    except Exception as exc:
        message = f"{args.strategy}: {type(exc).__name__}: {exc}"
        append_error(message, ts)
        payload = {
            "status": "NO_TRADE",
            "reason": "scanner_error",
            "error": message,
            "timestamp_ist": ts.isoformat(),
        }
        write_json(output, payload)
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
