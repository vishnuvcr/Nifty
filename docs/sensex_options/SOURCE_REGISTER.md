# SENSEX S1 Source Register

Last reviewed: 2026-09-20

## Exchange / contract sources

1. BSE Derivatives Chain. The public BSE derivatives chain exposes, for SENSEX options, expiry, strike, option type, LTP, bid price/quantity, ask price/quantity, volume and open interest fields. This establishes that executable quote fields exist in the BSE market-data display, but does not establish that a historical 09:30 archive is publicly available from the page itself.
   URL: https://www.bseindia.com/stock-share-price/future-options/derivatives/532646/%7B%7BLM_hisdata_url%7D%7D

2. BSE Equity Derivatives file-format documentation. The published derivatives file format includes contract/market fields such as expiry date, strike price, option type and OHLC/market summary fields. The EOD BhavCopy schema does not provide a historical best-bid/best-ask snapshot.
   URL: https://www.bseindia.com/downloads1/File_Format_Equity_Derivatives.pdf

3. BSE November 2015 specifications. SENSEX options were documented with lot size 20, 0.05 tick size, cash settlement and last-Thursday European expiry in that period.
   URL: https://www.bseindia.com/downloads1/BSE_Update_Nov_2015.pdf

4. BSE April 2023 methodology update. BSE/S&P BSE documentation records a change in SENSEX derivatives monthly expiry from Thursday to Friday in 2023. This demonstrates that expiry weekday must be treated as date-specific rather than hard-coded for a long historical test.
   URL: https://www.bseindia.com/downloads/SPDJ_ANN/MediaReleasePDF/1463746_mediareleasemodificationtothemethodologiesofthes%26pbseindices20230428.pdf

5. BSE October 2023 transaction-charge notice. BSE revised transaction charges for S&P BSE SENSEX Options nearest/immediate expiry from 1 November 2023 using premium-value turnover slabs. The backtest cost model must include exchange transaction charges in addition to broker brokerage and statutory levies.
   URL: https://www.bseindia.com/markets/MarketInfo/DispNewNoticesCirculars.aspx?page=20231020-46

## Broker-cost sources

6. Paytm Money current F&O FAQ. Current public FAQ states ₹10 brokerage for every unique executed F&O order.
   URL: https://www.paytmmoney.com/stocks/customer/fno-faq/onboarding-and-kyc/account-segment-activation/how-to-activate-fo-from-mobile-app-web

7. Paytm Money 25-Aug-2023 brokerage notice. Official notice states that account-vintage pricing differs: users joining before Aug 2022 retained ₹10 F&O/order; users joining Aug 2022–Aug 2023 retained ₹15; new users from 25-Aug-2023 were charged ₹20/order. Historical research must therefore use an effective-date/account-vintage scenario instead of a single universal brokerage value.
   URL: https://www.paytmmoney.com/blog/brokerage-charges-increase-from-25th-aug-23-existing-users-will-continue-on-old-brokerage-charges/

## S1 conclusion

The exchange and broker sources confirm that a serious SENSEX transfer study must be date-aware for contract metadata and cost rules. The EOD exchange files are useful for historical settlement/market diagnostics, but an executable 09:30 historical-options result requires a point-in-time quote dataset with bid/ask (or an explicitly labelled proxy analysis).
