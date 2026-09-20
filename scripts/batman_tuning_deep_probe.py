#!/usr/bin/env python3
from __future__ import annotations
import csv, io, json, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/".cache"/"batman_raw"
OUT=ROOT/"data"/"batman_tuning_cache"/"deep_probe.json"

def csv_rows_from_bytes(data, n=8):
    text=data.decode("utf-8-sig", errors="replace")
    reader=csv.reader(io.StringIO(text))
    rows=[]
    for row in reader:
        rows.append(row)
        if len(rows)>=n+1:
            break
    return rows

def probe_plain(zpath, member):
    with zipfile.ZipFile(zpath) as zf:
        with zf.open(member) as fh:
            return csv_rows_from_bytes(fh.read(256*1024), 8)

def probe_nested(zpath, outer_member_contains, inner_member_contains=None):
    with zipfile.ZipFile(zpath) as outer:
        outer_names=[n for n in outer.namelist() if n.lower().endswith(".zip")]
        outer_pick=next(n for n in outer_names if outer_member_contains.lower() in n.lower())
        with outer.open(outer_pick) as fh:
            outer_bytes=fh.read()
    with zipfile.ZipFile(io.BytesIO(outer_bytes)) as inner:
        names=[n for n in inner.namelist() if not n.endswith("/")]
        if inner_member_contains:
            names2=[n for n in names if inner_member_contains.lower() in n.lower()]
            pick=names2[0] if names2 else names[0]
        else:
            pick=names[0]
        with inner.open(pick) as fh:
            rows=csv_rows_from_bytes(fh.read(512*1024), 8)
        return {"outer_member":outer_pick,"inner_member":pick,"rows":rows}

def main():
    out={}
    ayush=RAW/"ayush_nifty_banknifty_options_2020_2024.zip"
    with zipfile.ZipFile(ayush) as zf:
        member="nifty_data/nifty_options/2020/1/nifty_options_01_01_2020.csv"
        out["ayush_option"]= {"member":member,"rows":probe_plain(ayush,member)}
    rahul=RAW/"rahul_nifty_options_2025_2026.zip"
    with zipfile.ZipFile(rahul) as zf:
        member=zf.namelist()[0]
        with zf.open(member) as fh:
            out["rahul_option"]={"member":member,"rows":csv_rows_from_bytes(fh.read(512*1024),8)}
    idx=RAW/"nifty_index_2008_2020.zip"
    with zipfile.ZipFile(idx) as zf:
        member="NIFTY_data/NIFTY_2008_2020.csv"
        out["long_nifty_index"]={"member":member,"rows":probe_plain(idx,member)}
    zopts=RAW/"zenodo_nifty_options_2017_2020.zip"
    out["zenodo_option_nested"]=probe_nested(zopts,"NiftyOptions 2020.zip")
    zspot=RAW/"zenodo_nifty_spot_futures_2017_2020.zip"
    out["zenodo_spot_nested"]=probe_nested(zspot,"2020.zip", "NIFTY.csv")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
