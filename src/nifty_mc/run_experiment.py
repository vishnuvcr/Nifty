from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .nse_ingest import normalize_option_csv
from .origins import build_expiry_schedule
from .walk_forward import ForecastOrigin, walk_forward
from .evaluation import summarize_oos


def load_price_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.lower() in {"date", "datetime", "timestamp"}), df.columns[0])
    close_col = next((c for c in df.columns if c.lower() in {"close", "adj close", "adj_close", "price"}), None)
    if close_col is None:
        raise ValueError("CSV must contain a close/price column")
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col).sort_index().rename(columns={close_col: "close"})


def load_origins(path: str) -> list[ForecastOrigin]:
    df = pd.read_csv(path)
    required = {"decision_date", "expiry_date"}
    if not required.issubset(df.columns):
        raise ValueError("origins CSV must contain decision_date,expiry_date")
    return [
        ForecastOrigin(pd.Timestamp(r.decision_date), pd.Timestamp(r.expiry_date))
        for r in df.itertuples(index=False)
    ]


def main():
    ap = argparse.ArgumentParser(description="NIFTY Monte Carlo walk-forward experiment")
    ap.add_argument("--prices", required=True)
    ap.add_argument("--origins", help="CSV with decision_date,expiry_date")
    ap.add_argument("--options", help="Normalized/raw NSE options CSV; used to derive expiry dates")
    ap.add_argument("--output", default="reports/wfa_results.csv")
    ap.add_argument("--summary", default="reports/wfa_summary.csv")
    ap.add_argument("--paths", type=int, default=50000)
    ap.add_argument("--min-history", type=int, default=120)
    ap.add_argument("--entry-days", type=int, nargs="+", default=[5, 3])
    args = ap.parse_args()

    prices = load_price_csv(args.prices)

    if args.origins:
        origins = load_origins(args.origins)
    elif args.options:
        options = normalize_option_csv(args.options)
        expiry_dates = options.loc[options["symbol"].astype(str).str.upper().eq("NIFTY"), "expiry"].dropna().unique()
        origins = build_expiry_schedule(
            prices, expiry_dates, entry_days_to_expiry=tuple(args.entry_days)
        )
    else:
        raise ValueError("provide either --origins or --options")

    out = walk_forward(
        prices, origins, n_paths=args.paths, min_history=args.min_history
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)

    summary = summarize_oos(out)
    pd.DataFrame([summary]).to_csv(args.summary, index=False)

    print(f"Forecast origins: {len(origins)}")
    print(f"Usable OOS forecasts: {len(out)}")
    if summary:
        print(pd.Series(summary).to_string())


if __name__ == "__main__":
    main()
