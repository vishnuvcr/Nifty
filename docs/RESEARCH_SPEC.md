# Nifty 50 Monte Carlo + Walk-Forward Research

## Objective
Build an out-of-sample framework that forecasts Nifty 50 expiry-price distributions and classifies the expected direction as bull, bear, or neutral, then evaluates whether those forecasts can support a Long Iron Condor under realistic option-market assumptions.

## Modeling distinction
The Monte Carlo forecast is a physical-measure forecast of future index outcomes. Option prices embed a risk-neutral/implied distribution. A difference between the two is not automatically arbitrage.

## Baseline Monte Carlo
For each decision date:
- S0: observed Nifty 50 spot/index level.
- T: actual time to expiry in years.
- mu: physical drift estimated only from observations available before the decision timestamp.
- sigma: volatility estimated only from observations available before the decision timestamp.

GBM baseline:
S_T = S0 * exp((mu - 0.5*sigma^2)*T + sigma*sqrt(T)*Z)

Use physical drift for forecasting. If a risk-neutral diagnostic is required, run a separate simulation using risk-free carry and dividends.

Primary volatility variants:
1. Rolling realized volatility.
2. EWMA volatility.
3. GARCH-family forecast.
4. India VIX / option-implied volatility as a separate diagnostic.

Primary simulation count: 50,000 paths per forecast origin, deterministic seed sequence.

## Forecast outputs
For each expiry:
- P01/P05/P10/P25/P50/P75/P90/P95/P99 of S_T
- 50/80/90% prediction intervals
- expected and median move
- probabilities of defined up/down moves
- bull/bear/neutral classification
- calibration versus realized expiry

Default trend rule:
- Bull when P(S_T > S0*(1+q)) >= bull_threshold
- Bear when P(S_T < S0*(1-q)) >= bear_threshold
- Neutral otherwise

Thresholds must be pre-registered or selected only on development data.

## Long Iron Condor
Strikes K1 < K2 < K3 < K4:
- short put K1
- long put K2
- long call K3
- short call K4
- net debit D

Expiry profit:
max(K1-ST,0) - max(K2-ST,0) + max(ST-K3,0) - max(ST-K4,0) - D

Piecewise:
- ST <= K1: (K2-K1)-D
- K1 < ST < K2: (K2-ST)-D
- K2 <= ST <= K3: -D
- K3 < ST < K4: (ST-K3)-D
- ST >= K4: (K4-K3)-D

Breakevens, when they fall within the active wings:
- lower = K2 - D
- upper = K3 + D

Maximum loss is the debit. Maximum upside/downside profit is wing-width minus debit on the corresponding side; it can differ if wing widths differ.

## Walk-forward protocol
For each chronological forecast origin:
1. Fit parameters only on data strictly before origin.
2. Generate the expiry distribution.
3. Freeze strike selection and entry assumptions.
4. Record realized expiry outcome and executable strategy P&L.
5. Move forward and refit.

Run expanding and rolling windows. Never use future option-chain state, future volatility, or future prices during training.

## Evaluation
Forecast:
- interval coverage and width
- interval score
- CRPS when full distributions are retained
- balanced accuracy
- MCC
- Brier score and reliability
- directional confusion matrix

Trading:
- trade count
- mean/median P&L
- expectancy
- win rate
- profit factor
- cumulative P&L
- max drawdown
- Sharpe/Sortino
- tail losses
- turnover
- realized-vs-forecast PoP calibration

Robustness:
- bootstrap confidence intervals
- yearly/regime breakdowns
- simple baselines
- parameter perturbation
- alternative volatility estimators
- multiple strike-selection rules

A positive Monte Carlo EV under one assumed volatility is not sufficient evidence of an exploitable edge.
