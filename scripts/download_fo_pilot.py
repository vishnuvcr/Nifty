from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import zipfile
import requests
import pandas as pd

from nifty_mc.nse_ingest import normalize_option_csv


def candidate_urls(dt: pd.Timestamp) -> list[str]:
    d = dt.strftime("%d")
    m = dt.strftime("%b").upper()
    y = dt.strftime("%Y")
    ymd = dt.strftime("%Y%m%d")
    legacy = f"fo{d}{m}{y}bhav.csv.zip"
    udiff = f"BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
    return [
        f"https://nsearchives.nseindia.com/content/fo/{udiff}",
        f"https://archives.nseindia.com/content/fo/{udiff}",
        f"https://archives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/{legacy}",
        f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/{legacy}",
    ]


def _normalize_archive_bytes(content: bytes, dt: pd.Timestamp) -> tuple[str, pd.DataFrame]:
    z = zipfile.ZipFile(BytesIO(content))
    names = [n for n in z.namelist() if not n.endswith("/")]
    if not names:
        raise ValueError("archive contains no files")
    name = names[0]
    raw_path = Path("/tmp") / name
    raw_path.write_bytes(z.read(name))
    return name, normalize_option_csv(raw_path)


def fetch_one(dt: pd.Timestamp, timeout=30):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,application/zip,*/*"}
    last = None
    for url in candidate_urls(dt):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 100:
                name, df = _normalize_archive_bytes(r.content, dt)
                return url, name, df
            last = f"{r.status_code} {url}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"

    # Secondary public mirrors are validation fallbacks only. Their provenance
    # is retained in the manifest and they must not be silently treated as
    # primary NSE downloads in the research dataset.
    mirror_urls = {
        "2025-02-03": "https://raw.githubusercontent.com/kiranfor2004/NSE_Downloader/e84ac65e1b727fc8354759bbd13d49c588abb361/fo_udiff_downloads/BhavCopy_NSE_FO_0_0_0_20250203_F_0000.csv.zip",
        "2026-04-01": "https://raw.githubusercontent.com/developerjava80-afk/strategy-squad/c38b0d169d2056e82894526f9172c9ae3df9603f/data/bhavcopy/historical/derivatives/BhavCopy_NSE_FO_0_0_0_20260401_F_0000.csv",
    }
    key = dt.strftime("%Y-%m-%d")
    if key in mirror_urls:
        url = mirror_urls[key]
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 100:
                if url.lower().endswith(".zip"):
                    name, df = _normalize_archive_bytes(r.content, dt)
                    return url, name, df
                raw_path = Path("/tmp") / f"mirror_{key.replace('-', '')}.csv"
                raw_path.write_bytes(r.content)
                return url, raw_path.name, normalize_option_csv(raw_path)
            last = f"{r.status_code} {url}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    raise RuntimeError(last or "all candidates failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", nargs="+", required=True)
    ap.add_argument("--out", default="data/options_pilot.csv")
    args = ap.parse_args()
    out = []
    manifests = []
    for s in args.dates:
        dt = pd.Timestamp(s).normalize()
        try:
            url, name, df = fetch_one(dt)
            x = df.copy()
            x["source_trade_date"] = dt
            out.append(x)
            manifests.append({
                "trade_date": dt,
                "status": "ok",
                "source_url": url,
                "archive_name": name,
                "rows": len(x),
            })
            print(dt.date(), "OK", len(x), url)
        except Exception as e:
            manifests.append({"trade_date": dt, "status": "failed", "error": str(e)})
            print(dt.date(), "FAILED", e)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pd.concat(out, ignore_index=True).to_csv(args.out, index=False) if out else pd.DataFrame().to_csv(args.out, index=False)
    pd.DataFrame(manifests).to_csv(Path(args.out).with_name("options_pilot_manifest.csv"), index=False)
    good = sum(m["status"] == "ok" for m in manifests)
    if good < len(manifests):
        raise SystemExit(f"{good}/{len(manifests)} dates acquired")


if __name__ == "__main__":
    main()
