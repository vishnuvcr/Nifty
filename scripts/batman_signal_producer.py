from __future__ import annotations

import argparse
import html
import json
import math
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from curl_cffi import requests

from nifty_mc.strategy_catalog import build_strategy

IST = ZoneInfo("Asia/Kolkata")
ENTRY_TIME_IST = time(9, 30)
NSE_BASE = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

SIGNAL_COLUMNS = [
    "run_timestamp_ist","entry_timestamp_ist","decision_date","model_data_cutoff","quote_retrieved_at_ist",
    "target_expiry","status","signal",
    "spot","spot_source","mc_paths","lookback_sessions","horizon_sessions",
    "p20_terminal","p35_terminal","p65_terminal","p80_terminal",
    "p20_strike","p35_strike","c65_strike","c80_strike",
    "mc_ev_points_gross","entry_cost_points","mc_ev_points_net","mc_pop",
    "mc_es95_points","mc_es99_points","lot_size","contracts_per_strategy_lot",
    "risk_points_per_lot","risk_budget_inr","estimated_risk_inr_per_lot",
    "minimum_capital_for_one_lot_inr","recommended_lots",
    "entry_cashflow_points_per_unit","entry_price_source","signal_id","notes",
]

LEDGER_COLUMNS = [
    "signal_id","decision_date","expiry","strategy","signal","spot","lot_size",
    "lots","risk_budget_inr","mc_ev_points_net","mc_pop","es95_points",
    "es99_points","entry_cost_points","entry_cashflow_points_per_unit",
    "entry_timestamp_ist","model_data_cutoff","quote_retrieved_at_ist",
    "legs_json","status","exit_date","exit_spot","exit_intrinsic_points_per_unit",
    "realized_pnl_points_per_unit","realized_pnl_inr","notes",
]

def now_ist() -> datetime:
    return datetime.now(IST)

def parse_float(value: object) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None

class NSEClient:
    def __init__(self) -> None:
        self.session = requests.Session(impersonate="chrome")
        self.session.headers.update(NSE_HEADERS)
        self.warmed = False
        self.index_history_source = "NSE"

    def warm(self) -> None:
        if self.warmed:
            return
        # NSE is protected by Akamai bot mitigation. A browser-like TLS
        # fingerprint plus a real page visit is required before API calls.
        page = self.session.get(NSE_BASE + "/option-chain", timeout=30)
        page.raise_for_status()
        warm_api = self.session.get(
            NSE_BASE + "/api/allIndices",
            params={"index": "NIFTY 50"},
            timeout=30,
        )
        warm_api.raise_for_status()
        self.warmed = True

    def get_json(self, path: str, params: dict[str, object] | None = None) -> dict:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                self.warm()
                r = self.session.get(NSE_BASE + path, params=params, timeout=30)
                if r.status_code in {401, 403}:
                    self.warmed = False
                    continue
                r.raise_for_status()
                payload = r.json()
                if not isinstance(payload, dict):
                    raise ValueError("NSE API returned a non-object JSON payload")
                return payload
            except Exception as exc:
                last_error = exc
                self.warmed = False
        raise RuntimeError(f"NSE request failed for {path}: {last_error}")

    def fetch_index_history_yahoo(self, start: date, end: date) -> pd.DataFrame:
        start_ts = int(pd.Timestamp(start, tz=IST).timestamp())
        end_ts = int((pd.Timestamp(end, tz=IST) + pd.Timedelta(days=1)).timestamp())
        r = self.session.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI",
            params={
                "period1": start_ts,
                "period2": end_ts,
                "interval": "1d",
                "events": "history",
                "includeAdjustedClose": "true",
            },
            timeout=30,
        )
        r.raise_for_status()
        payload = r.json()
        result = ((payload.get("chart") or {}).get("result") or [None])[0]
        if not result:
            raise RuntimeError("Yahoo Finance returned no ^NSEI history.")
        timestamps = result.get("timestamp") or []
        closes = (((result.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
        rows = []
        for ts, close in zip(timestamps, closes):
            px = parse_float(close)
            if px is None:
                continue
            local_date = pd.Timestamp(ts, unit="s", tz="UTC").tz_convert(IST).normalize().tz_localize(None)
            rows.append({"date": local_date, "close": px})
        if not rows:
            raise RuntimeError("Yahoo Finance returned no usable ^NSEI closes.")
        return (
            pd.DataFrame(rows)
            .drop_duplicates("date")
            .sort_values("date")
            .reset_index(drop=True)
        )

    def fetch_index_history(self, start: date, end: date) -> pd.DataFrame:
        try:
            chunks: list[pd.DataFrame] = []
            cursor = start
            while cursor <= end:
                chunk_end = min(cursor + timedelta(days=349), end)
                payload = self.get_json(
                    "/api/historical/indicesHistory",
                    params={
                        "indexType": "NIFTY 50",
                        "from": cursor.strftime("%d-%m-%Y"),
                        "to": chunk_end.strftime("%d-%m-%Y"),
                    },
                )
                records = payload.get("data", {}).get("indexCloseOnlineRecords", [])
                if records:
                    df = pd.DataFrame(records)
                    date_col = "EOD_TIMESTAMP" if "EOD_TIMESTAMP" in df.columns else "TIMESTAMP"
                    close_col = "EOD_CLOSE_INDEX_VAL" if "EOD_CLOSE_INDEX_VAL" in df.columns else "CLOSE"
                    if date_col in df.columns and close_col in df.columns:
                        x = pd.DataFrame({
                            "date": pd.to_datetime(df[date_col], errors="coerce"),
                            "close": pd.to_numeric(df[close_col], errors="coerce"),
                        }).dropna()
                        chunks.append(x)
                cursor = chunk_end + timedelta(days=1)
            if not chunks:
                raise RuntimeError("NSE returned no NIFTY 50 index history.")
            out = pd.concat(chunks, ignore_index=True)
            out["date"] = out["date"].dt.normalize()
            out = out.dropna(subset=["date","close"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
            self.index_history_source = "NSE"
            return out
        except Exception as nse_error:
            try:
                out = self.fetch_index_history_yahoo(start, end)
                self.index_history_source = "Yahoo Finance fallback"
                print(f"INDEX_HISTORY_FALLBACK: NSE history failed ({nse_error}); using Yahoo Finance ^NSEI history.")
                return out
            except Exception as yahoo_error:
                raise RuntimeError(
                    f"NIFTY 50 history failed from both NSE and Yahoo Finance. "
                    f"NSE={nse_error}; Yahoo={yahoo_error}"
                )

    def fetch_holidays(self) -> set[pd.Timestamp]:
        payload = self.get_json("/api/holiday-master", params={"type": "trading"})
        records = payload.get("FO") or payload.get("CM") or []
        dates: set[pd.Timestamp] = set()
        for row in records:
            raw = row.get("tradingDate") or row.get("date")
            if raw:
                ts = pd.to_datetime(raw, errors="coerce")
                if not pd.isna(ts):
                    dates.add(pd.Timestamp(ts).normalize())
        return dates

    def fetch_option_chain(
        self, requested_expiry: pd.Timestamp | None = None
    ) -> tuple[pd.DataFrame, float | None, str, pd.Timestamp]:
        # NSE's current v3 flow requires expiry discovery first.
        contract_info = self.get_json(
            "/api/option-chain-contract-info",
            params={"symbol": "NIFTY"},
        )
        raw_expiries = contract_info.get("expiryDates") or []
        expiry_dates = [
            pd.Timestamp(x).normalize()
            for x in raw_expiries
            if not pd.isna(pd.to_datetime(x, errors="coerce"))
        ]
        if not expiry_dates:
            raise RuntimeError("NSE returned no NIFTY option expiry dates.")

        available = set(expiry_dates)
        if requested_expiry is None:
            target_expiry = expiry_dates[0]
        else:
            target_expiry = pd.Timestamp(requested_expiry).normalize()
            if target_expiry not in available:
                available_text = ", ".join(d.date().isoformat() for d in expiry_dates[:10])
                raise RuntimeError(
                    f"Requested expiry {target_expiry.date()} is not available in NSE contract info. "
                    f"Available front expiries: {available_text}"
                )

        expiry_text = target_expiry.strftime("%d-%b-%Y")
        path = "/api/option-chain-v3"
        payload = self.get_json(
            path,
            params={
                "type": "Indices",
                "symbol": "NIFTY",
                "expiry": expiry_text,
            },
        )
        records = payload.get("records", {})
        underlying = parse_float(records.get("underlyingValue"))
        raw = (
            records.get("data")
            or payload.get("data")
            or payload.get("filtered", {}).get("data")
            or []
        )
        rows: list[dict[str, object]] = []
        for rec in raw:
            expiry = pd.to_datetime(rec.get("expiryDate"), errors="coerce")
            strike = parse_float(rec.get("strikePrice"))
            if pd.isna(expiry) or strike is None:
                continue
            for typ in ("CE", "PE"):
                q = rec.get(typ)
                if not isinstance(q, dict):
                    continue
                rows.append({
                    "expiry": pd.Timestamp(expiry).normalize(),
                    "strike": float(strike),
                    "option_type": typ,
                    "last_price": parse_float(q.get("lastPrice")),
                    "bid": parse_float(
                        q.get("bidprice") if q.get("bidprice") is not None else q.get("bidPrice")
                    ),
                    "ask": parse_float(
                        q.get("askPrice") if q.get("askPrice") is not None else q.get("askprice")
                    ),
                    "open_interest": parse_float(q.get("openInterest")),
                    "volume": parse_float(q.get("totalTradedVolume")),
                })
        if not rows:
            raise RuntimeError(
                f"NSE option-chain response contained no CE/PE rows for {expiry_text}."
            )
        return pd.DataFrame(rows), underlying, path, target_expiry

def trading_sessions_between(start: pd.Timestamp, end: pd.Timestamp, holidays: set[pd.Timestamp]) -> pd.DatetimeIndex:
    days = pd.date_range(start.normalize(), end.normalize(), freq="D")
    return pd.DatetimeIndex([d for d in days if d.weekday() < 5 and d.normalize() not in holidays])

def unique_strikes(strikes: np.ndarray, targets: dict[str, float]) -> dict[str, float]:
    available = np.sort(np.unique(np.asarray(strikes, dtype=float)))
    if len(available) < len(targets):
        raise ValueError("Not enough unique strikes to construct Batman.")
    used: set[float] = set()
    result: dict[str, float] = {}
    for label, target in sorted(targets.items(), key=lambda kv: kv[1]):
        for idx in np.argsort(np.abs(available - target)):
            value = float(available[idx])
            if value not in used:
                result[label] = value
                used.add(value)
                break
        else:
            raise ValueError(f"Unable to assign a unique strike for {label}.")
    return result

def side_execution_price(row: pd.Series, side: str) -> tuple[float, str]:
    key = "ask" if side == "BUY" else "bid"
    px = row.get(key)
    if px is not None and math.isfinite(float(px)) and float(px) > 0:
        return float(px), key
    raise ValueError(
        f"Missing executable {key} quote for {row['option_type']} {row['strike']}."
    )

def find_option_row(chain: pd.DataFrame, expiry: pd.Timestamp, option_type: str, strike: float) -> pd.Series:
    mask = (
        chain["expiry"].eq(expiry)
        & chain["option_type"].eq(option_type)
        & np.isclose(chain["strike"].to_numpy(float), float(strike), rtol=0.0, atol=1e-8)
    )
    x = chain.loc[mask]
    if x.empty:
        raise ValueError(f"Missing {option_type} {strike} for expiry {expiry.date()}.")
    return x.iloc[0]

def mc_paths(spot: float, returns: np.ndarray, horizon_sessions: int, paths: int, seed: int) -> np.ndarray:
    clean = returns[np.isfinite(returns)]
    if len(clean) < 60:
        raise ValueError("At least 60 historical daily log returns are required.")
    rng = np.random.default_rng(seed)
    sampled = rng.choice(clean, size=int(paths) * int(horizon_sessions), replace=True).reshape(int(paths), int(horizon_sessions))
    return spot * np.exp(sampled.sum(axis=1))

def build_batman_signal(
    spot: float,
    terminal: np.ndarray,
    chain: pd.DataFrame,
    expiry: pd.Timestamp,
    lot_size: int,
    capital: float,
    risk_pct: float,
    cost_per_contract: float,
) -> dict:
    qs = np.percentile(terminal, [20,35,65,80])
    targets = {"p20": float(qs[0]), "p35": float(qs[1]), "c65": float(qs[2]), "c80": float(qs[3])}
    strikes = unique_strikes(
        chain.loc[chain.expiry.eq(expiry), "strike"].dropna().unique(),
        targets,
    )
    legs = build_strategy("Batman", strikes | {"atm": spot})
    entry_cashflow = 0.0
    contract_count = 0
    priced_legs: list[dict[str, object]] = []
    for leg in legs:
        row = find_option_row(chain, expiry, leg.option_type, leg.strike)
        side = "BUY" if leg.qty > 0 else "SELL"
        px, source = side_execution_price(row, side)
        entry_cashflow -= float(leg.qty) * px
        contract_count += abs(int(leg.qty))
        priced_legs.append({
            "side": side,
            "option_type": leg.option_type,
            "strike": float(leg.strike),
            "quantity_per_lot": abs(int(leg.qty)),
            "expiry": str(expiry.date()),
            "premium_points": float(px),
            "quote_source": source,
        })

    pnl = np.full(len(terminal), float(entry_cashflow), dtype=float)
    for leg in legs:
        intrinsic = (
            np.maximum(terminal - leg.strike, 0.0)
            if leg.option_type == "CE"
            else np.maximum(leg.strike - terminal, 0.0)
        )
        pnl += float(leg.qty) * intrinsic

    entry_cost_points = float(cost_per_contract) * float(contract_count)
    net_pnl = pnl - entry_cost_points
    mc_ev_gross = float(np.mean(pnl))
    mc_ev_net = float(np.mean(net_pnl))
    mc_pop = float(np.mean(net_pnl > 0))
    q05 = float(np.quantile(net_pnl, 0.05))
    q01 = float(np.quantile(net_pnl, 0.01))
    es95 = float(max(0.0, -np.mean(net_pnl[net_pnl <= q05])))
    es99 = float(max(0.0, -np.mean(net_pnl[net_pnl <= q01])))
    risk_points = max(es95, es99)
    risk_per_lot = risk_points * int(lot_size)
    risk_budget = float(capital) * float(risk_pct)
    recommended_lots = int(math.floor(risk_budget / risk_per_lot)) if risk_per_lot > 0 else 0
    min_capital = risk_per_lot / float(risk_pct) if risk_pct > 0 else math.inf

    return {
        "strategy": "Batman",
        "strikes": {k: float(v) for k,v in strikes.items()},
        "p20_terminal": float(qs[0]),
        "p35_terminal": float(qs[1]),
        "p65_terminal": float(qs[2]),
        "p80_terminal": float(qs[3]),
        "mc_expected_pnl_points_gross": mc_ev_gross,
        "entry_cost_points": entry_cost_points,
        "mc_expected_pnl_points_net": mc_ev_net,
        "mc_probability_profit": mc_pop,
        "mc_es95_points": es95,
        "mc_es99_points": es99,
        "lot_size": int(lot_size),
        "contracts_per_strategy_lot": int(contract_count),
        "risk_points_per_lot": float(risk_points),
        "risk_budget_inr": risk_budget,
        "estimated_risk_inr_per_lot": float(risk_per_lot),
        "minimum_capital_for_one_lot_inr": float(min_capital),
        "recommended_lots": recommended_lots,
        "entry_cashflow_points_per_unit": float(entry_cashflow),
        "entry_price_source": ",".join(sorted({str(x["quote_source"]) for x in priced_legs})),
        "signal": "ENTER" if mc_ev_net > 0 and recommended_lots >= 1 else "NO_TRADE",
        "legs": priced_legs,
        "risk_note": "ES95/ES99 are sizing proxies; Batman has theoretically unbounded tail loss.",
    }

def read_csv_or_empty(path: Path, columns: list[str]) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=columns)

def calculate_realized_for_open_trades(ledger: pd.DataFrame, index_df: pd.DataFrame, decision: pd.Timestamp) -> list[dict[str, object]]:
    if ledger.empty or "status" not in ledger.columns:
        return []
    close_map = dict(zip(index_df["date"].dt.date, index_df["close"].astype(float)))
    events: list[dict[str, object]] = []
    for idx in ledger.index[ledger.status.eq("OPEN")]:
        expiry = pd.Timestamp(ledger.at[idx, "expiry"]).normalize()
        spot = close_map.get(expiry.date())
        if spot is None or expiry > decision:
            continue
        intrinsic = 0.0
        for leg in json.loads(str(ledger.at[idx, "legs_json"])):
            signed_qty = int(leg["quantity_per_lot"]) if leg["side"] == "BUY" else -int(leg["quantity_per_lot"])
            strike = float(leg["strike"])
            intrinsic += signed_qty * (
                max(spot - strike, 0.0) if leg["option_type"] == "CE" else max(strike - spot, 0.0)
            )
        realized_points = (
            float(ledger.at[idx, "entry_cashflow_points_per_unit"])
            + intrinsic
            - float(ledger.at[idx, "entry_cost_points"])
        )
        realized_inr = realized_points * float(ledger.at[idx, "lots"]) * float(ledger.at[idx, "lot_size"])
        events.append({
            "index": idx,
            "exit_date": expiry.date().isoformat(),
            "exit_spot": float(spot),
            "exit_intrinsic_points_per_unit": float(intrinsic),
            "realized_pnl_points_per_unit": float(realized_points),
            "realized_pnl_inr": float(realized_inr),
        })
    return events

def apply_closures(ledger: pd.DataFrame, events: list[dict[str, object]]) -> pd.DataFrame:
    for e in events:
        idx = e["index"]
        ledger.at[idx, "status"] = "CLOSED"
        ledger.at[idx, "exit_date"] = e["exit_date"]
        ledger.at[idx, "exit_spot"] = e["exit_spot"]
        ledger.at[idx, "exit_intrinsic_points_per_unit"] = e["exit_intrinsic_points_per_unit"]
        ledger.at[idx, "realized_pnl_points_per_unit"] = e["realized_pnl_points_per_unit"]
        ledger.at[idx, "realized_pnl_inr"] = e["realized_pnl_inr"]
    return ledger

def fmt(value: object, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        x = float(value)
        if not math.isfinite(x):
            return "—"
        return f"{x:,.{digits}f}"
    except (TypeError, ValueError):
        return html.escape(str(value))


def text_value(value: object) -> str:
    if value is None:
        return "—"
    text = str(value)
    if text.strip().lower() in {"nan", "nat", "none", ""}:
        return "—"
    return html.escape(text)

def build_site(site_dir: Path, latest: dict, signals: pd.DataFrame, ledger: pd.DataFrame) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "latest_signal.json").write_text(json.dumps(latest, indent=2, default=str), encoding="utf-8")
    signals.to_csv(data_dir / "batman_signals.csv", index=False)
    ledger.to_csv(data_dir / "batman_paper_ledger.csv", index=False)

    closed = ledger[ledger.status.eq("CLOSED")].copy() if not ledger.empty else pd.DataFrame()
    if not closed.empty:
        pnl = pd.to_numeric(closed["realized_pnl_inr"], errors="coerce").fillna(0.0)
        cum = pnl.cumsum()
        dd = cum - cum.cummax()
        total = float(pnl.sum())
        win_rate = float((pnl > 0).mean())
        gp = float(pnl[pnl > 0].sum())
        gl = float(-pnl[pnl < 0].sum())
        pf = gp / gl if gl > 0 else math.inf
        max_dd = float(dd.min())
    else:
        total = 0.0
        win_rate = 0.0
        pf = 0.0
        max_dd = 0.0

    status = html.escape(str(latest.get("status", "")))
    signal = html.escape(str(latest.get("signal", "")))
    decision = html.escape(str(latest.get("decision_date", "")))
    expiry = text_value(latest.get("target_expiry"))
    legs = latest.get("legs", [])

    leg_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(x.get('side')))}</td>"
        f"<td>{html.escape(str(x.get('option_type')))}</td>"
        f"<td>{fmt(x.get('strike'))}</td>"
        f"<td>{html.escape(str(x.get('quantity_per_lot')))}</td>"
        f"<td>{fmt(x.get('premium_points'))}</td>"
        "</tr>"
        for x in legs
    )

    recent_signals = signals.tail(20).iloc[::-1] if not signals.empty else signals
    signal_rows = "".join(
        "<tr>"
        f"<td>{text_value(row.get('decision_date'))}</td>"
        f"<td>{text_value(row.get('target_expiry'))}</td>"
        f"<td>{text_value(row.get('status'))}</td>"
        f"<td>{text_value(row.get('signal'))}</td>"
        f"<td>{fmt(row.get('spot'))}</td>"
        f"<td>{fmt(row.get('mc_ev_points_net'))}</td>"
        f"<td>{fmt(row.get('mc_pop'), 3)}</td>"
        f"<td>{text_value(row.get('recommended_lots'))}</td>"
        "</tr>"
        for _, row in recent_signals.iterrows()
    )

    workflow_audit_panel = """<div class="card">
<h2>Workflow audit</h2>
<div class="grid">
<div><small>Last completed workflow run</small><div class="kpi" id="wf-audit-time">Loading...</div></div>
<div><small>Workflow status</small><div class="kpi" id="wf-audit-status">Loading...</div></div>
</div>
<p><small>Audit source: <a href="../data/run_status_nifty_signal_generation.json">run_status_nifty_signal_generation.json</a></small></p>
</div>
<script>
(async()=>{
  const fmt=v=>v?new Date(v).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Kolkata'}):'Not recorded';
  try{const d=await (await fetch('../data/run_status_nifty_signal_generation.json?ts='+Date.now(),{cache:'no-store'})).json();
  document.getElementById('wf-audit-time').textContent=fmt(d.finished_at_ist);
  document.getElementById('wf-audit-status').textContent=(d.status||'NOT_RECORDED').toUpperCase();}
  catch(e){document.getElementById('wf-audit-time').textContent='Audit unavailable';document.getElementById('wf-audit-status').textContent='ERROR';}
})();
</script>
"""
    backfill_panel = """<div class="card">
<h2>09:40 IST controlled backfill</h2>
<div class="grid">
<div><small>Decision date</small><div class="kpi" id="bf-date">—</div></div>
<div><small>Entry time</small><div class="kpi">09:40 IST</div></div>
<div><small>Signal</small><div class="kpi" id="bf-signal">DATA_LIMITED_CANDIDATE</div></div>
<div><small>Backfill status</small><div class="kpi" id="bf-status">BACKFILL_0940_DATA_LIMITED_CANDIDATE</div></div>
</div>
<p id="bf-reason">Loading...</p>
<p><small>Historical observation only. Quote-dependent execution gates were not evaluated; it is separate from the prospective ledger.</small></p>
</div>
<script>
(async()=>{
  try{const d=await (await fetch('data/backfill_0940_2026-09-21.json?ts='+Date.now(),{cache:'no-store'})).json();
  document.getElementById('bf-date').textContent=d.decision_date||'—';
  document.getElementById('bf-signal').textContent=d.signal||'NO_TRADE';
  document.getElementById('bf-status').textContent=(d.status||'NOT_RECORDED').replaceAll('_',' ');
  document.getElementById('bf-reason').textContent=d.reason||d.source_note||'—';}
  catch(e){document.getElementById('bf-signal').textContent='Not recorded';document.getElementById('bf-status').textContent='ERROR';document.getElementById('bf-reason').textContent='09:40 backfill record could not be loaded.';}
})();
</script>
"""
    ledger_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('decision_date')))}</td>"
        f"<td>{text_value(row.get('expiry'))}</td>"
        f"<td>{html.escape(str(row.get('signal')))}</td>"
        f"<td>{html.escape(str(row.get('status')))}</td>"
        f"<td>{text_value(row.get('lots'))}</td>"
        f"<td>{fmt(row.get('mc_ev_points_net'))}</td>"
        f"<td>{fmt(row.get('realized_pnl_inr'))}</td>"
        "</tr>"
        for _, row in (ledger.tail(20).iloc[::-1] if not ledger.empty else ledger).iterrows()
    )

    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Batman Signal Producer</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#0d1117;color:#e6edf3}}
main{{max-width:1200px;margin:auto;padding:24px}} .card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:14px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}} .kpi{{font-size:24px;font-weight:700}}
small{{color:#8b949e}} table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{padding:8px;border-bottom:1px solid #30363d;text-align:left}}
.badge{{display:inline-block;padding:4px 9px;border-radius:999px;background:#21262d;font-weight:700}} a{{color:#58a6ff}}
</style></head><body><main>
<p><a href="../">← Strategy selector</a> · <a href="../adaptive/">Adaptive Regime</a></p>
{workflow_audit_panel}
{backfill_panel}
<h1>Batman Signal Producer</h1>
<p><small>Frozen protocol • entry at 09:30 IST • 3 trading sessions before expiry • 5,000 MC paths • 756-session lookback • net EV gate.</small></p>
<div class="card"><h2>Latest run</h2>
<p><span class="badge">{status} / {signal}</span></p>
<div class="grid">
<div><small>Decision date</small><div class="kpi">{decision}</div></div>
<div><small>Fixed entry time</small><div class="kpi">09:30 IST</div></div>
<div><small>Model cutoff</small><div class="kpi">{html.escape(str(latest.get("model_data_cutoff","—")))}</div></div>
<div><small>Quote snapshot</small><div class="kpi">{html.escape(str(latest.get("quote_retrieved_at_ist","—")))}</div></div>
<div><small>Expiry</small><div class="kpi">{expiry or "—"}</div></div>
<div><small>Spot</small><div class="kpi">{fmt(latest.get("spot"))}</div></div>
<div><small>MC EV net</small><div class="kpi">{fmt(latest.get("mc_expected_pnl_points_net"))}</div></div>
<div><small>MC POP</small><div class="kpi">{fmt(latest.get("mc_probability_profit"),3)}</div></div>
<div><small>Lots</small><div class="kpi">{html.escape(str(latest.get("recommended_lots","—")))}</div></div>
</div><p>{html.escape(str(latest.get("notes","")))}</p></div>

<div class="card"><h2>MC results</h2><table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>P20 / P35 / P65 / P80 terminal</td><td>{fmt(latest.get("p20_terminal"))} / {fmt(latest.get("p35_terminal"))} / {fmt(latest.get("p65_terminal"))} / {fmt(latest.get("p80_terminal"))}</td></tr>
<tr><td>P20 / P35 / C65 / C80 strikes</td><td>{fmt(latest.get("strikes",{}).get("p20")) if latest.get("strikes") else "—"} / {fmt(latest.get("strikes",{}).get("p35")) if latest.get("strikes") else "—"} / {fmt(latest.get("strikes",{}).get("c65")) if latest.get("strikes") else "—"} / {fmt(latest.get("strikes",{}).get("c80")) if latest.get("strikes") else "—"}</td></tr>
<tr><td>Gross EV / stress cost / net EV</td><td>{fmt(latest.get("mc_expected_pnl_points_gross"))} / {fmt(latest.get("entry_cost_points"))} / {fmt(latest.get("mc_expected_pnl_points_net"))}</td></tr>
<tr><td>MC POP</td><td>{fmt(latest.get("mc_probability_profit"),3)}</td></tr>
<tr><td>ES95 / ES99</td><td>{fmt(latest.get("mc_es95_points"))} / {fmt(latest.get("mc_es99_points"))}</td></tr>
<tr><td>Risk budget / estimated risk per lot</td><td>₹{fmt(latest.get("risk_budget_inr"))} / ₹{fmt(latest.get("estimated_risk_inr_per_lot"))}</td></tr>
<tr><td>Minimum capital for 1 lot</td><td>₹{fmt(latest.get("minimum_capital_for_one_lot_inr"))}</td></tr>
</table></div>

<div class="card"><h2>Suggested Batman structure</h2>
<table><tr><th>Side</th><th>Type</th><th>Strike</th><th>Qty/lot</th><th>Entry price</th></tr>{leg_rows}</table></div>

<div class="card"><h2>Paper-trading summary</h2>
<div class="grid">
<div><small>Closed trades</small><div class="kpi">{len(closed)}</div></div>
<div><small>Win rate</small><div class="kpi">{win_rate:.1%}</div></div>
<div><small>Profit factor</small><div class="kpi">{"∞" if math.isinf(pf) else f"{pf:.2f}"}</div></div>
<div><small>Total P&L</small><div class="kpi">₹{total:,.2f}</div></div>
<div><small>Max drawdown</small><div class="kpi">₹{max_dd:,.2f}</div></div>
</div></div>

<div class="card"><h2>Recent signals</h2>
<table><tr><th>Date</th><th>Expiry</th><th>Status</th><th>Signal</th><th>Spot</th><th>Net EV</th><th>POP</th><th>Lots</th></tr>{signal_rows}</table>
<p><a href="data/latest_signal.json">Latest JSON</a> · <a href="data/batman_signals.csv">Signals CSV</a> · <a href="data/batman_paper_ledger.csv">Paper ledger CSV</a></p>
</div>

<div class="card"><h2>Recent paper trades</h2>
<table><tr><th>Entry</th><th>Expiry</th><th>Signal</th><th>Status</th><th>Lots</th><th>Net EV</th><th>Realized P&L ₹</th></tr>{ledger_rows}</table></div>

<div class="card"><small>Option-chain data is obtained from NSE public endpoints; NIFTY history uses NSE when available and Yahoo Finance only as a documented fallback. This is a research/paper-trading publication system and does not place broker orders. Missing/invalid data is not imputed.</small></div>
</main></body></html>"""
    (site_dir / "index.html").write_text(page, encoding="utf-8")

def telegram_message(latest: dict, closures: list[dict[str, object]]) -> str:
    lines = [
        "🤖 BATMAN SIGNAL PRODUCER",
        f"Date: {latest.get('decision_date')}",
        f"Expiry: {latest.get('target_expiry') or '—'}",
        f"Status: {latest.get('status')}",
        f"Signal: {latest.get('signal')}",
        f"Entry time: 09:30 IST",
        f"Model cutoff: {latest.get('model_data_cutoff') or '—'}",
        f"Quote snapshot: {latest.get('quote_retrieved_at_ist') or '—'}",
    ]
    if latest.get("spot") is not None:
        lines.append(f"Spot: {float(latest['spot']):,.2f}")
    if latest.get("mc_expected_pnl_points_net") is not None:
        lines += [
            f"MC EV net: {float(latest['mc_expected_pnl_points_net']):,.2f} pts",
            f"MC POP: {float(latest['mc_probability_profit']):.1%}",
            f"ES95/99: {float(latest['mc_es95_points']):,.2f} / {float(latest['mc_es99_points']):,.2f} pts",
            f"Lots: {latest.get('recommended_lots')}",
            f"Strikes P20/P35/C65/C80: {latest.get('strikes',{}).get('p20')} / {latest.get('strikes',{}).get('p35')} / {latest.get('strikes',{}).get('c65')} / {latest.get('strikes',{}).get('c80')}",
        ]
    for e in closures:
        lines.append(f"✅ CLOSED {e['exit_date']} | P&L ₹{float(e['realized_pnl_inr']):,.2f}")
    return "\n".join(lines)

def send_telegram(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat_id:
        print("TELEGRAM_NOT_CONFIGURED: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()
    if not r.json().get("ok"):
        raise RuntimeError(f"Telegram rejected message: {r.text}")

def main() -> None:
    ap = argparse.ArgumentParser(description="Batman Signal Producer")
    ap.add_argument("--capital", type=float, default=100000.0)
    ap.add_argument("--risk-pct", type=float, default=0.02)
    ap.add_argument("--lot-size", type=int, default=65)
    ap.add_argument("--paths", type=int, default=5000)
    ap.add_argument("--lookback", type=int, default=756)
    ap.add_argument("--cost-per-contract", type=float, default=2.0)
    ap.add_argument("--decision-date", default="auto")
    ap.add_argument("--expiry", default="")
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--ledger", default="paper_trading/batman_ledger.csv")
    ap.add_argument("--signals", default="paper_trading/batman_signals.csv")
    ap.add_argument("--site-dir", default="site/batman")
    ap.add_argument("--telegram-all-runs", action="store_true")
    args = ap.parse_args()

    if args.capital <= 0 or not (0 < args.risk_pct < 1):
        raise SystemExit("capital must be >0 and risk-pct must be between 0 and 1.")
    if args.lot_size <= 0 or args.paths < 100 or args.lookback < 60:
        raise SystemExit("lot-size/paths/lookback values are invalid.")

    current = now_ist()
    # Keep the decision date timezone-naive because all NSE/Yahoo daily bars
    # in this module are normalized to timezone-naive session dates.
    decision = pd.Timestamp(current.date())
    if args.decision_date != "auto":
        decision = pd.Timestamp(args.decision_date).normalize()
        if decision.date() != current.date():
            raise SystemExit("Live mode only supports today's decision date.")

    client = NSEClient()
    index_df = client.fetch_index_history(
        (decision - pd.Timedelta(days=365*5)).date(),
        decision.date(),
    )
    holidays = client.fetch_holidays()

    # Freeze the model at the most recent completed session before entry.
    # Entry-day option quotes are fetched separately after 09:30 IST.
    prior_history = index_df.loc[index_df["date"] < decision].copy()
    if prior_history.empty:
        raise RuntimeError(
            f"No completed NIFTY 50 session exists before entry date {decision.date()}."
        )
    model_cutoff = pd.Timestamp(prior_history["date"].max()).normalize()
    model_spot = float(
        prior_history.loc[prior_history["date"].eq(model_cutoff), "close"].iloc[-1]
    )

    ledger_path = Path(args.ledger)
    ledger = read_csv_or_empty(ledger_path, LEDGER_COLUMNS)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(ledger_path, index=False)
    closures = calculate_realized_for_open_trades(ledger, index_df, decision)
    if closures:
        ledger = apply_closures(ledger, closures)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.to_csv(ledger_path, index=False)

    decision_is_session = decision.weekday() < 5 and decision not in holidays

    chain = pd.DataFrame(
        columns=["expiry","strike","option_type","last_price","bid","ask","open_interest","volume"]
    )
    chain_underlying = None
    chain_endpoint = ""
    chain_expiry = None
    chain_error = None

    quote_retrieved_at: datetime | None = None
    if decision_is_session and current.time() >= ENTRY_TIME_IST:
        requested_expiry = pd.Timestamp(args.expiry).normalize() if args.expiry else None
        try:
            chain, chain_underlying, chain_endpoint, chain_expiry = client.fetch_option_chain(
                requested_expiry
            )
            quote_retrieved_at = now_ist()
        except Exception as exc:
            chain_error = exc

    spot = model_spot
    spot_source = f"{client.index_history_source}_PREVIOUS_SESSION_CLOSE"

    payload: dict[str, object] = {
        "producer":"Batman Signal Producer",
        "strategy":"Batman",
        "run_timestamp_ist":current.isoformat(),
        "entry_timestamp_ist":"",
        "decision_date":decision.date().isoformat(),
        "model_data_cutoff":model_cutoff.date().isoformat(),
        "quote_retrieved_at_ist":quote_retrieved_at.isoformat() if quote_retrieved_at else "",
        "target_expiry":"",
        "status":"NOT_TRADING_DAY" if not decision_is_session else (
            "WAITING_FOR_ENTRY_TIME"
            if current.time() < ENTRY_TIME_IST
            else ("DATA_UNAVAILABLE" if chain_error else "OK")
        ),
        "signal":"NO_TRADE",
        "spot":spot,
        "spot_source":spot_source,
        "mc_paths":args.paths,
        "lookback_sessions":args.lookback,
        "chain_endpoint":chain_endpoint,
        "source":f"NSE option-chain endpoints; index history={client.index_history_source}",
        "closures":closures,
        "legs":[],
        "notes":"",
    }

    if not decision_is_session:
        payload["notes"] = "Decision date is not a NIFTY 50 trading session; no option-chain fetch was attempted."
    elif current.time() < ENTRY_TIME_IST:
        payload["notes"] = "Entry processing is held until the fixed 09:30 IST entry time."
    elif chain_error is not None:
        payload["status"] = "DATA_UNAVAILABLE"
        payload["notes"] = f"NSE option-chain unavailable: {chain_error}"
    else:
        target_expiry = chain_expiry
        if target_expiry is None:
            raise RuntimeError("NSE option chain did not provide a target expiry.")
        if target_expiry.date() < decision.date():
            raise RuntimeError(
                f"NSE returned an expired front expiry {target_expiry.date()} for decision date {decision.date()}."
            )
        payload["target_expiry"] = target_expiry.date().isoformat()

        sessions = trading_sessions_between(decision, target_expiry, holidays)
        future_sessions = sessions[sessions > decision]
        if len(future_sessions) != 3 or target_expiry not in set(sessions):
            payload["status"] = "NOT_ENTRY_DAY"
            payload["notes"] = f"Frozen entry rule requires exactly 3 future trading sessions; found {len(future_sessions)}."
        else:
            returns = (
                np.log(index_df.loc[index_df["date"] <= model_cutoff, "close"])
                .diff()
                .dropna()
                .tail(args.lookback)
                .to_numpy(float)
            )
            if len(returns) < args.lookback:
                raise RuntimeError(f"Need {args.lookback} historical returns, found {len(returns)}.")
            terminal = mc_paths(float(spot), returns, len(future_sessions), args.paths, args.seed)
            metrics = build_batman_signal(
                float(spot), terminal, chain, target_expiry, args.lot_size,
                args.capital, args.risk_pct, args.cost_per_contract,
            )
            payload.update(metrics)
            payload["status"] = "ENTRY_DAY"
            payload["horizon_sessions"] = len(future_sessions)
            payload["entry_timestamp_ist"] = quote_retrieved_at.isoformat() if quote_retrieved_at else ""
            payload["quote_retrieved_at_ist"] = quote_retrieved_at.isoformat() if quote_retrieved_at else ""
            payload["notes"] = (
                "Fixed entry time 09:30 IST. Model data is frozen through the prior completed "
                "NIFTY session; option premiums come only from the entry-day NSE snapshot. "
                "ENTER only when net MC EV > 0 and at least one risk-sized lot fits configured paper capital."
            )

    signal_row = {
        "run_timestamp_ist":payload["run_timestamp_ist"],
        "entry_timestamp_ist":payload.get("entry_timestamp_ist",""),
        "decision_date":payload["decision_date"],
        "model_data_cutoff":payload.get("model_data_cutoff",""),
        "quote_retrieved_at_ist":payload.get("quote_retrieved_at_ist",""),
        "target_expiry":payload.get("target_expiry",""),
        "status":payload.get("status",""),
        "signal":payload.get("signal",""),
        "spot":payload.get("spot"),
        "spot_source":spot_source,
        "mc_paths":args.paths,
        "lookback_sessions":args.lookback,
        "horizon_sessions":payload.get("horizon_sessions", ""),
        "p20_terminal":payload.get("p20_terminal"),
        "p35_terminal":payload.get("p35_terminal"),
        "p65_terminal":payload.get("p65_terminal"),
        "p80_terminal":payload.get("p80_terminal"),
        "p20_strike":payload.get("strikes",{}).get("p20") if payload.get("strikes") else "",
        "p35_strike":payload.get("strikes",{}).get("p35") if payload.get("strikes") else "",
        "c65_strike":payload.get("strikes",{}).get("c65") if payload.get("strikes") else "",
        "c80_strike":payload.get("strikes",{}).get("c80") if payload.get("strikes") else "",
        "mc_ev_points_gross":payload.get("mc_expected_pnl_points_gross"),
        "entry_cost_points":payload.get("entry_cost_points"),
        "mc_ev_points_net":payload.get("mc_expected_pnl_points_net"),
        "mc_pop":payload.get("mc_probability_profit"),
        "mc_es95_points":payload.get("mc_es95_points"),
        "mc_es99_points":payload.get("mc_es99_points"),
        "lot_size":args.lot_size,
        "contracts_per_strategy_lot":payload.get("contracts_per_strategy_lot"),
        "risk_points_per_lot":payload.get("risk_points_per_lot"),
        "risk_budget_inr":payload.get("risk_budget_inr"),
        "estimated_risk_inr_per_lot":payload.get("estimated_risk_inr_per_lot"),
        "minimum_capital_for_one_lot_inr":payload.get("minimum_capital_for_one_lot_inr"),
        "recommended_lots":payload.get("recommended_lots"),
        "entry_cashflow_points_per_unit":payload.get("entry_cashflow_points_per_unit"),
        "entry_price_source":payload.get("entry_price_source"),
        "signal_id":f"{payload['decision_date']}|{payload.get('target_expiry','')}|Batman",
        "notes":payload.get("notes",""),
    }

    signal_path = Path(args.signals)
    signals = read_csv_or_empty(signal_path, SIGNAL_COLUMNS)
    if signal_row["signal_id"] not in set(signals.get("signal_id", pd.Series(dtype=str)).astype(str)):
        signals = pd.concat([signals, pd.DataFrame([signal_row])], ignore_index=True)
        signal_path.parent.mkdir(parents=True, exist_ok=True)
        signals.to_csv(signal_path, index=False)

    if payload.get("status") == "ENTRY_DAY" and payload.get("target_expiry"):
        if signal_row["signal_id"] not in set(ledger.get("signal_id", pd.Series(dtype=str)).astype(str)):
            row = {
                "signal_id":signal_row["signal_id"],
                "decision_date":payload["decision_date"],
                "expiry":payload["target_expiry"],
                "strategy":"Batman",
                "signal":payload["signal"],
                "spot":payload.get("spot"),
                "lot_size":payload.get("lot_size", args.lot_size),
                "lots":payload.get("recommended_lots",0),
                "risk_budget_inr":payload.get("risk_budget_inr",0),
                "mc_ev_points_net":payload.get("mc_expected_pnl_points_net"),
                "mc_pop":payload.get("mc_probability_profit"),
                "es95_points":payload.get("mc_es95_points"),
                "es99_points":payload.get("mc_es99_points"),
                "entry_cost_points":payload.get("entry_cost_points",0),
                "entry_cashflow_points_per_unit":payload.get("entry_cashflow_points_per_unit"),
                "entry_timestamp_ist":payload.get("entry_timestamp_ist",""),
                "model_data_cutoff":payload.get("model_data_cutoff",""),
                "quote_retrieved_at_ist":payload.get("quote_retrieved_at_ist",""),
                "legs_json":json.dumps(payload.get("legs",[]), separators=(",",":")),
                "status":"OPEN" if payload.get("signal") == "ENTER" else "NO_TRADE",
                "exit_date":"","exit_spot":"","exit_intrinsic_points_per_unit":"",
                "realized_pnl_points_per_unit":"","realized_pnl_inr":"",
                "notes":payload.get("notes",""),
            }
            ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger.to_csv(ledger_path, index=False)

    build_site(Path(args.site_dir), payload, signals, ledger)

    if payload.get("status") in {"ENTRY_DAY", "DATA_UNAVAILABLE"} or closures or args.telegram_all_runs:
        send_telegram(telegram_message(payload, closures))

    Path(args.site_dir, "data", "producer_metadata.json").write_text(
        json.dumps({
            "run_timestamp_ist":payload["run_timestamp_ist"],
            "entry_time_ist":"09:30",
            "entry_timestamp_ist":payload.get("entry_timestamp_ist",""),
            "model_data_cutoff":payload.get("model_data_cutoff",""),
            "quote_retrieved_at_ist":payload.get("quote_retrieved_at_ist",""),
            "nse_option_chain_endpoint":chain_endpoint,
            "capital":args.capital,
            "risk_pct":args.risk_pct,
            "lot_size":args.lot_size,
            "paths":args.paths,
            "lookback":args.lookback,
            "cost_per_contract":args.cost_per_contract,
            "seed":args.seed,
        }, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, default=str))

if __name__ == "__main__":
    main()
