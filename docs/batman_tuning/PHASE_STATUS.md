# Phase Status

| Phase | Status | Evidence |
|---|---|---|
| T0 Protocol freeze | COMPLETE | Frozen control, parameter grid, cost/statistical plans |
| T1 Data and frozen-control reconstruction | **PARTIAL / BLOCKED** | Control specification independently matched to parent candidate; executable historical option-chain dataset is not present in this branch or parent `data/` tree |
| T2 Entry tuning | BLOCKED on T1 |
| T3 Exit tuning | BLOCKED on T1 |
| T4 Nested WFO | BLOCKED on T2/T3 |
| T5 Robustness and inference | BLOCKED on T4 |
| T6 Prospective freeze | BLOCKED on T5 |

## T1 finding

The parent BATMAN candidate specification is available and matches the frozen control:

- D3 entry;
- 09:30 signal;
- 756 prior NIFTY sessions;
- 5,000 MC paths;
- P20/P35/P65/P80;
- +1 P35 PE, -2 P20 PE, +1 C65 CE, -2 C80 CE;
- positive net MC-EV gate.

However, the parent repository explicitly does not commit bulk market data, and its visible `data/` tree contains only the data policy and an expiry-exit directory. The historical executable option-chain dataset needed to test D0-D6 and intraday exits is therefore not available to this branch through the repository contents currently accessible.

**No tuning P&L is fabricated from the parent summary.**

T1 can be completed when the required cached historical option data / artifact is made available to the workflow. The next implementation step is to make the workflow consume that cache rather than repeatedly download bulk data.
