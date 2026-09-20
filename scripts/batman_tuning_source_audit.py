#!/usr/bin/env python3
"""Inspect acquired BATMAN raw archives without full extraction."""
from __future__ import annotations
import csv, io, json, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/".cache"/"batman_raw"
OUT=ROOT/"data"/"batman_tuning_cache"/"source_audit.json"
FILES=["zenodo_nifty_options_2017_2020.zip","zenodo_nifty_spot_futures_2017_2020.zip","ayush_nifty_banknifty_options_2020_2024.zip","rahul_nifty_options_2025_2026.zip","nifty_index_2008_2020.zip"]

def sample_csv_header(zf,name):
    with zf.open(name) as fh:
        text=fh.read(8192).decode("utf-8-sig",errors="replace")
    line=text.splitlines()[0] if text.splitlines() else ""
    try: return next(csv.reader([line]))
    except Exception: return [line]

def choose_csv_members(names,include=(),exclude=()):
    out=[]
    for n in names:
        low=n.lower()
        if not low.endswith(".csv"): continue
        if any(k not in low for k in include): continue
        if any(k in low for k in exclude): continue
        out.append(n)
    return out[:5]

def inspect_outer(path):
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
        names=[i.filename for i in infos]
        if path.name.startswith("ayush_"):
            chosen=choose_csv_members(names,include=("nifty",),exclude=("banknifty","_fut","spot"))
        elif path.name.startswith("rahul_"):
            chosen=[n for n in names if n.lower().endswith(".csv")][:5]
        else:
            chosen=[]
        rec["targeted_members"]=chosen
        rec["csv_samples"]=[{"member":n,"header":sample_csv_header(zf,n)} for n in chosen]
        rec["members_sample"]=[{"name":i.filename,"bytes":i.file_size} for i in infos[:20]]
        if path.name.startswith("nifty_index_"):
            rec["index_targeted_members"]=[n for n in names if n.lower().startswith("nifty_data/") and n.lower().endswith(".csv")]
        if path.name.startswith("zenodo_"):
            nested=[n for n in names if n.lower().endswith(".zip")]
            rec["nested_archives"]=[]
            for n in nested:
                rec["nested_archives"].append({"name":n,"bytes":zf.getinfo(n).file_size})
                if len(rec["nested_archives"])>=4: break
            # Probe the first nested yearly ZIP without extracting the full outer archive.
            if nested:
                with zf.open(nested[0]) as src:
                    payload=src.read()
                with zipfile.ZipFile(io.BytesIO(payload)) as nz:
                    ninfos=[i for i in nz.infolist() if not i.is_dir()]
                    rec["nested_probe"]={
                        "archive":nested[0],
                        "member_count":len(ninfos),
                        "extensions":sorted({Path(i.filename).suffix.lower() for i in ninfos}),
                        "members_sample":[{"name":i.filename,"bytes":i.file_size} for i in ninfos[:20]]
                    }
    return rec

missing=[n for n in FILES if not (RAW/n).exists()]
if missing:
    print("SOURCE_AUDIT_MISSING")
    for n in missing: print(n)
    raise SystemExit(2)

OUT.parent.mkdir(parents=True,exist_ok=True)
report={"schema_version":"BATMAN-T1-SOURCE-AUDIT-2","archives":[inspect_outer(RAW/n) for n in FILES]}
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
