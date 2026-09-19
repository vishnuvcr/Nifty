from pathlib import Path

import numpy as np
import pandas as pd

from scripts.run_regime_strategy_router_v3 import classify_adaptive, summarize


def test_adaptive_classifier_uses_past_only_ranks():
    d = pd.DataFrame({
        'decision_date': pd.date_range('2020-01-01', periods=40, freq='D'),
        'trend20': np.arange(40, dtype=float),
        'trend60': np.arange(40, dtype=float),
        'rv20': np.arange(40, dtype=float),
        'p_expand': np.arange(40, dtype=float),
    })
    out = classify_adaptive(d)
    assert pd.isna(out.loc[0, 'trend20_rank'])
    assert out.loc[35, 'trend20_rank'] >= 0
    assert 'vol_regime' in out.columns
    assert 'direction_adaptive' in out.columns


def test_summary_reports_drawdown():
    s = summarize(np.array([10.0, -5.0, 8.0, -20.0]))
    assert s['n'] == 4
    assert s['total'] == -7.0
    assert s['max_drawdown'] < 0


def test_router_workflow_exists():
    wf = Path('.github/workflows/adaptive-regime-strategy-router.yml').read_text(encoding='utf-8')
    assert '--dev-min-n 30' in wf
    assert '--validation-min-n 10' in wf
    assert 'strategy-regime-lab-v2' in wf