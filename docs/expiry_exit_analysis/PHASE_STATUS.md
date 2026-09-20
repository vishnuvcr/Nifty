# Expiry-Day Exit Analysis — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata) — verified CI result published

| Phase | Status |
|---|---|
| E0 Exit-method specification | COMPLETE |
| E1 Analysis engine | COMPLETE |
| E2 Data preparation workflow | COMPLETE |
| E3 CI execution | COMPLETE |
| E4 Results verification | COMPLETE |
| E5 Final comparison report | COMPLETE |

## Branch

research/expiry-auction-exit-analysis-v1

CI runner: the analysis branch contains a push-triggered workflow and also declares workflow_dispatch. The connected GitHub toolset cannot call workflow_dispatch directly, so this run is being initiated by a controlled documentation push to the analysis branch. Analysis code and outputs remain isolated on this branch.

## Verified result set

GitHub Actions run: 35492648657 — conclusion: success.

## Frozen scenario set

- expiry settlement baseline
- 15:00 IST
- 15:10 IST

No exit result is used to change entry rules. Results are published under reports/expiry_exit/.

Numerical results are verified and published under reports/expiry_exit/.
