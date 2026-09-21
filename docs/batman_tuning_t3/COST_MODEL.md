# T3 Cost Model

Primary output is net P&L.

## Slippage
Adverse slippage is fixed at 2 option-premium points on every executed entry leg and exit leg.

## Brokerage
Report ₹10, ₹20 and ₹30 per executed F&O order. BATMAN uses four entry orders and four exit orders for separately executed legs.

## STT
Apply the historical option-sale STT rate by execution date. Do not use one timeless rate across the full study.

## Lot size
Use the historical NIFTY lot size applicable to the target expiry date rather than the current lot size.

Every result retains gross points, net INR, brokerage, STT, slippage assumption and lot size.
