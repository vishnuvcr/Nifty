# Strategy Universe and Risk Rules

## Source universe

The starting universe is the 36 strategies declared in src/nifty_mc/strategy_catalog.py. The first empirical run uses a mechanical audit over the complete catalog; no manual risk label is authoritative.

## Mechanical risk definition

For NIFTY's economically admissible underlying domain S >= 0, the classifier evaluates:
- exact leg quantities and expiry tags;
- aggregate call slope as S -> infinity;
- terminal payoff on a dense S>=0 grid;
- front-expiry versus multi-expiry structure.

A negative aggregate call slope implies an unbounded adverse upper-tail loss. A positive aggregate call slope implies an unbounded upper-tail profit. Put exposure remains finite as S approaches zero because the index cannot become negative.

The classifier is therefore more reliable than a manually curated “defined-risk” list.

## Classes produced by the audit

- R1: finite maximum loss, potentially unlimited favorable upper-tail profit.
- R2: finite maximum loss and finite maximum profit on the S>=0 domain.
- R3: finite-loss but multi-expiry/path-dependent; excluded from the single-expiry core.
- X: unbounded adverse loss; excluded from the limited-risk core.

## Important corrected classifications

### R1
- Buy Call
- Long Straddle
- Long Strangle
- Strip
- Strap
- Call Ratio Back Spread

### R2
- Buy Put
- Bull Call Spread
- Bull Put Spread
- Put Ratio Back Spread
- Bull Condor
- Bull Butterfly
- Long Iron Butterfly
- Long Iron Condor
- Iron Butterfly
- Short Iron Condor
- Bear Put Spread
- Bear Call Spread
- Bear Condor
- Bear Butterfly
- Double Plateau

### R3
- Long Calendar with Calls
- Long Calendar with Puts

These calendars have finite loss but require a path-/multi-expiry valuation model, so they are not mixed with single-expiry terminal-payoff tests.

### X
- Sell Put
- Range Forward
- Long Synthetic Future
- Call Ratio Spread
- Put Ratio Spread
- Short Straddle
- Short Strangle
- Batman
- Jade Lizard
- Reverse Jade Lizard
- Sell Call
- Risk Reversal
- Short Synthetic Future

Any structure that fails the mechanical audit is excluded regardless of its catalogue label.

## Position-sizing rule

For the limited-risk core, the structural maximum loss is the hard risk bound. MC ES95/ES99 remains a secondary diagnostic and must never replace a known finite maximum-loss calculation.

Historical rupee capital requirements require the actual entry strikes, premiums, lot size and cost model. They cannot be reconstructed honestly from aggregate strategy P&L alone.
