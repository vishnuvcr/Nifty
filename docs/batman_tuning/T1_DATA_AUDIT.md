# T1 Data and Frozen-Control Reconstruction

## Completed checks

The parent candidate specification was inspected and the frozen BATMAN rule was matched against the T0 protocol:

- D3 / third trading session before expiry;
- 09:30 IST decision;
- 756 prior NIFTY sessions;
- 5,000 Monte Carlo paths;
- P20/P35/P65/P80 terminal quantiles;
- +1 P35 put, -2 P20 puts, +1 C65 call, -2 C80 calls;
- positive net MC-EV gate;
- ES95/ES99 risk-budget proxy;
- missing required strikes/premiums => no trade.

The parent paper-signal implementation was also inspected. It requires timestamped option-chain rows and reconstructs strikes from the decision-date chain.

## Data availability finding

The parent repository's data policy states that bulk market data are not committed. The visible parent data tree currently exposes only the data policy and expiry-exit directory. The executable historical option-chain dataset required for the tuning study is therefore not available through repository contents accessible to this branch.

This is a **data availability blocker**, not evidence that BATMAN cannot be tuned.

## Why the blocker matters

The requested tuning variables require information unavailable from daily expiry settlement alone:

- D0-D6 requires option-chain state at each entry date;
- prior-session-to-open requires opening execution observations;
- fixed/trailing targets and stops require intraday option prices or sufficiently granular executable quotes;
- realistic slippage requires bid/ask or an explicit adverse-execution model.

Using the previously published aggregate BATMAN summary to infer these effects would be invalid because it contains neither the necessary intraday path nor all candidate entry/exit observations.

## Required T1 cache

The next workflow must consume a cached/reproducible dataset containing at minimum:

1. NIFTY trading-session calendar;
2. NIFTY daily closes;
3. historical NIFTY option chains or contract-wise prices for the complete study period;
4. intraday option data for exit rules;
5. timestamps and expiry identifiers;
6. contract lot-size metadata;
7. provenance/hash manifest.

The workflow must fail closed if these are absent.

## T1 conclusion

**Specification reconstruction: PASS.**

**Executable historical-data reconstruction: NOT COMPLETE.**

Therefore T2 and T3 remain blocked. No numerical tuning result is claimed.
