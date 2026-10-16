"""Specialist E of the high/low study: flexible models (L1 quantile regression, boosted quantile trees, quantile forest, conformal repair, stacks) on a menu of
known-in-advance parameters, tested against the project's baseline (src/hl_model.py).  Report: research/hl/E_quantile.md (the design, variants, grids and the
adoption rule were written BEFORE any variant was run; they are not changed here).

Targets (identical to the baseline):  pre-open  Hp = ln(H/P0), Lp = ln(L/P0)   |   post-open (official open O known at 09:08)  HO = ln(H/O) >= 0, LO = ln(L/O) <= 0.
Two ways a model is tied to the baseline (report 0.3):  A (direct):  y/sigma_t ~ f(x_t) ;  B (offset):  (y - q_base_t(tau))/sigma_t ~ f_tau(x_t), f = 0 is the baseline.

Usage (repo root; python3 src/hl_ml.py ...):
  --validate-solver                 check the own L1 quantile-regression solver against scikit-learn / HiGHS
  --eval [--workers N]              full walk-forward evaluation of all variants (hours; cached in the scratch folder), writes results/hl3_*.csv/json
  --leak                            leakage test of every variant at 6 sessions (junk from the target session onward)
  --importance                      permutation importance (training windows only) and partial-dependence style readings
  --date 2026-10-16 [--open 3450.0] [--save]   forecast of one session from the sessions before it (importable: ml_forecast(date, open_price=None))
No network access is used.  Sessions are NSE sessions (IST).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
import warnings
import zipfile
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):       # many small fits: one BLAS thread per process (thread oversubscription made the solver 20x slower)
    os.environ.setdefault(_v, "1")
import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import build_dataset as BD                      # noqa: E402  (read_udiff, PEERS: only to read raw bhavcopy zips with the project's own rule)
import hl_model as H                            # noqa: E402  (the BASELINE)
import metrics as M                             # noqa: E402
import models as P                              # noqa: E402
from common import EPS, GRID, targets           # noqa: E402

OUT = ROOT / "results"
SCRATCH = Path(os.environ.get("HL3_SCRATCH", "/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/E"))
START = H.START                                   # 750: first evaluated session (25 Feb 2020)
REFIT = P.REFIT                                   # 20
TR0 = 530                                         # first training row (sigma exists from session 500; the baseline FHS needs >= 30 residuals)
NG = len(GRID)
PNOW = H.P_NOW
TAUS = GRID
LAMS = (0.003, 0.01, 0.03)                        # L1 grid (fixed in the report, 0.5)
FOLDS = (0.55, 0.70, 0.85)
EMBARGO = 5
GBM_DEPTH = (2, 3)
GBM_TREES = (30, 60, 120)
GBM_LR, GBM_LEAF, GBM_L2, GBM_BINS = 0.05, 80, 1.0, 32
GBM_EVERY = 4                                     # nested search re-made every 4th refit
RF_PAR = dict(n_estimators=200, min_samples_leaf=40, max_features=0.3, max_samples=0.7, bootstrap=True)
CQR_CAL = 250
STACK_W = np.round(np.arange(0, 1.0001, 0.1), 1)
STACK_WIN, STACK_MIN = 250, 60
IV_MIN_TRAIN = 120
PEERS12 = ["CDSL", "MCX", "ANGELONE", "MOTILALOFS", "5PAISA", "IEX", "CAMS", "KFINTECH", "NUVAMA", "ANANDRATHI", "GEOJITFSL", "IIFLSEC"]
WINDOWS = ("dev", "val", "valfinal", "final", "cas")

# ----------------------------------------------------------------------------------------------- variants (report 0.5)
# id -> (name, kind, tie, feature groups)    kind: qr | gbm | rf | cqr_base | cqr_qr | cqr_gbm | stack
GROUPS_ALL = ("SIG", "OWN", "FLOW", "CAL", "IDX", "BRD", "PEER", "US", "GAP")
G_OWN = ("SIG", "OWN", "FLOW", "CAL", "GAP")
VARIANTS = {
    "V01": ("QR_sig", "qr", "A", ("SIG",)),
    "V02": ("QR_all", "qr", "A", GROUPS_ALL),
    "V03": ("QRB_all", "qr", "B", GROUPS_ALL),
    "V04": ("QRB_own", "qr", "B", G_OWN),
    "V05": ("QRB_idx", "qr", "B", G_OWN + ("IDX",)),
    "V06": ("QRB_brdpeer", "qr", "B", G_OWN + ("BRD", "PEER")),
    "V07": ("QRB_us", "qr", "B", G_OWN + ("US",)),
    "V08": ("GBM_all", "gbm", "A", GROUPS_ALL),
    "V09": ("GBMB_all", "gbm", "B", GROUPS_ALL),
    "V10": ("RF_all", "rf", "A", GROUPS_ALL),
    "V11": ("CQR_base", "cqr_base", "B", ()),
    "V12": ("CQR_QR", "cqr_qr", "A", GROUPS_ALL),
    "V13": ("CQR_GBM", "cqr_gbm", "A", GROUPS_ALL),
    "V14": ("ST_QR", "stack", "V02", ()),
    "V15": ("ST_GBM", "stack", "V08", ()),
    "V16": ("ST_BEST", "stack", "BEST", ()),
    "V17": ("QRB_iv", "qr", "B", GROUPS_ALL + ("IV",)),
    "V18": ("QRB_us1", "qr", "B", G_OWN + ("US1",)),
}
STACK_POOL = ("V02", "V03", "V08", "V09", "V10")
HEADLINE = tuple(f"V{i:02d}" for i in range(1, 11))
TGT = {"pre": ("H", "L"), "post": ("HO", "LO")}


def _root():
    os.chdir(ROOT)


# ----------------------------------------------------------------------------------------------- inputs
def _breadth_row(eq: pd.DataFrame, date) -> dict:
    """The project's own breadth rule (src/build_dataset.py) applied to one bhavcopy day."""
    u = eq[(eq["series"] == "EQ") & (eq["prev"] > 0) & (eq["close"] > 0) & (eq["turnover_cr"] >= 1.0)]
    r = u["close"] / u["prev"] - 1.0
    return {"date": date, "n_liquid": len(u), "adv_share": float((r > 0).mean()), "dec_share": float((r < 0).mean()), "med_ret": float(r.median()),
            "mean_ret_w": float(r.clip(r.quantile(.01), r.quantile(.99)).mean()), "turnover_cr_eq": float(eq.loc[eq["series"] == "EQ", "turnover_cr"].sum()),
            "n_ge_5pct_up": int((r >= .05).sum()), "n_ge_5pct_dn": int((r <= -.05).sum())}


def load_inputs() -> dict:
    """All raw inputs as plain frames.  Breadth and peers are extended past their file end from the raw NSE bhavcopy zips (data/raw/udiff, read only)."""
    _root()
    d = H.load_ohlc()
    ix = pd.read_csv("data/processed/index_daily.csv", parse_dates=["date"]).set_index("date").sort_index()
    br = pd.read_csv("data/processed/breadth_daily.csv", parse_dates=["date"]).set_index("date").sort_index()
    pe = pd.read_csv("data/processed/peers_daily.csv", parse_dates=["date"])
    pe = pe.drop_duplicates(["symbol", "date"], keep="last")
    add_b, add_p = [], []
    for z in sorted(Path("data/raw/udiff").glob("*.zip")):
        ds = pd.Timestamp(f"{z.stem[:4]}-{z.stem[4:6]}-{z.stem[6:]}")
        need_b, need_p = ds > br.index.max(), ds > pe["date"].max()
        if not (need_b or need_p):
            continue
        day = BD.read_udiff(z)
        eq = day[day["series"].isin(["EQ", "BE", "BZ", "BL"])].copy()
        eq["date"] = ds
        eq["src"] = "udiff"
        if need_b:
            add_b.append(_breadth_row(eq, ds))
        if need_p:
            add_p.append(eq[eq["symbol"].isin(BD.PEERS)])
    if add_b:
        br = pd.concat([br, pd.DataFrame(add_b).set_index("date")]).sort_index()
    if add_p:
        pe = pd.concat([pe] + add_p, ignore_index=True).drop_duplicates(["symbol", "date"], keep="last")
    mac = {}
    for nm in ("SP500", "VIXCLS", "DEXINUS", "DCOILBRENTEU", "DTWEXBGS", "DGS10"):
        x = pd.read_csv(f"data/raw/macro/{nm}.csv", na_values=[".", ""], parse_dates=["observation_date"]).dropna()
        mac[nm] = x.set_index("observation_date").iloc[:, 0].astype(float).sort_index()
    iv = pd.read_csv("data/processed/bse_iv_daily.csv", parse_dates=["date", "expiry"]).set_index("date").sort_index()
    ex = set()
    for f in sorted(Path("data/raw/fo_bse").glob("*.csv")):
        z = pd.read_csv(f, usecols=["TckrSymb", "XpryDt"])
        ex |= set(z.loc[z.TckrSymb == "BSE", "XpryDt"].unique())
    return dict(d=d, ix=ix, br=br, pe=pe, mac=mac, iv=iv, expiries=pd.DatetimeIndex(sorted(pd.to_datetime(list(ex)))))


def junk_inputs(inp: dict, t: int, seed: int = 123) -> dict:
    """Leakage test: replace ALL data dated from session t onward by junk (the open of session t is kept: it is part of the post-open information set).
    Bars (OHLC, volume, turnover, trades, delivery), index file, breadth, peers, FRED files and the IV file are replaced.  Calendar items (F&O expiry list) are not data and stay."""
    rng = np.random.default_rng(seed)
    d = inp["d"].copy()
    for col in d.columns:
        if pd.api.types.is_numeric_dtype(d[col]) and not pd.api.types.is_bool_dtype(d[col]):
            d[col] = d[col].astype(float)
    D = d.index[t]
    n = len(d)
    c = d["prev"].iloc[t]
    o_keep = d["open"].iloc[t]
    for k in range(t, n):
        prev = c if k > t else d["prev"].iloc[t]
        o = o_keep if k == t else prev * np.exp(rng.normal(0, 0.03))
        cl = o * np.exp(rng.normal(0, 0.03))
        hi = max(o, cl) * np.exp(abs(rng.normal(0, 0.02)) + 1e-4)
        lo = min(o, cl) * np.exp(-abs(rng.normal(0, 0.02)) - 1e-4)
        for col, v in (("open", o), ("high", hi), ("low", lo), ("close", cl), ("last", cl)):
            d.iloc[k, d.columns.get_loc(col)] = v
        d.iloc[k, d.columns.get_loc("prev")] = prev
        d.iloc[k, d.columns.get_loc("vol")] = float(rng.integers(10**5, 10**7))
        d.iloc[k, d.columns.get_loc("turnover_cr")] = float(rng.uniform(50, 5000))
        d.iloc[k, d.columns.get_loc("trades")] = float(rng.integers(10**4, 10**6))
        d.iloc[k, d.columns.get_loc("deliv_pct")] = float(rng.uniform(10, 80))
        c = cl
    out = dict(inp)
    out["d"] = d
    ix = inp["ix"].astype(float).copy()
    m = ix.index >= D
    ix.loc[m] = ix.loc[m].apply(lambda col: col * np.exp(rng.normal(0, 0.05, m.sum())))
    out["ix"] = ix
    br = inp["br"].astype(float).copy()
    m = br.index >= D
    for col in br.columns:
        br.loc[m, col] = br.loc[m, col] * np.exp(rng.normal(0, 0.2, m.sum()))
    out["br"] = br
    pe = inp["pe"].copy()
    for col in ("prev", "open", "high", "low", "last", "close", "vol", "turnover_cr", "trades"):
        pe[col] = pe[col].astype(float)
    m = pe["date"] >= D
    for col in ("prev", "open", "high", "low", "last", "close", "vol", "turnover_cr", "trades"):
        pe.loc[m, col] = pe.loc[m, col] * np.exp(rng.normal(0, 0.1, m.sum()))
    out["pe"] = pe
    mac = {}
    for k, s in inp["mac"].items():
        s = s.copy()
        m = s.index >= D
        s.loc[m] = s.loc[m] * np.exp(rng.normal(0, 0.05, m.sum()))
        mac[k] = s
    out["mac"] = mac
    iv = inp["iv"].copy()
    m = iv.index >= D
    for col in ("iv_lo_otm", "iv_hi_otm", "iv_atm"):
        iv.loc[m, col] = iv.loc[m, col] * np.exp(rng.normal(0, 0.2, m.sum()))
    out["iv"] = iv
    return out


def extend_live(inp: dict, date, open_price) -> dict:
    """Append the not-yet-played session `date` as a placeholder row (prev = last official close; high = low = close = open (or prev when the open is unknown)).
    Nothing of the placeholder is read by any feature other than the open (post-open gap block) and the calendar."""
    d = inp["d"].copy()
    date = pd.Timestamp(date)
    if date <= d.index[-1]:
        raise ValueError("live date must be after the last official bar")
    p0 = float(d["close"].iloc[-1])
    o = p0 if open_price is None else float(open_price)
    row = {c: np.nan for c in d.columns}
    row.update(series="EQ", open=o, high=o, low=o, last=o, close=o, prev=p0, ca_factor=1.0, short_session=False, weekend=bool(date.dayofweek >= 5))
    dtypes = d.dtypes
    d.loc[date] = pd.Series(row)
    for c in d.columns:
        if str(dtypes[c]).startswith("float") or str(dtypes[c]).startswith("int"):
            d[c] = d[c].astype(float)
        elif str(dtypes[c]) == "bool":
            d[c] = d[c].astype(bool)
    out = dict(inp)
    out["d"] = d
    return out


# ----------------------------------------------------------------------------------------------- baseline paths
def baseline_paths(d: pd.DataFrame, live: bool) -> dict:
    """Walk-forward S6 sigma of R and of I (padded to the series length), the baseline FHS quantiles for every session from TR0, and the targets.
    live=True: d carries one placeholder row at the end; its sigma uses parameters fitted on all known sessions (as hl_model.s6_next)."""
    n_all = len(d)
    dk = d.iloc[:-1] if live else d
    n = len(dk)
    t = targets(dk)
    R, v, I, gk = t["R"].values, t["v"].values, t["I"].values, t["gk"].values
    sR, sI = H.wf_sigmas(R, v, ("S6",))["S6"], H.wf_sigmas(I, gk, ("S6",))["S6"]
    if live:
        sR, sI = np.r_[sR, H.s6_next(R, v)], np.r_[sI, H.s6_next(I, gk)]
    Vp, Vo = t[["Hp", "Lp"]].values, t[["HO", "LO"]].values
    Vp = np.r_[Vp, np.full((n_all - n, 2), np.nan)]
    Vo = np.r_[Vo, np.full((n_all - n, 2), np.nan)]
    BQp = np.full((n_all, 2, NG), np.nan)
    BQo = np.full((n_all, 2, NG), np.nan)
    for s in range(TR0, n_all):
        BQp[s] = H.fhs_q(Vp, sR, s)
        BQo[s] = H.fhs_q(Vo, sI, s)
    return dict(n=n, n_all=n_all, t=t, sigR=sR, sigI=sI, Vp=Vp, Vo=Vo, BQp=BQp, BQo=BQo)


# ----------------------------------------------------------------------------------------------- features
def _zroll(x: pd.Series, w: int, minp: int | None = None) -> pd.Series:
    mp_ = w if minp is None else minp
    return (x - x.rolling(w, min_periods=mp_).mean()) / x.rolling(w, min_periods=mp_).std()


def _streak(r: np.ndarray, cap: int = 6) -> np.ndarray:
    out, run = np.zeros(len(r)), 0.0
    for i, x in enumerate(r):
        sgn = 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)
        run = (run + sgn if (run * sgn > 0) else sgn) if sgn != 0 else 0.0
        out[i] = max(-cap, min(cap, run))
    return out


def _fred_block(mac: dict, dates: pd.DatetimeIndex, lag_days: int) -> pd.DataFrame:
    """US/overnight block.  For the session dated D only observations dated <= D - lag_days are used (lag 2 = conservative: a FRED value can be posted a day late;
    lag 1 = the observation of the previous calendar day is assumed available before the Indian open).  An observation more than 7 days older than that cutoff counts as missing."""
    cutoff = dates - pd.Timedelta(days=lag_days)

    def pick(s: pd.Series, back: int = 1):
        ix = s.index.values.astype("datetime64[ns]")
        cv = cutoff.values.astype("datetime64[ns]")
        pos = np.searchsorted(ix, cv, side="right") - 1
        ok = pos >= back
        age = np.where(pos >= 0, (cv - ix[np.clip(pos, 0, len(ix) - 1)]) / np.timedelta64(1, "D"), np.inf)
        ok &= age <= 7
        cur = np.where(ok, s.values[np.clip(pos, 0, len(s) - 1)], np.nan)
        prv = np.where(ok, s.values[np.clip(pos - back, 0, len(s) - 1)], np.nan)
        return cur, prv

    f = {}
    c, p = pick(mac["SP500"]); f["sp_ret"] = np.log(c / p)
    c, p5 = pick(mac["SP500"], 5); f["sp_ret5"] = np.log(c / p5)
    c, p = pick(mac["VIXCLS"]); f["usvix_ln"] = np.log(c); f["usvix_chg"] = np.log(c / p)
    c, p = pick(mac["DEXINUS"]); f["inr_chg"] = np.log(c / p)
    c, p = pick(mac["DCOILBRENTEU"]); f["brent_ret"] = np.log(c / p)
    c, p = pick(mac["DTWEXBGS"]); f["dxy_ret"] = np.log(c / p)
    c, p = pick(mac["DGS10"]); f["us10y_chg"] = c - p
    return pd.DataFrame(f, index=dates)


def build_features(inp: dict, sig: np.ndarray, sigR: np.ndarray, phase: str) -> tuple[pd.DataFrame, dict]:
    """Feature matrix for every session t (row t uses information through the close of the previous session s = t-1, plus the open of t in the GAP block).
    `sig` = baseline scale of the phase (S6 of R pre-open, S6 of I post-open); `sigR` = S6 of R (gap scaling).  Returns (frame, group map)."""
    d, ix, br, pe, mac, iv = inp["d"], inp["ix"], inp["br"], inp["pe"], inp["mac"], inp["iv"]
    idx = d.index
    sg = pd.Series(sig, index=idx)
    sgR = pd.Series(sigR, index=idx)
    t = targets(d)
    R, G, Hp, Lp, rho, gk = t["R"], t["G"], t["Hp"], t["Lp"], t["rho"], t["gk"]
    c = R.cumsum()
    h, l = c.shift(1) + Hp, c.shift(1) + Lp
    S = lambda x: x.shift(1)                                                        # noqa: E731  (value of session s=t-1 placed on row t)
    lns = np.log(sg)
    F, grp = {}, {}

    def add(name, series, g):
        F[name] = series
        grp[name] = g

    add("sig_ln", lns, "SIG")
    add("own_rng1", S(np.log(rho.clip(lower=1e-6))) - lns, "OWN")
    for w in (5, 10, 20):
        add(f"own_park{w}", S(np.log(np.sqrt((rho ** 2).rolling(w).mean() / (4 * np.log(2))))) - lns, "OWN")
    for w in (5, 10, 20):
        add(f"own_gk{w}", S(np.log(np.sqrt(gk.rolling(w).mean()))) - lns, "OWN")
    for w in (5, 20):
        add(f"own_rv{w}", S(np.log(np.sqrt((R ** 2).rolling(w).mean().clip(lower=EPS)))) - lns, "OWN")
    add("own_gap1", S(G.abs()) / sg, "OWN")
    add("own_cloc", S((R - Lp) / (Hp - Lp).replace(0, np.nan)), "OWN")
    add("own_ret1", S(R) / sg, "OWN")
    add("own_ret5", S(R.rolling(5).sum()) / (sg * np.sqrt(5)), "OWN")
    add("own_ret20", S(R.rolling(20).sum()) / (sg * np.sqrt(20)), "OWN")
    add("own_dhi250", S(c - h.rolling(250, min_periods=250).max()), "OWN")
    add("own_dlo250", S(c - l.rolling(250, min_periods=250).min()), "OWN")
    add("own_streak", S(pd.Series(_streak(R.values), index=idx)), "OWN")
    add("own_hp1", S(Hp) / sg, "OWN")
    add("own_lp1", S(Lp) / sg, "OWN")
    add("own_hp20", S(Hp.rolling(20).mean()) / sg, "OWN")
    add("own_lp20", S(Lp.rolling(20).mean()) / sg, "OWN")
    # ---- FLOW
    lt = np.log(d["turnover_cr"].clip(lower=1e-6))
    add("flow_turn_z", S(_zroll(lt, 60)), "FLOW")
    add("flow_trades_z", S(_zroll(np.log(d["trades"].clip(lower=1)), 60)), "FLOW")
    add("flow_dturn5", S(lt - lt.shift(1).rolling(5).mean()), "FLOW")
    add("flow_deliv_z", S(_zroll(d["deliv_pct"], 60, 30)), "FLOW")
    # ---- CAL (calendar, known in advance)
    dow = pd.Series(idx.dayofweek, index=idx)
    for k, nm in enumerate(("mon", "tue", "wed", "thu")):
        add(f"cal_{nm}", (dow == k).astype(float), "CAL")
    add("cal_gapdays", pd.Series(idx, index=idx).diff().dt.days.astype(float), "CAL")
    first_last = {}
    for yy, mm in sorted(set(zip(idx.year, idx.month))):
        bd = pd.bdate_range(pd.Timestamp(yy, mm, 1), pd.Timestamp(yy, mm, 1) + pd.offsets.MonthEnd(0))
        first_last[(yy, mm)] = (bd[0], bd[-1])
    add("cal_mend", pd.Series([float(x == first_last[(x.year, x.month)][1]) for x in idx], index=idx), "CAL")
    add("cal_mstart", pd.Series([float(x == first_last[(x.year, x.month)][0]) for x in idx], index=idx), "CAL")
    # ---- IDX (index file of session s, published ~23:20 IST on s)
    ix = ix[~ix.index.duplicated(keep="last")]
    nr = {}
    for nm, key in (("nifty", "nifty50"), ("bank", "bank"), ("capmkts", "capmkts")):
        cl, hi, lo = ix[f"{key}_close"], ix[f"{key}_high"], ix[f"{key}_low"]
        r = np.log(cl).diff()
        nr[nm] = r
        rg = np.log(hi / lo).clip(lower=1e-6)
        add(f"idx_{nm}_ret_z", (r / r.rolling(60, min_periods=60).std()).reindex(idx).pipe(S), "IDX")
        add(f"idx_{nm}_rng", np.log(rg / rg.rolling(60, min_periods=60).mean()).reindex(idx).pipe(S), "IDX")
    lv = np.log(ix["vix_close"])
    add("idx_vix_ln", lv.reindex(idx).pipe(S), "IDX")
    add("idx_vix_chg", lv.diff().reindex(idx).pipe(S), "IDX")
    rv20 = np.sqrt((nr["nifty"] ** 2).rolling(20, min_periods=20).mean())
    add("idx_vix_rvspread", (np.log(ix["vix_close"] / 100 / np.sqrt(252)) - np.log(rv20)).reindex(idx).pipe(S), "IDX")
    add("idx_bse_minus_nifty", S(R - nr["nifty"].reindex(idx)) / sg, "IDX")
    # ---- BRD (breadth recomputed from / read from the bhavcopy of session s)
    br = br[~br.index.duplicated(keep="last")]
    add("brd_adv", (br["adv_share"] - 0.5).reindex(idx).pipe(S), "BRD")
    add("brd_med_z", (br["med_ret"] / br["med_ret"].rolling(60, min_periods=60).std()).reindex(idx).pipe(S), "BRD")
    add("brd_up5", (br["n_ge_5pct_up"] / br["n_liquid"]).reindex(idx).pipe(S), "BRD")
    add("brd_dn5", (br["n_ge_5pct_dn"] / br["n_liquid"]).reindex(idx).pipe(S), "BRD")
    add("brd_turn_z", _zroll(np.log(br["turnover_cr_eq"].clip(lower=1e-6)), 60).reindex(idx).pipe(S), "BRD")
    # ---- PEER
    p = pe[pe["symbol"].isin(PEERS12 + ["CDSL", "MCX"])].copy()
    p["ret"] = np.log(p["close"] / p["prev"])
    p.loc[p["ret"].abs() > 0.2, "ret"] = np.nan
    p["rng"] = np.log(p["high"] / p["low"]).clip(lower=1e-6)
    pr = p.pivot_table(index="date", columns="symbol", values="ret", aggfunc="last")
    pg = p.pivot_table(index="date", columns="symbol", values="rng", aggfunc="last")
    pr, pg = pr.reindex(columns=PEERS12), pg.reindex(columns=PEERS12)
    add("peer_ret", pr.mean(axis=1, skipna=True).reindex(idx).pipe(S) / sg, "PEER")
    add("peer_rng", np.log(pg.mean(axis=1, skipna=True)).reindex(idx).pipe(S) - lns, "PEER")
    for sym in ("CDSL", "MCX"):
        add(f"peer_{sym.lower()}_ret", p[p.symbol == sym].set_index("date")["ret"].reindex(idx).pipe(S) / sg, "PEER")
        add(f"peer_{sym.lower()}_rng", np.log(p[p.symbol == sym].set_index("date")["rng"]).reindex(idx).pipe(S) - lns, "PEER")
    # ---- US overnight (conservative lag 2) and the less conservative lag-1 duplicate block
    for lag, g in ((2, "US"), (1, "US1")):
        fb = _fred_block(mac, idx, lag)
        for col in fb.columns:
            add(f"{g.lower()}_{col}", fb[col], g)
    # ---- IV (own short window from 2024-11-29)
    ivs = iv[~iv.index.duplicated(keep="last")]
    iv_atm = ivs["iv_atm"] / np.sqrt(252)
    rv20b = np.sqrt((R ** 2).rolling(20).mean().clip(lower=EPS))
    ivd = iv_atm.reindex(idx)
    add("iv_rel", S(np.log(ivd)) - lns, "IV")
    add("iv_skew", ((ivs["iv_lo_otm"] - ivs["iv_hi_otm"]) / ivs["iv_atm"]).reindex(idx).pipe(S), "IV")
    add("iv_vs_rv20", S(np.log(ivd) - np.log(rv20b)), "IV")
    add("iv_chg", np.log(iv_atm).diff().reindex(idx).pipe(S), "IV")
    add("iv_dte", (ivs["dte"] / 30.0).reindex(idx).pipe(S), "IV")
    ex = inp["expiries"]
    exset = set(ex)
    on_ex = pd.Series(idx.isin(ex), index=idx).astype(float)
    nxt = pd.Series(idx, index=idx).shift(-1)
    day_before = pd.Series([float(pd.notna(x) and x in exset) for x in nxt], index=idx)
    # the expiry list is the contract calendar of the F&O period; before the IV file starts the whole IV block is "no information"
    live_iv = pd.Series(idx > iv.index.min(), index=idx)
    add("iv_expiry_day", on_ex.where(live_iv), "IV")
    add("iv_day_before_expiry", day_before.where(live_iv), "IV")
    # ---- GAP (post-open only): the official open O of session t (final 09:08 IST)
    gz = G / sgR
    ob = (c.shift(1) + G)                                                            # log open on the adjusted chain
    hy, ly = h.shift(1), l.shift(1)
    add("gap_gz", gz, "GAP")
    add("gap_agz", gz.abs(), "GAP")
    add("gap_above_yhigh", (ob > hy).astype(float).where(hy.notna()), "GAP")
    add("gap_below_ylow", (ob < ly).astype(float).where(ly.notna()), "GAP")
    add("gap_pos", ((ob - ly) / (hy - ly).replace(0, np.nan)).clip(-1, 2), "GAP")
    fr = pd.DataFrame(F, index=idx).replace([np.inf, -np.inf], np.nan)
    if phase == "pre":
        keep = [k for k in fr.columns if grp[k] != "GAP"]
        fr = fr[keep]
    return fr, {k: grp[k] for k in fr.columns}


# ----------------------------------------------------------------------------------------------- context
class Ctx:
    """Everything the walk-forward needs, built from raw inputs.  Row index = session number (0 = first session in the file)."""

    def __init__(self, inp: dict, live: bool = False):
        self.inp = inp
        self.live = live
        self.d = inp["d"]
        self.bp = baseline_paths(self.d, live)
        self.dates = self.d.index
        self.N = len(self.d)
        self.ph = {}
        for ph, sg, Y, BQ in (("pre", self.bp["sigR"], self.bp["Vp"], self.bp["BQp"]), ("post", self.bp["sigI"], self.bp["Vo"], self.bp["BQo"])):
            fr, grp = build_features(inp, sg, self.bp["sigR"], ph)
            self.ph[ph] = dict(sig=sg, Y=Y, BQ=BQ, F=fr, grp=grp, cols=list(fr.columns), X=fr.values.astype(float))
        # IV availability of training rows: sessions whose previous-session IV exists
        ivx = self.ph["pre"]["F"]["iv_rel"].notna().values
        self.iv_count = np.cumsum(ivx)                       # number of rows <= s with an IV feature

    def colidx(self, ph: str, groups) -> list:
        g = self.ph[ph]["grp"]
        return [i for i, c in enumerate(self.ph[ph]["cols"]) if g[c] in groups]


# ----------------------------------------------------------------------------------------------- learners
QR_H = 0.01                                        # smoothing width of the check loss (in units of the standardised target)


def pin_rows(y: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Mean pinball over the 9 levels per row (y [n], q [n,9])."""
    u = y[:, None] - q
    return np.mean(np.maximum(TAUS[None, :] * u, (TAUS[None, :] - 1) * u), axis=1)


def prep(Xtr: np.ndarray, *others: np.ndarray):
    """Standardise with TRAINING mean/sd, winsorise at +-4 sd, missing -> 0 (= training median 'no information')."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mu, sd = np.nanmean(Xtr, axis=0), np.nanstd(Xtr, axis=0)
    mu = np.where(np.isfinite(mu), mu, 0.0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-12), sd, 1.0)
    f = lambda A: np.ascontiguousarray(np.nan_to_num(np.clip((A - mu) / sd, -4.0, 4.0), nan=0.0))      # noqa: E731
    return (f(Xtr),) + tuple(f(A) for A in others)


def _qr_one(Z: np.ndarray, y: np.ndarray, tau: float, lam: float, x0: np.ndarray | None = None):
    """min  mean check_tau(y - a - Z b) + lam |b|_1  with the check loss smoothed by h (logistic): tau r + h log(1 + exp(-r/h)).  b = b+ - b-, bounded L-BFGS-B."""
    n, p = Z.shape
    h = QR_H

    def f(th):
        b = th[1:1 + p] - th[1 + p:]
        r = y - th[0] - Z @ b
        zz = r / h
        val = np.mean(tau * r + h * np.logaddexp(0.0, -zz)) + lam * th[1:].sum()
        g = tau - expit(-zz)
        gb = -(Z.T @ g) / n
        return val, np.r_[-g.sum() / n, gb + lam, -gb + lam]

    if x0 is None:
        x0 = np.zeros(1 + 2 * p)
        x0[0] = np.quantile(y, tau)
    res = optimize.minimize(f, x0, jac=True, method="L-BFGS-B", bounds=[(None, None)] + [(0.0, None)] * (2 * p), options=dict(maxiter=600, ftol=1e-11, gtol=1e-7, maxcor=15))
    return res.x


def qr_levels(Z: np.ndarray, y: np.ndarray, lam: float):
    """L1 quantile regression at the 9 levels.  y: [n] (same target for every level) or [n,9].  Returns intercepts [9] and coefficients [9,p]."""
    n, p = Z.shape
    a, B = np.zeros(NG), np.zeros((NG, p))
    prev = None
    for k, tau in enumerate(TAUS):
        yk = y if y.ndim == 1 else y[:, k]
        x0 = None
        if prev is not None:
            x0 = prev.copy()
            x0[0] = np.quantile(yk - Z @ (prev[1:1 + p] - prev[1 + p:]), tau)
        th = _qr_one(Z, yk, float(tau), lam, x0)
        prev = th
        a[k], B[k] = th[0], th[1:1 + p] - th[1 + p:]
    return a, B


def _target(kind: str, y, sg, bq):
    """Learner-scale target: A: y/sigma ([n]); B: (y - q_base(tau))/sigma ([n,9])."""
    return y / sg if kind == "A" else (y[:, None] - bq) / sg[:, None]


def _to_y(kind: str, ql: np.ndarray, sg, bq):
    """Learner-scale quantiles [n,9] -> y-scale quantiles."""
    return sg[:, None] * ql if kind == "A" else bq + sg[:, None] * ql


def finalize(q: np.ndarray, post_sign: int = 0) -> np.ndarray:
    """Monotone rearrangement (sort the 9 levels) and, post-open, the constraints HO >= 0 / LO <= 0."""
    q = np.sort(q, axis=1)
    if post_sign > 0:
        q = np.maximum(q, 0.0)
    elif post_sign < 0:
        q = np.minimum(q, 0.0)
    return q


def _fold_slices(m: int):
    for f in FOLDS:
        nf = int(f * m)
        v0 = nf + EMBARGO
        v1 = min(m, v0 + int(0.15 * m))
        if v1 - v0 >= 10 and nf >= 40:
            yield nf, v0, v1


def qr_cv_choose(X, y, sg, bq, kind: str, post_sign: int) -> int:
    """Nested expanding-window CV inside the training window: config 0 = null (A: unconditional quantile of y/sigma; B: no correction = baseline), 1..3 = L1 lambda grid.  Lowest mean pinball wins (ties -> null)."""
    m = len(y)
    sc, cnt = np.zeros(1 + len(LAMS)), 0
    for nf, v0, v1 in _fold_slices(m):
        Zf, Zv = prep(X[:nf], X[v0:v1])
        tgt = _target(kind, y[:nf], sg[:nf], bq[:nf])
        yv, sv, bv = y[v0:v1], sg[v0:v1], bq[v0:v1]
        null = _to_y(kind, np.tile(np.quantile(tgt, TAUS), (v1 - v0, 1)) if kind == "A" else np.zeros((v1 - v0, NG)), sv, bv)
        sc[0] += pin_rows(yv, finalize(null, post_sign)).mean()
        for i, lam in enumerate(LAMS):
            a, B = qr_levels(Zf, tgt, lam)
            sc[1 + i] += pin_rows(yv, finalize(_to_y(kind, a[None, :] + Zv @ B.T, sv, bv), post_sign)).mean()
        cnt += 1
    if cnt == 0:
        return 0
    return int(np.argmin(sc))


def qr_fit_predict(X, y, sg, bq, kind: str, cfg: int, Xq, sq, bqq, post_sign: int, want_coef: bool = False):
    """Fit with the chosen config on all training rows, predict query rows (y-scale, rearranged and clipped)."""
    Zt, Zq = prep(X, Xq)
    tgt = _target(kind, y, sg, bq)
    coef = None
    if cfg == 0:
        ql = np.tile(np.quantile(tgt, TAUS), (len(Xq), 1)) if kind == "A" else np.zeros((len(Xq), NG))
    else:
        a, B = qr_levels(Zt, tgt, LAMS[cfg - 1])
        ql = a[None, :] + Zq @ B.T
        coef = B
    out = finalize(_to_y(kind, ql, sq, bqq), post_sign)
    return (out, coef) if want_coef else out


# ---- gradient boosting
def _hgb(tau: float, depth: int, iters: int):
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(loss="quantile", quantile=float(tau), learning_rate=GBM_LR, max_iter=iters, max_depth=depth, min_samples_leaf=GBM_LEAF,
                                         l2_regularization=GBM_L2, max_bins=GBM_BINS, early_stopping=False, random_state=0)


GBM_CFGS = [(d, nt) for d in GBM_DEPTH for nt in GBM_TREES]


def gbm_staged(Ztr, tgt, Zq, depth: int):
    """For one depth, fit the 9 levels with the largest number of trees and return predictions of the query rows at 30/60/120 trees: {nt: [nq,9]}."""
    out = {nt: np.zeros((len(Zq), NG)) for nt in GBM_TREES}
    for k, tau in enumerate(TAUS):
        yk = tgt if tgt.ndim == 1 else tgt[:, k]
        mdl = _hgb(tau, depth, max(GBM_TREES)).fit(Ztr, yk)
        for it, pr in enumerate(mdl.staged_predict(Zq), start=1):
            if it in out:
                out[it][:, k] = pr
    return out


def gbm_cv_choose(X, y, sg, bq, kind: str, post_sign: int):
    """Returns None (null) or (depth, trees)."""
    m = len(y)
    sc = {None: 0.0, **{c: 0.0 for c in GBM_CFGS}}
    cnt = 0
    for nf, v0, v1 in _fold_slices(m):
        Zf, Zv = prep(X[:nf], X[v0:v1])
        tgt = _target(kind, y[:nf], sg[:nf], bq[:nf])
        yv, sv, bv = y[v0:v1], sg[v0:v1], bq[v0:v1]
        null = _to_y(kind, np.tile(np.quantile(tgt, TAUS), (v1 - v0, 1)) if kind == "A" else np.zeros((v1 - v0, NG)), sv, bv)
        sc[None] += pin_rows(yv, finalize(null, post_sign)).mean()
        for dpt in GBM_DEPTH:
            st = gbm_staged(Zf, tgt, Zv, dpt)
            for nt in GBM_TREES:
                sc[(dpt, nt)] += pin_rows(yv, finalize(_to_y(kind, st[nt], sv, bv), post_sign)).mean()
        cnt += 1
    if cnt == 0:
        return None
    return min(sc, key=lambda c: (sc[c], c is not None))


def gbm_fit_predict(X, y, sg, bq, kind: str, cfg, Xq, sq, bqq, post_sign: int):
    Zt, Zq = prep(X, Xq)
    tgt = _target(kind, y, sg, bq)
    if cfg is None:
        ql = np.tile(np.quantile(tgt, TAUS), (len(Xq), 1)) if kind == "A" else np.zeros((len(Xq), NG))
    else:
        dpt, nt = cfg
        ql = np.zeros((len(Xq), NG))
        for k, tau in enumerate(TAUS):
            yk = tgt if tgt.ndim == 1 else tgt[:, k]
            ql[:, k] = _hgb(tau, dpt, nt).fit(Zt, yk).predict(Zq)
    return finalize(_to_y(kind, ql, sq, bqq), post_sign)


# ---- random forest (Meinshausen quantile forest, direct form A)
def rf_fit_predict(X, y, sg, Xq, sq, post_sign: int, seed: int = 0):
    from sklearn.ensemble import RandomForestRegressor
    Zt, Zq = prep(X, Xq)
    u = y / sg
    rf = RandomForestRegressor(random_state=seed, n_jobs=1, **RF_PAR).fit(Zt, u)
    Lt, Lq = rf.apply(Zt), rf.apply(Zq)                       # [m,K], [nq,K]
    order = np.argsort(u)
    us = u[order]
    out = np.zeros((len(Xq), NG))
    for r in range(len(Xq)):
        match = Lt == Lq[r][None, :]
        cnt = match.sum(axis=0).astype(float)
        w = (match / np.maximum(cnt, 1.0)[None, :]).mean(axis=1)[order]
        cw = np.cumsum(w) / w.sum()
        out[r] = us[np.minimum(np.searchsorted(cw, TAUS, side="left"), len(us) - 1)]
    return finalize(sq[:, None] * out, post_sign)


# ---- conformal correction (CQR)
def cqr_shift(scores: np.ndarray) -> np.ndarray:
    """scores [n_cal,9] = (y - q_hat(tau))/sigma on the calibration block -> per level the ceil((n+1) tau)/n empirical quantile (one-sided at each level)."""
    n = len(scores)
    ss = np.sort(scores, axis=0)
    k = np.clip(np.ceil((n + 1) * TAUS).astype(int), 1, n)
    return np.array([ss[k[i] - 1, i] for i in range(NG)])


# ----------------------------------------------------------------------------------------------- one refit block
def _post_sign(ph: str, j: int) -> int:
    return 0 if ph == "pre" else (1 if j == 0 else -1)


QR_VARS = ("V01", "V02", "V03", "V04", "V05", "V06", "V07", "V17", "V18")


def fit_block(ctx: Ctx, ph: str, j: int, b0: int, gcfg: dict, refresh: bool, want_coef: bool = False):
    """Fit every non-stack variant with training rows TR0..b0-1 only and predict the sessions b0..b0+19.  Returns ({variant: [k,9] y-scale quantiles}, diagnostics)."""
    P_ = ctx.ph[ph]
    X, sgA, Y, BQ = P_["X"], P_["sig"], P_["Y"][:, j], P_["BQ"][:, j, :]
    sess = np.arange(b0, min(b0 + REFIT, ctx.N))
    tr = np.arange(TR0, b0)
    ps = _post_sign(ph, j)
    y, sg, bq = Y[tr], sgA[tr], BQ[tr]
    ys, sgs, bqs = Y[sess], sgA[sess], BQ[sess]
    res, diag = {}, {"b0": b0, "n_train": len(tr)}
    for var in QR_VARS:
        _, _, kind, groups = VARIANTS[var]
        cols = ctx.colidx(ph, groups) if var != "V01" else [P_["cols"].index("sig_ln")]
        if var == "V17":
            ivc = P_["cols"].index("iv_rel")
            diag["n_iv_train"] = int(np.isfinite(X[tr][:, ivc]).sum())
            if diag["n_iv_train"] < IV_MIN_TRAIN:
                continue
        bq_t, bq_s = (bq, bqs)
        cfg = qr_cv_choose(X[tr][:, cols], y, sg, bq_t, kind, ps)
        out = qr_fit_predict(X[tr][:, cols], y, sg, bq_t, kind, cfg, X[sess][:, cols], sgs, bq_s, ps, want_coef=want_coef and var in ("V02", "V03"))
        if want_coef and var in ("V02", "V03"):
            out, coef = out
            diag[f"coef_{var}"] = coef
        res[var] = out
        diag[f"cfg_{var}"] = cfg
        diag[f"ncols_{var}"] = len(cols)
    cols_all = ctx.colidx(ph, GROUPS_ALL)
    Xa, Xs = X[tr][:, cols_all], X[sess][:, cols_all]
    # gradient boosting (nested search re-made at the first block of every group of GBM_EVERY refits)
    for var, kind in (("V08", "A"), ("V09", "B")):
        if refresh or var not in gcfg:
            gcfg[var] = gbm_cv_choose(Xa, y, sg, bq, kind, ps)
        res[var] = gbm_fit_predict(Xa, y, sg, bq, kind, gcfg[var], Xs, sgs, bqs, ps)
        diag[f"cfg_{var}"] = gcfg[var]
    res["V10"] = rf_fit_predict(Xa, y, sg, Xs, sgs, ps)
    # conformal repair: calibration block = last min(250, 30%) training rows, base learner on the earlier rows
    ncal = int(min(CQR_CAL, int(0.3 * len(tr))))
    fr_, ca_ = tr[:-ncal], tr[-ncal:]
    ycal, sgcal, bqcal = Y[ca_], sgA[ca_], BQ[ca_]
    sc = (ycal[:, None] - bqcal) / sgcal[:, None]
    res["V11"] = finalize(bqs + sgs[:, None] * cqr_shift(sc)[None, :], ps)
    Xcs = np.vstack([X[ca_][:, cols_all], Xs])
    scs = np.r_[sgcal, sgs]
    cfg12 = qr_cv_choose(X[fr_][:, cols_all], Y[fr_], sgA[fr_], BQ[fr_], "A", ps)
    q12 = qr_fit_predict(X[fr_][:, cols_all], Y[fr_], sgA[fr_], BQ[fr_], "A", cfg12, Xcs, scs, np.zeros((len(scs), NG)), ps)
    sc12 = (ycal[:, None] - q12[:ncal]) / sgcal[:, None]
    res["V12"] = finalize(q12[ncal:] + sgs[:, None] * cqr_shift(sc12)[None, :], ps)
    diag["cfg_V12"] = cfg12
    if refresh or "V13" not in gcfg:
        gcfg["V13"] = gbm_cv_choose(X[fr_][:, cols_all], Y[fr_], sgA[fr_], BQ[fr_], "A", ps)
    q13 = gbm_fit_predict(X[fr_][:, cols_all], Y[fr_], sgA[fr_], BQ[fr_], "A", gcfg["V13"], Xcs, scs, np.zeros((len(scs), NG)), ps)
    sc13 = (ycal[:, None] - q13[:ncal]) / sgcal[:, None]
    res["V13"] = finalize(q13[ncal:] + sgs[:, None] * cqr_shift(sc13)[None, :], ps)
    diag["cfg_V13"] = gcfg["V13"]
    diag["n_cal"] = ncal
    return res, diag


_CTX: Ctx | None = None


def _worker_init():
    try:
        from threadpoolctl import threadpool_limits
        threadpool_limits(limits=1)
    except Exception:                                # noqa: BLE001
        pass


def n_blocks(ctx: Ctx) -> int:
    return int(np.ceil((ctx.N - START) / REFIT))


def run_group(args):
    """One task = (phase, target index, group g of GBM_EVERY consecutive refit blocks)."""
    ph, j, g = args
    ctx = _CTX
    out, dg, gcfg, t0 = {}, [], {}, time.time()
    for b in range(GBM_EVERY * g, min(GBM_EVERY * (g + 1), n_blocks(ctx))):
        b0 = START + REFIT * b
        r, d_ = fit_block(ctx, ph, j, b0, gcfg, refresh=(b == GBM_EVERY * g), want_coef=True)
        d_["block"] = b
        dg.append(d_)
        for v, q in r.items():
            out.setdefault(v, []).append((b0, q))
    return ph, j, g, out, dg, time.time() - t0


# ----------------------------------------------------------------------------------------------- solver validation (own smoothed L-BFGS-B vs scikit-learn / HiGHS)
def validate_solver(n_win: int = 18, seed: int = 7) -> pd.DataFrame:
    from sklearn.linear_model import QuantileRegressor
    _root()
    inp = load_inputs()
    ctx = Ctx(inp)
    rng = np.random.default_rng(seed)
    rows = []
    # ---- synthetic windows with a known sparse truth
    for w in range(6):
        n, p = int(rng.integers(300, 1500)), int(rng.integers(10, 70))
        Xs = rng.standard_normal((n, p))
        beta = np.zeros(p); beta[:3] = [0.6, -0.4, 0.3]
        y = Xs @ beta + rng.standard_t(5, n) * (1 + 0.3 * np.abs(Xs[:, 3]))
        Xte = rng.standard_normal((200, p))
        yte = Xte @ beta + rng.standard_t(5, 200) * (1 + 0.3 * np.abs(Xte[:, 3]))
        for tau in (0.05, 0.5, 0.95):
            for lam in LAMS:
                rows.append(_vs_row("synthetic", w, tau, lam, Xs, y, Xte, yte, QuantileRegressor))
    # ---- real windows: random phase / target / end of training window, 20 held-out next sessions
    for w in range(n_win):
        ph, j = ("pre", "post")[int(rng.integers(0, 2))], int(rng.integers(0, 2))
        e = int(rng.integers(700, ctx.N - 20))
        P_ = ctx.ph[ph]
        cols = ctx.colidx(ph, GROUPS_ALL)
        tr = np.arange(max(TR0, e - 1500), e)
        te = np.arange(e, e + 20)
        Zt, Zq = prep(P_["X"][tr][:, cols], P_["X"][te][:, cols])
        u, uq = P_["Y"][tr, j] / P_["sig"][tr], P_["Y"][te, j] / P_["sig"][te]
        for tau in (0.05, 0.5, 0.95):
            for lam in LAMS:
                rows.append(_vs_row(f"real_{ph}_{('H','L')[j]}", w, tau, lam, Zt, u, Zq, uq, QuantileRegressor))
    return pd.DataFrame(rows)


def _vs_row(kind, w, tau, lam, Zt, y, Zq, yq, QuantileRegressor):
    t0 = time.time()
    th = _qr_one(Zt, y, float(tau), lam)
    p = Zt.shape[1]
    a, b = th[0], th[1:1 + p] - th[1 + p:]
    t1 = time.time() - t0
    t0 = time.time()
    sk = QuantileRegressor(quantile=tau, alpha=lam, solver="highs").fit(Zt, y)
    t2 = time.time() - t0

    def obj(a_, b_):
        r = y - a_ - Zt @ b_
        return float(np.mean(np.maximum(tau * r, (tau - 1) * r)) + lam * np.abs(b_).sum())

    def pl(a_, b_):
        r = yq - a_ - Zq @ b_
        return float(np.mean(np.maximum(tau * r, (tau - 1) * r)))
    o1, o2 = obj(a, b), obj(sk.intercept_, sk.coef_)
    p1, p2 = a + Zq @ b, sk.intercept_ + Zq @ sk.coef_
    return dict(kind=kind, window=w, n=len(y), p=p, tau=tau, lam=lam, obj_own=o1, obj_highs=o2, obj_rel_gap=(o1 - o2) / o2, heldout_pinball_own=pl(a, b), heldout_pinball_highs=pl(sk.intercept_, sk.coef_),
                heldout_rel_diff=(pl(a, b) - pl(sk.intercept_, sk.coef_)) / max(pl(sk.intercept_, sk.coef_), 1e-12), median_abs_pred_diff=float(np.median(np.abs(p1 - p2))), max_abs_pred_diff=float(np.max(np.abs(p1 - p2))),
                nnz_own=int((np.abs(b) > 1e-6).sum()), nnz_highs=int((np.abs(sk.coef_) > 1e-6).sum()), sec_own=t1, sec_highs=t2)


# ----------------------------------------------------------------------------------------------- walk-forward driver and stacks
def run_walkforward(ctx: Ctx, workers: int = 4, cache: Path | None = None, groups_only=None, verbose: bool = True):
    """Run every (phase, target, group) task (cached on disk), return PRED[ph][variant] = [N-START, 2, 9] (NaN where not defined), DIAG list.
    groups_only: optional iterable of group indices (leak test: only the groups needed for one session)."""
    import pickle
    global _CTX
    _CTX = ctx
    nb = n_blocks(ctx)
    ng = int(np.ceil(nb / GBM_EVERY))
    gs = list(range(ng)) if groups_only is None else sorted(set(groups_only))
    tasks = [(ph, j, g) for g in reversed(gs) for ph in ("pre", "post") for j in (0, 1)]
    results, todo = [], []
    for tk in tasks:
        f = None if cache is None else cache / f"{tk[0]}_{tk[1]}_{tk[2]}.pkl"
        if f is not None and f.exists():
            results.append(pickle.load(open(f, "rb")))
        else:
            todo.append(tk)
    if verbose:
        print(f"tasks {len(tasks)}: cached {len(results)}, to run {len(todo)} on {workers} workers", flush=True)
    if todo:
        if cache is not None:
            cache.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        with mp.get_context("fork").Pool(workers, initializer=_worker_init) as pool:
            for k, r in enumerate(pool.imap_unordered(run_group, todo), start=1):
                results.append(r)
                if cache is not None:
                    pickle.dump(r, open(cache / f"{r[0]}_{r[1]}_{r[2]}.pkl", "wb"))
                if verbose:
                    print(f"  done {k}/{len(todo)}  task {r[0]} j={r[1]} g={r[2]}  {r[5]:.0f}s  elapsed {time.time() - t0:.0f}s", flush=True)
    n_e = ctx.N - START
    PRED = {ph: {v: np.full((n_e, 2, NG), np.nan) for v in VARIANTS} for ph in ("pre", "post")}
    DIAG = []
    for ph, j, g, out, dg, _ in results:
        for v, lst in out.items():
            for b0, q in lst:
                PRED[ph][v][b0 - START:b0 - START + len(q), j, :] = q
        for d_ in dg:
            DIAG.append(dict(phase=ph, j=j, **d_))
    return PRED, DIAG


def add_stacks(ctx: Ctx, PRED: dict, blocks=None):
    """V14-V16: quantile-wise convex combination of BASE and a flexible model; the weight (and for V16 the candidate) uses only out-of-sample predictions of the previous <= 250 sessions (>= 60 needed, else BASE)."""
    n_e = ctx.N - START
    log = []
    for ph in ("pre", "post"):
        Y, BQ = ctx.ph[ph]["Y"][START:], ctx.ph[ph]["BQ"][START:]
        for j in (0, 1):
            for b in (range(n_blocks(ctx)) if blocks is None else blocks):
                e0, e1 = REFIT * b, min(REFIT * (b + 1), n_e)
                w0 = max(0, e0 - STACK_WIN)
                base_t = BQ[e0:e1, j, :]
                have = (e0 - w0) >= STACK_MIN
                for var, cand in (("V14", "V02"), ("V15", "V08"), ("V16", None)):
                    w, c = 0.0, cand
                    if have:
                        yv, bq = Y[w0:e0, j], BQ[w0:e0, j, :]
                        if cand is None:
                            sc = {k: pin_rows(yv, PRED[ph][k][w0:e0, j, :]).mean() for k in STACK_POOL}
                            c = min(sc, key=lambda k: sc[k])
                        fl = PRED[ph][c][w0:e0, j, :]
                        s_ = [pin_rows(yv, (1 - w_) * bq + w_ * fl).mean() for w_ in STACK_W]
                        w = float(STACK_W[int(np.argmin(s_))])
                    PRED[ph][var][e0:e1, j, :] = (1 - w) * base_t + w * PRED[ph][c if c else "V02"][e0:e1, j, :]
                    log.append(dict(phase=ph, j=j, block=b, first_session=str(ctx.dates[START + e0].date()), variant=var, weight=w, candidate=c if have else "BASE"))
    return pd.DataFrame(log)


# ----------------------------------------------------------------------------------------------- evaluation tables
def eval_arrays(ctx: Ctx) -> dict:
    d = ctx.d
    idx = np.arange(START, ctx.N)
    dts = ctx.dates[idx]
    return dict(idx=idx, dts=dts, Y={"pre": ctx.ph["pre"]["Y"][idx], "post": ctx.ph["post"]["Y"][idx]}, ref={"pre": d["prev"].values[idx], "post": d["open"].values[idx]},
                hl=d[["high", "low"]].values[idx], BASE={"pre": ctx.ph["pre"]["BQ"][idx], "post": ctx.ph["post"]["BQ"][idx]})


def _emp250(V, idx):
    return np.array([H.emp_q(V, i, 250) for i in idx])


def window_mask(dts, w):
    a, b = H.WIN[w]
    return (dts >= a) & (dts <= b)


def band_widths(q, w_mask):
    """Mean 50% and 90% band widths in rupees at the reference price Rs 3,428 (exp(q) - 1 scaled)."""
    qq = q[w_mask]
    return (PNOW * np.mean(np.exp(qq[:, 5]) - np.exp(qq[:, 3])), PNOW * np.mean(np.exp(qq[:, 7]) - np.exp(qq[:, 1])))


def build_tables(ctx: Ctx, PRED: dict) -> dict:
    """Scores (all windows), DM/Holm family, adoption inputs.  Returns dict of DataFrames and loss arrays."""
    ea = eval_arrays(ctx)
    dts = ea["dts"]
    Qall = {}                               # name -> {'pre': [n,2,9], 'post': [n,2,9]}
    for v in VARIANTS:
        Qall[v] = {ph: PRED[ph][v] for ph in ("pre", "post")}
    Qall["BASE"] = {ph: ea["BASE"][ph] for ph in ("pre", "post")}
    Qall["EMP250"] = {"pre": _emp250(ctx.ph["pre"]["Y"], ea["idx"]), "post": _emp250(ctx.ph["post"]["Y"], ea["idx"])}
    rows, widths = [], []
    for name, Qd in Qall.items():
        for ph in ("pre", "post"):
            Q = Qd[ph]
            ok = np.isfinite(Q).all(axis=(1, 2))
            if ok.sum() == 0:
                continue
            tn = list(TGT[ph])
            for r in H.score_rows(name, Q[ok], ea["Y"][ph][ok], ea["ref"][ph][ok], ea["hl"][ok], dts[ok], tn):
                r["phase"] = ph
                rows.append(r)
            for j, t_ in enumerate(tn):
                for w in WINDOWS:
                    m = window_mask(dts, w) & ok
                    if m.sum() >= 5:
                        b50, b90 = band_widths(Q[:, j, :], m)
                        widths.append(dict(variant=name, target=t_, window=w, band50_rs=b50, band90_rs=b90))
    for nm, ph, ref_zero in (("PRICE_STAYS", "pre", True), ("OPEN_STAYS", "post", True)):
        Z = np.zeros((len(dts), 2, NG))
        for r in H.score_rows(nm, Z, ea["Y"][ph], ea["ref"][ph], ea["hl"], dts, list(TGT[ph])):
            r["phase"] = ph
            for k in ("pinball_x1e4", "pinball_rs_at_now", "cov50", "cov90", "cov90_wilson_lo", "cov90_wilson_hi", "kupiec50", "kupiec90", "below_q5", "above_q95", "p_below_q5", "p_above_q95"):
                r[k] = np.nan
            rows.append(r)
    sc = pd.DataFrame(rows).merge(pd.DataFrame(widths), on=["variant", "target", "window"], how="left")
    # per-session pinball losses (for DM)
    L = {}
    for name, Qd in Qall.items():
        for ph in ("pre", "post"):
            Q = Qd[ph]
            for j, t_ in enumerate(TGT[ph]):
                L[(name, t_)] = np.where(np.isfinite(Q[:, j, :]).all(axis=1), M.pinball(ea["Y"][ph][:, j], np.nan_to_num(Q[:, j, :])), np.nan)
    return dict(scores=sc, L=L, ea=ea, Q=Qall)


def block_boot_gain(lv: np.ndarray, lb: np.ndarray, B: int = 2000, blk: int = 10, seed: int = 11):
    """Moving-block bootstrap 90% interval of the gain 100*(mean lb - mean lv)/mean lb."""
    n = len(lv)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blk))
    starts = rng.integers(0, n - blk + 1, size=(B, nb))
    ix = (starts[:, :, None] + np.arange(blk)[None, None, :]).reshape(B, -1)[:, :n]
    g = 100 * (lb[ix].mean(axis=1) - lv[ix].mean(axis=1)) / lb[ix].mean(axis=1)
    return float(np.percentile(g, 5)), float(np.percentile(g, 95))


def dm_tables(tab: dict) -> pd.DataFrame:
    """DM (HAC lag 5, HLN) of every variant against BASE in Final / Validation / Validation+Final / CAS; Holm over the 72 Final pairs and over the 40 headline pairs."""
    L, ea = tab["L"], tab["ea"]
    dts = ea["dts"]
    rows = []
    for v in VARIANTS:
        for ph in ("pre", "post"):
            for j, t_ in enumerate(TGT[ph]):
                lv, lb = L[(v, t_)], L[("BASE", t_)]
                for w in ("final", "val", "valfinal", "cas"):
                    m = window_mask(dts, w) & np.isfinite(lv)
                    if m.sum() < 20:
                        continue
                    md, tt, p1, p2 = H.dm(lv[m], lb[m])
                    lo, hi = block_boot_gain(lv[m], lb[m]) if w == "final" else (np.nan, np.nan)
                    rows.append(dict(variant=v, name=VARIANTS[v][0], phase=ph, target=t_, window=w, n=int(m.sum()), mean_pinball_var_x1e4=1e4 * lv[m].mean(), mean_pinball_base_x1e4=1e4 * lb[m].mean(),
                                     gain_pct=100 * md / lb[m].mean(), dm_t=tt, p_two_sided=p2, boot90_lo=lo, boot90_hi=hi))
    df = pd.DataFrame(rows)
    df["holm72_final"] = np.nan
    df["holm40_headline_final"] = np.nan
    m = df.window == "final"
    df.loc[m, "holm72_final"] = H.holm(df.loc[m, "p_two_sided"].values)
    mh = m & df.variant.isin(HEADLINE)
    df.loc[mh, "holm40_headline_final"] = H.holm(df.loc[mh, "p_two_sided"].values)
    return df


# ----------------------------------------------------------------------------------------------- adoption rule
def adoption_table(tab: dict, dm: pd.DataFrame, leak: dict | None) -> pd.DataFrame:
    """The pre-fixed rule (report 0.6), one row per variant x target, every condition shown."""
    sc = tab["scores"]
    rows = []
    for v in VARIANTS:
        for ph in ("pre", "post"):
            for t_ in TGT[ph]:
                def S(variant, w, col):
                    x = sc[(sc.variant == variant) & (sc.target == t_) & (sc.window == w)]
                    return float(x[col].iloc[0]) if len(x) else np.nan
                def D(w, col):
                    x = dm[(dm.variant == v) & (dm.target == t_) & (dm.window == w)]
                    return float(x[col].iloc[0]) if len(x) else np.nan
                g_f, g_v, g_c = D("final", "gain_pct"), D("val", "gain_pct"), D("cas", "gain_pct")
                h72, praw = D("final", "holm72_final"), D("final", "p_two_sided")
                c1 = bool(np.isfinite(g_f) and g_f >= 2.0 and np.isfinite(h72) and h72 < 0.05)
                c2 = bool(np.isfinite(g_v) and g_v > 0) and v != "V17"
                dist = lambda x, nom: abs(x - nom)                                                          # noqa: E731
                c50 = dist(S(v, "final", "cov50"), 0.5) <= dist(S("BASE", "final", "cov50"), 0.5) + 1e-12 and S(v, "final", "kupiec50") > 0.05
                if t_ == "HO":
                    c90 = dist(S(v, "final", "above_q95"), 0.05) <= dist(S("BASE", "final", "above_q95"), 0.05) + 1e-12 and S(v, "final", "p_above_q95") > 0.05
                else:
                    c90 = dist(S(v, "final", "cov90"), 0.9) <= dist(S("BASE", "final", "cov90"), 0.9) + 1e-12 and S(v, "final", "kupiec90") > 0.05
                c3 = bool(c50 and c90)
                pv, pb = S(v, "cas", "pinball_x1e4"), S("BASE", "cas", "pinball_x1e4")
                c4 = bool(np.isfinite(pv) and pv <= 1.05 * pb)
                c5 = None if leak is None else bool(leak.get(v, False))
                rows.append(dict(variant=v, name=VARIANTS[v][0], target=t_, n_final=int(D("final", "n")), gain_final_pct=g_f, p_raw_final=praw, holm72_final=h72, cond_i_gain2_and_holm=c1,
                                 gain_val_pct=g_v, cond_ii_val_same_sign=c2, cov50=S(v, "final", "cov50"), cov50_base=S("BASE", "final", "cov50"), kupiec50=S(v, "final", "kupiec50"),
                                 cov90=S(v, "final", "cov90"), cov90_base=S("BASE", "final", "cov90"), kupiec90=S(v, "final", "kupiec90"), above_q95=S(v, "final", "above_q95"),
                                 above_q95_base=S("BASE", "final", "above_q95"), p_above_q95=S(v, "final", "p_above_q95"), cond_iii_coverage=c3, gain_cas_pct=g_c, cas_pinball=pv, cas_pinball_base=pb,
                                 cond_iv_cas_not_5pct_worse=c4, cond_v_leakage=c5,
                                 adopt=bool(c1 and c2 and c3 and c4 and (c5 is True)) if v not in ("V18",) else False, note="timing sensitivity, ineligible for adoption" if v == "V18" else ("short IV sample: rule (ii) cannot be met" if v == "V17" else "")))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------- leakage test
LEAK_DATES = ("2022-03-21", "2023-09-14", "2025-05-23", "2025-11-12", "2026-05-14", "2026-09-16")


def leak_test(inp: dict, clean_pred: dict, dates=LEAK_DATES, workers: int = 4) -> pd.DataFrame:
    """For each test session t: replace ALL data dated t and later by junk (open of t kept for the post-open model), rebuild the whole pipeline (features, S6 volatility, baseline quantiles, every
    variant incl. the stacks over the preceding 14 refit blocks) and compare the forecasts of session t with the stored clean walk-forward forecasts.  Positive control: forecasts of LATER sessions of the same block must change."""
    ctx0 = Ctx(inp)
    rows = []
    for ds in dates:
        t = ctx0.dates.get_loc(pd.Timestamp(ds))
        e_t = t - START
        b = e_t // REFIT
        g_hi, g_lo = b // GBM_EVERY, max(0, b - 13) // GBM_EVERY
        jn = junk_inputs(inp, t)
        ctxj = Ctx(jn)
        PJ, _ = run_walkforward(ctxj, workers=workers, cache=None, groups_only=range(g_lo, g_hi + 1), verbose=False)
        add_stacks(ctxj, PJ, blocks=[b])
        e1 = min((b + 1) * REFIT, ctx0.N - START)
        for v in VARIANTS:
            for ph in ("pre", "post"):
                for j, tn in enumerate(TGT[ph]):
                    a, c = PJ[ph][v][e_t, j], clean_pred[ph][v][e_t, j]
                    if np.isnan(c).all() and np.isnan(a).all():
                        same, md = True, 0.0
                    else:
                        same = bool(np.allclose(a, c, rtol=1e-9, atol=1e-12, equal_nan=True))
                        md = float(np.nanmax(np.abs(a - c))) if np.isfinite(a).any() and np.isfinite(c).any() else np.nan
                    later_a, later_c = PJ[ph][v][e_t + 1:e1, j], clean_pred[ph][v][e_t + 1:e1, j]
                    moved = bool(len(later_a) and not np.allclose(later_a, later_c, rtol=1e-9, atol=1e-12, equal_nan=True))
                    rows.append(dict(session=ds, session_index=t, block=b, position_in_block=e_t - b * REFIT, variant=v, phase=ph, target=tn, identical=same, max_abs_diff=md, later_sessions_in_block=int(e1 - e_t - 1), later_forecasts_changed=moved))
        print(f"leak test {ds}: all identical = {all(r['identical'] for r in rows if r['session'] == ds)}", flush=True)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------- permutation importance (training windows only) and partial-dependence style readings
IMP_BLOCKS = (30, 40, 50, 60, 70, 80)
IMP_REPS, IMP_NOISE = 10, 3


def _imp_one(args):
    """Permutation importance inside ONE training window: fit on the first 70% of the rows before block b, evaluate (loss increase when one feature, or one group of features, is shuffled) on the
    last 30% of the same training window (5-session embargo).  Direct form A, forced mid-strength settings (QR lambda 0.01; boosting depth 2, 60 trees) so that importance is shown
    even when the nested search would have chosen 'do nothing'.  Three pure-noise columns give the noise floor."""
    ph, j, b = args
    ctx = _CTX
    P_ = ctx.ph[ph]
    b0 = START + REFIT * b
    tr = np.arange(TR0, b0)
    m = len(tr)
    nf = int(0.7 * m)
    fit, ev = tr[:nf], tr[nf + EMBARGO:]
    cols = ctx.colidx(ph, GROUPS_ALL)
    names = [P_["cols"][c] for c in cols]
    grp = [P_["grp"][n] for n in names]
    rng = np.random.default_rng(1000 + b)
    noise = rng.standard_normal((ctx.N, IMP_NOISE))
    Xall = np.hstack([P_["X"][:, cols], noise])
    names_all = names + [f"noise{k}" for k in range(IMP_NOISE)]
    grp_all = grp + ["NOISE"] * IMP_NOISE
    ps = _post_sign(ph, j)
    y, sg = P_["Y"][:, j], P_["sig"]
    Zf, Ze = prep(Xall[fit], Xall[ev])
    u = y[fit] / sg[fit]
    out = []
    for mdl in ("QR_lam0.01", "GBM_d2_t60"):
        if mdl.startswith("QR"):
            a, B = qr_levels(Zf, u, 0.01)
            predict = lambda Z, a=a, B=B: a[None, :] + Z @ B.T                                              # noqa: E731
        else:
            ms = [_hgb(tau, 2, 60).fit(Zf, u) for tau in TAUS]
            predict = lambda Z, ms=ms: np.column_stack([mm.predict(Z) for mm in ms])                      # noqa: E731
        loss = lambda Z: pin_rows(y[ev], finalize(sg[ev][:, None] * predict(Z), ps)).mean()               # noqa: E731
        l0 = loss(Ze)
        items = [(n, [k]) for k, n in enumerate(names_all)]
        for g in sorted(set(grp_all)):
            items.append((f"GROUP:{g}", [k for k, gg in enumerate(grp_all) if gg == g]))
        for nm, ks in items:
            inc = []
            for r in range(IMP_REPS):
                perm = np.random.default_rng(10 * b + r).permutation(len(ev))
                Zp = Ze.copy()
                Zp[:, ks] = Ze[perm][:, ks]
                inc.append(loss(Zp) - l0)
            out.append(dict(phase=ph, j=j, target=TGT[ph][j], block=b, snapshot_start=str(ctx.dates[b0].date()), model=mdl, feature=nm, group="GROUP" if nm.startswith("GROUP:") else grp_all[names_all.index(nm)],
                            n_fit=len(fit), n_eval=len(ev), heldout_pinball_x1e4=1e4 * l0, importance_x1e4=1e4 * float(np.mean(inc))))
    return out


def importance_run(ctx: Ctx, workers: int = 4) -> pd.DataFrame:
    global _CTX
    _CTX = ctx
    tasks = [(ph, j, b) for b in IMP_BLOCKS for ph in ("pre", "post") for j in (0, 1)]
    rows = []
    with mp.get_context("fork").Pool(workers, initializer=_worker_init) as pool:
        for r in pool.imap_unordered(_imp_one, tasks):
            rows += r
    return pd.DataFrame(rows)


def pdp_run(ctx: Ctx, top: dict) -> pd.DataFrame:
    """Descriptive, in-sample 'what does the fitted model say' table.  For each target the direct models (QR lambda 0.01; boosting depth 2 / 60 trees) are fitted on ALL known sessions; one feature is moved from
    its 10th to its 90th training percentile with every other feature at its training median.  Reports the model's 50% and extreme-tail quantile in units of sigma at both values and the relative stretch.
    This is a reading of the fitted model, not a test and not an out-of-sample claim."""
    rows = []
    for ph in ("pre", "post"):
        P_ = ctx.ph[ph]
        cols = ctx.colidx(ph, GROUPS_ALL)
        names = [P_["cols"][c] for c in cols]
        tr = np.arange(TR0, ctx.N)
        for j in (0, 1):
            tn = TGT[ph][j]
            y, sg = P_["Y"][:, j], P_["sig"]
            Zt, = prep(P_["X"][tr][:, cols])
            u = y[tr] / sg[tr]
            a, B = qr_levels(Zt, u, 0.01)
            ms = [_hgb(tau, 2, 60).fit(Zt, u) for tau in TAUS]
            ext = 7 if j == 0 else 1                                                                       # 95% quantile for highs, 5% quantile for lows
            for feat in top.get((ph, j), []):
                k = names.index(feat)
                lo_v, hi_v = np.percentile(Zt[:, k], 10), np.percentile(Zt[:, k], 90)
                raw = P_["X"][tr][:, cols][:, k]
                r10, r90 = np.nanpercentile(raw, 10), np.nanpercentile(raw, 90)
                for mdl in ("QR_lam0.01", "GBM_d2_t60"):
                    qs = []
                    for val in (lo_v, hi_v):
                        z = np.zeros((1, len(cols)))
                        z[0, k] = val
                        q = (a[None, :] + z @ B.T) if mdl.startswith("QR") else np.column_stack([mm.predict(z) for mm in ms])
                        qs.append(np.sort(q[0]))
                    rows.append(dict(phase=ph, target=tn, feature=feat, model=mdl, raw_p10=r10, raw_p90=r90, q50_sigma_at_p10=qs[0][4], q50_sigma_at_p90=qs[1][4], ext_level=float(TAUS[ext]), ext_sigma_at_p10=qs[0][ext],
                                     ext_sigma_at_p90=qs[1][ext], ext_change_pct=100 * (qs[1][ext] / qs[0][ext] - 1) if abs(qs[0][ext]) > 1e-9 else np.nan, q50_change_sigma=qs[1][4] - qs[0][4]))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------- result files
def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    raise TypeError(type(o))


def choices_table(DIAG: list, ctx: Ctx) -> pd.DataFrame:
    rows = []
    for d_ in DIAG:
        b0 = d_["b0"]
        win = "final" if ctx.dates[b0] >= pd.Timestamp("2025-07-01") else ("val" if ctx.dates[b0] >= pd.Timestamp("2024-07-01") else "dev")
        for k, v in d_.items():
            if k.startswith("cfg_"):
                rows.append(dict(variant=k[4:], phase=d_["phase"], target=TGT[d_["phase"]][d_["j"]], block=d_["block"], first_session=str(ctx.dates[b0].date()), window=win, config=str(v), null=(v in (0, None))))
    df = pd.DataFrame(rows)
    return df


def coef_summary(DIAG: list, ctx: Ctx) -> pd.DataFrame:
    rows = []
    cols_all = {ph: [ctx.ph[ph]["cols"][c] for c in ctx.colidx(ph, GROUPS_ALL)] for ph in ("pre", "post")}
    for ph in ("pre", "post"):
        for j in (0, 1):
            for var in ("V02", "V03"):
                cs = [d_[f"coef_{var}"] for d_ in DIAG if d_["phase"] == ph and d_["j"] == j and f"coef_{var}" in d_ and d_[f"coef_{var}"] is not None
                      and ctx.dates[d_["b0"]] >= pd.Timestamp("2025-07-01")]
                nb_all = sum(1 for d_ in DIAG if d_["phase"] == ph and d_["j"] == j and ctx.dates[d_["b0"]] >= pd.Timestamp("2025-07-01"))
                if not cs:
                    continue
                C = np.stack(cs)                                       # [blocks_with_fit, 9, p]
                ext = 7 if j == 0 else 1
                for k, nm in enumerate(cols_all[ph]):
                    rows.append(dict(phase=ph, target=TGT[ph][j], variant=var, feature=nm, group=ctx.ph[ph]["grp"][nm], final_blocks=nb_all, blocks_with_nonnull_fit=len(cs),
                                     mean_abs_coef_q50=float(np.abs(C[:, 4, k]).mean()), mean_coef_q50=float(C[:, 4, k].mean()), mean_abs_coef_ext=float(np.abs(C[:, ext, k]).mean()),
                                     mean_coef_ext=float(C[:, ext, k].mean()), ext_level=float(TAUS[ext]), share_blocks_nonzero_q50=float((np.abs(C[:, 4, k]) > 1e-6).mean())))
    return pd.DataFrame(rows)


def write_oos(ctx: Ctx, tab: dict, PRED: dict) -> pd.DataFrame:
    """Compact out-of-sample forecasts used by the live stack and for audit: Final window, all variants + BASE; Validation window, the stack ingredients + BASE."""
    ea = tab["ea"]
    dts = ea["dts"]
    rows = []
    for ph in ("pre", "post"):
        for j, tn in enumerate(TGT[ph]):
            for v in ["BASE"] + list(VARIANTS):
                Q = tab["Q"][v][ph][:, j, :]
                for w, keep in (("final", True), ("val", v in ("BASE",) + STACK_POOL)):
                    if not keep:
                        continue
                    m = window_mask(dts, w) & np.isfinite(Q).all(axis=1)
                    for i in np.where(m)[0]:
                        rows.append([str(dts[i].date()), w, ph, tn, v, ea["Y"][ph][i, j]] + [float(x) for x in Q[i]])
    return pd.DataFrame(rows, columns=["date", "window", "phase", "target", "variant", "y_realised"] + [f"q{g * 100:g}" for g in GRID])


def write_results(ctx: Ctx, PRED: dict, DIAG: list, slog: pd.DataFrame, leak: pd.DataFrame | None = None, tag: str = "hl3") -> dict:
    OUT.mkdir(exist_ok=True)
    tab = build_tables(ctx, PRED)
    dm = dm_tables(tab)
    leak_ok = None
    if leak is not None:
        leak_ok = {v: bool(leak[leak.variant == v].identical.all()) for v in VARIANTS}
    ad = adoption_table(tab, dm, leak_ok)
    sc = tab["scores"].copy()
    sc["name"] = sc["variant"].map({k: v[0] for k, v in VARIANTS.items()} | {"BASE": "baseline (P_S6 / W_I6)", "EMP250": "trailing-250 empirical", "PRICE_STAYS": "price stays", "OPEN_STAYS": "open stays"})
    keep = ["variant", "name", "phase", "target", "window", "n", "pinball_x1e4", "cov50", "cov90", "kupiec50", "kupiec90", "below_q5", "above_q95", "p_above_q95", "mae_med_pct", "medae_med_pct", "mae_med_rs_at_now",
            "mae_med_se_rs_at_now", "medae_med_rs_at_now", "mae_med_rs_traded", "band50_rs", "band90_rs"]
    sc[keep].to_csv(OUT / f"{tag}_eval_variants.csv", index=False)
    dm.to_csv(OUT / f"{tag}_dm_holm.csv", index=False)
    ad.to_csv(OUT / f"{tag}_adoption.csv", index=False)
    ch = choices_table(DIAG, ctx)
    ch.to_csv(OUT / f"{tag}_choices_by_block.csv", index=False)
    if len(ch):
        cs = ch.groupby(["variant", "phase", "target", "window", "config"]).size().rename("n_blocks").reset_index()
        cs["share_of_window_blocks"] = cs["n_blocks"] / cs.groupby(["variant", "phase", "target", "window"])["n_blocks"].transform("sum")
        cs.to_csv(OUT / f"{tag}_choices.csv", index=False)
    slog.to_csv(OUT / f"{tag}_stack_weights.csv", index=False)
    coef_summary(DIAG, ctx).to_csv(OUT / f"{tag}_coef_summary.csv", index=False)
    write_oos(ctx, tab, PRED).to_csv(OUT / f"{tag}_oos_predictions.csv", index=False)
    if leak is not None:
        leak.to_csv(OUT / f"{tag}_leakage.csv", index=False)
    # ---- baseline reproduction check against the stored project tables
    ref = pd.concat([pd.read_csv(OUT / "hl_eval_preopen.csv").query("variant == 'P_S6'"), pd.read_csv(OUT / "hl_eval_postopen.csv").query("variant == 'W_I6'")])
    mine = sc[sc.variant == "BASE"]
    mg = mine.merge(ref, on=["target", "window"], suffixes=("", "_stored"))
    chk = []
    for c in ("pinball_x1e4", "cov50", "cov90", "mae_med_rs_at_now", "medae_med_rs_at_now", "kupiec90"):
        chk.append(dict(column=c, rows=len(mg), max_abs_diff_vs_stored=float(np.abs(mg[c] - mg[c + "_stored"]).max())))
    pd.DataFrame(chk).to_csv(OUT / f"{tag}_baseline_check.csv", index=False)
    # ---- pinball by calendar year (descriptive)
    ea, L = tab["ea"], tab["L"]
    yrs = ea["dts"].year
    by = []
    for v in list(VARIANTS) + ["EMP250"]:
        for tn in ("H", "L", "HO", "LO"):
            lv, lb = L[(v, tn)], L[("BASE", tn)]
            for y_ in sorted(set(yrs)):
                m = (yrs == y_) & np.isfinite(lv)
                if m.sum() >= 20:
                    by.append(dict(variant=v, target=tn, year=int(y_), n=int(m.sum()), pinball_x1e4=1e4 * lv[m].mean(), base_x1e4=1e4 * lb[m].mean(), gain_pct=100 * (lb[m].mean() - lv[m].mean()) / lb[m].mean()))
    pd.DataFrame(by).to_csv(OUT / f"{tag}_byyear.csv", index=False)
    return dict(tab=tab, dm=dm, ad=ad, sc=sc, ch=ch)


# ----------------------------------------------------------------------------------------------- live / replay forecast
PCT_KEYS = {"q2.5": 0, "q5": 1, "q10": 2, "q25": 3, "q50": 4, "q75": 5, "q90": 6, "q95": 7, "q97.5": 8}


def _live_task(args):
    ph, j = args
    ctx = _CTX
    res, diag = fit_block(ctx, ph, j, ctx.N - 1, {}, True)
    return ph, j, res, {k: v for k, v in diag.items() if not str(k).startswith("coef")}


def _stack_live(ph: str, tn: str, date, base_q: np.ndarray, flex: dict) -> dict:
    """V14-V16 for a live session from the stored out-of-sample forecasts (results/hl3_oos_predictions.csv): the last <= 250 sessions before `date`."""
    f = OUT / "hl3_oos_predictions.csv"
    if not f.exists():
        return {}
    oos = pd.read_csv(f, parse_dates=["date"])
    sub = oos[(oos.phase == ph) & (oos.target == tn) & (oos.date < pd.Timestamp(date))]
    ds = sorted(sub.date.unique())[-STACK_WIN:]
    sub = sub[sub.date.isin(ds)].sort_values("date")
    qcols = [c for c in sub.columns if c.startswith("q")]
    piv = {v: g.set_index("date")[qcols].reindex(ds).values for v, g in sub.groupby("variant")}
    yv = sub[sub.variant == "BASE"].set_index("date")["y_realised"].reindex(ds).values
    out = {}
    for var, cand in (("V14", "V02"), ("V15", "V08"), ("V16", None)):
        w, c = 0.0, cand
        if len(ds) >= STACK_MIN and "BASE" in piv and all(k in piv for k in STACK_POOL):
            if cand is None:
                sc = {k: pin_rows(yv, piv[k]).mean() for k in STACK_POOL}
                c = min(sc, key=lambda k: sc[k])
            s_ = [pin_rows(yv, (1 - w_) * piv["BASE"] + w_ * piv[c]).mean() for w_ in STACK_W]
            w = float(STACK_W[int(np.argmin(s_))])
        out[var] = ((1 - w) * base_q + w * flex[c if c else "V02"], w, c)
    return out


def _side_out(variant: str, tn: str, ref: float, q: np.ndarray) -> dict:
    px = {k: round(float(ref * np.exp(q[g])), 2) for k, g in PCT_KEYS.items()}
    out = {"variant": variant, "price_quantiles": px, "pct_of_reference": {k: round(100 * float(np.exp(q[g]) - 1), 2) for k, g in PCT_KEYS.items()},
           "band_width_rs": {"50%": round(px["q75"] - px["q25"], 1), "90%": round(px["q95"] - px["q5"], 1)}}
    f = OUT / "hl3_eval_variants.csv"
    if f.exists():
        r = pd.read_csv(f)
        x = r[(r.variant == variant) & (r.target == tn) & (r.window == "final")]
        if not x.empty:
            out.update(typical_miss_rs=round(float(x.mae_med_pct.iloc[0]) / 100 * ref, 1), half_the_time_within_rs=round(float(x.medae_med_pct.iloc[0]) / 100 * ref, 1), miss_measured_on_sessions=int(x.n.iloc[0]))
    return out


def _display_variant(tn: str) -> str:
    """Best flexible variant for display (descriptive choice, NOT an adoption): lowest pooled Validation+Final pinball among V01-V16; 'V03' when no evaluation file exists."""
    f = OUT / "hl3_eval_variants.csv"
    if not f.exists():
        return "V03"
    r = pd.read_csv(f)
    r = r[(r.target == tn) & (r.window == "valfinal") & r.variant.isin([v for v in VARIANTS if v not in ("V17", "V18")])]
    return str(r.sort_values("pinball_x1e4").variant.iloc[0]) if len(r) else "V03"


def ml_forecast(date, open_price=None, workers: int = 4, inp: dict | None = None) -> dict:
    """Forecast of the session high / low on `date` from the flexible models, using only sessions before `date` (and `open_price` = official open, final 09:08 IST, for the post-open part).
    Mirrors hl_model.hl_forecast: out['pre_open'] / out['post_open'] hold the DISPLAY variant (best flexible, descriptive, NOT adopted unless results/hl3_adoption.csv says so); out['base'] holds the baseline."""
    global _CTX
    _root()
    date = pd.Timestamp(date)
    inp = load_inputs() if inp is None else inp
    inp = dict(inp)
    inp["d"] = inp["d"][inp["d"].index < date]
    n = len(inp["d"])
    P0 = float(inp["d"]["close"].iloc[-1])
    if open_price is not None and abs(np.log(open_price / P0)) > 0.2:
        raise ValueError("open more than 20% from the previous close: check the number")
    ctx = Ctx(extend_live(inp, date, open_price), live=True)
    _CTX = ctx
    phases = ["pre"] + (["post"] if open_price is not None else [])
    tasks = [(ph, j) for ph in phases for j in (0, 1)]
    with mp.get_context("fork").Pool(min(workers, len(tasks)), initializer=_worker_init) as pool:
        got = pool.map(_live_task, tasks)
    Q = {ph: {v: np.full((2, NG), np.nan) for v in VARIANTS} for ph in phases}
    for ph, j, res, _ in got:
        for v, q in res.items():
            Q[ph][v][j] = q[0]
    base = {ph: ctx.ph[ph]["BQ"][n] for ph in phases}                                   # [2,9]
    sl = {}
    for ph in phases:
        for j, tn in enumerate(TGT[ph]):
            s = _stack_live(ph, tn, date, base[ph][j], {v: Q[ph][v][j] for v in STACK_POOL})
            for var, (q, w, c) in s.items():
                Q[ph][var][j] = q
                sl[(ph, tn, var)] = (w, c)
    adopted = {}
    f = OUT / "hl3_adoption.csv"
    if f.exists():
        a = pd.read_csv(f)
        adopted = {(r.variant, r.target): bool(r.adopt) for r in a.itertuples()}
    ref = {"pre": P0, "post": float(open_price) if open_price is not None else None}
    miss_in = [f"{c}" for c in ctx.ph["pre"]["cols"] if not np.isfinite(ctx.ph["pre"]["X"][n][ctx.ph["pre"]["cols"].index(c)])]
    out = {"date": str(date.date()), "p0": P0, "data_through": str(inp["d"].index[-1].date()), "n_sessions": n, "is_weekend": bool(date.dayofweek >= 5),
           "missing_weekdays_between_data_and_date": [str(x.date()) for x in pd.bdate_range(inp["d"].index[-1] + pd.Timedelta(days=1), date - pd.Timedelta(days=1))],
           "sigma_R_pct": 100 * float(ctx.ph["pre"]["sig"][n]), "model": "flexible models on the feature menu (research/hl/E_quantile.md); trained on sessions before the date only; display variant = best pooled Validation+Final pinball, DESCRIPTIVE, not an adoption",
           "inputs_missing_today_treated_as_no_information": miss_in}
    if open_price is not None:
        out["open"], out["gap_pct"], out["sigma_I_pct"] = float(open_price), 100 * float(np.log(open_price / P0)), 100 * float(ctx.ph["post"]["sig"][n])
    def blk(ph, which):
        r = {}
        for j, (k, tn) in enumerate(zip(("high", "low"), TGT[ph])):
            v = "BASE" if which == "base" else _display_variant(tn)
            q = base[ph][j] if which == "base" else Q[ph][v][j]
            r[k] = _side_out(v, tn, ref[ph], q)
            r[k]["adopted_by_prefixed_rule"] = False if which == "base" else adopted.get((v, tn), False)
        return r
    out["pre_open"], out["base"] = blk("pre", "flex"), {"pre_open": blk("pre", "base")}
    if open_price is not None:
        out["post_open"], out["base"]["post_open"] = blk("post", "flex"), blk("post", "base")
    out["variants"] = {v: {ph: {k: {g: round(float(ref[ph] * np.exp(Q[ph][v][j][i])), 2) for g, i in PCT_KEYS.items()} for j, k in enumerate(("high", "low"))} for ph in phases} for v in VARIANTS}
    out["stack_weights"] = {f"{ph}/{tn}/{var}": {"weight_on_flexible": w, "flexible_model": c} for (ph, tn, var), (w, c) in sl.items()}
    return out


# ----------------------------------------------------------------------------------------------- command line
def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validate-solver", action="store_true")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--leak", action="store_true")
    ap.add_argument("--importance", action="store_true")
    ap.add_argument("--date")
    ap.add_argument("--open", type=float)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", default=str(SCRATCH / "wf_cache"))
    a = ap.parse_args()
    _root()
    import pickle
    if a.validate_solver:
        df = validate_solver()
        df.to_csv(OUT / "hl3_solver_validation.csv", index=False)
        print(df.groupby("kind")[["obj_rel_gap", "heldout_rel_diff", "median_abs_pred_diff", "sec_own", "sec_highs"]].mean().to_string())
    if a.eval:
        inp = load_inputs()
        ctx = Ctx(inp)
        PRED, DIAG = run_walkforward(ctx, workers=a.workers, cache=Path(a.cache))
        slog = add_stacks(ctx, PRED)
        SCRATCH.mkdir(parents=True, exist_ok=True)
        pickle.dump(dict(PRED=PRED, DIAG=DIAG, slog=slog, N=ctx.N), open(SCRATCH / "wf_result.pkl", "wb"))
        leak = pd.read_csv(OUT / "hl3_leakage.csv") if (OUT / "hl3_leakage.csv").exists() else None
        write_results(ctx, PRED, DIAG, slog, leak)
        print("results written to results/hl3_*.csv")
    if a.leak:
        inp = load_inputs()
        res = pickle.load(open(SCRATCH / "wf_result.pkl", "rb"))
        lk = leak_test(inp, res["PRED"], workers=a.workers)
        lk.to_csv(OUT / "hl3_leakage.csv", index=False)
        print(lk.groupby("variant").identical.all().to_string())
    if a.importance:
        inp = load_inputs()
        ctx = Ctx(inp)
        imp = importance_run(ctx, workers=a.workers)
        imp.to_csv(OUT / "hl3_importance.csv", index=False)
        agg = imp[imp.group != "GROUP"].groupby(["phase", "target", "model", "feature", "group"]).importance_x1e4.mean().reset_index()
        top = {}
        for (ph, tn), g in agg[agg.model == "QR_lam0.01"].groupby(["phase", "target"]):
            gg = g[g.group != "NOISE"].sort_values("importance_x1e4", ascending=False)
            top[(ph, TGT[ph].index(tn))] = list(gg.feature.head(6))
        pdp = pdp_run(ctx, top)
        pdp.to_csv(OUT / "hl3_pdp.csv", index=False)
        print("importance and pdp written")
    if a.date:
        f = ml_forecast(a.date, a.open, workers=a.workers)
        txt = json.dumps(f, indent=1, default=_json_default)
        print(txt[:6000])
        if a.save:
            (OUT / f"hl3_{a.date}.json").write_text(txt)


if __name__ == "__main__":
    main()
