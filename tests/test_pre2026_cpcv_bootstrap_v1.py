import numpy as np
import pandas as pd
from scripts.run_pre2026_cpcv_bootstrap_v1 import add_vol_regime, block_bootstrap, mean_se, pf, trailing_rank
def test_rank_is_past_only():
    r=trailing_rank(pd.Series([1.,2.,3.,4.]),3)
    assert np.isnan(r[0]); assert r[1]==1.0
def test_decision_level_regime():
    rows=[]
    for i in range(40):
        for s in ["A","B","C"]:
            rows.append({"decision_id":str(i),"decision_date":pd.Timestamp("2020-01-01")+pd.Timedelta(days=i),"strategy":s,"rv20":float(i)})
    out=add_vol_regime(pd.DataFrame(rows),30,1/3,2/3)
    u=out.groupby("decision_id")[["rv20_rank","vol_regime"]].nunique(dropna=False)
    assert (u==1).all().all()
def test_mean_se_and_pf():
    m,se,score=mean_se(np.array([10.,0.,-5.]))
    assert round(m,8)==round(5/3,8)
    assert score < m
    assert pf(np.array([10.,-5.,5.]))==3.0
def test_bootstrap_is_finite():
    r=block_bootstrap(np.arange(20,dtype=float),3,200,1)
    assert np.isfinite(r["ci_low"]) and np.isfinite(r["ci_high"])
