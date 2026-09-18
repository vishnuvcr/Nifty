REQUIRED_PRICE_COLUMNS = {"date", "close"}
REQUIRED_OPTION_COLUMNS = {
    "timestamp", "expiry", "strike", "option_type", "bid", "ask"
}

def validate_price_frame(df):
    missing = REQUIRED_PRICE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"missing price columns: {sorted(missing)}")

def validate_option_frame(df):
    missing = REQUIRED_OPTION_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"missing option columns: {sorted(missing)}")
