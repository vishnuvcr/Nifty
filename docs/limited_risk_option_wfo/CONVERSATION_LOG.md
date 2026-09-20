# Limited-Risk Option WFO — Conversation / Audit Log

## 2026-09-20

### User instruction
The user asked to plan the next NIFTY MC-WFO research phase as a separate repository branch focused on option strategies with limited loss and either limited or unlimited profit, after recognizing that Batman has an unbounded-loss tail.

### Project context reviewed
The surviving project context included:
- NIFTY MC-WFO research and walk-forward work;
- Batman strategy development and paper-trading candidate work;
- expiry-day early-exit sensitivity analysis for NIFTY and SENSEX;
- combined Batman capital analysis;
- SENSEX transfer and robustness work;
- previous requests to avoid contamination of the NIFTY manuscript by separate transfer studies.

### Repository state reviewed
The repository vishnuvcr/Nifty was inspected, including:
- main README;
- research/monte-carlo-wfa-v1;
- strategy catalog and option/cost modules;
- existing WFO and regime workflows;
- prior CPCV/bootstrap results;
- Batman paper-trading candidate;
- expiry-exit research branch logs;
- branch inventory.

### Research decisions frozen for this branch
1. A mechanically verified finite maximum loss is the primary eligibility rule.
2. Limited-loss + limited-profit and limited-loss + unlimited-profit structures are separate risk families.
3. Batman is a descriptive comparator / historical context only, not an eligible limited-risk candidate.
4. Existing MC/WFO methodology remains the parent baseline; this branch is an extension, not a rewrite.
5. The previously exposed 2026 NIFTY period is not a fresh holdout for this new research.
6. Cached option data should be reused before any new download is attempted.
7. Execution realism must include bid/ask, slippage, brokerage, statutory costs and a separate current Paytm Money margin/charges verification before deployment-oriented capital claims.
8. No candidate is promoted on pooled P&L alone.
9. Multiple-testing and data-snooping controls are mandatory.
10. The final manuscript for this branch is separate until the study is complete.

### Implementation note
This log records user-visible decisions and repository-observable evidence. It is an audit record, not a reproduction of private hidden reasoning.
