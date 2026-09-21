#!/usr/bin/env python3
"""Create a look-ahead-safe 09:40 IST backfill observation."""
from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
ap = argparse.ArgumentParser()
ap.add_argument("--strategy", required=True)
ap.add_argument("--decision-date", required=True)
ap.add_argument("--entry-time-ist", required=True)
ap.add_argument("--output-json", required=True)
ap.add_argument("--source-note", default="")
args = ap.parse_args()

payload = {
    "producer": "Paper Trade Signals Producer  controlled 09:40 IST backfill",
    "strategy": args.strategy,
    "status": "BACKFILL_0940_NOT_EVALUATED",
    "signal": "NOT_EVALUATED",
    "decision_date": args.decision_date,
    "entry_time_ist": args.entry_time_ist,
    "workflow_finished_at_ist": datetime.now(IST).isoformat(),
    "historical_snapshot_available": False,
    "quote_snapshot_used": False,
    "future_outcome_used": False,
    "lookahead_safe": True,
    "backfill_only": True,
    "reason": "HISTORICAL_0940_EXECUTABLE_OPTION_SNAPSHOT_UNAVAILABLE",
    "source_note": args.source_note or "Historical 09:40 execution-grade option-chain data was unavailable through the repository/public sources available to this run. Current premiums/quotes were not substituted, so the strategy was not evaluated and the observation is not a NO_TRADE conclusion.",
}
Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
Path(args.output_json).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
