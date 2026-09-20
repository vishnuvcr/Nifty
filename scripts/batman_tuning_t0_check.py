from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
cfg = json.loads((root / "configs" / "batman_tuning_v1.json").read_text())

assert cfg["study"] == "BATMAN_TUNING_V1"
assert cfg["branch"] == "research/batman-tuning-v1"
assert cfg["control"]["entry_offset_sessions"] == 3
assert cfg["control"]["signal_time_ist"] == "09:30"
assert cfg["control"]["lookback_sessions"] == 756
assert cfg["control"]["mc_paths"] == 5000
assert cfg["entry_offsets"] == [0, 1, 2, 3, 4, 5, 6]
assert cfg["timings"] == [
    "prior_session_evening_to_open",
    "same_session_09_30",
]
assert cfg["status"] == "T0_COMPLETE"

print("BATMAN TUNING T0 protocol checks passed.")
