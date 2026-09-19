# Phase 10 — Adaptive Paper-Trading Infrastructure

Status: COMPLETE

Date: 2026-09-19

## Frozen research basis

The completed pre-2026 CPCV + block-bootstrap phase found that the regime-conditioned return effect was more reproducible than the exact strategy identity. The prospective Adaptive system therefore freezes a candidate set for each volatility regime rather than a single permanent strategy.

Candidate sets:

- Low: Risk Reversal; Long Synthetic Future; Buy Call
- Medium: Short Straddle; Put Ratio Spread; Short Strangle; Strip; Buy Put
- High: Sell Put; Risk Reversal; Long Synthetic Future; Batman

The primary-selection rule is prospective: among eligible candidates, choose the highest net MC EV. This exact ranking rule has not been historically validated and is intentionally being tested prospectively.

## Operational protocol

- Entry processing: 09:30 IST on NIFTY trading weekdays.
- Entry eligibility: exactly 3 future trading sessions to the target expiry.
- Historical cutoff: latest completed NIFTY session before the entry decision.
- Monte Carlo: 5,000 bootstrap paths from the previous 756 daily log returns.
- Stress execution cost: 2 option points per contract.
- Risk sizing: max(ES95, ES99), 2% paper-account risk budget, NIFTY lot size 65.
- Candidate gate: net MC EV > 0 and at least one risk-sized lot.
- Missing/invalid data: NO_TRADE; no imputation.
- Exit benchmark: expiry settlement; no discretionary early exit.
- No broker order execution.

## Publication architecture

The GitHub Pages site has one root selector with two independent dashboards:

- Batman
- Adaptive Regime

Adaptive state is isolated under paper_trading/adaptive_* and site/adaptive/*.

The root page is shared only as a selector; Batman and Adaptive do not share signal or ledger state.

## Automation

- 09:30 IST (04:00 UTC, weekdays): new entry signal workflow.
- 16:00 IST (10:30 UTC, weekdays): refresh-only workflow. It settles matured paper trades and republishes the pages without generating a second entry signal.
- Manual workflow_dispatch is available from the default-branch Adaptive workflow.

## Phase 10 validation

The branch research test suite passes after correction of:

- adaptive source-generation syntax,
- strategy-quantile unit expectations,
- strictly past-only volatility ranks,
- block-bootstrap test interface,
- Batman/Adaptive page separation and central scheduler compatibility.

The latest branch research test run completed successfully.

## Trading-status conclusion

Phase 10 is an infrastructure completion, not a claim of a new realized trading edge. The Adaptive strategy is now ready for genuinely prospective observations.

No new trade should be backfilled on a non-entry day merely to populate the ledger. The next valid Adaptive signal must be produced by the frozen 09:30 IST entry workflow on a genuine NIFTY entry session using then-available data.

The 2026 holdout already used in earlier research remains untouched.