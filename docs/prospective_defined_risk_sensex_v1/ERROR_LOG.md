# SENSEX Defined-Risk Prospective Validation — Error Log

Resolved configuration/deployment issues:

- The initial SENSEX prospective configuration exposed Sell Put and Bull Put Spread alongside Jade Lizard and Put Ratio Spread. They were removed before the first eligible prospective observation.
- Branch code pushes could trigger scanner execution during maintenance. The branch workflow push trigger was removed so only the scheduled weekday scan and manual dispatch can create prospective observations.
- The Pages root selector did not expose the defined-risk prospective section. The root page and publisher summary are being updated so the deployed navigation matches the active two-candidate scope.

Controls inherited from SENSEX S7:
- executable bid/ask required;
- no LTP fallback;
- hard NO_TRADE on schema/data failures;
- 5,000 MC paths;
- 756-session lookback;
- 0.50-point adverse slippage per executed contract;
- existing SENSEX transaction-cost schedule;
- one-lot paper mode;
- no broker orders.
