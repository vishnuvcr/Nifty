# Phase Status

| Phase | Status | Evidence |
|---|---|---|
| T0 Protocol freeze | COMPLETE | Frozen control, parameter grid, cost/statistical plans |
| T1 Data and frozen-control reconstruction | IN PROGRESS — SOURCE AUDIT | Four raw archives acquired successfully; persistent cache and schema audit now being validated |
| T2 Entry tuning | BLOCKED on T1 |
| T3 Exit tuning | BLOCKED on T1 |
| T4 Nested WFO | BLOCKED on T2/T3 |
| T5 Robustness and inference | BLOCKED on T4 |
| T6 Prospective freeze | BLOCKED on T5 |

## T1 execution update — 2026-09-21

The acquisition runs established that the required raw sources are actually downloadable in GitHub Actions:

- 2017–2020 Zenodo option archive;
- 2017–2020 Zenodo NIFTY spot/futures archive;
- 2020–2024 Ayush NIFTY/BankNIFTY archive;
- 2025–2026 Rahul/Dhan NIFTY archive.

Run 35537467726 generated a complete four-file SHA-256 manifest before its only failure: pytest was missing. Run 35537505911 repeated that same test-environment defect. Run 35537798592 contains the correction and is under execution.

The next gate is now source-schema audit, followed by contract-specific normalization into a compact BATMAN cache. The study will continue through every viable acquisition/repair path before declaring the data unavailable.

No tuning P&L is claimed.
