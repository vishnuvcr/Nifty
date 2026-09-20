# BATMAN Tuning V1 — Historical Data Source Decision

## Objective

Build an auditable historical dataset for the original BATMAN research horizon (2020-01-01 through 2026-03-30) that is sufficient to reconstruct entry selection and evaluate intraday exits without look-ahead leakage.

## Source hierarchy and selected roles

| Role | Source | Coverage | Use | Limitations |
|---|---|---|---|---|
| Pre-lookback NIFTY history | Zenodo, Bhat (2024), DOI 10.5281/zenodo.10899828 | 2017–2020 | Underlying history for 2017–2020 option data | Starts in 2017; not enough alone to provide the full 756-session seed for January 2020 |
| Long pre-lookback NIFTY index history | Kaggle Nishanth, dataset nishanthsalian/indian-stock-index-1minute-data-2008-2020 | 2008–2020 | Fills the 2016–2019 portion required by the earliest 756-session windows | Public Kaggle archive; schema/provenance must be audited before use |
| Historical option bars | Kaggle Ayush Gupta, dataset ayushsacri/indian-nifty-and-banknifty-options-data-2020-2024 | 2020–2024 | 2020–2024 NIFTY option bars | License shown as unknown; raw archive remains acquisition-only unless rights verified |
| 2024 cross-check / alternate archive | Kaggle Senthil Kumar, dataset senthilkumarvaithi/historical-nifty-options-2024-all-expiries | 2024 all expiries | Integrity cross-check and alternate 2024 source | Bid/ask unavailable |
| 2025–2026 option bars | Kaggle Rahul/Dhan, dataset rahultr1/nifty-options-weekly-1min-2025-01-01-to-2026-07-25 | 2025-01-01 to 2026-07-24 | 2025-01-01 through 2026-03-30 historical tuning | Bid/ask unavailable; expiry-code semantics must be validated |

## Why this is sufficient in principle

The parent BATMAN study ends on 2026-03-30 and uses the 2020–2026 historical split. The selected source stack now covers the full pre-entry underlying lookback as well as one-minute option history across the study window.

For entry/exit modelling, the canonical observation is bar OHLC + volume, not a synthetic bid/ask. Historical bid/ask quotes are unavailable in these public archives, so execution is stressed explicitly and zero-volume/stale bars are non-executable.

## Cache architecture

Raw source archives are cached once; the repository stores compact manifests and derived BATMAN-specific data rather than embedding multi-gigabyte source archives.

No tuning calculation may run against an unmanifested or unverified derived cache.

## Decision

Proceed with the source stack above and continue through normalization/probing. Do not label the resulting data exchange-grade quote history.
