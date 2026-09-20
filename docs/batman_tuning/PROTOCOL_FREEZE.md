# T0 Protocol Freeze

## Frozen control
- Entry: third trading session before target expiry (D3).
- Signal: 09:30 IST.
- Lookback: 756 prior NIFTY sessions.
- Monte Carlo paths: 5,000.
- Strike quantiles: P20, P35, P65, P80.
- Structure: long 1 P35, short 2 P20, long 1 C65, short 2 C80.
- Entry gate: net MC expected P&L greater than zero.

## Entry tuning
Offsets D0, D1, D2, D3, D4, D5, D6.
Timing A: prior-session evening signal to next-session market-open execution.
Timing B: same-session 09:30 signal to post-signal execution.

## Exit families
Frozen parent exit control; fixed target; fixed stop; fixed target plus stop; trailing target; trailing stop; trailing target plus stop.

## Leakage controls
No future price or option quote may enter an entry decision. The prior-session evening branch is computed only from data available by the declared evening cutoff. The market-open price must be the first executable observation after the open, not a hindsight-selected price.
