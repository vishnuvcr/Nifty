import pandas as pd

from nifty_mc.option_validation import nearest_actual_expiry, validate_condor_chain


def _chain():
    return pd.DataFrame([
        {"timestamp":"2025-05-09", "expiry":"2025-05-12", "strike":24500, "option_type":"PE", "symbol":"NIFTY", "close":10},
        {"timestamp":"2025-05-09", "expiry":"2025-05-12", "strike":24600, "option_type":"PE", "symbol":"NIFTY", "close":20},
        {"timestamp":"2025-05-09", "expiry":"2025-05-12", "strike":25000, "option_type":"CE", "symbol":"NIFTY", "close":25},
        {"timestamp":"2025-05-09", "expiry":"2025-05-12", "strike":25100, "option_type":"CE", "symbol":"NIFTY", "close":12},
        {"timestamp":"2025-05-09", "expiry":"2025-05-19", "strike":25000, "option_type":"CE", "symbol":"NIFTY", "close":30},
    ])


def test_nearest_actual_expiry_prefers_present_target():
    chain = _chain()
    assert nearest_actual_expiry(chain, "2025-05-09", "2025-05-12") == pd.Timestamp("2025-05-12")


def test_nearest_actual_expiry_falls_back_when_target_absent():
    chain = _chain()
    assert nearest_actual_expiry(chain, "2025-05-09", "2025-05-13") == pd.Timestamp("2025-05-12")


def test_validate_four_legs():
    result = validate_condor_chain(_chain(), "2025-05-12", (24500, 24600, 25000, 25100))
    assert result["valid"] is True
    assert result["missing_legs"] == []


def test_validate_reports_missing_leg():
    result = validate_condor_chain(_chain(), "2025-05-12", (24500, 24600, 24900, 25100))
    assert result["valid"] is False
    assert (24900.0, "CE") in result["missing_legs"]
