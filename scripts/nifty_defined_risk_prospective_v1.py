from __future__ import annotations
import argparse, html, json, math, os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.batman_signal_producer import (
    NSEClient,
    mc_paths,
    trading_sessions_between,
    unique_strikes,
    find_option_row,
    side_execution_price,
)
from nifty_mc.strategy_catalog import build_strategy

IST_NAME="Asia/Kolkata"
STRATEGIES=["Jade Lizard","Put Ratio Spread"]
LOT_SIZE=65
MC_PATHS=5000
LOOKBACK=756
ENTRY_HOUR=9
ENTRY_MINUTE=30
SLIPPAGE_POINTS=2.0
BROKERAGE_PER_ORDER_INR=10.0
STT_SELL_OLD=0.001
STT_SELL_NEW=0.0015
STT_EXERCISE_OLD=0.00125
STT_EXERCISE_NEW=0.0015
STT_CHANGE_DATE=pd.Timestamp("2026-04-01")
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"paper_trading/prospective_defined_risk/nifty"

def today_ist():
    return pd.Timestamp.now(tz=IST_NAME).tz_localize(None).normalize()

def seed_for(strategy,date_value):
    import zlib
    return int((20260920+zlib.crc32(f"{strategy}|{date_value.date()}".encode()))%(2**32-1))

def target_map(strategy,terminal,spot):
    qs=np.percentile(terminal,[10,35,65,90])
    all_targets={"p10":float(qs[0]),"p35":float(qs[1]),"c65":float(qs[2]),"c90":float(qs[3]),"atm":float(spot)}
    required={
        "Jade Lizard":["p35","c65","c90"],
        "Put Ratio Spread":["atm","p35"],
    }
    return {k:all_targets[k] for k in required[strategy]}

def stt_rates(d):
    if d>=STT_CHANGE_DATE:
        return STT_SELL_NEW,STT_EXERCISE_NEW
    return STT_SELL_OLD,STT_EXERCISE_OLD

def evaluate(strategy,terminal,spot,chain,expiry,decision):
    targets=target_map(strategy,terminal,spot)
    strikes=unique_strikes(chain.loc[chain.expiry.eq(expiry),"strike"].dropna().unique(),targets)
    legs=build_strategy(strategy,strikes)
    entry_cashflow=0.0
    contracts=0
    entry_stt_inr=0.0
    priced=[]
    sell_stt_rate,_=stt_rates(decision)
    for leg in legs:
        row=find_option_row(chain,expiry,leg.option_type,leg.strike)
        side="BUY" if leg.qty>0 else "SELL"
        raw_px,_=side_execution_price(row,side)
        px=raw_px+SLIPPAGE_POINTS if side=="BUY" else raw_px-SLIPPAGE_POINTS
        if px<=0:
            raise ValueError(f"quote becomes non-positive after slippage: {strategy} {leg.option_type} {leg.strike}")
        entry_cashflow-=leg.qty*px
        contracts+=abs(int(leg.qty))
        if side=="SELL":
            entry_stt_inr += abs(int(leg.qty))*LOT_SIZE*px*sell_stt_rate
        priced.append({"side":side,"option_type":leg.option_type,"strike":float(leg.strike),
                       "qty":int(leg.qty),"premium_points":float(px),
                       "bid":float(row.get("bid")),"ask":float(row.get("ask"))})
    entry_brokerage_inr=BROKERAGE_PER_ORDER_INR*len(legs)
    round_trip_brokerage_inr=BROKERAGE_PER_ORDER_INR*len(legs)*2
    entry_cost_points=(round_trip_brokerage_inr+entry_stt_inr)/LOT_SIZE
    gross=np.zeros(len(terminal))+entry_cashflow
    expected_exercise_stt_inr=np.zeros(len(terminal))
    _,exercise_stt_rate=stt_rates(decision)
    for leg in legs:
        intrinsic=np.maximum(terminal-leg.strike,0.0) if leg.option_type=="CE" else np.maximum(leg.strike-terminal,0.0)
        gross += leg.qty*intrinsic
        if leg.qty>0:
            expected_exercise_stt_inr += abs(int(leg.qty))*LOT_SIZE*intrinsic*exercise_stt_rate
    net=gross-(round_trip_brokerage_inr+entry_stt_inr+expected_exercise_stt_inr)/LOT_SIZE
    ev=float(np.mean(net))
    pop=float(np.mean(net>0))
    q05=float(np.quantile(net,0.05)); q01=float(np.quantile(net,0.01))
    es95=max(0.0,-float(np.mean(net[net<=q05])))
    es99=max(0.0,-float(np.mean(net[net<=q01])))
    return {
        "strategy":strategy,"expiry":str(expiry.date()),"spot":float(spot),
        "strikes":{k:float(v) for k,v in strikes.items()},"legs":priced,
        "mc_ev_points_net":ev,"mc_pop":pop,"mc_es95_points":es95,"mc_es99_points":es99,
        "risk_points_per_lot":max(es95,es99),"contracts":contracts,
        "entry_cashflow_points_per_unit":float(entry_cashflow),
        "slippage_points_total":float(SLIPPAGE_POINTS*contracts),
        "entry_stt_inr":float(entry_stt_inr),
        "round_trip_brokerage_inr":float(round_trip_brokerage_inr),
        "entry_brokerage_inr":float(entry_brokerage_inr),
        "signal":"ENTER" if ev>0 else "NO_TRADE",
    }

def load_csv(path,cols):
    return pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame(columns=cols)

SIGNAL_COLS=["signal_id","run_timestamp_ist","decision_date","expiry","strategy","status","signal","spot","mc_paths","lookback_sessions","horizon_sessions",
             "model_data_cutoff","quote_retrieved_at_ist","mc_ev_points_net","mc_pop","mc_es95_points","mc_es99_points","risk_points_per_lot",
             "slippage_points_total","entry_brokerage_inr","round_trip_brokerage_inr","entry_stt_inr","strikes_json","legs_json","notes"]
LEDGER_COLS=["signal_id","decision_date","expiry","strategy","status","signal","spot","lot_size","lots","mc_ev_points_net","mc_pop","risk_points_per_lot",
             "entry_cashflow_points_per_unit","entry_cost_inr","legs_json","model_data_cutoff","entry_timestamp_ist","exit_date","exit_spot",
             "realized_pnl_points_per_unit","realized_pnl_inr","notes"]

def settle_ledgers(index_df,ledger):
    if ledger.empty:return ledger
    close_map=dict(zip(pd.to_datetime(index_df.date).dt.normalize(),pd.to_numeric(index_df.close,errors="coerce")))
    for idx in ledger.index[ledger.status.eq("OPEN")]:
        expiry=pd.Timestamp(ledger.at[idx,"expiry"]).normalize()
        if expiry not in close_map: continue
        spot=float(close_map[expiry]); entry_cash=float(ledger.at[idx,"entry_cashflow_points_per_unit"])
        pnl=entry_cash
        for leg in json.loads(str(ledger.at[idx,"legs_json"])):
            q=int(leg["qty"]); k=float(leg["strike"])
            intrinsic=max(spot-k,0) if leg["option_type"]=="CE" else max(k-spot,0)
            pnl += q*intrinsic
        lot=int(ledger.at[idx,"lot_size"]); lots=int(ledger.at[idx,"lots"] or 1)
        entry_cost_inr=float(ledger.at[idx,"entry_cost_inr"])
        exercise_stt=0.0
        _,rate=stt_rates(expiry)
        for leg in json.loads(str(ledger.at[idx,"legs_json"])):
            if int(leg["qty"])>0:
                q=int(leg["qty"]); k=float(leg["strike"])
                intrinsic=max(spot-k,0) if leg["option_type"]=="CE" else max(k-spot,0)
                exercise_stt += q*lot*intrinsic*rate
        realized_inr=pnl*lot*lots-entry_cost_inr*lots-exercise_stt*lots
        ledger.at[idx,"status"]="CLOSED"
        ledger.at[idx,"exit_date"]=expiry.date().isoformat()
        ledger.at[idx,"exit_spot"]=spot
        ledger.at[idx,"realized_pnl_points_per_unit"]=pnl-(exercise_stt/lot)
        ledger.at[idx,"realized_pnl_inr"]=realized_inr
    return ledger

def strategy_page(strategy,signals,ledger,latest,site_dir):
    site_dir.mkdir(parents=True,exist_ok=True)
    closed=ledger[ledger.status.eq("CLOSED")].copy()
    pnl=pd.to_numeric(closed.realized_pnl_inr,errors="coerce").dropna()
    total=float(pnl.sum()) if len(pnl) else 0.0
    win=float((pnl>0).mean()) if len(pnl) else float("nan")
    gains=float(pnl[pnl>0].sum()) if len(pnl) else 0.0
    losses=float(-pnl[pnl<0].sum()) if len(pnl) else 0.0
    pf=gains/losses if losses else float("inf")
    eq=pnl.cumsum() if len(pnl) else pd.Series(dtype=float)
    dd=float((eq-eq.cummax()).min()) if len(eq) else 0.0
    def obs_row(r):
        pnl="" if pd.isna(r.realized_pnl_inr) else f"₹{float(r.realized_pnl_inr):,.2f}"
        return f"<tr><td>{html.escape(str(r.signal_id))}</td><td>{html.escape(str(r.expiry))}</td><td>{html.escape(str(r.status))}</td><td>{html.escape(str(r.signal))}</td><td>{float(r.mc_ev_points_net):.2f}</td><td>{pnl}</td></tr>"
    rows="".join(obs_row(r) for _,r in signals.tail(25).iloc[::-1].iterrows())
    page=f"""<!doctype html><html><head><meta charset="utf-8"><title>NIFTY {html.escape(strategy)}</title><style>body{{font-family:Arial;background:#0d1117;color:#e6edf3;max-width:1200px;margin:auto;padding:24px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:14px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}.kpi{{font-size:24px;font-weight:700}}table{{width:100%;border-collapse:collapse}}th,td{{padding:7px;border-bottom:1px solid #30363d;text-align:left}}a{{color:#58a6ff}}</style></head><body>
<h1>NIFTY — {html.escape(strategy)}</h1>
<p>Frozen prospective validation • 09:30 IST • 3 future trading sessions • 5,000 MC paths • 756-session lookback • net MC-EV gate. No strategy is selected over another.</p>
<div class="card"><h2>Latest observation</h2><div class="grid">
<div><small>Signal</small><div class="kpi">{html.escape(str(latest.get("signal","NO_TRADE")))}</div></div>
<div><small>Decision</small><div class="kpi">{html.escape(str(latest.get("decision_date","—")))}</div></div>
<div><small>Expiry</small><div class="kpi">{html.escape(str(latest.get("expiry","—")))}</div></div>
<div><small>Spot</small><div class="kpi">{float(latest.get("spot",0)):.2f}</div></div>
<div><small>Net MC EV</small><div class="kpi">{float(latest.get("mc_ev_points_net",0)):.2f}</div></div>
<div><small>MC POP</small><div class="kpi">{float(latest.get("mc_pop",0)):.1%}</div></div>
</div></div>
<div class="card"><h2>Prospective ledger summary</h2><div class="grid"><div><small>Closed trades</small><div class="kpi">{len(closed)}</div></div><div><small>Win rate</small><div class="kpi">{"—" if not len(pnl) else f"{win:.1%}"}</div></div><div><small>Profit factor</small><div class="kpi">{"—" if not len(pnl) else ("∞" if math.isinf(pf) else f"{pf:.2f}")}</div></div><div><small>Total P&L</small><div class="kpi">₹{total:,.2f}</div></div><div><small>Max drawdown</small><div class="kpi">₹{dd:,.2f}</div></div></div></div>
<div class="card"><h2>Recent observations</h2><table><tr><th>Signal ID</th><th>Expiry</th><th>Status</th><th>Signal</th><th>Net MC EV</th><th>Realized P&L</th></tr>{rows}</table></div>
<div class="card"><a href="../index.html">Back to NIFTY defined-risk selector</a></div></body></html>"""
    (site_dir/"index.html").write_text(page,encoding="utf-8")

def selector_page(stats,site_dir):
    site_dir.mkdir(parents=True,exist_ok=True)
    cards=[]
    for s in STRATEGIES:
        x=stats.get(s,{})
        folder=s.lower().replace(" ","-")
        cards.append(f'<div class="card"><h2>{html.escape(s)}</h2><p>Closed trades: {x.get("n",0)} &nbsp; Total P&L: ₹{x.get("total",0):,.2f}</p><p><a href="{folder}/index.html">Open dashboard</a></p></div>')
    (site_dir/"index.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>NIFTY Defined-Risk Prospective</title><style>body{{font-family:Arial;background:#0d1117;color:#e6edf3;max-width:1100px;margin:auto;padding:24px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:14px 0}}a{{color:#58a6ff}}</style></head><body><h1>NIFTY — Defined-Risk Prospective Validation</h1><p>Two frozen strategies. Each strategy has an independent paper-validation ledger and no post-hoc selection.</p>{''.join(cards)}</body></html>""",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["scan","settle"],default="scan")
    ap.add_argument("--strategy",default="all",choices=["all","Jade Lizard","Put Ratio Spread"])
    ap.add_argument("--decision-date",default="auto")
    ap.add_argument("--seed",type=int,default=20260920)
    args=ap.parse_args()
    BASE.mkdir(parents=True,exist_ok=True)
    site_root=ROOT/"site/prospective-defined-risk/nifty"
    client=NSEClient()
    decision=today_ist() if args.decision_date=="auto" else pd.Timestamp(args.decision_date).normalize()
    index_df=client.fetch_index_history((decision-pd.Timedelta(days=2200)).date(),decision.date())
    index_df["date"]=pd.to_datetime(index_df["date"]).dt.normalize()
    holidays=client.fetch_holidays()
    selected=STRATEGIES if args.strategy=="all" else [args.strategy]
    all_latest={}
    if args.mode=="settle":
        for strategy in STRATEGIES:
            lp=BASE/f"{strategy.lower().replace(' ','-')}_ledger.csv"
            ledger=load_csv(lp,LEDGER_COLS); ledger=settle_ledgers(index_df,ledger); ledger.to_csv(lp,index=False)
            sp=BASE/f"{strategy.lower().replace(' ','-')}_signals.csv"
            signals=load_csv(sp,SIGNAL_COLS)
            latest=signals.tail(1).iloc[0].to_dict() if len(signals) else {"signal":"NO_TRADE","decision_date":decision.date().isoformat(),"strategy":strategy}
            strategy_page(strategy,signals,ledger,latest,site_root/strategy.lower().replace(" ","-"))
            pnl=pd.to_numeric(ledger.loc[ledger.status.eq("CLOSED"),"realized_pnl_inr"],errors="coerce").dropna()
            all_latest[strategy]={"n":len(pnl),"total":float(pnl.sum()) if len(pnl) else 0.0}
        selector_page(all_latest,site_root)
        return
    # scan
    if decision.weekday()>=5:
        for strategy in STRATEGIES:
            lp=BASE/f"{strategy.lower().replace(' ','-')}_ledger.csv"; ledger=load_csv(lp,LEDGER_COLS)
            sp=BASE/f"{strategy.lower().replace(' ','-')}_signals.csv"; signals=load_csv(sp,SIGNAL_COLS)
            latest=signals.tail(1).iloc[0].to_dict() if len(signals) else {"signal":"NO_TRADE","decision_date":decision.date().isoformat(),"strategy":strategy}
            strategy_page(strategy,signals,ledger,latest,site_root/strategy.lower().replace(" ","-"))
            all_latest[strategy]={"n":int((ledger.status=="CLOSED").sum()),"total":float(pd.to_numeric(ledger.loc[ledger.status.eq("CLOSED"),"realized_pnl_inr"],errors="coerce").fillna(0).sum())}
        selector_page(all_latest,site_root)
        return
    prior=index_df.loc[index_df.date<decision].copy()
    if prior.empty: raise RuntimeError("No prior completed NIFTY session")
    cutoff=pd.Timestamp(prior.date.max()).normalize()
    model_spot=float(prior.loc[prior.date.eq(cutoff),"close"].iloc[-1])
    for strategy in selected:
        sp=BASE/f"{strategy.lower().replace(' ','-')}_signals.csv"; lp=BASE/f"{strategy.lower().replace(' ','-')}_ledger.csv"
        signals=load_csv(sp,SIGNAL_COLS); ledger=load_csv(lp,LEDGER_COLS)
        sid=f"{decision.date()}|{strategy}"
        if sid in set(signals.get("signal_id",pd.Series(dtype=str)).astype(str)):
            continue
        try:
            chain,underlying,endpoint,front_expiry=client.fetch_option_chain()
            sessions=trading_sessions_between(decision,front_expiry,holidays)
            future_sessions=sessions[sessions>decision]
            if len(future_sessions)!=3 or front_expiry not in set(sessions):
                raise RuntimeError(f"frozen entry rule requires exactly 3 future sessions; found {len(future_sessions)}")
            returns=np.log(prior.close.astype(float)).diff().dropna().tail(LOOKBACK).to_numpy(float)
            if len(returns)<LOOKBACK: raise RuntimeError("insufficient 756-session lookback")
            terminal=mc_paths(model_spot,returns,len(future_sessions),MC_PATHS,seed_for(strategy,decision))
            result=evaluate(strategy,terminal,model_spot,chain,front_expiry,decision)
            row={"signal_id":sid,"run_timestamp_ist":pd.Timestamp.now(tz=IST_NAME).isoformat(),
                 "decision_date":decision.date().isoformat(),"expiry":front_expiry.date().isoformat(),"strategy":strategy,
                 "status":"ENTRY_DAY","signal":result["signal"],"spot":model_spot,"mc_paths":MC_PATHS,"lookback_sessions":LOOKBACK,
                 "horizon_sessions":len(future_sessions),"model_data_cutoff":cutoff.date().isoformat(),"quote_retrieved_at_ist":pd.Timestamp.now(tz=IST_NAME).isoformat(),
                 "mc_ev_points_net":result["mc_ev_points_net"],"mc_pop":result["mc_pop"],"mc_es95_points":result["mc_es95_points"],
                 "mc_es99_points":result["mc_es99_points"],"risk_points_per_lot":result["risk_points_per_lot"],
                 "slippage_points_total":result["slippage_points_total"],"entry_brokerage_inr":result["entry_brokerage_inr"],
                 "round_trip_brokerage_inr":result["round_trip_brokerage_inr"],"entry_stt_inr":result["entry_stt_inr"],
                 "strikes_json":json.dumps(result["strikes"],sort_keys=True),"legs_json":json.dumps(result["legs"],sort_keys=True),
                 "notes":"Frozen NIFTY prospective candidate. No strategy ranking or retuning is performed."}
            signals=pd.concat([signals,pd.DataFrame([row])],ignore_index=True)
            if result["signal"]=="ENTER":
                ledger_row={"signal_id":sid,"decision_date":decision.date().isoformat(),"expiry":front_expiry.date().isoformat(),
                            "strategy":strategy,"status":"OPEN","signal":"ENTER","spot":model_spot,"lot_size":LOT_SIZE,"lots":1,
                            "mc_ev_points_net":result["mc_ev_points_net"],"mc_pop":result["mc_pop"],"risk_points_per_lot":result["risk_points_per_lot"],
                            "entry_cashflow_points_per_unit":result["entry_cashflow_points_per_unit"],"entry_cost_inr":result["round_trip_brokerage_inr"]+result["entry_stt_inr"],
                            "legs_json":json.dumps(result["legs"],sort_keys=True),"model_data_cutoff":cutoff.date().isoformat(),
                            "entry_timestamp_ist":pd.Timestamp.now(tz=IST_NAME).isoformat(),"exit_date":"","exit_spot":"",
                            "realized_pnl_points_per_unit":"","realized_pnl_inr":"","notes":"One-lot paper observation; no broker order."}
                ledger=pd.concat([ledger,pd.DataFrame([ledger_row])],ignore_index=True)
        except Exception as exc:
            row={"signal_id":sid,"run_timestamp_ist":pd.Timestamp.now(tz=IST_NAME).isoformat(),"decision_date":decision.date().isoformat(),
                 "expiry":"","strategy":strategy,"status":"NO_TRADE","signal":"NO_TRADE","spot":model_spot,"mc_paths":MC_PATHS,"lookback_sessions":LOOKBACK,
                 "horizon_sessions":"","model_data_cutoff":cutoff.date().isoformat(),"quote_retrieved_at_ist":"",
                 "mc_ev_points_net":"","mc_pop":"","mc_es95_points":"","mc_es99_points":"","risk_points_per_lot":"",
                 "slippage_points_total":"","entry_brokerage_inr":"","round_trip_brokerage_inr":"","entry_stt_inr":"","strikes_json":"[]","legs_json":"[]",
                 "notes":f"NO_TRADE due to hard data/protocol condition: {exc}"}
            signals=pd.concat([signals,pd.DataFrame([row])],ignore_index=True)
        signals.to_csv(sp,index=False); ledger.to_csv(lp,index=False)
        latest=signals.tail(1).iloc[0].to_dict(); strategy_page(strategy,signals,ledger,latest,site_root/strategy.lower().replace(" ","-"))
        pnl=pd.to_numeric(ledger.loc[ledger.status.eq("CLOSED"),"realized_pnl_inr"],errors="coerce").dropna()
        all_latest[strategy]={"n":len(pnl),"total":float(pnl.sum()) if len(pnl) else 0.0}
    selector_page(all_latest,site_root)

if __name__=="__main__":
    main()
