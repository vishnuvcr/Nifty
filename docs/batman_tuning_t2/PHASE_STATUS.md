# T2 Phase Status

| Phase | Status |
|---|---|
| T0 protocol freeze | COMPLETE |
| T1 data/source validation | COMPLETE |
| T2 entry tuning | IN PROGRESS — CONTROL RECONCILIATION |
| T3 exit tuning | NOT STARTED |
| T4 nested WFO | NOT STARTED |
| T5 robustness/inference | NOT STARTED |
| T6 prospective freeze | NOT STARTED |

## Corrections before accepting T2 results

The first T2 implementation changed the parent BATMAN rule by gating on net MC-EV after execution costs. The corrected T2 version restores the parent gate of gross MC-EV > 0 as the primary rule. Net-cost gating remains a sensitivity only.

The first T2 report also conflated two execution layers. The promoted historical research used daily NSE F&O bhavcopy snapshots; the new timing study uses minute-level option/spot data. The research therefore distinguishes:

1. Parent historical EOD benchmark.
2. Operational D3/09:30 intraday control.

The parent-style EOD benchmark is being reconstructed from the validated 2020-2024 Ayush archive and independently checked against official NSE bhavcopy observations on a stratified sample.

No candidate is promoted until reconciliation is complete.
