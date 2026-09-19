# SENSEX v1 Cost Model

Base study account: ₹100,000 paper capital; risk budget 2%.

| Cost | Base rule | Effective period/source |
|---|---|---|
| Paytm Money brokerage | ₹10 per unique executed F&O order | Current Paytm Money F&O FAQ; historical account-vintage rates are a sensitivity, not silently substituted |
| BSE Sensex option transaction fee | ₹500/₹1 crore premium turnover for low-volume pre-2024 slab; ₹3,250/₹1 crore premium turnover from 2024-10-01 | BSE notices |
| STT on short option sale | 0.10% of premium through 2026-03-31; 0.15% from 2026-04-01 | Income Tax/NSE tax schedule |
| STT on long option exercised at expiry | 0.125% of intrinsic value through 2026-03-31; 0.15% from 2026-04-01 | Income Tax/NSE tax schedule |
| SEBI turnover fee | 0.00010% of option premium turnover | SEBI/NSE fee schedule |
| Stamp duty | 0.003% of option premium on buyer side | NSE/Paytm public schedule |
| GST | 18% on brokerage + exchange transaction charges + SEBI fee | Paytm Money public pricing description |
| Slippage | 0.50 option points adverse per contract per executed leg, base; sensitivity 0.25/1.00/2.00 | Pre-registered research assumption because dataset has OHLC, not bid/ask |

## Quote limitation

The SENSEX dataset used in this transfer test contains OHLCV/OI bars, not historical best bid/ask. Therefore entry execution is modeled from the 09:30 bar open plus adverse slippage. It is a bar-based executable-price proxy, not a reconstructed bid/ask backtest.

## Historical brokerage sensitivity

Paytm Money's official historical communication shows account-vintage F&O rates of ₹10/₹15/₹20 per order. The base case uses the currently published ₹10/order; a ₹20/order sensitivity is mandatory in S6.