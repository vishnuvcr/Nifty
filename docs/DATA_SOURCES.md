# Data sources and provenance

## NSE
Official NSE historical derivative reports include contract-wise price-volume data and daily/monthly F&O archives. NSE's data-sharing documentation identifies contract-wise price-volume data and F&O archives as research data sources.

## India VIX
India VIX is calculated from NIFTY option order-book prices and represents expected volatility over the next 30 calendar days. It is therefore an implied-volatility diagnostic, not a realized-volatility forecast.

## Research dataset tiers
Tier A: timestamped bid/ask option quotes or order-book snapshots.
Tier B: timestamped option trades with reconstructed executable prices.
Tier C: daily option OHLC/settlement data.

The walk-forward engine should run Tier A/B first when available; Tier C is a secondary robustness experiment.


## Current acquisition decision (2026-09)

The public NSE historical-report pages provide NIFTY index history and contract-wise F&O price/volume history. These are sufficient for the underlying walk-forward forecast layer and for an end-of-day option-price research layer. NSE's historical contract-wise F&O report exposes fields such as symbol, date, expiry, OHLC/LTP, settlement, open interest and underlying value.

For an executable four-leg Long Iron Condor, however, the preferred pricing input is timestamped bid/ask data. NSE separately provides EOD/historical order-and-trade data through its data products; historical F&O order/trade data is subscription-based. Therefore the project will not fabricate bid/ask quotes from daily closes.

Research tiers:
- Tier A: timestamped bid/ask/order-book data — executable entry/exit modelling.
- Tier B: daily option OHLC/settlement — end-of-day proxy backtest, explicitly labelled as such.
- Tier C: underlying NIFTY + India VIX — forecast/calibration research without option execution.

Public references:
- NSE historical contract-wise F&O data: https://www.nseindia.com/report-detail/fo_eq_security
- NSE all derivatives reports: https://www.nseindia.com/all-reports-derivatives
- NSE historical reports: https://www.nseindia.com/static/resources/historical-reports-capital-market-daily-monthly-archives
- NSE EOD/historical data subscription: https://www.nseindia.com/static/market-data/eod-historical-data-subscription
