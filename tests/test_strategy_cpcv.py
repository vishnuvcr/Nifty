from pathlib import Path

import numpy as np

from scripts.run_strategy_cpcv import (
    contract_count,
    iid_bootstrap_prob_positive,
    moving_block_bootstrap_prob_positive,
    summary,
)


def test_contract_count_matches_catalog():
    assert contract_count("Batman") == 6
    assert contract_count("Short Iron Condor") == 4


def test_summary_handles_losses_and_drawdown():
    s = summary(np.array([10.0, -5.0, 8.0, -3.0]))
    assert s["n"] == 4
    assert s["total"] == 10.0
    assert s["profit_factor"] > 1
    assert s["max_drawdown"] < 0


def test_bootstrap_functions_return_probabilities():
    x = np.array([1.0, 2.0, -0.5, 1.5])
    assert 0 <= iid_bootstrap_prob_positive(x, 200, 1) <= 1
    assert 0 <= moving_block_bootstrap_prob_positive(x, 200, 2, 2) <= 1


def test_cpcv_workflow_exists():
    workflow = Path(".github/workflows/strategy-cpcv-gated.yml").read_text(encoding="utf-8")
    assert "strategy-regime-lab-v2" in workflow
    assert "--cost-per-contract 2" in workflow
    assert "--n-groups 6" in workflow
