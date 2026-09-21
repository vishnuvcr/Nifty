# T3 Exit Protocol Freeze

## Entry
The entry rule is inherited unchanged from T2:
D3, same-session 09:30, gross MC-EV > 0, 5,000 paths, 756-session history, BATMAN P20/P35/P65/P80, first positive-volume option OPEN strictly after 09:30, 2-point adverse slippage.

## Exit reference definitions

### Maximum-profit reference
Compute the strategy payoff at the finite set of strike breakpoints implied by the four selected strikes. The maximum observed payoff over those breakpoints is the reference profit.

### Initial-risk reference
Use MC ES95, defined as the negative of the mean MC P&L in the worst 5% of simulated paths, floored at zero.

### Trigger semantics
- Fixed target triggers when realized marked basket P&L >= target fraction × maximum-profit reference.
- Fixed stop triggers when realized marked basket P&L <= negative stop fraction × ES95 reference.
- Trailing stop becomes active after entry and trails the running favorable basket P&L by the declared trail fraction of maximum-profit reference.
- Trailing target activates only after the favorable P&L reaches its activation fraction; after activation it exits on the declared retracement from the running peak.
- Combined trailing-target + fixed-stop rules use the fixed stop independently of the trailing target.

## Execution semantics
Every trigger is evaluated only from observed option closes after entry. The exit itself is the first positive-volume observation strictly after the trigger timestamp, using OPEN and adverse slippage.

No expiry-session hindsight, later bar, later strike or future volume information may affect a trigger.

## Control
Expiry-session final executable option close, subject to the same 2-point adverse slippage assumption.

No post hoc parameter expansion is permitted.
