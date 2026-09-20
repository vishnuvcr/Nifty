# Expiry-Day Exit Analysis — NIFTY + SENSEX

Entry rules were frozen before exit outcomes. Exit scenarios: expiry settlement, 15:00 IST, 15:10 IST.

Historical minute-bar execution proxy: exact exit-minute OPEN; no same-minute CLOSE look-ahead.
NIFTY: 2 option-point stress at entry and 2 option-point stress at early exit, one strategy unit/one lot for exit comparison.
SENSEX: frozen S5/S6 one-lot transfer-edge entry gate and SENSEX transaction-cost model; early-close turnover costs applied; no exercise STT on early exits.

- NIFTY Adaptive 15:00: n=167, total=₹-1,101,335.75, mean=₹-6,594.82, win=42.5%, PF=0.58, bootstrap CI=-12794.920359281437 to -354.0671781437136.
- NIFTY Adaptive 15:10: n=167, total=₹-1,111,582.00, mean=₹-6,656.18, win=42.5%, PF=0.57, bootstrap CI=-12878.935329341317 to -410.4417290419166.
- NIFTY Adaptive expiry_settlement: n=168, total=₹445,425.00, mean=₹2,651.34, win=52.4%, PF=1.46, bootstrap CI=-427.320684523808 to 5662.718080357147.
- NIFTY Batman 15:00: n=50, total=₹228,671.25, mean=₹4,573.43, win=68.0%, PF=4.28, bootstrap CI=1475.690125 to 8007.379625.
- NIFTY Batman 15:10: n=50, total=₹227,473.50, mean=₹4,549.47, win=70.0%, PF=3.98, bootstrap CI=1448.4315 to 8074.175375.
- NIFTY Batman expiry_settlement: n=51, total=₹174,718.75, mean=₹3,425.86, win=80.4%, PF=2.17, bootstrap CI=-177.9473039215653 to 6611.375735294126.
- SENSEX Adaptive 15:00: n=59, total=₹63,824.16, mean=₹1,081.77, win=49.2%, PF=1.12, bootstrap CI=-6891.2769741375405 to 9345.481056227642.
- SENSEX Adaptive 15:10: n=59, total=₹16,425.05, mean=₹278.39, win=49.2%, PF=1.03, bootstrap CI=-7148.456714909407 to 7995.505975721205.
- SENSEX Adaptive expiry_settlement: n=64, total=₹167,227.66, mean=₹2,612.93, win=62.5%, PF=1.60, bootstrap CI=-906.3710905056092 to 6112.477683792905.
- SENSEX Batman 15:00: n=19, total=₹110,249.09, mean=₹5,802.58, win=78.9%, PF=11.35, bootstrap CI=1322.7925384834746 to 11085.98009008426.
- SENSEX Batman 15:10: n=21, total=₹179,645.07, mean=₹8,554.53, win=81.0%, PF=19.53, bootstrap CI=1912.1667116153328 to 17410.585566949478.
- SENSEX Batman expiry_settlement: n=22, total=₹126,325.43, mean=₹5,742.06, win=81.8%, PF=2.92, bootstrap CI=618.5478280254259 to 10776.06164479122.
