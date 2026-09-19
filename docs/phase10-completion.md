# Phase 10 Completion — Adaptive Paper-Trading Infrastructure v1

## Status

**PHASE 10 COMPLETE**

Branch: `research/adaptive-paper-signals-v1`

## What is now frozen

### Adaptive candidate sets

- Low volatility: Risk Reversal; Long Synthetic Future; Buy Call
- Medium volatility: Short Straddle; Put Ratio Spread; Short Strangle; Strip; Buy Put
- High volatility: Sell Put; Risk Reversal; Long Synthetic Future; Batman

These are carried forward from the completed pre-2026 CPCV analysis. They are not re-optimized during prospective paper trading.

### Entry rule

New entry signals are produced at **09:30 IST** on NIFTY trading weekdays.

A trade is considered only when the front expiry has exactly **3 future trading sessions** remaining.

### Monte Carlo model

- 5,000 paths
- 756-session return lookback
- terminal P20/P35/P65/P80
- deterministic seed per decision date unless an explicit seed is provided

### Cost and risk controls

- 2 option points per contract stress cost
- 2% paper capital risk budget
- ES95/ES99 risk proxy
- risk sizing uses max(ES95, ES99)
- at least one risk-sized lot is required
- otherwise NO_TRADE
- missing/invalid data is never imputed

### Primary candidate rule

Among eligible candidates in the frozen regime set:

**highest net MC EV → primary paper candidate**

The rule is explicitly **prospective and not historically validated**. The CPCV phase validated the regime-conditioned effect and candidate universe, not this exact ranking rule.

## Scientific safeguards

- Regime rank is strictly past-only.
- Development/test runs are excluded from the prospective ledger.
- The previously used 2026 holdout is not reopened or re-optimized.
- Candidate screening is recorded for every prospective entry day.
- The primary signal and all candidate metrics are persisted.
- No broker order execution is implemented.

## Two-stage daily automation

### 09:30 IST — signal generation

Generates exactly one new entry observation for Batman and Adaptive, if the date is an eligible trading day.

### 16:00 IST — refresh only

The dashboard refresh job:

- settles matured paper trades,
- updates ledgers,
- republishes the dashboards,

and **does not generate another entry signal**.

## Published pages

Root selector:

https://vishnuvcr.github.io/Nifty/

Adaptive:

https://vishnuvcr.github.io/Nifty/adaptive/

Batman:

https://vishnuvcr.github.io/Nifty/batman/

The latest final dashboard deployment completed successfully after Phase 10 validation.

## Validation runs

- Research tests: latest Phase 10 test run completed successfully.
- Manual Adaptive producer run: completed successfully.
- Signal-generation workflow: completed successfully.
- Refresh-only dashboard workflow: completed successfully.

## Phase 10 conclusion

The Adaptive strategy is now a **usable prospective paper-trading strategy specification and signal-generation system**:

**Regime → frozen candidate set → current MC distribution → candidate EV/risk gate → highest eligible net MC EV → paper signal**

It is **not yet a proven live-trading strategy**. The next evidence must come from genuinely new prospective observations collected without changing these rules.
