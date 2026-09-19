from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.adaptive_paper_signal_producer_v1 import (
    CANDIDATES_BY_REGIME,
    candidate_contract_count,
    select_primary_candidate,
    strategy_targets,
)


def test_candidate_universe_matches_frozen_cpcv_sets() -> None:
    assert CANDIDATES_BY_REGIME["low"] == [
        "Risk Reversal",
        "Long Synthetic Future",
        "Buy Call",
    ]
    assert CANDIDATES_BY_REGIME["medium"] == [
        "Short Straddle",
        "Put Ratio Spread",
        "Short Strangle",
        "Strip",
        "Buy Put",
    ]
    assert CANDIDATES_BY_REGIME["high"] == [
        "Sell Put",
        "Risk Reversal",
        "Long Synthetic Future",
        "Batman",
    ]


def test_contract_counts_are_strategy_specific() -> None:
    assert candidate_contract_count("Buy Call") == 1
    assert candidate_contract_count("Short Straddle") == 2
    assert candidate_contract_count("Put Ratio Spread") == 3
    assert candidate_contract_count("Short Strangle") == 2
    assert candidate_contract_count("Strip") == 3
    assert candidate_contract_count("Risk Reversal") == 2
    assert candidate_contract_count("Long Synthetic Future") == 2
    assert candidate_contract_count("Batman") == 6


def test_strategy_targets_use_only_required_terminal_quantiles() -> None:
    terminal = np.array([95.0, 100.0, 105.0, 110.0])
    assert strategy_targets("Buy Call", terminal, 102.0) == {"atm": 102.0}
    assert strategy_targets("Put Ratio Spread", terminal, 102.0) == {
        "atm": 102.0,
        "p35": 100.25,
    }
    assert strategy_targets("Batman", terminal, 102.0) == {
        "p20": 98.0,
        "p35": 98.5,
        "c65": 106.5,
        "c80": 108.0,
    }


def test_primary_selection_prefers_highest_net_ev_only_with_eligibility() -> None:
    rows = [
        {"strategy": "A", "eligible": True, "net_ev": 8.0, "cpcv_frequency": 1},
        {"strategy": "B", "eligible": True, "net_ev": 12.0, "cpcv_frequency": 1},
        {"strategy": "C", "eligible": False, "net_ev": 100.0, "cpcv_frequency": 9},
    ]
    selected = select_primary_candidate(rows)
    assert selected["strategy"] == "B"


def test_config_matches_checked_in_spec() -> None:
    config = json.loads(Path("configs/adaptive_paper_v1.json").read_text())
    assert config["execution"]["mc_paths"] == 5000
    assert config["execution"]["lookback_sessions"] == 756
    assert config["execution"]["entry_sessions_before_expiry"] == 3
    assert config["execution"]["stress_cost_points_per_contract"] == 2.0
    assert config["execution"]["risk_pct"] == 0.02
