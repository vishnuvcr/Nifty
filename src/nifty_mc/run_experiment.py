from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from .walk_forward import ForecastOrigin, walk_forward


def load_price_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.lower() in {"date","datetime","timestamp"}), df.columns[0])
    close_col = next((c for c in df.columns if c.lower() in {"close","adj close","adj_close","price"}), None)
    if close_col is None:
        raise ValueError("CSV must contain a close/price column")
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col).sort_index().rename(columns={close_col:"close"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices", required=True)
    ap.add_argument("--origins", required=True, help="CSV with decision_date,expiry_date")
    ap.add_argument("--output", default="reports/wfa_results.csv")
    ap.add_argument("--paths", type=int, default=50000)
    args = ap.parse_args()

    prices = load_price_csv(args.prices)
    origins_df = pd.read_csv(args.origins)
    origins = [
        ForecastOrigin(r.decision_date, r.expiry_date)
        for r in origins_df.itertuples(index=False)
    ]
    out = walk_forward(prices, origins, n_paths=args.paths)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(out.tail(10).to_string(index=False))
    if not out.empty:
        print("\nCoverage:")
        for level in (50,80,90):
            print(level, round(out[f"coverage_{level}"].mean(),4))


if __name__ == "__main__":
    main()
