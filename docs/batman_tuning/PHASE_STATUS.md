# Phase Status

| Phase | Status | Evidence |
|---|---|---|
| T0 Protocol freeze | COMPLETE | Frozen control, parameter grid, cost/statistical plans |
| T1 Data and frozen-control reconstruction | IN PROGRESS — NORMALIZATION / PROBE | Raw-source cache validated and reusable; long NIFTY index fallback added; compact BATMAN cache not yet built |
| T2 Entry tuning | BLOCKED on T1 |
| T3 Exit tuning | BLOCKED on T1 |
| T4 Nested WFO | BLOCKED on T2/T3 |
| T5 Robustness and inference | BLOCKED on T4 |
| T6 Prospective freeze | BLOCKED on T5 |

## T1 execution update — 2026-09-21

All four initial raw archives were successfully acquired and validated in GitHub Actions. The reusable raw cache is populated.

A separate automatic normalization/probe workflow has now been added so acquisition is not repeated on every research commit. It restores the existing raw cache, adds a longer 2008–2020 NIFTY index source if needed, audits nested ZIP/source schemas, and publishes a v2 provenance manifest.

The scientific next gate is construction of a compact point-in-time BATMAN cache with verified expiry and contract identity plus sufficient intraday option bars. The research continues automatically toward that gate.

No tuning P&L is claimed.
