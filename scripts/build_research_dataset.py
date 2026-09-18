from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from nifty_mc.nse_ingest import normalize_price_csv, normalize_option_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spot", required=True)
    ap.add_argument("--options", required=True)
    ap.add_argument("--out", default="data/processed")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    spot = normalize_price_csv(args.spot)
    options = normalize_option_csv(args.options)

    spot.to_parquet(out / "nifty_spot.parquet", index=False)
    options.to_parquet(out / "nifty_options.parquet", index=False)

    print("spot rows:", len(spot))
    print("option rows:", len(options))
    print("spot range:", spot["date"].min(), "to", spot["date"].max())
    print("option timestamps:", options["timestamp"].min(), "to", options["timestamp"].max())
    print("expiries:", options["expiry"].nunique())


if __name__ == "__main__":
    main()
