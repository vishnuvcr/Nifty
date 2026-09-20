# SENSEX Defined-Risk Prospective Validation v1

## Purpose

Transfer the two retained NIFTY finite-loss candidates to SENSEX and observe them prospectively without selecting among them from future outcomes. The prospective scope was narrowed before the first eligible observation.

Current frozen candidates:
- Jade Lizard
- Put Ratio Spread

Superseded pre-observation candidates: Sell Put and Bull Put Spread. They are not part of the SENSEX prospective stream.

## Frozen transfer rules

- Entry: 09:30 IST.
- Target expiry: exactly the third future weekday, using the frozen SENSEX prospective calendar rule.
- Monte Carlo: 5,000 bootstrap paths from 756 completed daily log returns.
- Each strategy is evaluated independently.
- Positive net MC EV is an entry gate.
- Executable bid/ask is mandatory. Missing quote = NO_TRADE.
- 0.50-point adverse execution/slippage stress per contract remains frozen for SENSEX.
- SENSEX transaction-cost model from the prior S2 work is retained, including brokerage, exchange charges, SEBI fee, stamp duty, GST and STT.
- One-lot paper observation only.
- Expiry settlement is the common prospective benchmark.

## Scientific boundary

This is a transfer/prospective observation phase, not a SENSEX retuning phase. The two retained candidate definitions cannot be replaced, reordered, or optimized using SENSEX future outcomes.

Any parameter change requires a new branch and a new validation boundary.

## Scope-change record — 2026-09-20

The prospective SENSEX scope was narrowed to Jade Lizard and Put Ratio Spread before any prospective observation. Sell Put and Bull Put Spread are excluded from future scans, ledgers and Pages dashboards. No prospective outcome was used to make this change.
