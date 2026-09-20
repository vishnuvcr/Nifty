# BATMAN Tuning V1 — Historical Data Source Decision

## Objective

Build an auditable historical dataset for the original BATMAN research horizon (2020-01-01 through 2026-03-30) that is sufficient to reconstruct entry selection and evaluate intraday exits without look-ahead leakage.

## Source hierarchy and selected roles

| Role | Source | Coverage | Use | Limitations |
|---|---|---|---|---|
| Pre-lookback NIFTY history | Zenodo, Bhat (2024), DOI 10.5281/zenodo.10899828 | 2017–2020 | Underlying history needed for the 756-session Monte Carlo lookback | Public archive is trade OHLCV; the Zenodo page does not display a clear license field, so raw redistribution is not assumed |
| Historical option bars | Kaggle, Ayush Gupta, ayushsacri/indian-nifty-and-banknifty-options-data-2020-2024 | Jan-2020 to Oct-2024 | 2020–2024 NIFTY option bars | License shown as unknown; raw archive must remain acquisition-only unless redistribution rights are verified |
| 2024 cross-check / alternate archive | Kaggle, Senthil Kumar, senthilkumarvaithi/historical-nifty-options-2024-all-expiries | 2024 all expiries | Integrity cross-check and fallback for 2024 | Bid/ask unavailable; use only with explicit close-bar/adverse-execution modelling |
| 2025–2026 option bars | Kaggle, Rahul/Dhan, rahultr1/nifty-options-weekly-1min-2025-01-01-to-2026-07-25 | 2025-01-01 to 2026-07-24 | 2025-01-01 to 2026-03-30 historical study window | Bid/ask unavailable; expiry codes need verified calendar resolution |
| Official EOD/metadata reference | NSE India All Reports / Historical Data | Ongoing | Validate trading dates, daily settlement/contract metadata and provenance where available | Official freely visible pages do not provide the full intraday option-history required for this study; NSE historical EOD/trade datasets are separately subscription-based |

## Why this is sufficient in principle

The parent BATMAN study ends on 2026-03-30 and uses the 2020–2026 historical split. The selected sources provide one-minute option OHLC histories across that interval, while the 2017–2020 Zenodo spot history can supply the older observations needed to seed a 756-session return window for early-2020 tests.

For entry/exit modelling, the canonical observation will be the bar OHLC + volume, not a synthetic bid/ask. Because historical bid/ask quotes are unavailable in these public archives, execution must be stressed explicitly using the fixed adverse-slippage model in COST_MODEL.md, and all zero-volume/stale bars must be non-executable.

## Important scientific restriction

The datasets above are not treated as exchange-certified tick/quote feeds. The tuning study therefore distinguishes:

1. Historical bar-level backtest evidence — permitted after integrity checks and conservative execution assumptions.
2. Prospective/executable validation — must remain based on the separate live/paper infrastructure with actual executable quotes.

The public archives must not be described as providing historical bid/ask execution.

## Cache architecture

The raw source archives are too large and/or license-ambiguous to commit directly to the repository. They are therefore acquired once into an immutable GitHub Actions cache, while a compact, provenance-tagged BATMAN-specific derived cache is the intended repository dataset.

The derived cache must contain only the observations actually needed by the frozen BATMAN reconstruction/tuning engine, plus a manifest with source dataset and URL, source version/date, source file member names, SHA-256 hashes of source archives when acquired, study coverage, extraction rules, row counts, zero-volume share, missing/ambiguous timestamp counts, expiry-calendar provenance, and schema version.

No tuning calculation may run against an unmanifested or unverified cache.

## Official-source context

NSE's current reports page lists F&O daily settlement prices and UDiFF common bhavcopy files, while its historical-data subscription page describes a separate paid End-of-Day / Historical Trade data service. The public option-chain page is a current chain interface, not a substitute for a full historical intraday archive.

## External literature/data provenance reviewed

- Bhat's Zenodo dataset is explicitly cited as the openly available data source supporting the 2024 Journal of Futures Markets study on NIFTY option return asymmetry.
- Public Kaggle/GitHub archives document one-minute NIFTY options data for 2020–2024 and 2025–2026; their source semantics are retained as metadata and independently audited before use.

## Decision

Proceed with these sources for T1 acquisition and mechanical audit, but do not call the resulting dataset exchange-grade quote data. The study remains fail-closed if coverage, expiry resolution, contract identity, timestamps, or executable-bar requirements cannot be validated.
