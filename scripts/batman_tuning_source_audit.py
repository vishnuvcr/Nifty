#!/usr/bin/env python3
"""Inspect acquired BATMAN raw archives without full extraction."""
from __future__ import annotations
import csv, json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/".cache"/"batman_raw"
OUT=ROOT/"data"/"batman_tuning_cache"/"source_audit.json"
FILES=["zenodo_nifty_options_2017_2020.zip","zenodo_nifty_spot_futures_2017_2020.zip","ayush_nifty_banknifty_options_2020_2024.zip","rahul_nifty_options_2025_2026.zip"]
def sample_csv_header(zf,name):
    with zf.open(name) as fh:
        text=fh.read(8192).decode("utf-8-sig",errors="replace")
    line=text.splitlines()[0] if text.splitlines() else ""
    try: return next(csv.reader([line]))
    except Exception: return [line]
def audit_one(path):
    rec={"archive":path.name,"bytes":path.stat().st_size}
    with zipfile.ZipFile(path) as zf:
        infos=[i for i in zf.infolist() if not i.is_dir()]
        rec["member_count"]=len(infos)
        rec["total_uncompressed_bytes"]=sum(i.file_size for i in infos)
        ext={}
        for i in infos:
            e=Path(i.filename).suffix.lower() or "<none>"
            ext[e]=ext.get(e,0)+1
        rec["extensions"]=ext
        rec["members_sample"]=[{"name":i.filename,"bytes":i.file_size} for i in infos[:20]]
        rec["csv_samples"]=[{"member":n,"header":sample_csv_header(zf,n)} for n in [i.filename for i in infos if Path(i.filename).suffix.lower()==".csv"][:5]]
    return rec
missing=[n for n in FILES if not (RAW/n).exists()]
if missing:
    print("SOURCE_AUDIT_MISSING")
    for n in missing: print(n)
    raise SystemExit(2)
OUT.parent.mkdir(parents=True,exist_ok=True)
report={"schema_version":"BATMAN-T1-SOURCE-AUDIT-1","archives":[audit_one(RAW/n) for n in FILES]}
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
