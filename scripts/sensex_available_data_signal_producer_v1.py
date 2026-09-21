from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.sensex_backtest_v1 import CANDIDATES_BY_REGIME, compute_regime, mc_terminal, strategy_targets
from scripts.sensex_paper_signal_producer_v1 import (
    DEFAULT_SEED,
    LOOKBACK,
    LOT_SIZE,
    MC_PATHS,
    RANK_LOOKBACK,
    RISK_BUDGET_INR,
    SLIPPAGE_POINTS,
    NoEligibleListedExpiry,
    fetch_index_history,
    fetch_live_sensex,
    fetch_option_chain,
    extract_live_spot_and_date,
    live_strategy_eval,
    make_signal_row,
    now_ist,
    third_future_weekday,
    write_json,
)

def data_limited_legs(strategy: str, terminal: np.ndarray, spot: float) -> list[dict[str, Any]]:
    targets = strategy_targets(strategy, terminal, spot)
    if strategy != "Batman":
        return []
    mapping = [
        ("BUY", "PE", "p35", 1),
        ("SELL", "PE", "p20", 2),
        ("BUY", "CE", "c65", 1),
        ("SELL", "CE", "c80", 2),
    ]
    return [
        {
            "side": side,
            "option_type": option_type,
            "target_label": label,
            "target_price": round(float(targets[label]), 2),
            "quantity_per_lot": qty,
            "quote_status": "UNAVAILABLE",
        }
        for side, option_type, label, qty in mapping
    ]

def append_row_union(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame([row])
    if not path.exists() or not path.stat().st_size:
        new.to_csv(path, index=False)
        return
    old = pd.read_csv(path)
    cols = list(dict.fromkeys([*old.columns.tolist(), *new.columns.tolist()]))
    old = old.reindex(columns=cols)
    new = new.reindex(columns=cols)
    combined = pd.concat([old, new], ignore_index=True)
    if "signal_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["signal_id"], keep="last")
    combined.to_csv(path, index=False)

def make_data_limited_row(
    strategy: str,
    decision_date: pd.Timestamp,
    expiry: pd.Timestamp,
    regime: dict[str, Any],
    spot: float,
    cutoff: pd.Timestamp,
    terminal: np.ndarray,
    timestamp: Any,
    reason: str,
    lookback_sessions_used: int,
) -> dict[str, Any]:
    row = {
        "signal_id": f"{decision_date.date()}|{expiry.date()}|{strategy}|DATA_LIMITED",
        "decision_date": str(decision_date.date()),
        "expiry": str(expiry.date()),
        "strategy": strategy,
        "signal": "DATA_LIMITED_CANDIDATE",
        "status": "DATA_LIMITED",
        "execution_status": "NOT_EXECUTABLE",
        "option_chain_available": False,
        "premium_available": False,
        "bid_ask_available": False,
        "quote_snapshot_used": False,
        "lookahead_safe": True,
        "regime": regime.get("vol_regime", "UNAVAILABLE"),
        "spot": float(spot),
        "lot_size": LOT_SIZE,
        "lots": 0,
        "risk_budget_inr": RISK_BUDGET_INR,
        "mc_ev_points_net": float("nan"),
        "mc_pop": float("nan"),
        "es95_points": float("nan"),
        "es99_points": float("nan"),
        "entry_slippage_points": SLIPPAGE_POINTS,
        "entry_cost_inr_expected": float("nan"),
        "entry_cashflow_points_per_unit": float("nan"),
        "legs_json": json.dumps(
            data_limited_legs("Batman", terminal, spot) if strategy == "Batman" else [],
            sort_keys=True,
        ),
        "entry_timestamp_ist": timestamp.isoformat(),
        "entry_observation_time_ist": "09:30",
        "model_data_cutoff": str(cutoff.date()),
        "model_lookback_sessions_used": int(lookback_sessions_used),
        "model_lookback_status": (
            "FULL_FROZEN_LOOKBACK" if lookback_sessions_used >= LOOKBACK else "DATA_LIMITED_SHORT_LOOKBACK"
        ),
        "quote_retrieved_at_ist": "",
        "selected_candidate": "",
        "candidate_screen_json": "[]",
        "publication_status": "DECISION_TIME_AVAILABLE_DATA_OBSERVATION",
        "data_quality_status": (
            "FULL_UNDERLYING_MODEL" if lookback_sessions_used >= LOOKBACK else "DATA_LIMITED_UNDERLYING_MODEL"
        ),
        "status_reason": reason,
        "target_strikes_source": "MC terminal quantiles; listed strike not verified",
        "notes": (
            "Available-data decision-time signal only. Underlying spot and past-only return "
            "history are available, but live option premiums/bid-ask are missing. No option "
            "premium, P&L, MC-EV or executable entry is claimed."
        ),
    }
    if strategy == "Adaptive":
        regime_name = regime.get("vol_regime", "UNAVAILABLE")
        if regime_name in CANDIDATES_BY_REGIME:
            candidates = [
                {"strategy": name, "regime": regime_name}
                for name in CANDIDATES_BY_REGIME[regime_name]
            ]
        else:
            candidates = [
                {"strategy": name, "regime": reg}
                for reg, names in CANDIDATES_BY_REGIME.items()
                for name in names
            ]
        row["candidate_screen_json"] = json.dumps(candidates, sort_keys=True)
        row["status_reason"] = (
            reason
            + "; Adaptive primary selection is withheld because highest net MC-EV "
            "cannot be computed without option premiums/bid-ask."
        )
    return row

def run_one(
    strategy: str,
    ledger: Path,
    output: Path,
    seed: int,
    fallback_spot: float | None = None,
) -> dict[str, Any]:
    ts = now_ist()
    decision_date = pd.Timestamp(ts.date()).normalize()
    history = fetch_index_history(
        decision_date - pd.Timedelta(days=2200),
        decision_date - pd.Timedelta(days=1),
    )
    if history.empty:
        raise RuntimeError("BSE SENSEX history returned no rows")
    cutoff = pd.Timestamp(history["date"].max()).normalize()
    returns = np.log(history["close"]).diff().dropna().to_numpy(float)
    if len(returns) < 10:
        raise RuntimeError(f"insufficient SENSEX return history: {len(returns)} rows")

    if fallback_spot is not None:
        spot = float(fallback_spot)
        live_date = decision_date
        spot_source = "workflow fallback input"
    else:
        live = fetch_live_sensex()
        spot, live_date = extract_live_spot_and_date(live)
        spot_source = "BSE public live SENSEX endpoint"
        if live_date.date() != decision_date.date():
            raise RuntimeError(
                f"BSE live SENSEX quote is dated {live_date.date()}, not {decision_date.date()}"
            )

    expiry = third_future_weekday(decision_date)
    terminal = mc_terminal(returns, spot, 3, MC_PATHS, seed)
    regime = compute_regime(history, cutoff, RANK_LOOKBACK)

    try:
        chain = fetch_option_chain(expiry)
    except (NoEligibleListedExpiry, RuntimeError, ValueError) as exc:
        row = make_data_limited_row(
            strategy,
            decision_date,
            expiry,
            regime,
            spot,
            cutoff,
            terminal,
            ts,
            f"{type(exc).__name__}: {exc}",
            min(LOOKBACK, len(returns)),
        )
        row["spot_source"] = spot_source
    else:
        if strategy == "Batman":
            evaluation = live_strategy_eval(
                "Batman", terminal, spot, chain, expiry, decision_date, seed
            )
            selected = "Batman"
        else:
            evaluations: list[dict[str, Any]] = []
            for candidate in CANDIDATES_BY_REGIME.get(regime["vol_regime"], []):
                try:
                    evaluations.append(
                        live_strategy_eval(
                            candidate, terminal, spot, chain, expiry, decision_date, seed
                        )
                    )
                except (RuntimeError, ValueError, KeyError) as exc:
                    evaluations.append(
                        {"strategy": candidate, "eligible": False, "error": str(exc)}
                    )
            eligible = [x for x in evaluations if x.get("eligible")]
            if not eligible:
                raise RuntimeError(
                    "no eligible frozen Adaptive candidate after executable quote/cost gates"
                )
            chosen = sorted(
                eligible,
                key=lambda x: (-float(x["mc_ev_points_net"]), str(x["strategy"])),
            )[0]
            evaluation = dict(chosen)
            evaluation["strategy"] = "Adaptive"
            selected = str(chosen["strategy"])

        row = make_signal_row(
            strategy,
            evaluation,
            decision_date,
            expiry,
            regime,
            spot,
            ts,
            cutoff,
        )
        row.update(
            {
                "execution_status": "PAPER_ONLY_EXECUTABLE_PROXY",
                "option_chain_available": True,
                "premium_available": True,
                "bid_ask_available": True,
                "quote_snapshot_used": True,
                "selected_candidate": selected,
                "spot_source": spot_source,
                "publication_status": "EXECUTABLE_QUOTE_OBSERVATION",
            }
        )

    append_row_union(ledger, row)
    payload = {
        "producer": "SENSEX available-data signal producer v2",
        "status": row["signal"],
        "signal": row,
        "decision_time_rule": "09:30 IST",
        "today_observation_date": str(decision_date.date()),
        "publication_note": (
            "DATA_LIMITED_CANDIDATE is a lookahead-safe decision-time observation, not an "
            "executable option trade. It is published when underlying/model data are "
            "available but option premiums/bid-ask are not."
        ),
    }
    write_json(output, payload)
    return payload

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["Batman", "Adaptive"], required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--fallback-spot", type=float, default=None)
    args = ap.parse_args()
    try:
        payload = run_one(
            args.strategy,
            Path(args.ledger),
            Path(args.output_json),
            args.seed,
            args.fallback_spot,
        )
        print(json.dumps(payload, indent=2, default=str))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
