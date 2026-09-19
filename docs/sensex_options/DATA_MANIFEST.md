# SENSEX Options Data Manifest

Status: INITIAL / NO PERFORMANCE DATA YET

| Dataset | Required fields | Preferred source | Validation |
|---|---|---|---|
| SENSEX daily index | date, close | BSE or another auditable historical source | duplicate-date, monotonic-date, calendar checks |
| SENSEX option chain | timestamp, expiry, strike, option_type, bid, ask, LTP, volume, OI | BSE/authoritative historical feed or licensed archive | point-in-time availability and quote-quality audit |
| SENSEX contract metadata | effective_date, expiry, lot_size, strike_step | BSE contract specification/history | effective-date join; no silent forward-fill across changes |
| Trading calendar | date, open/closed, holiday_reason | BSE | cross-check against observed sessions |
| Cost schedule | effective_date, brokerage, turnover, STT, GST, SEBI, stamp | broker/exchange/statutory sources | effective-date versioning |

## Required provenance per cached file
- source URL/document
- retrieval timestamp in IST
- source publication/effective date where available
- checksum
- transformation script/version
- row count
- minimum/maximum date or timestamp
- known missingness
- quote-quality flags

## Prohibited shortcuts
- Do not use current option-chain values to reconstruct historical quotes.
- Do not infer bid/ask from LTP unless a separately labelled robustness scenario requires it.
- Do not use SENSEX outcome data to change the frozen candidate universe before the final holdout.