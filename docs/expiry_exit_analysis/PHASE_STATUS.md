# Expiry-Day Exit Analysis — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata) — CI rerun after SENSEX pricer argument correction

| Phase | Status |
|---|---|
| E0 Exit-method specification | COMPLETE |
| E1 Analysis engine | COMPLETE |
| E2 Data preparation workflow | COMPLETE |
| E3 CI execution | IN PROGRESS |
| E4 Results verification | NOT STARTED |
| E5 Final comparison report | NOT STARTED |

## Branch

research/expiry-auction-exit-analysis-v1

CI runner: the analysis branch contains a push-triggered workflow and also declares workflow_dispatch. The connected GitHub toolset cannot call workflow_dispatch directly, so this run is being initiated by a controlled documentation push to the analysis branch. Analysis code and outputs remain isolated on this branch.

## Frozen scenario set

- expiry settlement baseline
- 15:00 IST
- 15:10 IST

No exit result is used to change entry rules.

Numerical results remain unclaimed until the CI run completes and the required output files pass verification.
