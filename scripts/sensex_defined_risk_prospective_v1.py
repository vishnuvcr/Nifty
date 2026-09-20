from __future__ import annotations
import argparse, html, json, math
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.sensex_paper_signal_producer_v1 import (
    fetch_index_history,
    fetch_live_sensex,
    extract_live_spot_and_date,
    third_future_weekday,
    fetch_option_chain,
    quote_for_leg,
    now_ist,
)
from scripts.sensex_backtest_v1 import mc_terminal, map_unique_strikes, transaction_costs, realized_costs
from nifty_mc.strategy_catalog import build_strategy

STRATEGIES=["Jade Lizard","Put Ratio Spread"]
LOT_SIZE=20
MC_PATHS=5000
LOOKBACK=756
SLIPPAGE_POINTS=0.50
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"paper_trading/prospective_defined_risk/sensex"

SIGNAL_COLS=["signal_id","run_timestamp_ist","decision_date","expiry","strategy","status","signal","spot","mc_paths","lookback_sessions",
             "model_data_cutoff","quote_retrieved_at_ist","mc_ev_points_net","mc_pop","es95_points","es99_points","risk_points_per_lot",
             "entry_cost_inr_expected","entry_cost_inr_entry_only","strikes_json","legs_json","notes"]
LEDGER_COLS=["signal_id","decision_date","expiry","strategy","status","signal","spot","lot_size","lots","mc_ev_points_net","mc_pop","risk_points_per_lot",
             "entry_cashflow_points_per_unit","entry_cost_inr","legs_json","model_data_cutoff","entry_timestamp_ist","exit_date","exit_spot",
             "realized_pnl_points_per_unit","realized_pnl_inr","notes"]

def target_map(strategy,terminal,spot):
    q10,q35,q65,q90=np.percentile(terminal,[10,35,65,90])
    d={"p10":float(q10),"p35":float(q35),"c65":float(q65),"c90":float(q90),"atm":float(spot)}
    needed={"Jade Lizard":["p35","c65","c90"],"Put Ratio Spread":["atm","p35"],"Sell Put":["atm"],"Bull Put Spread":["p35","p10"]}
    return {k:d[k] for k in needed[strategy]}

def load_csv(path,cols):
    return pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame(columns=cols)

def evaluate(strategy,terminal,spot,chain,expiry,decision):
    strikes=map_unique_strikes(chain,target_map(strategy,terminal,spot))
    legs=build_strategy(strategy,strikes)
    priced=[]
    entry_cashflow=0.0
    for leg in legs:
        side="BUY" if leg.qty>0 else "SELL"
        px=quote_for_leg(chain,leg.option_type,float(leg.strike),side)
        entry_cashflow-=float(leg.qty)*px
        row=chain.loc[chain.option_type.eq(leg.option_type)&np.isclose(chain.strike.to_numpy(float),float(leg.strike),atol=1e-9)].iloc[0]
        priced.append({"side":side,"option_type":leg.option_type,"strike":float(leg.strike),"qty":int(leg.qty),
                       "quantity_per_lot":abs(int(leg.qty)),"premium_points":float(px),"bid":float(row.bid),"ask":float(row.ask),
                       "expiry":str(expiry.date())})
    expected_cost,entry_only_cost=transaction_costs(decision,priced,LOT_SIZE,entry_cashflow,terminal)
    gross=np.full(len(terminal),entry_cashflow)
    for leg in priced:
        intrinsic=np.maximum(terminal-leg["strike"],0.0) if leg["option_type"]=="CE" else np.maximum(leg["strike"]-terminal,0.0)
        gross += float(leg["qty"])*intrinsic
    net=gross-(expected_cost/LOT_SIZE)
    q05=float(np.quantile(net,.05)); q01=float(np.quantile(net,.01))
    es95=max(0.0,-float(np.mean(net[net<=q05])))
    es99=max(0.0,-float(np.mean(net[net<=q01])))
    return {"strikes":strikes,"legs":priced,"entry_cashflow":float(entry_cashflow),
            "mc_ev_points_net":float(np.mean(net)),"mc_pop":float(np.mean(net>0)),
            "es95_points":es95,"es99_points":es99,"risk_points_per_lot":max(es95,es99),
            "entry_cost_inr_expected":float(expected_cost),"entry_cost_inr_entry_only":float(entry_only_cost),
            "signal":"ENTER" if np.mean(net)>0 else "NO_TRADE"}

def settle(index_df,ledger):
    if ledger.empty:return ledger
    close_map=dict(zip(pd.to_datetime(index_df.date).dt.normalize(),pd.to_numeric(index_df.close,errors="coerce")))
    for idx in ledger.index[ledger.status.eq("OPEN")]:
        expiry=pd.Timestamp(ledger.at[idx,"expiry"]).normalize()
        if expiry not in close_map:continue
        spot=float(close_map[expiry])
        pnl=float(ledger.at[idx,"entry_cashflow_points_per_unit"])
        for leg in json.loads(str(ledger.at[idx,"legs_json"])):
            k=float(leg["strike"]); q=int(leg["qty"])
            pnl += q*(max(spot-k,0.0) if leg["option_type"]=="CE" else max(k-spot,0.0))
        legs=json.loads(str(ledger.at[idx,"legs_json"]))
        costs=realized_costs(pd.Timestamp(ledger.at[idx,"decision_date"]),legs,LOT_SIZE,spot)
        realized_inr=pnl*LOT_SIZE*int(ledger.at[idx,"lots"] or 1)-costs*int(ledger.at[idx,"lots"] or 1)
        ledger.at[idx,"status"]="CLOSED"; ledger.at[idx,"exit_date"]=expiry.date().isoformat(); ledger.at[idx,"exit_spot"]=spot
        ledger.at[idx,"realized_pnl_points_per_unit"]=pnl; ledger.at[idx,"realized_pnl_inr"]=realized_inr
    return ledger

def page(strategy,signals,ledger,site_dir):
    site_dir.mkdir(parents=True,exist_ok=True)
    closed=ledger[ledger.status.eq("CLOSED")].copy(); pnl=pd.to_numeric(closed.realized_pnl_inr,errors="coerce").dropna()
    total=float(pnl.sum()) if len(pnl) else 0.0; win=float((pnl>0).mean()) if len(pnl) else float("nan")
    gains=float(pnl[pnl>0].sum()) if len(pnl) else 0.0; losses=float(-pnl[pnl<0].sum()) if len(pnl) else 0.0
    pf=gains/losses if losses else float("inf"); eq=pnl.cumsum() if len(pnl) else pd.Series(dtype=float)
    dd=float((eq-eq.cummax()).min()) if len(eq) else 0.0
    latest=signals.tail(1).iloc[0].to_dict() if len(signals) else {"signal":"NO_TRADE","decision_date":"—","strategy":strategy}
    def obs_row(r):
        ev="" if pd.isna(r.mc_ev_points_net) else f"{float(r.mc_ev_points_net):.2f}"
        pnl="" if pd.isna(r.realized_pnl_inr) else f"₹{float(r.realized_pnl_inr):,.2f}"
        return f"<tr><td>{html.escape(str(r.signal_id))}</td><td>{html.escape(str(r.expiry))}</td><td>{html.escape(str(r.status))}</td><td>{html.escape(str(r.signal))}</td><td>{ev}</td><td>{pnl}</td></tr>"
    rows="".join(obs_row(r) for _,r in signals.tail(25).iloc[::-1].iterrows())
    (site_dir/"index.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>SENSEX {html.escape(strategy)}</title><style>body{{font-family:Arial;background:#0d1117;color:#e6edf3;max-width:1200px;margin:auto;padding:24px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:14px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}.kpi{{font-size:24px;font-weight:700}}table{{width:100%;border-collapse:collapse}}th,td{{padding:7px;border-bottom:1px solid #30363d;text-align:left}}a{{color:#58a6ff}}</style></head><body><h1>SENSEX — {html.escape(strategy)}</h1><p>Frozen prospective validation • 09:30 IST • third future weekday expiry • 5,000 MC paths • 756-session lookback.</p><div class="card"><h2>Latest observation</h2><div class="grid"><div><small>Signal</small><div class="kpi">{html.escape(str(latest.get("signal","NO_TRADE")))}</div></div><div><small>Decision</small><div class="kpi">{html.escape(str(latest.get("decision_date","—")))}</div></div><div><small>Expiry</small><div class="kpi">{html.escape(str(latest.get("expiry","—")))}</div></div><div><small>Spot</small><div class="kpi">{float(latest.get("spot",0) or 0):.2f}</div></div><div><small>Net MC EV</small><div class="kpi">{'' if pd.isna(latest.get("mc_ev_points_net")) else f'{float(latest.get("mc_ev_points_net")):.2f}'}</div></div></div></div><div class="card"><h2>Prospective ledger</h2><div class="grid"><div><small>Closed trades</small><div class="kpi">{len(closed)}</div></div><div><small>Win rate</small><div class="kpi">{"—" if not len(pnl) else f"{win:.1%}"}</div></div><div><small>Profit factor</small><div class="kpi">{"—" if not len(pnl) else ("∞" if math.isinf(pf) else f"{pf:.2f}")}</div></div><div><small>Total P&L</small><div class="kpi">₹{total:,.2f}</div></div><div><small>Max DD</small><div class="kpi">₹{dd:,.2f}</div></div></div></div><div class="card"><h2>Recent observations</h2><table><tr><th>Signal ID</th><th>Expiry</th><th>Status</th><th>Signal</th><th>Net MC EV</th><th>Realized P&L</th></tr>{rows}</table></div><p><a href="../index.html">Back to SENSEX defined-risk selector</a></p></body></html>""",encoding="utf-8")

def selector(stats,site_root):
    site_root.mkdir(parents=True,exist_ok=True)
    cards=[]
    for s in STRATEGIES:
        x=stats.get(s,{"n":0,"total":0.0}); folder=s.lower().replace(" ","-")
        cards.append(f'<div class="card"><h2>{html.escape(s)}</h2><p>Closed trades: {x["n"]} • Total P&L: ₹{x["total"]:,.2f}</p><a href="{folder}/index.html">Open dashboard</a></div>')
    (site_root/"index.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>SENSEX Defined-Risk Prospective</title><style>body{{font-family:Arial;background:#0d1117;color:#e6edf3;max-width:1100px;margin:auto;padding:24px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:14px 0}}a{{color:#58a6ff}}</style></head><body><h1>SENSEX — Defined-Risk Prospective Validation</h1><p>Two retained frozen strategies, independently observed. No retrospective selection.</p>{''.join(cards)}</body></html>""",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["scan","settle"],default="scan")
    ap.add_argument("--strategy",default="all",choices=["all","Jade Lizard","Put Ratio Spread"])
    ap.add_argument("--seed",type=int,default=20260920)
    args=ap.parse_args()
    BASE.mkdir(parents=True,exist_ok=True); site_root=ROOT/"site/sensex/prospective-defined-risk"
    ts=now_ist(); decision=pd.Timestamp(ts.date()).normalize()
    history=fetch_index_history(decision-pd.Timedelta(days=2200),decision-pd.Timedelta(days=1))
    history["date"]=pd.to_datetime(history.date).dt.normalize()
    selected=STRATEGIES if args.strategy=="all" else [args.strategy]
    stats={}
    if args.mode=="settle":
        for strategy in STRATEGIES:
            folder=strategy.lower().replace(" ","-"); lp=BASE/f"{folder}_ledger.csv"; sp=BASE/f"{folder}_signals.csv"
            ledger=load_csv(lp,LEDGER_COLS); ledger=settle(history,ledger); ledger.to_csv(lp,index=False)
            signals=load_csv(sp,SIGNAL_COLS); page(strategy,signals,ledger,site_root/folder)
            pnl=pd.to_numeric(ledger.loc[ledger.status.eq("CLOSED"),"realized_pnl_inr"],errors="coerce").dropna()
            stats[strategy]={"n":len(pnl),"total":float(pnl.sum()) if len(pnl) else 0.0}
        selector(stats,site_root); return
    live=fetch_live_sensex(); spot,live_date=extract_live_spot_and_date(live)
    if live_date.date()!=decision.date(): raise RuntimeError(f"SENSEX live date {live_date.date()} != decision date {decision.date()}")
    expiry=third_future_weekday(decision)
    chain=fetch_option_chain(expiry)
    cutoff=pd.Timestamp(history.date.max()).normalize()
    returns=np.log(history.close.astype(float)).diff().dropna().tail(LOOKBACK).to_numpy(float)
    if len(returns)<LOOKBACK: raise RuntimeError("insufficient 756-session SENSEX history")
    terminal=mc_terminal(returns,spot,3,MC_PATHS,args.seed)
    for strategy in selected:
        folder=strategy.lower().replace(" ","-"); lp=BASE/f"{folder}_ledger.csv"; sp=BASE/f"{folder}_signals.csv"
        ledger=load_csv(lp,LEDGER_COLS); signals=load_csv(sp,SIGNAL_COLS); sid=f"{decision.date()}|{strategy}"
        if sid in set(signals.get("signal_id",pd.Series(dtype=str)).astype(str)): continue
        try:
            result=evaluate(strategy,terminal,spot,chain,expiry,decision)
            row={"signal_id":sid,"run_timestamp_ist":ts.isoformat(),"decision_date":decision.date().isoformat(),"expiry":expiry.date().isoformat(),
                 "strategy":strategy,"status":"ENTRY_DAY","signal":result["signal"],"spot":float(spot),"mc_paths":MC_PATHS,"lookback_sessions":LOOKBACK,
                 "model_data_cutoff":cutoff.date().isoformat(),"quote_retrieved_at_ist":ts.isoformat(),"mc_ev_points_net":result["mc_ev_points_net"],
                 "mc_pop":result["mc_pop"],"es95_points":result["es95_points"],"es99_points":result["es99_points"],"risk_points_per_lot":result["risk_points_per_lot"],
                 "entry_cost_inr_expected":result["entry_cost_inr_expected"],"entry_cost_inr_entry_only":result["entry_cost_inr_entry_only"],
                 "strikes_json":json.dumps(result["strikes"],sort_keys=True),"legs_json":json.dumps(result["legs"],sort_keys=True),"notes":"Frozen SENSEX prospective candidate; no cross-candidate selection."}
            signals=pd.concat([signals,pd.DataFrame([row])],ignore_index=True)
            if result["signal"]=="ENTER":
                l={"signal_id":sid,"decision_date":decision.date().isoformat(),"expiry":expiry.date().isoformat(),"strategy":strategy,"status":"OPEN","signal":"ENTER",
                   "spot":float(spot),"lot_size":LOT_SIZE,"lots":1,"mc_ev_points_net":result["mc_ev_points_net"],"mc_pop":result["mc_pop"],"risk_points_per_lot":result["risk_points_per_lot"],
                   "entry_cashflow_points_per_unit":result["entry_cashflow"],"entry_cost_inr":result["entry_cost_inr_expected"],"legs_json":json.dumps(result["legs"],sort_keys=True),
                   "model_data_cutoff":cutoff.date().isoformat(),"entry_timestamp_ist":ts.isoformat(),"exit_date":"","exit_spot":"","realized_pnl_points_per_unit":"","realized_pnl_inr":"","notes":"One-lot paper observation; no broker order."}
                ledger=pd.concat([ledger,pd.DataFrame([l])],ignore_index=True)
        except Exception as exc:
            row={"signal_id":sid,"run_timestamp_ist":ts.isoformat(),"decision_date":decision.date().isoformat(),"expiry":expiry.date().isoformat(),"strategy":strategy,
                 "status":"NO_TRADE","signal":"NO_TRADE","spot":float(spot),"mc_paths":MC_PATHS,"lookback_sessions":LOOKBACK,"model_data_cutoff":cutoff.date().isoformat(),
                 "quote_retrieved_at_ist":ts.isoformat(),"notes":f"NO_TRADE due to hard data/protocol condition: {exc}"}
            signals=pd.concat([signals,pd.DataFrame([row])],ignore_index=True)
        signals.to_csv(sp,index=False); ledger.to_csv(lp,index=False); page(strategy,signals,ledger,site_root/folder)
        pnl=pd.to_numeric(ledger.loc[ledger.status.eq("CLOSED"),"realized_pnl_inr"],errors="coerce").dropna()
        stats[strategy]={"n":len(pnl),"total":float(pnl.sum()) if len(pnl) else 0.0}
    selector(stats,site_root)

if __name__=="__main__":
    main()
