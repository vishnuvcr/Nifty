# Expiry-Day Exit Analysis — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata) — CI retry after network interruption

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

CI trigger: main-branch pull_request + branch-push workflow; analysis code remains isolated on this branch.

## Frozen scenario set

- expiry settlement baseline
- 15:00 IST
- 15:10 IST

No exit result is used to change entry rules.
