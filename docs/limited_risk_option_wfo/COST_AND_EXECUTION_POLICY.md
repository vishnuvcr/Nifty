# Cost and Execution Policy

## 1. Objective

Every reported strategy result must be economically net of the declared execution-cost model.

## 2. Existing research baseline

The parent research commonly uses a stress convention of 2 option points per contract for comparative robustness.

This branch retains that stress as one mandatory sensitivity point so results remain comparable with the parent research.

## 3. Execution model

For each entry:
- BUY option -> executable price = ask, plus adverse slippage;
- SELL option -> executable price = bid, minus adverse slippage.

For each exit:
- close a long -> bid, minus adverse slippage;
- close a short -> ask, plus adverse slippage.

If only end-of-day close is available, the result must be labelled as an EOD reconstruction and must not be presented as an executable intraday fill.

## 4. Cost components

The model must separately track:
- brokerage;
- exchange transaction charges;
- SEBI or other statutory charges where applicable;
- GST;
- stamp duty;
- option-selling STT where applicable;
- explicit adverse slippage;
- turnover.

The existing src/nifty_mc/costs.py defaults are a research baseline, not a claim about today's Paytm Money tariff.

## 5. Paytm Money verification rule

Before any deployment-oriented capital statement:
1. verify the current Paytm Money brokerage schedule;
2. verify applicable F&O exchange/statutory charges;
3. verify the exact basket's margin using the current broker margin calculator;
4. capture the date/time/source;
5. archive the snapshot in the branch;
6. do not substitute historical cost assumptions for the current broker state.

## 6. Sensitivity grid

The minimum planned execution stress grid is:
- 0.00 points/leg;
- 0.50 points/leg;
- 1.00 points/leg;
- 2.00 points/leg;
- 3.00 points/leg.

A broader stress grid may be added only before seeing the final holdout.

## 7. Reporting

Every strategy-level result must report:
- gross P&L;
- total explicit costs;
- slippage;
- net P&L;
- cost per trade;
- turnover;
- max loss after costs;
- return on max loss.
