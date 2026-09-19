# Frozen Parent Provenance

Parent branch: research/adaptive-paper-signals-v1
Parent branch tip at transfer freeze: da17889580691ce5dd5445f19b530e530f60205c

| Parent artefact | Blob SHA | Purpose |
|---|---|---|
| scripts/batman_signal_producer.py | 0423f356f6e79a3718387a2915b21a27261a2803 | Frozen Batman producer implementation |
| scripts/adaptive_paper_signal_producer_v1.py | 716c0577b52d803753c0e177375acf6750f1a564 | Frozen Adaptive producer implementation |
| src/nifty_mc/strategy_catalog.py | a4f31b81175d0f102fe27221d49d1171c32fbe64 | Strategy structure definitions |
| configs/adaptive_paper_v1.json | 65cfbbe84d2866266e86c4f04e1207817ddfe1eb | Frozen Adaptive candidate/risk config |
| docs/batman-paper-trading-candidate.md | 0b3c82b619de97d7ca37f41a108db946dad54374 | Frozen Batman protocol |
| docs/adaptive-paper-trading-v1.md | 9a151b44dd168262aede535743c860309da0bc8b | Frozen Adaptive protocol |

## Freeze rule

No SENSEX outcome data is permitted to modify these parent specifications before the final SENSEX holdout is locked and evaluated.