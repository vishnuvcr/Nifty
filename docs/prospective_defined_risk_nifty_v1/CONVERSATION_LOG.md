# NIFTY Defined-Risk Prospective Validation — Conversation / Audit Log

## 2026-09-20

User directive:
Freeze Jade Lizard, Put Ratio Spread, Sell Put and Bull Put Spread and test them prospectively for NIFTY without changing the rules after future outcomes are seen. Publish each strategy separately and schedule automatic scans.

Action:
- Created a dedicated branch.
- Frozen the four candidate definitions.
- Reused the parent NIFTY MC/WFO model cutoff, 5,000-path MC engine and 756-session lookback.
- Implemented independent candidate signal production.
- Implemented separate Pages dashboards/ledgers.
- Scheduled 09:30 IST entry scanning and 16:00 IST settlement/page refresh.
- Prospective observations remain unbackfilled.

## 2026-09-20 — scope correction

User directive: Remove Sell Put and Bull Put Spread from prospective validation and fix the Pages publication.

Action:
- Narrowed the NIFTY prospective engine and manual workflow choices to Jade Lizard and Put Ratio Spread.
- Removed the superseded strategy dashboards from the prospective branch.
- Updated protocol, phase status, candidate provenance, report, error log and audit log before the prospective stream begins.
- Removed maintenance-push scanning so code changes cannot generate prospective observations.

## 2026-09-20 — Pages dashboard styling

User requested the prospective strategy pages to use the same mobile-friendly paper-trading dashboard presentation as the SENSEX Batman page: badge header, Latest Signal, paper-trading summary, recent signals and scientific boundary cards.

Action:
- Restyled NIFTY Jade Lizard and Put Ratio Spread pages.
- Updated the NIFTY generator so future scanner runs preserve the same layout.
- Sell Put and Bull Put Spread remain excluded.
