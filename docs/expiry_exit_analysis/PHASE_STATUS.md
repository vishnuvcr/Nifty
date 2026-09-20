# Expiry-Day Exit Analysis — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata) — authoritative PR dispatcher

| Phase | Status |
|---|---|
| E0 Exit-method specification | COMPLETE |
| E1 Analysis engine | COMPLETE |
| E2 Data preparation workflow | COMPLETE |
| E3 CI execution | BLOCKED — explicit manual GitHub Actions dispatch required |
| E4 Results verification | NOT STARTED |
| E5 Final comparison report | NOT STARTED |

## Branch

research/expiry-auction-exit-analysis-v1

CI runner: explicit manual dispatch from the main-branch dispatcher; analysis code and outputs remain isolated on this branch. The connected GitHub toolset cannot invoke workflow_dispatch itself.

## Frozen scenario set

- expiry settlement baseline
- 15:00 IST
- 15:10 IST

No exit result is used to change entry rules.
