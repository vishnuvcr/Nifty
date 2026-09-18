# Data policy

Do not commit bulk market data to this repository.

The research pipeline expects:
- Nifty 50 historical spot/index prices
- India VIX history
- NIFTY option-chain snapshots or contract-wise historical option prices
- expiry calendar
- risk-free proxy

NSE provides official historical derivative reports and contract-wise price-volume data. Its historical-data framework also describes bhavcopy, snapshots, trades and related archives.

For a production-quality options backtest, bid/ask or sufficiently granular trade/order-book data is preferred over settlement prices alone because the four-leg Long Iron Condor requires executable entry prices.
