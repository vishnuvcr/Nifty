from scripts.run_limited_risk_wfo import risk_audit, stable_seed, contract_count

def test_batman_unbounded_loss():
    r=risk_audit("Batman")
    assert r["loss_unbounded"] is True
    assert r["core_limited_risk"] is False

def test_short_iron_condor_defined_risk():
    r=risk_audit("Short Iron Condor")
    assert r["loss_unbounded"] is False
    assert r["core_limited_risk"] is True

def test_double_plateau_detected_as_defined_risk():
    r=risk_audit("Double Plateau")
    assert r["loss_unbounded"] is False
    assert r["core_limited_risk"] is True

def test_put_ratio_backspread_has_finite_loss():
    r=risk_audit("Put Ratio Back Spread")
    assert r["loss_unbounded"] is False
    assert r["core_limited_risk"] is True

def test_stable_seed():
    assert stable_seed("A")==stable_seed("A")

def test_contract_count():
    assert contract_count("Batman")==6
    assert contract_count("Short Iron Condor")==4
