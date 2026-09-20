# Phase Status

| Phase | Status | Evidence |
|---|---|---|
| T0 Protocol freeze | COMPLETE | Frozen control, parameter grid, cost/statistical plans |
| T1 Data and frozen-control reconstruction | IN PROGRESS — DATA ACQUISITION GATE | Historical sources identified; acquisition/cache workflow committed; integrity execution still pending |
| T2 Entry tuning | BLOCKED on T1 |
| T3 Exit tuning | BLOCKED on T1 |
| T4 Nested WFO | BLOCKED on T2/T3 |
| T5 Robustness and inference | BLOCKED on T4 |
| T6 Prospective freeze | BLOCKED on T5 |

## T1 execution update — 2026-09-21

The source audit now covers the original BATMAN study horizon. A reproducible acquisition workflow has been committed using: Zenodo Bhat 2017–2020 NIFTY data for the pre-2020 756-session lookback seed, a public 2020–2024 NIFTY/BankNIFTY options archive, and the documented 2025–2026 Rahul/Dhan one-minute NIFTY options archive. NSE public reports are retained as the official EOD/metadata reference.

The workflow uses a persistent GitHub Actions cache so large raw archives are not downloaded on every run. It writes a source SHA-256 manifest and publishes the manifest as a workflow artifact. The raw sources are not treated as exchange-grade bid/ask quotes.

The actual compact BATMAN-specific derived cache has not yet been generated and validated. Therefore T2/T3 remain blocked and no tuning P&L is claimed.

## Required next gate

T1 completes only after the acquisition workflow successfully validates:

1. coverage through 2026-03-30;
2. authoritative/verified expiry mapping for each historical option observation;
3. canonical contract identity;
4. timestamp and OHLC integrity;
5. zero-volume non-executability;
6. sufficient one-minute observations for entry and all exit rules;
7. a signed/provenance-tagged derived cache manifest.
