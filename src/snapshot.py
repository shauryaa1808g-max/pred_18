"""Descriptive market-structure snapshot as of the last row of data (all numbers computed; nothing here is a validated predictor)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import EPS, index_returns, load_bse, load_index, load_breadth, targets
from location import rsi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provisional", default=None)
    ap.add_argument("--out", default="results/snapshot.json")
    a = ap.parse_args()
    d = load_bse()
    if d.index[-1] < pd.Timestamp("2026-10-13") and a.provisional:
        o, h, l, c, v = [float(z) for z in a.provisional.split(",")]
        d = pd.concat([d, pd.DataFrame({"prev": [d.close.iloc[-1]], "open": [o], "high": [h], "low": [l], "close": [c], "vol": [v], "turnover_cr": [np.nan], "deliv_pct": [np.nan]}, index=[pd.Timestamp("2026-10-13")])])
    t = targets(d)
    adj = d["close"].copy()
    f = d["ca_factor"].fillna(1.0).values if "ca_factor" in d else np.ones(len(d))
    suffix = np.concatenate([np.cumprod(f[::-1])[::-1][1:], [1.0]])
    adj = d["close"] / suffix            # bonus-adjusted close (post-2025 basis)
    adjh, adjl = d["high"] / suffix, d["low"] / suffix
    px = float(adj.iloc[-1])
    out = {"asof": str(d.index[-1].date()), "close": px}
    for n in (5, 10, 20, 50, 100, 200):
        ma = adj.rolling(n).mean().iloc[-1]
        out[f"ma{n}"] = float(ma); out[f"close_vs_ma{n}_pct"] = float(100 * (px / ma - 1))
    out["rsi14"] = float(rsi(adj).iloc[-1])
    tr = pd.concat([adjh - adjl, (adjh - adj.shift()).abs(), (adjl - adj.shift()).abs()], axis=1).max(axis=1)
    out["atr14"] = float(tr.rolling(14).mean().iloc[-1]); out["atr14_pct"] = float(100 * out["atr14"] / px)
    for n in (5, 10, 20, 60, 120):
        out[f"ret_{n}d_pct"] = float(100 * (px / adj.iloc[-1 - n] - 1))
    w = adj.iloc[-252:]; hh, ll = float(adjh.iloc[-252:].max()), float(adjl.iloc[-252:].min())
    out.update({"hi_52w": hh, "hi_52w_date": str(adjh.iloc[-252:].idxmax().date()), "lo_52w": ll, "lo_52w_date": str(adjl.iloc[-252:].idxmin().date()),
                "pct_below_52w_high": float(100 * (px / hh - 1)), "pct_above_52w_low": float(100 * (px / ll - 1)), "pos_in_52w_range": float((px - ll) / (hh - ll))})
    lo1 = adj.loc["2026-10-01"]; out["pct_above_2026-10-01_close"] = float(100 * (px / lo1 - 1))
    R = t["R"]
    for n in (10, 20, 60, 250):
        out[f"realized_vol_{n}d_daily_pct"] = float(100 * R.iloc[-n:].std())
    out["realized_vol_20d_annualised_pct"] = float(100 * R.iloc[-20:].std() * np.sqrt(252))
    out["gk_vol_20d_daily_pct"] = float(100 * np.sqrt(t["gk"].iloc[-20:].mean()))
    out["avg_abs_gap_20d_pct"] = float(100 * t["G"].iloc[-20:].abs().mean()); out["avg_range_20d_pct"] = float(100 * (np.exp(t["rho"].iloc[-20:]) - 1).mean())
    out["days_abs_ret_gt3pct_last50"] = int((R.iloc[-50:].abs() > np.log(1.03)).sum())
    out["drawdown_from_2026_high_close_pct"] = float(100 * (px / adj.loc["2026-01-01":].max() - 1))
    # volume / delivery
    vol = d["vol"] / suffix                                   # share-count basis post-bonus
    out["rel_volume_vs_20d"] = float(vol.iloc[-1] / vol.iloc[-21:-1].mean())
    out["rel_volume_vs_60d"] = float(vol.iloc[-1] / vol.iloc[-61:-1].mean())
    dv = d["deliv_pct"].dropna()
    out["delivery_pct_last"] = float(dv.iloc[-1]) if len(dv) else None
    out["delivery_pct_mean_60d"] = float(dv.iloc[-60:].mean()) if len(dv) else None
    out["vwap_proxy_last_day"] = float((d["turnover_cr"].iloc[-1] * 1e7) / d["vol"].iloc[-1]) if np.isfinite(d["turnover_cr"].iloc[-1]) else None
    # relative strength vs Nifty / capital-markets index / peers
    ix = load_index().reindex(d.index)
    ir = index_returns(ix)
    for name, col in (("nifty50", "nifty50_close"), ("capmkts", "capmkts_close"), ("finserv", "finserv_close")):
        s = ix[col]
        for n in (5, 20, 60):
            if s.iloc[-1 - n:].notna().all():
                out[f"rs_{n}d_vs_{name}_pct"] = float(100 * ((px / adj.iloc[-1 - n]) / (s.iloc[-1] / s.iloc[-1 - n]) - 1))
    nr = ir["r_nifty50"]
    for n in (60, 120, 250):
        x, y = nr.iloc[-n:], R.iloc[-n:]
        m = x.notna() & y.notna()
        out[f"beta_nifty_{n}d"] = float(np.cov(x[m], y[m])[0, 1] / x[m].var()); out[f"corr_nifty_{n}d"] = float(np.corrcoef(x[m], y[m])[0, 1])
    pe = pd.read_csv("data/processed/peers_daily.csv", parse_dates=["date"])
    pr = {}
    for s_ in ("CDSL", "MCX", "ANGELONE", "NUVAMA", "CAMS", "KFINTECH"):
        g = pe[pe.symbol == s_].set_index("date").sort_index()
        if len(g) > 61 and g.index[-1] == pe.date.max():
            r = np.log(g["close"] / g["prev"])        # raw prev may be unadjusted on ex-dates: clip obvious corporate-action days
            r = r.where(r.abs() < 0.4)
            pr[s_] = {"1d_pct": float(100 * (np.exp(r.iloc[-1]) - 1)), "20d_pct": float(100 * (np.exp(r.iloc[-20:].sum()) - 1)), "corr60_with_BSE": float(np.corrcoef(r.iloc[-60:].fillna(0), R.reindex(r.index).iloc[-60:].fillna(0))[0, 1]) if len(r) >= 60 else None}
    out["peers"] = pr
    # support / resistance zones from volume-by-price (last 120 sessions) and swing pivots (descriptive; untested as predictors)
    h120 = adj.iloc[-120:]; v120 = vol.iloc[-120:]
    bins = np.linspace(h120.min(), h120.max(), 25)
    hist, edges = np.histogram(h120, bins=bins, weights=v120)
    top = np.argsort(hist)[::-1][:4]
    out["volume_nodes_120d"] = [{"lo": float(edges[i]), "hi": float(edges[i + 1]), "share_of_volume": float(hist[i] / hist.sum())} for i in sorted(top)]
    piv = []
    ah, al = adjh.iloc[-160:], adjl.iloc[-160:]
    for i in range(5, len(ah) - 5):
        if ah.iloc[i] == ah.iloc[i - 5:i + 6].max():
            piv.append(("swing_high", str(ah.index[i].date()), float(ah.iloc[i])))
        if al.iloc[i] == al.iloc[i - 5:i + 6].min():
            piv.append(("swing_low", str(al.index[i].date()), float(al.iloc[i])))
    out["swing_pivots_last160"] = piv
    out["last5_bars"] = d[["open", "high", "low", "close", "vol"]].tail(5).round(2).rename_axis("date").reset_index().assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
    # options structure from F&O end-of-day (latest available)
    import glob
    fo = sorted(glob.glob("data/raw/fo_bse/*.csv"))[-1]
    df = pd.read_csv(fo); asof = pd.Timestamp(Path(fo).stem)
    df["XpryDt"] = pd.to_datetime(df["XpryDt"])
    o = df[df.FinInstrmTp == "STO"]; fu = df[df.FinInstrmTp == "STF"]
    e1 = sorted(o.XpryDt.unique())[0]
    oc = o[o.XpryDt == e1]
    out["fo_asof"] = str(asof.date()); out["fo_near_expiry"] = str(e1.date())
    out["pcr_oi_near_expiry"] = float(oc[oc.OptnTp == "PE"].OpnIntrst.sum() / oc[oc.OptnTp == "CE"].OpnIntrst.sum())
    out["pcr_volume_near_expiry"] = float(oc[oc.OptnTp == "PE"].TtlTradgVol.sum() / max(1, oc[oc.OptnTp == "CE"].TtlTradgVol.sum()))
    oi_by_k = oc.groupby(["StrkPric", "OptnTp"]).OpnIntrst.sum().unstack().fillna(0)
    out["max_oi_call_strike"] = float(oi_by_k["CE"].idxmax()); out["max_oi_put_strike"] = float(oi_by_k["PE"].idxmax())
    out["fut_oi"] = fu[["XpryDt", "OpnIntrst", "ChngInOpnIntrst", "SttlmPric"]].assign(XpryDt=lambda x: x.XpryDt.dt.strftime("%Y-%m-%d")).to_dict(orient="records")
    ivdf = pd.read_csv("data/processed/bse_iv_daily.csv", parse_dates=["date"]).set_index("date")
    out["iv_atm_last"] = float(ivdf.iv_atm.iloc[-1]); out["iv_atm_percentile_in_history"] = float((ivdf.iv_atm <= ivdf.iv_atm.iloc[-1]).mean())
    out["iv_atm_20d_mean"] = float(ivdf.iv_atm.iloc[-20:].mean()); out["realized_vol_20d_ann_vs_iv"] = out["realized_vol_20d_annualised_pct"] / (100 * out["iv_atm_last"])
    # skew: IV of 5%-OTM put vs 5%-OTM call
    from options_iv import implied_vol
    F = float(fu[fu.XpryDt == e1].SttlmPric.iloc[0]); T = (e1 - asof).days / 365.0
    def iv_k(K, cp):
        r = oc[(oc.StrkPric == K) & (oc.OptnTp == cp)]
        return implied_vol(float(r.SttlmPric.iloc[0]), F, K, T, cp) if len(r) else np.nan
    ks = np.array(sorted(oc.StrkPric.unique()))
    kp, kc = ks[np.argmin(np.abs(ks - 0.95 * F))], ks[np.argmin(np.abs(ks - 1.05 * F))]
    out["skew_5pct_otm"] = {"put_strike": float(kp), "put_iv": iv_k(kp, "PE"), "call_strike": float(kc), "call_iv": iv_k(kc, "CE")}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    keys = ["close", "ma20", "ma50", "ma100", "ma200", "close_vs_ma20_pct", "close_vs_ma50_pct", "close_vs_ma200_pct", "rsi14", "atr14", "atr14_pct", "ret_5d_pct", "ret_20d_pct", "ret_60d_pct", "pct_below_52w_high", "pct_above_52w_low", "pos_in_52w_range",
            "realized_vol_20d_daily_pct", "realized_vol_60d_daily_pct", "realized_vol_250d_daily_pct", "gk_vol_20d_daily_pct", "avg_range_20d_pct", "avg_abs_gap_20d_pct", "days_abs_ret_gt3pct_last50", "rel_volume_vs_20d", "rel_volume_vs_60d",
            "delivery_pct_last", "delivery_pct_mean_60d", "rs_20d_vs_nifty50_pct", "rs_20d_vs_capmkts_pct", "rs_60d_vs_nifty50_pct", "beta_nifty_60d", "corr_nifty_60d", "beta_nifty_250d", "corr_nifty_250d",
            "pcr_oi_near_expiry", "max_oi_call_strike", "max_oi_put_strike", "iv_atm_last", "iv_atm_percentile_in_history", "iv_atm_20d_mean", "realized_vol_20d_ann_vs_iv", "skew_5pct_otm"]
    for k in keys:
        if k in out:
            print(f"{k:34s} {out[k]}")
    print("volume nodes:", [(round(z['lo']), round(z['hi']), round(z['share_of_volume'], 3)) for z in out["volume_nodes_120d"]])
    print("recent pivots:", piv[-8:])
    print("peers:", json.dumps(pr))


if __name__ == "__main__":
    main()
