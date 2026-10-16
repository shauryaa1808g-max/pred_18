"""Analogue ("comparable past days") forecasts of the session HIGH and LOW of NSE:BSE (specialist G of the H/L study; report research/hl/G_analogue.md).

IDEA   Describe every session by a vector of context features known BEFORE the forecast time (previous-day bar shape, volatility state, volume,
       market / VIX / breadth / peers, US overnight; after 09:08 also the official open), find the past sessions whose context was closest, and use THEIR standardised
       high / low outcomes (Hp, Lp = ln(H/P0), ln(L/P0) pre-open; HO, LO = ln(H/O), ln(L/O) post-open, divided by the baseline S6 sigma of that day) times the target day's
       baseline sigma as the forecast distribution.  Optionally blend (quantile average) with the baseline (src/hl_model.py) with a weight fitted on past data only.
       The design, variant list and adoption rule were fixed before any result (research/hl/G_analogue.md, Section 0).

Usage (repo root; python3 src/hl_analog.py ...), no network access:
  --eval            full walk-forward evaluation of all variants -> results/hl5_*.csv   (about 40 s)
  --leak            leakage tests (junk from the target session on, and a positive control, for 8 sessions) -> results/hl5_leakage.csv   (about 7 min)
  --adopt           apply the pre-fixed adoption rule (needs --eval and --leak first) -> results/hl5_adoption.csv
  --live            the 16 Oct 2026 result as of the 15 Oct close and the official open Rs 3,450.0 -> results/hl5_2026-10-16.json (+ results/hl5_2026-10-16_analogues.csv)
  --tables          markdown tables for the report, from the result files
  --check           consistency of analog_forecast() with the walk-forward rows and of the baseline with hl_model.hl_forecast (needs --eval and --live first) -> results/hl5_live_checks.csv
  --date YYYY-MM-DD [--open P] [--p0 P] [--json]     plain words (or JSON) for any date; only sessions BEFORE --date are used
Importable: analog_forecast(date, open_price=None, p0=None, d=None) -> dict   (same keys as hl_model.hl_forecast, plus 'analogues' and 'variants').
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hl_model as HM          # noqa: E402  the BASELINE (S6 volatility x filtered historical simulation)
import metrics as M            # noqa: E402
from common import EPS, GRID, load_breadth, load_index, targets   # noqa: E402

OUT = Path("results")
START, REFIT, P_NOW = HM.START, 20, HM.P_NOW
POOL_FIRST, EXCL, MIN_FIT, MIN_POOL = 500, 5, 60, 30       # first session with a baseline sigma; sessions t-5..t-1 excluded; minimum rows to fit a metric / to form a pool
KS, KER_K = (40, 80, 160), 80                                # k grid and the kernel bandwidth neighbour
SHRINK, ZCLIP = 0.3, 4.0                                     # Mahalanobis: 0.7*correlation + 0.3*identity; z-scores clipped
RIDGE, RIDGE_MIN_ROWS = (1.0, 10.0, 100.0, 1e3, 1e4), 150
WGRID, W_WIN, W_MIN, W_DEF = np.round(np.linspace(0, 1, 11), 1), 500, 120, 0.5
DISPLAY_SPACE, DISPLAY_EST = "B", "k80"
PEERS = ("CDSL", "MCX", "MOTILALOFS", "IEX")
MACRO_FILES = {"SP500": ("SP500.csv", 2), "VIX": ("VIXCLS.csv", 2), "US10Y": ("DGS10.csv", 6), "BRENT": ("DCOILBRENTEU.csv", 8), "DXY": ("DTWEXBGS.csv", 12), "INR": ("DEXINUS.csv", 12)}   # file, calendar-day lag rule
EST = ["k40", "k80", "k160", "ker"]

# ----------------------------------------------------------------------------------------------- feature menu (timestamp rules: research/hl/G_analogue.md Section 0.3)
F_V = ["lnsig_rel"]
F_A = ["rng1", "cloc", "gap1", "r5", "r20", "lnsig_rel"]
F_B = F_A + ["pk5", "gk20", "volz", "turnz", "delz", "dhi", "dlo", "streak"]
F_CAL = ["dow_mon", "dow_tue", "dow_wed", "dow_thu", "mend"]
F_MKT = ["nifty_r1", "nifty_rng1", "bank_r1", "bank_rng1", "vix_ln", "vix_d1", "vix_rv", "adv", "tailbal", "mktturn_z", "peers_r1", "peers_rng1"]
F_US = ["sp_r1", "usvix_ln", "usvix_d1"]
F_SLOW = ["us10y_d5", "brent_r5", "dxy_r5", "inr_r5"]
F_C = F_B + F_CAL + F_MKT + F_US
F_L = F_C + F_SLOW
F_POST = ["gz", "agz", "obeyond", "orel", "lnsI_rel"]
SPACES = {"V": F_V, "A": F_A, "B": F_B, "C": F_C, "L": F_L}
ALL_COLS = list(dict.fromkeys(F_L + F_POST))
CI = {c: i for i, c in enumerate(ALL_COLS)}
FEATURE_SOURCE = {   # id -> (group, timestamp rule)
    "lnsig_rel": ("volatility state", "baseline S6 sigma of the target session (known pre-open) over RMS of R, sessions j-249..j"),
    "rng1": ("BSE own", "ln(H/L) of session j minus ln sigma_s; bar of j (bhavcopy ~16:34 IST on j)"), "cloc": ("BSE own", "(C-L)/(H-L) of session j"),
    "gap1": ("BSE own", "abs opening gap of session j over sigma_s"), "r5": ("BSE own", "log return j-5..j over sigma_s*sqrt5"), "r20": ("BSE own", "log return j-20..j over sigma_s*sqrt20"),
    "pk5": ("BSE own", "5-session Parkinson vol to j minus ln sigma_s"), "gk20": ("BSE own", "20-session Garman-Klass vol to j minus ln sigma_s"),
    "volz": ("BSE own", "60-session z of ln share volume (split-adjusted), window ends j"), "turnz": ("BSE own", "60-session z of ln turnover, window ends j"),
    "delz": ("BSE own", "60-session z of delivery %, window ends j (file has no delivery % for 14-15 Oct 2026)"), "dhi": ("BSE own", "close_j minus trailing-250 high, over sigma_s*sqrt20"),
    "dlo": ("BSE own", "close_j minus trailing-250 low, over sigma_s*sqrt20"), "streak": ("BSE own", "signed run of consecutive up/down closes to j (cap 6)"),
    "dow_mon": ("calendar", "weekday of the target date"), "dow_tue": ("calendar", "weekday of the target date"), "dow_wed": ("calendar", "weekday of the target date"), "dow_thu": ("calendar", "weekday of the target date"),
    "mend": ("calendar", "target date is one of the last two weekdays of its month"),
    "nifty_r1": ("market", "Nifty 50 return on date j over its trailing-60 sd (index file row j)"), "nifty_rng1": ("market", "Nifty 50 ln(H/L) on j over its trailing-60 return sd"),
    "bank_r1": ("market", "Bank Nifty return on j over trailing-60 sd"), "bank_rng1": ("market", "Bank Nifty ln(H/L) on j over trailing-60 sd"),
    "vix_ln": ("market", "ln India VIX close on j"), "vix_d1": ("market", "change of ln India VIX on j"), "vix_rv": ("market", "ln VIX minus ln Nifty 20-session realised vol (annualised %) at j"),
    "adv": ("breadth", "advance share on j (breadth file row j)"), "tailbal": ("breadth", "(stocks up>=5% minus down>=5%)/liquid stocks on j"), "mktturn_z": ("breadth", "60-session z of ln equity-market turnover to j"),
    "peers_r1": ("peers", "mean return of CDSL, MCX, MOTILALOFS, IEX on j over trailing-60 sd (abs return >15% dropped)"), "peers_rng1": ("peers", "ln of mean peer ln(H/L) on j over its trailing-60 mean"),
    "sp_r1": ("US overnight", "S&P 500 return, last observation dated <= target date - 2 days, over trailing-60 sd"), "usvix_ln": ("US overnight", "ln US VIX (VIXCLS), obs dated <= target date - 2 days"),
    "usvix_d1": ("US overnight", "change of ln US VIX, obs dated <= target date - 2 days"), "us10y_d5": ("slow macro", "DGS10 5-observation change, obs <= target date - 6 days"),
    "brent_r5": ("slow macro", "Brent 5-observation log change, obs <= target date - 8 days"), "dxy_r5": ("slow macro", "broad dollar index 5-observation log change, obs <= target date - 12 days"),
    "inr_r5": ("slow macro", "DEXINUS (INR per USD) 5-observation log change, obs <= target date - 12 days"),
    "gz": ("post-open", "ln(O/P0)/sigma_s, O = official open (NSE pre-open auction, final 09:08 IST)"), "agz": ("post-open", "abs(gz)"),
    "obeyond": ("post-open", "+1 / -1 / 0: open above yesterday's high / below yesterday's low / inside"), "orel": ("post-open", "(open - low_j)/(high_j - low_j) clipped to [-1, 2]"),
    "lnsI_rel": ("post-open", "baseline S6 sigma of the open-to-close return (known pre-open) over RMS of I, sessions j-249..j")}


def space_cols(phase: str, space: str) -> list:
    if phase == "pre":
        return SPACES[space]
    return ["lnsI_rel"] if space == "V" else SPACES[space] + F_POST


def variant_ids() -> list:
    ids = [f"{s}_{e}_{f}" for s in SPACES for e in EST for f in ("a", "b")]
    return ids + ["RAND80_a", "RAND80_b", "POOL_a"]


# ----------------------------------------------------------------------------------------------- data
def load_bundle(d=None, before=None) -> dict:
    """All inputs.  d = official bars (hl_model.load_ohlc).  If `before` is given every source is cut to dates strictly before it."""
    d = HM.load_ohlc(before) if d is None else (d if before is None else d[d.index < pd.Timestamp(before)])
    ix, br = load_index(), load_breadth()
    pe = pd.read_csv("data/processed/peers_daily.csv", parse_dates=["date"])
    macro = {}
    for k, (f, _) in MACRO_FILES.items():
        s = pd.read_csv(f"data/raw/macro/{f}", parse_dates=[0]); s = s.set_index(s.columns[0])[s.columns[1]]
        macro[k] = pd.to_numeric(s, errors="coerce")
    b = dict(d=d, ix=ix, br=br, peers=pe, macro=macro)
    if before is not None:
        c = pd.Timestamp(before)
        b.update(ix=ix[ix.index < c], br=br[br.index < c], peers=pe[pe.date < c], macro={k: v[v.index < c] for k, v in macro.items()})
    return b


def rollz(x, w, minp=None) -> np.ndarray:
    s = pd.Series(np.asarray(x, float)); mp = minp or w
    m, sd = s.rolling(w, min_periods=mp).mean(), s.rolling(w, min_periods=mp).std()
    return ((s - m) / sd.where(sd > 0)).values


def run_streak(R) -> np.ndarray:
    s = np.zeros(len(R))
    for i, r in enumerate(R):
        sg = np.sign(r)
        s[i] = (s[i - 1] + sg) if (i > 0 and sg != 0 and sg == np.sign(s[i - 1])) else sg
    return np.clip(s, -6, 6)


def after_state(b: dict) -> dict:
    """Quantities 'as of the close of session j' (row j), from the official bars.  Log-adjusted prices are built from the project's log returns because OHLC levels are raw traded prices."""
    d = b["d"]; t = targets(d)
    R, G, Hp, Lp, I, gk = (t[k].values for k in ("R", "G", "Hp", "Lp", "I", "gk"))
    c = np.cumsum(R); cp = np.r_[0.0, c[:-1]]
    h, l, o = cp + Hp, cp + Lp, cp + G
    rho = h - l
    lsplit = np.cumsum(np.log(d["ca_factor"].fillna(1.0).values))               # 3-for-1 events: share volume made comparable across the ex-date
    lvol = np.log(d["vol"].clip(lower=1).values) - lsplit
    A = dict(c=c, h=h, l=l, o=o, rho=rho, cloc=np.where(rho > 0, (c - l) / np.where(rho > 0, rho, 1), 0.5), gabs=np.abs(G))
    cs = pd.Series(c)
    A["c5"], A["c20"] = (cs - cs.shift(5)).values, (cs - cs.shift(20)).values
    A["pk5"] = 0.5 * np.log(pd.Series(rho ** 2 / (4 * np.log(2))).rolling(5).mean().clip(lower=EPS)).values
    A["gk20"] = 0.5 * np.log(pd.Series(gk).rolling(20).mean().clip(lower=EPS)).values
    A["volz"], A["turnz"] = rollz(lvol, 60), rollz(np.log(d["turnover_cr"].clip(lower=EPS).values), 60)
    A["delz"] = rollz(d["deliv_pct"].values.astype(float), 60, 40)
    A["dhi"] = (cs - pd.Series(h).rolling(250).max()).values
    A["dlo"] = (cs - pd.Series(l).rolling(250).min()).values
    A["streak"] = run_streak(R)
    A["rms250"] = np.sqrt(pd.Series(R ** 2).rolling(250).mean()).values
    A["rmsI250"] = np.sqrt(pd.Series(I ** 2).rolling(250).mean()).values
    return A


def market_after(b: dict, dates) -> pd.DataFrame:
    """Index, breadth and peer features 'as of the close of date j', reindexed to the session dates (NaN where the source file has no row)."""
    ix = b["ix"]
    nr, br_ = np.log(ix["nifty50_close"]).diff(), np.log(ix["bank_close"]).diff()
    sdn, sdb = nr.rolling(60).std(), br_.rolling(60).std()
    f = pd.DataFrame(index=ix.index)
    f["nifty_r1"], f["nifty_rng1"] = nr / sdn, np.log(ix["nifty50_high"] / ix["nifty50_low"]) / sdn
    f["bank_r1"], f["bank_rng1"] = br_ / sdb, np.log(ix["bank_high"] / ix["bank_low"]) / sdb
    f["vix_ln"] = np.log(ix["vix_close"]); f["vix_d1"] = f["vix_ln"].diff()
    f["vix_rv"] = f["vix_ln"] - np.log(100 * np.sqrt(252) * nr.rolling(20).std())
    br = b["br"]
    g = pd.DataFrame(index=br.index)
    g["adv"], g["tailbal"] = br["adv_share"], (br["n_ge_5pct_up"] - br["n_ge_5pct_dn"]) / br["n_liquid"]
    g["mktturn_z"] = rollz(np.log(br["turnover_cr_eq"].clip(lower=EPS).values), 60)
    pe = b["peers"]; pe = pe[(pe.series == "EQ") & pe.symbol.isin(PEERS)].copy()
    pe["r"], pe["g"] = np.log(pe.close / pe.prev), np.log(pe.high / pe.low)
    pe[["r", "g"]] = pe[["r", "g"]].replace([np.inf, -np.inf], np.nan)
    pe.loc[pe.r.abs() > 0.15, "r"] = np.nan
    pr = pe.pivot_table(index="date", columns="symbol", values="r", aggfunc="first").mean(axis=1)
    pg = pe.pivot_table(index="date", columns="symbol", values="g", aggfunc="first").mean(axis=1)
    p = pd.DataFrame({"peers_r1": pr / pr.rolling(60).std(), "peers_rng1": np.log(pg / pg.rolling(60).mean())})
    return pd.concat([f.reindex(dates), g.reindex(dates), p.reindex(dates)], axis=1)


def lookup(s: pd.Series, lag: int, D: pd.DatetimeIndex) -> np.ndarray:
    """Value of the (derived) series at its last observation dated on or before D - lag days; NaN if the file does not cover D - lag (file end + lag < D)."""
    s = s.dropna(); idx = s.index
    pos = idx.searchsorted(D - pd.Timedelta(days=lag), side="right") - 1
    ok = (pos >= 0) & (D <= idx[-1] + pd.Timedelta(days=lag))
    return np.where(ok, s.values[np.clip(pos, 0, None)], np.nan)


def macro_feats(macro: dict, D: pd.DatetimeIndex) -> dict:
    sp = np.log(macro["SP500"].dropna()).diff(); vx = np.log(macro["VIX"].dropna())
    out = {"sp_r1": lookup(sp / sp.rolling(60).std(), MACRO_FILES["SP500"][1], D), "usvix_ln": lookup(vx, MACRO_FILES["VIX"][1], D), "usvix_d1": lookup(vx.diff(), MACRO_FILES["VIX"][1], D),
           "us10y_d5": lookup(macro["US10Y"].dropna().diff(5), MACRO_FILES["US10Y"][1], D)}
    for nm, k in (("brent_r5", "BRENT"), ("dxy_r5", "DXY"), ("inr_r5", "INR")):
        out[nm] = lookup(np.log(macro[k].dropna()).diff(5), MACRO_FILES[k][1], D)
    return out


def feature_table(b, A, mk, sig, sigI, Gall, dates) -> np.ndarray:
    """Master matrix [N, len(ALL_COLS)]; row s = features of session s, known at its pre-open (post-open columns: also the official open).  N = len(sig)."""
    N = len(sig)
    Lg = lambda a: np.r_[np.nan, np.asarray(a, float)][:N]                      # noqa: E731  row s takes the value of session s-1
    ls = np.log(sig)
    F = {"rng1": np.log(Lg(A["rho"])) - ls, "cloc": Lg(A["cloc"]), "gap1": Lg(A["gabs"]) / sig, "r5": Lg(A["c5"]) / (sig * np.sqrt(5)), "r20": Lg(A["c20"]) / (sig * np.sqrt(20)),
         "lnsig_rel": ls - np.log(Lg(A["rms250"])), "pk5": Lg(A["pk5"]) - ls, "gk20": Lg(A["gk20"]) - ls, "volz": Lg(A["volz"]), "turnz": Lg(A["turnz"]), "delz": Lg(A["delz"]),
         "dhi": Lg(A["dhi"]) / (sig * np.sqrt(20)), "dlo": Lg(A["dlo"]) / (sig * np.sqrt(20)), "streak": Lg(A["streak"])}
    D = pd.DatetimeIndex(dates)
    for k, nm in enumerate(("dow_mon", "dow_tue", "dow_wed", "dow_thu")):
        F[nm] = (D.dayofweek.values == k).astype(float)
    F["mend"] = (D >= (D + pd.offsets.BMonthEnd(0)) - pd.offsets.BDay(1)).astype(float)
    for nm in F_MKT:
        F[nm] = Lg(mk[nm].values)
    F.update(macro_feats(b["macro"], D))
    cp, hh, ll = Lg(A["c"]), Lg(A["h"]), Lg(A["l"])
    o = cp + Gall
    F["gz"], F["agz"] = Gall / sig, np.abs(Gall) / sig
    F["obeyond"] = np.where(np.isfinite(o), np.where(o > hh, 1.0, np.where(o < ll, -1.0, 0.0)), np.nan)
    F["orel"] = np.clip((o - ll) / np.where(hh > ll, hh - ll, np.nan), -1, 2)
    F["lnsI_rel"] = np.log(sigI) - np.log(Lg(A["rmsI250"]))
    X = np.column_stack([np.asarray(F[c], float) for c in ALL_COLS])
    X[~np.isfinite(X)] = np.nan
    return X


# ----------------------------------------------------------------------------------------------- distances, analogues, quantiles
def invsqrt(S: np.ndarray) -> np.ndarray:
    w, Q = np.linalg.eigh(S)
    return (Q / np.sqrt(np.clip(w, 1e-9, None))) @ Q.T


def wquant(vals: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted quantiles on GRID (Hazen plotting positions) for each column of vals [m, 2] -> [2, 9]."""
    out = np.empty((vals.shape[1], len(GRID)))
    for j in range(vals.shape[1]):
        o = np.argsort(vals[:, j], kind="stable"); ww = w[o]; cw = np.cumsum(ww)
        out[j] = np.interp(GRID, (cw - 0.5 * ww) / cw[-1], vals[o, j])
    return out


def ridge_fit(Zf: np.ndarray, Uf: np.ndarray):
    """Ridge of the two standardised outcomes on the standardised features; penalty chosen on the last 30% of the training rows.  Returns (feature weights, diagnostics)."""
    m, p = Zf.shape
    mu_y, sd_y = Uf.mean(0), Uf.std(0, ddof=1); Y = (Uf - mu_y) / sd_y
    if m < RIDGE_MIN_ROWS:
        return np.ones(p), dict(lam=np.nan, rows=m, beta=np.zeros((p, 2)), mu_y=mu_y, sd_y=sd_y, r2_val=np.nan)
    cut = int(0.7 * m); best = None
    for lam in RIDGE:
        B = np.linalg.solve(Zf[:cut].T @ Zf[:cut] + lam * np.eye(p), Zf[:cut].T @ Y[:cut])
        sse = float(((Y[cut:] - Zf[cut:] @ B) ** 2).sum()); sst = float(((Y[cut:] - Y[:cut].mean(0)) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, lam, 1 - sse / sst)
    B = np.linalg.solve(Zf.T @ Zf + best[1] * np.eye(p), Zf.T @ Y)
    return np.sqrt((B ** 2).sum(1)), dict(lam=best[1], rows=m, beta=B, mu_y=mu_y, sd_y=sd_y, r2_val=best[2])


def run_space(phase, space, X, U, scale, idx, blocks, keep=()):
    """Walk-forward analogue quantiles of one space for sessions idx: dict est -> [len(idx), 2, 9].  Parameters (standardisation, covariance, ridge weights) are fitted at each block start on sessions before it."""
    cols = [CI[c] for c in space_cols(phase, space)]
    Xs, N, p = X[:, cols], len(X), len(cols)
    Ufin = np.isfinite(U).all(1)
    pos = {s: i for i, s in enumerate(idx)}
    outs = {e: np.full((len(idx), 2, 9), np.nan) for e in EST}
    info = dict(fallback=0, neigh={}, k5=np.full((len(idx), 2), np.nan), ridge_pred=np.full((len(idx), 2), np.nan), ridge_bench=np.full((len(idx), 2), np.nan), ridge_w=[], ridge_r2val=[], n_dropped={},
                age80=np.full(len(idx), np.nan), rec500_80=np.full(len(idx), np.nan), rec500_pool=np.full(len(idx), np.nan))       # descriptive: how old are the 80 nearest sessions, and which share is from the last 500 sessions
    for b0, sess in blocks:
        okf = np.isfinite(Xs).all(1) & Ufin; okf[:POOL_FIRST] = False; okf[b0:] = False
        if okf.sum() < MIN_FIT:
            info["fallback"] += len(sess); continue
        mu, sd = Xs[okf].mean(0), Xs[okf].std(0, ddof=1); sd = np.where(sd > 1e-12, sd, 1.0)
        Z = np.clip((Xs - mu) / sd, -ZCLIP, ZCLIP)
        if space == "L":
            wraw, dg = ridge_fit(Z[okf], U[okf]); wn = wraw / np.sqrt(np.mean(wraw ** 2)) if np.any(wraw > 0) else np.ones(p)
            W, S = np.diag(wn), None
            info["ridge_w"].append((b0, wn / wn.sum())); info["ridge_r2val"].append((b0, dg["lam"], dg["r2_val"], dg["rows"]))
        else:
            S = (1 - SHRINK) * (np.corrcoef(Z[okf].T) if p > 1 else np.ones((1, 1))) + SHRINK * np.eye(p)
            W, wn = invsqrt(S), None
        ZW = Z @ W.T
        okrow = np.isfinite(Xs).all(1) & Ufin
        for t in sess:
            i = pos[t]; used = np.isfinite(Xs[t]); elig = np.zeros(N, bool); elig[POOL_FIRST:max(POOL_FIRST, t - EXCL)] = True
            if space == "L" and dg is not None and np.isfinite(U[t]).all() and used.all():              # descriptive out-of-sample R2 of the ridge fit (diagnostic only)
                info["ridge_pred"][i] = (Z[t] @ dg["beta"]) * dg["sd_y"] + dg["mu_y"]; info["ridge_bench"][i] = dg["mu_y"]
            if used.all():
                pidx = np.nonzero(okrow & elig)[0]
                d2 = ((ZW[pidx] - ZW[t]) ** 2).sum(1) if len(pidx) else np.empty(0)
            elif used.any():
                u_ = np.nonzero(used)[0]; info["n_dropped"][t] = [ALL_COLS[cols[j]] for j in np.nonzero(~used)[0]]
                pidx = np.nonzero(np.isfinite(Xs[:, u_]).all(1) & Ufin & elig)[0]
                Wsub = np.diag(wn[u_]) if space == "L" else invsqrt(S[np.ix_(u_, u_)])
                d2 = (((Z[pidx][:, u_] - Z[t, u_]) @ Wsub.T) ** 2).sum(1) if len(pidx) else np.empty(0)
            else:
                pidx, d2 = np.empty(0, int), np.empty(0)
            if len(pidx) < MIN_POOL:
                info["fallback"] += 1; continue
            order = np.argsort(d2, kind="stable"); sc = scale[t]
            for k in KS:
                outs[f"k{k}"][i] = np.quantile(sc * U[pidx[order[:k]]], GRID, axis=0).T
            h2 = max(float(d2[order[min(KER_K, len(pidx)) - 1]]), 1e-12)
            outs["ker"][i] = wquant(sc * U[pidx], np.exp(-0.5 * d2 / h2))
            info["k5"][i] = sc * np.median(U[pidx[order[:5]]], axis=0)
            age = t - pidx; info["age80"][i], info["rec500_80"][i], info["rec500_pool"][i] = float(np.median(age[order[:80]])), float((age[order[:80]] <= 500).mean()), float((age <= 500).mean())
            if t in keep:
                info["neigh"][t] = dict(idx=pidx[order[:50]], idx160=pidx[order[:160]], d2=d2[order[:50]], h2=h2, n_pool=len(pidx), d2_all=d2, used=used, cols=[ALL_COLS[c] for c in cols])
    return outs, info


def run_controls(U, scale, idx):
    """POOL (all eligible past sessions, no matching) and RAND80 (80 random eligible sessions, seed 10000+t)."""
    pool = np.full((len(idx), 2, 9), np.nan); rnd = pool.copy(); fin = np.isfinite(U).all(1)
    for i, t in enumerate(idx):
        pidx = np.nonzero(fin[:max(POOL_FIRST, t - EXCL)] & (np.arange(max(POOL_FIRST, t - EXCL)) >= POOL_FIRST))[0]
        if len(pidx) < MIN_POOL:
            continue
        pool[i] = np.quantile(scale[t] * U[pidx], GRID, axis=0).T
        sel = np.random.default_rng(10000 + t).choice(pidx, size=min(80, len(pidx)), replace=False)
        rnd[i] = np.quantile(scale[t] * U[sel], GRID, axis=0).T
    return pool, rnd


def blend(Qb, Qa, Y, starts, m):
    """Quantile-average blend (1-w)*baseline + w*analogue, w per target from the trailing W_WIN scored sessions before each block (default 0.5 until W_MIN)."""
    Qbl, Ws = np.full_like(Qa, np.nan), np.zeros((m, 2))
    Lw = [[M.pinball(Y[:, j], (1 - w) * Qb[:, j] + w * Qa[:, j]) if np.isfinite(Y[:, j]).any() else np.full(m, np.nan) for w in WGRID] for j in range(2)]
    ends = list(starts[1:]) + [m]
    for e, e2 in zip(starts, ends):
        for j in range(2):
            if e >= W_MIN:
                lo = max(0, e - W_WIN); w = WGRID[int(np.argmin([np.nanmean(Lw[j][wi][lo:e]) for wi in range(len(WGRID))]))]
            else:
                w = W_DEF
            Qbl[e:e2, j], Ws[e:e2, j] = (1 - w) * Qb[e:e2, j] + w * Qa[e:e2, j], w
    return Qbl, Ws


# ----------------------------------------------------------------------------------------------- pipeline
def pipeline(b: dict, live_date=None, live_open=None, upto=None, keep=(), verbose=True, live_p0=None) -> dict:
    """All walk-forward forecasts for sessions START..(last session, or `upto`); with live_date also the live session n (outcome unknown; its metric fits use all n known sessions).
    Returns baseline and variant quantile arrays [m, 2, 9] for both phases."""
    d = b["d"]; t = targets(d); n = len(d); live = live_date is not None
    R, v, I, gk, G = (t[k].values for k in ("R", "v", "I", "gk", "G"))
    t0 = time.time()
    sig, sigI = HM.wf_sigmas(R, v, ("S6",))["S6"], HM.wf_sigmas(I, gk, ("S6",))["S6"]
    if live:
        sig, sigI = np.r_[sig, HM.s6_next(R, v)], np.r_[sigI, HM.s6_next(I, gk)]
    N = len(sig)
    P0 = (float(d["close"].iloc[-1]) if live_p0 is None else float(live_p0)) if live else None        # previous official close (the project's rule: last bar of the file)
    dates = pd.DatetimeIndex(list(d.index) + ([pd.Timestamp(live_date)] if live else []))
    Gall = np.r_[G, np.log(live_open / P0) if (live and live_open is not None) else (np.nan if live else [])] if live else G.copy()
    A = after_state(b); mk = market_after(b, d.index)
    X = feature_table(b, A, mk, sig, sigI, Gall, dates)
    last = (N - 1) if upto is None else min(upto, N - 1)
    idx = np.arange(START, last + 1); m = len(idx)
    Vp, Vq = t[["Hp", "Lp"]].values, t[["HO", "LO"]].values
    pad = lambda a: np.vstack([a, np.full((N - n, 2), np.nan)]) if N > n else a        # noqa: E731
    Up, Uq = pad(Vp / sig[:n, None]), pad(Vq / sigI[:n, None])
    blocks = [(b0, [s for s in range(b0, min(b0 + REFIT, last + 1))]) for b0 in range(START, min(n, last + 1), REFIT)]
    if live and last >= n:
        blocks.append((n, [n]))
    starts = [b0 - START for b0, _ in blocks]
    Vp_e, Vq_e = pad(Vp), pad(Vq)
    res = dict(idx=idx, dates=dates[idx], N=N, n=n, sig=sig, sigI=sigI, sig_next=sig[n] if live else None, sigI_next=sigI[n] if live else None, X=X, starts=starts, A=A, t=t, keep=keep, P0_live=P0,
               Y={"pre": Vp_e[idx], "post": Vq_e[idx]}, base={}, Q={"pre": {}, "post": {}}, W={"pre": {}, "post": {}}, info={"pre": {}, "post": {}})
    res["base"]["pre"] = np.array([HM.fhs_q(Vp, sig, s) for s in idx])
    run_post = (not live) or live_open is not None
    if run_post:
        res["base"]["post"] = np.array([HM.fhs_q(Vq, sigI, s) for s in idx])
        if live and live_open is None:
            pass
    if verbose:
        print(f"  sigma paths + features {time.time() - t0:.0f}s; sessions {n}, evaluated {m} ({dates[idx[0]].date()} -> {dates[idx[-1]].date()})", flush=True)
    for phase, U, scale in (("pre", Up, sig), ("post", Uq, sigI)):
        if phase == "post" and not run_post:
            continue
        Qb, Y = res["base"][phase], res["Y"][phase]
        pool, rnd = run_controls(U, scale, idx)
        raw = {"POOL_a": pool, "RAND80_a": rnd}
        for space in SPACES:
            outs, info = run_space(phase, space, X, U, scale, idx, [(b0, s) for b0, s in blocks], keep=keep)
            for e in EST:
                raw[f"{space}_{e}_a"] = outs[e]
            res["info"][phase][space] = info
            if verbose:
                print(f"  {phase} space {space} done ({time.time() - t0:.0f}s, fallbacks {info['fallback']})", flush=True)
        for name, Qa in raw.items():
            bad = ~np.isfinite(Qa).all(axis=(1, 2)); Qa = np.where(bad[:, None, None], Qb, Qa)         # a session with too small a pool: analogue = baseline
            res["Q"][phase][name] = Qa
            if name in ("POOL_a",):
                continue
            Qbl, Ws = blend(Qb, Qa, Y, starts, m)
            bn = name[:-1] + "b"; res["Q"][phase][bn], res["W"][phase][bn] = Qbl, Ws
    return res


# ----------------------------------------------------------------------------------------------- evaluation tables
def eval_tables(res: dict, d: pd.DataFrame):
    """Summary metrics per variant x target x window, DM tests vs the baseline with Holm, secondary comparisons."""
    idx, dts = res["idx"], res["dates"]
    ok = np.arange(len(idx)) < (res["n"] - START)                                              # exclude the live row, if any
    idx, dts = idx[ok], dts[ok]
    P0, O = d["prev"].values[idx], d["open"].values[idx]; hl = d[["high", "low"]].values[idx]
    Vp, Vq = res["t"][["Hp", "Lp"]].values, res["t"][["HO", "LO"]].values
    rows, L, Qall = [], {}, {}
    names = {"pre": (["H", "L"], "P_S6", P0, Vp[idx]), "post": (["HO", "LO"], "W_I6", O, Vq[idx])}
    for ph, (tn, bn, ref, Y) in names.items():
        qs = {bn: res["base"][ph][ok]} | {k: q[ok] for k, q in res["Q"][ph].items()}
        qs["EMP250"] = np.array([HM.emp_q(Vp if ph == "pre" else Vq, i, 250) for i in idx])
        for k, q in qs.items():
            Qall[(ph, k)] = q
            nm = bn if k == bn else (("P_" if ph == "pre" else "W_") + k if k == "EMP250" else k)
            rows += [dict(phase=ph, **r) for r in HM.score_rows(nm, q, Y, ref, hl, dts, tn)]
            L[(ph, nm)] = [M.pinball(Y[:, j], q[:, j, :]) for j in range(2)]
        for nm in ("PRICE_STAYS" if ph == "pre" else "OPEN_STAYS",):
            rr = HM.score_rows(nm, np.zeros((len(idx), 2, 9)), Y, ref, hl, dts, tn)
            rows += [dict(phase=ph, **{k: (np.nan if k in ("pinball_x1e4", "pinball_rs_at_now", "cov50", "cov90", "cov90_wilson_lo", "cov90_wilson_hi", "kupiec50", "kupiec90", "below_q5", "above_q95", "p_below_q5", "p_above_q95") else x) for k, x in r.items()}) for r in rr]
    summ = pd.DataFrame(rows)
    # mean blend weights per window
    wr = []
    for ph in ("pre", "post"):
        for k, Wk in res["W"][ph].items():
            for w, (a, bb) in HM.WIN.items():
                mm = (dts >= a) & (dts <= bb)
                if mm.sum() >= 5:
                    wr.append(dict(phase=ph, variant=k, window=w, n=int(mm.sum()), mean_w_first_target=float(Wk[ok][mm, 0].mean()), mean_w_second_target=float(Wk[ok][mm, 1].mean())))
    # DM vs baseline
    dm_rows = []
    fam = [(ph, k) for ph in ("pre", "post") for k in res["Q"][ph]]
    for w in ("final", "valfinal", "val", "cas"):
        a, bb = HM.WIN[w]; mm = (dts >= a) & (dts <= bb)
        blk = []
        for ph, k in fam:
            tn, bn = names[ph][0], names[ph][1]
            for j in range(2):
                lv, lb = L[(ph, k)][j][mm], L[(ph, bn)][j][mm]
                md, tt, p1, p2 = HM.dm(lv, lb)
                blk.append(dict(window=w, phase=ph, variant=k, target=tn[j], n=int(mm.sum()), mean_pinball_var_x1e4=1e4 * lv.mean(), mean_pinball_base_x1e4=1e4 * lb.mean(), gain_pct=100 * md / lb.mean(), dm_t=tt, p_variant_better=p1, p_two_sided=p2))
        if w != "cas":
            p = np.array([r["p_two_sided"] for r in blk]); h = HM.holm(p)
            o = np.argsort(p); bh = np.empty(len(p)); run = 1.0
            for r_, i in enumerate(o[::-1]):
                run = min(run, p[i] * len(p) / (len(p) - r_)); bh[i] = run
        else:
            h = bh = [np.nan] * len(blk)
        dm_rows += [{**r, "holm_two_sided": float(hh), "bh_q": float(qq), "family_size": len(blk)} for r, hh, qq in zip(blk, h, bh)]
    dmt = pd.DataFrame(dm_rows)
    # secondary S1: context spaces vs vol-only V control (same estimator and form), Final window, own Holm family
    s1 = []
    a, bb = HM.WIN["final"]; mm = (dts >= a) & (dts <= bb)
    for ph in ("pre", "post"):
        tn = names[ph][0]
        for sp in ("A", "B", "C", "L"):
            for f in ("a", "b"):
                for j in range(2):
                    md, tt, p1, p2 = HM.dm(L[(ph, f"{sp}_k80_{f}")][j][mm], L[(ph, f"V_k80_{f}")][j][mm])
                    s1.append(dict(phase=ph, space=sp, form=f, estimator="k80", target=tn[j], n=int(mm.sum()), mean_pinball_space_x1e4=1e4 * L[(ph, f"{sp}_k80_{f}")][j][mm].mean(), mean_pinball_V_x1e4=1e4 * L[(ph, f"V_k80_{f}")][j][mm].mean(),
                                   gain_pct_vs_V=100 * md / L[(ph, f"V_k80_{f}")][j][mm].mean(), dm_t=tt, p_two_sided=p2))
    s1 = pd.DataFrame(s1); s1["holm_two_sided"] = HM.holm(s1.p_two_sided.values); s1["family_size"] = len(s1)
    # secondary S2: median of the 5 nearest (space B), descriptive
    s2 = []
    for ph in ("pre", "post"):
        tn, bn, _, Y = names[ph]; k5 = res["info"][ph]["B"]["k5"][ok]; q50 = res["base"][ph][ok][:, :, 4]
        for w in ("final", "valfinal", "cas"):
            a, bb = HM.WIN[w]; mm = (dts >= a) & (dts <= bb)
            for j in range(2):
                e5, eb = np.abs(Y[mm, j] - k5[mm, j]), np.abs(Y[mm, j] - q50[mm, j])
                s2.append(dict(phase=ph, target=tn[j], window=w, n=int(mm.sum()), mae_median_of_5_nearest_rs=P_NOW * e5.mean(), se_rs=P_NOW * e5.std(ddof=1) / np.sqrt(mm.sum()), mae_baseline_median_rs=P_NOW * eb.mean(), ratio=e5.mean() / eb.mean()))
    # secondary S3: ridge out-of-sample R2 (descriptive)
    s3 = []
    for ph in ("pre", "post"):
        pr, bch = res["info"][ph]["L"]["ridge_pred"][ok], res["info"][ph]["L"]["ridge_bench"][ok]; Y = names[ph][3]
        for w in ("valfinal", "final"):
            a, bb = HM.WIN[w]; mm = (dts >= a) & (dts <= bb)
            for j in range(2):
                g = mm & np.isfinite(pr[:, j])
                s3.append(dict(phase=ph, target=names[ph][0][j], window=w, n=int(g.sum()), oos_r2_vs_training_mean=float(1 - np.sum((Y[g, j] - pr[g, j]) ** 2) / np.sum((Y[g, j] - bch[g, j]) ** 2))))
    # ---- ADDED AFTER THE FIRST RESULTS WERE SEEN (post hoc, not part of the pre-fixed rule; Section 6 of the report): S4 matching vs random draws, S5 by-year gains, S6 age of the neighbours
    a, bb = HM.WIN["final"]; mm = (dts >= a) & (dts <= bb)                                       # Final window
    s4 = []
    for ph in ("pre", "post"):
        tn = names[ph][0]
        for sp in ("V", "A", "B", "C", "L"):
            for j in range(2):
                md, tt, p1, p2 = HM.dm(L[(ph, f"{sp}_k80_a")][j][mm], L[(ph, "RAND80_a")][j][mm])
                s4.append(dict(phase=ph, space=sp, estimator="k80", form="a", target=tn[j], n=int(mm.sum()), mean_pinball_matched_x1e4=1e4 * L[(ph, f"{sp}_k80_a")][j][mm].mean(), mean_pinball_random80_x1e4=1e4 * L[(ph, "RAND80_a")][j][mm].mean(),
                               gain_pct_vs_random80=100 * md / L[(ph, "RAND80_a")][j][mm].mean(), dm_t=tt, p_two_sided=p2))
    s4 = pd.DataFrame(s4); s4["holm_two_sided"] = HM.holm(s4.p_two_sided.values); s4["family_size"] = len(s4)
    s5 = []
    for ph in ("pre", "post"):
        tn, bn = names[ph][0], names[ph][1]
        for j in range(2):
            fin_gain = {v: 100 * (L[(ph, bn)][j][mm].mean() - L[(ph, v)][j][mm].mean()) / L[(ph, bn)][j][mm].mean() for (p_, v) in L if p_ == ph and v not in (bn, "P_EMP250", "W_EMP250")}
            best = max(fin_gain, key=fin_gain.get)
            for v, tag in (("B_k80_a", "display, pre-fixed"), ("B_k80_b", "display, pre-fixed"), ("POOL_a", "control"), (best, "best variant in Final for this target (chosen after seeing Final: post hoc)")):
                for yr in sorted(set(dts.year)):
                    my = dts.year == yr
                    s5.append(dict(phase=ph, target=tn[j], variant=v, tag=tag, year=int(yr), n=int(my.sum()), pinball_base_x1e4=1e4 * L[(ph, bn)][j][my].mean(), pinball_variant_x1e4=1e4 * L[(ph, v)][j][my].mean(),
                                   gain_pct=100 * (L[(ph, bn)][j][my].mean() - L[(ph, v)][j][my].mean()) / L[(ph, bn)][j][my].mean()))
    s6 = []
    for ph in ("pre", "post"):
        for sp in SPACES:
            inf = res["info"][ph][sp]
            for w in ("val", "final", "cas"):
                a, bb = HM.WIN[w]; mw = (dts >= a) & (dts <= bb)
                s6.append(dict(phase=ph, space=sp, window=w, n=int(mw.sum()), median_age_sessions_of_80_nearest=float(np.nanmean(inf["age80"][ok][mw])), share_of_80_nearest_from_last_500_sessions=float(np.nanmean(inf["rec500_80"][ok][mw])),
                               share_of_all_eligible_from_last_500_sessions=float(np.nanmean(inf["rec500_pool"][ok][mw]))))
    return summ, pd.DataFrame(wr), dmt, s1, pd.DataFrame(s2), pd.DataFrame(s3), Qall, dict(s4=s4, s5=pd.DataFrame(s5), s6=pd.DataFrame(s6))


def adoption(summ: pd.DataFrame, dmt: pd.DataFrame, leak_ok) -> pd.DataFrame:
    """The pre-fixed five-part adoption rule for every variant-target pair."""
    out = []
    fin = summ[summ.window == "final"].set_index(["phase", "variant", "target"]); cas = summ[summ.window == "cas"].set_index(["phase", "variant", "target"])
    D = {w: dmt[dmt.window == w].set_index(["phase", "variant", "target"]) for w in ("final", "val", "valfinal")}
    for (ph, v, tg), r in D["final"].iterrows():
        bn = "P_S6" if ph == "pre" else "W_I6"; bf, vf = fin.loc[(ph, bn, tg)], fin.loc[(ph, v, tg)]
        c1 = bool(r.gain_pct >= 2.0 and r.holm_two_sided < 0.05)
        c2 = bool(D["val"].loc[(ph, v, tg)].gain_pct > 0)
        c50 = bool(abs(vf.cov50 - 0.5) <= abs(bf.cov50 - 0.5) and vf.kupiec50 > 0.05)
        if tg == "HO":
            c90 = bool(abs(vf.above_q95 - 0.05) <= abs(bf.above_q95 - 0.05) and vf.p_above_q95 > 0.05); k90 = vf.p_above_q95
        else:
            c90 = bool(abs(vf.cov90 - 0.9) <= abs(bf.cov90 - 0.9) and vf.kupiec90 > 0.05); k90 = vf.kupiec90
        c3 = c50 and c90
        cv, cb = cas.loc[(ph, v, tg)], cas.loc[(ph, bn, tg)]
        c4 = bool(cv.pinball_x1e4 <= 1.05 * cb.pinball_x1e4)
        c5 = bool(leak_ok)
        out.append(dict(phase=ph, variant=v, target=tg, gain_pct_final=r.gain_pct, holm_final=r.holm_two_sided, p_final_unadjusted=r.p_two_sided, gain_pct_val=D["val"].loc[(ph, v, tg)].gain_pct,
                        gain_pct_valfinal=D["valfinal"].loc[(ph, v, tg)].gain_pct, cov50=vf.cov50, cov50_base=bf.cov50, kupiec50=vf.kupiec50, cov90=vf.cov90, cov90_base=bf.cov90, kupiec90_or_tailcheck=k90,
                        cas_pinball_ratio=cv.pinball_x1e4 / cb.pinball_x1e4, miss_rs_final=vf.mae_med_rs_at_now, miss_rs_base_final=bf.mae_med_rs_at_now,
                        c1_accuracy_holm=c1, c2_validation_sign=c2, c3_calibration=c3, c4_auction_slice=c4, c5_leakage=c5, ADOPT=bool(c1 and c2 and c3 and c4 and c5), family_size=int(r.family_size)))
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------------------------- leakage test
def junkify(b: dict, k: int, seed: int = 0, perturb_only_previous=False) -> dict:
    """Copy of the inputs where everything from session k on is replaced by junk (session k keeps its open and previous close).  perturb_only_previous: positive control, session k-1 is distorted instead."""
    rng = np.random.default_rng(seed)
    d = b["d"].copy(); n = len(d); t0 = d.index[k]
    d = d.astype({c: float for c in d.select_dtypes("number").columns})                    # junk values are floats (pandas refuses float into an int64 column)
    if perturb_only_previous:
        r = d.index[k - 1]
        d.loc[r, "high"] *= 1.07; d.loc[r, "low"] *= 0.94; d.loc[r, "close"] *= 1.03; d.loc[r, "high"] = max(d.loc[r, "high"], d.loc[r, "close"]); d.loc[d.index[k], "prev"] = d.loc[r, "close"]
        d.loc[r, "vol"] *= 2.5; d.loc[r, "turnover_cr"] *= 2.5
        return dict(b, d=d)
    prevc, cols = float(d["close"].iloc[k - 1]), {c: d[c].values.copy() for c in ("open", "prev", "high", "low", "close", "last", "vol", "turnover_cr", "trades", "deliv_pct", "ca_factor") if c in d.columns}
    for r in range(k, n):
        o = float(cols["open"][r]) if r == k else prevc * np.exp(rng.normal(0, 0.03))
        if r > k:
            cols["open"][r], cols["prev"][r] = o, prevc
        c = o * np.exp(rng.normal(0, 0.05)); hi = max(o, c) * np.exp(abs(rng.normal(0, 0.03))); lo = min(o, c) * np.exp(-abs(rng.normal(0, 0.03)))
        for col, val in (("close", c), ("high", hi), ("low", lo), ("last", c), ("vol", float(np.exp(rng.normal(14, 1)))), ("turnover_cr", float(np.exp(rng.normal(6, 1)))), ("trades", 5e4), ("deliv_pct", float(rng.uniform(10, 70))), ("ca_factor", 1.0)):
            if col in cols:
                cols[col][r] = val
        prevc = c
    for col, arr in cols.items():
        d[col] = arr
    junk = lambda df, cut: df.mask(df.index >= cut) if False else df                                      # noqa: E731
    def jdf(df, cut, date_col=None):
        df = df.copy(); df = df.astype({c: float for c in df.select_dtypes("number").columns}); m = (df[date_col] >= cut) if date_col else (df.index >= cut)
        num = df.select_dtypes("number").columns
        for c in num:
            if (date_col and c == date_col):
                continue
            df.loc[m, c] = np.abs(rng.normal(1, 0.5, m.sum())) * (df.loc[~m, c].median() if (~m).any() else 1.0)
        return df
    ix, br, pe = jdf(b["ix"], t0), jdf(b["br"], t0), jdf(b["peers"], t0, "date")
    pe.loc[pe.date >= t0, "high"] = pe.loc[pe.date >= t0, "close"] * 1.02; pe.loc[pe.date >= t0, "low"] = pe.loc[pe.date >= t0, "close"] * 0.98
    for df, h_, l_ in ((ix, "nifty50_high", "nifty50_low"), (ix, "bank_high", "bank_low")):
        df.loc[df.index >= t0, h_] = df.loc[df.index >= t0, h_.replace("high", "close")] * 1.01; df.loc[df.index >= t0, l_] = df.loc[df.index >= t0, l_.replace("low", "close")] * 0.99
    mac = {}
    for key, s in b["macro"].items():
        s = s.copy(); m = s.index >= t0 - pd.Timedelta(days=1)
        s[m] = np.abs(rng.normal(1, 0.3, m.sum())) * s[~m].dropna().iloc[-1]; mac[key] = s
    return dict(b, d=d, ix=ix, br=br, peers=pe, macro=mac)


def leak_test(res: dict, b: dict, sessions) -> pd.DataFrame:
    rows = []
    for k in sessions:
        for mode in ("junk_from_target_on", "positive_control_previous_session_changed"):
            bj = junkify(b, k, perturb_only_previous=(mode != "junk_from_target_on"))
            t0 = b["d"].index[k]                                                           # proof that the junk really replaced the data (counts of changed values from the target session on, and before it)
            nchg = lambda x, y: int(((x.values != y.values) & ~(np.isnan(x.values) & np.isnan(y.values))).sum())      # noqa: E731
            ixa, ixb, bra, brb, pea, peb = bj["ix"], b["ix"], bj["br"], b["br"], bj["peers"], b["peers"]
            chg = dict(bars_changed_from_target_on=nchg(bj["d"]["close"].iloc[k:], b["d"]["close"].iloc[k:]), bars_changed_before_target=nchg(bj["d"]["close"].iloc[:k], b["d"]["close"].iloc[:k]),
                       index_rows_changed_from_target_on=nchg(ixa["nifty50_close"][ixa.index >= t0], ixb["nifty50_close"][ixb.index >= t0]), index_rows_changed_before_target=nchg(ixa["nifty50_close"][ixa.index < t0], ixb["nifty50_close"][ixb.index < t0]),
                       breadth_rows_changed_from_target_on=nchg(bra["adv_share"][bra.index >= t0], brb["adv_share"][brb.index >= t0]), peer_rows_changed_from_target_on=nchg(pea["close"][pea.date >= t0], peb["close"][peb.date >= t0]),
                       macro_obs_changed_from_day_before_target=sum(nchg(bj["macro"][kk][bj["macro"][kk].index >= t0 - pd.Timedelta(days=1)], b["macro"][kk][b["macro"][kk].index >= t0 - pd.Timedelta(days=1)]) for kk in b["macro"]))
            rj = pipeline(bj, upto=k, verbose=False); i = k - START
            for ph in ("pre", "post"):
                diffs = {v: float(np.max(np.abs(rj["Q"][ph][v][i] - res["Q"][ph][v][i]))) for v in res["Q"][ph]}
                diffs["BASELINE"] = float(np.max(np.abs(rj["base"][ph][i] - res["base"][ph][i])))
                mx = max(diffs.values()); worst = max(diffs, key=diffs.get)
                rows.append(dict(session_index=k, session_date=str(res["dates"][i].date()), test=mode, phase=ph, n_variants=len(diffs), max_abs_diff_log_units=mx, worst_variant=worst,
                                 n_variants_changed=int(sum(x > 1e-9 for x in diffs.values())), passed=(mx <= 1e-9) if mode == "junk_from_target_on" else (mx > 1e-9), **chg))
            print(f"  leak test session {k} ({res['dates'][i].date()}) {mode}: pre max diff {rows[-2]['max_abs_diff_log_units']:.2e}, post {rows[-1]['max_abs_diff_log_units']:.2e}", flush=True)
    out = pd.DataFrame(rows); out["overall"] = "PASSED" if out.passed.all() else "FAILED"
    return out


# ----------------------------------------------------------------------------------------------- live forecast
LV = HM.LV


def _side(ref, q, summ_row) -> dict:
    px = {**{k: round(float(ref * np.exp(q[g])), 2) for k, g in LV.items()}, "q2.5": round(float(ref * np.exp(q[0])), 2), "q97.5": round(float(ref * np.exp(q[8])), 2)}
    out = {"price_quantiles": px, "pct_of_reference": {k: round(100 * float(np.exp(q[g]) - 1), 2) for k, g in LV.items()}, "band_width_rs": {"50%": round(px["q75"] - px["q25"], 1), "90%": round(px["q95"] - px["q5"], 1)}}
    if summ_row is not None:
        out.update(typical_miss_rs=round(float(summ_row.mae_med_pct) / 100 * ref, 1), half_the_time_within_rs=round(float(summ_row.medae_med_pct) / 100 * ref, 1), miss_measured_on_sessions=int(summ_row.n))
    return out


def _analogues(res, phase, space, t, d, N_SHOW=10) -> dict:
    nb = res["info"][phase][space]["neigh"][t]
    ds = res["dates"]; dts_all = pd.DatetimeIndex(list(d.index) + [res["live_date"]])
    tg = res["t"]; rows = []
    for rank, (s, d2) in enumerate(zip(nb["idx"][:N_SHOW], nb["d2"][:N_SHOW]), 1):
        e = {"rank": rank, "date": str(dts_all[s].date()), "distance": round(float(np.sqrt(d2)), 3), "similarity_vs_80th": round(float(np.exp(-0.5 * d2 / nb["h2"])), 3),
             "more_similar_than_pct_of_past_sessions": round(100 * float((nb["d2_all"] > d2).mean()), 1), "gap_pct": round(100 * float(np.exp(tg["G"].values[s]) - 1), 2), "day_return_pct": round(100 * float(np.exp(tg["R"].values[s]) - 1), 2)}
        if phase == "pre":
            e.update(high_pct_of_prev_close=round(100 * float(np.exp(tg["Hp"].values[s]) - 1), 2), low_pct_of_prev_close=round(100 * float(np.exp(tg["Lp"].values[s]) - 1), 2))
        else:
            e.update(high_pct_of_open=round(100 * float(np.exp(tg["HO"].values[s]) - 1), 2), low_pct_of_open=round(100 * float(np.exp(tg["LO"].values[s]) - 1), 2))
        rows.append(e)
    hk, lk = ("high_pct_of_prev_close", "low_pct_of_prev_close") if phase == "pre" else ("high_pct_of_open", "low_pct_of_open")
    summ = {f"top{k}": {"median_high_pct": round(float(np.median([r[hk] for r in rows[:k]])), 2), "median_low_pct": round(float(np.median([r[lk] for r in rows[:k]])), 2),
                        "range_high_pct": [min(r[hk] for r in rows[:k]), max(r[hk] for r in rows[:k])], "range_low_pct": [min(r[lk] for r in rows[:k]), max(r[lk] for r in rows[:k])]} for k in (5, 10)}
    return dict(space=space, phase=phase, n_pool=int(nb["n_pool"]), features_used=[c for c, u in zip(nb["cols"], nb["used"]) if u], features_dropped=[c for c, u in zip(nb["cols"], nb["used"]) if not u], sessions=rows, summary=summ)


def analog_forecast(date, open_price=None, p0=None, d=None, bundle=None, verbose=False) -> dict:
    """Analogue forecast for session `date` using only sessions before it (and `open_price` = official open, if given).  Mirrors hl_model.hl_forecast: pre_open / post_open blocks for the display variant
    (space B, 80 nearest, analogue alone) in `pre_open`/`post_open`, the blended version and the baseline in `variants`, and the comparable days in `analogues`."""
    date = pd.Timestamp(date)
    b = load_bundle(d=d, before=date) if bundle is None else bundle
    dd = b["d"]; n = len(dd); P0 = float(dd["close"].iloc[-1]) if p0 is None else float(p0)
    if open_price is not None and abs(np.log(open_price / P0)) > 0.2:
        raise ValueError("open more than 20% from the previous close: check the number")
    missing = [str(x.date()) for x in pd.bdate_range(dd.index[-1] + pd.Timedelta(days=1), date - pd.Timedelta(days=1))]
    res = pipeline(b, live_date=date, live_open=open_price, keep=(n,), verbose=verbose, live_p0=P0); res["live_date"] = date
    i = n - START; vid = f"{DISPLAY_SPACE}_{DISPLAY_EST}"
    sm = pd.read_csv(OUT / "hl5_eval_summary.csv") if (OUT / "hl5_eval_summary.csv").exists() else pd.DataFrame(columns=["phase", "variant", "target", "window"])
    row = lambda ph, v, tg: (lambda x: x.iloc[0] if len(x) else None)(sm[(sm.phase == ph) & (sm.variant == v) & (sm.target == tg) & (sm.window == "final")])     # noqa: E731
    out = {"date": str(date.date()), "p0": P0, "data_through": str(dd.index[-1].date()), "n_sessions": n, "missing_weekdays_between_data_and_date": missing, "is_weekend": bool(date.dayofweek >= 5),
           "data_sha256": {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ("data/processed/bse_daily.csv", str(HM.EXTRA), "data/processed/index_daily.csv") if Path(f).exists()},
           "display_variant": vid, "sigma_R_pct": 100 * float(res["sig_next"]), "model_pre": f"analogue forecast, space {DISPLAY_SPACE} (14 BSE-own features, shrunk Mahalanobis), {DISPLAY_EST[1:]} nearest past sessions (equal weight, sessions t-5..t-1 excluded), standardised (Hp, Lp) x today's S6 sigma",
           "features_dropped_for_this_session": {sp: res["info"]["pre"][sp]["n_dropped"].get(n, []) for sp in SPACES}}
    ref, tgn = P0, ("H", "L")
    var = {}
    for form, nm in (("a", "analogue_alone"), ("b", "blend_with_baseline")):
        q = res["Q"]["pre"][f"{vid}_{form}"][i]
        var[nm] = {"pre_open": {"high": _side(ref, q[0], row("pre", f"{vid}_{form}", "H")), "low": _side(ref, q[1], row("pre", f"{vid}_{form}", "L"))}}
        if form == "b":
            var[nm]["blend_weight_w_on_analogue"] = {"high": float(res["W"]["pre"][f"{vid}_b"][i, 0]), "low": float(res["W"]["pre"][f"{vid}_b"][i, 1])}
    qb = res["base"]["pre"][i]
    var["baseline"] = {"pre_open": {"high": _side(ref, qb[0], row("pre", "P_S6", "H")), "low": _side(ref, qb[1], row("pre", "P_S6", "L"))}}
    out["pre_open"] = var["analogue_alone"]["pre_open"]
    tgt, sg, sgI = res["t"], res["sig"], res["sigI"]
    def draws(phase):                                                                       # the 80 nearest sessions' standardised outcomes x the target session's baseline sigma (the display variant's own sample)
        ii = res["info"][phase][DISPLAY_SPACE]["neigh"][n]["idx160"][:80]
        cols, s_ = (("Hp", "Lp"), sg) if phase == "pre" else (("HO", "LO"), sgI)
        return np.column_stack([tgt[c].values[ii] / s_[ii] for c in cols]) * float(res["sig_next"] if phase == "pre" else res["sigI_next"])
    U80 = draws("pre")
    out["pre_open"]["touch_prob"] = {f"high >= P0+{c:g}%": round(float((U80[:, 0] >= np.log1p(c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)} | {f"low <= P0-{c:g}%": round(float((U80[:, 1] <= np.log1p(-c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)}
    ana = {"pre_open": {sp: _analogues(res, "pre", sp, n, dd) for sp in SPACES}}
    if open_price is not None:
        sI = float(res["sigI_next"]); out.update(open=float(open_price), gap_pct=100 * float(np.log(open_price / P0)), sigma_I_pct=100 * sI)
        for form, nm in (("a", "analogue_alone"), ("b", "blend_with_baseline")):
            q = res["Q"]["post"][f"{vid}_{form}"][i]
            var[nm]["post_open"] = {"high": _side(open_price, q[0], row("post", f"{vid}_{form}", "HO")), "low": _side(open_price, q[1], row("post", f"{vid}_{form}", "LO"))}
            if form == "b":
                var[nm]["blend_weight_w_on_analogue_post"] = {"high": float(res["W"]["post"][f"{vid}_b"][i, 0]), "low": float(res["W"]["post"][f"{vid}_b"][i, 1])}
        qb = res["base"]["post"][i]
        var["baseline"]["post_open"] = {"high": _side(open_price, qb[0], row("post", "W_I6", "HO")), "low": _side(open_price, qb[1], row("post", "W_I6", "LO"))}
        out["post_open"] = var["analogue_alone"]["post_open"]
        out["model_post"] = f"analogue forecast, space {DISPLAY_SPACE} + the 5 post-open features, {DISPLAY_EST[1:]} nearest past sessions, standardised (HO, LO) x today's S6 open-to-close sigma"
        U80o = draws("post")
        out["post_open"]["touch_prob"] = {f"high >= open+{c:g}%": round(float((U80o[:, 0] >= np.log1p(c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)} | {f"low <= open-{c:g}%": round(float((U80o[:, 1] <= np.log1p(-c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)}
        ana["post_open"] = {sp: _analogues(res, "post", sp, n, dd) for sp in SPACES}
        out["open_vs_yesterday"] = {"open_above_yesterdays_high": bool(res["X"][n, CI["obeyond"]] > 0), "open_below_yesterdays_low": bool(res["X"][n, CI["obeyond"]] < 0), "yesterdays_high": float(dd["high"].iloc[-1]), "yesterdays_low": float(dd["low"].iloc[-1])}
    out["variants"], out["analogues"] = var, ana
    rd = {}
    for ph, key, unit in (("pre_open", "pre", "previous close"), ("post_open", "post", "open")):
        if ph not in ana:
            continue
        a = ana[ph][DISPLAY_SPACE]; hk, lk = ("high_pct_of_prev_close", "low_pct_of_prev_close") if key == "pre" else ("high_pct_of_open", "low_pct_of_open")
        r5, r10 = a["sessions"][:5], a["sessions"][:10]; q = out[ph]
        rd[ph] = (f"The 5 most similar past sessions (space {DISPLAY_SPACE}, {len(a['features_used'])} features, {a['n_pool']} past sessions compared) ended with a high of {min(r[hk] for r in r5):+.2f}% to {max(r[hk] for r in r5):+.2f}% (median {a['summary']['top5']['median_high_pct']:+.2f}%) "
                  f"and a low of {min(r[lk] for r in r5):+.2f}% to {max(r[lk] for r in r5):+.2f}% (median {a['summary']['top5']['median_low_pct']:+.2f}%) of the {unit}; the 10 most similar: median high {a['summary']['top10']['median_high_pct']:+.2f}%, median low {a['summary']['top10']['median_low_pct']:+.2f}%. "
                  f"The 80-nearest forecast (scaled to today's sigma) has a median high {q['high']['pct_of_reference']['q50']:+.2f}% and low {q['low']['pct_of_reference']['q50']:+.2f}%; the project baseline says {var['baseline'][ph]['high']['pct_of_reference']['q50']:+.2f}% / {var['baseline'][ph]['low']['pct_of_reference']['q50']:+.2f}%. "
                  f"Five days are a very small sample: their range is about as wide as the whole spread of past days, and in the walk-forward test the median of the 5 nearest was a worse guess than the baseline median (research/hl/G_analogue.md).")
    out["reading"] = rd
    out["_res"] = res
    return out


def words(o: dict) -> str:
    day = pd.Timestamp(o["date"]).strftime("%a %d %b %Y")
    L = [f"BSE Ltd (NSE: BSE), session of {day}.  Comparable-days forecast; reference: official close Rs {o['p0']:,.1f} of {o['data_through']}.  Baseline typical daily move sigma = {o['sigma_R_pct']:.2f}%."]
    if o["is_weekend"] or o["missing_weekdays_between_data_and_date"]:
        L.append(f"WARNING: weekend or missing official bars {o['missing_weekdays_between_data_and_date']}: the forecast is for the next session after the data.")
    def blk(title, a, key):
        out = [title]
        for k, nm in (("high", "HIGH"), ("low", "LOW ")):
            q = a[key][k]["price_quantiles"]
            out.append(f"  {nm}: median Rs {q['q50']:,.0f}; half the time Rs {q['q25']:,.0f} to {q['q75']:,.0f}; 19 days in 20 inside Rs {q['q2.5']:,.0f} to {q['q97.5']:,.0f}.")
        return "\n".join(out)
    v = o["variants"]
    L.append(blk("PRE-OPEN, analogues alone (80 most similar past sessions):", v["analogue_alone"], "pre_open"))
    L.append(blk("PRE-OPEN, baseline (project model):", v["baseline"], "pre_open"))
    a = o["analogues"]["pre_open"][DISPLAY_SPACE]
    L.append(f"The 5 most similar past days (space {DISPLAY_SPACE}, pool {a['n_pool']}): median high {a['summary']['top5']['median_high_pct']:+.2f}% / low {a['summary']['top5']['median_low_pct']:+.2f}% of the previous close.  The {a['summary']['top10']['median_high_pct']:+.2f}% / {a['summary']['top10']['median_low_pct']:+.2f}% is the median of the 10.")
    for r in a["sessions"][:5]:
        L.append(f"    #{r['rank']} {r['date']}  distance {r['distance']:.2f}  high {r['high_pct_of_prev_close']:+.2f}%  low {r['low_pct_of_prev_close']:+.2f}%")
    if "post_open" in o:
        L.append(f"AFTER THE OPEN (official open Rs {o['open']:,.1f}, gap {o['gap_pct']:+.2f}%):")
        L.append(blk("  analogues alone:", v["analogue_alone"], "post_open")); L.append(blk("  baseline:", v["baseline"], "post_open"))
        a = o["analogues"]["post_open"][DISPLAY_SPACE]
        L.append(f"  The 5 most similar past opens: median high {a['summary']['top5']['median_high_pct']:+.2f}% / low {a['summary']['top5']['median_low_pct']:+.2f}% of the open.")
    L.append("Honest limits: see research/hl/G_analogue.md (the pre-fixed adoption rule decides whether any of this replaces the baseline).")
    return "\n".join(L)


# ----------------------------------------------------------------------------------------------- orchestration
def baseline_repro(res: dict, d: pd.DataFrame) -> pd.DataFrame:
    """My baseline arrays against results/hl_eval_predictions.csv and the project's summary files."""
    pr = pd.read_csv(OUT / "hl_eval_predictions.csv", parse_dates=["date"]).set_index("date")
    ok = np.arange(len(res["idx"])) < (res["n"] - START); idx = res["idx"][ok]; dts = res["dates"][ok]
    P0, O = d["prev"].values[idx], d["open"].values[idx]
    rows = []
    for ph, nm, ref, tn in (("pre", "P_S6", P0, ("H", "L")), ("post", "W_I6", O, ("H", "L"))):
        for j, tg in enumerate(tn):
            for k, g in LV.items():
                mine = ref * np.exp(res["base"][ph][ok][:, j, g]); ref_ = pr.loc[dts, f"{nm}_{tg}_{k}"].values
                rows.append(dict(check=f"{nm} {tg} {k}: max |mine - stored| (Rs)", value=float(np.max(np.abs(mine - ref_))), n=len(dts)))
    for f, ph, nm in (("hl_eval_preopen.csv", "pre", "P_S6"), ("hl_eval_postopen.csv", "post", "W_I6")):
        st = pd.read_csv(OUT / f); st = st[(st.variant == nm) & (st.window == "final")].set_index("target")
        tn = ("H", "L") if ph == "pre" else ("HO", "LO")
        Y = (res["t"][["Hp", "Lp"]] if ph == "pre" else res["t"][["HO", "LO"]]).values[idx]
        for j, tg in enumerate(tn):
            m = dts >= pd.Timestamp("2025-07-01"); pl = 1e4 * M.pinball(Y[m, j], res["base"][ph][ok][m][:, j, :]).mean(); mae = P_NOW * np.abs(Y[m, j] - res["base"][ph][ok][m][:, j, 4]).mean()
            rows.append(dict(check=f"{nm} {tg} Final n={int(m.sum())}: pinball x1e4 mine {pl:.4f} vs project {st.loc[tg, 'pinball_x1e4']:.4f}", value=float(pl - st.loc[tg, "pinball_x1e4"]), n=int(m.sum())))
            rows.append(dict(check=f"{nm} {tg} Final n={int(m.sum())}: typical miss Rs mine {mae:.2f} vs project {st.loc[tg, 'mae_med_rs_at_now']:.2f}", value=float(mae - st.loc[tg, "mae_med_rs_at_now"]), n=int(m.sum())))
    return pd.DataFrame(rows)


def feature_table_csv(res: dict) -> pd.DataFrame:
    X, n = res["X"], res["n"]
    rows = []
    for c in ALL_COLS:
        col = X[:n, CI[c]]; fv = np.where(np.isfinite(col))[0]
        spaces = [s for s in SPACES if c in space_cols("post", s)] if c in F_POST else [s for s in SPACES if c in SPACES[s]]
        rows.append(dict(feature=c, group=FEATURE_SOURCE[c][0], timestamp_rule=FEATURE_SOURCE[c][1], in_spaces="".join(spaces) if c not in F_POST else "post-open (" + "".join(spaces) + ")",
                         first_valid_session=int(fv[0]) if len(fv) else -1, first_valid_date=str(res["dates_all"][fv[0]].date()) if len(fv) else "", share_valid_from_session_500=float(np.isfinite(col[POOL_FIRST:]).mean()),
                         live_value_16oct=float(X[n, CI[c]]) if X.shape[0] > n and np.isfinite(X[n, CI[c]]) else np.nan))
    return pd.DataFrame(rows)


def do_eval():
    OUT.mkdir(exist_ok=True); t0 = time.time()
    b = load_bundle(); d = b["d"]
    print("pipeline (walk-forward, all variants) ...", flush=True)
    res = pipeline(b); res["dates_all"] = d.index
    summ, wts, dmt, s1, s2, s3, Qall, ex = eval_tables(res, d)
    summ.to_csv(OUT / "hl5_eval_summary.csv", index=False); wts.to_csv(OUT / "hl5_blend_weights.csv", index=False); dmt.to_csv(OUT / "hl5_dm_holm.csv", index=False)
    s1.to_csv(OUT / "hl5_secondary_vs_volonly.csv", index=False); s2.to_csv(OUT / "hl5_secondary_5nearest_point.csv", index=False); s3.to_csv(OUT / "hl5_secondary_ridge_r2.csv", index=False)
    ex["s4"].to_csv(OUT / "hl5_posthoc_matching_vs_random.csv", index=False); ex["s5"].to_csv(OUT / "hl5_posthoc_byyear.csv", index=False); ex["s6"].to_csv(OUT / "hl5_posthoc_neighbour_age.csv", index=False)
    rep = baseline_repro(res, d); rep.to_csv(OUT / "hl5_baseline_repro.csv", index=False)
    vt = pd.DataFrame([dict(phase=ph, variant=v, space=v.split("_")[0], estimator=(v.split("_")[1] if v.split("_")[0] in SPACES else ("k80 random" if v.startswith("RAND") else "all eligible")), form=v.split("_")[-1],
                            n_features=len(space_cols(ph, v.split("_")[0])) if v.split("_")[0] in SPACES else 0) for ph in ("pre", "post") for v in res["Q"][ph]])
    vt.to_csv(OUT / "hl5_variants.csv", index=False)
    feature_table_csv(res).to_csv(OUT / "hl5_features.csv", index=False)
    # ridge weights (mean share over blocks), and ridge validation info
    rw = []
    for ph in ("pre", "post"):
        W = res["info"][ph]["L"]["ridge_w"]; cols = space_cols(ph, "L")
        for wn, sel in (("all_blocks", lambda b0: True), ("final_blocks", lambda b0: res["dates_all"][b0] >= pd.Timestamp("2025-07-01"))):
            sh = np.mean([w for b0, w in W if sel(b0)], axis=0)
            rw += [dict(phase=ph, blocks=wn, feature=c, mean_weight_share=float(s), equal_share=1 / len(cols)) for c, s in zip(cols, sh)]
    pd.DataFrame(rw).to_csv(OUT / "hl5_ridge_weights.csv", index=False)
    pd.DataFrame([dict(phase=ph, block_start_session=b0, block_start_date=str(res["dates_all"][b0].date()), lam=lam, r2_validation_part=r2, train_rows=rows_) for ph in ("pre", "post") for b0, lam, r2, rows_ in res["info"][ph]["L"]["ridge_r2val"]]).to_csv(OUT / "hl5_ridge_blocks.csv", index=False)
    # stored predictions: baseline and display variants (prices)
    ok = np.arange(len(res["idx"])) < (res["n"] - START); idx = res["idx"][ok]; P0, O = d["prev"].values[idx], d["open"].values[idx]
    pr = pd.DataFrame({"date": res["dates"][ok], "P0": P0, "open": O, "H": d["high"].values[idx], "L": d["low"].values[idx]})
    cols_ = {}
    for ph, ref, nms in (("pre", P0, ["P_S6", "B_k80_a", "B_k80_b", "V_k80_b"]), ("post", O, ["W_I6", "B_k80_a", "B_k80_b", "V_k80_b"])):
        for nm in nms:
            Q = res["base"][ph][ok] if nm in ("P_S6", "W_I6") else res["Q"][ph][nm][ok]
            for j, tg in enumerate(("H", "L")):
                for k, g in LV.items():
                    cols_[f"{ph}_{nm}_{tg}_{k}"] = ref * np.exp(Q[:, j, g])
    pd.concat([pr, pd.DataFrame(cols_)], axis=1).to_csv(OUT / "hl5_predictions.csv", index=False)
    fam = dmt[(dmt.window == "final")]
    print(f"done in {time.time() - t0:.0f}s; variants per phase {len(res['Q']['pre'])}; family size {len(fam)} variant-target pairs")
    return res


def do_leak():
    t0 = time.time(); b = load_bundle(); d = b["d"]; res = pipeline(b, verbose=False)
    sessions = [900, 1100, 1500, 1800, 2100, 2250, 2330, len(d) - 1]
    lk = leak_test(res, b, sessions); lk.to_csv(OUT / "hl5_leakage.csv", index=False)
    print("LEAKAGE TEST", lk.overall.iloc[0], f"({time.time() - t0:.0f}s)"); return lk


def do_adopt():
    summ, dmt = pd.read_csv(OUT / "hl5_eval_summary.csv"), pd.read_csv(OUT / "hl5_dm_holm.csv")
    lk = pd.read_csv(OUT / "hl5_leakage.csv") if (OUT / "hl5_leakage.csv").exists() else None
    leak_ok = bool(lk is not None and (lk.overall == "PASSED").all())
    ad = adoption(summ, dmt, leak_ok); ad.to_csv(OUT / "hl5_adoption.csv", index=False)
    print("leakage test", "PASSED" if leak_ok else "NOT PASSED / NOT RUN", "| family size", int(ad.family_size.iloc[0]), "| adopted:", ad[ad.ADOPT][["phase", "variant", "target"]].values.tolist() or "none"); return ad


def do_check():
    """Consistency of the production function with the walk-forward evaluation: (1) analog_forecast for replayed dates against results/hl5_predictions.csv (differences come only from the fresh S6 fit at the target session and from the blend weight being refitted at the target rather than at the 20-session block start);
    (2) the baseline inside the 16 Oct result against hl_model.hl_forecast."""
    pr = pd.read_csv(OUT / "hl5_predictions.csv", parse_dates=["date"]).set_index("date"); rows = []
    d0 = HM.load_ohlc()
    for day in ("2025-12-01", "2026-09-01", "2026-10-14", "2026-10-15", str(d0.index[2350].date())):          # session 2350 (19 Aug 2026) is the first session of a 20-session block: live and walk-forward fits coincide there
        r = pr.loc[day]; o = analog_forecast(day, float(r["open"]), verbose=False); o.pop("_res")
        for nm, key in (("analogue_alone", "B_k80_a"), ("blend_with_baseline", "B_k80_b")):
            for ph, ptag, blk in (("pre", "pre", "pre_open"), ("post", "post", "post_open")):
                for tg, side in (("H", "high"), ("L", "low")):
                    for qk in ("q5", "q25", "q50", "q75", "q95"):
                        live = o["variants"][nm][blk][side]["price_quantiles"][qk]; wf = r[f"{ptag}_{key}_{tg}_{qk}"]
                        rows.append(dict(check="analog_forecast(date, open) vs walk-forward row", date=day, variant=key, phase=ph, quantile=f"{tg} {qk}", live=live, walk_forward=float(wf), abs_diff_rs=abs(live - float(wf))))
    f = HM.hl_forecast("2026-10-16", 3450.0); o = json.load(open(OUT / "hl5_2026-10-16.json"))["variants"]["baseline"]
    for blk in ("pre_open", "post_open"):
        for side in ("high", "low"):
            for qk in ("q5", "q25", "q50", "q75", "q95"):
                rows.append(dict(check="baseline in hl5 result vs hl_model.hl_forecast, 16 Oct", date="2026-10-16", variant="baseline", phase=blk, quantile=f"{side} {qk}", live=o[blk][side]["price_quantiles"][qk], walk_forward=f[blk][side]["price_quantiles"][qk],
                                 abs_diff_rs=abs(o[blk][side]["price_quantiles"][qk] - f[blk][side]["price_quantiles"][qk])))
    out = pd.DataFrame(rows); out.to_csv(OUT / "hl5_live_checks.csv", index=False)
    print(out.groupby(["check", "date", "variant"]).abs_diff_rs.agg(["max", "median"]).round(3).to_string()); return out


# ----------------------------------------------------------------------------------------------- report tables (markdown) from the result files
def _md(df: pd.DataFrame, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    df = df.rename(columns=str); cols = list(df.columns)
    def cell(c, v):
        if isinstance(v, (float, np.floating)):
            return "" if not np.isfinite(v) else fmt.get(c, "{:.2f}").format(v)
        return str(v)
    head = "| " + " | ".join(cols) + " |\n|" + "|".join("---" for _ in cols) + "|\n"
    return head + "\n".join("| " + " | ".join(cell(c, v) for c, v in zip(cols, row)) + " |" for row in df.itertuples(index=False))


def report_tables() -> dict:
    """Markdown tables for research/hl/G_analogue.md, read from the hl5_*.csv files (so every number in them is in a file)."""
    S, D, A = pd.read_csv(OUT / "hl5_eval_summary.csv"), pd.read_csv(OUT / "hl5_dm_holm.csv"), pd.read_csv(OUT / "hl5_adoption.csv")
    T = {}
    f = S[S.window == "final"]
    rows = []
    for ph, tn, names in (("pre", ("H", "L"), [("P_S6", "BASELINE P_S6"), ("P_EMP250", "trailing-250 empirical"), ("PRICE_STAYS", "price stays")]), ("post", ("HO", "LO"), [("W_I6", "BASELINE W_I6"), ("W_EMP250", "trailing-250 empirical"), ("OPEN_STAYS", "open stays")])):
        for v, lab in names:
            for tg in tn:
                r = f[(f.phase == ph) & (f.variant == v) & (f.target == tg)].iloc[0]
                rows.append({"target": tg, "model": lab, "n": int(r.n), "pinball x1e4": r.pinball_x1e4, "50% band covers": r.cov50, "90% band covers": r.cov90, "typical miss of median (Rs at 3,428)": r.mae_med_rs_at_now, "half the time within (Rs)": r.medae_med_rs_at_now})
    T["baseline"] = _md(pd.DataFrame(rows), {"50% band covers": "{:.3f}", "90% band covers": "{:.3f}", "pinball x1e4": "{:.3f}", "typical miss of median (Rs at 3,428)": "{:.1f}", "half the time within (Rs)": "{:.1f}"})
    fin = D[D.window == "final"]; val = D[D.window == "val"]
    order = lambda v: (["V", "A", "B", "C", "L", "RAND80", "POOL"].index(v.split("_")[0]), (["k40", "k80", "k160", "ker"].index(v.split("_")[1]) if v.split("_")[0] in SPACES else 0), v[-1])      # noqa: E731
    for ph, tn in (("pre", ("H", "L")), ("post", ("HO", "LO"))):
        vs = sorted(fin[fin.phase == ph].variant.unique(), key=order); rows = []
        for v in vs:
            row = {"variant": v}
            for tg in tn:
                r = fin[(fin.phase == ph) & (fin.variant == v) & (fin.target == tg)].iloc[0]; rv = val[(val.phase == ph) & (val.variant == v) & (val.target == tg)].iloc[0]
                m = S[(S.window == "final") & (S.phase == ph) & (S.variant == v) & (S.target == tg)].iloc[0]
                row.update({f"{tg} gain % (Final)": r.gain_pct, f"{tg} Holm p": r.holm_two_sided, f"{tg} Val gain %": rv.gain_pct, f"{tg} miss Rs": m.mae_med_rs_at_now})
            rows.append(row)
        T[f"matrix_{ph}"] = _md(pd.DataFrame(rows), {c: ("{:.3f}" if "Holm" in c else ("{:.1f}" if "miss" in c else "{:+.2f}")) for c in pd.DataFrame(rows).columns})
    rows = []
    for (ph, tg), g in A.groupby(["phase", "target"], sort=False):
        fg = fin[(fin.phase == ph) & (fin.target == tg)]
        best = g.sort_values("gain_pct_final", ascending=False).iloc[0]
        pos = fg[fg.gain_pct > 0]; se = np.abs(fg.gain_pct / fg.dm_t); se = se[np.isfinite(se)]
        rows.append({"target": tg, "variants": len(g), "c1 gain >= 2% and Holm < 0.05": int(g.c1_accuracy_holm.sum()), "c2 validation sign": int(g.c2_validation_sign.sum()), "c3 calibration": int(g.c3_calibration.sum()), "c4 auction slice": int(g.c4_auction_slice.sum()),
                     "c5 leakage": int(g.c5_leakage.sum()), "ADOPTED": int(g.ADOPT.sum()), "variants better than baseline in Final": len(pos), "largest Final gain %": best.gain_pct_final, "that variant": best.variant, "its Holm p": best.holm_final,
                     "smallest raw p among the better ones": pos.p_two_sided.min() if len(pos) else np.nan, "worse than baseline with Holm < 0.05": int(((fg.gain_pct < 0) & (fg.holm_two_sided < 0.05)).sum()), "median s.e. of the gain (% points)": float(np.median(se))})
    T["adoption"] = _md(pd.DataFrame(rows), {"largest Final gain %": "{:+.2f}", "its Holm p": "{:.3f}", "smallest raw p among the better ones": "{:.4f}", "median s.e. of the gain (% points)": "{:.2f}"})
    s1 = pd.read_csv(OUT / "hl5_secondary_vs_volonly.csv")
    r1 = s1.assign(cell=lambda x: x.apply(lambda r: f"{r.gain_pct_vs_V:+.2f}% (p {r.p_two_sided:.3f}, Holm {r.holm_two_sided:.2f})", axis=1)).pivot_table(index=["phase", "space", "form"], columns="target", values="cell", aggfunc="first").reset_index()
    T["s1"] = _md(r1[["phase", "space", "form"] + [c for c in ("H", "L", "HO", "LO") if c in r1.columns]])
    s4 = pd.read_csv(OUT / "hl5_posthoc_matching_vs_random.csv")
    r4 = s4.assign(cell=lambda x: x.apply(lambda r: f"{r.gain_pct_vs_random80:+.2f}% (p {r.p_two_sided:.3f}, Holm {r.holm_two_sided:.2f})", axis=1)).pivot_table(index=["phase", "space"], columns="target", values="cell", aggfunc="first").reset_index()
    T["s4"] = _md(r4[["phase", "space"] + [c for c in ("H", "L", "HO", "LO") if c in r4.columns]])
    T["s2"] = _md(pd.read_csv(OUT / "hl5_secondary_5nearest_point.csv"), {"mae_median_of_5_nearest_rs": "{:.1f}", "se_rs": "{:.1f}", "mae_baseline_median_rs": "{:.1f}", "ratio": "{:.3f}"})
    T["s3"] = _md(pd.read_csv(OUT / "hl5_secondary_ridge_r2.csv"), {"oos_r2_vs_training_mean": "{:+.4f}"})
    ag = pd.read_csv(OUT / "hl5_posthoc_neighbour_age.csv"); T["age"] = _md(ag[ag.window == "final"].drop(columns="window"), {"median_age_sessions_of_80_nearest": "{:.0f}", "share_of_80_nearest_from_last_500_sessions": "{:.3f}", "share_of_all_eligible_from_last_500_sessions": "{:.3f}"})
    by = pd.read_csv(OUT / "hl5_posthoc_byyear.csv"); by = by[by.tag.str.startswith("display") | (by.variant == "POOL_a")]
    rb = by.assign(cell=lambda x: x.gain_pct.map("{:+.2f}".format)).pivot_table(index=["phase", "target", "variant"], columns="year", values="cell", aggfunc="first").reset_index()
    T["byyear"] = _md(rb)
    return T


def do_tables():
    T = report_tables()
    for k, v in T.items():
        print(f"\n##### {k}\n{v}")


def do_live(date="2026-10-16", open_price=3450.0):
    o = analog_forecast(date, open_price, verbose=True); res = o.pop("_res")
    o["adoption_status"] = "see results/hl5_adoption.csv: the baseline stays the headline unless a variant is adopted by the pre-fixed rule"
    (OUT / f"hl5_{date}.json").write_text(json.dumps(o, indent=1, default=float))
    rows = []
    for ph, spaces in o["analogues"].items():
        for sp, a in spaces.items():
            for r in a["sessions"]:
                rows.append(dict(phase=ph, space=sp, n_pool=a["n_pool"], features_dropped=";".join(a["features_dropped"]), **r))
    pd.DataFrame(rows).to_csv(OUT / f"hl5_{date}_analogues.csv", index=False)
    print(words(o)); return o


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--eval", action="store_true"); ap.add_argument("--leak", action="store_true"); ap.add_argument("--adopt", action="store_true"); ap.add_argument("--live", action="store_true"); ap.add_argument("--check", action="store_true"); ap.add_argument("--tables", action="store_true")
    ap.add_argument("--date"); ap.add_argument("--open", type=float, default=None); ap.add_argument("--p0", type=float, default=None); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.eval:
        return do_eval()
    if a.leak:
        return do_leak()
    if a.adopt:
        return do_adopt()
    if a.live:
        return do_live()
    if a.check:
        return do_check()
    if a.tables:
        return do_tables()
    if not a.date:
        ap.error("--date YYYY-MM-DD (or --eval / --leak / --adopt / --live)")
    o = analog_forecast(a.date, a.open, a.p0); o.pop("_res")
    print(json.dumps(o, indent=1, default=float) if a.json else words(o))


if __name__ == "__main__":
    main()
