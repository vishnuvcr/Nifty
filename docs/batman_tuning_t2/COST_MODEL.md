# T2 Entry Cost Model

## Slippage
Adverse execution stress: 2.0 option-premium points per contract per entry fill.

For a buy leg: adjusted execution premium = observed OPEN + 2.0.

For a sell leg: adjusted execution premium = observed OPEN - 2.0.

The same stress is applied when evaluating the signal-time MC-EV gate so that a positive gate cannot depend on an optimistic mid/close fill.

## Brokerage
Scenarios:
- ₹10 per executed F&O order;
- ₹20 per executed F&O order;
- ₹30 per executed F&O order.

Four BATMAN entry orders are assumed.

Paytm Money's older public F&O material documents ₹10 per option order, while newer account/pricing materials can differ; therefore T2 reports all three scenarios instead of assuming one user's current tariff. citeturn922011search1turn922011search0

## STT
For option sales, use 0.0625% of premium turnover through 2024-09-30 and 0.1% from 2024-10-01 onward. The rate change is documented by Paytm Money and the Union Budget memorandum. citeturn922011search0turn922011search24

T2 reports brokerage/slippage/STT-adjusted results. Exchange transaction charges, GST on brokerage/transaction charges and other statutory line items remain parameterized in the broader T5 cost model; they must not be silently treated as zero in final deployment analysis.
