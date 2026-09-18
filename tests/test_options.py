import pandas as pd
from nifty_mc.options import four_leg_debit

def test_executable_debit():
    c = pd.DataFrame([
        [100,"PE",2.0,2.2],[110,"PE",5.0,5.2],
        [130,"CE",4.0,4.2],[140,"CE",1.0,1.2]
    ], columns=["strike","option_type","bid","ask"])
    d = four_leg_debit(c,100,110,130,140)
    assert d == 5.2 + 4.2 - 2.0 - 1.0
