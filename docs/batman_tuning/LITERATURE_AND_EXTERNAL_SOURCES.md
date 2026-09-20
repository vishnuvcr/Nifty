# Literature and External Sources

The tuning study should review evidence on walk-forward optimization, financial backtest overfitting, multiple testing and data snooping, bootstrap Reality Check / SPA-style inference, option execution costs, bid-ask spreads, slippage, stop-loss path dependence, trailing-stop path dependence, intraday execution, Indian derivatives microstructure, and exchange/broker trading rules.

Primary source classes:
- NSE official market and derivatives documentation;
- SEBI and exchange circulars;
- Paytm Money current fee documentation;
- peer-reviewed finance and statistics literature;
- reproducible academic working papers;
- high-quality technical research where primary papers are unavailable.

Retrieval dates and claims are recorded in docs/batman_tuning/EXTERNAL_SOURCE_SNAPSHOT.md.


## 2026-09-21 data-source review update

### Historical data sources

- NSE India All Reports: official F&O daily settlement prices, UDiFF common bhavcopy and related derivatives reports. The public reports interface confirms these report classes; NSE separately advertises paid End-of-Day / Historical Trade data for deeper historical records.
- NSE Equity Derivatives Contract Information: current contract metadata and permitted lot-size reference.
- Bhat (2024), Zenodo DOI 10.5281/zenodo.10899828: one-minute NIFTY spot, futures and options data for 2017–2020. The associated Journal of Futures Markets paper states the underlying data are openly available in Zenodo.
- Ayush Gupta, Kaggle dataset ayushsacri/indian-nifty-and-banknifty-options-data-2020-2024: NIFTY/BankNIFTY spot, futures and options data from 2020-01 through 2024-10; license is listed as unknown on the dataset page, so raw redistribution is not assumed.
- Senthil Kumar, Kaggle dataset senthilkumarvaithi/historical-nifty-options-2024-all-expiries: 2024 NIFTY options archive covering all expiries; Apache 2.0 is stated on the dataset page.
- Rahul/Dhan, Kaggle dataset rahultr1/nifty-options-weekly-1min-2025-01-01-to-2026-07-25: one-minute NIFTY option archive covering 2025-01-01 through 2026-07-24; the independent audit documented in an external GitHub research repository measured 15,504,535 rows and flagged zero-volume/stale-bar semantics and expiry-code ambiguity.

### Methodological implications

The public archives are bar-level OHLCV datasets and do not supply historical bid/ask quotes. Consequently, the BATMAN tuning study will not represent close-to-close prices as executable quotes. Entry and exit rules must use explicit bar-event conventions and adverse-slippage sensitivity, and zero-volume bars are not executable. This distinction is carried into T1 data validation and the statistical analysis plan.

### Selected research literature / concepts to preserve in later phases

- Monte Carlo simulation for terminal-range distributions must remain separated from option-implied risk-neutral quantities.
- Walk-forward analysis must preserve chronological train/validation/test boundaries and nested tuning selection.
- Multiple comparisons across D0-D6 × timing × exit grids require data-snooping diagnostics and an untouched outer holdout.
- Intraday OHLC target/stop evaluation requires a deterministic intrabar ambiguity rule; same-bar high/low cannot be used as though execution order were known when both barriers are crossed.
