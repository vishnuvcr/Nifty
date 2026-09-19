from __future__ import annotations
import pandas as pd

def normalize_expiry_dates(expiry_series):
    return pd.to_datetime(expiry_series).dt.normalize()

def validate_expiry_after_decision(decision, expiry):
    d,e = pd.Timestamp(decision),pd.Timestamp(expiry)
    if e <= d: raise ValueError("expiry must be after decision timestamp")
    return True

def trading_days_to_expiry(index, decision, expiry):
    idx = pd.DatetimeIndex(index).normalize()
    d,e = pd.Timestamp(decision).normalize(),pd.Timestamp(expiry).normalize()
    return int(((idx > d) & (idx <= e)).sum())
