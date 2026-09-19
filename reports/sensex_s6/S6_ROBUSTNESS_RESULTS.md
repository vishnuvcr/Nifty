# SENSEX S6 Robustness Results

Frozen Batman/Adaptive rules; one-lot transfer-edge mode; no SENSEX retuning.

## Slippage sensitivity

| scenario      | split       |   slippage_points_per_leg |   adaptive_trades |   adaptive_total_pnl |   adaptive_mean_pnl |   adaptive_win_rate |   adaptive_profit_factor |   adaptive_max_drawdown |   batman_trades |   batman_total_pnl |   batman_mean_pnl |   batman_win_rate |   batman_profit_factor |   batman_max_drawdown |
|:--------------|:------------|--------------------------:|------------------:|---------------------:|--------------------:|--------------------:|-------------------------:|------------------------:|----------------:|-------------------:|------------------:|------------------:|-----------------------:|----------------------:|
| slippage_0.25 | development |                      0.25 |                 0 |                  0   |                0    |            0        |                  0       |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |
| slippage_0.25 | holdout     |                      0.25 |                18 |              55490.1 |             3082.78 |            0.666667 |                  1.59571 |                     nan |              26 |             213291 |           8203.51 |          0.846154 |                3.70653 |                   nan |
| slippage_0.25 | validation  |                      0.25 |                10 |              36087.9 |             3608.79 |            0.6      |                  2.32693 |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |
| slippage_0.50 | development |                      0.5  |                 0 |                  0   |                0    |            0        |                  0       |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |
| slippage_0.50 | holdout     |                      0.5  |                18 |              55055.5 |             3058.64 |            0.666667 |                  1.59045 |                     nan |              26 |             212512 |           8173.54 |          0.846154 |                3.69254 |                   nan |
| slippage_0.50 | validation  |                      0.5  |                10 |              36037.9 |             3603.79 |            0.6      |                  2.32412 |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |
| slippage_1.00 | development |                      1    |                 0 |                  0   |                0    |            0        |                  0       |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |
| slippage_1.00 | holdout     |                      1    |                18 |              54186.3 |             3010.35 |            0.666667 |                  1.57994 |                     nan |              26 |             210953 |           8113.6  |          0.846154 |                3.6647  |                   nan |
| slippage_1.00 | validation  |                      1    |                10 |              35937.8 |             3593.78 |            0.6      |                  2.3185  |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |
| slippage_2.00 | development |                      2    |                 0 |                  0   |                0    |            0        |                  0       |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |
| slippage_2.00 | holdout     |                      2    |                18 |              57864.5 |             3214.69 |            0.666667 |                  1.6168  |                     nan |              26 |             207836 |           7993.71 |          0.846154 |                3.60952 |                   nan |
| slippage_2.00 | validation  |                      2    |                10 |              35737.8 |             3573.78 |            0.6      |                  2.30732 |                     nan |               0 |                  0 |              0    |          0        |                0       |                   nan |

## Seed sensitivity (0.50-point slippage)

| split      |   adaptive_total_mean |   adaptive_total_min |   adaptive_total_max |   adaptive_positive_seed_fraction |   batman_total_mean |   batman_total_min |   batman_total_max |   batman_positive_seed_fraction |
|:-----------|----------------------:|---------------------:|---------------------:|----------------------------------:|--------------------:|-------------------:|-------------------:|--------------------------------:|
| holdout    |               63844.9 |              51324.1 |              71587.3 |                                 1 |              216474 |             205049 |             225549 |                               1 |
| validation |               35369   |              18161.1 |              43304.1 |                                 1 |                   0 |                  0 |                  0 |                               0 |

## Dependence-aware bootstrap

| strategy   |   n_validation_holdout_trades |   observed_mean_pnl |   observed_total_pnl |   bootstrap_ci_low_mean_pnl |   bootstrap_ci_high_mean_pnl |   bootstrap_p_mean_gt_zero |
|:-----------|------------------------------:|--------------------:|---------------------:|----------------------------:|-----------------------------:|---------------------------:|
| Adaptive   |                            28 |             3253.34 |              91093.4 |                    -3080.27 |                      9467.81 |                     0.8413 |
| Batman     |                            26 |             8173.54 |             212512   |                     1353.79 |                     14539.8  |                     0.9921 |

## Controls

- Slippage grid is a predeclared stress analysis, not a preferred-cost selection.
- Seed sensitivity measures Monte Carlo path/strike instability without changing the frozen candidate universe.
- Block bootstrap is descriptive uncertainty, not a guarantee of future performance.
- No historical bid/ask snapshots were available; quote-source sensitivity is therefore not claimed.
- One-lot edge results do not establish deployability for a ₹100,000 account.
