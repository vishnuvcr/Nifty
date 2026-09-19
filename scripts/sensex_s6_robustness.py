from __future__ import annotations
import argparse, glob, json
from pathlib import Path
import numpy as np
import pandas as pd

def load_summaries(root: Path, kind: str) -> pd.DataFrame:
    pat = str(root / ("slippage_*" if kind=="slippage" else "seed_*") / "summary_*.json")
    rows=[]
    for p in sorted(glob.glob(pat)):
        d=json.loads(Path(p).read_text(encoding="utf-8"))
        scen=Path(p).parent.name
        row={"scenario":scen,"split":d["split"],"slippage_points_per_leg":float(d["slippage_points_per_leg"])}
        for s in ("adaptive","batman"):
            row[f"{s}_trades"]=int(d[s].get("trades",0))
            row[f"{s}_total_pnl"]=float(d[s].get("total_pnl",0.0))
            row[f"{s}_mean_pnl"]=float(d[s].get("mean_pnl",0.0))
            row[f"{s}_win_rate"]=float(d[s].get("win_rate",np.nan))
            row[f"{s}_profit_factor"]=float(d[s].get("profit_factor",np.nan))
            row[f"{s}_max_drawdown"]=float(d[s].get("max_drawdown",np.nan))
        if kind=="seed": row["seed"]=int(scen.split("_")[1])
        rows.append(row)
    return pd.DataFrame(rows)

def combined_trades(root: Path, prefix: str) -> pd.DataFrame:
    frames=[]
    for split in ("validation","holdout"):
        p=root/"slippage_0.50"/f"{prefix}_trades_{split}.csv"
        if p.exists():
            x=pd.read_csv(p)
            if "status" in x: x=x.loc[x["status"].eq("CLOSED")].copy()
            if not x.empty:
                x["split"]=split
                frames.append(x)
    if not frames: return pd.DataFrame()
    x=pd.concat(frames,ignore_index=True)
    for c in ("entry_date","expiry"):
        if c in x: x[c]=pd.to_datetime(x[c],errors="coerce")
    cols=[c for c in ("entry_date","expiry") if c in x]
    return x.sort_values(cols).reset_index(drop=True) if cols else x

def circular_block_bootstrap(values, block_len=3, reps=10000, seed=87654321):
    v=np.asarray(values,dtype=float); v=v[np.isfinite(v)]; n=len(v)
    if n < max(6,2*block_len):
        return {"n":int(n),"block_length":block_len,"reps":0,"mean":float(v.mean()) if n else None,"ci_low":None,"ci_high":None,"p_mean_gt_zero":None}
    rng=np.random.default_rng(seed); out=np.empty(reps); starts=np.arange(n); blocks=int(np.ceil(n/block_len))
    for i in range(reps):
        idx=[]
        for _ in range(blocks):
            s=int(rng.choice(starts)); idx.extend(((s+np.arange(block_len))%n).tolist())
        out[i]=np.mean(v[idx[:n]])
    return {"n":n,"block_length":block_len,"reps":reps,"mean":float(v.mean()),
            "ci_low":float(np.quantile(out,.025)),"ci_high":float(np.quantile(out,.975)),
            "p_mean_gt_zero":float(np.mean(out>0)),"median_bootstrap_mean":float(np.median(out))}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--reports-dir",required=True); ap.add_argument("--out-dir",required=True)
    a=ap.parse_args(); root=Path(a.reports_dir); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    slip=load_summaries(root,"slippage"); seed=load_summaries(root,"seed")
    slip.to_csv(out/"S6_SLIPPAGE_SUMMARY.csv",index=False); seed.to_csv(out/"S6_SEED_SUMMARY.csv",index=False)

    boot_rows=[]; boot_details={}
    for name,prefix in (("Adaptive","adaptive"),("Batman","batman")):
        t=combined_trades(root,prefix)
        if t.empty or "realized_pnl_inr" not in t:
            boot_details[name]={"status":"no_closed_trades"}; continue
        vals=pd.to_numeric(t["realized_pnl_inr"],errors="coerce").dropna().to_numpy(float)
        res=circular_block_bootstrap(vals,3,10000,87654321+len(vals)); boot_details[name]=res
        boot_rows.append({"strategy":name,"n_validation_holdout_trades":len(vals),"observed_mean_pnl":float(vals.mean()),
                          "observed_total_pnl":float(vals.sum()),"bootstrap_ci_low_mean_pnl":res["ci_low"],
                          "bootstrap_ci_high_mean_pnl":res["ci_high"],"bootstrap_p_mean_gt_zero":res["p_mean_gt_zero"]})
    boot=pd.DataFrame(boot_rows); boot.to_csv(out/"S6_BLOCK_BOOTSTRAP.csv",index=False)
    meta={"phase":"S6","one_lot_edge_mode":True,"slippage_grid":[.25,.50,1.00,2.00],"seed_grid":[101,202,303,404,505],
          "seed_sensitivity_scope":["validation","holdout"],"bootstrap":{"method":"circular moving-block","block_length_trades":3,"repetitions":10000,"scope":"validation + holdout, 0.50 slippage"},
          "quote_data_limitation":"Historical archive contains OHLCV/OI, not point-in-time bid/ask; slippage is a stress test, not direct spread reconstruction.",
          "results":boot_details}
    (out/"S6_ROBUSTNESS_SUMMARY.json").write_text(json.dumps(meta,indent=2,default=str),encoding="utf-8")

    md=["# SENSEX S6 Robustness Results","","Frozen Batman/Adaptive rules; one-lot transfer-edge mode; no SENSEX retuning.",""]
    if not slip.empty: md += ["## Slippage sensitivity","",slip.to_markdown(index=False),""]
    if not seed.empty:
        agg=seed.groupby("split").agg(
            adaptive_total_mean=("adaptive_total_pnl","mean"),adaptive_total_min=("adaptive_total_pnl","min"),adaptive_total_max=("adaptive_total_pnl","max"),
            adaptive_positive_seed_fraction=("adaptive_total_pnl",lambda s:float((s>0).mean())),
            batman_total_mean=("batman_total_pnl","mean"),batman_total_min=("batman_total_pnl","min"),batman_total_max=("batman_total_pnl","max"),
            batman_positive_seed_fraction=("batman_total_pnl",lambda s:float((s>0).mean()))).reset_index()
        md += ["## Seed sensitivity (0.50-point slippage)","",agg.to_markdown(index=False),""]
    md += ["## Dependence-aware bootstrap","",boot.to_markdown(index=False),"",
           "## Controls","",
           "- Slippage grid is a predeclared stress analysis, not a preferred-cost selection.",
           "- Seed sensitivity measures Monte Carlo path/strike instability without changing the frozen candidate universe.",
           "- Block bootstrap is descriptive uncertainty, not a guarantee of future performance.",
           "- No historical bid/ask snapshots were available; quote-source sensitivity is therefore not claimed.",
           "- One-lot edge results do not establish deployability for a ₹100,000 account."]
    (out/"S6_ROBUSTNESS_RESULTS.md").write_text("\n".join(md)+"\n",encoding="utf-8")
if __name__=="__main__": main()
