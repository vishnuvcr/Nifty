from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

@dataclass(frozen=True)
class Leg:
    option_type: str
    strike: float
    qty: int
    expiry: str = "front"  # front or next; qty>0 buy, qty<0 sell

STRATEGY_META = {
    "Buy Call": ("bullish", "directional"),
    "Sell Put": ("bullish", "premium"),
    "Bull Call Spread": ("bullish", "defined_directional"),
    "Bull Put Spread": ("bullish", "credit_defined"),
    "Call Ratio Back Spread": ("bullish", "convex_directional"),
    "Long Calendar with Calls": ("bullish", "calendar"),
    "Bull Condor": ("bullish", "target_range"),
    "Bull Butterfly": ("bullish", "target_price"),
    "Range Forward": ("bullish", "synthetic_directional"),
    "Long Synthetic Future": ("bullish", "synthetic_directional"),
    "Call Ratio Spread": ("bullish_neutral", "ratio"),
    "Put Ratio Spread": ("bearish_neutral", "ratio"),
    "Long Straddle": ("high_vol", "long_vol"),
    "Long Iron Butterfly": ("range_or_move", "defined_long_vol"),
    "Long Strangle": ("high_vol", "long_vol"),
    "Long Iron Condor": ("range", "defined_long_vol"),
    "Strip": ("high_vol_bearish", "long_vol"),
    "Strap": ("high_vol_bullish", "long_vol"),
    "Short Straddle": ("low_vol", "short_vol"),
    "Iron Butterfly": ("range", "defined_short_vol"),
    "Short Strangle": ("range", "short_vol"),
    "Short Iron Condor": ("range", "defined_short_vol"),
    "Batman": ("range_two_peaks", "ratio"),
    "Double Plateau": ("range_two_zones", "defined_ratio"),
    "Jade Lizard": ("bullish_neutral", "credit_partial_defined"),
    "Reverse Jade Lizard": ("bearish_neutral", "credit_partial_defined"),
    "Buy Put": ("bearish", "directional"),
    "Sell Call": ("bearish", "premium"),
    "Bear Put Spread": ("bearish", "defined_directional"),
    "Bear Call Spread": ("bearish", "credit_defined"),
    "Put Ratio Back Spread": ("bearish", "convex_directional"),
    "Long Calendar with Puts": ("bearish", "calendar"),
    "Bear Condor": ("bearish", "target_range"),
    "Bear Butterfly": ("bearish", "target_price"),
    "Risk Reversal": ("bullish", "synthetic_directional"),
    "Short Synthetic Future": ("bearish", "synthetic_directional"),
}

STRATEGY_NAMES = list(STRATEGY_META)

def _L(t: str, k: float, q: int, e: str = "front") -> Leg:
    return Leg(t, float(k), int(q), e)

def build_strategy(name: str, k: Dict[str, float]) -> List[Leg]:
    a = k
    if name == "Buy Call": return [_L("CE", a["atm"], 1)]
    if name == "Sell Put": return [_L("PE", a["atm"], -1)]
    if name == "Bull Call Spread": return [_L("CE", a["atm"], 1), _L("CE", a["c65"], -1)]
    if name == "Bull Put Spread": return [_L("PE", a["p35"], -1), _L("PE", a["p10"], 1)]
    if name == "Call Ratio Back Spread": return [_L("CE", a["atm"], -1), _L("CE", a["c65"], 2)]
    if name == "Long Calendar with Calls": return [_L("CE", a["atm"], -1, "front"), _L("CE", a["atm"], 1, "next")]
    if name == "Bull Condor": return [_L("CE", a["atm"], 1), _L("CE", a["c65"], -1), _L("CE", a["c75"], -1), _L("CE", a["c90"], 1)]
    if name == "Bull Butterfly": return [_L("CE", a["atm"], 1), _L("CE", a["c65"], -2), _L("CE", a["c80"], 1)]
    if name == "Range Forward": return [_L("PE", a["p35"], -1), _L("CE", a["c65"], 1)]
    if name == "Long Synthetic Future": return [_L("CE", a["atm"], 1), _L("PE", a["atm"], -1)]
    if name == "Call Ratio Spread": return [_L("CE", a["atm"], 1), _L("CE", a["c65"], -2)]
    if name == "Put Ratio Spread": return [_L("PE", a["atm"], 1), _L("PE", a["p35"], -2)]
    if name == "Long Straddle": return [_L("CE", a["atm"], 1), _L("PE", a["atm"], 1)]
    if name == "Long Iron Butterfly": return [_L("PE", a["p35"], 1), _L("PE", a["atm"], -1), _L("CE", a["atm"], -1), _L("CE", a["c65"], 1)]
    if name == "Long Strangle": return [_L("PE", a["p35"], 1), _L("CE", a["c65"], 1)]
    if name == "Long Iron Condor": return [_L("PE", a["p10"], 1), _L("PE", a["p35"], -1), _L("CE", a["c65"], 1), _L("CE", a["c90"], -1)]
    if name == "Strip": return [_L("CE", a["atm"], 1), _L("PE", a["atm"], 2)]
    if name == "Strap": return [_L("CE", a["atm"], 2), _L("PE", a["atm"], 1)]
    if name == "Short Straddle": return [_L("CE", a["atm"], -1), _L("PE", a["atm"], -1)]
    if name == "Iron Butterfly": return [_L("PE", a["p35"], -1), _L("PE", a["atm"], 1), _L("CE", a["atm"], 1), _L("CE", a["c65"], -1)]
    if name == "Short Strangle": return [_L("PE", a["p35"], -1), _L("CE", a["c65"], -1)]
    if name == "Short Iron Condor": return [_L("PE", a["p10"], 1), _L("PE", a["p35"], -1), _L("CE", a["c65"], -1), _L("CE", a["c90"], 1)]
    if name == "Batman": return [_L("PE", a["p35"], 1), _L("PE", a["p20"], -2), _L("CE", a["c65"], 1), _L("CE", a["c80"], -2)]
    if name == "Double Plateau": return [_L("PE", a["p20"], 1), _L("PE", a["p35"], -2), _L("PE", a["p45"], 1),
                                           _L("CE", a["c55"], 1), _L("CE", a["c65"], -2), _L("CE", a["c80"], 1)]
    if name == "Jade Lizard": return [_L("PE", a["p35"], -1), _L("CE", a["c65"], -1), _L("CE", a["c90"], 1)]
    if name == "Reverse Jade Lizard": return [_L("CE", a["c65"], -1), _L("PE", a["p35"], -1), _L("PE", a["p10"], 1)]
    if name == "Buy Put": return [_L("PE", a["atm"], 1)]
    if name == "Sell Call": return [_L("CE", a["atm"], -1)]
    if name == "Bear Put Spread": return [_L("PE", a["atm"], 1), _L("PE", a["p35"], -1)]
    if name == "Bear Call Spread": return [_L("CE", a["atm"], -1), _L("CE", a["c90"], 1)]
    if name == "Put Ratio Back Spread": return [_L("PE", a["atm"], -1), _L("PE", a["p35"], 2)]
    if name == "Long Calendar with Puts": return [_L("PE", a["atm"], -1, "front"), _L("PE", a["atm"], 1, "next")]
    if name == "Bear Condor": return [_L("PE", a["p45"], 1), _L("PE", a["p35"], -1), _L("PE", a["p25"], -1), _L("PE", a["p10"], 1)]
    if name == "Bear Butterfly": return [_L("PE", a["atm"], 1), _L("PE", a["p35"], -2), _L("PE", a["p20"], 1)]
    if name == "Risk Reversal": return [_L("CE", a["c65"], 1), _L("PE", a["p35"], -1)]
    if name == "Short Synthetic Future": return [_L("CE", a["atm"], -1), _L("PE", a["atm"], 1)]
    raise KeyError(name)
