# Limited-Risk Option WFO — Literature Review (L1)

Last updated: 2026-09-20.

## Evidence used to set the methodology

### Backtest overfitting and multiple testing
Bailey et al. describe backtest overfitting as a source of optimistic simulated performance when many alternative configurations are searched. Their Probability of Backtest Overfitting paper proposes combinatorial cross-validation specifically for investment backtests.

Sources:
- Bailey et al. (2015), The Probability of Backtest Overfitting: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Bailey & López de Prado (2014), The Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey et al. (2014), Pseudo-Mathematics and Financial Charlatanism: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659

### Data-snooping correction
Sullivan, Timmermann and White apply White's Reality Check bootstrap to a full universe of trading rules to quantify data-snooping bias.

Source:
- Sullivan, Timmermann & White (1999), Data-Snooping, Technical Trading Rule Performance, and the Bootstrap: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=160330

### White Reality Check / Hansen SPA
Hsu and Kuan discuss White's Reality Check and Hansen's SPA for evaluating trading-rule performance while accounting for data snooping and transaction costs.

Source:
- Hsu & Kuan (2005), Re-Examining Technical Analysis with White's Reality Check and Hansen's SPA: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=685361

### Volatility and option pricing
The academic literature distinguishes physical-return dynamics from option-implied/risk-neutral information. This supports using Monte Carlo as a forecasting input without assuming that option prices equal the physical distribution.

Sources:
- Atmaz (2022), Stock Return Extrapolation, Option Prices, and Variance Risk Premium, Review of Financial Studies 35(3): https://academic.oup.com/rfs/issue/35/3
- Hao & Zhang (2013), GARCH Option Pricing Models, the CBOE VIX, and Variance Risk Premium: https://academic.oup.com/jfec/article-abstract/11/3/556/845864

## Strategy-taxonomy implications
The literature does not establish profitability of any particular NIFTY weekly-options strategy. It supports the experimental design:
- separate defined-risk structures from unbounded-loss structures;
- use data-snooping controls over the declared strategy universe;
- include execution costs;
- distinguish physical Monte Carlo forecasts from option-market pricing;
- reserve an untouched future period for confirmation.

## Indian execution references
NSE's published STT schedule states that from 1 April 2026 the sale of an option in securities is charged at 0.15% of option premium for the seller. NSE's contract-information pages provide current expiry and lot-size references. NSE's 3 October 2025 circular revised the NIFTY 50 market lot from 75 to 65 for the applicable revised contracts.

Sources:
- NSE STT: https://www.nseindia.com/static/products-services/equity-derivatives-securities-transaction-tax
- NSE contract information: https://www.nseindia.com/static/products-services/equity-derivatives-contract-information
- NSE NIFTY 50 F&O: https://www.nseindia.com/static/products-services/equity-derivatives-nifty50
- NSE lot-size circular: https://nsearchives.nseindia.com/content/circulars/FAOP70616.pdf

Paytm Money's current F&O FAQ states ₹10 brokerage per unique executed F&O order; its margin materials state that option buyers pay premium while option writers require margin and that exact basket margin should be checked using the margin calculator.

Sources:
- Paytm Money F&O FAQ: https://www.paytmmoney.com/stocks/customer/fno-faq/onboarding-and-kyc/account-segment-activation/how-to-activate-fo-from-mobile-app-web
- Paytm Money margin calculator information: https://www.paytmmoney.com/blog/margin-calculator/
- Paytm Money brokerage calculator: https://www.paytmmoney.com/stocks/brokerage-calculator

## L1 conclusion
L1 freezes the methodological rationale but provides no empirical profitability conclusion. No strategy is selected from literature. The next step is L2 data audit and then L3 mechanical payoff-risk classification.
