from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/136.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def dmy(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def nse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(BASE + "/", timeout=30)
    r.raise_for_status()
    return s


def fetch_index_history(
    session: requests.Session, start: date, end: date, index_type: str = "NIFTY 50"
) -> pd.DataFrame:
    url = BASE + "/api/historical/indicesHistory"
    r = session.get(
        url,
        params={"indexType": index_type, "from": dmy(start), "to": dmy(end)},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    records = payload.get("data", {}).get("indexCloseOnlineRecords", [])
    if not records:
        raise RuntimeError("NSE returned no index records")
    df = pd.DataFrame(records)
    date_col = "EOD_TIMESTAMP" if "EOD_TIMESTAMP" in df else "TIMESTAMP"
    close_col = "EOD_CLOSE_INDEX_VAL" if "EOD_CLOSE_INDEX_VAL" in df else "CLOSE"
    df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["close"] = pd.to_numeric(df[close_col], errors="coerce")
    return df[["date", "close"]].dropna().sort_values("date").drop_duplicates("date")


def fetch_fno_history(
    session: requests.Session,
    start: date,
    end: date,
    instrument_type: str,
    symbol: str,
    expiry: str,
    year: int,
    option_type: str | None = None,
    strike_price: float | None = None,
) -> pd.DataFrame:
    url = BASE + "/api/historicalOR/foCPV"
    params = {
        "from": dmy(start),
        "to": dmy(end),
        "instrumentType": instrument_type,
        "symbol": symbol,
        "year": str(year),
        "expiryDate": expiry,
    }
    if option_type:
        params["optionType"] = option_type
    if strike_price is not None:
        params["strikePrice"] = str(strike_price)
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    records = payload.get("data", [])
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def main() -> None:
    ap = argparse.ArgumentParser(description="Download public NSE research data.")
    ap.add_argument("--start", required=True, type=lambda x: datetime.strptime(x, "%Y-%m-%d").date())
    ap.add_argument("--end", required=True, type=lambda x: datetime.strptime(x, "%Y-%m-%d").date())
    ap.add_argument("--out-dir", default="data/raw")
    ap.add_argument("--index-only", action="store_true")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    s = nse_session()

    idx = fetch_index_history(s, args.start, args.end)
    idx.to_csv(out / "nifty50_index.csv", index=False)
    print(f"saved {len(idx)} NIFTY 50 sessions to {out / 'nifty50_index.csv'}")
    if args.index_only:
        return

    raise SystemExit(
        "For F&O, supply contract-specific expiry/instrument parameters and use "
        "fetch_fno_history from a controlled research script; bulk option chains "
        "should not be requested blindly."
    )


if __name__ == "__main__":
    main()
