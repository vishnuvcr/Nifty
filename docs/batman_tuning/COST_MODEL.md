# Cost Model

Gross P&L is never the primary result.

Include brokerage or order fees, exchange transaction charges, GST and statutory charges where applicable, SEBI charges, stamp duty, STT where applicable, bid-ask or adverse slippage, and liquidity/impact stress when data allow.

BATMAN contains four option instruments and six contracts. Under separate execution of each leg there are four entry orders and four exit orders per round trip.

The current broker fee schedule must be re-verified from Paytm Money before any deployment decision. The current NSE contract-information page is the authority for applicable contract metadata and lot size.

Every result must identify the cost-model version, slippage assumption and lot-size assumption.


## Current Paytm Money execution-cost verification — 2026-09-21

Paytm Money's public materials indicate that brokerage is charged per executed F&O order; its onboarding FAQ currently states ₹10 per unique executed F&O order, while Paytm Money's published pricing update states a ₹20 per executed order schedule for newer accounts and its later 2026 educational material describes flat-₹20 models. These public pages are not sufficient to infer the exact account-specific tariff for a particular trader. Therefore the research engine must expose brokerage as an explicit scenario parameter and must not hard-code an account-specific legacy rate.

For conservative current-account sensitivity, the branch will report at least ₹10 / ₹20 / ₹30 per executed order scenarios, with the actual deployment tariff checked against the live Paytm Money pricing page/account before any live use. citeturn234496search2turn234496search9turn785577search3

Paytm Money also documents ₹50 + applicable taxes for an intraday square-off order. That fee is not automatically added to the planned BATMAN research trades when exits are deliberately executed as normal orders; it becomes relevant only if the broker's auto-square-off mechanism is invoked. citeturn234496search7

Paytm Money's October 2024 pricing update states STT on sale of options increased to 0.1% of transaction value from 1 October 2024. The cost engine must therefore use the applicable historical tax schedule by trade date rather than one timeless rate. citeturn234496search0

NSE's current Equity Derivatives Contract Information page is the authoritative reference for permitted lot size and related contract metadata; it was updated on 10 September 2026. Historical lot sizes must be taken from the contract applicable on each trade date, not a single current lot size. citeturn234496search1
