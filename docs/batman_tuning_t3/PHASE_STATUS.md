# T3 Phase Status

| Phase | Status |
|---|---|
| T0 protocol freeze | COMPLETE |
| T1 data/source validation | COMPLETE |
| T2 entry tuning | COMPLETE — corrected gross-gate results frozen |
| T3 exit tuning | COMPLETE — corrected run 20 accepted |
| T4 nested WFO | IN PROGRESS |
| T5 robustness/inference | NOT STARTED |
| T6 prospective freeze | NOT STARTED |

## Accepted T3 run

GitHub Actions run: 35601226109.

Validation:
- source acquisition: PASS
- unit tests: PASS
- full 165-variant grid: PASS
- denominator/grid completeness: PASS
- artifact: batman-tuning-t3-exit-results
- artifact SHA-256: 9bcfa5bda14472142c28dd846467903575b815634c2a6b7813621b1b0ecc4925

The accepted T3 results contain 69 trades per exit variant and three brokerage scenarios.

The prior T3 run that dropped non-triggering exits is retained only as a rejected audit artifact.
