from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from nifty_mc.walk_forward import ForecastOrigin, walk_forward
from nifty_mc.evaluation import summarize_oos

def build_weekly_expiries(start: pd.Timestamp, end: pd.Timestamp, sessions: pd.DatetimeIndex) -> list[pd.Timestamp]:
    sessions = pd.DatetimeIndex(sessions).normalize().sort_values().unique()
    out = []
    def add_candidates(freq: str, lo: str, hi: str):
        for d in pd.date_range(max(start, pd.Timestamp(lo)), min(end, pd.Timestamp(hi)), freq=freq):
            eligible = sessions[sessions <= d]
            if len(eligible):
                out.append(eligible[-1])
    # NIFTY weekly options launched Feb 11, 2019; initial weekly expiry was Thursday.
    add_candidates("W-THU", "2019-02-14", "2025-04-03")
    # NSE revised NIFTY expiry to Monday effective Apr 4, 2025.
    add_candidates("W-MON", "2025-04-04", "2025-08-28")
    # NSE revised it again to Tuesday, effective for new/revised contracts from Aug 29, 2025.
    add_candidates("W-TUE", "2025-08-29", str(end.date()))
    return sorted(set(x for x in out if start <= x <= end))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices", required=True)
    ap.add_argument("--out", default="reports/wfa_results.csv")
    ap.add_argument("--summary", default="reports/wfa_summary.csv")
    ap.add_argument("--origins", default="reports/wfa_origins.csv")
    ap.add_argument("--paths", type=int, default=20000)
    args = ap.parse_args()

    df = pd.read_csv(args.prices, parse_dates=["date"]).dropna(subset=["date", "close"])
    df = df.drop_duplicates("date").sort_values("date").set_index("date")
    expiries = build_weekly_expiries(df.index.min(), df.index.max(), df.index)
    origins = []
    sessions = df.index
    for expiry in expiries:
        eligible = sessions[sessions < expiry]
        for n in (5, 3):
            if len(eligible) >= n:
                origins.append(ForecastOrigin(eligible[-n], expiry))
    origins = sorted(set(origins), key=lambda x: (x.expiry_date, x.decision_date))
    pd.DataFrame([{"decision_date":o.decision_date,"expiry_date":o.expiry_date} for o in origins]).to_csv(args.origins,index=False)

    out = walk_forward(df, origins, n_paths=args.paths, min_history=120)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out,index=False)
    summary = summarize_oos(out)
    summary.update({
        "paths": args.paths,
        "expiry_count": len(expiries),
        "origin_count": len(origins),
        "usable_oos": len(out),
        "data_start": str(df.index.min().date()),
        "data_end": str(df.index.max().date()),
    })
    pd.DataFrame([summary]).to_csv(args.summary,index=False)
    print(pd.Series(summary).to_string())

if __name__ == "__main__":
    main()
