# Frozen Long-Premium Rules

The following rule family was frozen before validation was interpreted.

## Candidate universe

1. Buy Call
2. Buy Put

## Cheapness filter

Entry premium divided by NIFTY spot must be <= one of these predeclared thresholds:

0.30%, 0.35%, 0.40%, 0.45%, 0.50%, 0.55%, 0.60%, 0.65%, 0.70%, 0.75%, 0.80%.

## MC gate

Net MC expected P&L must be > 0 after baseline execution stress.

## Selection

Development-only candidate generation. Minimum development sample 20. Select maximum mean P&L minus one standard error.

## Costs

- 2.0 option points per contract execution stress.
- ₹10 per executed F&O order.
- Two orders for a round trip.
- NIFTY lot size 65 in this research snapshot.
- Brokerage is converted to option points before the gate.

## Important time-decay rule

The realized historical trade P&L is:

expiry intrinsic value - option premium paid - execution costs

Therefore time decay is already represented through the difference between premium paid and terminal intrinsic value. No separate theta deduction is permitted.

## No-retuning rule

The validation period and exposed period cannot be used to alter the candidate threshold, side, or MC gate.
