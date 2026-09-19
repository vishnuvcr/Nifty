from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd


COLUMNS = [
    "signal_id","decision_date","expiry","strategy","signal","spot",
    "mc_ev","mc_pop","es95","es99","lots","risk_budget_inr",
    "entry_cashflow_points","status","exit_date","exit_pnl_points",
    "realized_pnl_inr","notes"
]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--signal", required=True)
    ap.add_argument("--ledger", default="paper_trading/ledger.csv")
    ap.add_argument("--action", choices=["append","close"], default="append")
    ap.add_argument("--exit-pnl-points", type=float)
    ap.add_argument("--exit-date")
    ap.add_argument("--notes", default="")
    args=ap.parse_args()

    ledger=Path(args.ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if ledger.exists():
        df=pd.read_csv(ledger)
    else:
        df=pd.DataFrame(columns=COLUMNS)

    sig=json.loads(Path(args.signal).read_text())
    signal_id=f"{sig['decision_date']}|{sig['target_expiry']}|{sig['strategy']}"

    if args.action=="append":
        if signal_id in set(df.get("signal_id", [])):
            raise SystemExit(f"Signal already logged: {signal_id}")
        row={
            "signal_id":signal_id,
            "decision_date":sig["decision_date"],
            "expiry":sig["target_expiry"],
            "strategy":sig["strategy"],
            "signal":sig["signal"],
            "spot":sig["spot"],
            "mc_ev":sig["mc_expected_pnl_points_per_lot_unit"],
            "mc_pop":sig["mc_probability_profit"],
            "es95":sig["mc_es95_points"],
            "es99":sig["mc_es99_points"],
            "lots":sig["recommended_lots"],
            "risk_budget_inr":sig["risk_budget_inr"],
            "entry_cashflow_points":sig["entry_cashflow_points_per_strategy_unit"],
            "status":"OPEN" if sig["signal"]=="ENTER" else "NO_TRADE",
            "exit_date":"",
            "exit_pnl_points":"",
            "realized_pnl_inr":"",
            "notes":args.notes,
        }
        df=pd.concat([df,pd.DataFrame([row])],ignore_index=True)
    else:
        if signal_id not in set(df.get("signal_id", [])):
            raise SystemExit(f"Signal not found: {signal_id}")
        if args.exit_pnl_points is None or not args.exit_date:
            raise SystemExit("--exit-pnl-points and --exit-date are required for close")
        mask=df.signal_id.eq(signal_id)
        lots=float(df.loc[mask,"lots"].iloc[0])
        df.loc[mask,"status"]="CLOSED"
        df.loc[mask,"exit_date"]=args.exit_date
        df.loc[mask,"exit_pnl_points"]=args.exit_pnl_points
        df.loc[mask,"realized_pnl_inr"]=args.exit_pnl_points*65*lots
        df.loc[mask,"notes"]=args.notes

    df.to_csv(ledger,index=False)
    print(df.tail(10).to_string(index=False))


if __name__=="__main__":
    main()
