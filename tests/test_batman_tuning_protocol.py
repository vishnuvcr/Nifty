import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_control_is_frozen():
    cfg = json.loads((ROOT / "configs" / "batman_tuning_v1.json").read_text())
    assert cfg["control"]["entry_offset_sessions"] == 3
    assert cfg["control"]["signal_time_ist"] == "09:30"
    assert cfg["control"]["lookback_sessions"] == 756
    assert cfg["control"]["mc_paths"] == 5000

def test_entry_grid_is_preregistered():
    cfg = json.loads((ROOT / "configs" / "batman_tuning_v1.json").read_text())
    assert cfg["entry_offsets"] == [0, 1, 2, 3, 4, 5, 6]
    assert "prior_session_evening_to_open" in cfg["timings"]
    assert "same_session_09_30" in cfg["timings"]
