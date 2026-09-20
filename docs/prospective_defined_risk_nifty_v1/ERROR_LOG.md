# NIFTY Defined-Risk Prospective Validation — Error Log

Resolved configuration/deployment issues:

- The initial prospective configuration exposed Sell Put and Bull Put Spread alongside Jade Lizard and Put Ratio Spread. They were removed before the first eligible prospective observation so the prospective universe now contains only the two retained candidates.
- Branch code pushes were able to trigger the scanner, which could create non-market-day NO_TRADE rows during maintenance. The branch workflow push trigger was removed; only the scheduled weekday scan and manual dispatch can create prospective observations.
- The Pages root selector did not expose the defined-risk prospective section. The root page and publisher summary are being updated so the deployed Pages navigation matches the active two-candidate scope.

Prevention controls:
- hard quote validation;
- no LTP fallback;
- exact 09:30 entry boundary;
- prior-session model cutoff;
- deterministic MC seed;
- independent candidate ledgers;
- one commit after all four candidates are scanned;
- no parameter changes from prospective outcomes.
