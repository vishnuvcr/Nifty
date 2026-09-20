# Phase Status

| Phase | Status | Evidence |
|---|---|---|
| T0 Protocol freeze | COMPLETE | Frozen control, parameter grid, cost/statistical plans |
| T1 Data and frozen-control reconstruction | PARTIAL / BLOCKED | Control specification matched; historical executable cache still absent |
| T2 Entry tuning | BLOCKED on T1 |
| T3 Exit tuning | BLOCKED on T1 |
| T4 Nested WFO | BLOCKED on T2/T3 |
| T5 Robustness and inference | BLOCKED on T4 |
| T6 Prospective freeze | BLOCKED on T5 |

## T1 execution update — 2026-09-21

A repository-wide audit was extended to historical BATMAN commits and GitHub Actions backfill runs. The parent branch contains a reconstructed first-trade paper record, but its own note states that historical bid/ask quotes were unavailable. The associated backfill diagnostic runs did not retain downloadable workflow artifacts. Therefore that record cannot serve as the executable historical dataset for D0-D6 and intraday exit tuning.

A fail-closed cache contract and validator have now been added to this branch. The validator requires manifest.json, sessions.parquet, option_quotes.parquet, and intraday_underlying.parquet, with provenance/hash metadata. T1 remains blocked until those objects are supplied through the approved cache/artifact path.

No tuning P&L or parameter winner is claimed.
