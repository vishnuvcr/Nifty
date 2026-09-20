#!/usr/bin/env python3
from __future__ import annotations
import csv, io, json, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/".cache"/"batman_raw"
OUT=ROOT/"data"/"batman_tuning_cache"/"deep_probe.json"
PROBE_VERSION="2"

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

def probe_nested_until_csv(zpath, outer_member_contains):
    with zipfile.ZipFile(zpath) as outer:
        outer_names=[n for n in outer.namelist() if n.lower().endswith(".zip")]
        outer_pick=next(n for n in outer_names if outer_member_contains.lower() in n.lower())
        payload=outer.read(outer_pick)
    chain=[outer_pick]
    while True:
        try:
            zf = zipfile.ZipFile(io.BytesIO(payload))
        except zipfile.BadZipFile:
            return {"chain":chain,"error":"nested payload is not a readable ZIP at this level"}
        with zf:
            names=[n for n in zf.namelist() if not n.endswith("/")]
            csvs=[n for n in names if n.lower().endswith(".csv")]
            if csvs:
                pick=csvs[0]
                with zf.open(pick) as fh:
                    return {"chain":chain,"csv_member":pick,"rows":csv_rows_from_bytes(fh.read(512*1024),8)}
            zips=[n for n in names if n.lower().endswith(".zip")]
            if not zips:
                return {"chain":chain,"error":"no CSV or ZIP member at nested level"}
            pick=zips[0]
            payload=zf.read(pick)
            chain.append(pick)

def main():
    out={}
    ayush=RAW/"ayush_nifty_banknifty_options_2020_2024.zip"
    with zipfile.ZipFile(ayush) as zf:
        opt_member="nifty_data/nifty_options/2020/1/nifty_options_01_01_2020.csv"
        spot_candidates=[n for n in zf.namelist() if n.lower().startswith("nifty_data/nifty_spot/2020/1/") and n.lower().endswith(".csv")]
        spot_member=next((n for n in spot_candidates if "01_01_2020" in n), spot_candidates[0] if spot_candidates else None)
        out["ayush_option"]={"member":opt_member,"rows":probe_plain(ayush,opt_member)}
        if spot_member:
            out["ayush_spot"]={"member":spot_member,"rows":probe_plain(ayush,spot_member)}
        else:
            out["ayush_spot"]={"member":None,"rows":[]}
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
    out["zenodo_option_nested"]=probe_nested_until_csv(zopts,"NiftyOptions 2020.zip")
    zspot=RAW/"zenodo_nifty_spot_futures_2017_2020.zip"
    out["zenodo_spot_nested"]=probe_nested_until_csv(zspot,"2020.zip")
    out["probe_version"]=PROBE_VERSION
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
