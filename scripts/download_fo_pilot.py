from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import zipfile
import requests
import pandas as pd

from nifty_mc.nse_ingest import normalize_option_csv

def candidate_urls(dt: pd.Timestamp) -> list[str]:
    d=dt.strftime("%d"); m=dt.strftime("%b").upper(); y=dt.strftime("%Y"); ymd=dt.strftime("%Y%m%d")
    legacy=f"fo{d}{m}{y}bhav.csv.zip"
    udiff=f"BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
    return [
        f"https://nsearchives.nseindia.com/content/fo/{udiff}",
        f"https://archives.nseindia.com/content/fo/{udiff}",
        f"https://archives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/{legacy}",
        f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/{legacy}",
    ]

def fetch_one(dt: pd.Timestamp, timeout=30):
    headers={"User-Agent":"Mozilla/5.0","Accept":"text/csv,application/zip,*/*"}
    last=None
    for url in candidate_urls(dt):
        try:
            r=requests.get(url,headers=headers,timeout=timeout)
            if r.status_code==200 and len(r.content)>100:
                z=zipfile.ZipFile(BytesIO(r.content))
                name=z.namelist()[0]
                raw=BytesIO(z.read(name))
                raw_path=Path("/tmp")/name
                raw_path.write_bytes(raw.getvalue())
                df=normalize_option_csv(raw_path)
                return url, name, df
            last=f"{r.status_code} {url}"
        except Exception as e:
            last=f"{type(e).__name__}: {e}"
    raise RuntimeError(last or "all candidates failed")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dates",nargs="+",required=True)
    ap.add_argument("--out",default="data/options_pilot.csv")
    args=ap.parse_args()
    out=[]
    manifests=[]
    for s in args.dates:
        dt=pd.Timestamp(s).normalize()
        try:
            url,name,df=fetch_one(dt)
            x=df.copy()
            x["source_trade_date"]=dt
            out.append(x)
            manifests.append({"trade_date":dt,"status":"ok","source_url":url,"archive_name":name,"rows":len(x)})
            print(dt.date(), "OK", len(x), url)
        except Exception as e:
            manifests.append({"trade_date":dt,"status":"failed","error":str(e)})
            print(dt.date(), "FAILED", e)
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    pd.concat(out,ignore_index=True).to_csv(args.out,index=False) if out else pd.DataFrame().to_csv(args.out,index=False)
    pd.DataFrame(manifests).to_csv(Path(args.out).with_name("options_pilot_manifest.csv"),index=False)
    good=sum(m["status"]=="ok" for m in manifests)
    if good < len(manifests):
        raise SystemExit(f"{good}/{len(manifests)} dates acquired")

if __name__=="__main__":
    main()
