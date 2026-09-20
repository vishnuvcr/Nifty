# SENSEX Defined-Risk Prospective Validation — Conversation / Audit Log

## 2026-09-20

User directive:
Add Jade Lizard, Put Ratio Spread, Sell Put and Bull Put Spread to separate SENSEX prospective validation, with separate Pages and scheduled workflows.

Action:
- Created a dedicated SENSEX branch from the existing S7 infrastructure.
- Frozen the four candidate strategies.
- Reused the SENSEX 5,000-path / 756-session MC specification and existing transaction-cost engine.
- Implemented independent candidate scans and separate strategy dashboards/ledgers.
- Scheduled 09:30 IST entry scanning and 16:00 IST settlement/page refresh.
- No historical SENSEX result was substituted for prospective observations.

## 2026-09-20 — scope correction

User directive: Remove Sell Put and Bull Put Spread from prospective validation and fix the Pages publication.

Action:
- Narrowed the SENSEX prospective engine and manual workflow choices to Jade Lizard and Put Ratio Spread.
- Removed the superseded strategy dashboards from the prospective branch.
- Updated protocol, phase status, candidate provenance, report, error log and audit log before the prospective stream begins.
- Removed maintenance-push scanning so code changes cannot generate prospective observations.
