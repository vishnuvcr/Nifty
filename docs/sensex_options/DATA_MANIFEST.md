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
## Source findings from S1

- BSE documents an Equity Derivatives Bhav Copy with contract type, symbol, expiry, strike, option type, OHLC, settlement, weighted-average price, contracts traded and open interest.
- BSE's current market-data service advertises exchange-verified Equity Derivatives APIs and Indices OHLC data; access is subscription-based.
- The historical EOD Bhav Copy schema does not contain historical best bid/ask fields. Therefore it can support settlement/EOD diagnostics but cannot, by itself, recreate a 09:30 executable entry.

## Primary-data requirement

The primary SENSEX trading test must use either (a) an archived point-in-time intraday/order-book feed with bid/ask, or (b) a licensed historical derivatives dataset with point-in-time executable quotes. EOD-only data may be used as a clearly labelled secondary robustness/proxy analysis.