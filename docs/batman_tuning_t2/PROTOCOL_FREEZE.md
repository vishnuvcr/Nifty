# T2 Entry Protocol Freeze

## Frozen control
D3 + same-session 09:30 signal + first executable observation after 09:30.

## Decision-day offsets
D0-D6 mean the 0th through 6th prior trading sessions relative to the target expiry session.

## Signal timestamps
- Timing A: prior trading session, 15:30 IST cutoff.
- Timing B: entry session, 09:30 IST.

## Execution timestamps
- Timing A: first positive-volume observation on the entry date at/after 09:15 IST.
- Timing B: first positive-volume observation on the entry date strictly after 09:30 IST.

## Strike selection
- Forecast quantiles are calculated first.
- Then the closest unique listed strikes are selected from contracts observable by the signal timestamp.
- No later strike listing may influence selection.

## Intrinsic expiry realization
For the entry study, realized expiry P&L is based on the NIFTY spot close on the target expiry session. This keeps T2 focused on entry timing. T3 will use intraday option marks for active exit rules.

## D0 caveat
D0 Timing B is evaluated with the frozen one-session Monte Carlo horizon floor inherited from the parent model. It is separately flagged so later intraday-MC sensitivity cannot be confused with an ex-post model change.

## No look-ahead
No close, premium, strike, expiry, or execution observation after the signal timestamp may enter the signal or strike-selection decision.
