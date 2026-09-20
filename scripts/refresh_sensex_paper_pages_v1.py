from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.sensex_backtest_v1 import realized_costs
from scripts.sensex_paper_signal_producer_v1 import fetch_index_history, now_ist

BATMAN_LEDGER = Path("paper_trading/sensex_batman_ledger.csv")
ADAPTIVE_LEDGER = Path("paper_trading/sensex_adaptive_ledger.csv")
PAGE_ROOT = Path("site/sensex")

def load_ledger(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()

def settle(path: Path, history: pd.DataFrame) -> int:
    df = load_ledger(path)
    if df.empty or "status" not in df:
        return 0
    closed = 0
    for i, row in df.loc[df["status"].astype(str).eq("OPEN")].iterrows():
        expiry = pd.Timestamp(row["expiry"]).normalize()
        matches = history.loc[history["date"].eq(expiry)]
        if matches.empty:
            continue
        expiry_spot = float(matches.iloc[-1]["close"])
        legs = json.loads(row["legs_json"])
        net_points = float(row["entry_cashflow_points_per_unit"])
        for leg in legs:
            intrinsic = (
                max(expiry_spot - float(leg["strike"]), 0.0)
                if leg["option_type"] == "CE"
                else max(float(leg["strike"]) - expiry_spot, 0.0)
            )
            net_points += int(leg["qty"]) * intrinsic
        entry_date = pd.Timestamp(row["decision_date"]).normalize()
        cost = realized_costs(entry_date, legs, int(row["lot_size"]), expiry_spot)
        lots = int(row["lots"])
        pnl_inr = net_points * int(row["lot_size"]) * lots - cost * lots
        df.at[i, "status"] = "CLOSED"
        df.at[i, "exit_date"] = str(expiry.date())
        df.at[i, "exit_spot"] = expiry_spot
        df.at[i, "realized_pnl_points_per_unit"] = net_points
        df.at[i, "realized_pnl_inr"] = pnl_inr
        closed += 1
    df.to_csv(path, index=False)
    return closed

def stats(df: pd.DataFrame) -> dict[str, Any]:
    closed = df.loc[df["status"].astype(str).eq("CLOSED")].copy() if not df.empty else pd.DataFrame()
    if closed.empty:
        return {"closed_trades":0,"win_rate":0.0,"profit_factor":0.0,"total_pnl":0.0,"max_drawdown":0.0}
    pnl = pd.to_numeric(closed["realized_pnl_inr"], errors="coerce").fillna(0.0)
    gains = float(pnl[pnl>0].sum()); losses = float(-pnl[pnl<0].sum())
    eq = pnl.cumsum(); dd = eq - eq.cummax()
    return {
        "closed_trades": int(len(closed)),
        "win_rate": float((pnl>0).mean()),
        "profit_factor": gains/losses if losses>0 else (float("inf") if gains>0 else 0.0),
        "total_pnl": float(pnl.sum()),
        "max_drawdown": float(dd.min()),
    }

def esc(v: Any) -> str:
    return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def render_rows(df: pd.DataFrame, cols: list[str], limit: int = 12) -> str:
    if df.empty:
        return "<p class='note'>No prospective observations yet.</p>"
    x=df.sort_values("decision_date", ascending=False).head(limit)
    head="".join(f"<th>{esc(c)}</th>" for c in cols)
    body=[]
    for _,r in x.iterrows():
        body.append("<tr>"+ "".join(f"<td>{esc(r.get(c,''))}</td>" for c in cols) +"</tr>")
    return f"<table><tr>{head}</tr>{''.join(body)}</table>"

def build_strategy_page(strategy: str, ledger: pd.DataFrame, latest_json: dict[str,Any], path: Path) -> None:
    s=stats(ledger)
    latest=latest_json.get("signal",{}) if latest_json else {}
    title=f"SENSEX {strategy} Paper Trading"
    back="adaptive" if strategy=="Batman" else "batman"
    latest_html="<p class='badge'>NO PROSPECTIVE OBSERVATION YET</p>"
    if latest:
        latest_html = f"""
        <div class="grid">
        <div><small>Signal</small><div class="kpi">{esc(latest.get('signal',''))}</div></div>
        <div><small>Decision date</small><div class="kpi">{esc(latest.get('decision_date',''))}</div></div>
        <div><small>Expiry</small><div class="kpi">{esc(latest.get('expiry',''))}</div></div>
        <div><small>Regime</small><div class="kpi">{esc(latest.get('regime',''))}</div></div>
        <div><small>Spot</small><div class="kpi">{esc(latest.get('spot',''))}</div></div>
        <div><small>Net MC EV</small><div class="kpi">{esc(latest.get('mc_ev_points_net',''))}</div></div>
        <div><small>MC POP</small><div class="kpi">{esc(latest.get('mc_pop',''))}</div></div>
        <div><small>Lots</small><div class="kpi">{esc(latest.get('lots',0))}</div></div>
        </div>
        <p class='note'>Model cutoff: {esc(latest.get('model_data_cutoff',''))}. Quotes retrieved: {esc(latest.get('quote_retrieved_at_ist',''))}.</p>
        """
    signal_cols=["decision_date","expiry","signal","regime","mc_ev_points_net","mc_pop","lots","status"]
    trade_cols=["decision_date","expiry","signal","status","lots","realized_pnl_inr"]
    extra = ""
    if strategy=="Adaptive":
        extra = "<div class='card'><h2>Candidate-selection boundary</h2><p class='note'>The regime candidate set is frozen from S0–S6. The prospective primary is the highest net MC-EV eligible candidate; this rule is not retrospectively revalidated on the historical holdout.</p></div>"
    html=f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{title}</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#0b1220;color:#e8eef6}}main{{max-width:1220px;margin:auto;padding:24px}}
.card{{background:#111a2a;border:1px solid #2a374b;border-radius:14px;padding:18px;margin:14px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}
.kpi{{font-size:23px;font-weight:750}}small{{color:#93a5bb}}a{{color:#7fb0ff}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:8px;border-bottom:1px solid #293547;text-align:left;vertical-align:top}}.badge{{display:inline-block;padding:5px 10px;border-radius:999px;background:#21304a;font-weight:700}}.note{{color:#aebdce;line-height:1.55}}
</style></head><body><main>
<p><a href="../">← SENSEX strategy selector</a> · <a href="../{back}/">{back.title()}</a></p>
<div class="card"><span class="badge">SENSEX • {strategy.upper()} • PAPER ONLY</span><h1>{strategy} Paper-Trading Scanner</h1>
<p class="note">Prospective S7 stream only. Entry at 09:30 IST; 0.50-point per-leg slippage stress; one-lot transfer-edge sizing; no broker execution.</p></div>
<div class="card"><h2>Latest signal</h2>{latest_html}</div>
<div class="card"><h2>Paper-trading summary</h2><div class="grid">
<div><small>Closed trades</small><div class="kpi">{s['closed_trades']}</div></div>
<div><small>Win rate</small><div class="kpi">{s['win_rate']:.1%}</div></div>
<div><small>Profit factor</small><div class="kpi">{s['profit_factor'] if np.isfinite(s['profit_factor']) else '∞'}</div></div>
<div><small>Total P&amp;L</small><div class="kpi">₹{s['total_pnl']:,.2f}</div></div>
<div><small>Max drawdown</small><div class="kpi">₹{s['max_drawdown']:,.2f}</div></div>
</div></div>
<div class="card"><h2>Recent signals</h2>{render_rows(ledger,signal_cols)}</div>
<div class="card"><h2>Recent paper trades</h2>{render_rows(ledger,trade_cols)}</div>
{extra}
<div class="card"><h2>Research boundary</h2><p class="note">Missing bid/ask, incompatible BSE schemas, or unavailable target expiry produce NO_TRADE. No LTP fallback is permitted. The S5/S6 historical holdout is not reopened or used to backfill this ledger.</p></div>
<div class="card"><small>Branch: research/sensex-s7-paper-trading-v1 • Paper only • No broker order execution.</small></div>
</main></body></html>"""
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(html,encoding="utf-8")

def main() -> None:
    today=pd.Timestamp(now_ist().date()).normalize()
    history=fetch_index_history(today-pd.Timedelta(days=2200), today)
    closed_b=settle(BATMAN_LEDGER,history)
    closed_a=settle(ADAPTIVE_LEDGER,history)
    PAGE_ROOT.mkdir(parents=True,exist_ok=True)
    latest_b=Path("site/sensex/batman/data/latest_signal.json")
    latest_a=Path("site/sensex/adaptive/data/latest_signal.json")
    lb=json.loads(latest_b.read_text()) if latest_b.exists() else {}
    la=json.loads(latest_a.read_text()) if latest_a.exists() else {}
    build_strategy_page("Batman", load_ledger(BATMAN_LEDGER), lb, PAGE_ROOT/"batman"/"index.html")
    build_strategy_page("Adaptive", load_ledger(ADAPTIVE_LEDGER), la, PAGE_ROOT/"adaptive"/"index.html")
    selector="""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>SENSEX Paper Trading</title><style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#0b1220;color:#e8eef6}main{max-width:1000px;margin:auto;padding:32px 20px 48px}.hero,.card{padding:24px;border:1px solid #2a374b;border-radius:18px;background:#111a2a}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin-top:22px}.card{display:block;text-decoration:none;color:inherit}.tag{display:inline-block;padding:5px 9px;border-radius:999px;background:#21304a;color:#bcd0ff;font-size:12px;font-weight:700}.card h2{margin:14px 0 8px}.card p{color:#aebdce;line-height:1.5}.open{font-weight:700;color:#7fb0ff}</style></head><body><main><section class='hero'><div class='tag'>BSE SENSEX • PAPER TRADING</div><h1>Choose a strategy dashboard</h1><p>SENSEX Batman and Adaptive prospective paper-trading streams.</p></section><section class='grid'><a class='card' href='batman/'><div class='tag'>SYSTEM 01</div><h2>Batman</h2><p>Frozen standalone Batman paper-trading scanner.</p><span class='open'>Open Batman →</span></a><a class='card' href='adaptive/'><div class='tag'>SYSTEM 02</div><h2>Adaptive</h2><p>Frozen regime-conditioned candidate router.</p><span class='open'>Open Adaptive →</span></a></section><p style='margin-top:22px;color:#8b98aa'>Entry scan: 09:30 IST weekdays. Settlement/page refresh: 16:00 IST. No broker orders.</p></main></body></html>"""
    (PAGE_ROOT/"index.html").write_text(selector,encoding="utf-8")
    meta={"refresh_timestamp_ist":now_ist().isoformat(),"batman_closed":closed_b,"adaptive_closed":closed_a}
    (PAGE_ROOT/"refresh_metadata.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    print(json.dumps(meta,indent=2))

if __name__=="__main__":
    main()
