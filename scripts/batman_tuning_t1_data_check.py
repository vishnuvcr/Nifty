#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "batman_tuning_cache"
REQUIRED = ["manifest.json", "sessions.parquet", "option_quotes.parquet", "intraday_underlying.parquet"]
def main() -> int:
    missing = [name for name in REQUIRED if not (CACHE / name).exists()]
    if missing:
        print("T1_DATA_UNAVAILABLE")
        for name in missing: print(f"- {name}")
        print("No historical tuning computation is permitted.")
        return 2
    try: manifest = json.loads((CACHE / "manifest.json").read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"T1_MANIFEST_INVALID: {exc}"); return 3
    required_keys = {"schema_version","coverage_start","coverage_end","source","sha256"}
    absent = sorted(required_keys - set(manifest))
    if absent:
        print("T1_MANIFEST_INCOMPLETE"); print("Missing keys:", ", ".join(absent)); return 4
    print("T1_DATA_CACHE_PRESENT"); print(json.dumps(manifest, indent=2, sort_keys=True)); return 0
if __name__ == "__main__": sys.exit(main())
