# Data Contract

Required inputs: NIFTY 50 daily closes; trading calendar and holidays; timestamped underlying/intraday data when trigger timing requires it; option expiry, option type, strike, timestamp, OHLC/trade/quote data, contract metadata and lot size.

Preferred source hierarchy: exchange-sourced executable data first; high-quality transparent historical vendor data second; settlement or close-only data only when the research question permits it.

Cached data or a reproducible manifest must be used by workflows. Future records relative to a decision timestamp are prohibited.
