# BATMAN Tuning T2 — Entry Timing Study

## Aim
Evaluate D0-D6 entry offsets and two pre-registered signal/execution timings against the frozen D3/09:30 control, using the same BATMAN Monte Carlo model and causal execution rules.

## Study horizon
Primary T2 study: 2020-01-01 through 2024-10-31, using the validated Ayush NIFTY options archive. 2025-2026 remains an untouched final/outer holdout for later nested WFO.

## Entry candidates
- Offsets D0, D1, D2, D3, D4, D5, D6.
- Timing A: previous-session evening signal -> next-session market-open execution.
- Timing B: same-session 09:30 signal -> first executable observation after 09:30.
- Control: D3 + Timing B.

## Monte Carlo freeze
- 756 prior completed NIFTY daily log returns.
- 5,000 paths.
- Bootstrap-with-replacement daily return sampling.
- Terminal spot = signal spot × exp(sum sampled returns).
- Horizon for Timing A = max(1, Dk + 1) completed/future sessions from the evening signal; the extra session is the entry day.
- Horizon for Timing B = max(1, Dk). D0 therefore uses the same one-session floor as the parent BATMAN engine; this is a known approximation for expiry-day 09:30 and is not silently changed after results are seen.
- Seed is deterministic and derived from the expiry/offset/timing identifier.
- Quantiles: P20/P35/P65/P80.
- BATMAN legs remain +1 P35 PE, -2 P20 PE, +1 C65 CE, -2 C80 CE.

## Causal price rules
Signal prices use only observations available at the signal timestamp. Strike availability is restricted to contracts observed by that timestamp.

Timing A:
- signal spot = prior-session NIFTY close;
- signal option marks = last positive-volume observation at or before 15:30 IST on the prior session;
- execution = first positive-volume observation on the entry session at or after 09:15 IST; use that bar OPEN per leg.

Timing B:
- signal spot = NIFTY spot at 09:30 IST from the spot archive;
- signal option marks = last positive-volume observation at or before 09:30 IST;
- execution = first positive-volume observation strictly after 09:30 IST; use that bar OPEN per leg.

A basket is a valid entry only if all four required contracts have usable signal marks and usable execution observations. Different legs may execute at different first executable timestamps; those timestamps are retained in the trade-level output.

## Entry gate
Primary/frozen gate: positive **gross** Monte Carlo expected P&L, exactly matching the promoted parent Batman rule. Execution costs are applied to realized P&L and reported as a sensitivity; a secondary net-cost-adjusted MC-EV gate is also reported but is not the primary selection rule.

Execution-cost sensitivity uses:
- 2.0 points adverse slippage per option contract;
- Paytm Money brokerage scenario;
- applicable option-sale STT.

Brokerage scenarios are ₹10, ₹20 and ₹30 per executed F&O order. Four entry orders are assumed because BATMAN has four distinct legs. Historical lot size is date/expiry dependent.

## Historical lot-size schedule used for INR conversion
- Expiries through 2021-06-30: 75.
- July-2021 through April-25-2024 expiries: 50.
- May-2024 through November-19-2024 expiries: 25.

These boundaries follow NSE circulars: the 2021 revision changed NIFTY from 75 to 50 for July-2021 and later contracts; the 2024 revision changed NIFTY from 50 to 25 for contracts available from April 26, 2024 and later; the November 2024 revision to 75 affects new contracts from November 20, 2024 onward, outside the Ayush T2 endpoint. citeturn926639search16turn926639search15turn926639search17

## Output
- Complete candidate opportunity matrix, including non-trades and skip reasons.
- Trade-level results for every eligible D0-D6 × timing observation.
- Gross and net MC-EV.
- Gross and net realized expiry P&L under each brokerage scenario.
- Trade count, win rate, expectancy, profit factor, maximum drawdown and tail metrics by candidate.
- Matched control comparisons.

No candidate is promoted in T2. Selection, if any, is provisional until T4 nested WFO and T5 inference.
