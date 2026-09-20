# Limited-Risk Option WFO — L2 Data Audit

## Status
2026-09-20 — audit specification complete; empirical CI audit pending.

## Source
The intended empirical source is the existing NIFTY option archive used by the parent strategy-regime-lab-v2 workflow on research/monte-carlo-wfa-v1. The new branch will use the latest successful acquisition artifact from that parent workflow rather than silently downloading a different archive.

## Known schema from the parent acquisition workflow
- timestamp
- expiry
- symbol
- option_type
- strike
- close

## Critical limitation
The parent historical archive exposes end-of-day option close data to the strategy-regime-lab-v2 engine, not a verified historical bid/ask stream.

Therefore:
- the historical result can be reproduced as an EOD option-price reconstruction;
- it cannot honestly be labelled as historical executable bid/ask replay;
- the analysis retains explicit adverse execution stress;
- no missing quote is silently imputed.

## Expiry/date controls
The parent engine uses actual listed expiries present in the option archive and derives the final market session from the NIFTY index history.

## Fresh-holdout control
The current parent Batman research records a data boundary around 2026-03-30. The new branch must not use the already-exposed 2026 sample as a clean final holdout.

## L2 gate
Pass when the CI audit confirms:
1. all years in the pinned acquisition are readable;
2. NIFTY/CE/PE schema invariants hold;
3. decision dates are ordered and unique;
4. expiry dates are after decision dates;
5. no malformed strikes/prices enter the analysis;
6. source coverage is recorded;
7. the prior-exposure boundary is preserved.
