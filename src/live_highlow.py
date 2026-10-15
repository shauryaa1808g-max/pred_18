"""Live running high / low estimate for NSE:BSE: where will today's OFFICIAL day high and day low end up, given what the price has done so far?

Idea (descriptive; it does NOT predict direction).  The final high is at least the running high so far (M) and the final low at most the running low (N).  How far they usually
extend depends on how much variance is left in the session.  Model: from now to about 15:15 the log price is a driftless random walk whose variance follows the time-of-day
profile of src/live_nowcast.py (15-minute slots, estimated on the post-closing-auction sessions); then ONE closing-auction print (slot 24, variance ev[24]) sets the close.
With s_c^2 = remaining continuous variance, s_J^2 = auction-jump variance, sigma_W^2 = s_c^2 + s_J^2, the maximum of the remaining path (log, relative to the price now) has the exact CDF
        F(b) = Phi(b / s_c) + Phi(b / sigma_W) - 1,   b >= 0
(reflection principle for the continuous part; the auction print is monitored once, so by the strong Markov property P(end above b | path touched b) = 1/2 still holds; checked against Monte-Carlo
in --selftest).  Final Yahoo-bars high = max(M, P * exp(future max)); P(high already in) = F(ln(M/P)); the low is the mirror image.  All scales are multiplied by one volatility multiplier c,
calibrated by leave-one-session-out (--backtest).  The NSE official high / low is the Yahoo extreme moved outwards by a small offset (measured on 39 sessions: median Rs 0.2 / 0.7, up to Rs 5);
the printed quantiles convolve the model distribution with that empirical offset ('M1c' in the report).  Report: research/hl/B_liveintraday.md.

Usage (repo root):
  python3 src/live_highlow.py                    # fetch Yahoo 1-minute bars now, print the estimate in plain words, log it to results/live_hl_log.jsonl
  python3 src/live_highlow.py --asof 12:30       # replay the last session as of 12:30 (bars that STARTED before 12:30 only, as live_nowcast does)
  python3 src/live_highlow.py --replay           # table for the last completed session (results/live_hl_replay_latest.csv)
  python3 src/live_highlow.py --backtest         # nested leave-one-session-out (15-minute) + walk-forward (hourly) evaluation; writes results/live_hl_*.csv/json  (needs --hourly <h60 json> once)
  python3 src/live_highlow.py --selftest         # closed form vs Monte-Carlo, profile vs live_nowcast.profile, state check, no-leak test
  python3 src/live_highlow.py --now "2026-10-17 10:00"   # TEST ONLY: pretend the clock (weekend / before-open / holiday / after-close messages)
Handled: Yahoo 429 or bad JSON (query2 then query1 with back-off, then the cached bars in results/live_hl_bars_1m.csv), weekends, no bars today (holiday / before 09:15), after the close (all bars used).
Data: Yahoo chart API 1-minute bars (unofficial), official daily bars from data/processed (read only; bse_daily.csv ends 13 Oct, bse_daily_extra.csv carries 14-15 Oct).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import live_nowcast as LN  # noqa: E402  (reused: yahoo_1m, rows_1m, to_15m, profile, load_history)
import metrics as M  # noqa: E402
from common import GRID, load_bse  # noqa: E402

IST = LN.IST
NB = LN.NB                                   # 25 fifteen-minute slots; slot 24 (15:15-15:30) holds the closing-auction print
TAUS = np.asarray(GRID, float)               # 0.025 ... 0.975 (the project's 9-level grid)
NT = len(TAUS)
CGRID = np.round(np.arange(0.50, 2.0001, 0.025), 4)
RS = 3400.0                                  # rupees per unit of log price used for pooled loss tables (BSE trades near Rs 3,400)
PARAMS = "results/live_hl_params.json"
LOG = "results/live_hl_log.jsonl"
BARS1M = "results/live_hl_bars_1m.csv"
HOURLY_CSV = "results/live_hl_hourly_bars.csv"
CAS_START = "2026-08-03"
CHECK15 = {"09:45": 2, "10:30": 5, "11:30": 9, "12:30": 13, "13:15": 16, "14:00": 19, "14:30": 21, "15:00": 23}
CHECKH = {"10:15": 1, "11:15": 2, "12:15": 3, "13:15": 4, "14:15": 5, "15:15": 6}


# =============================================================================================================================== exact distribution of the future maximum
def fmax_cdf(b, sc, sj):
    """P(max(continuous path to ~15:15, final auction point) <= b), log distance above the price now, b >= 0.
    sc, sj: std of the remaining continuous part and of the final jump.  F(b) = Phi(b/sc) + Phi(b/sigma_W) - 1 (sc > 0); Phi(b/sj) if sc == 0."""
    b, sc, sj = np.broadcast_arrays(np.asarray(b, float), np.asarray(sc, float), np.asarray(sj, float))
    sw = np.hypot(sc, sj)
    t1 = np.where(sc > 0, ndtr(b / np.where(sc > 0, sc, 1.0)), 1.0)
    t2 = np.where(sw > 0, ndtr(b / np.where(sw > 0, sw, 1.0)), 1.0)
    F = np.where(sc > 0, t1 + t2 - 1.0, t2)
    return np.where(b >= 0, np.clip(F, 0.0, 1.0), 0.0)


def fmax_quantile(tau, sc, sj):
    """exact quantile of the future maximum by bisection (vectorised); 0 if tau lies inside the atom at 0 (only when sc == 0)."""
    tau, sc, sj = np.broadcast_arrays(np.asarray(tau, float), np.asarray(sc, float), np.asarray(sj, float))
    sw = np.hypot(sc, sj)
    lo = np.zeros_like(sw)
    hi = 12.0 * sw + 1e-12
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        up = fmax_cdf(mid, sc, sj) < tau
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    return 0.5 * (lo + hi)


def conv_quantiles(taus, P, a, sc, sj, deltas, side: int):
    """Quantiles (log extension relative to P) of the OFFICIAL final extreme = the Yahoo-based final extreme pushed outwards by an offset drawn from `deltas` (rupees, >= 0; NSE high minus Yahoo high,
    or Yahoo low minus NSE low), offset independent of the path.  CDF = mean_k F_fut(y_yahoo(y_off, delta_k)), zero below the running extreme.  Broadcasts taus, P, a, sc, sj."""
    taus, P, a, sc, sj = [np.asarray(x, float) for x in (taus, P, a, sc, sj)]
    shape = np.broadcast(taus, P, a, sc, sj).shape
    taus, P, a, sc, sj = [np.broadcast_to(x, shape) for x in (taus, P, a, sc, sj)]
    d = np.clip(np.asarray(deltas, float), 0.0, None).reshape((-1,) + (1,) * len(shape))
    eps = d / P[None]
    lo = a.copy()
    hi = a + 12.0 * np.hypot(sc, sj) + 2.0 * float(d.max()) / np.maximum(P, 1.0) + 1e-3
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if side == 0:
            z = np.exp(mid)[None] - eps
            ok = z >= np.exp(a)[None] - 1e-12
            yy = np.log(np.maximum(z, 1e-12))
        else:
            z = np.exp(-mid)[None] + eps
            yy = -np.log(z)
            ok = yy >= a[None] - 1e-12
        F = np.where(ok, fmax_cdf(np.maximum(yy, 0.0), sc[None], sj[None]), 0.0).mean(axis=0)
        up = F < taus
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    return 0.5 * (lo + hi)


def conv_quantiles_emp(taus, P: float, a: float, samples, deltas, side: int):
    """same as conv_quantiles but the Yahoo-basis distribution of the future extreme is the empirical distribution of `samples` (log, relative to the price at that time) - used for benchmark B4."""
    taus = np.asarray(taus, float)
    smp = np.sort(np.asarray(samples, float))
    d = np.clip(np.asarray(deltas, float), 0.0, None)[:, None]
    eps = d / P
    lo = np.full(len(taus), float(a))
    hi = np.full(len(taus), max(float(a), float(smp.max())) + 2.0 * float(d.max()) / P + 1e-3)
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if side == 0:
            z = np.exp(mid)[None, :] - eps
            ok = z >= np.exp(a) - 1e-12
            yy = np.log(np.maximum(z, 1e-12))
        else:
            z = np.exp(-mid)[None, :] + eps
            yy = -np.log(z)
            ok = yy >= a - 1e-12
        F = np.where(ok, np.searchsorted(smp, yy, side="right") / len(smp), 0.0).mean(axis=0)
        up = F < taus
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    return 0.5 * (lo + hi)


def _solve_q(tau: float, rho: np.ndarray) -> np.ndarray:
    """q >= 0 with Phi(q/rho) + Phi(q) - 1 = tau  (unit sigma_W; rho = s_c / sigma_W)."""
    lo = np.zeros_like(rho)
    hi = np.full_like(rho, 12.0)
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        z = np.where(rho > 0, mid / np.where(rho > 0, rho, 1.0), np.inf)
        up = (ndtr(z) + ndtr(mid) - 1.0) < tau
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    return 0.5 * (lo + hi)


RHO_GRID = np.linspace(0.0, 1.0, 2001)
QTAB = np.stack([_solve_q(float(t), RHO_GRID) for t in TAUS], axis=1)          # (2001, 9): quantile of the future max in units of sigma_W


def base_quantiles(sc2: np.ndarray, sj2: np.ndarray) -> np.ndarray:
    """(…, 9) quantiles of the future maximum (log) at the 9 grid levels for variances sc2, sj2 (before any multiplier)."""
    sc2 = np.asarray(sc2, float)
    sj2 = np.asarray(sj2, float)
    sw = np.sqrt(sc2 + sj2)
    rho = np.where(sw > 0, np.sqrt(sc2) / np.where(sw > 0, sw, 1.0), 0.0)
    q = np.stack([np.interp(rho, RHO_GRID, QTAB[:, k]) for k in range(NT)], axis=-1)
    return sw[..., None] * q


# =============================================================================================================================== data
def load_official() -> pd.DataFrame:
    """official NSE daily bars, READ ONLY: bse_daily.csv (common.load_bse) + bse_daily_extra.csv rows not in it.  Index = 'YYYY-MM-DD'."""
    base = load_bse()
    cols = ["open", "high", "low", "close"]
    d = base[cols].copy()
    ex = Path("data/processed/bse_daily_extra.csv")
    if ex.exists():
        e = pd.read_csv(ex, index_col=0, parse_dates=True)
        d = pd.concat([d, e[~e.index.isin(base.index)][cols]])
    d = d.sort_index()
    d.index = d.index.strftime("%Y-%m-%d")
    return d


def ewma_pre_session(off: pd.DataFrame, lam: float = 0.94) -> pd.Series:
    """day-ahead sigma stand-in: EWMA of the Garman-Klass intraday variance of EARLIER sessions only (value for date t uses sessions < t)."""
    gk = (0.5 * np.log(off.high / off.low) ** 2 - (2 * np.log(2) - 1) * np.log(off.close / off.open) ** 2).clip(lower=1e-8).values
    v = float(np.mean(gk[:30]))
    out = np.full(len(gk), np.nan)
    for t in range(30, len(gk)):
        out[t] = v
        v = lam * v + (1 - lam) * gk[t]
    return pd.Series(out, index=off.index)


def _session_record(date, r, c, hi, lo, o0, has_last, auc, off, ew, kf=1.0):
    hy = float(np.nanmax(hi))
    ly = float(np.nanmin(lo))
    rec = {"date": date, "r": r, "c": c, "hi": hi, "lo": lo, "o0": o0, "has_last": has_last, "auc": auc, "Hy": hy, "Ly": ly, "kf": kf,
           "Ho": np.nan, "Lo": np.nan, "ew": float(ew.get(date, np.nan))}
    if date in off.index:
        rec["Ho"] = float(off.high[date]) / kf
        rec["Lo"] = float(off.low[date]) / kf
    return rec


def load_sessions_15m() -> list[dict]:
    """39 post-closing-auction sessions: LN.load_history() (r, c, has24) + per-slot highs/lows from the same two files + official daily H/L."""
    hist = LN.load_history()
    cols = ["date", "time", "open", "high", "low", "close", "volume"]
    frames = [pd.read_csv(LN.UNION)[cols]]
    if Path(LN.EXTRA).exists():
        frames.append(pd.read_csv(LN.EXTRA)[cols])
    u = pd.concat(frames).drop_duplicates(["date", "time"], keep="first")
    off = load_official()
    ew = ewma_pre_session(off)
    out = []
    for s in hist:
        g = u[u.date == s["date"]].copy()
        g["slot"] = [(int(t[:2]) * 60 + int(t[3:5]) - 555) // 15 for t in g.time.astype(str)]
        g = g.sort_values("slot")
        hi = np.full(NB, np.nan)
        lo = np.full(NB, np.nan)
        hi[g.slot.values] = g.high.values
        lo[g.slot.values] = g.low.values
        out.append(_session_record(s["date"], s["r"], s["c"], hi, lo, float(g.open.iloc[0]), s["has24"], True, off, ew))
    return sorted(out, key=lambda x: x["date"])


def hourly_bars(path: str | None) -> pd.DataFrame:
    """Yahoo hourly bars (bonus-adjusted by Yahoo; start times 09:15 ... 15:15).  Reads the repo CSV copy, else converts the scratchpad JSON and writes the copy."""
    if Path(HOURLY_CSV).exists() and not path:
        return pd.read_csv(HOURLY_CSV)
    if not path:
        raise SystemExit("hourly bars not found: pass --hourly <h60_BSE.NS.json> once to create results/live_hl_hourly_bars.csv")
    res = json.load(open(path))["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    h = pd.DataFrame({"t": pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(IST), "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"]})
    h["date"] = h.t.dt.strftime("%Y-%m-%d")
    h["hm"] = h.t.dt.strftime("%H:%M")
    h = h.dropna(subset=["close"])
    h = h[h.hm.isin(["09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:15"])]
    h[["date", "hm", "open", "high", "low", "close", "volume"]].to_csv(HOURLY_CSV, index=False)
    return pd.read_csv(HOURLY_CSV)


def load_sessions_hourly(path: str | None = None) -> list[dict]:
    """complete 7-bar sessions only.  kf = 3 for sessions before the 2025-05-23 bonus (Yahoo divides old prices by 3, the official file does not)."""
    h = hourly_bars(path)
    off = load_official()
    ew = ewma_pre_session(off)
    out = []
    for date, g in h.groupby("date"):
        g = g.sort_values("hm")
        if len(g) != 7:
            continue
        c = g.close.values.astype(float)
        o0 = float(g.open.iloc[0])
        r = np.diff(np.log(np.r_[o0, c]))
        kf = 1.0
        if date in off.index:
            kf = 3.0 if float(off.close[date]) / c[-1] > 2 else 1.0
        out.append(_session_record(date, r, c, g.high.values.astype(float), g.low.values.astype(float), o0, True, date >= CAS_START, off, ew, kf))
    return sorted(out, key=lambda x: x["date"])


# =============================================================================================================================== sample container + profile
class Sample:
    """Arrays for one intraday sample.  Slot boundaries m = 1..mmax are the checkpoints (m completed slots); state = price now, running high / low."""

    def __init__(self, sess: list[dict], nb: int, mmax: int, name: str, full_only: tuple = ()):
        self.sess, self.nb, self.name = sess, nb, name
        self.n = len(sess)
        self.ms = np.arange(1, mmax + 1)
        self.nm = len(self.ms)
        self.full_only = full_only
        self.R2 = np.array([x["r"] ** 2 for x in sess])
        self.full = np.array([x["has_last"] for x in sess])
        self.auc = np.array([x["auc"] for x in sess])
        self.dates = np.array([x["date"] for x in sess])
        n, nm = self.n, self.nm
        self.P = np.zeros((n, nm))
        self.a = np.zeros((n, nm, 2))          # ln(M/P), ln(P/N)
        self.yy = np.zeros((n, nm, 2))         # Yahoo-final ln(Hy/P), ln(P/Ly)
        self.yo = np.full((n, nm, 2), np.nan)  # official-final
        self.fmax = np.zeros((n, nm, 2))       # future max / min of the Yahoo bars from the checkpoint on, relative to P (log)
        self.rv = np.zeros((n, nm))
        self.pk = np.zeros((n, nm))
        self.ew = pd.Series([x["ew"] for x in sess]).ffill().bfill().values
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for i, x in enumerate(sess):
                for jm, m in enumerate(self.ms):
                    P = x["c"][m - 1]
                    Mx, Nn = np.nanmax(x["hi"][:m]), np.nanmin(x["lo"][:m])
                    self.P[i, jm] = P
                    self.a[i, jm] = (np.log(Mx / P), np.log(P / Nn))
                    self.yy[i, jm] = (np.log(x["Hy"] / P), np.log(P / x["Ly"]))
                    if np.isfinite(x["Ho"]):
                        self.yo[i, jm] = (np.log(x["Ho"] / P), np.log(P / x["Lo"]))
                    fm = np.nanmax(x["hi"][m:]) if m < nb else -np.inf
                    fl = np.nanmin(x["lo"][m:]) if m < nb else np.inf
                    self.fmax[i, jm] = (max(0.0, np.log(fm / P)) if np.isfinite(fm) else 0.0, max(0.0, np.log(P / fl)) if np.isfinite(fl) else 0.0)
                    self.rv[i, jm] = np.nansum(x["r"][:m] ** 2)
                    self.pk[i, jm] = np.log(Mx / Nn) ** 2 / (4 * np.log(2))
        # floating-point guard: final extreme can not be inside the running one
        self.yy = np.maximum(self.yy, self.a)
        self.yo = np.where(np.isfinite(self.yo), np.maximum(self.yo, self.a), np.nan)

    # -- profile exactly as live_nowcast.profile (15-minute) with an optional regime-specific last slot (hourly)
    def profile(self, idx, auction: bool) -> np.ndarray:
        idx = np.asarray(list(idx), int)
        R2 = self.R2[idx]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ev = np.nanmean(R2, axis=0)
        if self.full_only:
            f = self.full[idx]
            if f.sum() >= 10:
                for s in self.full_only:
                    ev[s] = R2[f, s].mean()
        else:                                   # hourly: last slot is a continuous bar before the closing auction, a single print after it
            a = self.auc[idx]
            mask = a if auction else ~a
            if mask.sum() >= 8:
                ev[self.nb - 1] = R2[mask, self.nb - 1].mean()
        return ev

    def remaining(self, ev: np.ndarray, auction: bool) -> tuple[np.ndarray, np.ndarray]:
        """(s_c^2, s_J^2) for each checkpoint m: continuous part up to the last slot, last slot = one jump if `auction` else continuous."""
        nb = self.nb
        cs = np.r_[np.cumsum(ev[::-1])[::-1], 0.0]
        if auction:
            sc2 = np.maximum(cs[self.ms] - ev[nb - 1], 0.0)
            sj2 = np.full(self.nm, ev[nb - 1])
        else:
            sc2 = cs[self.ms]
            sj2 = np.zeros(self.nm)
        return sc2, sj2


# =============================================================================================================================== variants
MODEL_VARIANTS = {            # name -> weights on (realised variance, realised range, day-ahead EWMA); sigma^2 factor = clip(1 + sum w_k (ratio_k - 1), 0.4, 4)
    "M1": {}, "M2a": {"rv": 0.5}, "M2b": {"rv": 1.0}, "M3a": {"pk": 0.5}, "M3b": {"pk": 1.0}, "M4a": {"ew": 0.5}, "M4b": {"ew": 1.0}, "M5": {"rv": 0.5, "ew": 0.5},
}
ALL_VARIANTS = ["B1", "B2", "B3", "B4", "M0", "M1", "M2a", "M2b", "M3a", "M3b", "M4a", "M4b", "M5", "M6", "M7", "M1+off", "M1c", "B3c", "B4c"]       # M1c, B3c, B4c: POST-HOC (added after the official-target bands were seen to collapse onto the running extreme): same structure / benchmark, moved outwards by the Yahoo-to-NSE offset
FAMILY_MODEL = ["M2a", "M2b", "M3a", "M3b", "M4a", "M4b", "M5", "M6", "M7"]       # Holm family (i): against M1
FAMILY_BENCH = ["B1", "B2", "B3", "B4"]                                              # Holm family (ii): M1 against these
BUCKET_EDGES = {25: (8, 16), 7: (3, 5)}                                              # m < e0 morning, e0 <= m < e1 midday, else afternoon (15-minute: from 11:15 / 13:15; hourly: from 12:15 / 14:15)


def g_factor(w: dict, rv, pk, ew, ref_rv, ref_pk, ref_ew) -> np.ndarray:
    """multiplicative factor on sigma, shape of rv; ratios are relative to the training-sample average at the same checkpoint."""
    x = np.ones_like(rv, dtype=float)
    if "rv" in w:
        x = x + w["rv"] * (rv / np.maximum(ref_rv, 1e-12) - 1.0)
    if "pk" in w:
        x = x + w["pk"] * (pk / np.maximum(ref_pk, 1e-12) - 1.0)
    if "ew" in w:
        x = x + w["ew"] * (ew / max(ref_ew, 1e-12) - 1.0)
    return np.sqrt(np.clip(x, 0.4, 4.0))


def pinball_tensor(B: np.ndarray, g: np.ndarray, a: np.ndarray, y: np.ndarray) -> np.ndarray:
    """sum over sides of pinball loss for every multiplier in CGRID.  B (nm,9), g (nm,), a (nm,2), y (nm,2) -> (nc, nm, 9)."""
    Q = np.maximum(a[None, :, :, None], CGRID[:, None, None, None] * g[None, :, None, None] * B[None, :, None, :])      # (nc, nm, 2, 9)
    u = y[None, :, :, None] - Q
    L = np.maximum(TAUS * u, (TAUS - 1) * u)
    return L.sum(axis=2)


def quantile_forecast(B, g, a, c) -> np.ndarray:
    """(nm,2,9) log quantiles of the final extreme.  c scalar, (9,) per-level, or (nm,) per-checkpoint."""
    c = np.asarray(c, float)
    if c.ndim == 0:
        cc = c
    elif c.shape == (NT,):
        cc = c[None, None, :]
    else:
        cc = c[:, None, None]
    Q = np.maximum(a[:, :, None], cc * g[:, None, None] * B[:, None, :])
    return np.maximum.accumulate(Q, axis=2)


def p_in(a, sc2, sj2, c, g) -> np.ndarray:
    """P(the running extreme is the final extreme), (nm,2)."""
    s = c * g
    return fmax_cdf(a, (np.sqrt(sc2) * s)[:, None], (np.sqrt(sj2) * s)[:, None])


def uniform_profile(ev: np.ndarray) -> np.ndarray:
    return np.full_like(ev, ev.sum() / len(ev))


# =============================================================================================================================== engines
def _argmin_c(Lsum: np.ndarray) -> float:
    """Lsum (nc, nm, 9): multiplier minimising the mean loss over all checkpoints and levels."""
    return float(CGRID[int(np.argmin(Lsum.mean(axis=(1, 2))))])


def _argmin_c_levels(Lsum: np.ndarray) -> np.ndarray:
    return CGRID[np.argmin(Lsum.mean(axis=1), axis=0)]


def _argmin_c_buckets(Lsum: np.ndarray, S: Sample) -> np.ndarray:
    e0, e1 = BUCKET_EDGES[S.nb]
    ms = S.ms
    out = np.zeros(S.nm)
    for lo_, hi_ in ((0, e0), (e0, e1), (e1, 10 ** 6)):
        sel = (ms >= lo_) & (ms < hi_) & (ms >= 1)
        if sel.any():
            out[sel] = CGRID[int(np.argmin(Lsum[:, sel, :].mean(axis=(1, 2))))]
    return out


class Result:
    def __init__(self, S: Sample):
        self.S = S
        self.Q = {v: np.full((S.n, S.nm, 2, NT), np.nan) for v in ALL_VARIANTS}
        self.p0 = {v: np.full((S.n, S.nm, 2), np.nan) for v in list(MODEL_VARIANTS) + ["M0", "B3"]}
        self.c = {v: np.full(S.n, np.nan) for v in list(MODEL_VARIANTS) + ["B3"]}
        self.ev = [None] * S.n
        self.sc2 = np.full((S.n, S.nm), np.nan)
        self.sj2 = np.full((S.n, S.nm), np.nan)
        self.offs = np.full((S.n, 2), np.nan)


def _forecast_one(S: Sample, R: Result, t: int, ev: np.ndarray, tr, refs, cal: dict, delta: np.ndarray, y_tr: np.ndarray):
    """fill R for scored session t.  ev: profile of training sessions; refs: (ref_rv, ref_pk, ref_ew) training averages; cal: Lsum per variant; delta: mean official-Yahoo offsets (Rs) of training."""
    auction = bool(S.auc[t])
    sc2, sj2 = S.remaining(ev, auction)
    B = base_quantiles(sc2, sj2)
    R.ev[t], R.sc2[t], R.sj2[t] = ev, sc2, sj2
    a = S.a[t]
    for v, w in MODEL_VARIANTS.items():
        g = g_factor(w, S.rv[t], S.pk[t], S.ew[t], *refs)
        c = _argmin_c(cal[v])
        R.c[v][t] = c
        R.Q[v][t] = quantile_forecast(B, g, a, c)
        R.p0[v][t] = p_in(a, sc2, sj2, c, g)
        if v == "M1":
            R.Q["M0"][t] = quantile_forecast(B, g, a, 1.0)
            R.p0["M0"][t] = p_in(a, sc2, sj2, 1.0, g)
            R.Q["M6"][t] = quantile_forecast(B, g, a, _argmin_c_levels(cal["M1"]))
            R.Q["M7"][t] = quantile_forecast(B, g, a, _argmin_c_buckets(cal["M1"], S))
            sh = np.log1p(delta[None, :] / S.P[t][:, None])                                  # (nm,2) offset in log terms
            R.Q["M1+off"][t] = R.Q["M1"][t] + sh[:, :, None]
    # B3: constant variance rate (no time-of-day profile), own multiplier
    ev_u = uniform_profile(ev)
    sc2u, sj2u = S.remaining(ev_u, auction)
    Bu = base_quantiles(sc2u, sj2u)
    cu = _argmin_c(cal["B3"])
    R.c["B3"][t] = cu
    R.Q["B3"][t] = quantile_forecast(Bu, np.ones(S.nm), a, cu)
    R.p0["B3"][t] = p_in(a, sc2u, sj2u, cu, np.ones(S.nm))
    # B1 price stays; B2 empirical extension; B4 path replay
    R.Q["B1"][t] = np.repeat(a[:, :, None], NT, axis=2)
    u = np.maximum(y_tr - S.a[tr], 0.0)                                                         # (ntr, nm, 2) extension of the training sessions
    R.Q["B2"][t] = a[:, :, None] + np.moveaxis(np.quantile(u, TAUS, axis=0), 0, -1)
    R.Q["B4"][t] = np.maximum(a[:, :, None], np.moveaxis(np.quantile(S.fmax[tr], TAUS, axis=0), 0, -1))
    R.offs[t] = delta


def engine_loo(S: Sample, tgt: str = "o", verbose: bool = True) -> Result:
    """nested leave-one-session-out.  For scored session t: multiplier chosen on the other sessions i, each forecast with the profile of the sessions excluding i AND t."""
    n = S.n
    Y = S.yo if tgt == "o" else S.yy
    R = Result(S)
    tot_rv, tot_pk, tot_ew = S.rv.sum(0), S.pk.sum(0), S.ew.sum()
    vnames = list(MODEL_VARIANTS) + ["B3"]
    off_h = np.array([x["Ho"] - x["Hy"] if np.isfinite(x["Ho"]) else np.nan for x in S.sess])
    off_l = np.array([x["Ly"] - x["Lo"] if np.isfinite(x["Lo"]) else np.nan for x in S.sess])
    t0 = time.time()
    for t in range(n):
        tr = np.array([i for i in range(n) if i != t])
        cal = {v: np.zeros((len(CGRID), S.nm, NT)) for v in vnames}
        for i in tr:
            idx = [k for k in range(n) if k != i and k != t]
            ev = S.profile(idx, bool(S.auc[i]))
            sc2, sj2 = S.remaining(ev, bool(S.auc[i]))
            B = base_quantiles(sc2, sj2)
            refs = ((tot_rv - S.rv[i] - S.rv[t]) / (n - 2), (tot_pk - S.pk[i] - S.pk[t]) / (n - 2), (tot_ew - S.ew[i] - S.ew[t]) / (n - 2))
            for v, w in MODEL_VARIANTS.items():
                cal[v] += pinball_tensor(B, g_factor(w, S.rv[i], S.pk[i], S.ew[i], *refs), S.a[i], Y[i])
            sc2u, sj2u = S.remaining(uniform_profile(ev), bool(S.auc[i]))
            cal["B3"] += pinball_tensor(base_quantiles(sc2u, sj2u), np.ones(S.nm), S.a[i], Y[i])
        ev_t = S.profile(tr, bool(S.auc[t]))
        refs_t = (S.rv[tr].mean(0), S.pk[tr].mean(0), S.ew[tr].mean())
        delta = np.array([np.nanmean(off_h[tr]), np.nanmean(off_l[tr])])
        _forecast_one(S, R, t, ev_t, tr, refs_t, cal, delta, Y[tr])
        if verbose and (t + 1) % 10 == 0:
            print(f"  LOO {S.name}: {t + 1}/{n} sessions ({time.time() - t0:.0f}s)", flush=True)
    return R


def engine_wf(S: Sample, tgt: str = "y", warm: int = 50, prof_min: int = 20, verbose: bool = True) -> Result:
    """expanding walk-forward.  Session t (>= warm): profile of sessions < t; multiplier chosen on sessions prof_min..t-1, each forecast with the profile of the sessions before it."""
    n = S.n
    Y = S.yo if tgt == "o" else S.yy
    R = Result(S)
    vnames = list(MODEL_VARIANTS) + ["B3"]
    cs_rv, cs_pk, cs_ew = np.cumsum(S.rv, axis=0), np.cumsum(S.pk, axis=0), np.cumsum(S.ew)
    Lcum = {v: np.zeros((n + 1, len(CGRID), S.nm, NT)) for v in vnames}              # Lcum[k] = sum over sessions prof_min..k-1
    t0 = time.time()
    for i in range(prof_min, n):
        idx = np.arange(i)
        ev = S.profile(idx, bool(S.auc[i]))
        sc2, sj2 = S.remaining(ev, bool(S.auc[i]))
        B = base_quantiles(sc2, sj2)
        refs = (cs_rv[i - 1] / i, cs_pk[i - 1] / i, cs_ew[i - 1] / i)
        for v, w in MODEL_VARIANTS.items():
            Lcum[v][i + 1] = Lcum[v][i] + pinball_tensor(B, g_factor(w, S.rv[i], S.pk[i], S.ew[i], *refs), S.a[i], Y[i])
        sc2u, sj2u = S.remaining(uniform_profile(ev), bool(S.auc[i]))
        Lcum["B3"][i + 1] = Lcum["B3"][i] + pinball_tensor(base_quantiles(sc2u, sj2u), np.ones(S.nm), S.a[i], Y[i])
        if verbose and (i + 1) % 100 == 0:
            print(f"  WF {S.name}: prepared {i + 1}/{n} ({time.time() - t0:.0f}s)", flush=True)
    for t in range(warm, n):
        tr = np.arange(t)
        ev_t = S.profile(tr, bool(S.auc[t]))
        refs_t = (cs_rv[t - 1] / t, cs_pk[t - 1] / t, cs_ew[t - 1] / t)
        cal = {v: Lcum[v][t] for v in vnames}
        delta = np.array([0.0, 0.0])
        _forecast_one(S, R, t, ev_t, tr, refs_t, cal, delta, Y[tr])
    return R


def offsets_arrays(S: Sample) -> tuple[np.ndarray, np.ndarray]:
    """per-session NSE-minus-Yahoo high and Yahoo-minus-NSE low (rupees), clipped at 0 (the sign never flipped by more than float noise in the 15-minute sample)."""
    dh = np.array([x["Ho"] - x["Hy"] if np.isfinite(x["Ho"]) else np.nan for x in S.sess])
    dl = np.array([x["Ly"] - x["Lo"] if np.isfinite(x["Lo"]) else np.nan for x in S.sess])
    return np.clip(dh, 0, None), np.clip(dl, 0, None)


def add_m1c(S: Sample, R_o: Result, R_y: Result, chrono: bool = False, first: int = 0) -> None:
    """POST-HOC variants M1c / B3c / B4c: structure (profile, multiplier c) fitted on the Yahoo-bars target (R_y), then the official high / low = Yahoo extreme moved outwards by an offset drawn from the OTHER sessions' offsets.
    B3c: constant-variance-rate model, B4c: historical path replay (other sessions' future extremes), both with the same offset treatment."""
    dh, dl = offsets_arrays(S)
    for t in range(first, S.n):
        tr = np.arange(t) if chrono else np.array([i for i in range(S.n) if i != t])
        c = R_y.c["M1"][t]
        sc, sj = c * np.sqrt(R_y.sc2[t]), c * np.sqrt(R_y.sj2[t])
        sc2u, sj2u = S.remaining(uniform_profile(R_y.ev[t]), bool(S.auc[t]))
        cu = R_y.c["B3"][t]
        for side, dd in ((0, dh), (1, dl)):
            q = conv_quantiles(TAUS[None, :], S.P[t][:, None], S.a[t][:, side][:, None], sc[:, None], sj[:, None], dd[tr], side)
            R_o.Q["M1c"][t, :, side, :] = np.maximum.accumulate(q, axis=1)
            q = conv_quantiles(TAUS[None, :], S.P[t][:, None], S.a[t][:, side][:, None], (cu * np.sqrt(sc2u))[:, None], (cu * np.sqrt(sj2u))[:, None], dd[tr], side)
            R_o.Q["B3c"][t, :, side, :] = np.maximum.accumulate(q, axis=1)
            for jm in range(S.nm):
                q = conv_quantiles_emp(TAUS, S.P[t, jm], S.a[t, jm, side], S.fmax[tr, jm, side], dd[tr], side)
                R_o.Q["B4c"][t, jm, side, :] = np.maximum.accumulate(q)


# =============================================================================================================================== evaluation helpers
def pinball_arr(y: np.ndarray, Q: np.ndarray) -> np.ndarray:
    u = y[..., None] - Q
    return np.mean(np.maximum(TAUS * u, (TAUS - 1) * u), axis=-1)


def holm(p: dict) -> dict:
    items = sorted(((k, v) for k, v in p.items() if np.isfinite(v)), key=lambda kv: kv[1])
    out, run = {}, 0.0
    for r, (k, v) in enumerate(items):
        run = max(run, min(1.0, (len(items) - r) * v))
        out[k] = run
    for k, v in p.items():
        out.setdefault(k, np.nan)
    return out


def band_hits(Q: np.ndarray, a: np.ndarray, y: np.ndarray, p0: np.ndarray | None, level: float, band: str = "upto"):
    """hit indicator, model-implied nominal coverage (atom aware; nan without p0) and 'collapsed' flag for the printed band of the final extreme.
    band 'upto' (what the live tool prints): [running extreme, q_level]; band 'central': [q_(1-level)/2, q_(1+level)/2].  Q (...,9), a (...), y (...)."""
    tol = 1e-9
    if band == "upto":
        qh = Q[..., list(TAUS).index(level)]
        hit = y <= qh + tol
        collapsed = qh <= a + tol
        nom = np.full(hit.shape, np.nan) if p0 is None else np.where(collapsed, p0, level)
        return hit, nom, collapsed
    lo_t, hi_t = {0.5: (0.25, 0.75), 0.9: (0.05, 0.95)}[level]
    ql, qh = Q[..., list(TAUS).index(lo_t)], Q[..., list(TAUS).index(hi_t)]
    hit = (y >= ql - tol) & (y <= qh + tol)
    nom = np.full(hit.shape, np.nan)
    if p0 is not None:
        nom = np.where(qh > a + tol, hi_t, p0) - np.where(ql > a + tol, lo_t, 0.0)
    return hit, nom, qh <= a + tol


def cluster_boot(hit_by_session: np.ndarray, B: int = 4000, seed: int = 7) -> tuple[float, float]:
    """95% interval of the pooled coverage resampling whole sessions (hit_by_session: (n_sessions, n_checkpoints))."""
    rng = np.random.default_rng(seed)
    n = len(hit_by_session)
    m = np.array([hit_by_session[rng.integers(0, n, n)].mean() for _ in range(B)])
    return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def session_losses(R: Result, v: str, cps: list[int], y: np.ndarray) -> np.ndarray:
    """per-session mean pinball (Rs at RS per unit log) over the given checkpoints (indices into ms) and both sides."""
    Q = R.Q[v][:, cps]
    return RS * pinball_arr(y[:, cps], Q).mean(axis=(1, 2))


# =============================================================================================================================== backtest driver
def windows_hourly(S: Sample, warm: int) -> dict:
    d = S.dates
    sc = np.zeros(S.n, bool)
    sc[warm:] = True
    return {"Validation (scored, before 2025-07-01)": sc & (d < "2025-07-01"), "Final (2025-07-01 on)": sc & (d >= "2025-07-01"), "Post-closing-auction (2026-08-03 on)": sc & (d >= CAS_START), "All scored": sc}


def summarise(R: Result, y: np.ndarray, name: str, cps: dict, wins: dict, dm_lag: int, tgt_label: str) -> dict:
    """tables: variants (pinball, DM vs M1, Holm), coverage by checkpoint (M1 and M1c), pooled coverage (+session-cluster bootstrap)."""
    S = R.S
    cpi = list(cps.values())
    out = {"variants": [], "coverage": [], "pooled": []}
    for wname, wm in wins.items():
        idx = np.where(wm)[0]
        if len(idx) < 5:
            continue
        vlist = [v for v in ALL_VARIANTS if np.isfinite(R.Q[v][idx][:, cpi]).all()]
        loss = {v: session_losses(R, v, cpi, y)[idx] for v in vlist}
        dm_p_model, dm_p_bench = {}, {}
        for v in FAMILY_MODEL:
            dm_p_model[v] = M.diebold_mariano(loss[v], loss["M1"], lag=dm_lag)[2]
        for v in FAMILY_BENCH:
            dm_p_bench[v] = M.diebold_mariano(loss["M1"], loss[v], lag=dm_lag)[2]
        hm, hb = holm(dm_p_model), holm(dm_p_bench)
        dm_p_c, hc = {}, {}
        if "M1c" in vlist:
            dm_p_c = {v: M.diebold_mariano(loss["M1c"], loss[v], lag=dm_lag)[2] for v in ("B1", "B2", "B3c", "B4c")}
            hc = holm(dm_p_c)
        for v in vlist:
            row = {"sample": name, "target": tgt_label, "window": wname, "n_sessions": int(len(idx)), "variant": v, "pinball_Rs_mean": float(loss[v].mean()),
                   "pinball_vs_M1_pct": float(100 * (loss[v].mean() / loss["M1"].mean() - 1))}
            if v in FAMILY_MODEL:
                d, t_, p = M.diebold_mariano(loss[v], loss["M1"], lag=dm_lag)
                row.update(dm_t_vs_M1=t_, dm_p_better_than_M1=p, dm_p_holm=hm[v])
            elif v in FAMILY_BENCH:
                d, t_, p = M.diebold_mariano(loss["M1"], loss[v], lag=dm_lag)
                row.update(dm_t_vs_M1=t_, dm_p_M1_better_than_this=p, dm_p_holm=hb[v])
            elif v == "M1c":
                d, t_, p = M.diebold_mariano(loss[v], loss["M1"], lag=dm_lag)
                row.update(dm_t_vs_M1=t_, dm_p_better_than_M1=p, dm_p_holm=np.nan)
            if "M1c" in vlist and v in ("B1", "B2", "B3c", "B4c"):
                row.update(dm_p_M1c_better_than_this=dm_p_c[v], dm_p_holm_M1c_family=hc[v])
            row["post_hoc"] = v in ("M1c", "B3c", "B4c")
            out["variants"].append(row)
        for v in [x for x in ("M1", "M1c", "M0", "B3", "B3c", "B2", "B4", "B4c") if x in vlist]:
            for band in ("upto", "central"):
                if v in ("M1c", "B3c", "B4c") and band == "central":
                    continue
                for lev in (0.5, 0.9):
                    for side, sname in ((0, "high"), (1, "low")):
                        hit_all = []
                        for cn, ci in cps.items():
                            Qv = R.Q[v][idx][:, ci, side]
                            a_ = S.a[idx][:, ci, side]
                            yv = y[idx][:, ci, side]
                            p0 = R.p0[v][idx][:, ci, side] if v in R.p0 else None
                            hit, nom, col = band_hits(Qv, a_, yv, p0, lev, band)
                            hit_all.append(hit)
                            if v in ("M1", "M1c", "B3c", "B4c"):
                                k, nn = int(hit.sum()), len(hit)
                                nm_ = float(np.nanmean(nom)) if np.isfinite(nom).any() else lev
                                out["coverage"].append({"sample": name, "target": tgt_label, "window": wname, "variant": v, "band": band, "side": sname, "level": lev, "checkpoint": cn, "n_sessions": nn,
                                                        "hits": k, "coverage": k / nn, "model_implied_nominal": nm_, "share_band_collapsed_on_running_extreme": float(col.mean()),
                                                        "kupiec_p_vs_stated_level": M.kupiec(hit.astype(int), lev), "kupiec_p_vs_model_implied": M.kupiec(hit.astype(int), min(max(nm_, 1e-6), 1 - 1e-6))})
                        H = np.array(hit_all).T
                        lo_, hi_ = cluster_boot(H)
                        sd = H.std(axis=0)
                        out["pooled"].append({"sample": name, "target": tgt_label, "window": wname, "variant": v, "band": band, "side": sname, "level": lev, "n_sessions": len(idx), "n_checkpoints": len(cps),
                                              "pooled_coverage": float(H.mean()), "boot95_lo": lo_, "boot95_hi": hi_,
                                              "mean_within_session_hit_corr": float(np.nanmean(np.corrcoef(H.T)[np.triu_indices(H.shape[1], 1)])) if sd.min() > 0 else np.nan})
    return out


def p_in_reliability(R: Result, name: str, wins: dict, cps: dict) -> list[dict]:
    """calibration of P(running extreme is already the final extreme) on the Yahoo-bars basis (event: price never exceeds the running extreme again)."""
    S = R.S
    rows = []
    bins = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0001]
    cpi = list(cps.values())
    for wname, wm in wins.items():
        idx = np.where(wm)[0]
        if len(idx) < 5:
            continue
        for side, sname in ((0, "high"), (1, "low")):
            p = R.p0["M1"][idx][:, cpi, side].ravel()
            ev = (S.yy[idx][:, cpi, side] <= S.a[idx][:, cpi, side] + 1e-9).ravel().astype(float)
            # constant-base-rate benchmark per checkpoint, leave-one-session-out within the scored window
            ev2 = (S.yy[idx][:, cpi, side] <= S.a[idx][:, cpi, side] + 1e-9).astype(float)
            loo_base = (ev2.sum(axis=0, keepdims=True) - ev2) / (len(idx) - 1)
            rows.append({"sample": name, "window": wname, "side": sname, "bin": "ALL", "n_states": int(len(p)), "n_sessions": int(len(idx)), "mean_predicted": float(p.mean()), "observed_freq": float(ev.mean()),
                         "brier_model": float(np.mean((p - ev) ** 2)), "brier_checkpoint_base_rate_leave_one_out": float(np.mean((loo_base.ravel() - ev) ** 2))})
            for lo_, hi_ in zip(bins[:-1], bins[1:]):
                sel = (p >= lo_) & (p < hi_)
                if sel.sum() == 0:
                    continue
                rows.append({"sample": name, "window": wname, "side": sname, "bin": f"[{lo_:.1f},{min(hi_, 1):.1f})", "n_states": int(sel.sum()), "n_sessions": int(len(idx)), "mean_predicted": float(p[sel].mean()),
                             "observed_freq": float(ev[sel].mean())})
    return rows


def miss_tables(R: Result, y: np.ndarray, name: str, idx_scored: np.ndarray, variant: str = "M1") -> pd.DataFrame:
    """typical miss by slot: |final extreme - model median|, |final extreme - running extreme| (naive), in rupees (price now x log difference) and in percent of price."""
    S = R.S
    rows = []
    for jm, m in enumerate(S.ms):
        for side, sname in ((0, "high"), (1, "low")):
            q50 = R.Q[variant][idx_scored][:, jm, side, list(TAUS).index(0.5)]
            yy = y[idx_scored][:, jm, side]
            aa = S.a[idx_scored][:, jm, side]
            P = S.P[idx_scored][:, jm]
            miss_model = np.abs(yy - q50)
            miss_naive = np.abs(yy - aa)
            rows.append({"sample": name, "slot_m": int(m), "side": sname, "n_sessions": int(len(idx_scored)),
                         "model_median_miss_pct_mean": float(100 * miss_model.mean()), "model_median_miss_pct_median": float(100 * np.median(miss_model)),
                         "naive_running_extreme_miss_pct_mean": float(100 * miss_naive.mean()), "naive_running_extreme_miss_pct_median": float(100 * np.median(miss_naive)),
                         "model_median_miss_Rs_mean": float((miss_model * P).mean()), "model_median_miss_Rs_median": float(np.median(miss_model * P)),
                         "naive_miss_Rs_mean": float((miss_naive * P).mean()), "naive_miss_Rs_median": float(np.median(miss_naive * P))})
    return pd.DataFrame(rows)


def stats_of(x: np.ndarray) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)), "p75": float(np.quantile(x, .75)), "p90": float(np.quantile(x, .9)), "p95": float(np.quantile(x, .95)), "max": float(x.max()), "min": float(x.min()),
            "share_over_0.05": float((x > 0.05).mean()), "share_negative_over_0.05": float((x < -0.05).mean())}


def consistency_1m_vs_15m(S15: Sample, cache: pd.DataFrame) -> dict:
    """the 15-minute bars aggregated from the cached 1-minute bars (live_nowcast.to_15m) against the 15-minute file used for the profile, session by session."""
    c1 = cache.copy()
    c1["date"] = c1.t.dt.strftime("%Y-%m-%d")
    c1["slot"] = ((c1.t.dt.hour * 60 + c1.t.dt.minute - 555) // 15).astype(int)
    c1 = c1[(c1.slot >= 0) & (c1.slot < NB)]
    g = LN.to_15m(c1)
    date_idx = {d: i for i, d in enumerate(S15.dates)}
    dh, dl, dc, n, nbad, sess = [], [], [], 0, 0, set()
    for r in g.itertuples():
        if r.date not in date_idx:
            continue
        x = S15.sess[date_idx[r.date]]
        k = (int(r.time[:2]) * 60 + int(r.time[3:5]) - 555) // 15
        if not np.isfinite(x["hi"][k]):
            continue
        sess.add(r.date)
        n += 1
        dh.append(abs(r.high - x["hi"][k]))
        dl.append(abs(r.low - x["lo"][k]))
        dc.append(abs(r.close - x["c"][k]))
        nbad += int(max(dh[-1], dl[-1], dc[-1]) > 0.06)
    return {"sessions": len(sess), "bars_compared": n, "max_abs_high_diff": float(max(dh)), "max_abs_low_diff": float(max(dl)), "max_abs_close_diff": float(max(dc)), "bars_with_any_difference_over_0.06": nbad}


def check_1m(S15: Sample, R_y: Result, cache: pd.DataFrame) -> dict:
    """DESCRIPTIVE check on the sessions Yahoo serves at 1-minute resolution (last ~7): the state is rebuilt every 5 minutes from the minute bars (price now, running extremes, fractional slot) and scored
    against the Yahoo 1-minute final extreme, with the profile and multiplier of the LOO fit that excluded that session.  n = number of sessions (7); the 5-minute marks of one session are strongly dependent."""
    c1 = cache.copy()
    c1["date"] = c1.t.dt.strftime("%Y-%m-%d")
    c1["slot"] = ((c1.t.dt.hour * 60 + c1.t.dt.minute - 555) // 15).astype(int)
    rows = []
    date_idx = {d: i for i, d in enumerate(S15.dates)}
    for d_, g in c1.groupby("date"):
        if d_ not in date_idx or len(g) < 300:
            continue
        t = date_idx[d_]
        ev, c = R_y.ev[t], float(R_y.c["M1"][t])
        fh, fl = float(g.high.max()), float(g.low.min())
        for mins in range(5, 24 * 15 + 1, 5):                                  # 09:20 ... 15:15
            hh, mm = divmod(555 + mins, 60)
            asof = f"{hh:02d}:{mm:02d}"
            gg = g[g.t.dt.strftime("%H:%M") < asof]
            if gg.empty:
                continue
            st = state_from_bars(gg, ev)
            est = estimate(st, c)
            for side, sname, fin in ((0, "high", fh), (1, "low", fl)):
                e = est[sname]
                rows.append({"session": d_, "asof": asof, "side": sname, "price": st["price"], "running": e["running"], "p_in": e["p_in"], "q50": e["q"][0.5], "q90": e["q"][0.9], "final_yahoo_1m": fin,
                             "hit50": (fin <= e["q"][0.5] + 1e-9) if side == 0 else (fin >= e["q"][0.5] - 1e-9), "hit90": (fin <= e["q"][0.9] + 1e-9) if side == 0 else (fin >= e["q"][0.9] - 1e-9),
                             "in_event": abs(fin - e["running"]) < 1e-9, "q50_collapsed": abs(e["q"][0.5] - e["running"]) < 1e-9, "q90_collapsed": abs(e["q"][0.9] - e["running"]) < 1e-9, "c": c})
    df = pd.DataFrame(rows)
    df.to_csv("results/live_hl_check_1m.csv", index=False)
    out = {"n_sessions": int(df.session.nunique()), "n_marks_per_session": int(len(df) // max(1, 2 * df.session.nunique()))}
    for sname in ("high", "low"):
        x = df[df.side == sname]
        hit = x.pivot(index="session", columns="asof", values="hit90").astype(float).values if len(x) else np.zeros((0, 0))
        out[sname] = {"pooled_hit50": float(x.hit50.mean()), "pooled_hit90": float(x.hit90.mean()), "mean_p_in": float(x.p_in.mean()), "observed_in": float(x.in_event.mean()),
                      "share_q90_collapsed": float(x.q90_collapsed.mean()), "mean_nominal90": float(np.where(x.q90_collapsed, x.p_in, 0.9).mean()), "boot95_hit90": cluster_boot(hit) if hit.size else None}
    Path("results/live_hl_check_1m_summary.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# =============================================================================================================================== 1-minute cache and fetching
def fetch_1m(rng: str = "7d", tries: int = 3) -> dict:
    """Yahoo 1-minute bars.  live_nowcast.yahoo_1m first (query2 then query1); on 429 / empty / bad JSON retry both hosts with back-off."""
    err = None
    try:
        res = LN.yahoo_1m(rng)
        if res and res.get("timestamp"):
            return res
    except Exception as e:  # noqa: BLE001
        err = e
    for k in range(tries):
        for host in ("query2", "query1"):
            url = f"https://{host}.finance.yahoo.com/v8/finance/chart/BSE.NS?interval=1m&range={rng}"
            out = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", url], capture_output=True, text=True)
            body, _, code = out.stdout.rpartition("\n")
            if code == "429":
                err = RuntimeError(f"HTTP 429 from {host}")
                continue
            try:
                res = json.loads(body)["chart"]["result"][0]
                if res.get("timestamp"):
                    return res
            except Exception as e:  # noqa: BLE001
                err = e
        time.sleep(2 * (k + 1))
    raise RuntimeError(f"Yahoo fetch failed on both hosts ({err})")


def load_cache_1m() -> pd.DataFrame:
    if not Path(BARS1M).exists():
        return pd.DataFrame(columns=["t", "date", "open", "high", "low", "close", "volume"])
    d = pd.read_csv(BARS1M)
    d["t"] = pd.to_datetime(d["t"], utc=True).dt.tz_convert(IST)
    return d


def save_cache_1m(df1: pd.DataFrame) -> pd.DataFrame:
    """merge fresh bars into results/live_hl_bars_1m.csv (the last bar of a live session may change, so fresh rows win); returns the merged table."""
    old = load_cache_1m()
    cols = ["t", "date", "open", "high", "low", "close", "volume"]
    new = df1[cols].copy()
    allb = pd.concat([old[~old.t.isin(new.t)], new]).sort_values("t")
    out = allb.copy()
    out["t"] = out.t.map(lambda z: z.isoformat())
    out.to_csv(BARS1M, index=False)
    return load_cache_1m()


# =============================================================================================================================== live estimate
def load_params() -> dict | None:
    p = Path(PARAMS)
    return json.loads(p.read_text()) if p.exists() else None


def fit_live_c(S: Sample) -> float:
    """multiplier fitted on ALL sessions against the Yahoo-bars final extremes (profile of the other sessions for each); used when no params file exists."""
    Lsum = np.zeros((len(CGRID), S.nm, NT))
    for i in range(S.n):
        ev = S.profile([k for k in range(S.n) if k != i], bool(S.auc[i]))
        sc2, sj2 = S.remaining(ev, bool(S.auc[i]))
        Lsum += pinball_tensor(base_quantiles(sc2, sj2), np.ones(S.nm), S.a[i], S.yy[i])
    return _argmin_c(Lsum)


def state_from_bars(df1: pd.DataFrame, ev: np.ndarray, force_closed: bool = False) -> dict:
    """everything the estimate needs from one session's 1-minute bars (all bars passed in are used)."""
    last = df1.t.iloc[-1]
    price = float(df1.close.iloc[-1])
    Mx, Nn = float(df1.high.max()), float(df1.low.min())
    hm_last = last.hour * 60 + last.minute
    end_min = hm_last + 1 - 555                                    # minutes since 09:15 at the END of the last bar
    printed = hm_last >= 15 * 60 + 28                              # the closing-auction print shows up at 15:28-15:29
    if printed or end_min >= 375 or force_closed:
        status, m, frac = "closed", NB, 0.0
    elif end_min >= (NB - 1) * 15:
        status, m, frac = "auction", NB - 1, 0.0                   # continuous trading over (~15:15), the closing print still to come
    else:
        status, m, frac = "open", int(end_min // 15), float((end_min % 15) / 15)
    if status == "closed":
        sc2 = sj2 = 0.0
    elif status == "auction":
        sc2, sj2 = 0.0, float(ev[NB - 1])
    else:
        sc2 = float((1 - frac) * ev[m] + ev[m + 1:NB - 1].sum())
        sj2 = float(ev[NB - 1])
    return {"asof": last + pd.Timedelta(minutes=1), "price": price, "M": Mx, "N": Nn, "status": status, "m": m, "frac": frac, "sc2": sc2, "sj2": sj2, "open_first": float(df1.open.iloc[0]),
            "minutes_to_close": float(max(0, 375 - end_min))}


def extension_probs(price: float, level: float, side: int, sc: float, sj: float, ds=(5, 10, 20, 40)) -> dict:
    """P(final extreme goes beyond the running extreme by at least d rupees) (side 0: high, 1: low)."""
    out = {}
    for d in ds:
        tgt = level + d if side == 0 else level - d
        b = np.log(tgt / price) if side == 0 else np.log(price / tgt)
        out[d] = float(1 - fmax_cdf(b, sc, sj))
    return out


EXT_TAUS = (0.25, 0.5, 0.75, 0.9, 0.95)


def estimate(st: dict, c: float, deltas: tuple | None = None) -> dict:
    """per side: P(running extreme is final) [Yahoo basis], quantiles of the final extreme's price (keyed by the extension quantile: for the high the price it ends at or below with that probability,
    for the low the price it ends at or above), on the Yahoo basis ('q') and, when offsets are given, on the NSE official basis ('q_official'); chance of Rs d further extension; quartiles of the extension if it extends."""
    price, Mx, Nn = st["price"], st["M"], st["N"]
    sc, sj = c * np.sqrt(st["sc2"]), c * np.sqrt(st["sj2"])
    est = {}
    for side, (lvl, sname) in enumerate(((Mx, "high"), (Nn, "low"))):
        a = np.log(Mx / price) if side == 0 else np.log(price / Nn)
        to_price = (lambda b: float(price * np.exp(b))) if side == 0 else (lambda b: float(price * np.exp(-b)))
        p0 = 1.0 if st["status"] == "closed" else float(fmax_cdf(a, sc, sj))
        qy = {tau: to_price(max(a, float(fmax_quantile(tau, sc, sj)))) for tau in EXT_TAUS}
        qo = None
        if deltas is not None:
            qb = conv_quantiles(np.array(EXT_TAUS), price, a, sc, sj, deltas[side], side)
            qo = {tau: to_price(float(b)) for tau, b in zip(EXT_TAUS, qb)}
        cond = None
        if st["status"] != "closed" and p0 < 0.999:
            cq = []
            for tp in (0.25, 0.75):
                b = float(fmax_quantile(p0 + tp * (1 - p0), sc, sj))
                cq.append(float(price * np.exp(b) - lvl) if side == 0 else float(lvl - price * np.exp(-b)))
            cond = cq
        est[sname] = {"running": lvl, "p_in": p0, "q": qy, "q_official": qo, "ext_probs": extension_probs(price, lvl, side, sc, sj) if st["status"] != "closed" else {d: 0.0 for d in (5, 10, 20, 40)}, "cond_ext_rs": cond}
    return est


def miss_for_slot(params: dict | None, m: int, price: float) -> dict | None:
    """typical miss in rupees at this time of day from the nested leave-one-out table (stored percentages x price now)."""
    if not params or "miss_by_slot" not in params:
        return None
    tab = params["miss_by_slot"]
    k = str(int(np.clip(m, 1, params.get("miss_max_slot", 23))))
    if k not in tab.get("high", {}):
        return None
    return {s: {"model_rs": tab[s][k]["model_median_miss_pct"] * price / 100, "naive_mean_rs": tab[s][k]["naive_miss_mean_pct"] * price / 100, "naive_median_rs": tab[s][k]["naive_miss_median_pct"] * price / 100} for s in ("high", "low")}


def words(st: dict, est: dict, c: float, pc: float | None, params: dict | None, tag: str = "", c_note: str = "") -> str:
    t = st.get("label_time") or st["asof"].strftime("%H:%M")
    price = st["price"]
    L = []
    chg = f" ({100 * (price / pc - 1):+.2f}% vs the previous official close Rs {pc:,.1f})" if pc else ""
    if st["status"] == "closed":
        L.append(f"Session complete{tag}. Last price (the closing print) Rs {price:,.1f}{chg}. Day range from Yahoo 1-minute bars: low Rs {st['N']:,.1f} - high Rs {st['M']:,.1f} (unofficial; see the Yahoo vs NSE note).")
    else:
        L.append(f"At {t} IST{tag} BSE is Rs {price:,.1f}{chg}; {st['minutes_to_close']:.0f} min to the close. Running range so far (Yahoo 1-minute bars, unofficial): low Rs {st['N']:,.1f} - high Rs {st['M']:,.1f}.")
    off = (params or {}).get("offset_15min")
    if off:
        L.append(f"Yahoo vs NSE: over {off['n']} sessions the NSE official high was above Yahoo's by Rs {off['high']['median']:.1f} typically (mean {off['high']['mean']:.1f}, 90th percentile {off['high']['p90']:.1f}, max {off['high']['max']:.1f}) and the NSE official low below Yahoo's by Rs {off['low']['median']:.1f} typically "
                 f"(mean {off['low']['mean']:.1f}, 90th percentile {off['low']['p90']:.1f}, max {off['low']['max']:.1f}); never the other way in this sample. The ranges below are on the NSE basis (Yahoo path plus that offset), so they sit a little outside the Yahoo figures.")
    for sname, rs_word, cmp_word, bound in (("high", "up", "below", "floor"), ("low", "down", "above", "ceiling")):
        e = est[sname]
        lvl = e["running"]
        q = e["q_official"] or e["q"]
        if st["status"] == "closed":
            L.append(f"The day's {sname} was Rs {lvl:,.1f} on Yahoo; the NSE figure (published about 16:34 IST) is expected at Rs {q[0.5]:,.1f} (nine times in ten {'between' if sname == 'high' else 'between'} Rs {min(lvl, q[0.9]):,.1f} and {max(lvl, q[0.9]):,.1f}).")
            continue
        p = e["p_in"]
        ce = e["cond_ext_rs"]
        ext_txt = f"; if it extends, another Rs {abs(ce[0]):.0f}-{abs(ce[1]):.0f} {rs_word} is typical" if ce and p < 0.995 else ""
        if p >= 0.995:
            verdict = f"the {sname} is in (over 99%: the price would need a very large move to make a new {sname})"
        elif p >= 0.60:
            verdict = f"the {sname} is probably in ({100 * p:.0f}%)" + ext_txt
        elif p <= 0.40:
            verdict = f"the {sname} still has room ({100 * (1 - p):.0f}% chance of a new {sname})" + ext_txt
        else:
            verdict = f"toss-up whether the {sname} is in ({100 * p:.0f}% it is)" + ext_txt
        word_at = "at or below" if sname == "high" else "at or above"
        L.append(f"Final {sname.upper()}: {verdict}. It can not end {cmp_word} Rs {lvl:,.1f} (the running {sname}, the {bound}). Half the time it ends {word_at} Rs {q[0.5]:,.1f}; nine times in ten {word_at} Rs {q[0.9]:,.1f}; 19 times in 20 {word_at} Rs {q[0.95]:,.1f}.")
        if sname == "high" and 0.2 <= p <= 0.9 and (params or {}).get("p_in_note"):
            L.append("   Note: in past sessions this 'is in' probability for the HIGH ran low (the high was in more often than stated; see the calibration table in research/hl/B_liveintraday.md).")
        ep = e["ext_probs"]
        L.append(f"   Chance the {sname} is pushed at least Rs 5 / 10 / 20 / 40 {rs_word} from the running {sname}: " + " / ".join(f"{100 * ep[d]:.0f}%" for d in (5, 10, 20, 40)) + ".")
    ms = miss_for_slot(params, st["m"], price)
    if ms and st["status"] != "closed":
        L.append(f"Typical miss at this time of day (39 past sessions, out of sample, vs the NSE figure): assuming the final high equals the running high is off by Rs {ms['high']['naive_mean_rs']:.0f} on average (half the time under Rs {ms['high']['naive_median_rs']:.0f}); "
                 f"for the low Rs {ms['low']['naive_mean_rs']:.0f} (half under Rs {ms['low']['naive_median_rs']:.0f}). The model's median is off by Rs {ms['high']['model_rs']:.0f} (high) / Rs {ms['low']['model_rs']:.0f} (low) on average.")
    L.append(f"This says how far the extremes usually extend, not which way the price goes (no drift assumed). Volatility multiplier c = {c:.2f}{c_note}. " + ((params or {}).get("calibration_note", "calibration note not available: run --backtest")) + ".")
    return "\n".join(L)


def prev_close_before(day: str) -> float | None:
    try:
        off = load_official()
        return float(off.loc[off.index < day, "close"].iloc[-1])
    except Exception:  # noqa: BLE001
        return None


def get_bars(save: bool = True) -> tuple[pd.DataFrame, bool]:
    """(1-minute bars with date and slot columns, fetched_live).  Falls back to the cached bars if Yahoo cannot be reached."""
    try:
        res = fetch_1m("7d")
        df = LN.rows_1m(res)
        if save:
            Path("results").mkdir(exist_ok=True)
            df = save_cache_1m(df)
        fetched = True
    except Exception as e:  # noqa: BLE001
        print(f"Could not fetch Yahoo 1-minute bars ({e}). Using the cached bars in {BARS1M} if any.")
        df, fetched = load_cache_1m(), False
    if len(df):
        df = df.copy()
        df["date"] = df.t.dt.strftime("%Y-%m-%d")
        df["slot"] = ((df.t.dt.hour * 60 + df.t.dt.minute - 555) // 15).astype(int)
        df = df[(df.slot >= 0) & (df.slot < NB)]
    return df, fetched


def run_live(asof: str | None = None, save: bool = True, date: str | None = None, quiet: bool = False, bars: tuple | None = None, now: dt.datetime | None = None) -> dict | None:
    now = now or dt.datetime.now(IST)
    df_all, fetched = bars if bars is not None else get_bars(save)
    if df_all is None or len(df_all) == 0:
        print("No bars available (Yahoo unreachable or rate-limited, no cache). Try again in a minute: the query2 host is tried first, then query1 with back-off.")
        return None
    today = now.strftime("%Y-%m-%d")
    live_mode = asof is None and date is None
    if live_mode:
        if now.weekday() >= 5:
            print(f"Today ({today}, {now:%A}) is a weekend: the market is closed. Last session in the data: {df_all.date.iloc[-1]}. Use --replay for it or --asof HH:MM to replay it.")
            return None
        if now.hour * 60 + now.minute < 9 * 60 + 15:
            print(f"Before 09:15 IST ({now:%H:%M}): the session has not started, no bars for today yet. Use --replay for the last session ({df_all.date.iloc[-1]}).")
            return None
        if df_all.date.iloc[-1] != today:
            print(f"No Yahoo bars for today ({today}): holiday, or the feed has not started yet. Last session in the data: {df_all.date.iloc[-1]}. Use --replay for it.")
            return None
        if not fetched:
            print("WARNING: Yahoo could not be reached; the numbers below use CACHED bars and are not live.")
    sdate = date or df_all.date.iloc[-1]
    df1 = df_all[df_all.date == sdate]
    if df1.empty:
        print(f"No 1-minute bars for {sdate} (Yahoo keeps about 7 sessions; cached sessions: {sorted(df_all.date.unique())}).")
        return None
    if asof:
        df1 = df1[df1.t.dt.strftime("%H:%M") < asof]
        if df1.empty:
            print(f"No bars before {asof} on {sdate} (the session starts at 09:15).")
            return None
    hist = [s for s in LN.load_history() if s["date"] != sdate]
    ev, _ = LN.profile(hist)
    params = load_params()
    c_note = ""
    if params and "c_live" in params:
        c = float(params["c_live"])
        deltas = (np.array(params["delta_high"]), np.array(params["delta_low"]))
        if not live_mode and sdate in params.get("c_loo_by_date", {}):
            c, c_note = float(params["c_loo_by_date"][sdate]), " (leave-one-out value for this session, so the replay does not see itself)"
            tr_d = [i for i, d_ in enumerate(params["dates"]) if d_ != sdate]
            deltas = (deltas[0][tr_d], deltas[1][tr_d])
    else:
        S15 = Sample(load_sessions_15m(), NB, 23, "15min", full_only=(NB - 2, NB - 1))
        c = fit_live_c(S15)
        deltas = offsets_arrays(S15)
        c_note = " (fitted now; run --backtest to store the calibration tables)"
    after_close = live_mode and (now.hour * 60 + now.minute) >= 15 * 60 + 35
    st = state_from_bars(df1, ev, force_closed=after_close)
    if after_close and df1.t.dt.strftime("%H:%M").iloc[-1] < "15:28":
        c_note += " (the closing-auction print is not in the Yahoo feed yet; all bars used)"
    if asof:
        st["label_time"] = asof
    est = estimate(st, c, deltas)
    pc = prev_close_before(sdate)
    tag = f" [replay as of {asof}, session {sdate}]" if asof else (f" [session {sdate}]" if date else "")
    text = words(st, est, c, pc, params, tag, c_note)
    out = {"logged_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "asof_ist": st["asof"].isoformat(timespec="seconds"), "session": sdate, "mode": "live" if live_mode else "replay", "status": st["status"],
           "price_now": st["price"], "running_high_yahoo": st["M"], "running_low_yahoo": st["N"], "c": c, "slot_m": st["m"], "slot_frac": round(st["frac"], 3), "sc": float(np.sqrt(st["sc2"])), "sj": float(np.sqrt(st["sj2"])),
           "high": est["high"], "low": est["low"], "prev_official_close": pc, "source": "Yahoo chart API 1-minute bars (unofficial)"}
    if save:
        Path("results").mkdir(exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps(out, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o)) + "\n")
    if not quiet:
        print(text)
    out["text"] = text
    return out


def run_replay(save: bool = True) -> pd.DataFrame | None:
    bars = get_bars(save)
    cache = bars[0]
    if cache is None or len(cache) == 0:
        print("no bars available")
        return None
    last = cache.date.iloc[-1]
    off = load_official()
    ho, lo_, o_ = (float(off.high[last]), float(off.low[last]), float(off.open[last])) if last in off.index else (np.nan, np.nan, np.nan)
    d1 = cache[cache.date == last]
    print(f"Replay of {last}: NSE official open {o_}, high {ho}, low {lo_}; Yahoo 1-minute bars: high {d1.high.max()}, low {d1.low.min()} ({len(d1)} bars; NSE minus Yahoo: high {ho - d1.high.max():+.2f}, low {d1.low.min() - lo_:+.2f}).")
    rows = []
    for hhmm in ("09:45", "10:30", "11:30", "12:30", "13:15", "14:00", "14:30", "15:00"):
        o = run_live(asof=hhmm, save=False, date=last, quiet=True, bars=bars)
        if o is None:
            continue
        h, l = o["high"], o["low"]
        qh, ql = h["q_official"], l["q_official"]
        rows.append({"session": last, "asof": hhmm, "price_then": o["price_now"], "run_high_yahoo": o["running_high_yahoo"], "run_low_yahoo": o["running_low_yahoo"], "p_high_in": h["p_in"], "p_low_in": l["p_in"],
                     "high_at_or_below_50": qh[0.5], "high_at_or_below_90": qh[0.9], "high_at_or_below_95": qh[0.95], "low_at_or_above_50": ql[0.5], "low_at_or_above_90": ql[0.9], "low_at_or_above_95": ql[0.95],
                     "official_high": ho, "official_low": lo_, "high_le_q50": bool(ho <= qh[0.5] + 1e-9), "high_le_q90": bool(ho <= qh[0.9] + 1e-9), "low_ge_q50": bool(lo_ >= ql[0.5] - 1e-9), "low_ge_q90": bool(lo_ >= ql[0.9] - 1e-9),
                     "c": o["c"]})
    df = pd.DataFrame(rows)
    if save:
        Path("results").mkdir(exist_ok=True)
        df.to_csv("results/live_hl_replay_latest.csv", index=False)
    show = df[["asof", "price_then", "run_high_yahoo", "run_low_yahoo", "p_high_in", "p_low_in", "high_at_or_below_50", "high_at_or_below_90", "official_high", "high_le_q50", "high_le_q90",
               "low_at_or_above_50", "low_at_or_above_90", "official_low", "low_ge_q50", "low_ge_q90"]].copy()
    print(show.round(2).to_string(index=False))
    return df


# =============================================================================================================================== self-test and backtest main
def selftest() -> dict:
    out = {}
    rng = np.random.default_rng(1)
    ev = np.array([2.0, 1.0, 0.5, 0.8]) * 1e-5
    sj = np.sqrt(1.5e-5)
    nsub, chunk, reps = 50, 20000, 10
    sig = np.repeat(np.sqrt(ev / nsub), nsub)
    Fs = []
    for _ in range(reps):
        path = np.cumsum(rng.standard_normal((chunk, len(sig))) * sig, axis=1)
        x0 = np.concatenate([np.zeros((chunk, 1)), path[:, :-1]], axis=1)
        mx = 0.5 * (x0 + path + np.sqrt((path - x0) ** 2 - 2 * sig ** 2 * np.log(rng.random((chunk, len(sig))))))
        Fs.append(np.maximum(np.maximum(mx.max(axis=1), path[:, -1] + rng.standard_normal(chunk) * sj), 0))
    F = np.concatenate(Fs)
    sc = np.sqrt(ev.sum())
    rows = []
    for b in (0.001, 0.003, 0.005, 0.008, 0.012):
        rows.append({"b": b, "monte_carlo": float((F <= b).mean()), "closed_form": float(fmax_cdf(b, sc, sj))})
    out["closed_form_vs_montecarlo"] = rows
    out["max_abs_diff"] = max(abs(r["monte_carlo"] - r["closed_form"]) for r in rows)
    out["n_paths"] = int(len(F))
    # quantile function / table consistency
    tau = 0.9
    out["quantile_exact_vs_table"] = float(abs(fmax_quantile(tau, sc, sj) - base_quantiles(np.array(sc ** 2), np.array(sj ** 2))[list(TAUS).index(0.9)]))
    # profile identical to live_nowcast.profile
    S15 = load_sessions_15m()
    S = Sample(S15, NB, 23, "15min", full_only=(NB - 2, NB - 1))
    ev_ln, _ = LN.profile(LN.load_history())
    out["profile_max_abs_diff_vs_live_nowcast"] = float(np.max(np.abs(ev_ln - S.profile(range(S.n), True))))
    out["n_sessions_15min"] = S.n
    # (a) a real LOO state against a path simulation (piecewise-constant slot variances, exact Brownian-bridge maxima, one auction jump)
    R = engine_loo(S, "y", verbose=False)
    jm = CHECK15["12:30"] - 1
    t = int(np.argmin(np.abs(R.p0["M1"][:, jm, 0] - 0.4)))          # a state with a non-trivial chance that the high is not yet in
    ev, c = R.ev[t], float(R.c["M1"][t])
    m = jm + 1
    sig_slots = c * np.sqrt(ev[m:NB - 1])
    nsub, N = 20, 400000
    sig = np.repeat(sig_slots / np.sqrt(nsub), nsub)
    path = np.cumsum(rng.standard_normal((N, len(sig))) * sig, axis=1)
    x0 = np.concatenate([np.zeros((N, 1)), path[:, :-1]], axis=1)
    mx = 0.5 * (x0 + path + np.sqrt((path - x0) ** 2 - 2 * sig ** 2 * np.log(rng.random((N, len(sig))))))
    fut = np.maximum(np.maximum(mx.max(axis=1), path[:, -1] + rng.standard_normal(N) * c * np.sqrt(ev[NB - 1])), 0.0)
    a = S.a[t, jm, 0]
    mc_q = {tau: float(max(a, np.quantile(fut, tau))) for tau in (0.5, 0.75, 0.9, 0.95)}
    mod_q = {tau: float(R.Q["M1"][t, jm, 0, list(TAUS).index(tau)]) for tau in (0.5, 0.75, 0.9, 0.95)}
    out["state_check"] = {"session": str(S.dates[t]), "checkpoint": "12:30", "a_log": float(a), "c": c, "monte_carlo_quantiles": mc_q, "model_quantiles": mod_q,
                          "mc_p_high_in": float((fut <= a).mean()), "model_p_high_in": float(R.p0["M1"][t, jm, 0])}
    # (b) leak test: wipe everything about the scored session that is not known at the checkpoint (final extremes, future bars) -> its forecasts must not move
    S2 = Sample(load_sessions_15m(), NB, 23, "15min", full_only=(NB - 2, NB - 1))
    S2.yy[t] = 99.0
    S2.yo[t] = 99.0
    S2.fmax[t] = 99.0
    S2.R2[t] = 1e-3
    R2_ = engine_loo(S2, "y", verbose=False)
    out["leak_test_max_abs_change_in_forecasts_of_wiped_session"] = {v: float(np.nanmax(np.abs(R.Q[v][t] - R2_.Q[v][t]))) for v in ("M0", "M1", "M2a", "M3a", "M4a", "M5", "M6", "M7", "B1", "B2", "B3", "B4")}
    Path("results").mkdir(exist_ok=True)
    Path("results/live_hl_selftest.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


def run_backtest(hourly_path: str | None) -> dict:
    t0 = time.time()
    Path("results").mkdir(exist_ok=True)
    all_variants, all_cov, all_pooled, all_rel = [], [], [], []
    # ---------------------------------------------------------------- 15-minute sample, nested LOO
    S15 = Sample(load_sessions_15m(), NB, 23, "15min", full_only=(NB - 2, NB - 1))
    print(f"15-minute sample: {S15.n} sessions {S15.dates[0]} .. {S15.dates[-1]}; sessions without a 15:15 bar: {int((~S15.full).sum())}")
    cps15 = {k: v - 1 for k, v in CHECK15.items()}          # index into ms (ms starts at 1)
    wins15 = {"All 39 sessions (all in Final and post-closing-auction)": np.ones(S15.n, bool), "31 sessions that have a 15:15 bar": S15.full.copy()}
    R_o = engine_loo(S15, "o")
    R_y = engine_loo(S15, "y")
    add_m1c(S15, R_o, R_y)
    for R_, y_, lab in ((R_o, S15.yo, "official NSE final H/L"), (R_y, S15.yy, "Yahoo-bars final H/L")):
        sm = summarise(R_, y_, "15min LOO nested", cps15, wins15, 2, lab)
        all_variants += sm["variants"]
        all_cov += sm["coverage"]
        all_pooled += sm["pooled"]
        if R_ is R_y:
            all_rel += p_in_reliability(R_, "15min LOO nested", wins15, cps15)
    mt = miss_tables(R_o, S15.yo, "15min", np.arange(S15.n), "M1c")
    mt.to_csv("results/live_hl_miss_by_slot_15min.csv", index=False)
    # per-session forecasts for the report (official basis M1c and Yahoo basis M1) at the 8 checkpoints
    rows = []
    for t in range(S15.n):
        for cn, ci in cps15.items():
            P = S15.P[t, ci]
            r = {"date": S15.dates[t], "checkpoint": cn, "price": P, "running_high_yahoo": P * np.exp(S15.a[t, ci, 0]), "running_low_yahoo": P * np.exp(-S15.a[t, ci, 1]),
                 "official_high": S15.sess[t]["Ho"], "official_low": S15.sess[t]["Lo"], "yahoo_final_high": S15.sess[t]["Hy"], "yahoo_final_low": S15.sess[t]["Ly"], "has_1515_bar": bool(S15.full[t]),
                 "c_yahoo_fit": R_y.c["M1"][t], "p_high_in": R_y.p0["M1"][t, ci, 0], "p_low_in": R_y.p0["M1"][t, ci, 1]}
            for side, sn in ((0, "high"), (1, "low")):
                for tau in (0.5, 0.9, 0.95):
                    for lab, R_, vv in (("off", R_o, "M1c"), ("yh", R_y, "M1")):
                        q = R_.Q[vv][t, ci, side, list(TAUS).index(tau)]
                        r[f"{sn}_ext_q{int(tau * 100):02d}_{lab}"] = P * np.exp(q) if side == 0 else P * np.exp(-q)
            rows.append(r)
    pd.DataFrame(rows).to_csv("results/live_hl_loo_forecasts_15min.csv", index=False)
    # ---------------------------------------------------------------- hourly sample, expanding walk-forward
    Sh = Sample(load_sessions_hourly(hourly_path), 7, 6, "hourly")
    print(f"hourly sample: {Sh.n} complete sessions {Sh.dates[0]} .. {Sh.dates[-1]}; post-closing-auction sessions {int(Sh.auc.sum())}")
    warm = 50
    cpsh = {k: v - 1 for k, v in CHECKH.items()}
    winsh = windows_hourly(Sh, warm)
    Rh = engine_wf(Sh, "y", warm=warm)
    smh = summarise(Rh, Sh.yy, "hourly walk-forward", cpsh, winsh, 5, "Yahoo hourly-bars final H/L")
    all_variants += smh["variants"]
    all_cov += smh["coverage"]
    all_pooled += smh["pooled"]
    all_rel += p_in_reliability(Rh, "hourly walk-forward", winsh, cpsh)
    miss_tables(Rh, Sh.yy, "hourly", np.where(winsh["Final (2025-07-01 on)"])[0], "M1").to_csv("results/live_hl_miss_by_slot_hourly.csv", index=False)
    # ---------------------------------------------------------------- sensitivity: the 15-minute sample scored strictly chronologically (past sessions only), 19 scored sessions
    warm15 = 20
    Rw_o = engine_wf(S15, "o", warm=warm15, prof_min=10, verbose=False)
    Rw_y = engine_wf(S15, "y", warm=warm15, prof_min=10, verbose=False)
    add_m1c(S15, Rw_o, Rw_y, chrono=True, first=warm15)
    mask_w = np.zeros(S15.n, bool)
    mask_w[warm15:] = True
    winsw = {f"chronological, scored {S15.dates[warm15]} .. {S15.dates[-1]}": mask_w}
    for R_, y_, lab in ((Rw_o, S15.yo, "official NSE final H/L"), (Rw_y, S15.yy, "Yahoo-bars final H/L")):
        sm = summarise(R_, y_, "15min chronological (past sessions only)", cps15, winsw, 2, lab)
        all_variants += sm["variants"]
        all_cov += sm["coverage"]
        all_pooled += sm["pooled"]
    pd.DataFrame(all_variants).to_csv("results/live_hl_backtest_variants.csv", index=False)
    pd.DataFrame(all_cov).to_csv("results/live_hl_backtest_coverage_checkpoints.csv", index=False)
    pd.DataFrame(all_pooled).to_csv("results/live_hl_backtest_coverage_pooled.csv", index=False)
    pd.DataFrame(all_rel).to_csv("results/live_hl_backtest_p_in_reliability.csv", index=False)
    pd.DataFrame({"date": Sh.dates, "c_M1": Rh.c["M1"], "c_B3": Rh.c["B3"]}).iloc[warm:].to_csv("results/live_hl_hourly_c_path.csv", index=False)
    pd.DataFrame({"date": S15.dates, "c_M1_official_fit": R_o.c["M1"], "c_M1_yahoo_fit": R_y.c["M1"], "c_B3_official_fit": R_o.c["B3"], "has_1515_bar": S15.full}).to_csv("results/live_hl_loo_c_15min.csv", index=False)
    # ---------------------------------------------------------------- offsets Yahoo vs NSE
    off15 = pd.DataFrame([{"sample": "15min", "date": x["date"], "yahoo_high": x["Hy"], "nse_high": x["Ho"], "nse_minus_yahoo_high": x["Ho"] - x["Hy"], "yahoo_low": x["Ly"], "nse_low": x["Lo"],
                           "yahoo_minus_nse_low": x["Ly"] - x["Lo"], "has_1515_bar": bool(x["has_last"])} for x in S15.sess])
    offh = pd.DataFrame([{"sample": "hourly", "date": x["date"], "yahoo_high_as_traded": x["Hy"] * x["kf"], "nse_high": x["Ho"] * x["kf"], "nse_minus_yahoo_high": (x["Ho"] - x["Hy"]) * x["kf"], "yahoo_low_as_traded": x["Ly"] * x["kf"],
                          "nse_low": x["Lo"] * x["kf"], "yahoo_minus_nse_low": (x["Ly"] - x["Lo"]) * x["kf"]} for x in Sh.sess if np.isfinite(x["Ho"])])
    pd.concat([off15, offh]).to_csv("results/live_hl_offsets_yahoo_vs_nse.csv", index=False)
    post = offh[offh.date >= CAS_START]
    offsum = {"15min": {"n": int(len(off15)), "high": stats_of(off15.nse_minus_yahoo_high), "low": stats_of(off15.yahoo_minus_nse_low)},
              "hourly_all": {"n": int(len(offh)), "high": stats_of(offh.nse_minus_yahoo_high), "low": stats_of(offh.yahoo_minus_nse_low)},
              "hourly_post_cas": {"n": int(len(post)), "high": stats_of(post.nse_minus_yahoo_high), "low": stats_of(post.yahoo_minus_nse_low)}}
    c1 = load_cache_1m()
    if len(c1):
        c1 = c1.copy()
        c1["date"] = c1.t.dt.strftime("%Y-%m-%d")
        off_d = load_official()
        r1 = []
        for d_, g in c1.groupby("date"):
            if d_ in off_d.index and len(g) > 300:
                r1.append({"date": d_, "n_bars": len(g), "yahoo_1m_high": g.high.max(), "nse_high": off_d.high[d_], "nse_minus_yahoo_high": off_d.high[d_] - g.high.max(), "yahoo_1m_low": g.low.min(), "nse_low": off_d.low[d_],
                           "yahoo_minus_nse_low": g.low.min() - off_d.low[d_]})
        pd.DataFrame(r1).to_csv("results/live_hl_offsets_1m_sessions.csv", index=False)
        if r1:
            offsum["1min_sessions"] = {"n": len(r1), "high": stats_of([r["nse_minus_yahoo_high"] for r in r1]), "low": stats_of([r["yahoo_minus_nse_low"] for r in r1])}
        chk = check_1m(S15, R_y, c1)
        offsum["check_1m"] = chk
        offsum["consistency_1m_vs_15m"] = consistency_1m_vs_15m(S15, c1)
    Path("results/live_hl_offsets_summary.json").write_text(json.dumps(offsum, indent=1))
    # ---------------------------------------------------------------- parameters for the live tool
    c_live = fit_live_c(S15)
    miss_by_slot = {"high": {}, "low": {}}
    for sname in ("high", "low"):
        sub = mt[mt.side == sname].set_index("slot_m")
        for m in sub.index:
            win = sub.loc[[k for k in (m - 1, m, m + 1) if k in sub.index]]
            miss_by_slot[sname][str(int(m))] = {"model_median_miss_pct": float(win.model_median_miss_pct_mean.mean()), "naive_miss_mean_pct": float(win.naive_running_extreme_miss_pct_mean.mean()),
                                                 "naive_miss_median_pct": float(win.naive_running_extreme_miss_pct_median.mean())}
    def p_gap(R_, wmask, cps, side, lo=0.3, hi=0.9):
        idx = np.where(wmask)[0]
        cpi = list(cps.values())
        p = R_.p0["M1"][idx][:, cpi, side].ravel()
        ev = (R_.S.yy[idx][:, cpi, side] <= R_.S.a[idx][:, cpi, side] + 1e-9).ravel().astype(float)
        sel_ = (p >= lo) & (p < hi)
        return float(p[sel_].mean()), float(ev[sel_].mean()), int(sel_.sum())
    pn = {}
    for side, sn in ((0, "HIGH"), (1, "LOW")):
        a15 = p_gap(R_y, np.ones(S15.n, bool), cps15, side)
        ah = p_gap(Rh, winsh["Final (2025-07-01 on)"], cpsh, side)
        pn[sn] = f"{sn}: stated {100 * a15[0]:.0f}% -> in {100 * a15[1]:.0f}% of {a15[2]} states (15-minute, 39 sessions), stated {100 * ah[0]:.0f}% -> {100 * ah[1]:.0f}% of {ah[2]} states (hourly Final, 306 sessions)"
    p_in_note = ("Reliability of 'the high/low is probably in' when the model said 30-90% (pooled over checkpoints; states are dependent): " + "; ".join(pn.values()) + ". "
                 "So a stated 'is in' probability was somewhat conservative (the extreme was in more often than stated), clearly so for the HIGH.")
    cov_pool = pd.DataFrame(all_pooled)
    sel = cov_pool[(cov_pool["sample"] == "15min LOO nested") & (cov_pool.variant == "M1c") & (cov_pool.target == "official NSE final H/L") & (cov_pool.band == "upto") & cov_pool.window.str.startswith("All 39")]
    def pc(side, lev):
        return sel[(sel.side == side) & (sel.level == lev)].iloc[0].pooled_coverage
    note = (f"checked leave-one-session-out on {S15.n} sessions (8 checkpoints each, strongly dependent): 'half the time at or below/above' held {100 * pc('high', 0.5):.0f}% (high) / {100 * pc('low', 0.5):.0f}% (low) of the time and "
            f"'nine times in ten' held {100 * pc('high', 0.9):.0f}% / {100 * pc('low', 0.9):.0f}% (effective sample about {S15.n} sessions, so +-8 points on the first and +-5 on the second from sampling alone; per-checkpoint table in research/hl/B_liveintraday.md)")
    dh, dl = offsets_arrays(S15)
    params = {"c_live": c_live, "n_sessions": S15.n, "dates": list(map(str, S15.dates)), "delta_high": dh.tolist(), "delta_low": dl.tolist(), "miss_by_slot": miss_by_slot, "miss_max_slot": 23, "offset_15min": offsum["15min"],
              "calibration_note": note, "p_in_note": p_in_note, "c_loo_by_date": {str(d): float(cv) for d, cv in zip(S15.dates, R_y.c["M1"])}, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "data_last_session": str(S15.dates[-1])}
    Path(PARAMS).write_text(json.dumps(params, indent=1))
    summary = {"c_live": c_live, "elapsed_s": time.time() - t0, "note": note}
    Path("results/live_hl_backtest_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return summary


def main():
    os.chdir(ROOT)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--asof", default=None, help="replay the last session as of HH:MM IST (bars that started before HH:MM)")
    ap.add_argument("--date", default=None, help="session date YYYY-MM-DD from the cached 1-minute bars (default: the last session)")
    ap.add_argument("--replay", action="store_true", help="table for the last completed session")
    ap.add_argument("--backtest", action="store_true", help="nested leave-one-session-out (15-minute) + walk-forward (hourly); writes results/live_hl_*")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--nosave", action="store_true", help="do not write the log / caches")
    ap.add_argument("--hourly", default=None, help="path to the Yahoo hourly JSON (h60_BSE.NS.json); copied once to results/live_hl_hourly_bars.csv")
    ap.add_argument("--now", default=None, help="TEST ONLY: pretend the clock is 'YYYY-MM-DD HH:MM' IST (exercises the weekend / before-open / holiday / after-close messages)")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.backtest:
        run_backtest(a.hourly)
    elif a.replay:
        run_replay(not a.nosave)
    else:
        run_live(asof=a.asof, save=not a.nosave, date=a.date, now=(dt.datetime.strptime(a.now, "%Y-%m-%d %H:%M").replace(tzinfo=IST) if a.now else None))


if __name__ == "__main__":
    main()
