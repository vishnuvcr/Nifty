# Long-Premium MC/WFO v1 — Conversation / Audit Log

## 2026-09-20

User instruction:
- Create a new research question around buying cheap NIFTY calls/puts using the MC/WFO forecast.
- Include premium, brokerage, slippage and time decay.
- Do not stop until the phase produces a usable result/report.

Research action:
- Reviewed the limited-risk branch and the frozen parent NIFTY strategy artifact.
- Confirmed 607 Buy Call and 607 Buy Put decision observations in the parent strategy-trades artifact.
- Froze a 22-rule cheapness universe.
- Ran development-only selection, chronological validation, block-bootstrap uncertainty, cross-rule max-statistic bootstrap, and cost sensitivity.
- Corrected a prototype parameter-handling error before committing code.
- Historical conclusion: no selected rule passed the validation gate.

Interpretation boundary:
- The 2025-2026 period is already exposed and cannot be promoted to fresh holdout evidence.
- No paper/live promotion was made.
