# Data sources and provenance

## NSE
Official NSE historical derivative reports include contract-wise price-volume data and daily/monthly F&O archives. NSE's data-sharing documentation identifies contract-wise price-volume data and F&O archives as research data sources.

## India VIX
India VIX is calculated from NIFTY option order-book prices and represents expected volatility over the next 30 calendar days. It is therefore an implied-volatility diagnostic, not a realized-volatility forecast.

## Research dataset tiers
Tier A: timestamped bid/ask option quotes or order-book snapshots.
Tier B: timestamped option trades with reconstructed executable prices.
Tier C: daily option OHLC/settlement data.

The walk-forward engine should run Tier A/B first when available; Tier C is a secondary robustness experiment.
