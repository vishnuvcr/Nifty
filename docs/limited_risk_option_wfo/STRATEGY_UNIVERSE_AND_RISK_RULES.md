# Strategy Universe and Risk Rules

## Source universe

The starting universe is the 36 strategies declared in src/nifty_mc/strategy_catalog.py. The complete catalog is audited mechanically; no manual label is authoritative.

## Mathematical risk domain

For index-option expiry payoff analysis, the underlying domain is **S >= 0**.

This matters for puts: a short put can lose heavily if the index approaches zero, but its terminal loss is still finite because the index cannot become less than zero. By contrast, net short-call exposure has an unbounded adverse upper tail as S -> infinity.

## Mechanical audit

For every catalog strategy the auditor evaluates:
- exact leg quantities;
- option type;
- front versus next expiry;
- aggregate call slope as S -> infinity;
- terminal payoff on a dense S>=0 grid;
- whether loss is unbounded, profit is unbounded, or both are bounded.

Risk classes:
- R1 = finite maximum loss + potentially unlimited favorable upper-tail profit.
- R2 = finite maximum loss + finite maximum profit on S>=0.
- R3 = finite-loss but multi-expiry/path-dependent.
- X = unbounded adverse loss; excluded from the limited-risk core.

## Expected core classifications, subject to the executable audit

### R1
Buy Call; Call Ratio Back Spread; Long Straddle; Long Strangle; Strip; Strap; Range Forward; Long Synthetic Future; Risk Reversal.

### R2
Sell Put; Bull Call Spread; Bull Put Spread; Put Ratio Spread; Long Iron Butterfly; Long Iron Condor; Iron Butterfly; Short Iron Condor; Double Plateau; Buy Put; Bear Put Spread; Bear Call Spread; Bull/Bear Condors; Bull/Bear Butterflies; Jade Lizard; Put Ratio Back Spread.

### R3
Long Calendar with Calls; Long Calendar with Puts.

### Expected X examples
Call Ratio Spread; Short Call; Short Straddle; Short Strangle; Batman; Reverse Jade Lizard; Short Synthetic Future.

The executable audit remains authoritative if any strategy behaves differently because its actual leg definition differs from this expectation.

## Important distinction from common trading-language labels

Terms such as “defined risk” are not accepted as evidence by themselves. The classification here is mathematical and domain-specific. A structure may be colloquially described as “risky” while still having a finite terminal loss under S>=0, or may have apparently hedged legs while retaining an unbounded short-call tail.

## Position sizing

For a core candidate, the structural maximum loss is the hard risk bound. MC ES95/ES99 is a secondary diagnostic, never a replacement for a known finite structural maximum.

Historical rupee capital requirements require the actual trade's strikes, premiums, lot size and cost model. They cannot be inferred from aggregate P&L alone.
