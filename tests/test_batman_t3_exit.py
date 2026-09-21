import pandas as pd

from scripts.batman_t3_exit import trigger_exit, rule_candidates


def test_combined_trailing_target_uses_retracement_parameter():
    family, activation, stop, retracement = ("trailing_target_stop", 0.30, 0.75, 0.10)
    # At +25% of max profit, the target is activated only after +30%, so no exit yet.
    assert trigger_exit(family, 0.25, 100.0, 50.0, activation, stop, retracement) is None
    assert any(
        fam == "trailing_target_stop" and a == 0.30 and b == 0.75 and r == 0.10
        for fam, a, b, r in rule_candidates()
    )


def test_fixed_target_and_stop_trigger_at_declared_thresholds():
    assert trigger_exit("fixed_target", 10.0, 100.0, 50.0, 0.10, None, None) == "fixed_target"
    assert trigger_exit("fixed_stop", -50.0, 100.0, 50.0, None, 1.00, None) == "fixed_stop"
    assert trigger_exit("fixed_target_stop", -50.0, 100.0, 50.0, 0.20, 1.00, None) == "fixed_stop"


def test_rule_grid_counts_are_predeclared():
    candidates = list(rule_candidates())
    assert len(candidates) == 1 + 7 + 7 + 49 + 5 + 12 + 84
