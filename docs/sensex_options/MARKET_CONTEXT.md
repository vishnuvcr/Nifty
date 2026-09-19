# SENSEX Market/Contract Context — Initial Audit

Last reviewed: 2026-09-20

## Current observations

- Current SENSEX option-chain sources list a 20-unit lot size and September 24, 2026 as the front expiry. Current option pages also show strikes such as 75,600/75,700/75,800 for that expiry. These observations are used only to design the data audit, not as historical backtest inputs.
- BSE published a 2015 notice revising the SENSEX derivatives market lot from 15 to 20 for November 2015 and later expiries.
- BSE's methodology history shows that SENSEX derivative expiry conventions changed over time, including a 2023 move from Thursday to Friday and a 2025 methodology change referring to Tuesday for the monthly futures contract. Current listed contracts must therefore be read from date-specific contract metadata rather than from a single hard-coded weekday rule.
- Paytm Money's current F&O FAQ states brokerage of Rs.10 per unique executed order, while Paytm Money's historical 2023 pricing communication stated Rs.20 per executed F&O order for new users and preserved older account-vintage rates. Therefore the research configuration must use an effective-date/account-versioned brokerage scenario rather than a single universal number.

## SENSEX transfer-control implication

Before any historical result is calculated, the pipeline must join each option observation to the contract metadata effective on that date: expiry date, lot size, strike grid, tick size, settlement type and availability.

Any conflict between a generalized expiry calendar and the actual contract master is resolved in favor of the point-in-time contract record. Conflicting public sources are retained in the provenance log.

## Sources to retain in the data manifest

- BSE market-lot notice / historical contract documentation.
- BSE contract-format documentation, which explicitly provides expiry date, strike price, option type, minimum lot size, tick size and contract start/settlement fields.
- Current market listings only as cross-checks for current state; they are not substitutes for historical contract records.
- Paytm Money current F&O FAQ and historical pricing notices, with effective dates.

## No performance conclusion

This file records contract-data risks only. It is not evidence that Batman or Adaptive works on SENSEX.