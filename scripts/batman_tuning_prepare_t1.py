#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / ".cache" / "batman_raw"
OUT = ROOT / "data" / "batman_tuning_cache"
AYUSH = RAW / "ayush_nifty_banknifty_options_2020_2024.zip"
INDEX_YF = RAW / "nifty_daily_yfinance_2014_2026.csv"
EXPIRY_CAL = OUT / "ayush_expiry_calendar_2020_2024.csv"
FILE_MAP = OUT / "ayush_daily_file_map_2020_2024.csv"
MANIFEST = OUT / "t1_prepared_manifest.json"
RAW_EXPIRY_CAL = RAW / "prepared_ayush_expiry_calendar_2020_2024.csv"
RAW_FILE_MAP = RAW / "prepared_ayush_daily_file_map_2020_2024.csv"

SYMBOL_RE = re.compile(r"^NIFTY(\d{2})([A-Z]{3})(\d{2})(\d+)(CE|PE)$", re.I)
MONTHS = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,"JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}

def parse_symbol(s: str):
    m = SYMBOL_RE.match(str(s).strip().upper())
    if not m:
        return None
    dd, mmm, yy, strike, typ = m.groups()
    try:
        return date(2000 + int(yy), MONTHS[mmm], int(dd))
    except Exception:
        return None

def acquire_yfinance():
    if INDEX_YF.exists() and INDEX_YF.stat().st_size > 10000:
        return
    import yfinance as yf
    df = yf.download("^NSEI", start="2014-01-01", end="2026-04-01", auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError("Yahoo Finance returned an empty NIFTY index history.")
    if hasattr(df.columns, "levels"):
        if len(df.columns.levels) > 1:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    close_col = "Close"
    if close_col not in df.columns:
        raise RuntimeError(f"Yahoo NIFTY data missing Close column: {list(df.columns)}")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce").dt.tz_localize(None).dt.normalize(),
        "close": pd.to_numeric(df[close_col], errors="coerce"),
    }).dropna().drop_duplicates("date").sort_values("date")
    out.to_csv(INDEX_YF, index=False)

def build_ayush_manifest():
    if RAW_EXPIRY_CAL.exists() and RAW_FILE_MAP.exists():
        EXPIRY_CAL.parent.mkdir(parents=True, exist_ok=True)
        FILE_MAP.parent.mkdir(parents=True, exist_ok=True)
        EXPIRY_CAL.write_bytes(RAW_EXPIRY_CAL.read_bytes())
        FILE_MAP.write_bytes(RAW_FILE_MAP.read_bytes())
        return
    if EXPIRY_CAL.exists() and FILE_MAP.exists():
        return
    if not AYUSH.exists():
        raise FileNotFoundError(AYUSH)
    expiries = defaultdict(set)
    file_rows = []
    with zipfile.ZipFile(AYUSH) as zf:
        members = [
            n for n in zf.namelist()
            if n.lower().endswith(".csv")
            and n.lower().startswith("nifty_data/nifty_options/")
        ]
        for i, name in enumerate(sorted(members), 1):
            m = re.search(r"nifty_options_(\d{2})_(\d{2})_(\d{4})\.csv$", name, re.I)
            if not m:
                continue
            dd, mm, yyyy = map(int, m.groups())
            trade_date = date(yyyy, mm, dd)
            file_rows.append({"trade_date": trade_date.isoformat(), "member": name})
            with zf.open(name) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                seen = set()
                for row in reader:
                    exp = parse_symbol(row.get("symbol", ""))
                    if exp is not None and exp >= trade_date and exp not in seen:
                        expiries[trade_date].add(exp)
                        seen.add(exp)
            if i % 250 == 0:
                print(f"scanned {i}/{len(members)} Ayush option files")
    exp_rows = []
    for td, exps in sorted(expiries.items()):
        for exp in sorted(exps):
            if exp >= td:
                exp_rows.append({"trade_date": td.isoformat(), "expiry": exp.isoformat()})
    cal_df=pd.DataFrame(exp_rows).drop_duplicates()
    map_df=pd.DataFrame(file_rows).drop_duplicates().sort_values("trade_date")
    cal_df.to_csv(EXPIRY_CAL, index=False)
    map_df.to_csv(FILE_MAP, index=False)
    cal_df.to_csv(RAW_EXPIRY_CAL, index=False)
    map_df.to_csv(RAW_FILE_MAP, index=False)

def validate():
    idx = pd.read_csv(INDEX_YF, parse_dates=["date"])
    cal = pd.read_csv(EXPIRY_CAL, parse_dates=["trade_date","expiry"])
    fmap = pd.read_csv(FILE_MAP, parse_dates=["trade_date"])
    if idx["date"].min().date() > date(2016, 1, 1):
        raise RuntimeError("NIFTY daily index does not reach far enough before the 2020 study start.")
    if cal.empty or fmap.empty:
        raise RuntimeError("Ayush expiry/file maps are empty.")
    if cal["expiry"].max().date() < date(2024, 10, 1):
        raise RuntimeError("Ayush option archive does not provide expected late-2024 expiry coverage.")
    checks = {
        "index_rows": int(len(idx)),
        "index_start": idx["date"].min().date().isoformat(),
        "index_end": idx["date"].max().date().isoformat(),
        "ayush_files": int(len(fmap)),
        "ayush_trade_dates": int(fmap["trade_date"].nunique()),
        "ayush_distinct_expiries": int(cal["expiry"].nunique()),
        "ayush_first_expiry": cal["expiry"].min().date().isoformat(),
        "ayush_last_expiry": cal["expiry"].max().date().isoformat(),
    }
    MANIFEST.write_text(json.dumps({
        "schema_version":"BATMAN-T1-PREPARED-1",
        "study_start":"2020-01-01",
        "development_end":"2022-12-30",
        "validation_end":"2024-12-31",
        "sources":{
            "nifty_daily":"Yahoo Finance ^NSEI, cached after one acquisition",
            "options":"Ayush Kaggle NIFTY 2020-2024, parsed from canonical NIFTY option symbols",
        },
        "checks":checks
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(checks,indent=2))

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    acquire_yfinance()
    build_ayush_manifest()
    validate()
