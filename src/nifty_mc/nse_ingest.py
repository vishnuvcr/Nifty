from __future__ import annotations

from pathlib import Path
import pandas as pd


PRICE_ALIASES = {
    "Date": "date", "DATE": "date", "TIMESTAMP": "date",
    "Close": "close", "CLOSE": "close", "Closing Price": "close",
}

OPTION_ALIASES = {
    "TradDt": "timestamp", "TIMESTAMP": "timestamp", "Date": "timestamp",
    "FinInstrmNm": "symbol", "Symbol": "symbol",
    "XpryDt": "expiry", "Expiry": "expiry",
    "StrkPric": "strike", "Strike Price": "strike", "Strike": "strike",
    "OptnTp": "option_type", "Option Type": "option_type",
    "OpnPric": "open", "Open": "open",
    "HghPric": "high", "High": "high",
    "LwPric": "low", "Low": "low",
    "ClsPric": "close", "Close": "close",
    "LastPric": "last", "Last": "last",
    "BidPric": "bid", "Bid": "bid",
    "AskPric": "ask", "Ask": "ask",
    "OpnIntrst": "open_interest", "Open Interest": "open_interest",
    "TtlTradgVol": "volume", "Volume": "volume",
}


def _read(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in {".gz", ".zip"}:
        return pd.read_csv(path, compression="infer")
    return pd.read_csv(path)


def normalize_price_csv(path: str | Path) -> pd.DataFrame:
    df = _read(path).rename(columns=PRICE_ALIASES)
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("price data requires date and close columns")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)


def normalize_option_csv(path: str | Path) -> pd.DataFrame:
    df = _read(path).rename(columns=OPTION_ALIASES)
    required = {"timestamp", "expiry", "strike", "option_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"option data missing columns: {sorted(missing)}")

    for c in ("timestamp", "expiry"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")

    for c in ("open","high","low","close","last","bid","ask","open_interest","volume"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["option_type"] = df["option_type"].astype(str).str.upper().replace(
        {"CALL":"CE", "PUT":"PE"}
    )
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper().str.contains("NIFTY", na=False)]

    return df.dropna(subset=["timestamp","expiry","strike"]).sort_values(
        ["timestamp","expiry","strike","option_type"]
    ).reset_index(drop=True)


def snapshot_at_or_before(chain: pd.DataFrame, timestamp, expiry) -> pd.DataFrame:
    t = pd.Timestamp(timestamp)
    e = pd.Timestamp(expiry)
    x = chain[(chain["expiry"] == e) & (chain["timestamp"] <= t)]
    if x.empty:
        raise ValueError("no option-chain observations available before decision time")
    latest = x["timestamp"].max()
    return x[x["timestamp"] == latest].copy()
