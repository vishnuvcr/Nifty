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
    "status": "BACKFILL_0940_NO_TRADE",
    "signal": "NO_TRADE",
    "decision_date": args.decision_date,
    "entry_time_ist": args.entry_time_ist,
    "workflow_finished_at_ist": datetime.now(IST).isoformat(),
    "historical_snapshot_available": False,
    "quote_snapshot_used": False,
    "future_outcome_used": False,
    "lookahead_safe": True,
    "backfill_only": True,
    "reason": "HISTORICAL_0940_EXECUTABLE_OPTION_SNAPSHOT_UNAVAILABLE",
    "source_note": args.source_note or "No trustworthy cached historical 09:40 IST executable option-chain snapshot was available. Current premiums/quotes were not substituted.",
}
Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
Path(args.output_json).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
