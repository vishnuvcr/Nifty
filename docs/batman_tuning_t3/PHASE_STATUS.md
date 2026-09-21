# T3 Phase Status

| Phase | Status |
|---|---|
| T0 protocol freeze | COMPLETE |
| T1 data/source validation | COMPLETE |
| T2 entry tuning | COMPLETE — corrected gross-gate results frozen |
| T3 exit tuning | IN PROGRESS |
| T4 nested WFO | NOT STARTED |
| T5 robustness/inference | NOT STARTED |
| T6 prospective freeze | NOT STARTED |

## T3 starting state
T3 uses the frozen D3/09:30 operational control and does not alter entry selection. The 2025-2026 dataset remains reserved for the final outer holdout.

## T2 reconciliation status
The parent historical benchmark is an EOD bhavcopy execution layer, while T3's entry control is an intraday 09:30 execution layer. This distinction is preserved throughout T3 and T4.

No exit variant is promoted before nested walk-forward analysis.
