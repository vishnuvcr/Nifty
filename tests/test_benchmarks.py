import numpy as np
from nifty_mc.benchmarks import historical_bootstrap_terminal


def test_bootstrap_shape():
    returns = np.resize(np.array([.01, -.01, .0, .005]), 30)
    out = historical_bootstrap_terminal(100, returns, 3, n_paths=100, seed=1)
    assert out.shape == (100,)
    assert np.all(out > 0)
