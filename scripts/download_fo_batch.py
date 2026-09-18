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


def mirror_urls(dt: pd.Timestamp) -> list[str]:
    legacy_name = f"fo{dt.strftime('%d')}{dt.strftime('%b').upper()}{dt.strftime('%Y')}bhav.csv.zip"
    udiff_name = f"BhavCopy_NSE_FO_0_0_0_{dt.strftime('%Y%m%d')}_F_0000.csv.zip"
    urls = [
        f"https://raw.githubusercontent.com/SantoshSrinivas79/NSE-FNO-Data-bank/main/data/{dt.strftime('%Y/%m')}/{legacy_name}",
        f"https://raw.githubusercontent.com/SantoshSrinivas79/NSE-FNO-Data-bank/main/data/{dt.strftime('%Y/%m')}/{udiff_name}",
    ]
    if dt.strftime("%Y-%m-%d") == "2025-02-03":
        urls.insert(
            0,
            "https://raw.githubusercontent.com/kiranfor2004/NSE_Downloader/e84ac65e1b727fc8354759bbd13d49c588abb361/fo_udiff_downloads/BhavCopy_NSE_FO_0_0_0_20250203_F_0000.csv.zip",
        )
    if dt.strftime("%Y-%m-%d") == "2026-04-01":
        urls.insert(
            0,
            "https://raw.githubusercontent.com/developerjava80-afk/strategy-squad/c38b0d169d2056e82894526f9172c9ae3df9603f/data/bhavcopy/historical/derivatives/BhavCopy_NSE_FO_0_0_0_20260401_F_0000.csv",
        )
    return urls


def _read_response(url: str, content: bytes, dt: pd.Timestamp) -> pd.DataFrame:
    if url.endswith(".zip"):
        z = zipfile.ZipFile(BytesIO(content))
        names = [n for n in z.namelist() if not n.endswith("/")]
        if not names:
            raise ValueError("empty zip")
        raw_path = Path("/tmp") / names[0]
        raw_path.write_bytes(z.read(names[0]))
    else:
        raw_path = Path("/tmp") / f"mirror_{dt.strftime('%Y%m%d')}.csv"
        raw_path.write_bytes(content)
    return normalize_option_csv(raw_path)


def _try_urls(urls: list[str], dt: pd.Timestamp, timeout: int, headers: dict) -> tuple[pd.DataFrame | None, str | None, list[str]]:
    errors = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code != 200 or len(r.content) <= 100:
                errors.append(f"{r.status_code}:{url}")
                continue
            return _read_response(url, r.content, dt), url, errors
        except Exception as e:
            errors.append(f"{type(e).__name__}:{e}")
    return None, None, errors


def fetch_one(date_str: str, timeout: int = 20) -> tuple[str, pd.DataFrame | None, dict]:
    dt = pd.Timestamp(date_str).normalize()
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,application/zip,*/*"}
    errors = []

    # The validated secondary archive is tried first because it contains the
    # original NSE daily archives and is much more reliable from CI than the
    # NSE web archive endpoints. Provenance remains explicitly secondary.
    df, url, errs = _try_urls(mirror_urls(dt), dt, timeout, {})
    errors.extend(errs)
    if df is not None:
        return date_str, df, {
            "trade_date": date_str,
            "status": "ok",
            "source_url": url,
            "source_tier": "secondary_public_mirror",
            "rows": len(df),
        }

    # Fall back to official NSE archives when the secondary mirror lacks a date.
    df, url, errs = _try_urls(candidate_urls(dt), dt, timeout, headers)
    errors.extend(errs)
    if df is not None:
        return date_str, df, {
            "trade_date": date_str,
            "status": "ok",
            "source_url": url,
            "source_tier": "tier_b_daily_eod_official",
            "rows": len(df),
        }

    return date_str, None, {
        "trade_date": date_str,
        "status": "failed",
        "error": " | ".join(errors[-8:]),
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
