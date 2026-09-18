from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from nifty_mc.strategy_catalog import STRATEGY_NAMES, STRATEGY_META, build_strategy

def option_price(chain, expiry, typ, strike):
    x = chain[(chain["expiry"] == expiry) & (chain["option_type"] == typ) & (chain["strike"] == float(strike))]
    if x.empty:
        return None
    v = float(pd.to_numeric(x.iloc[0]["close"], errors="coerce"))
    return None if not np.isfinite(v) or v <= 0 else v

def payoff_paths(terminal, priced):
    pnl = np.zeros(len(terminal), dtype=float)
    for leg, px in priced:
        intrinsic = np.maximum((terminal - leg.strike) if leg.option_type == "CE" else (leg.strike - terminal), 0.0)
        pnl += leg.qty * intrinsic
    entry = -sum(leg.qty * px for leg, px in priced)
    return pnl + entry, float(entry)

def mc_terminal(spot, returns, horizon_days, n, seed):
    r = returns[np.isfinite(returns)]
    if len(r) < 60:
        return None
    rng = np.random.default_rng(seed)
    h = max(1, int(horizon_days))
    sampled = rng.choice(r, size=n * h, replace=True).reshape(n, h)
    return spot * np.exp(sampled.sum(axis=1))

def unique_strikes(strikes, targets):
    strikes = np.sort(np.unique(np.asarray(strikes, dtype=float)))
    if len(strikes) < len(targets):
        return None
    used, out = set(), {}
    for label, target in sorted(targets.items(), key=lambda kv: kv[1]):
        order = np.argsort(np.abs(strikes - target))
        pick = None
        for i in order:
            v = float(strikes[i])
            if v not in used:
                pick = v
                break
        if pick is None:
            return None
        out[label] = pick
        used.add(pick)
    return out

def decision_features(idx, decision, terminal, spot):
    s = idx.loc[idx["date"] <= decision, "close"].to_numpy(float)
    r = idx.loc[idx["date"] <= decision, "logret"].dropna().to_numpy(float)
    if len(s) < 80 or len(r) < 60:
        return None
    tail = r[-60:]
    rv20 = float(np.std(r[-20:], ddof=1) * np.sqrt(252))
    rv60 = float(np.std(r[-60:], ddof=1) * np.sqrt(252))
    trend20 = float(s[-1] / s[-21] - 1)
    trend60 = float(s[-1] / s[-61] - 1)
    trend_accel = trend20 - trend60
    p_up = float(np.mean(terminal > spot * 1.005))
    p_down = float(np.mean(terminal < spot * 0.995))
    p_range = float(np.mean((terminal >= spot * 0.995) & (terminal <= spot * 1.005)))
    p_expand = float(np.mean(np.abs(terminal / spot - 1) >= 0.015))
    mc_median_return = float(np.median(terminal) / spot - 1)
    return {
        "rv20": rv20, "rv60": rv60, "trend20": trend20, "trend60": trend60, "trend_accel": trend_accel,
        "p_up": p_up, "p_down": p_down, "p_range": p_range, "p_expand": p_expand,
        "mc_median_return": mc_median_return
    }

def classify_with_frozen_development(df, dev):
    out = df.copy()
    q20_lo, q20_hi = dev.trend20.quantile(1/3), dev.trend20.quantile(2/3)
    q60_lo, q60_hi = dev.trend60.quantile(1/3), dev.trend60.quantile(2/3)
    qvol_lo, qvol_hi = dev.rv20.quantile(1/3), dev.rv20.quantile(2/3)
    qexp = dev.p_expand.quantile(2/3)

    out["trend20_rank"] = out.trend20.apply(lambda x: float((dev.trend20 <= x).mean()))
    out["trend60_rank"] = out.trend60.apply(lambda x: float((dev.trend60 <= x).mean()))
    out["trend_score"] = 0.5 * out.trend20_rank + 0.5 * out.trend60_rank

    direction = np.where(
        (out.trend20 >= q20_hi) & (out.trend60 >= q60_hi), "bull",
        np.where((out.trend20 <= q20_lo) & (out.trend60 <= q60_lo), "bear", "neutral")
    )
    breakout = (out.p_expand >= qexp) & (np.abs(out.trend_score - 0.5) < 0.18)
    direction = np.where(breakout, "breakout", direction)

    out["direction_prediction"] = direction
    out["vol_regime"] = np.where(out.rv20 <= qvol_lo, "low", np.where(out.rv20 <= qvol_hi, "medium", "high"))
    out["regime"] = out.direction_prediction + "_" + out.vol_regime
    out["development_q20_lo"] = q20_lo
    out["development_q20_hi"] = q20_hi
    out["development_q60_lo"] = q60_lo
    out["development_q60_hi"] = q60_hi
    return out

def summarize(g):
    if g.empty:
        return {"trades": 0, "win_rate": np.nan, "mean_pnl": np.nan, "median_pnl": np.nan,
                "total_pnl": 0.0, "profit_factor": np.nan, "max_drawdown": np.nan}
    x = g.realized_pnl.to_numpy(float)
    eq = np.cumsum(x)
    dd = eq - np.maximum.accumulate(eq)
    gains = x[x > 0].sum()
    losses = -x[x < 0].sum()
    return {
        "trades": len(g), "win_rate": float(np.mean(x > 0)), "mean_pnl": float(np.mean(x)),
        "median_pnl": float(np.median(x)), "total_pnl": float(np.sum(x)),
        "profit_factor": float(gains / losses) if losses > 0 else np.inf,
        "max_drawdown": float(dd.min())
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--options-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--paths", type=int, default=5000)
    args = ap.parse_args()

    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)

    idx = pd.read_csv(args.index, parse_dates=["date"]).sort_values("date")
    idx["close"] = pd.to_numeric(idx["close"], errors="coerce")
    idx = idx.dropna(subset=["date", "close"]).drop_duplicates("date").reset_index(drop=True)
    idx["logret"] = np.log(idx["close"]).diff()
    price = dict(zip(idx.date.dt.normalize(), idx.close))

    parts, target_files = [], []
    for p in sorted(Path(args.options_dir).rglob("nifty_options_*.csv.gz")):
        d = pd.read_csv(p, parse_dates=["timestamp", "expiry"], low_memory=False)
        d["timestamp"] = pd.to_datetime(d.timestamp).dt.normalize()
        d["expiry"] = pd.to_datetime(d.expiry).dt.normalize()
        d["strike"] = pd.to_numeric(d.strike, errors="coerce")
        d["close"] = pd.to_numeric(d.close, errors="coerce")
        d["option_type"] = d.option_type.astype(str).str.upper()
        d = d[(d.symbol.astype(str).str.upper() == "NIFTY") & d.option_type.isin(["CE", "PE"]) &
              d.strike.notna() & d.close.notna()]
        parts.append(d)
        y = p.name.split("_")[-1].split(".")[0]
        target_files.extend(Path(args.options_dir).rglob(f"targets_{y}.csv"))
    opt = pd.concat(parts, ignore_index=True)
    by_day = {k: g for k, g in opt.groupby("timestamp", sort=False)}

    targ_parts = []
    for p in sorted(set(target_files)):
        t = pd.read_csv(p)
        c = "target_expiry" if "target_expiry" in t.columns else "expiry"
        t["decision_date"] = pd.to_datetime(t.decision_date).dt.normalize()
        t["target_expiry"] = pd.to_datetime(t[c]).dt.normalize()
        targ_parts.append(t[["decision_date", "target_expiry"]])
    targ = pd.concat(targ_parts, ignore_index=True).drop_duplicates().sort_values("decision_date")

    rows = []
    decision_rows = []
    for i, t in enumerate(targ.itertuples(index=False)):
        decision, target_exp = t.decision_date, t.target_expiry
        spot, day = price.get(decision), by_day.get(decision)
        if spot is None or day is None:
            continue
        exps = sorted(pd.to_datetime(day.expiry.dropna().unique()))
        actual = [e for e in exps if e >= target_exp]
        if not actual:
            continue
        expiry = pd.Timestamp(actual[0]).normalize()
        sessions = idx[(idx.date > decision) & (idx.date <= expiry)]
        if sessions.empty:
            continue
        exp_session = sessions.iloc[-1].date.normalize()
        hist = idx.loc[idx.date <= decision, "logret"].dropna().tail(756).to_numpy()
        terminal = mc_terminal(float(spot), hist, len(sessions), args.paths, 100000 + i)
        if terminal is None:
            continue
        qs = np.percentile(terminal, [10, 20, 25, 35, 45, 55, 65, 75, 80, 90])
        targets = {
            "p10": qs[0], "p20": qs[1], "p25": qs[2], "p35": qs[3], "p45": qs[4],
            "atm": float(spot), "c55": qs[5], "c65": qs[6], "c75": qs[7], "c80": qs[8], "c90": qs[9]
        }
        strikes = unique_strikes(day.strike.dropna().unique(), targets)
        if strikes is None:
            continue
        chain = day[day.expiry == expiry]
        if chain.empty:
            continue
        feats = decision_features(idx, decision, terminal, float(spot))
        if feats is None:
            continue

        did = f"{decision.date()}|{expiry.date()}"
        realized_expiry_spot = price.get(exp_session)
        if realized_expiry_spot is None or not np.isfinite(realized_expiry_spot):
            continue
        decision_rows.append({
            "decision_id": did, "decision_date": decision, "actual_expiry": expiry,
            "expiry_session": exp_session, "spot": float(spot),
            "expiry_return": float(realized_expiry_spot / float(spot) - 1.0),
            **feats
        })

        for name in STRATEGY_NAMES:
            legs = build_strategy(name, strikes)
            priced, ok = [], True
            for leg in legs:
                if leg.expiry != "front":
                    ok = False
                    break
                px = option_price(chain, expiry, leg.option_type, leg.strike)
                if px is None:
                    ok = False
                    break
                priced.append((leg, px))
            if not ok:
                continue

            pnl_paths, entry = payoff_paths(terminal, priced)
            risk_p95 = max(1e-6, -float(np.quantile(pnl_paths, 0.05)))
            risk_p99 = max(1e-6, -float(np.quantile(pnl_paths, 0.01)))
            realized_spot = float(price[exp_session])
            realized = 0.0
            for leg, _ in priced:
                intrinsic = max(realized_spot - leg.strike, 0.0) if leg.option_type == "CE" else max(leg.strike - realized_spot, 0.0)
                realized += leg.qty * intrinsic
            realized_pnl = float(realized + entry)
            rows.append({
                "decision_id": did, "decision_date": decision.date(), "actual_expiry": expiry.date(),
                "expiry_session": exp_session.date(), "spot": float(spot), "strategy": name,
                "family": STRATEGY_META[name][1], "bias": STRATEGY_META[name][0], "n_legs": len(legs),
                "entry_cashflow": float(entry), "realized_pnl": realized_pnl, "win": int(realized_pnl > 0),
                "mc_ev": float(pnl_paths.mean()), "mc_pop": float(np.mean(pnl_paths > 0)),
                "mc_risk_p95": risk_p95, "mc_risk_p99": risk_p99,
                "realized_return_on_mc_risk": realized_pnl / risk_p95,
                "expiry_return": realized_spot / float(spot) - 1,
                "settlement": "expiry", **feats
            })

    trades = pd.DataFrame(rows)
    decisions = pd.DataFrame(decision_rows).drop_duplicates("decision_id").sort_values("decision_date")
    if trades.empty or decisions.empty:
        raise SystemExit("No strategy observations generated")

    trades["year"] = pd.to_datetime(trades.decision_date).dt.year
    decisions["year"] = pd.to_datetime(decisions.decision_date).dt.year
    dev_dec = decisions[decisions.year <= 2022].copy()

    decisions = classify_with_frozen_development(decisions, dev_dec)
    trades = trades.merge(decisions[["decision_id", "direction_prediction", "vol_regime", "regime", "trend_score"]],
                          on="decision_id", how="left")
    trades["period"] = np.select([trades.year <= 2022, trades.year <= 2024], ["development", "validation"], default="final")
    # Refresh the development trade frame after regime labels are merged.
    dev_trades = trades[trades.year <= 2022].copy()

    # Actual direction/expansion labels are for evaluation only.
    exp_q = dev_trades.expiry_return.abs().quantile(2/3)
    decisions["actual_direction"] = np.where(decisions.expiry_return >= 0.0, "bull", "bear")
    decisions["actual_expansion"] = np.where(decisions.expiry_return.abs() >= exp_q, "expansion", "normal")
    decisions["direction_correct"] = np.where(
        decisions.direction_prediction.isin(["bull", "bear"]),
        decisions.direction_prediction == decisions.actual_direction, np.nan
    )
    decisions["breakout_correct"] = np.where(
        decisions.direction_prediction == "breakout",
        decisions.expiry_return.abs() >= exp_q, np.nan
    )

    # Strategy-level report.
    summary = []
    for (period, strategy), g in trades.groupby(["period", "strategy"]):
        s = summarize(g)
        summary.append({
            "period": period, "strategy": strategy, **s,
            "mean_mc_ev": float(g.mc_ev.mean()), "mean_mc_pop": float(g.mc_pop.mean()),
            "mean_ror": float(g.realized_return_on_mc_risk.mean())
        })
    pd.DataFrame(summary).to_csv(out / "strategy_summary.csv", index=False)

    # Development-only risk-normalized router.
    mapping = []
    for regime, rg in dev_trades.groupby("regime"):
        for strategy, g in rg.groupby("strategy"):
            if len(g) < 20:
                continue
            x = g.realized_return_on_mc_risk.to_numpy(float)
            mean = float(np.mean(x))
            se = float(np.std(x, ddof=1) / np.sqrt(len(x)))
            mapping.append({
                "regime": regime, "strategy": strategy, "n": len(x),
                "mean_ror": mean, "win_rate": float(g.win.mean()),
                "mean_pnl": float(g.realized_pnl.mean()), "conservative_score": mean - se
            })
    ranking = pd.DataFrame(mapping).sort_values(["regime", "conservative_score"], ascending=[True, False])
    ranking.to_csv(out / "regime_strategy_ranking.csv", index=False)

    frozen_rows = []
    rank_map = {}
    for regime, g in ranking.groupby("regime"):
        gg = g[g.conservative_score > 0].sort_values("conservative_score", ascending=False)
        rank_map[regime] = gg.strategy.tolist()
        if not gg.empty:
            frozen_rows.append(gg.iloc[0])
    frozen = pd.DataFrame(frozen_rows)
    frozen.to_csv(out / "frozen_regime_router.csv", index=False)

    # Frozen router: one strategy per decision, otherwise NO TRADE.
    routed = []
    for period, frame in [("development", trades[trades.period == "development"]),
                          ("validation", trades[trades.period == "validation"]),
                          ("final", trades[trades.period == "final"])]:
        for did, dg in frame.groupby("decision_id", sort=False):
            regime = str(dg.iloc[0].regime)
            chosen = None
            for strategy in rank_map.get(regime, []):
                z = dg[dg.strategy == strategy]
                if not z.empty:
                    chosen = z.iloc[0]
                    break
            if chosen is None:
                routed.append({"period": period, "decision_id": did, "regime": regime,
                                "strategy": "NO_TRADE", "realized_pnl": 0.0, "mc_ev": np.nan,
                                "mc_pop": np.nan, "realized_return_on_mc_risk": 0.0})
            else:
                routed.append({"period": period, "decision_id": did, "regime": regime,
                                "strategy": chosen.strategy, "realized_pnl": float(chosen.realized_pnl),
                                "mc_ev": float(chosen.mc_ev), "mc_pop": float(chosen.mc_pop),
                                "realized_return_on_mc_risk": float(chosen.realized_return_on_mc_risk)})
    routed = pd.DataFrame(routed)
    routed.to_csv(out / "regime_router_trades.csv", index=False)

    router_summary = []
    for period, g in routed.groupby("period"):
        active = g[g.strategy != "NO_TRADE"]
        x = active.realized_pnl.to_numpy(float)
        eq = np.cumsum(x) if len(x) else np.array([])
        dd = eq - np.maximum.accumulate(eq) if len(eq) else np.array([0.0])
        router_summary.append({
            "period": period, "decisions": len(g), "trades": len(active),
            "coverage": len(active) / len(g), "win_rate": float(np.mean(x > 0)) if len(x) else np.nan,
            "mean_pnl_per_trade": float(np.mean(x)) if len(x) else np.nan,
            "total_pnl": float(np.sum(x)) if len(x) else 0.0,
            "max_drawdown": float(dd.min())
        })
    pd.DataFrame(router_summary).to_csv(out / "regime_router_summary.csv", index=False)

    # Prediction evaluation.
    pred_rows = []
    for period, mask in [("development", decisions.year <= 2022),
                         ("validation", decisions.year.between(2023, 2024)),
                         ("final", decisions.year >= 2025)]:
        d = decisions[mask].copy()
        directional = d[d.direction_prediction.isin(["bull", "bear"])]
        pred_rows.append({
            "period": period, "decisions": len(d),
            "bull_predictions": int((d.direction_prediction == "bull").sum()),
            "bear_predictions": int((d.direction_prediction == "bear").sum()),
            "range_predictions": int((d.direction_prediction == "neutral").sum()),
            "breakout_predictions": int((d.direction_prediction == "breakout").sum()),
            "direction_accuracy": float(directional.direction_correct.mean()) if len(directional) else np.nan,
            "breakout_accuracy": float(d[d.direction_prediction == "breakout"].breakout_correct.mean())
            if (d.direction_prediction == "breakout").any() else np.nan,
            "mean_abs_expiry_return": float(d.expiry_return.abs().mean())
        })
    pd.DataFrame(pred_rows).to_csv(out / "prediction_summary.csv", index=False)

    decisions.to_csv(out / "nifty_regime_predictions.csv", index=False)
    trades.to_csv(out / "strategy_trades.csv", index=False)

    lines = [
        "# NIFTY Multi-Strategy Regime Lab v2", "",
        f"- Strategies tested: {len(STRATEGY_NAMES)}",
        f"- Decision observations: {len(decisions)}",
        f"- Strategy observations: {len(trades)}",
        "- Development 2020-2022; validation 2023-2024; final 2025-2026.",
        "- Regime uses development-frozen trend ranks + volatility + MC expansion probability.",
        "- Router selection uses development-only MC-risk-normalized P&L; NO_TRADE is allowed.",
        "", "## Frozen router", ""
    ]
    for _, r in frozen.iterrows():
        lines.append(f"- {r.regime} -> {r.strategy} (n={int(r.n)}, mean RoR={r.mean_ror:.4f}, score={r.conservative_score:.4f})")
    lines += ["", "## Router summary", "", pd.DataFrame(router_summary).to_csv(index=False),
              "", "## Prediction summary", "", pd.DataFrame(pred_rows).to_csv(index=False)]
    (out / "strategy_regime_v2_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:80]))

if __name__ == "__main__":
    main()
