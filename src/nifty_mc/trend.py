from __future__ import annotations
import numpy as np

def classify_trend(samples, s0, neutral_band=0.005, bull_probability=0.60, bear_probability=0.60):
    x = np.asarray(samples, dtype=float)
    p_bull = float(np.mean(x > s0*(1+neutral_band)))
    p_bear = float(np.mean(x < s0*(1-neutral_band)))
    if p_bull >= bull_probability and p_bull > p_bear:
        label = "BULL"
    elif p_bear >= bear_probability and p_bear > p_bull:
        label = "BEAR"
    else:
        label = "NEUTRAL"
    return {"label":label,"p_bull":p_bull,"p_bear":p_bear}
