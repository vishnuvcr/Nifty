from __future__ import annotations

import argparse
import html
import json
import math
import os
import zlib
from datetime import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import build_strategy

try:
    from batman_signal_producer import (
        NSEClient,
        apply_closures,
        calculate_realized_for_open_trades,
        find_option_row,
        mc_paths,
        now_ist,
        side_execution_price,
        trading_sessions_between,
    )
except ImportError:  # Allows package-style test imports.
    from scripts.batman_signal_producer import (
        NSEClient,
        apply_closures,
        calculate_realized_for_open_trades,
        find_option_row,
        mc_paths,
        now_ist,
        side_execution_price,
        trading_sessions_between,
    )


ENTRY_TIME_IST = time(9, 30)
CANDIDATES_BY_REGIME = {
    "low": ["Risk Reversal", "Long Synthetic Future", "Buy Call"],
    "medium": ["Short Straddle", "Put Ratio Spread", "Short Strangle", "Strip", "Buy Put"],
    "high": ["Sell Put", "Risk Reversal", "Long Synthetic Future", "Batman"],
}
CPCV_FREQUENCY = {
    "low": {"Risk Reversal": 9, "Long Synthetic Future": 4, "Buy Call": 2},
    "medium": {
        "Short Straddle": 4,
        "Put Ratio Spread": 4,
        "Short Strangle": 3,
        "Strip": 3,
        "Buy Put": 1,
    },
    "high": {"Sell Put": 5, "Risk Reversal": 5, "Long Synthetic Future": 3, "Batman": 2},
}

SIGNAL_COLUMNS = [
    "run_timestamp_ist", "decision_date", "target_expiry", "status", "signal",
    "vol_regime", "rv20", "rv20_rank", "spot", "model_data_cutoff",
    "quote_retrieved_at_ist", "horizon_sessions", "primary_strategy",
    "primary_net_ev_points", "primary_mc_pop", "primary_es95_points", "primary_es99_points",
    "primary_recommended_lots", "primary_contracts_per_lot", "primary_risk_points_per_lot",
    "primary_risk_budget_inr", "primary_minimum_capital_inr", "primary_entry_cashflow_points",
    "primary_strikes_json", "primary_legs_json", "candidate_count", "eligible_candidate_count",
    "signal_id", "notes",
]

CANDIDATE_COLUMNS = [
    "run_timestamp_ist", "decision_date", "target_expiry", "vol_regime", "rv20", "rv20_rank",
    "spot", "model_data_cutoff", "horizon_sessions", "strategy", "cpcv_selection_frequency",
    "p20_terminal", "p35_terminal", "p65_terminal", "p80_terminal",
    "strikes_json", "mc_ev_points_gross", "entry_cost_points", "mc_ev_points_net",
    "mc_pop", "mc_es95_points", "mc_es99_points", "contracts_per_lot", "risk_points_per_lot",
    "risk_budget_inr", "estimated_risk_inr_per_lot", "minimum_capital_for_one_lot_inr",
    "recommended_lots", "eligible", "eligibility_reason", "primary_selected",
    "entry_cashflow_points", "entry_price_source", "legs_json",
]

LEDGER_COLUMNS = [
    "signal_id", "decision_date", "expiry", "strategy", "signal", "regime", "spot",
    "lot_size", "lots", "risk_budget_inr", "mc_ev_points_net", "mc_pop", "es95_points",
    "es99_points", "entry_cost_points", "entry_cashflow_points_per_unit", "legs_json",
    "entry_timestamp_ist", "model_data_cutoff", "quote_retrieved_at_ist", "status",
    "exit_date", "exit_spot", "exit_intrinsic_points_per_unit", "realized_pnl_points_per_unit",
    "realized_pnl_inr", "notes",
]


def deterministic_seed(decision_date: pd.Timestamp) -> int:
    return 100000 + zlib.crc32(f"adaptive-v1|{decision_date.date()}".encode("utf-8")) % 900000


def read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path)
    for col in columns:
        if col not in df.columns:
            df[col] = np.nan
    return df[columns]


def candidate_contract_count(strategy: str) -> int:
    return int(sum(abs(leg.qty) for leg in build_strategy(strategy, strategy_targets(strategy, np.array([100.0, 101.0, 102.0, 103.0]), 101.5))))


def strategy_targets(strategy: str, terminal: np.ndarray, spot: float) -> dict[str, float]:
    qs = np.percentile(terminal, [20, 35, 65, 80])
    targets = {
        "p20": float(qs[0]),
        "p35": float(qs[1]),
        "c65": float(qs[2]),
        "c80": float(qs[3]),
        "atm": float(spot),
    }
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
    if strategy not in required:
        raise KeyError(f"Unsupported adaptive candidate: {strategy}")
    return {k: targets[k] for k in required[strategy]}


def map_unique_strikes(chain: pd.DataFrame, targets: dict[str, float]) -> dict[str, float]:
    available = np.sort(np.unique(chain["strike"].dropna().astype(float)))
    if len(available) < len(targets):
        raise ValueError("Not enough unique listed strikes for strategy.")
    used: set[float] = set()
    out: dict[str, float] = {}
    # ATM gets first priority so directional/synthetic structures stay centered.
    ordered = sorted(targets.items(), key=lambda kv: (0 if kv[0] == "atm" else 1, kv[1]))
    for label, target in ordered:
        choice = None
        for idx in np.argsort(np.abs(available - target)):
            value = float(available[idx])
            if value not in used:
                choice = value
                break
        if choice is None:
            raise ValueError(f"Unable to map unique strike for {label}.")
        out[label] = choice
        used.add(choice)
    return out


def compute_volatility_regime(index_df: pd.DataFrame, cutoff: pd.Timestamp, rank_window: int) -> dict[str, float | str]:
    close = (
        index_df.loc[index_df["date"] <= cutoff, ["date", "close"]]
        .drop_duplicates("date")
        .sort_values("date")
    )
    if len(close) < 100:
        raise ValueError("Insufficient NIFTY history for volatility regime classification.")
    logret = np.log(close["close"]).diff()
    rv20_series = logret.rolling(20).std(ddof=1) * np.sqrt(252)
    rv20_series = rv20_series.dropna()
    if rv20_series.empty:
        raise ValueError("Unable to calculate RV20.")
    latest = float(rv20_series.iloc[-1])
    hist = rv20_series.iloc[:-1].tail(rank_window)
    if len(hist) < min(60, rank_window):
        raise ValueError("Insufficient past-only RV20 history for regime rank.")
    rank = float(np.mean(hist.to_numpy(float) <= latest))
    if rank <= 1 / 3:
        regime = "low"
    elif rank <= 2 / 3:
        regime = "medium"
    else:
        regime = "high"
    return {"rv20": latest, "rv20_rank": rank, "vol_regime": regime}


def select_primary_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [r for r in rows if bool(r.get("eligible"))]
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda r: (
            -float(r["net_ev"]),
            -int(r.get("cpcv_frequency", 0)),
            str(r["strategy"]),
        ),
    )[0]


def candidate_metrics(
    strategy: str,
    terminal: np.ndarray,
    spot: float,
    chain: pd.DataFrame,
    expiry: pd.Timestamp,
    lot_size: int,
    capital: float,
    risk_pct: float,
    stress_cost_per_contract: float,
    cpcv_frequency: int,
) -> dict[str, Any]:
    expiry_chain = chain.loc[chain["expiry"].eq(expiry)].copy()
    targets = strategy_targets(strategy, terminal, spot)
    strikes = map_unique_strikes(expiry_chain, targets)
    legs = build_strategy(strategy, strikes)

    entry_cashflow = 0.0
    contract_count = 0
    priced_legs: list[dict[str, Any]] = []
    pnl = np.zeros(len(terminal), dtype=float)

    for leg in legs:
        row = find_option_row(chain, expiry, leg.option_type, leg.strike)
        side = "BUY" if leg.qty > 0 else "SELL"
        premium, source = side_execution_price(row, side)
        entry_cashflow -= float(leg.qty) * float(premium)
        contract_count += abs(int(leg.qty))
        priced_legs.append({
            "side": side,
            "option_type": leg.option_type,
            "strike": float(leg.strike),
            "quantity_per_lot": abs(int(leg.qty)),
            "expiry": str(expiry.date()),
            "premium_points": float(premium),
            "quote_source": source,
        })
        intrinsic = (
            np.maximum(terminal - float(leg.strike), 0.0)
            if leg.option_type == "CE"
            else np.maximum(float(leg.strike) - terminal, 0.0)
        )
        pnl += float(leg.qty) * intrinsic

    pnl += entry_cashflow
    entry_cost_points = float(stress_cost_per_contract) * float(contract_count)
    net_pnl = pnl - entry_cost_points
    mc_ev_gross = float(np.mean(pnl))
    mc_ev_net = float(np.mean(net_pnl))
    mc_pop = float(np.mean(net_pnl > 0))

    q05 = float(np.quantile(net_pnl, 0.05))
    q01 = float(np.quantile(net_pnl, 0.01))
    worst5 = net_pnl[net_pnl <= q05]
    worst1 = net_pnl[net_pnl <= q01]
    es95 = float(max(0.0, -np.mean(worst5))) if len(worst5) else 0.0
    es99 = float(max(0.0, -np.mean(worst1))) if len(worst1) else 0.0
    risk_points = max(es95, es99)
    risk_budget = float(capital) * float(risk_pct)
    estimated_risk_inr = risk_points * float(lot_size)
    recommended_lots = int(math.floor(risk_budget / estimated_risk_inr)) if estimated_risk_inr > 0 else 0
    eligible = bool(mc_ev_net > 0 and recommended_lots >= 1)

    if mc_ev_net <= 0:
        eligibility_reason = "MC_EV_NONPOSITIVE"
    elif recommended_lots < 1:
        eligibility_reason = "RISK_BUDGET_CANNOT_FUND_ONE_LOT"
    else:
        eligibility_reason = "ELIGIBLE"

    return {
        "strategy": strategy,
        "cpcv_frequency": int(cpcv_frequency),
        "p20_terminal": float(np.percentile(terminal, 20)),
        "p35_terminal": float(np.percentile(terminal, 35)),
        "p65_terminal": float(np.percentile(terminal, 65)),
        "p80_terminal": float(np.percentile(terminal, 80)),
        "strikes": {k: float(v) for k, v in strikes.items()},
        "mc_ev_gross": mc_ev_gross,
        "entry_cost_points": entry_cost_points,
        "mc_ev_net": mc_ev_net,
        "mc_pop": mc_pop,
        "mc_es95": es95,
        "mc_es99": es99,
        "contracts_per_lot": int(contract_count),
        "risk_points_per_lot": float(risk_points),
        "risk_budget_inr": risk_budget,
        "estimated_risk_inr_per_lot": float(estimated_risk_inr),
        "minimum_capital_for_one_lot_inr": (
            float(estimated_risk_inr / risk_pct) if risk_pct > 0 else math.inf
        ),
        "recommended_lots": int(recommended_lots),
        "eligible": eligible,
        "eligibility_reason": eligibility_reason,
        "entry_cashflow_points": float(entry_cashflow),
        "entry_price_source": ",".join(sorted({str(x["quote_source"]) for x in priced_legs})),
        "legs": priced_legs,
    }


def append_once(df: pd.DataFrame, row: dict[str, Any], key: str) -> pd.DataFrame:
    value = str(row.get(key, ""))
    if key in df.columns and value in set(df[key].astype(str)):
        return df
    return pd.concat([df, pd.DataFrame([row])], ignore_index=True)


def summary_stats(ledger: pd.DataFrame) -> dict[str, float | int]:
    closed = ledger.loc[ledger["status"].eq("CLOSED")].copy() if not ledger.empty else pd.DataFrame()
    if closed.empty:
        return {"closed": 0, "win_rate": 0.0, "profit_factor": 0.0, "total": 0.0, "max_dd": 0.0}
    pnl = pd.to_numeric(closed["realized_pnl_inr"], errors="coerce").fillna(0.0)
    eq = pnl.cumsum()
    dd = eq - eq.cummax()
    gains = float(pnl[pnl > 0].sum())
    losses = float(-pnl[pnl < 0].sum())
    return {
        "closed": int(len(closed)),
        "win_rate": float((pnl > 0).mean()),
        "profit_factor": gains / losses if losses > 0 else math.inf,
        "total": float(pnl.sum()),
        "max_dd": float(dd.min()),
    }


def fmt(value: object, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        x = float(value)
        if math.isnan(x):
            return "—"
        return f"{x:,.{digits}f}"
    except (TypeError, ValueError):
        return html.escape(str(value))


def build_site(site_dir: Path, latest: dict[str, Any], candidates: pd.DataFrame, signals: pd.DataFrame, ledger: pd.DataFrame) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "adaptive_latest.json").write_text(json.dumps(latest, indent=2, default=str), encoding="utf-8")
    candidates.to_csv(data_dir / "adaptive_candidate_screen.csv", index=False)
    signals.to_csv(data_dir / "adaptive_signals.csv", index=False)
    ledger.to_csv(data_dir / "adaptive_ledger.csv", index=False)
    (data_dir / "adaptive_metadata.json").write_text(
        json.dumps({
            "producer": "Adaptive Paper Signal Producer v1",
            "research_basis": "Pre-2026 CPCV + block bootstrap",
            "candidate_universe": CANDIDATES_BY_REGIME,
            "entry_time_ist": "09:30",
            "entry_sessions_before_expiry": 3,
            "mc_paths": int(latest.get("mc_paths", 5000)),
            "lookback_sessions": int(latest.get("lookback_sessions", 756)),
            "stress_cost_points_per_contract": float(latest.get("stress_cost_points_per_contract", 2.0)),
            "primary_selection": "highest_net_mc_ev_among_eligible_candidates",
            "primary_selection_validated": False,
        }, indent=2),
        encoding="utf-8",
    )

    s = summary_stats(ledger)
    candidate_rows = []
    recent_candidates = candidates.tail(40).iloc[::-1] if not candidates.empty else candidates
    for _, row in recent_candidates.iterrows():
        candidate_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('decision_date')))}</td>"
            f"<td>{html.escape(str(row.get('vol_regime')))}</td>"
            f"<td>{html.escape(str(row.get('strategy')))}</td>"
            f"<td>{fmt(row.get('mc_ev_points_net'))}</td>"
            f"<td>{fmt(row.get('mc_pop'), 3)}</td>"
            f"<td>{fmt(row.get('risk_points_per_lot'))}</td>"
            f"<td>{html.escape(str(row.get('recommended_lots')))}</td>"
            f"<td>{'YES' if bool(row.get('eligible')) else 'NO'}</td>"
            f"<td>{'PRIMARY' if bool(row.get('primary_selected')) else ''}</td>"
            "</tr>"
        )

    signal_rows = []
    recent_signals = signals.tail(20).iloc[::-1] if not signals.empty else signals
    for _, row in recent_signals.iterrows():
        signal_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('decision_date')))}</td>"
            f"<td>{html.escape(str(row.get('target_expiry')))}</td>"
            f"<td>{html.escape(str(row.get('vol_regime')))}</td>"
            f"<td>{html.escape(str(row.get('primary_strategy')))}</td>"
            f"<td>{html.escape(str(row.get('signal')))}</td>"
            f"<td>{fmt(row.get('primary_net_ev_points'))}</td>"
            f"<td>{html.escape(str(row.get('primary_recommended_lots')))}</td>"
            "</tr>"
        )

    primary_legs = latest.get("primary_legs", []) or []
    leg_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(x.get('side')))}</td>"
        f"<td>{html.escape(str(x.get('option_type')))}</td>"
        f"<td>{fmt(x.get('strike'))}</td>"
        f"<td>{html.escape(str(x.get('quantity_per_lot')))}</td>"
        f"<td>{fmt(x.get('premium_points'))}</td>"
        "</tr>"
        for x in primary_legs
    )

    pf_display = "∞" if math.isinf(float(s["profit_factor"])) else f'{float(s["profit_factor"]):.2f}'

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Adaptive Regime Paper Trading v1</title>
<style>
:root{{color-scheme:dark}}
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#0b1220;color:#e8eef6}}
main{{max-width:1250px;margin:auto;padding:24px}}
.card{{background:#111a2a;border:1px solid #2a374b;border-radius:14px;padding:18px;margin:14px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}
.kpi{{font-size:23px;font-weight:750}}
small{{color:#93a5bb}}
a{{color:#7fb0ff}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:8px;border-bottom:1px solid #293547;text-align:left;vertical-align:top}}
.badge{{display:inline-block;padding:5px 10px;border-radius:999px;background:#21304a;font-weight:700}}
.warn{{background:#2b2416;border-color:#59471e}}
.ok{{background:#142b20;border-color:#285d43}}
.note{{color:#aebdce;line-height:1.55}}
</style></head>
<body><main>
<p><a href="../">← Strategy selector</a> · <a href="../batman/">Batman</a></p>
<div class="card">
<span class="badge">ADAPTIVE PAPER TRADING v1</span>
<h1>Adaptive Regime Signal Producer</h1>
<p class="note">Candidate-set paper trader derived from the completed pre-2026 CPCV finding. The regime-level evidence and the prospective primary-selection rule are displayed separately.</p>
<p class="note"><b>Automation:</b> new entry signals are generated at 09:30 IST on trading weekdays. The 16:00 IST job is refresh-only: it settles matured paper trades and republishes the dashboards without creating a second entry signal.</p>
</div>

<div class="card">
<h2>Latest signal</h2>
<p><span class="badge">{html.escape(str(latest.get("status", "—")))} / {html.escape(str(latest.get("signal", "—")))}</span></p>
<div class="grid">
<div><small>Decision date</small><div class="kpi">{html.escape(str(latest.get("decision_date", "—")))}</div></div>
<div><small>Volatility regime</small><div class="kpi">{html.escape(str(latest.get("vol_regime", "—")))}</div></div>
<div><small>RV20 rank</small><div class="kpi">{fmt(latest.get("rv20_rank"),3)}</div></div>
<div><small>Expiry</small><div class="kpi">{html.escape(str(latest.get("target_expiry") or "—"))}</div></div>
<div><small>Spot</small><div class="kpi">{fmt(latest.get("spot"))}</div></div>
<div><small>Primary</small><div class="kpi">{html.escape(str(latest.get("primary_strategy") or "NO_TRADE"))}</div></div>
<div><small>Primary net MC EV</small><div class="kpi">{fmt(latest.get("primary_net_ev_points"))}</div></div>
<div><small>Primary lots</small><div class="kpi">{html.escape(str(latest.get("primary_recommended_lots", "—")))}</div></div>
</div>
<p class="note">{html.escape(str(latest.get("notes", "")))}</p>
</div>

<div class="card">
<h2>Primary paper-trade structure</h2>
<table><tr><th>Side</th><th>Type</th><th>Strike</th><th>Qty/lot</th><th>Entry price</th></tr>{leg_rows}</table>
</div>

<div class="card">
<h2>Primary MC / risk metrics</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>MC EV gross / stress cost / net</td><td>{fmt(latest.get("primary_mc_ev_gross"))} / {fmt(latest.get("primary_entry_cost_points"))} / {fmt(latest.get("primary_net_ev_points"))}</td></tr>
<tr><td>MC POP</td><td>{fmt(latest.get("primary_mc_pop"),3)}</td></tr>
<tr><td>ES95 / ES99</td><td>{fmt(latest.get("primary_es95_points"))} / {fmt(latest.get("primary_es99_points"))}</td></tr>
<tr><td>Risk budget / estimated risk per lot</td><td>₹{fmt(latest.get("primary_risk_budget_inr"))} / ₹{fmt(latest.get("primary_estimated_risk_inr_per_lot"))}</td></tr>
<tr><td>Minimum capital for one lot</td><td>₹{fmt(latest.get("primary_minimum_capital_inr"))}</td></tr>
</table>
</div>

<div class="card">
<h2>Paper-trading summary</h2>
<div class="grid">
<div><small>Closed trades</small><div class="kpi">{s["closed"]}</div></div>
<div><small>Win rate</small><div class="kpi">{s["win_rate"]:.1%}</div></div>
<div><small>Profit factor</small><div class="kpi">{pf_display}</div></div>
<div><small>Total P&L</small><div class="kpi">₹{float(s["total"]):,.2f}</div></div>
<div><small>Max drawdown</small><div class="kpi">₹{float(s["max_dd"]):,.2f}</div></div>
</div>
</div>

<div class="card">
<h2>Candidate screen</h2>
<p class="note">Every strategy in the frozen regime candidate set is evaluated. <b>PRIMARY</b> means highest net MC EV among candidates that passed the MC EV gate and could fund at least one risk-sized lot.</p>
<table><tr><th>Date</th><th>Regime</th><th>Strategy</th><th>Net EV</th><th>POP</th><th>Risk pts</th><th>Lots</th><th>Eligible</th><th>Selected</th></tr>
{"".join(candidate_rows)}
</table>
</div>

<div class="card">
<h2>Signal history</h2>
<table><tr><th>Date</th><th>Expiry</th><th>Regime</th><th>Primary</th><th>Signal</th><th>Net EV</th><th>Lots</th></tr>
{"".join(signal_rows)}
</table>
</div>

<div class="card ok">
<h2>Research boundary</h2>
<p class="note">The completed CPCV phase supports the regime-conditioned effect and showed instability in exact strategy identity. The candidate universe above is frozen from that phase. The highest-net-EV primary selection is a new prospective rule and is not historically validated. The 2026 holdout used previously is not reopened.</p>
</div>

<div class="card">
<h2>Published artifacts</h2>
<p><a href="data/adaptive_latest.json">Latest JSON</a> · <a href="data/adaptive_signals.csv">Signals CSV</a> · <a href="data/adaptive_candidate_screen.csv">Candidate screen CSV</a> · <a href="data/adaptive_ledger.csv">Paper ledger CSV</a> · <a href="data/adaptive_metadata.json">Metadata JSON</a></p>
</div>

<div class="card"><small>Paper trading only. Model data is frozen through the prior completed session. Missing/invalid data is not imputed. No broker order execution is performed.</small></div>
</main></body></html>"""
    (site_dir / "index.html").write_text(page, encoding="utf-8")


def telegram_message(latest: dict[str, Any]) -> str:
    return "\n".join([
        "🤖 ADAPTIVE REGIME PAPER SIGNAL V1",
        f"Date: {latest.get('decision_date')}",
        f"Regime: {latest.get('vol_regime')}",
        f"Expiry: {latest.get('target_expiry') or '—'}",
        f"Primary: {latest.get('primary_strategy') or 'NO_TRADE'}",
        f"Signal: {latest.get('signal')}",
        f"Net MC EV: {fmt(latest.get('primary_net_ev_points'))} pts",
        f"MC POP: {fmt(latest.get('primary_mc_pop'),3)}",
        f"ES95/ES99: {fmt(latest.get('primary_es95_points'))}/{fmt(latest.get('primary_es99_points'))} pts",
        f"Lots: {latest.get('primary_recommended_lots', 0)}",
    ])


def send_telegram(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("TELEGRAM_NOT_CONFIGURED")
        return
    try:
        from curl_cffi import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=30,
        )
        r.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"Telegram delivery failed: {exc}") from exc


def main() -> None:
    ap = argparse.ArgumentParser(description="Adaptive regime candidate-set paper signal producer v1")
    ap.add_argument("--capital", type=float, default=100000.0)
    ap.add_argument("--risk-pct", type=float, default=0.02)
    ap.add_argument("--lot-size", type=int, default=65)
    ap.add_argument("--paths", type=int, default=5000)
    ap.add_argument("--lookback", type=int, default=756)
    ap.add_argument("--rank-lookback", type=int, default=252)
    ap.add_argument("--cost-per-contract", type=float, default=2.0)
    ap.add_argument("--decision-date", default="auto")
    ap.add_argument("--expiry", default="")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--ledger", default="paper_trading/adaptive_ledger.csv")
    ap.add_argument("--signals", default="paper_trading/adaptive_signals.csv")
    ap.add_argument("--candidate-screen", default="paper_trading/adaptive_candidate_screen.csv")
    ap.add_argument("--feature-history", default="paper_trading/adaptive_feature_history.csv")
    ap.add_argument("--site-dir", default="site/adaptive")
    ap.add_argument("--telegram-all-runs", action="store_true")
    args = ap.parse_args()

    if args.capital <= 0 or not (0 < args.risk_pct < 1):
        raise SystemExit("capital must be >0 and risk-pct must be between 0 and 1.")
    if args.lot_size <= 0 or args.paths < 100 or args.lookback < 60:
        raise SystemExit("Invalid lot-size/paths/lookback.")

    current = now_ist()
    decision = pd.Timestamp(current.date() if args.decision_date == "auto" else args.decision_date).normalize()
    if decision.date() != current.date():
        raise SystemExit("Prospective producer only supports today's decision date.")

    client = NSEClient()
    holidays = client.fetch_holidays()
    index_df = client.fetch_index_history(
        (decision - pd.Timedelta(days=365 * 5)).date(),
        decision.date(),
    )
    index_df["date"] = pd.to_datetime(index_df["date"]).dt.normalize()
    index_df["close"] = pd.to_numeric(index_df["close"], errors="coerce")
    index_df = index_df.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)

    prior = index_df.loc[index_df["date"] < decision].copy()
    if prior.empty:
        raise RuntimeError("No completed NIFTY session is available before decision date.")
    model_cutoff = pd.Timestamp(prior["date"].max()).normalize()
    spot = float(prior.loc[prior["date"].eq(model_cutoff), "close"].iloc[-1])
    regime = compute_volatility_regime(index_df, model_cutoff, args.rank_lookback)

    ledger_path = Path(args.ledger)
    signals_path = Path(args.signals)
    candidate_path = Path(args.candidate_screen)
    feature_path = Path(args.feature_history)
    ledger = read_csv(ledger_path, LEDGER_COLUMNS)
    signals = read_csv(signals_path, SIGNAL_COLUMNS)
    candidates = read_csv(candidate_path, CANDIDATE_COLUMNS)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    feature_path.parent.mkdir(parents=True, exist_ok=True)

    closures = calculate_realized_for_open_trades(ledger, index_df, decision)
    ledger = apply_closures(ledger, closures)

    feature_row = {
        "decision_date": decision.date().isoformat(),
        "model_data_cutoff": model_cutoff.date().isoformat(),
        "spot": spot,
        "rv20": regime["rv20"],
        "rv20_rank": regime["rv20_rank"],
        "vol_regime": regime["vol_regime"],
        "run_timestamp_ist": current.isoformat(),
    }
    feature_df = pd.read_csv(feature_path) if feature_path.exists() else pd.DataFrame()
    if "decision_date" not in feature_df.columns or feature_row["decision_date"] not in set(feature_df.get("decision_date", pd.Series(dtype=str)).astype(str)):
        feature_df = pd.concat([feature_df, pd.DataFrame([feature_row])], ignore_index=True)
        feature_df.to_csv(feature_path, index=False)

    latest: dict[str, Any] = {
        "producer": "Adaptive Paper Signal Producer v1",
        "run_timestamp_ist": current.isoformat(),
        "decision_date": decision.date().isoformat(),
        "model_data_cutoff": model_cutoff.date().isoformat(),
        "spot": spot,
        "spot_source": "NIFTY prior completed session close",
        "vol_regime": regime["vol_regime"],
        "rv20": float(regime["rv20"]),
        "rv20_rank": float(regime["rv20_rank"]),
        "status": "NO_TRADE",
        "signal": "NO_TRADE",
        "target_expiry": "",
        "quote_retrieved_at_ist": "",
        "horizon_sessions": 0,
        "mc_paths": args.paths,
        "lookback_sessions": args.lookback,
        "stress_cost_points_per_contract": args.cost_per_contract,
        "primary_strategy": "",
        "primary_net_ev_points": None,
        "primary_mc_ev_gross": None,
        "primary_entry_cost_points": None,
        "primary_mc_pop": None,
        "primary_es95_points": None,
        "primary_es99_points": None,
        "primary_recommended_lots": 0,
        "primary_contracts_per_lot": None,
        "primary_risk_points_per_lot": None,
        "primary_risk_budget_inr": float(args.capital * args.risk_pct),
        "primary_estimated_risk_inr_per_lot": None,
        "primary_minimum_capital_inr": None,
        "primary_entry_cashflow_points": None,
        "primary_strikes": {},
        "primary_legs": [],
        "candidate_count": 0,
        "eligible_candidate_count": 0,
        "mc_terminal_quantiles": {},
        "notes": "",
    }

    today_is_session = decision.weekday() < 5 and decision not in holidays
    if not today_is_session:
        latest["status"] = "NOT_TRADING_DAY"
        latest["notes"] = "Decision date is not a NIFTY trading session; no option-chain request was made."
    elif current.time() < ENTRY_TIME_IST:
        latest["status"] = "WAITING_FOR_ENTRY_TIME"
        latest["notes"] = "Entry processing starts at the fixed 09:30 IST entry time."
    else:
        requested_expiry = pd.Timestamp(args.expiry).normalize() if args.expiry else None
        chain, _, _, expiry = client.fetch_option_chain(requested_expiry)
        quote_time = now_ist()
        future_sessions = trading_sessions_between(decision, expiry, holidays)
        future_sessions = future_sessions[future_sessions > decision]
        latest["target_expiry"] = expiry.date().isoformat()
        latest["quote_retrieved_at_ist"] = quote_time.isoformat()

        if len(future_sessions) != 3:
            latest["status"] = "NOT_ENTRY_DAY"
            latest["notes"] = (
                f"Frozen entry rule requires exactly 3 future trading sessions before the front expiry; "
                f"found {len(future_sessions)}."
            )
        else:
            returns = (
                np.log(prior["close"]).diff().dropna().tail(args.lookback).to_numpy(float)
            )
            if len(returns) < args.lookback:
                raise RuntimeError(f"Need {args.lookback} historical returns; found {len(returns)}.")
            seed = args.seed if args.seed is not None else deterministic_seed(decision)
            terminal = mc_paths(spot, returns, len(future_sessions), args.paths, seed)
            q20, q35, q65, q80 = np.percentile(terminal, [20, 35, 65, 80])
            latest["status"] = "ENTRY_DAY"
            latest["horizon_sessions"] = int(len(future_sessions))
            latest["mc_terminal_quantiles"] = {
                "p20": float(q20), "p35": float(q35), "p65": float(q65), "p80": float(q80)
            }

            rows: list[dict[str, Any]] = []
            for strategy in CANDIDATES_BY_REGIME[str(regime["vol_regime"])]:
                freq = CPCV_FREQUENCY[regime["vol_regime"]][strategy]
                try:
                    m = candidate_metrics(
                        strategy, terminal, spot, chain, expiry,
                        args.lot_size, args.capital, args.risk_pct, args.cost_per_contract, freq,
                    )
                    rows.append(m)
                except Exception as exc:
                    rows.append({
                        "strategy": strategy,
                        "cpcv_frequency": freq,
                        "p20_terminal": float(q20), "p35_terminal": float(q35),
                        "p65_terminal": float(q65), "p80_terminal": float(q80),
                        "strikes": {}, "mc_ev_gross": None, "entry_cost_points": None,
                        "mc_ev_net": None, "mc_pop": None, "mc_es95": None, "mc_es99": None,
                        "contracts_per_lot": None, "risk_points_per_lot": None,
                        "risk_budget_inr": float(args.capital * args.risk_pct),
                        "estimated_risk_inr_per_lot": None, "minimum_capital_for_one_lot_inr": None,
                        "recommended_lots": 0, "eligible": False,
                        "eligibility_reason": f"DATA_ERROR:{exc}",
                        "entry_cashflow_points": None, "entry_price_source": "",
                        "legs": [],
                    })

            primary = select_primary_candidate([
                {
                    "strategy": r["strategy"],
                    "eligible": r["eligible"],
                    "net_ev": r["mc_ev_net"],
                    "cpcv_frequency": r["cpcv_frequency"],
                }
                for r in rows
                if r.get("mc_ev_net") is not None
            ])
            if primary:
                selected_strategy = primary["strategy"]
                selected = next(r for r in rows if r["strategy"] == selected_strategy)
                latest.update({
                    "signal": "ENTER",
                    "primary_strategy": selected["strategy"],
                    "primary_net_ev_points": float(selected["mc_ev_net"]),
                    "primary_mc_ev_gross": float(selected["mc_ev_gross"]),
                    "primary_entry_cost_points": float(selected["entry_cost_points"]),
                    "primary_mc_pop": float(selected["mc_pop"]),
                    "primary_es95_points": float(selected["mc_es95"]),
                    "primary_es99_points": float(selected["mc_es99"]),
                    "primary_recommended_lots": int(selected["recommended_lots"]),
                    "primary_contracts_per_lot": int(selected["contracts_per_lot"]),
                    "primary_risk_points_per_lot": float(selected["risk_points_per_lot"]),
                    "primary_risk_budget_inr": float(selected["risk_budget_inr"]),
                    "primary_estimated_risk_inr_per_lot": float(selected["estimated_risk_inr_per_lot"]),
                    "primary_minimum_capital_inr": float(selected["minimum_capital_for_one_lot_inr"]),
                    "primary_entry_cashflow_points": float(selected["entry_cashflow_points"]),
                    "primary_strikes": selected["strikes"],
                    "primary_legs": selected["legs"],
                    "eligible_candidate_count": int(sum(bool(r["eligible"]) for r in rows)),
                    "notes": (
                        "Primary paper candidate = highest net MC EV among eligible candidates in the "
                        "frozen regime candidate set. This primary-selection rule is prospective and "
                        "unvalidated; it is not a new historical backtest."
                    ),
                })
            else:
                latest["eligible_candidate_count"] = 0
                latest["signal"] = "NO_TRADE"
                latest["notes"] = (
                    "No regime candidate passed both the net MC EV > 0 gate and the one-lot risk-budget gate."
                )
            latest["candidate_count"] = len(rows)

            candidate_key_prefix = decision.date().isoformat()
            if not any(candidates["decision_date"].astype(str).eq(candidate_key_prefix)):
                candidate_rows = []
                for r in rows:
                    is_primary = bool(primary and r["strategy"] == primary["strategy"])
                    candidate_rows.append({
                        "run_timestamp_ist": current.isoformat(),
                        "decision_date": candidate_key_prefix,
                        "target_expiry": expiry.date().isoformat(),
                        "vol_regime": regime["vol_regime"],
                        "rv20": regime["rv20"],
                        "rv20_rank": regime["rv20_rank"],
                        "spot": spot,
                        "model_data_cutoff": model_cutoff.date().isoformat(),
                        "horizon_sessions": len(future_sessions),
                        "strategy": r["strategy"],
                        "cpcv_selection_frequency": r["cpcv_frequency"],
                        "p20_terminal": r["p20_terminal"],
                        "p35_terminal": r["p35_terminal"],
                        "p65_terminal": r["p65_terminal"],
                        "p80_terminal": r["p80_terminal"],
                        "strikes_json": json.dumps(r["strikes"], separators=(",", ":")),
                        "mc_ev_points_gross": r["mc_ev_gross"],
                        "entry_cost_points": r["entry_cost_points"],
                        "mc_ev_points_net": r["mc_ev_net"],
                        "mc_pop": r["mc_pop"],
                        "mc_es95_points": r["mc_es95"],
                        "mc_es99_points": r["mc_es99"],
                        "contracts_per_lot": r["contracts_per_lot"],
                        "risk_points_per_lot": r["risk_points_per_lot"],
                        "risk_budget_inr": r["risk_budget_inr"],
                        "estimated_risk_inr_per_lot": r["estimated_risk_inr_per_lot"],
                        "minimum_capital_for_one_lot_inr": r["minimum_capital_for_one_lot_inr"],
                        "recommended_lots": r["recommended_lots"],
                        "eligible": r["eligible"],
                        "eligibility_reason": r["eligibility_reason"],
                        "primary_selected": is_primary,
                        "entry_cashflow_points": r["entry_cashflow_points"],
                        "entry_price_source": r["entry_price_source"],
                        "legs_json": json.dumps(r["legs"], separators=(",", ":")),
                    })
                candidates = pd.concat([candidates, pd.DataFrame(candidate_rows)], ignore_index=True)

    signal_id = f"{decision.date().isoformat()}|{latest.get('target_expiry','')}|AdaptiveV1"
    latest["signal_id"] = signal_id
    latest["model_data_cutoff"] = model_cutoff.date().isoformat()

    signal_row = {
        "run_timestamp_ist": latest["run_timestamp_ist"],
        "decision_date": latest["decision_date"],
        "target_expiry": latest.get("target_expiry", ""),
        "status": latest["status"],
        "signal": latest["signal"],
        "vol_regime": latest["vol_regime"],
        "rv20": latest["rv20"],
        "rv20_rank": latest["rv20_rank"],
        "spot": latest["spot"],
        "model_data_cutoff": latest["model_data_cutoff"],
        "quote_retrieved_at_ist": latest.get("quote_retrieved_at_ist", ""),
        "horizon_sessions": latest.get("horizon_sessions", 0),
        "primary_strategy": latest.get("primary_strategy", ""),
        "primary_net_ev_points": latest.get("primary_net_ev_points"),
        "primary_mc_pop": latest.get("primary_mc_pop"),
        "primary_es95_points": latest.get("primary_es95_points"),
        "primary_es99_points": latest.get("primary_es99_points"),
        "primary_recommended_lots": latest.get("primary_recommended_lots", 0),
        "primary_contracts_per_lot": latest.get("primary_contracts_per_lot"),
        "primary_risk_points_per_lot": latest.get("primary_risk_points_per_lot"),
        "primary_risk_budget_inr": latest.get("primary_risk_budget_inr"),
        "primary_minimum_capital_inr": latest.get("primary_minimum_capital_inr"),
        "primary_entry_cashflow_points": latest.get("primary_entry_cashflow_points"),
        "primary_strikes_json": json.dumps(latest.get("primary_strikes", {}), separators=(",", ":")),
        "primary_legs_json": json.dumps(latest.get("primary_legs", []), separators=(",", ":")),
        "candidate_count": latest.get("candidate_count", 0),
        "eligible_candidate_count": latest.get("eligible_candidate_count", 0),
        "signal_id": signal_id,
        "notes": latest.get("notes", ""),
    }
    signals = append_once(signals, signal_row, "signal_id")

    if latest["signal"] == "ENTER" and latest.get("target_expiry"):
        if signal_id not in set(ledger["signal_id"].astype(str)):
            ledger = pd.concat([ledger, pd.DataFrame([{
                "signal_id": signal_id,
                "decision_date": latest["decision_date"],
                "expiry": latest["target_expiry"],
                "strategy": latest["primary_strategy"],
                "signal": latest["signal"],
                "regime": latest["vol_regime"],
                "spot": latest["spot"],
                "lot_size": args.lot_size,
                "lots": latest["primary_recommended_lots"],
                "risk_budget_inr": latest["primary_risk_budget_inr"],
                "mc_ev_points_net": latest["primary_net_ev_points"],
                "mc_pop": latest["primary_mc_pop"],
                "es95_points": latest["primary_es95_points"],
                "es99_points": latest["primary_es99_points"],
                "entry_cost_points": latest["primary_entry_cost_points"],
                "entry_cashflow_points_per_unit": latest["primary_entry_cashflow_points"],
                "legs_json": json.dumps(latest["primary_legs"], separators=(",", ":")),
                "entry_timestamp_ist": latest.get("quote_retrieved_at_ist", ""),
                "model_data_cutoff": latest["model_data_cutoff"],
                "quote_retrieved_at_ist": latest.get("quote_retrieved_at_ist", ""),
                "status": "OPEN",
                "exit_date": "",
                "exit_spot": "",
                "exit_intrinsic_points_per_unit": "",
                "realized_pnl_points_per_unit": "",
                "realized_pnl_inr": "",
                "notes": latest["notes"],
            }])], ignore_index=True)

    latest["closures"] = closures
    latest["paper_ledger_summary"] = summary_stats(ledger)
    Path(args.site_dir).mkdir(parents=True, exist_ok=True)
    build_site(Path(args.site_dir), latest, candidates, signals, ledger)

    signals.to_csv(signals_path, index=False)
    candidates.to_csv(candidate_path, index=False)
    ledger.to_csv(ledger_path, index=False)

    if latest["status"] in {"ENTRY_DAY", "DATA_UNAVAILABLE"} or closures or args.telegram_all_runs:
        send_telegram(telegram_message(latest))


if __name__ == "__main__":
    main()
