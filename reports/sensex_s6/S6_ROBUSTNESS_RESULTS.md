# SENSEX S6 Robustness Results

Frozen Batman/Adaptive rules; one-lot transfer-edge mode; no SENSEX retuning.

## Slippage sensitivity

| scenario      | split       |   slippage_points_per_leg |   adaptive_trades |   adaptive_total_pnl |   adaptive_mean_pnl |   adaptive_win_rate |   adaptive_profit_factor |   adaptive_max_drawdown |   batman_trades |   batman_total_pnl |   batman_mean_pnl |   batman_win_rate |   batman_profit_factor |   batman_max_drawdown |
|:--------------|:------------|--------------------------:|------------------:|---------------------:|--------------------:|--------------------:|-------------------------:|------------------------:|----------------:|-------------------:|------------------:|------------------:|-----------------------:|----------------------:|
| slippage_0.25 | development |                      0.25 |                51 |             327832   |             6428.08 |            0.705882 |                  2.53888 |                     nan |              40 |            61846.8 |           1546.17 |          0.85     |                1.65363 |                   nan |
| slippage_0.25 | holdout     |                      0.25 |                18 |              52188.7 |             2899.37 |            0.666667 |                  1.56027 |                     nan |              26 |           206689   |           7949.56 |          0.846154 |                3.62274 |                   nan |
| slippage_0.25 | validation  |                      0.25 |                46 |             115993   |             2521.59 |            0.608696 |                  1.61862 |                     nan |              18 |            47281.1 |           2626.73 |          0.777778 |                1.90125 |                   nan |
| slippage_0.50 | development |                      0.5  |                51 |             327167   |             6415.04 |            0.705882 |                  2.53428 |                     nan |              40 |            60647.6 |           1516.19 |          0.85     |                1.63974 |                   nan |
| slippage_0.50 | holdout     |                      0.5  |                18 |              51754.1 |             2875.23 |            0.666667 |                  1.55504 |                     nan |              26 |           205909   |           7919.59 |          0.846154 |                3.60889 |                   nan |
| slippage_0.50 | validation  |                      0.5  |                46 |             115474   |             2510.29 |            0.608696 |                  1.61531 |                     nan |              18 |            46741.6 |           2596.75 |          0.777778 |                1.88893 |                   nan |
| slippage_1.00 | development |                      1    |                50 |             296099   |             5921.98 |            0.7      |                  2.28637 |                     nan |              40 |            58249.3 |           1456.23 |          0.85     |                1.61212 |                   nan |
| slippage_1.00 | holdout     |                      1    |                18 |              50884.9 |             2826.94 |            0.666667 |                  1.54461 |                     nan |              26 |           204351   |           7859.64 |          0.846154 |                3.5813  |                   nan |
| slippage_1.00 | validation  |                      1    |                46 |             114434   |             2487.7  |            0.608696 |                  1.6087  |                     nan |              18 |            45662.4 |           2536.8  |          0.777778 |                1.86446 |                   nan |
| slippage_2.00 | development |                      2    |                50 |             293680   |             5873.61 |            0.7      |                  2.27189 |                     nan |              40 |            53452.7 |           1336.32 |          0.85     |                1.5575  |                   nan |
| slippage_2.00 | holdout     |                      2    |                18 |              49146.6 |             2730.37 |            0.666667 |                  1.52388 |                     nan |              26 |           201234   |           7739.76 |          0.846154 |                3.52662 |                   nan |
| slippage_2.00 | validation  |                      2    |                46 |             119701   |             2602.2  |            0.608696 |                  1.63449 |                     nan |              18 |            43504.1 |           2416.89 |          0.777778 |                1.81619 |                   nan |

## Seed sensitivity (0.50-point slippage)

| split      |   adaptive_total_mean |   adaptive_total_min |   adaptive_total_max |   adaptive_positive_seed_fraction |   batman_total_mean |   batman_total_min |   batman_total_max |   batman_positive_seed_fraction |
|:-----------|----------------------:|---------------------:|---------------------:|----------------------------------:|--------------------:|-------------------:|-------------------:|--------------------------------:|
| holdout    |               59234.1 |              51324.1 |              66010.6 |                                 1 |            215263   |           205049   |           226179   |                               1 |
| validation |               94264.7 |              83682.8 |             108616   |                                 1 |             47338.2 |            44124.4 |            51886.4 |                               1 |

## Dependence-aware bootstrap

| strategy   |   n_validation_holdout_trades |   observed_mean_pnl |   observed_total_pnl |   bootstrap_ci_low_mean_pnl |   bootstrap_ci_high_mean_pnl |   bootstrap_p_mean_gt_zero |
|:-----------|------------------------------:|--------------------:|---------------------:|----------------------------:|-----------------------------:|---------------------------:|
| Adaptive   |                            64 |             2612.93 |               167228 |                    -804.314 |                      6133.11 |                     0.9314 |
| Batman     |                            44 |             5742.06 |               252651 |                     662.675 |                     10341.5  |                     0.9875 |

## Controls

- Slippage grid is a predeclared stress analysis, not a preferred-cost selection.
- Seed sensitivity measures Monte Carlo path/strike instability without changing the frozen candidate universe.
- Block bootstrap is descriptive uncertainty, not a guarantee of future performance.
- No historical bid/ask snapshots were available; quote-source sensitivity is therefore not claimed.
- One-lot edge results do not establish deployability for a ₹100,000 account.
