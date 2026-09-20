# Long-Premium MC/WFO v1 — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata)

| Phase | Status | Result / gate |
|---|---|---|
| LP0 Protocol freeze and parent-artifact audit | COMPLETE | Parent run 35425922439 and strategy-trades schema verified. |
| LP1 Long-call/long-put rule grid | COMPLETE | 22 predeclared cheapness rules tested. |
| LP2 Development-only selection | COMPLETE | Buy Call <=0.55% of spot selected by mean-SE score. |
| LP3 Validation | COMPLETE | Selected rule failed validation: mean -1.68 points, PF 0.968. |
| LP4 Statistical robustness | COMPLETE | Validation block bootstrap CI crosses zero; max-statistic multiple-testing p=0.886. |
| LP5 Cost sensitivity | COMPLETE | Stored in COST_SENSITIVITY.csv. |
| LP6 Fresh holdout | HOLD | 2025-2026 is already exposed by parent research. |
| LP7 Prospective promotion | HOLD | No rule promoted. |
| LP8 Manuscript/report | COMPLETE | FINAL_PHASE_REPORT.md completed. |

## Current decision

**HOLD — no Buy Call/Buy Put rule is promoted.**

A fresh post-exposure dataset and deployment-grade bid/ask history are required for any future confirmation.
