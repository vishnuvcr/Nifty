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
        # NIFTY weekly expiry regime.  NSE's 2025 circulars changed the
        # weekday in stages; use explicit transition dates rather than a
        # single hard-coded weekday across the whole sample.
        if d < pd.Timestamp("2025-04-04"):
            if d.weekday() == 3:  # Thursday
                out.append(d)
        elif d < pd.Timestamp("2025-07-01"):
            if d.weekday() == 0:  # Monday
                out.append(d)
        elif d < pd.Timestamp("2025-08-29"):
            if d.weekday() == 3:  # Thursday; existing contracts unchanged
                out.append(d)
        else:
            if d.weekday() == 1:  # Tuesday
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
        # The August 2025 transition had no Thursday weekly expiries after
        # Aug-28; monthly/long-dated contracts are handled by the actual
        # option-chain expiry field during ingestion.
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

    out = pd.DataFrame(rows).drop_duplicates().sort_values(
        ["decision_date", "target_expiry", "entry_session_offset"]
    )
    return out.reset_index(drop=True)


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
