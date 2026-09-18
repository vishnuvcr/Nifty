from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import zipfile
import requests
import pandas as pd

from nifty_mc.nse_ingest import normalize_option_csv


def candidate_urls(dt: pd.Timestamp) -> list[str]:
    d, m, y = dt.strftime("%d"), dt.strftime("%b").upper(), dt.strftime("%Y")
    ymd = dt.strftime("%Y%m%d")
    legacy = f"fo{d}{m}{y}bhav.csv.zip"
    udiff = f"BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
    return [
        f"https://nsearchives.nseindia.com/content/fo/{udiff}",
        f"https://archives.nseindia.com/content/fo/{udiff}",
        f"https://archives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/{legacy}",
        f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/{legacy}",
    ]


def fetch_one(date_str: str, timeout: int = 30) -> tuple[str, pd.DataFrame | None, dict]:
    dt = pd.Timestamp(date_str).normalize()
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,application/zip,*/*"}
    errors = []
    for url in candidate_urls(dt):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code != 200 or len(r.content) <= 100:
                errors.append(f"{r.status_code}:{url}")
                continue
            z = zipfile.ZipFile(BytesIO(r.content))
            names = [n for n in z.namelist() if not n.endswith("/")]
            if not names:
                errors.append(f"empty_zip:{url}")
                continue
            raw_path = Path("/tmp") / names[0]
            raw_path.write_bytes(z.read(names[0]))
            df = normalize_option_csv(raw_path)
            return date_str, df, {
                "trade_date": date_str, "status": "ok", "source_url": url,
                "source_tier": "A? daily_EOD_archive", "rows": len(df)
            }
        except Exception as e:
            errors.append(f"{type(e).__name__}:{e}")

    # Mirrors are deliberately limited to validation copies already pinned
    # in the pilot. They are recorded as secondary_public_mirror.
    mirrors = {
        "2025-02-03": "https://raw.githubusercontent.com/kiranfor2004/NSE_Downloader/e84ac65e1b727fc8354759bbd13d49c588abb361/fo_udiff_downloads/BhavCopy_NSE_FO_0_0_0_20250203_F_0000.csv.zip",
        "2026-04-01": "https://raw.githubusercontent.com/developerjava80-afk/strategy-squad/c38b0d169d2056e82894526f9172c9ae3df9603f/data/bhavcopy/historical/derivatives/BhavCopy_NSE_FO_0_0_0_20260401_F_0000.csv",
    }
    if date_str in mirrors:
        url = mirrors[date_str]
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 100:
                if url.endswith(".zip"):
                    z = zipfile.ZipFile(BytesIO(r.content))
                    name = [n for n in z.namelist() if not n.endswith("/")][0]
                    raw_path = Path("/tmp") / name
                    raw_path.write_bytes(z.read(name))
                else:
                    raw_path = Path("/tmp") / f"mirror_{dt.strftime('%Y%m%d')}.csv"
                    raw_path.write_bytes(r.content)
                df = normalize_option_csv(raw_path)
                return date_str, df, {
                    "trade_date": date_str, "status": "ok", "source_url": url,
                    "source_tier": "secondary_public_mirror", "rows": len(df)
                }
        except Exception as e:
            errors.append(f"mirror:{type(e).__name__}:{e}")

    return date_str, None, {
        "trade_date": date_str, "status": "failed",
        "error": " | ".join(errors[-6:])
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    targets = pd.read_csv(args.targets)
    dates = sorted(targets["decision_date"].dropna().astype(str).unique())
    frames, manifest = [], []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_one, d): d for d in dates}
        for fut in as_completed(futures):
            date_str, df, meta = fut.result()
            manifest.append(meta)
            if df is not None:
                x = df.copy()
                x["source_trade_date"] = pd.Timestamp(date_str)
                frames.append(x)
            print(date_str, meta["status"], meta.get("rows", 0), meta.get("source_tier", ""))

    if not frames:
        raise SystemExit("no option dates acquired")

    out = pd.concat(frames, ignore_index=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False, compression="gzip")
    pd.DataFrame(manifest).sort_values("trade_date").to_csv(args.manifest, index=False)

    expected = set(dates)
    acquired = {m["trade_date"] for m in manifest if m["status"] == "ok"}
    print("ACQUIRED", len(acquired), "of", len(expected))
    if acquired != expected:
        missing = sorted(expected - acquired)
        raise SystemExit(f"incomplete acquisition; missing {len(missing)} dates: {missing[:20]}")


if __name__ == "__main__":
    main()
