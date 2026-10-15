"""Day-ahead and post-open forecasts of the session HIGH and LOW of NSE:BSE (specialist A of the H/L study; report research/hl/A_dayahead.md).

PRE-OPEN  (information up to the previous official close P0):   Hp = ln(H/P0), Lp = ln(L/P0)
    quantiles = sigma_t x trailing-500 standardised residuals of (Hp, Lp)    -- the project's OHLC bootstrap (src/eval_hl.py); sigma = S6 of the close-to-close return R
POST-OPEN (plus the official open O, final at 09:08 IST from the NSE pre-open auction):   HO = ln(H/O) >= 0, LO = ln(L/O) <= 0
    quantiles = sigma_t^I x trailing-500 standardised residuals of (HO, LO)  -- sigma = S6 of the open-to-close return I; the bootstrap respects HO >= 0, LO <= 0
Both were walk-forward evaluated against simple benchmarks (python3 src/hl_model.py --eval -> results/hl_eval_*.csv).  The median is the 'pin-point'; the typical miss printed beside it is its out-of-sample mean absolute error.

Usage (repo root; python3 src/hl_model.py ...):
  --date 2026-10-16 [--open 3440.0] [--p0 3428.0] [--json] [--save]      plain words (or JSON); only sessions BEFORE --date are used (--save writes results/hl_dayahead_<date>.json)
  --eval [--hourly PATH]                                                  full walk-forward evaluation and all tables (about 30 s); PATH = Yahoo 1h chart JSON for the Yahoo-vs-NSE check
  --selftest                                                              same-row leakage tests (about 1 min);  --replicate: reproduce the project's Final 90.2% / 88.6% H/L coverage
Importable: hl_forecast(date, open_price=None, p0=None) -> dict.   No network access is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import metrics as M
import models as P
from common import EPS, GRID, load_bse, targets

EXTRA, UNION15, EXTRA15 = Path("data/processed/bse_daily_extra.csv"), "data/processed/intraday_union_15m.csv", "data/processed/intraday_extra_15m.csv"
OUT = Path("results")
START, W, W_POOL, MIN_POOL = 750, 500, 1000, 30           # first evaluated session (as eval_hl), bootstrap window, window for pooled variants, minimum pool size
P_NOW = 3428.0                                             # official close 15-Oct-2026: rupee conversions of log errors
LV = {"q5": 1, "q10": 2, "q25": 3, "q50": 4, "q75": 5, "q90": 6, "q95": 7}      # positions in common.GRID of the requested quantiles
WIN = {"dev": ("2000-01-01", "2024-06-30"), "val": ("2024-07-01", "2025-06-30"), "valfinal": ("2024-07-01", "2099-01-01"), "final": ("2025-07-01", "2099-01-01"),
       "final_to_1012": ("2025-07-01", "2026-10-12"), "cas": ("2026-08-03", "2099-01-01"), "cas_from_0804": ("2026-08-04", "2099-01-01")}
LIVE_PRE, LIVE_POST = "P_S6", "W_I6"                       # models used by hl_forecast (chosen by the adoption rule in the report)


# ----------------------------------------------------------------------------------------------- data and sigma paths
def load_ohlc(before=None) -> pd.DataFrame:
    """Official daily bars: the processed file (its previous close is bonus-adjusted, its OHLC levels are raw traded prices) plus the extra official bars (14-15 Oct); optionally only sessions before a date."""
    d = load_bse()
    if EXTRA.exists():
        e = pd.read_csv(EXTRA, index_col=0, parse_dates=True)
        d = pd.concat([d, e[~e.index.isin(d.index)].reindex(columns=d.columns)]).sort_index()
    ok = (d["high"] >= d[["open", "close"]].max(axis=1) - 1e-9) & (d["low"] <= d[["open", "close"]].min(axis=1) + 1e-9) & (d["high"] >= d["low"])
    if not ok.all():
        raise ValueError(f"bad OHLC rows: {d.index[~ok].tolist()[:5]}")
    return d if before is None else d[d.index < pd.Timestamp(before)]


def pad(s) -> np.ndarray:
    return np.r_[np.full(P.MIN_HIST, np.nan), s]


def wf_sigmas(x, v, models=("S0", "S1", "S4", "S6")) -> dict:
    """Walk-forward sigma paths (models.run_scale_models: refit every 20 sessions on data strictly before the block), padded to the series length."""
    return {m: pad(s) for m, s in P.run_scale_models(x, v, None, models=models).sigma.items()}


def har_path(v, extra=None) -> np.ndarray:
    """Walk-forward HAR sigma (as S4) for any variance proxy v; extra columns are used exactly as given (the caller dates them)."""
    n, s = len(v), np.full(len(v), np.nan)
    for b0 in range(P.MIN_HIST, n, P.REFIT):
        s[b0:b0 + P.REFIT] = P.sigma_har_block(v, b0, extra)[b0:b0 + P.REFIT]
    return s


def s6_next(x, v) -> float:
    """S6 scale of the unseen session n, parameters fitted on all n known values (as forecast_live.live_sigma)."""
    n, xe, ve = len(x), np.append(x, 0.0), np.append(v, EPS)
    g, _, ok = P.sigma_garch_block(xe, n, False, None)
    if not ok:
        print("WARNING: GARCH fit failed; EWMA fallback inside S6")
    return float(np.sqrt(g[n] * P.sigma_har_block(ve, n)[n]))


def gap_bins(g, s1):
    """Gap in units of the EWMA scale: z (size, capped at 4) and bin ids. 5 bins: 0 flat (|z|<.25) 1 up-small 2 up-large 3 down-small 4 down-large; size: 0 flat 1 small 2 large; sign: 0 flat 1 up 2 down."""
    zs = g / s1
    a = np.abs(zs)
    size = np.where(a < 0.25, 0, np.where(a < 1.0, 1, 2))
    sign = np.where(a < 0.25, 0, np.where(zs > 0, 1, 2))
    b5 = np.where(size == 0, 0, np.where(zs > 0, size, size + 2))
    return np.minimum(a, 4.0), size, sign, b5


# ----------------------------------------------------------------------------------------------- quantile engines
def fhs_draws(V, sig, t, window=W, pool=None) -> np.ndarray:
    """sigma_t x standardised residuals V_s/sigma_s of the trailing window (s < t); pool = bin ids to split on (same bin as day t; unsplit if fewer than MIN_POOL)."""
    lo = max(0, t - window)
    u = V[lo:t] / sig[lo:t, None]
    ok = np.isfinite(u).all(axis=1)
    if pool is not None and (ok & (pool[lo:t] == pool[t])).sum() >= MIN_POOL:
        ok &= pool[lo:t] == pool[t]
    return sig[t] * u[ok]


def fhs_q(V, sig, t, window=W, pool=None) -> np.ndarray:
    """[n_cols, len(GRID)] quantiles."""
    return np.quantile(fhs_draws(V, sig, t, window, pool), GRID, axis=0).T


def emp_q(V, t, window) -> np.ndarray:
    return np.quantile(V[t - window:t], GRID, axis=0).T


# ----------------------------------------------------------------------------------------------- statistics helpers
def holm(p) -> np.ndarray:
    p = np.asarray(p, float)
    adj, run = np.empty(len(p)), 0.0
    for r, i in enumerate(np.argsort(p)):
        run = max(run, min(1.0, (len(p) - r) * p[i]))
        adj[i] = run
    return adj


def dm(loss_var, loss_base):
    """Diebold-Mariano (src/metrics.py): positive mean => variant better than baseline.  Returns mean diff, t, one-sided p (variant better), two-sided p."""
    md, t, p1 = M.diebold_mariano(loss_var, loss_base)
    return md, t, p1, (2 * min(p1, 1 - p1) if np.isfinite(p1) else np.nan)


def score_rows(name, Q, Y, ref, hl, dts, tgt_names):
    """Metrics per window for one variant. Q [n,2,9], Y [n,2], ref = reference price per day (P0 or O), hl = true (H, L) price [n,2]."""
    rows = []
    for j, tn in enumerate(tgt_names):
        for w, (a, b) in WIN.items():
            m = (dts >= a) & (dts <= b)
            if m.sum() < 5:
                continue
            q, y = Q[m, j, :], Y[m, j]
            pl = M.pinball(y, q)
            c50, h50 = M.coverage(y, q, 0.5)
            c90, h90 = M.coverage(y, q, 0.9)
            e = np.abs(y - q[:, LV["q50"]])
            tr = np.abs(hl[m, j] - ref[m] * np.exp(q[:, LV["q50"]]))
            rows.append(dict(variant=name, target=tn, window=w, n=int(m.sum()), pinball_x1e4=1e4 * pl.mean(), pinball_rs_at_now=P_NOW * pl.mean(), cov50=c50, cov90=c90,
                             kupiec50=M.kupiec(h50, 0.5), kupiec90=M.kupiec(h90, 0.9), below_q5=float((y < q[:, LV["q5"]]).mean()), above_q95=float((y > q[:, LV["q95"]]).mean()),
                             p_below_q5=stats.binomtest(int((y < q[:, LV["q5"]]).sum()), int(m.sum()), 0.05).pvalue, p_above_q95=stats.binomtest(int((y > q[:, LV["q95"]]).sum()), int(m.sum()), 0.05).pvalue, share_y_zero=float((np.abs(y) < 1e-12).mean()),
                             mae_med_pct=100 * e.mean(), medae_med_pct=100 * np.median(e), mae_med_rs_at_now=P_NOW * e.mean(), mae_med_se_rs_at_now=P_NOW * e.std(ddof=1) / np.sqrt(len(e)), medae_med_rs_at_now=P_NOW * np.median(e),
                             cov90_wilson_lo=M.wilson(int(h90.sum()), int(m.sum()))[0], cov90_wilson_hi=M.wilson(int(h90.sum()), int(m.sum()))[1],
                             mae_med_rs_traded=tr.mean() if w in ("final", "cas", "final_to_1012", "cas_from_0804") else np.nan,
                             medae_med_rs_traded=np.median(tr) if w in ("final", "cas", "final_to_1012", "cas_from_0804") else np.nan))
    return rows


def dm_family(fam, base, variants, L, tgt_names, dts, windows=("valfinal", "val", "final", "cas")):
    """DM of every variant against the baseline, per window; Holm within (family, window)."""
    rows = []
    for w in windows:
        a, b = WIN[w]
        m = (dts >= a) & (dts <= b)
        blk = []
        for v in variants:
            for j, tn in enumerate(tgt_names):
                md, t, p1, p2 = dm(L[v][j][m], L[base][j][m])
                blk.append(dict(family=fam, window=w, variant=v, baseline=base, target=tn, n=int(m.sum()), mean_pinball_var_x1e4=1e4 * L[v][j][m].mean(),
                                mean_pinball_base_x1e4=1e4 * L[base][j][m].mean(), gain_x1e4=1e4 * md, gain_pct=100 * md / L[base][j][m].mean(), dm_t=t, p_variant_better=p1, p_two_sided=p2))
        h = holm([r["p_two_sided"] for r in blk]) if w != "cas" else [np.nan] * len(blk)
        for r, hp in zip(blk, h):
            rows.append({**r, "holm_two_sided": hp})
    return rows


# ----------------------------------------------------------------------------------------------- live forecast
def _side(variant, target, ref, q):
    """Rupee quantiles of one side, the same as % of the reference, band widths, and the out-of-sample typical miss of its median (mean and median absolute error) from results/hl_eval_{pre,post}open.csv."""
    px = {**{k: round(float(ref * np.exp(q[g])), 2) for k, g in LV.items()}, "q2.5": round(float(ref * np.exp(q[0])), 2), "q97.5": round(float(ref * np.exp(q[8])), 2)}
    out = {"price_quantiles": px, "pct_of_reference": {k: round(100 * float(np.exp(q[g]) - 1), 2) for k, g in LV.items()},
           "band_width_rs": {"50%": round(px["q75"] - px["q25"], 1), "90%": round(px["q95"] - px["q5"], 1)}}
    f = OUT / ("hl_eval_preopen.csv" if variant.startswith("P_") else "hl_eval_postopen.csv")
    r = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["variant", "target", "window"])
    for w, key in (("final", ""), ("cas", "_cas_slice")):
        x = r[(r.variant == variant) & (r.target == target) & (r.window == w)]
        if not x.empty:
            out.update({f"typical_miss_rs{key}": round(float(x.mae_med_pct.iloc[0]) / 100 * ref, 1), f"half_the_time_within_rs{key}": round(float(x.medae_med_pct.iloc[0]) / 100 * ref, 1), f"miss_measured_on_sessions{key}": int(x.n.iloc[0])})
            if w == "cas" and variant.startswith("P_"):          # tail check in the closing-auction era (for HO / LO the lower tail is an atom at zero, so only the pre-open version is flagged)
                out["cas_slice_tail_shares"] = {"n": int(x.n.iloc[0]), "below_q5": float(x.below_q5.iloc[0]), "above_q95": float(x.above_q95.iloc[0])}
    return out


def hl_forecast(date, open_price=None, p0=None, d=None, examples=False) -> dict:
    """Forecast of the session high / low on `date` using only sessions before it (and `open_price` = official open, if given; examples=True adds post-open tables for opens of -2..+2% vs P0).  Returns a dict."""
    date = pd.Timestamp(date)
    d = load_ohlc(date) if d is None else d[d.index < date]
    n, t = len(d), targets(d)
    P0 = float(d["close"].iloc[-1]) if p0 is None else float(p0)
    if open_price is not None and abs(np.log(open_price / P0)) > 0.2:
        raise ValueError("open more than 20% from the previous close: check the number")
    missing = [str(x.date()) for x in pd.bdate_range(d.index[-1] + pd.Timedelta(days=1), date - pd.Timedelta(days=1))]
    R, v, I, gk = t["R"].values, t["v"].values, t["I"].values, t["gk"].values
    sig = np.r_[wf_sigmas(R, v, ("S6",))["S6"], s6_next(R, v)]                 # walk-forward S6 for sessions < n, parameters fitted on all n sessions for session n
    Vp, last = t[["Hp", "Lp"]].values, str(d.index[-1].date())
    qh, dr = fhs_q(Vp, sig, n), fhs_draws(Vp, sig, n)
    out = {"date": str(date.date()), "p0": P0, "data_through": last, "n_sessions": n, "missing_weekdays_between_data_and_date": missing, "is_weekend": bool(date.dayofweek >= 5),
           "data_sha256": {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ("data/processed/bse_daily.csv", str(EXTRA)) if Path(f).exists()},
           "model_pre": f"S6 sigma (GARCH(1,1)-t x HAR on gap^2+Garman-Klass) of the close-to-close return x trailing-500 standardised (Hp, Lp) residuals; fitted with sessions through {last} only",
           "sigma_R_pct": 100 * float(sig[n]), "pre_open": {"high": _side(LIVE_PRE, "H", P0, qh[0]), "low": _side(LIVE_PRE, "L", P0, qh[1])}}
    out["pre_open"]["touch_prob"] = {f"high >= P0+{c:g}%": round(float((dr[:, 0] >= np.log1p(c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)} | {f"low <= P0-{c:g}%": round(float((dr[:, 1] <= np.log1p(-c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)}
    if open_price is not None or examples:
        sI = np.r_[wf_sigmas(I, gk, ("S6",))["S6"], s6_next(I, gk)]
        Vq = t[["HO", "LO"]].values
        qo, dro = fhs_q(Vq, sI, n), fhs_draws(Vq, sI, n)
        out["model_post"] = f"S6 sigma of the open-to-close return x trailing-500 standardised (HO, LO) residuals (HO >= 0, LO <= 0 by construction); the open sets the reference level only; fitted with sessions through {last} only"
        out["sigma_I_pct"] = 100 * float(sI[n])
        tp = {f"high >= open+{c:g}%": round(float((dro[:, 0] >= np.log1p(c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)} | {f"low <= open-{c:g}%": round(float((dro[:, 1] <= np.log1p(-c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)}
        post = lambda O: {"open": float(O), "gap_pct": 100 * float(np.log(O / P0)), "high": _side(LIVE_POST, "HO", float(O), qo[0]), "low": _side(LIVE_POST, "LO", float(O), qo[1]), "touch_prob": tp}      # noqa: E731
        if open_price is not None:
            out["gap_pct"], out["open"], out["post_open"] = 100 * float(np.log(open_price / P0)), float(open_price), post(open_price)
        if examples:
            out["post_open_examples"] = {f"open {x:+g}% vs previous close": post(P0 * (1 + x / 100)) for x in (-2, -1, 0, 1, 2)}
    return out


def words(o: dict) -> str:
    day = pd.Timestamp(o["date"]).strftime("%a %d %b %Y")
    L = [f"BSE Ltd (NSE: BSE), session of {day}.  Reference: official close Rs {o['p0']:,.1f} of {o['data_through']}.  Volatility model fitted with sessions through {o['data_through']} only (typical daily move sigma = {o['sigma_R_pct']:.2f}%)."]
    if o["is_weekend"]:
        L.append("WARNING: this date is a weekend; the forecast is for the next trading session after the data.")
    if o["missing_weekdays_between_data_and_date"]:
        L.append(f"WARNING: no official bar for {o['missing_weekdays_between_data_and_date']} between the data and this date: a holiday, or the data are stale; the forecast is for the NEXT session after the data.")
    def side(blk):
        out = []
        for k, nm in (("high", "HIGH"), ("low", "LOW ")):
            b, q = blk[k], blk[k]["price_quantiles"]
            miss = f"  Typical miss about Rs {b['typical_miss_rs']:,.0f} (half the time within Rs {b['half_the_time_within_rs']:,.0f}), measured out of sample on the last {b['miss_measured_on_sessions']} sessions." if "typical_miss_rs" in b else ""
            out.append(f"  {nm}: best single guess Rs {q['q50']:,.0f}.{miss}\n        Half the time between Rs {q['q25']:,.0f} and {q['q75']:,.0f} (band Rs {b['band_width_rs']['50%']:,.0f} wide); nine times in ten between Rs {q['q5']:,.0f} and {q['q95']:,.0f} (band Rs {b['band_width_rs']['90%']:,.0f} wide).")
            c = b.get("cas_slice_tail_shares")
            if c and max(c["below_q5"], c["above_q95"]) > 0.10:
                out.append(f"        Caution (small sample, suggestive): since the closing auction began ({c['n']} sessions) the actual {nm.strip().lower()} fell below this band's 5% level on {100*c['below_q5']:.0f}% and above its 95% level on {100*c['above_q95']:.0f}% of days (5% each expected).")
        return "\n".join(out)
    L.append("BEFORE THE OPEN (information to the previous close only):\n" + side(o["pre_open"]))
    tp = o["pre_open"]["touch_prob"]
    L.append("  Chance the high reaches +1% / +2% above the previous close: " + f"{100*tp['high >= P0+1%']:.0f}% / {100*tp['high >= P0+2%']:.0f}%; the low reaches -1% / -2% below it: {100*tp['low <= P0-1%']:.0f}% / {100*tp['low <= P0-2%']:.0f}%.")
    if "post_open" in o:
        po = o["post_open"]
        L.append(f"AFTER THE OPEN (official open Rs {po['open']:,.1f}, gap {po['gap_pct']:+.2f}% vs the previous close; the high is at least the open and the low at most the open):\n" + side(po))
        tp = po["touch_prob"]
        L.append("  Chance the high gets +1% / +2% above the open: " + f"{100*tp['high >= open+1%']:.0f}% / {100*tp['high >= open+2%']:.0f}%; the low gets -1% / -2% below it: {100*tp['low <= open-1%']:.0f}% / {100*tp['low <= open-2%']:.0f}%.")
    L.append("Honest limits: ranges, not a direction call; the gap size and direction did not improve the after-open bands in tests (they only set the level); the targets are the NSE official high/low (Yahoo / chart extremes differ by a few rupees); see research/hl/A_dayahead.md.")
    return "\n".join(L)


# ----------------------------------------------------------------------------------------------- evaluation
def build(d: pd.DataFrame):
    """All walk-forward quantile forecasts for sessions START..n-1: pre-open Qp (Hp, Lp) and post-open Qo (HO, LO), each [n_eval, 2, 9], plus the sigma paths and gap bins."""
    t, n = targets(d), len(d); idx = np.arange(START, n)
    R, v, I, gk, G = t["R"].values, t["v"].values, t["I"].values, t["gk"].values, t["G"].values
    Vp, Vq = t[["Hp", "Lp"]].values, t[["HO", "LO"]].values
    run = lambda f: np.array([f(i) for i in idx])                                                       # noqa: E731
    sg = wf_sigmas(R, v)                                                                               # S0 S1 S4 S6 for R
    sg["RNG"] = har_path(np.clip(t["rho"].values ** 2, EPS, None)); sg["GK"] = har_path(gk)
    sI6 = wf_sigmas(I, gk, ("S6",))["S6"]
    z, size, sign, b5 = gap_bins(G, P.sigma_ewma(R))                                                   # z_t known at 09:08 of day t; the EWMA scale uses R to t-1
    sg["HARz"] = har_path(gk, z[:, None])
    Qp = {"P_EMP250": run(lambda i: emp_q(Vp, i, 250)), "P_EMP500": run(lambda i: emp_q(Vp, i, 500))}
    for nm, s in (("P_S0", sg["S0"]), ("P_S1", sg["S1"]), ("P_S4", sg["S4"]), ("P_S6", sg["S6"]), ("P_RNG", sg["RNG"]), ("P_GK", sg["GK"])):
        Qp[nm] = run(lambda i, s=s: fhs_q(Vp, s, i))
    Qo = {"W_EMP250": run(lambda i: emp_q(Vq, i, 250)), "W_EMP500": run(lambda i: emp_q(Vq, i, 500)), "W_I6": run(lambda i: fhs_q(Vq, sI6, i)),
          "W_I6w": run(lambda i: fhs_q(Vq, sI6, i, W_POOL)), "W_HAR": run(lambda i: fhs_q(Vq, sg["GK"], i)), "W_HARz": run(lambda i: fhs_q(Vq, sg["HARz"], i))}
    for nm, b in (("W_SIZE", size), ("W_SIGN", sign), ("W_SZSG", b5)):
        Qo[nm] = run(lambda i, b=b: fhs_q(Vq, sI6, i, W_POOL, pool=b))
    Qo["W_PRE"] = np.stack([np.maximum(Qp["P_S6"][:, 0, :] - G[idx][:, None], 0), np.minimum(Qp["P_S6"][:, 1, :] - G[idx][:, None], 0)], axis=1)   # pre-open P_S6 shifted to the open, clipped at the constraints
    return Qp, Qo, dict(sg=sg, sI6=sI6, size=size, sign=sign, b5=b5, run=run)


def evaluate(hourly=None):
    OUT.mkdir(exist_ok=True)
    d = load_ohlc(); t = targets(d); n = len(d); idx = np.arange(START, n); dts = d.index[idx]
    G, Vp, Vq = t["G"].values, t[["Hp", "Lp"]].values, t[["HO", "LO"]].values
    print(f"sessions {n} ({d.index[0].date()} -> {d.index[-1].date()}); evaluated {len(idx)} ({dts[0].date()} -> {dts[-1].date()})")
    Qp, Qo, aux = build(d); sg, sI6, size, sign, b5 = aux["sg"], aux["sI6"], aux["size"], aux["sign"], aux["b5"]
    # ---- day-of-week screen (Development + Validation sessions only); the P_DOW variant is built only if it passes (Holm p < 0.05)
    dow = d.index.dayofweek.values
    scr = (dts <= pd.Timestamp("2025-06-30")) & (dow[idx] < 5)
    stat = {"ln(rho/sigma_S6)": np.log(t["rho"].values[idx] / sg["S6"][idx]), "Hp/sigma_S6": Vp[idx, 0] / sg["S6"][idx], "Lp/sigma_S6": Vp[idx, 1] / sg["S6"][idx]}
    pv = [stats.kruskal(*[x[scr & (dow[idx] == k)] for k in range(5)]).pvalue for x in stat.values()]
    dsc = pd.DataFrame({"statistic": list(stat), "kruskal_p": pv, "holm_p": holm(pv)} | {f"mean_{nm}": [float(x[scr & (dow[idx] == k)].mean()) for x in stat.values()] for k, nm in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"])})
    dsc["n"] = int(scr.sum()); dsc.to_csv(OUT / "hl_eval_dow_screen.csv", index=False); print("\nday-of-week screen (Dev+Val):\n", dsc.round(4).to_string(index=False))
    if (dsc.holm_p < 0.05).any():
        Qp["P_DOW"] = aux["run"](lambda i: fhs_q(Vp, sg["S6"], i, pool=dow))
    nfb = {nm: int(sum(((pool[max(0, i - W_POOL):i] == pool[i]).sum() < MIN_POOL) for i in idx)) for nm, pool in (("W_SIZE", size), ("W_SIGN", sign), ("W_SZSG", b5))}
    print("pool fallbacks (days with < 30 draws in the day's bin):", nfb)
    Yp, Yq = Vp[idx], Vq[idx]; P0, O = d["prev"].values[idx], d["open"].values[idx]; hl = d[["high", "low"]].values[idx]
    rows_p = [r for nm, q in Qp.items() for r in score_rows(nm, q, Yp, P0, hl, dts, ["H", "L"])]
    rows_o = [r for nm, q in Qo.items() for r in score_rows(nm, q, Yq, O, hl, dts, ["HO", "LO"])]
    # point benchmarks: price stays (H=L=P0), open stays (H=L=O)
    for nm, Y, ref, rows, tn in (("PRICE_STAYS", Yp, P0, rows_p, ["H", "L"]), ("OPEN_STAYS", Yq, O, rows_o, ["HO", "LO"])):
        for r in score_rows(nm, np.zeros((len(idx), 2, len(GRID))), Y, ref, hl, dts, tn):          # point forecast only: only the miss columns mean anything
            rows.append({k: (np.nan if k in ("pinball_x1e4", "pinball_rs_at_now", "cov50", "cov90", "cov90_wilson_lo", "cov90_wilson_hi", "kupiec50", "kupiec90", "below_q5", "above_q95", "p_below_q5", "p_above_q95") else x) for k, x in r.items()})
    rp, ro = pd.DataFrame(rows_p), pd.DataFrame(rows_o)
    rp.to_csv(OUT / "hl_eval_preopen.csv", index=False); ro.to_csv(OUT / "hl_eval_postopen.csv", index=False)
    # ---- DM + Holm families
    Lp_ = {k: [M.pinball(Yp[:, j], q[:, j, :]) for j in range(2)] for k, q in Qp.items()}
    Lo_ = {k: [M.pinball(Yq[:, j], q[:, j, :]) for j in range(2)] for k, q in Qo.items()}
    fam1 = dm_family("F1_pre_vs_P_S6", "P_S6", [k for k in Qp if k != "P_S6"], Lp_, ["H", "L"], dts)
    fam2 = dm_family("F2_post_vs_W_I6", "W_I6", [k for k in Qo if k != "W_I6"], Lo_, ["HO", "LO"], dts)
    Lo_["P_S6"] = Lp_["P_S6"]                                                                           # pinball(Hp, q) == pinball(HO, q - G): same quantity, same loss
    fam3 = dm_family("F3_post_vs_pre_P_S6", "P_S6", ["W_I6", "W_HARz", "W_SZSG"], Lo_, ["H", "L"], dts)
    # point accuracy: absolute error of the median, DM on |error|
    def ae(Q, Y, j): return np.abs(Y[:, j] - Q[:, j, LV["q50"]])
    LA = {"P_S6": [ae(Qp["P_S6"], Yp, j) for j in range(2)], "P_EMP250": [ae(Qp["P_EMP250"], Yp, j) for j in range(2)], "PRICE_STAYS": [np.abs(Yp[:, j]) for j in range(2)],
          "W_I6": [ae(Qo["W_I6"], Yq, j) for j in range(2)], "W_EMP250": [ae(Qo["W_EMP250"], Yq, j) for j in range(2)], "OPEN_STAYS": [np.abs(Yq[:, j]) for j in range(2)]}
    fam4 = dm_family("F4_abs_err_median_P_S6", "PRICE_STAYS", ["P_S6", "P_EMP250"], LA, ["H", "L"], dts) + dm_family("F4_abs_err_median_W_I6", "OPEN_STAYS", ["W_I6", "W_EMP250"], LA, ["HO", "LO"], dts)
    fam56 = dm_family("F5_abs_err_median_post_vs_pre", "P_S6", ["W_I6"], LA, ["H", "L"], dts) + dm_family("F6_abs_err_median_S6_vs_EMP250", "P_EMP250", ["P_S6"], LA, ["H", "L"], dts)
    dmt = pd.DataFrame(fam1 + fam2 + fam3 + fam4 + fam56); dmt.to_csv(OUT / "hl_eval_dm_holm.csv", index=False)
    # ---- reliability (share of outcomes at or below each quantile), baseline models
    rel = []
    for nm, Q, Y, tn in (("P_S6", Qp["P_S6"], Yp, ["H", "L"]), ("P_EMP250", Qp["P_EMP250"], Yp, ["H", "L"]), ("W_I6", Qo["W_I6"], Yq, ["HO", "LO"])):
        for w in ("valfinal", "final", "cas"):
            m = (dts >= WIN[w][0]) & (dts <= WIN[w][1])
            for j in range(2):
                rel += [dict(variant=nm, target=tn[j], window=w, n=int(m.sum()), tau=g, share_at_or_below=float((Y[m, j] <= Q[m, j, k]).mean())) for k, g in enumerate(GRID)]
    pd.DataFrame(rel).to_csv(OUT / "hl_eval_reliability.csv", index=False)
    # ---- touch-probability calibration (probability that the high / low reaches c% from the reference)
    tp = []
    for c in (0.005, 0.01, 0.02, 0.03):
        for nm, V, s, Yv, nmv in (("P_S6", Vp, sg["S6"], Yp, ("H", "L")), ("W_I6", Vq, sI6, Yq, ("HO", "LO"))):
            dr = [fhs_draws(V, s, i) for i in idx]
            for j in range(2):
                thr = np.log1p(c) if j == 0 else np.log1p(-c)
                ev = (Yv[:, j] >= thr) if j == 0 else (Yv[:, j] <= thr)
                pm = np.array([(x[:, j] >= thr).mean() if j == 0 else (x[:, j] <= thr).mean() for x in dr])
                pb = np.array([((V[i - W:i, j] >= thr).mean() if j == 0 else (V[i - W:i, j] <= thr).mean()) for i in idx])
                for w in ("valfinal", "final"):
                    m = (dts >= WIN[w][0]) & (dts <= WIN[w][1])
                    bm, bb = (pm[m] - ev[m]) ** 2, (pb[m] - ev[m]) ** 2
                    _, tt, p1, p2 = dm(bm, bb)
                    tp.append(dict(model=nm, target=nmv[j], distance_pct=100 * c, window=w, n=int(m.sum()), mean_predicted=float(pm[m].mean()), observed=float(ev[m].mean()), mean_trailing500_freq=float(pb[m].mean()),
                                   brier_model=float(bm.mean()), brier_trailing500=float(bb.mean()), dm_p_two_sided=p2))
    pd.DataFrame(tp).to_csv(OUT / "hl_eval_touchprob.csv", index=False)
    # ---- stored predictions of the two live models
    pr = pd.DataFrame({"date": dts, "P0": P0, "open": O, "H": hl[:, 0], "L": hl[:, 1]})
    for nm, Q in (("P_S6", Qp["P_S6"]), ("W_I6", Qo["W_I6"])):
        for j, tn in enumerate(("H", "L")):
            for k, g in LV.items():
                pr[f"{nm}_{tn}_{k}"] = (P0 if nm.startswith("P_") else O) * np.exp(Q[:, j, g])
    pr.to_csv(OUT / "hl_eval_predictions.csv", index=False)
    # ---- 14 and 15 Oct, as the production function would have said at the prior close
    two = []
    for day in ("2026-10-14", "2026-10-15"):
        r = d.loc[day]; f = hl_forecast(day, open_price=r["open"], d=d)
        for k, tru in (("high", r["high"]), ("low", r["low"])):
            for ph, blk in (("pre_open", f["pre_open"][k]), ("post_open", f["post_open"][k])):
                q = blk["price_quantiles"]
                two.append(dict(date=day, p0=f["p0"], open=r["open"], which=k, phase=ph, realised=tru, **{kk: q[kk] for kk in LV}, error_of_median_rs=tru - q["q50"], inside_50=q["q25"] <= tru <= q["q75"], inside_90=q["q5"] <= tru <= q["q95"],
                                typical_miss_rs=blk["typical_miss_rs"]))
    pd.DataFrame(two).to_csv(OUT / "hl_eval_twodays.csv", index=False)
    extra_tables(d, t, idx, dts, Qp, Qo, Yp, Yq, P0, O, hl, dmt, b5)
    yahoo_vs_nse(d, hourly)
    # ---- print the headline tables
    pd.set_option("display.width", 250)
    cols = ["variant", "target", "window", "n", "pinball_x1e4", "cov50", "cov90", "kupiec90", "mae_med_pct", "mae_med_rs_at_now", "medae_med_rs_at_now"]
    for nm, tb in (("PRE-OPEN", rp), ("POST-OPEN", ro)):
        print(f"\n===== {nm} (final window and CAS) =====")
        print(tb[tb.window.isin(["final", "cas"])][cols].round(4).to_string(index=False))
    print("\n===== DM / Holm =====")
    print(dmt[dmt.window.isin(["valfinal", "final"])][["family", "window", "variant", "target", "n", "gain_pct", "dm_t", "p_two_sided", "holm_two_sided"]].round(4).to_string(index=False))


def extra_tables(d, t, idx, dts, Qp, Qo, Yp, Yq, P0, O, hl, dmt, b5):
    """By-year stability, closing-auction-era facts, adoption verdicts (the rule fixed in the report)."""
    by = []
    for nm, Q, Y, tn in (("P_S6", Qp["P_S6"], Yp, ["H", "L"]), ("P_EMP250", Qp["P_EMP250"], Yp, ["H", "L"]), ("P_S0", Qp["P_S0"], Yp, ["H", "L"]), ("W_I6", Qo["W_I6"], Yq, ["HO", "LO"]), ("W_EMP250", Qo["W_EMP250"], Yq, ["HO", "LO"])):
        for yr in sorted(set(dts.year)):
            m = dts.year == yr
            for j in range(2):
                by.append(dict(variant=nm, target=tn[j], year=yr, n=int(m.sum()), pinball_x1e4=1e4 * M.pinball(Y[m, j], Q[m, j, :]).mean(), mae_med_pct=100 * np.abs(Y[m, j] - Q[m, j, LV["q50"]]).mean()))
    pd.DataFrame(by).to_csv(OUT / "hl_eval_byyear.csv", index=False)
    cf = []
    for lab, m in (("pre-CAS: 250 sessions before 2026-08-03", (d.index < "2026-08-03") & (np.arange(len(d)) >= (d.index >= "2026-08-03").argmax() - 250)), ("CAS: 2026-08-03 on", d.index >= "2026-08-03"), ("CAS: 2026-08-04 on (previous close is an auction price)", d.index >= "2026-08-04")):
        x = d[m]; tt = t[m]
        cf.append(dict(slice=lab, n=int(m.sum()), share_open_eq_prev=float((x.open == x.prev).mean()), median_gap_pct=100 * tt.G.median(), mean_ret_pct=100 * tt.R.mean(), median_Hp_pct=100 * tt.Hp.median(), median_Lp_pct=100 * tt.Lp.median(),
                       share_H_below_P0=float((x.high < x.prev).mean()), share_L_above_P0=float((x.low > x.prev).mean()), median_HO_pct=100 * tt.HO.median(), median_LO_pct=100 * tt.LO.median(), median_range_pct=100 * (np.exp(tt.rho) - 1).median(),
                       share_close_eq_high=float((x.close == x.high).mean()), share_close_eq_low=float((x.close == x.low).mean())))
    pd.DataFrame(cf).to_csv(OUT / "hl_eval_cas_facts.csv", index=False)
    gb = []                                                                                    # DESCRIPTIVE (not a forecast): where the high / low sit relative to the open, by gap bin, as % of the open
    for w in ("valfinal", "final", "cas"):
        m = (dts >= WIN[w][0]) & (dts <= WIN[w][1])
        for b, lab in enumerate(["flat (|gap| < 0.25 sigma)", "gap up, small (0.25-1 sigma)", "gap up, large (>= 1 sigma)", "gap down, small", "gap down, large"]):
            k = m & (b5[idx] == b); HO, LO = 100 * (np.exp(Yq[k, 0]) - 1), 100 * (np.exp(Yq[k, 1]) - 1)
            if k.sum():
                gb.append(dict(window=w, gap_bin=lab, n=int(k.sum()), median_high_above_open_pct=np.median(HO), p25_HO=np.percentile(HO, 25), p75_HO=np.percentile(HO, 75), median_low_below_open_pct=np.median(LO), p25_LO=np.percentile(LO, 25), p75_LO=np.percentile(LO, 75),
                               share_open_is_high=float((Yq[k, 0] == 0).mean()), share_open_is_low=float((Yq[k, 1] == 0).mean())))
    pd.DataFrame(gb).to_csv(OUT / "hl_eval_gap_bins.csv", index=False)
    r = dmt[dmt.family.isin(["F1_pre_vs_P_S6", "F2_post_vs_W_I6"])]
    ad = []
    for (fam, v, tg), g in r.groupby(["family", "variant", "target"]):
        g = g.set_index("window")
        ad.append(dict(family=fam, variant=v, target=tg, holm_valfinal=g.loc["valfinal", "holm_two_sided"], gain_pct_valfinal=g.loc["valfinal", "gain_pct"], gain_pct_val=g.loc["val", "gain_pct"], gain_pct_final=g.loc["final", "gain_pct"],
                       adopt=bool(g.loc["valfinal", "holm_two_sided"] < 0.05 and g.loc["valfinal", "gain_pct"] > 0 and g.loc["val", "gain_pct"] > 0 and g.loc["final", "gain_pct"] > 0)))
    pd.DataFrame(ad).to_csv(OUT / "hl_eval_adoption.csv", index=False); print("\nvariants adopted by the pre-fixed rule:", [(a["variant"], a["target"]) for a in ad if a["adopt"]] or "none")


def selftest():
    """Same-row leakage test on the real series: change the outcome of one session k (high, low, close; the next session's prev follows) and rebuild every walk-forward forecast.
    Forecasts for sessions <= k must be identical (they may use the open of k but nothing else of k); forecasts after k must move (positive control)."""
    d = load_ohlc(); k = len(d) - 40; e = d.copy(); r = e.index[k]
    e.loc[r, "high"] *= 1.06; e.loc[r, "low"] *= 0.95; e.loc[r, "close"] = e.loc[r, "close"] * 1.03; e.loc[r, "high"] = max(e.loc[r, "high"], e.loc[r, "close"]); e.loc[e.index[k + 1], "prev"] = e.loc[r, "close"]
    A, B = build(d), build(e); j = k - START; ok = True; rows = []
    for nm, (QA, QB) in (("pre", (A[0], B[0])), ("post", (A[1], B[1]))):
        for v in QA:
            same_before = bool(np.allclose(QA[v][:j + 1], QB[v][:j + 1], rtol=0, atol=1e-12))
            moved_after = bool(not np.allclose(QA[v][j + 1:], QB[v][j + 1:], rtol=0, atol=1e-12))
            ok &= same_before and moved_after
            rows.append(dict(test="outcome (H, L, C) of one session changed", phase=nm, variant=v, session=str(r.date()), identical_up_to_and_including_session=same_before, changes_afterwards=moved_after))
    f = d.copy(); f.loc[r, "open"] = f.loc[r, "open"] + 0.3 * (f.loc[r, "close"] - f.loc[r, "open"]) + (0.01 * f.loc[r, "open"] if f.loc[r, "open"] * 1.01 < f.loc[r, "high"] else 0)      # same session, only the OPEN changed
    C = build(f)
    for v in A[0]:
        same = bool(np.allclose(A[0][v][:j + 1], C[0][v][:j + 1], rtol=0, atol=1e-12)); ok &= same
        rows.append(dict(test="only the open of one session changed", phase="pre", variant=v, session=str(r.date()), identical_up_to_and_including_session=same, changes_afterwards=np.nan))
    for v in A[1]:
        rows.append(dict(test="only the open of one session changed", phase="post", variant=v, session=str(r.date()), identical_up_to_and_including_session=bool(np.allclose(A[1][v][j], C[1][v][j], rtol=0, atol=1e-12)), changes_afterwards=np.nan))
    pd.DataFrame(rows).assign(overall="PASSED" if ok else "FAILED").to_csv(OUT / "hl_eval_selftest.csv", index=False)
    print("SELFTEST", "PASSED" if ok else "FAILED", "(details: results/hl_eval_selftest.csv)"); return ok


def replicate():
    """Check against the project: (1) my walk-forward S6 sigma equals the stored results/forecasts_R.csv; (2) the OHLC bootstrap on the STORED sigma gives the project's Final coverage (90.2% / 88.6%, n=317, sessions to 12-Oct).
    (src/eval_hl.py itself now also scores the 13-Oct row, which has no stored sigma: it prints nan pinball and counts that row as a miss.)"""
    d = load_ohlc(); t = targets(d); fc = pd.read_csv(OUT / "forecasts_R.csv", parse_dates=["date"])
    stored = fc[fc.model == "S6"].set_index("date")["sigma"].reindex(d.index).values
    mine = wf_sigmas(t["R"].values, t["v"].values, ("S6",))["S6"]
    ok = np.isfinite(stored)
    rows = [dict(check="max relative difference, my S6 sigma vs stored", value=float(np.max(np.abs(mine[ok] / stored[ok] - 1))), n=int(ok.sum()))]
    Vp, last = t[["Hp", "Lp"]].values, np.where(ok)[0].max()
    idx = np.arange(np.where(ok)[0].min() + 250, last + 1); dts = d.index[idx]; m = dts >= pd.Timestamp("2025-07-01")
    Q = np.array([fhs_q(Vp, stored, i) for i in idx])
    for j, tn in enumerate(("Hp", "Lp")):
        rows += [dict(check=f"{tn}: stored-sigma bootstrap, Final to {dts[-1].date()}: {k}", value=v, n=int(m.sum())) for k, v in (("coverage 90%", M.coverage(Vp[idx, j][m], Q[m, j, :], 0.9)[0]), ("coverage 50%", M.coverage(Vp[idx, j][m], Q[m, j, :], 0.5)[0]),
                                                                                                                                 ("pinball x1e4", 1e4 * M.pinball(Vp[idx, j][m], Q[m, j, :]).mean()))]
    out = pd.DataFrame(rows); out.to_csv(OUT / "hl_eval_replication.csv", index=False); print(out.round(5).to_string(index=False))


def yahoo_vs_nse(d, hourly=None):
    """Yahoo intraday extremes minus the official NSE high / low, per complete session, in rupees."""
    fr = [pd.read_csv(f)[["date", "time", "open", "high", "low", "close"]] for f in (UNION15, EXTRA15) if Path(f).exists()]
    u = pd.concat(fr).drop_duplicates(["date", "time"], keep="first")
    sets = {"15min": u.assign(date=pd.to_datetime(u.date)).groupby("date").agg(h=("high", "max"), l=("low", "min"), nb=("high", "size")).query("nb >= 24")}
    if hourly and Path(hourly).exists():
        r = json.load(open(hourly))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
        h = pd.DataFrame({"date": pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata").tz_localize(None).normalize(), "high": q["high"], "low": q["low"]}).dropna()
        sets["1h"] = h.groupby("date").agg(h=("high", "max"), l=("low", "min"), nb=("high", "size")).query("nb >= 7")
        sets["1h"] = sets["1h"][sets["1h"].index >= "2025-05-23"]              # Yahoo back-adjusts for the 2:1 bonus (ex 2025-05-23); the repo's OHLC levels are raw, so compare only from the ex-date on
    rows, per = [], []
    for src, s in sets.items():
        s = s[s.index.isin(d.index)]
        dh, dl = s["h"] - d.loc[s.index, "high"], s["l"] - d.loc[s.index, "low"]
        per.append(pd.DataFrame({"source": src, "date": s.index, "diff_high_rs": dh.values, "diff_low_rs": dl.values}))
        for nm, x in (("high (Yahoo - NSE)", dh), ("low (Yahoo - NSE)", dl)):
            rows.append(dict(source=src, quantity=nm, n=len(x), share_equal=float((x.abs() < 0.05).mean()), mean_rs=x.mean(), median_rs=x.median(), mean_abs_rs=x.abs().mean(), median_abs_rs=x.abs().median(), p90_abs_rs=x.abs().quantile(0.9), p99_abs_rs=x.abs().quantile(0.99), share_within_rs2=float((x.abs() <= 2).mean()), n_abs_gt_5=int((x.abs() > 5).sum()), n_abs_gt_10=int((x.abs() > 10).sum()), max_abs_rs=x.abs().max(),
                             share_yahoo_inside_nse_range=float((x <= 0.05).mean() if "high" in nm else (x >= -0.05).mean())))
    pd.concat(per).to_csv(OUT / "hl_eval_yahoo_vs_nse.csv", index=False)
    sm = pd.DataFrame(rows); sm.to_csv(OUT / "hl_eval_yahoo_vs_nse_summary.csv", index=False); print("\nYahoo vs NSE high/low:\n", sm.round(3).to_string(index=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date"); ap.add_argument("--open", type=float, default=None); ap.add_argument("--p0", type=float, default=None)
    ap.add_argument("--json", action="store_true"); ap.add_argument("--save", action="store_true"); ap.add_argument("--eval", action="store_true"); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--replicate", action="store_true"); ap.add_argument("--hourly", default=None)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.replicate:
        return replicate()
    if a.eval:
        return evaluate(a.hourly)
    if not a.date:
        ap.error("--date YYYY-MM-DD (or --eval)")
    o = hl_forecast(a.date, a.open, a.p0, examples=a.save and a.open is None)
    if a.save:
        OUT.mkdir(exist_ok=True); (OUT / f"hl_dayahead_{a.date}{'' if a.open is None else f'_open{a.open:g}'}.json").write_text(json.dumps(o, indent=1))
    print(json.dumps(o, indent=1) if a.json else words(o))


if __name__ == "__main__":
    main()
