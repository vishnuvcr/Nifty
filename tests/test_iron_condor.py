import numpy as np
from nifty_mc.iron_condor import long_iron_condor_profit

def test_flat_zone():
    assert long_iron_condor_profit(np.array([150.0]),80,100,200,220,5.0)[0] == -5.0

def test_downside_cap():
    assert long_iron_condor_profit(np.array([50.0]),80,100,200,220,5.0)[0] == 15.0

def test_upside_cap():
    assert long_iron_condor_profit(np.array([250.0]),80,100,200,220,5.0)[0] == 15.0
