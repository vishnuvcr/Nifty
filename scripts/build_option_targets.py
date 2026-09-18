from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def _previous_session(sessions: pd.DatetimeIndex, candidate: pd.Timestamp) -> pd.Timestamp | None:
    x = sessions[sessions <= candidate]
    return x[-1] if len(x) else None


def expiry_candidates(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    dates = pd.date_range(start.normalize(), end.normalize(), freq="D")
    out = []
    for d in dates:
        if d < pd.Timestamp("2025-04-04"):
            if d.weekday() == 3:  # historical NIFTY weekly expiry: Thursday
                out.append(d)
        elif d < pd.Timestamp("2025-07-01"):
            # 2025 transition was not a simple weekday switch. The NSE
            # circular explicitly revised the existing April/May contracts.
            # Use the documented expiry dates, then Monday cadence after them.
            explicit = {
                pd.Timestamp("2025-04-11"),
                pd.Timestamp("2025-04-21"),
                pd.Timestamp("2025-05-05"),
            }
            if d in explicit or (
                d >= pd.Timestamp("2025-05-12") and d.weekday() == 0
            ):
                out.append(d)
        elif d < pd.Timestamp("2025-08-29"):
            # Existing contracts through Aug-28-2025 remained on Thursday.
            if d.weekday() == 3:
                out.append(d)
        else:
            # From the revised regime, NIFTY weekly expiry is Tuesday.
            if d.weekday() == 1:
                out.append(d)
    return pd.DatetimeIndex(out)


def build_targets(index_csv: str, start: str, end: str, dte_sessions=(5, 3)) -> pd.DataFrame:
    prices = pd.read_csv(index_csv, parse_dates=["date"])
    sessions = pd.DatetimeIndex(
        prices["date"].dropna().dt.normalize().drop_duplicates().sort_values()
    )
    lo, hi = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    sessions = sessions[(sessions >= lo) & (sessions <= hi)]
    if len(sessions) == 0:
        raise ValueError("no index sessions in requested range")

    rows = []
    for candidate in expiry_candidates(lo, hi):
        expiry = _previous_session(sessions, candidate)
        if expiry is None or expiry < lo:
            continue
        eligible = sessions[sessions < expiry]
        for n in dte_sessions:
            if len(eligible) < n:
                continue
            decision = eligible[-n]
            rows.append({
                "decision_date": decision.date().isoformat(),
                "target_expiry": expiry.date().isoformat(),
                "entry_session_offset": n,
            })

    return pd.DataFrame(rows).drop_duplicates().sort_values(
        ["decision_date", "target_expiry", "entry_session_offset"]
    ).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = build_targets(args.index, args.start, args.end)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print("targets", len(out))
    print("decision dates", out["decision_date"].nunique())
    print("expiry dates", out["target_expiry"].nunique())
    print(out.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
