from __future__ import annotations

import argparse
import html
import json
import math
import os
import zlib
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd
from curl_cffi import requests

from nifty_mc.strategy_catalog import build_strategy
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

ENTRY_TIME_IST = time(9, 30)
MC_PATHS_DEFAULT = 5000
LOOKBACK_DEFAULT = 756
RANK_LOOKBACK_DEFAULT = 252
STRESS_COST_DEFAULT = 2.0
RISK_PCT_DEFAULT = 0.02
LOT_SIZE_DEFAULT = 65

SIGNAL_COLUMNS = [
    "run_timestamp_ist","entry_timestamp_ist","decision_date","model_data_cutoff",
    "quote_retrieved_at_ist","target_expiry","status","signal","strategy",
    "direction_regime","vol_regime","trend60_rank","p_expand_rank","rv20_rank",
    "filter_reason","spot","mc_paths","lookback_sessions","horizon_sessions",
    "p20_terminal","p35_terminal","p65_terminal","p80_terminal",
    "strategy_strikes_json","mc_ev_points_gross","entry_cost_points",
    "mc_ev_points_net","mc_pop","mc_es95_points","mc_es99_points","lot_size",
    "contracts_per_strategy_lot","risk_points_per_lot","risk_budget_inr",
    "estimated_risk_inr_per_lot","minimum_capital_for_one_lot_inr",
    "recommended_lots","entry_cashflow_points_per_unit","entry_price_source",
    "signal_id","notes",
]

LEDGER_COLUMNS = [
    "signal_id","decision_date","expiry","strategy","signal","spot","lot_size",
    "lots","risk_budget_inr","mc_ev_points_net","mc_pop","es95_points","es99_points",
    "entry_cost_points","entry_cashflow_points_per_unit","entry_timestamp_ist",
    "model_data_cutoff","quote_retrieved_at_ist","legs_json","status","exit_date",
    "exit_spot","exit_intrinsic_points_per_unit","realized_pnl_points_per_unit",
    "realized_pnl_inr","notes",
]


def deterministic_seed(decision_date: pd.Timestamp) -> int:
    return 100000 + zlib.crc32(f"adaptive|{decision_date.date()}".encode("utf-8")) % 900000


def read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(path)


def unique_targets(chain: pd.DataFrame, targets: dict[str, float]) -> dict[str, float]:
    strikes = np.sort(np.unique(chain["strike"].dropna().to_numpy(float)))
    if len(strikes) < len(targets):
        raise ValueError("Not enough unique listed strikes for the selected strategy.")
    used: set[float] = set()
    out: dict[str, float] = {}
    for label, target in sorted(targets.items(), key=lambda x: x[1]):
        pick = None
        for idx in np.argsort(np.abs(strikes - target)):
            value = float(strikes[idx])
            if value not in used:
                pick = value
                break
        if pick is None:
            raise ValueError(f"Unable to map unique strike for {label}.")
        out[label] = pick
        used.add(pick)
    return out


def feature_values(index_df: pd.DataFrame, cutoff: pd.Timestamp, spot: float, terminal: np.ndarray) -> dict[str, float]:
    s = index_df.loc[index_df["date"] <= cutoff, "close"].to_numpy(float)
    r = np.log(index_df.loc[index_df["date"] <= cutoff, "close"]).diff().dropna().to_numpy(float)
    if len(s) < 61 or len(r) < 60:
        raise ValueError("Insufficient history for trend/volatility features.")
    return {
        "rv20": float(np.std(r[-20:], ddof=1) * np.sqrt(252)),
        "trend20": float(s[-1] / s[-21] - 1.0),
        "trend60": float(s[-1] / s[-61] - 1.0),
        "p_expand": float(np.mean(np.abs(terminal / float(spot) - 1.0) >= 0.015)),
    }


def trailing_rank(history: pd.Series, value: float, window: int) -> float | None:
    h = pd.to_numeric(history, errors="coerce").dropna().to_numpy(float)[-window:]
    if len(h) < 30 or not np.isfinite(value):
        return None
    return float(np.mean(h <= value))


def regime_class(vol_rank: float | None) -> str:
    if vol_rank is None:
        return "unknown"
    if vol_rank <= 1 / 3:
        return "low"
    if vol_rank <= 2 / 3:
        return "medium"
    return "high"


def strategy_for_regime(
    vol_regime: str,
    p_expand_rank: float | None,
    trend60_rank: float | None,
) -> tuple[str | None, str]:
    if vol_regime == "high":
        if p_expand_rank is not None and p_expand_rank < 0.50:
            return "Short Strangle", "high_vol_p_expand_filter_pass"
        return None, "high_vol_p_expand_filter_block"
    if vol_regime == "medium":
        if trend60_rank is not None and trend60_rank > 0.20:
            return "Sell Put", "medium_vol_trend60_filter_pass"
        return None, "medium_vol_trend60_filter_block"
    if vol_regime == "low":
        return None, "low_volatility_no_trade"
    return None, "insufficient_feature_history"


def build_option_signal(
    strategy: str,
    spot: float,
    terminal: np.ndarray,
    chain: pd.DataFrame,
    expiry: pd.Timestamp,
    lot_size: int,
    capital: float,
    risk_pct: float,
    cost_per_contract: float,
) -> dict:
    qs = np.percentile(terminal, [20, 35, 65, 80])
    if strategy == "Short Strangle":
        targets = {"p35": float(qs[1]), "c65": float(qs[2])}
    elif strategy == "Sell Put":
        targets = {"atm": float(spot)}
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    strikes = unique_targets(chain.loc[chain.expiry.eq(expiry)], targets)
    legs = build_strategy(strategy, strikes)

    entry_cashflow = 0.0
    contract_count = 0
    pnl = np.zeros(len(terminal), dtype=float)
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
        intrinsic = (
            np.maximum(terminal - leg.strike, 0.0)
            if leg.option_type == "CE"
            else np.maximum(leg.strike - terminal, 0.0)
        )
        pnl += float(leg.qty) * intrinsic

    pnl += entry_cashflow
    entry_cost_points = float(cost_per_contract * contract_count)
    net_pnl = pnl - entry_cost_points
    q05 = float(np.quantile(net_pnl, 0.05))
    q01 = float(np.quantile(net_pnl, 0.01))
    es95 = float(max(0.0, -np.mean(net_pnl[net_pnl <= q05])))
    es99 = float(max(0.0, -np.mean(net_pnl[net_pnl <= q01])))
    risk_points = max(es95, es99)
    risk_per_lot = risk_points * lot_size
    risk_budget = capital * risk_pct
    lots = int(math.floor(risk_budget / risk_per_lot)) if risk_per_lot > 0 else 0

    return {
        "strategy": strategy,
        "strikes": strikes,
        "p20_terminal": float(qs[0]),
        "p35_terminal": float(qs[1]),
        "p65_terminal": float(qs[2]),
        "p80_terminal": float(qs[3]),
        "mc_ev_gross": float(np.mean(pnl)),
        "entry_cost_points": entry_cost_points,
        "mc_ev_net": float(np.mean(net_pnl)),
        "mc_pop": float(np.mean(net_pnl > 0)),
        "mc_es95": es95,
        "mc_es99": es99,
        "contracts": contract_count,
        "risk_points": risk_points,
        "risk_budget_inr": risk_budget,
        "estimated_risk_inr_per_lot": float(risk_per_lot),
        "minimum_capital_for_one_lot_inr": float(risk_per_lot / risk_pct) if risk_pct > 0 else math.inf,
        "recommended_lots": lots,
        "entry_cashflow": float(entry_cashflow),
        "entry_price_source": ",".join(sorted({str(x["quote_source"]) for x in priced_legs})),
        "legs": priced_legs,
        "signal": "ENTER" if np.mean(net_pnl) > 0 and lots >= 1 else "NO_TRADE",
    }


def build_html(latest: dict, signals: pd.DataFrame, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    legs = latest.get("legs", [])
    leg_rows = "".join(
        f"<tr><td>{html.escape(str(x.get('side')))}</td><td>{html.escape(str(x.get('option_type')))}</td>"
        f"<td>{x.get('strike')}</td><td>{x.get('quantity_per_lot')}</td><td>{x.get('premium_points')}</td></tr>"
        for x in legs
    )
    recent = signals.tail(25).iloc[::-1] if not signals.empty else signals
    rows = "".join(
        f"<tr><td>{row.get('decision_date')}</td><td>{row.get('strategy')}</td><td>{row.get('vol_regime')}</td>"
        f"<td>{row.get('status')}</td><td>{row.get('signal')}</td><td>{row.get('mc_ev_points_net')}</td>"
        f"<td>{row.get('recommended_lots')}</td></tr>"
        for _, row in recent.iterrows()
    )
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Adaptive Regime Signal</title>
<style>body{{font-family:system-ui;margin:0;background:#0d1117;color:#e6edf3}}main{{max-width:1100px;margin:auto;padding:24px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:14px 0}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:8px;border-bottom:1px solid #30363d;text-align:left}}
pre{{white-space:pre-wrap;word-break:break-word}}</style></head><body><main>
<h1>Adaptive Regime Signal Producer</h1>
<div class="card"><h2>Latest</h2><pre>{html.escape(json.dumps(latest, indent=2, default=str))}</pre></div>
<div class="card"><h2>Selected legs</h2><table><tr><th>Side</th><th>Type</th><th>Strike</th><th>Qty</th><th>Premium</th></tr>{leg_rows}</table></div>
<div class="card"><h2>Recent signals</h2><table><tr><th>Date</th><th>Strategy</th><th>Vol</th><th>Status</th><th>Signal</th><th>Net EV</th><th>Lots</th></tr>{rows}</table></div>
</main></body></html>"""
    (out / "index.html").write_text(page, encoding="utf-8")


def telegram_message(latest: dict, closures: list[dict[str, object]]) -> str:
    lines = [
        "🤖 ADAPTIVE REGIME SIGNAL",
        f"Date: {latest.get('decision_date')}",
        f"Expiry: {latest.get('target_expiry') or '—'}",
        f"Regime: {latest.get('vol_regime')}",
        f"Strategy: {latest.get('strategy') or 'NO_TRADE'}",
        f"Status: {latest.get('status')} | Signal: {latest.get('signal')}",
        f"Filter: {latest.get('filter_reason')}",
        f"Model cutoff: {latest.get('model_data_cutoff') or '—'}",
    ]
    if latest.get("mc_ev_points_net") is not None:
        lines += [
            f"MC EV net: {latest['mc_ev_points_net']:.2f} pts",
            f"MC POP: {latest['mc_pop']:.1%}",
            f"ES95/99: {latest['mc_es95_points']:.2f}/{latest['mc_es99_points']:.2f} pts",
            f"Lots: {latest.get('recommended_lots')}",
        ]
    for e in closures:
        lines.append(f"✅ CLOSED {e['exit_date']} | P&L ₹{float(e['realized_pnl_inr']):,.2f}")
    return "\n".join(lines)


def send_telegram(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        print("TELEGRAM_NOT_CONFIGURED")
        return
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": message, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()


def main() -> None:
    ap = argparse.ArgumentParser(description="Prospective adaptive regime strategy signal producer")
    ap.add_argument("--capital", type=float, default=100000.0)
    ap.add_argument("--risk-pct", type=float, default=RISK_PCT_DEFAULT)
    ap.add_argument("--lot-size", type=int, default=LOT_SIZE_DEFAULT)
    ap.add_argument("--paths", type=int, default=MC_PATHS_DEFAULT)
    ap.add_argument("--lookback", type=int, default=LOOKBACK_DEFAULT)
    ap.add_argument("--rank-lookback", type=int, default=RANK_LOOKBACK_DEFAULT)
    ap.add_argument("--cost-per-contract", type=float, default=STRESS_COST_DEFAULT)
    ap.add_argument("--decision-date", default="auto")
    ap.add_argument("--expiry", default="")
    ap.add_argument("--history-seed", default="")
    ap.add_argument("--feature-history", default="paper_trading/adaptive_feature_history.csv")
    ap.add_argument("--ledger", default="paper_trading/adaptive_regime_ledger.csv")
    ap.add_argument("--signals", default="paper_trading/adaptive_regime_signals.csv")
    ap.add_argument("--site-dir", default="site/adaptive")
    ap.add_argument(
        "--enable-experimental-routing",
        action="store_true",
        help="Enable the currently-unvalidated adaptive router. Disabled by default.",
    )
    args = ap.parse_args()

    client = NSEClient()
    current = now_ist()
    decision = current.date() if args.decision_date == "auto" else pd.Timestamp(args.decision_date).date()
    decision_ts = pd.Timestamp(decision).normalize()

    holidays = client.fetch_holidays()
    index_start = decision_ts - pd.Timedelta(days=2200)
    index_df = client.fetch_index_history(index_start.date(), decision)
    index_df["date"] = pd.to_datetime(index_df["date"]).dt.normalize()
    index_df = index_df.drop_duplicates("date").sort_values("date").reset_index(drop=True)

    signal_path = Path(args.signals)
    ledger_path = Path(args.ledger)
    feature_path = Path(args.feature_history)
    signals = read_csv(signal_path, SIGNAL_COLUMNS)
    ledger = read_csv(ledger_path, LEDGER_COLUMNS)

    closures = calculate_realized_for_open_trades(ledger, index_df, decision_ts)
    ledger = apply_closures(ledger, closures)

    base = {
        "run_timestamp_ist": current.isoformat(),
        "entry_timestamp_ist": "",
        "decision_date": decision_ts.date().isoformat(),
        "model_data_cutoff": "",
        "quote_retrieved_at_ist": "",
        "target_expiry": "",
        "status": "NO_TRADE",
        "signal": "NO_TRADE",
        "strategy": "",
        "direction_regime": "neutral",
        "vol_regime": "unknown",
        "trend60_rank": None,
        "p_expand_rank": None,
        "rv20_rank": None,
        "filter_reason": "",
        "spot": None,
        "mc_paths": args.paths,
        "lookback_sessions": args.lookback,
        "horizon_sessions": 0,
        "p20_terminal": None,
        "p35_terminal": None,
        "p65_terminal": None,
        "p80_terminal": None,
        "strategy_strikes_json": "{}",
        "mc_ev_points_gross": None,
        "entry_cost_points": None,
        "mc_ev_points_net": None,
        "mc_pop": None,
        "mc_es95_points": None,
        "mc_es99_points": None,
        "lot_size": args.lot_size,
        "contracts_per_strategy_lot": None,
        "risk_points_per_lot": None,
        "risk_budget_inr": args.capital * args.risk_pct,
        "estimated_risk_inr_per_lot": None,
        "minimum_capital_for_one_lot_inr": None,
        "recommended_lots": 0,
        "entry_cashflow_points_per_unit": None,
        "entry_price_source": "",
        "signal_id": f"{decision_ts.date().isoformat()}|adaptive",
        "notes": "",
    }

    decision_is_session = (
        decision_ts in set(index_df["date"])
        and decision_ts not in holidays
        and decision_ts.weekday() < 5
    )

    if not decision_is_session:
        base["status"] = "NOT_TRADING_DAY"
        base["notes"] = "Decision date is not a NIFTY trading session; no entry signal was evaluated."
    elif args.decision_date == "auto" and current.time() < ENTRY_TIME_IST:
        base["status"] = "BEFORE_ENTRY_TIME"
        base["notes"] = "Processing is held until 09:30 IST."
    else:
        contract_info = client.get_json("/api/option-chain-contract-info", params={"symbol": "NIFTY"})
        expiry_dates = [
            pd.Timestamp(x).normalize()
            for x in (contract_info.get("expiryDates") or [])
            if not pd.isna(pd.to_datetime(x, errors="coerce"))
        ]
        if args.expiry:
            expiry_dates = [pd.Timestamp(args.expiry).normalize()]

        chosen_expiry = None
        chosen_sessions = None
        for expiry in expiry_dates:
            if expiry <= decision_ts:
                continue
            sessions = trading_sessions_between(decision_ts, expiry, holidays)
            future = sessions[sessions > decision_ts]
            if len(future) == 3 and expiry in set(sessions):
                chosen_expiry = expiry
                chosen_sessions = future
                break

        if chosen_expiry is None:
            base["status"] = "NOT_ENTRY_DAY"
            base["filter_reason"] = "no_expiry_with_exactly_3_future_sessions"
            base["notes"] = "Frozen rule requires exactly three future trading sessions through the selected expiry."
        else:
            chain, underlying, endpoint, _ = client.fetch_option_chain(chosen_expiry)
            if underlying is not None:
                spot = float(underlying)
            else:
                eligible_spot = index_df.loc[index_df["date"] <= decision_ts, "close"]
                if eligible_spot.empty:
                    raise RuntimeError("No usable NIFTY spot was returned by NSE and no index close fallback is available.")
                spot = float(eligible_spot.iloc[-1])

            prev = index_df[index_df["date"] < decision_ts]
            if prev.empty:
                raise RuntimeError("No completed session exists before decision date.")
            cutoff = pd.Timestamp(prev.iloc[-1]["date"]).normalize()
            returns = (
                np.log(index_df.loc[index_df["date"] <= cutoff, "close"])
                .diff()
                .dropna()
                .tail(args.lookback)
                .to_numpy(float)
            )
            if len(returns) < args.lookback:
                raise RuntimeError(f"Need {args.lookback} historical returns, found {len(returns)}.")

            terminal = mc_paths(
                spot, returns, len(chosen_sessions), args.paths, deterministic_seed(decision_ts)
            )
            feats = feature_values(index_df, cutoff, spot, terminal)

            seed = pd.DataFrame()
            if args.history_seed and Path(args.history_seed).exists():
                seed = pd.read_csv(args.history_seed, parse_dates=["decision_date"])
                keep = [c for c in ["decision_date", "trend20", "trend60", "rv20", "p_expand"] if c in seed.columns]
                seed = seed[keep].copy()

            live = read_csv(feature_path, ["decision_date", "trend20", "trend60", "rv20", "p_expand"])
            if not live.empty:
                live["decision_date"] = pd.to_datetime(live["decision_date"])

            if seed.empty and live.empty:
                hist = pd.DataFrame(columns=["decision_date", "trend20", "trend60", "rv20", "p_expand"])
            else:
                hist = pd.concat([seed, live], ignore_index=True)

            hist["decision_date"] = pd.to_datetime(hist["decision_date"]).dt.normalize()
            hist = (
                hist[hist["decision_date"] < decision_ts]
                .drop_duplicates("decision_date")
                .sort_values("decision_date")
            )

            ranks = {
                "trend60_rank": trailing_rank(hist["trend60"], feats["trend60"], args.rank_lookback),
                "p_expand_rank": trailing_rank(hist["p_expand"], feats["p_expand"], args.rank_lookback),
                "rv20_rank": trailing_rank(hist["rv20"], feats["rv20"], args.rank_lookback),
            }

            vol_regime = regime_class(ranks["rv20_rank"])
            strategy, filter_reason = strategy_for_regime(
                vol_regime, ranks["p_expand_rank"], ranks["trend60_rank"]
            )

            base.update({
                "entry_timestamp_ist": current.isoformat() if args.decision_date == "auto" else "",
                "model_data_cutoff": cutoff.date().isoformat(),
                "quote_retrieved_at_ist": current.isoformat(),
                "target_expiry": chosen_expiry.date().isoformat(),
                "status": "ENTRY_DAY",
                "spot": spot,
                "horizon_sessions": len(chosen_sessions),
                "trend60_rank": ranks["trend60_rank"],
                "p_expand_rank": ranks["p_expand_rank"],
                "rv20_rank": ranks["rv20_rank"],
                "vol_regime": vol_regime,
                "filter_reason": filter_reason,
                "strategy": strategy or "",
                "signal_id": f"{decision_ts.date().isoformat()}|{chosen_expiry.date().isoformat()}|adaptive",
                "notes": (
                    f"Prospective protocol: model cutoff={cutoff.date()}, entry snapshot={current.isoformat()}, "
                    f"exact 3-session expiry rule, MC seed={deterministic_seed(decision_ts)}, endpoint={endpoint}."
                ),
            })

            if strategy is not None and all(v is not None for v in ranks.values()):
                metrics = build_option_signal(
                    strategy,
                    spot,
                    terminal,
                    chain,
                    chosen_expiry,
                    args.lot_size,
                    args.capital,
                    args.risk_pct,
                    args.cost_per_contract,
                )
                base.update({
                    "p20_terminal": metrics["p20_terminal"],
                    "p35_terminal": metrics["p35_terminal"],
                    "p65_terminal": metrics["p65_terminal"],
                    "p80_terminal": metrics["p80_terminal"],
                    "strategy_strikes_json": json.dumps(metrics["strikes"], sort_keys=True),
                    "mc_ev_points_gross": metrics["mc_ev_gross"],
                    "entry_cost_points": metrics["entry_cost_points"],
                    "mc_ev_points_net": metrics["mc_ev_net"],
                    "mc_pop": metrics["mc_pop"],
                    "mc_es95_points": metrics["mc_es95"],
                    "mc_es99_points": metrics["mc_es99"],
                    "contracts_per_strategy_lot": metrics["contracts"],
                    "risk_points_per_lot": metrics["risk_points"],
                    "risk_budget_inr": metrics["risk_budget_inr"],
                    "estimated_risk_inr_per_lot": metrics["estimated_risk_inr_per_lot"],
                    "minimum_capital_for_one_lot_inr": metrics["minimum_capital_for_one_lot_inr"],
                    "recommended_lots": metrics["recommended_lots"],
                    "entry_cashflow_points_per_unit": metrics["entry_cashflow"],
                    "entry_price_source": metrics["entry_price_source"],
                    "signal": metrics["signal"],
                    "legs": metrics["legs"],
                })
                if not args.enable_experimental_routing:
                    base["signal"] = "NO_TRADE"
                    base["status"] = "RESEARCH_OBSERVATION_ONLY"
                    base["recommended_lots"] = 0
                    base["filter_reason"] = "adaptive_router_not_promoted_after_nested_2026_holdout"
                    base["notes"] += " Experimental routing is disabled; this run records features and candidate metrics only."
            else:
                base["notes"] += " No strategy passed the regime filter or feature-history requirement; NO_TRADE."

            row = pd.DataFrame([{
                "decision_date": decision_ts,
                "trend20": feats["trend20"],
                "trend60": feats["trend60"],
                "rv20": feats["rv20"],
                "p_expand": feats["p_expand"],
            }])
            if live.empty:
                live = row
            else:
                live = pd.concat([live, row], ignore_index=True)
            live["decision_date"] = pd.to_datetime(live["decision_date"]).dt.strftime("%Y-%m-%d")
            feature_path.parent.mkdir(parents=True, exist_ok=True)
            live.drop_duplicates("decision_date").sort_values("decision_date").to_csv(feature_path, index=False)

    # Always materialize the feature-history file so NO_TRADE/non-session runs
    # still produce a complete paper-trading state artifact.
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    if not feature_path.exists():
        pd.DataFrame(columns=["decision_date", "trend20", "trend60", "rv20", "p_expand"]).to_csv(
            feature_path, index=False
        )

    signal_row = {k: base.get(k) for k in SIGNAL_COLUMNS}
    if signal_row["signal_id"] not in set(signals.get("signal_id", pd.Series(dtype=str)).astype(str)):
        signals = pd.concat([signals, pd.DataFrame([signal_row])], ignore_index=True)
        signal_path.parent.mkdir(parents=True, exist_ok=True)
        signals.to_csv(signal_path, index=False)

    if base.get("status") == "ENTRY_DAY" and base.get("target_expiry") and base.get("strategy"):
        ids = set(ledger.get("signal_id", pd.Series(dtype=str)).astype(str))
        if base["signal_id"] not in ids:
            row = {
                "signal_id": base["signal_id"],
                "decision_date": base["decision_date"],
                "expiry": base["target_expiry"],
                "strategy": base.get("strategy", ""),
                "signal": base.get("signal", "NO_TRADE"),
                "spot": base.get("spot"),
                "lot_size": args.lot_size,
                "lots": base.get("recommended_lots", 0),
                "risk_budget_inr": base.get("risk_budget_inr", 0),
                "mc_ev_points_net": base.get("mc_ev_points_net"),
                "mc_pop": base.get("mc_pop"),
                "es95_points": base.get("mc_es95_points"),
                "es99_points": base.get("mc_es99_points"),
                "entry_cost_points": base.get("entry_cost_points", 0),
                "entry_cashflow_points_per_unit": base.get("entry_cashflow_points_per_unit"),
                "entry_timestamp_ist": base.get("entry_timestamp_ist", ""),
                "model_data_cutoff": base.get("model_data_cutoff", ""),
                "quote_retrieved_at_ist": base.get("quote_retrieved_at_ist", ""),
                "legs_json": json.dumps(base.get("legs", []), separators=(",", ":")),
                "status": "OPEN" if base.get("signal") == "ENTER" else "NO_TRADE",
                "exit_date": "",
                "exit_spot": "",
                "exit_intrinsic_points_per_unit": "",
                "realized_pnl_points_per_unit": "",
                "realized_pnl_inr": "",
                "notes": base.get("notes", ""),
            }
            ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(ledger_path, index=False)

    site_dir = Path(args.site_dir)
    build_html(base, signals, site_dir)
    (site_dir / "data").mkdir(parents=True, exist_ok=True)
    (site_dir / "data" / "latest_signal.json").write_text(
        json.dumps(base, indent=2, default=str), encoding="utf-8"
    )
    signals.to_csv(site_dir / "data" / "adaptive_regime_signals.csv", index=False)
    ledger.to_csv(site_dir / "data" / "adaptive_regime_ledger.csv", index=False)

    if base.get("status") in {"ENTRY_DAY", "DATA_UNAVAILABLE"} or closures:
        send_telegram(telegram_message(base, closures))

    print(json.dumps(base, indent=2, default=str))


if __name__ == "__main__":
    main()
