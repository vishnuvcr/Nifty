from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from batman_signal_producer import (
        NSEClient,
        apply_closures,
        calculate_realized_for_open_trades,
        now_ist,
        build_site as build_batman_site,
    )
    from adaptive_paper_signal_producer_v1 import (
        CANDIDATE_COLUMNS,
        SIGNAL_COLUMNS,
        build_site as build_adaptive_site,
        read_csv as adaptive_read_csv,
        summary_stats as adaptive_summary_stats,
    )
except ImportError:
    from scripts.batman_signal_producer import (
        NSEClient,
        apply_closures,
        calculate_realized_for_open_trades,
        now_ist,
        build_site as build_batman_site,
    )
    from scripts.adaptive_paper_signal_producer_v1 import (
        CANDIDATE_COLUMNS,
        SIGNAL_COLUMNS,
        build_site as build_adaptive_site,
        read_csv as adaptive_read_csv,
        summary_stats as adaptive_summary_stats,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh paper ledgers and publish dashboards without creating new entries.")
    ap.add_argument("--capital", type=float, default=100000.0)
    ap.add_argument("--refresh-cutoff", default="auto")
    ap.add_argument("--batman-ledger", default="paper_trading/batman_ledger.csv")
    ap.add_argument("--batman-signals", default="paper_trading/batman_signals.csv")
    ap.add_argument("--adaptive-ledger", default="paper_trading/adaptive_ledger.csv")
    ap.add_argument("--adaptive-signals", default="paper_trading/adaptive_signals.csv")
    ap.add_argument("--adaptive-candidates", default="paper_trading/adaptive_candidate_screen.csv")
    ap.add_argument("--adaptive-site", default="site/adaptive")
    ap.add_argument("--batman-site", default="site/batman")
    args = ap.parse_args()

    now = now_ist()
    cutoff = pd.Timestamp(now.date() if args.refresh_cutoff == "auto" else args.refresh_cutoff).normalize()

    client = NSEClient()
    index_df = client.fetch_index_history(
        (cutoff - pd.Timedelta(days=365 * 5)).date(),
        cutoff.date(),
    )
    index_df["date"] = pd.to_datetime(index_df["date"]).dt.normalize()
    index_df["close"] = pd.to_numeric(index_df["close"], errors="coerce")
    index_df = (
        index_df.dropna(subset=["date", "close"])
        .drop_duplicates("date")
        .sort_values("date")
        .reset_index(drop=True)
    )

    batman_ledger_path = Path(args.batman_ledger)
    batman_signals_path = Path(args.batman_signals)
    adaptive_ledger_path = Path(args.adaptive_ledger)
    adaptive_signals_path = Path(args.adaptive_signals)
    adaptive_candidates_path = Path(args.adaptive_candidates)

    batman_ledger = pd.read_csv(batman_ledger_path) if batman_ledger_path.exists() else pd.DataFrame()
    adaptive_ledger = (
        pd.read_csv(adaptive_ledger_path)
        if adaptive_ledger_path.exists()
        else pd.DataFrame()
    )

    batman_closures = calculate_realized_for_open_trades(batman_ledger, index_df, cutoff)
    adaptive_closures = calculate_realized_for_open_trades(adaptive_ledger, index_df, cutoff)

    batman_ledger = apply_closures(batman_ledger, batman_closures)
    adaptive_ledger = apply_closures(adaptive_ledger, adaptive_closures)

    if not batman_ledger_path.parent.exists():
        batman_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not adaptive_ledger_path.parent.exists():
        adaptive_ledger_path.parent.mkdir(parents=True, exist_ok=True)

    batman_ledger.to_csv(batman_ledger_path, index=False)
    adaptive_ledger.to_csv(adaptive_ledger_path, index=False)

    batman_signals = pd.read_csv(batman_signals_path) if batman_signals_path.exists() else pd.DataFrame()
    adaptive_signals = adaptive_read_csv(adaptive_signals_path, SIGNAL_COLUMNS)
    adaptive_candidates = adaptive_read_csv(adaptive_candidates_path, CANDIDATE_COLUMNS)

    batman_latest_path = Path(args.batman_site) / "data" / "latest_signal.json"
    adaptive_latest_path = Path(args.adaptive_site) / "data" / "adaptive_latest.json"

    if not batman_latest_path.exists() or not adaptive_latest_path.exists():
        raise SystemExit("Cannot refresh before both dashboard state files exist. Run the signal producers first.")

    batman_latest = json.loads(batman_latest_path.read_text(encoding="utf-8"))
    adaptive_latest = json.loads(adaptive_latest_path.read_text(encoding="utf-8"))

    batman_latest["last_refresh_timestamp_ist"] = now.isoformat()
    batman_latest["refresh_cutoff"] = cutoff.date().isoformat()
    batman_latest["refresh_closures"] = batman_closures
    adaptive_latest["last_refresh_timestamp_ist"] = now.isoformat()
    adaptive_latest["refresh_cutoff"] = cutoff.date().isoformat()
    adaptive_latest["refresh_closures"] = adaptive_closures
    adaptive_latest["paper_ledger_summary"] = adaptive_summary_stats(adaptive_ledger)

    batman_latest_path.write_text(json.dumps(batman_latest, indent=2, default=str), encoding="utf-8")
    adaptive_latest_path.write_text(json.dumps(adaptive_latest, indent=2, default=str), encoding="utf-8")

    build_batman_site(Path(args.batman_site), batman_latest, batman_signals, batman_ledger)
    build_adaptive_site(
        Path(args.adaptive_site),
        adaptive_latest,
        adaptive_candidates,
        adaptive_signals,
        adaptive_ledger,
    )

    metadata = {
        "refresh_timestamp_ist": now.isoformat(),
        "refresh_cutoff": cutoff.date().isoformat(),
        "mode": "refresh_only_no_new_entries",
        "batman_closures": len(batman_closures),
        "adaptive_closures": len(adaptive_closures),
    }
    Path(args.adaptive_site, "data", "refresh_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
