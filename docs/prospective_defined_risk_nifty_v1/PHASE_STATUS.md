# NIFTY Defined-Risk Prospective Validation — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata)

| Phase | Status | Evidence |
|---|---|---|
| NPV0 Candidate freeze | COMPLETE | Two strategies retained for prospective observation; Sell Put and Bull Put Spread were removed before the first eligible observation. |
| NPV1 Execution/cost specification | COMPLETE | Bid/ask, slippage, brokerage and STT rules frozen. |
| NPV2 Signal producer | COMPLETE | Independent per-strategy MC/WFO scanner implemented. |
| NPV3 Pages/ledger | COMPLETE | Two separate strategy dashboards and ledgers implemented. |
| NPV4 Scheduled workflow | COMPLETE | 09:30 IST weekday scanner and 16:00 IST settlement/page refresh defined. |
| NPV5 Prospective observations | ACTIVE | Observation stream begins from the next eligible NIFTY trading session for Jade Lizard and Put Ratio Spread; no result is backfilled. |
| NPV6 Statistical assessment | PENDING | Requires a meaningful prospective sample under the frozen rules. |
| NPV7 Promotion gate | HOLD | No paper/live promotion before the prospective evidence gate. |

## Frozen candidates

Jade Lizard; Put Ratio Spread.

Each retained candidate is assessed independently. Sell Put and Bull Put Spread are outside the prospective scope. The phase never chooses a winner retrospectively.
