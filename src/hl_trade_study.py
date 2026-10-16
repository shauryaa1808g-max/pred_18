"""Specialist C: can the high / low estimates be traded?  (NSE:BSE)

Part 1 (descriptive): excursions, stop / target hit probabilities by volatility regime, how often the open / first hour holds the day's extremes.
Part 2 (inferential): eight pre-fixed rules (31 variants), walk-forward, costs, fill conventions, Holm, and a random-walk placebo.
The design is written in research/hl/C_tradeability.md section 0 BEFORE any result was computed.

Run from the repo root (python3; no network; reads data/processed/*.csv, results/hl_eval_predictions.csv, the hourly Yahoo json):
  python3 src/hl_trade_study.py selftest
  python3 src/hl_trade_study.py part1  --hourly <h60_BSE.NS.json>
  python3 src/hl_trade_study.py part2  --hourly <h60_BSE.NS.json>
  python3 src/hl_trade_study.py placebo --hourly <h60_BSE.NS.json> --reps 2000 [--procs 4]
  python3 src/hl_trade_study.py finish --hourly <h60_BSE.NS.json>
  python3 src/hl_trade_study.py posthoc --hourly <h60_BSE.NS.json>   (post-hoc variants + pooled-clock placebo sensitivity; needs the placebo output)
  python3 src/hl_trade_study.py today --hourly <h60_BSE.NS.json>     (numbers for 16 Oct 2026)
(`all` = selftest, part1, part2, placebo, finish, posthoc, today.)  Temporary placebo output goes to $HL_TRADE_TMP (default /tmp/hl_trade).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M                                    # noqa: E402
from common import load_bse                            # noqa: E402

# ----------------------------------------------------------------------------- constants (fixed in section 0 of the report)
RS = 3428.0                    # reference price for rupee conversion (official close of 15 Oct 2026)
TICK = 0.10 / RS               # one tick (Rs 0.10 at today's price) as a fraction of price
COST = 0.0010                  # 0.10% round trip
SLIP = 0.0005                  # 0.05% per marketable leg (stress S1 only)
LAM = 0.94
D0 = pd.Timestamp("2019-01-01")
VAL0, FIN0, CAS0, MODEL0 = pd.Timestamp("2024-07-01"), pd.Timestamp("2025-07-01"), pd.Timestamp("2026-08-04"), pd.Timestamp("2020-02-25")
EX_DATE = pd.Timestamp("2025-05-23")                   # 2:1 bonus; Yahoo hourly prices before it are raw/3
WINDOWS = ("all", "dev", "val", "final", "cas")
HOURS = ["09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:15"]
K5 = 75                        # five-minute steps in 09:15-15:30
BAR_STEPS = [0, 12, 24, 36, 48, 60, 72]
PRED = Path("results/hl_eval_predictions.csv")
OUT = Path("results")
TMP = Path(os.environ.get("HL_TRADE_TMP", "/tmp/hl_trade"))
SEED = 20261015


# ----------------------------------------------------------------------------- loading
def load_daily() -> pd.DataFrame:
    """bse_daily.csv + bse_daily_extra.csv, no network (same table official_bars.load_bse_ext() returns after its download step)."""
    d = load_bse()
    e = pd.read_csv("data/processed/bse_daily_extra.csv", index_col=0, parse_dates=True)
    e = e[~e.index.isin(d.index)].reindex(columns=d.columns)
    d = pd.concat([d, e]).sort_index()
    ok = (d[["prev", "open", "high", "low", "close"]] > 0).all(axis=1) & (d["high"] >= d["low"]) & (d["high"] >= d[["open", "close"]].max(axis=1) - 1e-9) & (d["low"] <= d[["open", "close"]].min(axis=1) + 1e-9)
    if not ok.all():
        raise ValueError(f"bad OHLC rows {d.index[~ok].tolist()[:5]}")
    return d


class Sess:
    """Container; every array has shape [R, n] (daily) or [R, m, 7] (hourly); R = 1 for the real data, > 1 for placebo histories."""

    def __init__(self, dates, O, H, L, C, P0, hidx, ho=None, hh=None, hl=None, hc=None):
        self.dates, self.O, self.H, self.L, self.C, self.P0 = pd.DatetimeIndex(dates), O, H, L, C, P0
        self.hidx, self.ho, self.hh, self.hl, self.hc = hidx, ho, hh, hl, hc
        self.n = len(self.dates)
        self.i0 = int(np.searchsorted(self.dates.values, D0.to_datetime64()))


def load_hourly(path: str, d: pd.DataFrame):
    """Complete 7-bar sessions that are in the daily file; Yahoo prices x3 before the 23 May 2025 ex-date (official raw units)."""
    r = json.load(open(path))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"t": pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata"), "o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"], "v": q["volume"]}).dropna(subset=["o", "h", "l", "c"])
    df["date"] = pd.to_datetime(df.t.dt.strftime("%Y-%m-%d"))
    df["hm"] = df.t.dt.strftime("%H:%M")
    keep, arrs = [], []
    audit = {"dates_in_file": int(df.date.nunique()), "not_in_daily": [], "not_7_bars": []}
    for dt_, g in df.groupby("date"):
        if dt_ not in d.index:
            audit["not_in_daily"].append(str(dt_.date()))
            continue
        g = g.sort_values("t")
        if list(g.hm) != HOURS:
            audit["not_7_bars"].append(str(dt_.date()))
            continue
        f = 3.0 if dt_ < EX_DATE else 1.0
        keep.append(dt_)
        arrs.append(np.column_stack([g.o.values * f, g.h.values * f, g.l.values * f, g.c.values * f]))
    A = np.stack(arrs)                                  # [m, 7, 4]
    audit["sessions_used"] = len(keep)
    return pd.DatetimeIndex(keep), A[..., 0], A[..., 1], A[..., 2], A[..., 3], audit


def real_sess(d: pd.DataFrame, hpath: str):
    hd, ho, hh, hl, hc, audit = load_hourly(hpath, d)
    hidx = d.index.get_indexer(hd)
    S = Sess(d.index, d.open.values[None], d.high.values[None], d.low.values[None], d.close.values[None], d.prev.values[None], hidx, ho[None], hh[None], hl[None], hc[None])
    return S, audit


# ----------------------------------------------------------------------------- estimators (all use sessions strictly before t)
def ewma_rms(x: np.ndarray, lam: float = LAM, warm: int = 30) -> np.ndarray:
    """EWMA of squares, value at t uses x[:t]; first `warm` sessions initialise (the project's S1).  Works on [..., n]."""
    n = x.shape[-1]
    s = np.full(x.shape, np.nan)
    v = np.mean(x[..., :warm] ** 2, axis=-1)
    for t in range(warm, n):
        s[..., t] = np.sqrt(v)
        v = lam * v + (1 - lam) * x[..., t] ** 2
    return s


def roll_q(x: np.ndarray, qs, w: int = 250) -> np.ndarray:
    """Trailing empirical quantiles of x[t-w:t] (t >= w).  Returns [len(qs), ..., n]."""
    from numpy.lib.stride_tricks import sliding_window_view
    n = x.shape[-1]
    out = np.full((len(qs),) + x.shape, np.nan)
    v = sliding_window_view(x, w, axis=-1)[..., : n - w, :]
    out[..., w:] = np.quantile(v, qs, axis=-1)
    return out


# ----------------------------------------------------------------------------- fill conventions
def tt_buy(low, level, mode):
    """A resting buy at `level` fills if the low trades through it: 0 strict, 1 one tick through, 2 through by 0.10%."""
    if mode == 0:
        return low < level
    if mode == 1:
        return low <= level * (1 - TICK)
    return low <= level * (1 - 0.001)


def tt_sell(high, level, mode):
    if mode == 0:
        return high > level
    if mode == 1:
        return high >= level * (1 + TICK)
    return high >= level * (1.001)


def pack(fill, gross, legs, pos, elig=None):
    """fill/gross/legs/elig have shape [R, k]; `elig` marks the sessions where the variant's inputs exist (scale estimator warmed up, model quantiles stored)."""
    fill = np.asarray(fill, bool)
    elig = np.ones_like(fill) if elig is None else np.asarray(elig, bool)
    fill = fill & elig
    gross = np.where(fill, gross, np.nan)
    legs = np.broadcast_to(legs, fill.shape).astype(float)
    return {"fill": fill, "gross": gross, "legs": np.where(fill, legs, np.nan), "pos": np.asarray(pos), "elig": elig}


# ----------------------------------------------------------------------------- the rules
def load_model(S: Sess):
    if not PRED.exists():
        return None
    m = pd.read_csv(PRED, parse_dates=["date"]).set_index("date")
    return m.reindex(S.dates)


def estimators(S: Sess):
    G, LO, HO = np.log(S.O / S.P0), np.log(S.L / S.O), np.log(S.H / S.O)
    return {"G": G, "LO": LO, "HO": HO, "I": np.log(S.C / S.O), "R": np.log(S.C / S.P0),
            "sigL": ewma_rms(LO), "sigH": ewma_rms(HO), "sigG": ewma_rms(G), "sigI": ewma_rms(np.log(S.C / S.O)), "sigR": ewma_rms(np.log(S.C / S.P0))}


def bracket(S, E, side, s, t, mode, optimistic=False, order=None):
    """Fixed bracket from the open.  order: optional [R,n] array with +1 stop first, -1 target first, 0 unknown (hourly resolved)."""
    O, H, L, C = S.O, S.H, S.L, S.C
    if side == "long":
        hit_stop, hit_tgt = L <= O * (1 - s), tt_sell(H, O * (1 + t), mode)
        close_ret = C / O - 1
    else:
        hit_stop, hit_tgt = H >= O * (1 + s), tt_buy(L, O * (1 - t), mode)
        close_ret = 1 - C / O
    both = hit_stop & hit_tgt
    if order is not None:
        stopfirst = (hit_stop & ~hit_tgt) | (both & (order >= 0))
        tgtfirst = (hit_tgt & ~hit_stop) | (both & (order < 0))
    elif optimistic:
        stopfirst, tgtfirst = hit_stop & ~hit_tgt, hit_tgt
    else:
        stopfirst, tgtfirst = hit_stop, hit_tgt & ~hit_stop
    gross = np.where(stopfirst, -s, np.where(tgtfirst, t, close_ret))
    legs = np.where(tgtfirst, 1.0, 2.0)
    return np.ones_like(gross, bool), gross, legs, both


def run_variants(S: Sess, mode: int = 0, model: pd.DataFrame | None = None, with_model: bool = True) -> dict:
    """All 31 variants (model variants only when `model` is given).  Returns {name: pack(...)}; positions index S.dates."""
    E = estimators(S)
    n, i0 = S.n, S.i0
    pos = np.arange(i0, n)
    sl = (Ellipsis, slice(i0, n))
    O, H, L, C, P0 = (a[sl] for a in (S.O, S.H, S.L, S.C, S.P0))
    out = {}
    # ---- R1 / R2: sigma-scaled limit orders around the open
    for k in (1.0, 0.5, 1.5):
        lv = O * np.exp(-k * E["sigL"][sl])
        out[f"R1_k{k}"] = pack(tt_buy(L, lv, mode), C / lv - 1, 1, pos, np.isfinite(lv))
        lv = O * np.exp(k * E["sigH"][sl])
        out[f"R2_k{k}"] = pack(tt_sell(H, lv, mode), 1 - C / lv, 1, pos, np.isfinite(lv))
    # ---- R5: gap reversion
    zG = E["G"][sl] / E["sigG"][sl]
    for z0 in (1.0, 0.5, 1.5):
        buy, sell = zG <= -z0, zG >= z0
        out[f"R5_z{z0}"] = pack(buy | sell, np.where(buy, C / O - 1, 1 - C / O), 2, pos, np.isfinite(zG))
    # ---- R6: brackets from the open
    for side, s, t in (("long", 0.01, 0.02), ("long", 0.02, 0.01), ("short", 0.01, 0.02), ("short", 0.02, 0.01)):
        f, g, lg, _ = bracket(S, E, side, s, t, mode)
        out[f"R6_{side}_s{int(s*100)}_t{int(t*100)}"] = pack(f[sl], g[sl], lg[sl], pos)
    # ---- EMP250 siblings of R7 / R8 (post-open, benchmark level)
    qL = roll_q(E["LO"], [0.25, 0.10])
    qH = roll_q(E["HO"], [0.75, 0.90])
    for j, tau in enumerate(("q25", "q10")):
        lv = O * np.exp(qL[j][sl])
        out[f"R7_emp_{tau}"] = pack(tt_buy(L, lv, mode), C / lv - 1, 1, pos, np.isfinite(lv))
    for j, tau in enumerate(("q75", "q90")):
        lv = O * np.exp(qH[j][sl])
        out[f"R8_emp_{tau}"] = pack(tt_sell(H, lv, mode), 1 - C / lv, 1, pos, np.isfinite(lv))
    # ---- R7 / R8: the project's stored model quantiles (real data only)
    if model is not None and with_model:
        m = {c: model[c].values[None, :][sl] for c in model.columns if c.startswith(("P_S6_", "W_I6_"))}
        have = np.isfinite(m["W_I6_L_q25"])
        for tau in ("q25", "q10"):
            lv = m[f"W_I6_L_{tau}"]
            out[f"R7_post_{tau}"] = pack(tt_buy(L, lv, mode), C / lv - 1, 1, pos, have)
            lv = m[f"P_S6_L_{tau}"]
            atopen = O <= lv
            out[f"R7_pre_{tau}"] = pack(atopen | tt_buy(L, lv, mode), C / np.where(atopen, O, lv) - 1, 1, pos, have)
        for tau in ("q75", "q90"):
            lv = m[f"W_I6_H_{tau}"]
            out[f"R8_post_{tau}"] = pack(tt_sell(H, lv, mode), 1 - C / lv, 1, pos, have)
            lv = m[f"P_S6_H_{tau}"]
            atopen = O >= lv
            out[f"R8_pre_{tau}"] = pack(atopen | tt_sell(H, lv, mode), 1 - C / np.where(atopen, O, lv), 1, pos, have)
    # ---- hourly rules R3, R4 (sessions with 7 hourly bars)
    if S.hidx is not None and S.ho is not None:
        hp = S.hidx
        Ch = S.C[..., hp]
        o1, h1, l1, c1 = S.ho[..., 0], S.hh[..., 0], S.hl[..., 0], S.hc[..., 0]
        r1 = np.log(c1 / o1)
        sig1 = ewma_rms(r1, warm=40)
        z1 = r1 / sig1
        for z0 in (1.5, 1.0, 2.0):
            buy, sell = z1 <= -z0, z1 >= z0
            out[f"R3_z{z0}"] = pack(buy | sell, np.where(buy, Ch / c1 - 1, 1 - Ch / c1), 2, hp, np.isfinite(z1))
        buy, sell = z1 <= -1.5, z1 >= 1.5
        Hmax, Lmin = S.hh[..., 1:].max(-1), S.hl[..., 1:].min(-1)
        tb, ts = tt_sell(Hmax, o1, mode) & buy, tt_buy(Lmin, o1, mode) & sell
        g = np.where(buy, np.where(tb, o1 / c1 - 1, Ch / c1 - 1), np.where(ts, 1 - o1 / c1, 1 - Ch / c1))
        out["R3t_z1.5"] = pack(buy | sell, g, np.where(tb | ts, 1.0, 2.0), hp, np.isfinite(z1))
        # R4a stop entry at the opening range, bars 2..5 ; R4b market entry at a bar close beyond the range
        shp = Ch.shape
        done, ga, gb, doneb = np.zeros(shp, bool), np.zeros(shp), np.zeros(shp), np.zeros(shp, bool)
        for k in range(1, 5):
            lb, sb = tt_sell(S.hh[..., k], h1, mode), tt_buy(S.hl[..., k], l1, mode)
            el, es = np.maximum(h1, S.ho[..., k]), np.minimum(l1, S.ho[..., k])
            rl, rs_ = Ch / el - 1, 1 - Ch / es
            r = np.where(lb & sb, np.minimum(rl, rs_), np.where(lb, rl, rs_))
            new = ~done & (lb | sb)
            ga = np.where(new, r, ga); done |= new
            lc, sc = S.hc[..., k] > h1, S.hc[..., k] < l1
            r = np.where(lc, Ch / S.hc[..., k] - 1, 1 - Ch / S.hc[..., k])
            newb = ~doneb & (lc | sc)
            gb = np.where(newb, r, gb); doneb |= newb
        out["R4a"] = pack(done, ga, 2, hp, np.isfinite(sig1))
        out["R4b"] = pack(doneb, gb, 2, hp, np.isfinite(sig1))
    return out


POSTHOC_FAMILY_SIZE = 16          # M2 x3, M1 x3, M8_emp x2, M7_emp x2, M8_post x2, M7_post x2 (the last four are model-quantile mirrors), R4a_long, R4a_short -> see posthoc_variants


def posthoc_variants(S: Sess, mode: int = 0, model: pd.DataFrame | None = None, with_model: bool = True) -> dict:
    """POST-HOC variants, declared AFTER the pre-fixed results were seen (they are exploratory and are labelled so in the report).
    M1 / M2 / M7 / M8 = the mirror image of R1 / R2 / R7 / R8: trade WITH the breach of the level (stop-entry: buy when the high trades through
    the upper level, sell short when the low trades through the lower level; filled at the level, which is generous for a stop order; exit at the close;
    two marketable legs).  R4a_long / R4a_short = R4a split by the direction of the first breakout."""
    E = estimators(S)
    n, i0 = S.n, S.i0
    pos = np.arange(i0, n)
    sl = (Ellipsis, slice(i0, n))
    O, H, L, C = (a[sl] for a in (S.O, S.H, S.L, S.C))
    out = {}
    for k in (0.5, 1.0, 1.5):
        lv = O * np.exp(k * E["sigH"][sl])
        out[f"M2_k{k}"] = pack(tt_sell(H, lv, mode), C / lv - 1, 2, pos, np.isfinite(lv))
        lv = O * np.exp(-k * E["sigL"][sl])
        out[f"M1_k{k}"] = pack(tt_buy(L, lv, mode), 1 - C / lv, 2, pos, np.isfinite(lv))
    qL = roll_q(E["LO"], [0.25, 0.10])
    qH = roll_q(E["HO"], [0.75, 0.90])
    for j, tau in enumerate(("q75", "q90")):
        lv = O * np.exp(qH[j][sl])
        out[f"M8_emp_{tau}"] = pack(tt_sell(H, lv, mode), C / lv - 1, 2, pos, np.isfinite(lv))
    for j, tau in enumerate(("q25", "q10")):
        lv = O * np.exp(qL[j][sl])
        out[f"M7_emp_{tau}"] = pack(tt_buy(L, lv, mode), 1 - C / lv, 2, pos, np.isfinite(lv))
    if model is not None and with_model:
        m = {c: model[c].values[None, :][sl] for c in model.columns if c.startswith("W_I6_")}
        have = np.isfinite(m["W_I6_L_q25"])
        for tau in ("q75", "q90"):
            lv = m[f"W_I6_H_{tau}"]
            out[f"M8_post_{tau}"] = pack(tt_sell(H, lv, mode), C / lv - 1, 2, pos, have)
        for tau in ("q25", "q10"):
            lv = m[f"W_I6_L_{tau}"]
            out[f"M7_post_{tau}"] = pack(tt_buy(L, lv, mode), 1 - C / lv, 2, pos, have)
    if S.hidx is not None and S.ho is not None:
        hp = S.hidx
        Ch = S.C[..., hp]
        o1, h1, l1, c1 = S.ho[..., 0], S.hh[..., 0], S.hl[..., 0], S.hc[..., 0]
        sig1 = ewma_rms(np.log(c1 / o1), warm=40)
        shp = Ch.shape
        done, ga, dirn = np.zeros(shp, bool), np.zeros(shp), np.zeros(shp)
        for k in range(1, 5):
            lb, sb = tt_sell(S.hh[..., k], h1, mode), tt_buy(S.hl[..., k], l1, mode)
            el, es = np.maximum(h1, S.ho[..., k]), np.minimum(l1, S.ho[..., k])
            rl, rs_ = Ch / el - 1, 1 - Ch / es
            r = np.where(lb & sb, np.minimum(rl, rs_), np.where(lb, rl, rs_))
            dd = np.where(lb & sb, np.where(rl <= rs_, 1, -1), np.where(lb, 1, -1))
            new = ~done & (lb | sb)
            ga = np.where(new, r, ga)
            dirn = np.where(new, dd, dirn)
            done |= new
        ok = np.isfinite(sig1)
        out["R4a_long"] = pack(done & (dirn == 1), ga, 2, hp, ok)
        out["R4a_short"] = pack(done & (dirn == -1), ga, 2, hp, ok)
    return out


PRIMARY = {"R1": "R1_k1.0", "R2": "R2_k1.0", "R3": "R3_z1.5", "R4": "R4a", "R5": "R5_z1.0", "R6": "R6_long_s1_t2", "R7": "R7_post_q25", "R8": "R8_post_q75"}
HOURLY_VARIANTS = ("R3_z1.5", "R3_z1.0", "R3_z2.0", "R3t_z1.5", "R4a", "R4b")


def rule_of(name: str) -> str:
    return name.split("_")[0].rstrip("t") if name[:2] in ("R1", "R2", "R5", "R6", "R7", "R8") else name[:2]


# ----------------------------------------------------------------------------- statistics
def win_mask(dates: pd.DatetimeIndex, w: str) -> np.ndarray:
    d = dates.values
    return {"all": np.ones(len(d), bool), "dev": d < VAL0.to_datetime64(), "val": (d >= VAL0.to_datetime64()) & (d < FIN0.to_datetime64()),
            "final": d >= FIN0.to_datetime64(), "cas": d >= CAS0.to_datetime64(), "final_pre": (d >= FIN0.to_datetime64()) & (d < CAS0.to_datetime64())}[w]


def nw_t(x: np.ndarray, lag: int = 5):
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    v = M._nw_var(x, min(lag, n - 1))
    if v <= 0:
        return np.nan, np.nan
    return float(x.mean() / np.sqrt(v)), float(np.sqrt(v))


N_FAMILY = 31


def holm(p, m_total: int | None = N_FAMILY) -> np.ndarray:
    """Holm step-down; missing p-values count as 1; the family size is padded to `m_total` (31 variants) so that windows without some variants are not favoured."""
    p = np.where(np.isnan(np.asarray(p, float)), 1.0, np.asarray(p, float))
    m = max(len(p), m_total or len(p))
    adj = np.empty(len(p))
    run = 0.0
    for rank, i in enumerate(np.argsort(p)):
        run = max(run, min(1.0, (m - rank) * p[i]))
        adj[i] = run
    return adj


MIN_TRADES = 10


def summarize_one(name, rec, dates_all, window, mode, label=None) -> dict:
    """Real-data summary of one variant in one window (R = 1)."""
    pos = rec["pos"]
    dts = dates_all[pos]
    wm = win_mask(dts, window)
    f = rec["fill"][0] & wm
    g = rec["gross"][0][f]
    lg = rec["legs"][0][f]
    nsess = int((wm & rec["elig"][0]).sum())
    # sessions with a valid (non-nan) scale count as eligible; hourly rules: sig1h needs a burn-in, counted via finite gross/fill only
    row = {"variant": name, "rule": rule_of(name), "fill_mode": mode, "window": window, "n_sessions": nsess, "n_trades": int(f.sum()),
           "fill_rate": float(f.sum() / nsess) if nsess else np.nan}
    if f.sum() == 0:
        return row
    net = g - COST
    net1 = g - COST - SLIP * lg
    row.update({"mean_gross_pct": 100 * g.mean(), "mean_net_pct": 100 * net.mean(), "mean_net_rs": net.mean() * RS, "mean_net_s1_pct": 100 * net1.mean(),
                "median_net_pct": 100 * np.median(net), "sd_net_pct": 100 * net.std(ddof=1) if len(net) > 1 else np.nan, "win_rate": float((net > 0).mean()),
                "sum_net_pct": 100 * net.sum(), "net_pct_per_100_sessions": 100 * net.sum() / nsess * 100 if nsess else np.nan})
    if len(net) >= MIN_TRADES:
        for tag, x in (("net", net), ("gross", g)):
            t_iid = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
            t_h, se_h = nw_t(x)
            row[f"t_iid_{tag}"] = float(t_iid)
            row[f"p_iid_{tag}"] = float(stats.t.sf(t_iid, len(x) - 1))
            row[f"t_hac_{tag}"] = t_h
            row[f"p_hac_{tag}"] = float(stats.t.sf(t_h, len(x) - 1)) if np.isfinite(t_h) else np.nan
            if tag == "net":
                row["se_hac_pct"] = 100 * se_h if np.isfinite(se_h) else np.nan
                row["mde_80pct_power_pct"] = 100 * 2.49 * se_h if np.isfinite(se_h) else np.nan
    return row


# ----------------------------------------------------------------------------- part 2 on the real data
def part2(S: Sess, d: pd.DataFrame, model, outdir: Path, hpath: str):
    rows, trades = [], []
    allrec = {}
    for mode in (0, 1, 2):
        rec = run_variants(S, mode, model)
        allrec[mode] = rec
        for name, r in rec.items():
            for w in WINDOWS:
                if name in HOURLY_VARIANTS and w == "dev":
                    continue
                rows.append(summarize_one(name, r, S.dates, w, mode))
    R = pd.DataFrame(rows)
    R.to_csv(outdir / "hl_trade_rules.csv", index=False)
    # trade list (F0)
    for name, r in allrec[0].items():
        f = r["fill"][0]
        dts = S.dates[r["pos"]][f]
        g = r["gross"][0][f]
        lg = r["legs"][0][f]
        trades.append(pd.DataFrame({"variant": name, "date": dts.strftime("%Y-%m-%d"), "gross_pct": 100 * g, "net_pct": 100 * (g - COST), "net_s1_pct": 100 * (g - COST - SLIP * lg), "legs": lg}))
    pd.concat(trades).to_csv(outdir / "hl_trade_trades.csv", index=False, float_format="%.5f")
    return allrec, R


def by_year(S, rec, outdir):
    rows = []
    for name in PRIMARY.values():
        r = rec[name]
        dts = S.dates[r["pos"]]
        for y in sorted(set(dts.year)):
            wm = dts.year == y
            f = r["fill"][0] & wm
            g = r["gross"][0][f]
            if wm.sum() == 0:
                continue
            row = {"variant": name, "year": y, "n_sessions": int(wm.sum()), "n_trades": int(f.sum()), "fill_rate": float(f.sum() / wm.sum())}
            if f.sum():
                net = g - COST
                row.update({"mean_gross_pct": 100 * g.mean(), "mean_net_pct": 100 * net.mean(), "win_rate": float((net > 0).mean())})
            rows.append(row)
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_byyear.csv", index=False)


def baseline_longs(S, outdir):
    """Reference rows (not rules): buy at the official open and sell at the official close every session; mean intraday drift of the stock."""
    O, C = S.O[0], S.C[0]
    r = C / O - 1
    rows = []
    for w in WINDOWS:
        wm = win_mask(S.dates, w) & (np.arange(S.n) >= S.i0)
        x = r[wm]
        rows.append({"reference": "buy every open, sell every close (gross)", "window": w, "n": int(wm.sum()), "mean_pct": 100 * x.mean(), "sd_pct": 100 * x.std(ddof=1), "t_hac": nw_t(x)[0],
                     "mean_gap_pct": 100 * (np.log(S.O[0] / S.P0[0])[wm]).mean(), "mean_close_to_close_pct": 100 * (S.C[0] / S.P0[0] - 1)[wm].mean()})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_reference_drift.csv", index=False)
    return pd.DataFrame(rows)


def dm_and_kupiec(S, rec0, outdir):
    """Model-level vs EMP250-level (post-open), calendar P&L; Kupiec of the fill frequency of the model limit orders vs their nominal rate."""
    rows = []
    n = S.n
    def cal(name):
        r = rec0[name]
        pnl = np.where(r["fill"][0], r["gross"][0] - COST, 0.0)
        s = pd.Series(pnl, index=S.dates[r["pos"]])
        return s
    pairs = [("R7_post_q25", "R7_emp_q25"), ("R7_post_q10", "R7_emp_q10"), ("R8_post_q75", "R8_emp_q75"), ("R8_post_q90", "R8_emp_q90")]
    for a, b in pairs:
        sa, sb = cal(a), cal(b)
        idx = sa.index.intersection(sb.index)
        idx = idx[idx >= MODEL0]
        sa, sb = sa.loc[idx], sb.loc[idx]
        for w in ("all", "val", "final", "cas"):
            wm = win_mask(idx, w)
            if w == "all":
                wm = np.ones(len(idx), bool)
            if wm.sum() < 20:
                continue
            la, lb = -sa.values[wm], -sb.values[wm]
            md, t, p = M.diebold_mariano(la, lb, lag=5)
            rows.append({"model_variant": a, "benchmark": b, "window": w, "n": int(wm.sum()), "mean_daily_net_pnl_model_pct": 100 * sa.values[wm].mean(), "mean_daily_net_pnl_bench_pct": 100 * sb.values[wm].mean(),
                         "dm_mean_diff_pct": 100 * md, "dm_t": t, "p_one_sided_model_better": p, "p_two_sided": 2 * min(p, 1 - p) if np.isfinite(p) else np.nan})
    D = pd.DataFrame(rows)
    pm = D.copy()
    for w, g in D.groupby("window"):
        D.loc[g.index, "holm_one_sided_over_pairs"] = holm(g["p_one_sided_model_better"].values)
    # added after the first run (two-sided, "model differs from benchmark"), Holm over all pairs x windows in the table
    D["holm_two_sided_over_all_rows"] = holm(D["p_two_sided"].values, m_total=len(D))
    D.to_csv(outdir / "hl_trade_dm.csv", index=False)
    # Kupiec fill frequency
    nominal = {"q25": 0.25, "q10": 0.10, "q75": 0.25, "q90": 0.10}
    kr = []
    for name in [k for k in rec0 if k.startswith(("R7_post", "R7_pre", "R8_post", "R8_pre", "R7_emp", "R8_emp"))]:
        r = rec0[name]
        dts = S.dates[r["pos"]]
        for w in ("all", "dev", "val", "final", "cas"):
            wm = win_mask(dts, w) & (dts >= MODEL0)
            if wm.sum() < 20:
                continue
            hit = r["fill"][0][wm].astype(int)
            nom = nominal[name.split("_")[-1]]
            kr.append({"variant": name, "window": w, "n": int(wm.sum()), "nominal_fill": nom, "observed_fill": float(hit.mean()), "kupiec_p": M.kupiec(hit, nom)})
    pd.DataFrame(kr).to_csv(outdir / "hl_trade_kupiec_fill.csv", index=False)
    return D, pd.DataFrame(kr)


# ----------------------------------------------------------------------------- part 1
def regime_labels(sigR: np.ndarray, start: int = 100, window: int | None = None):
    """Terciles of sigR with cut points from sessions before t only: expanding (pre-fixed definition) or trailing `window` sessions (POST-HOC variant).
    Returns labels [n] 0/1/2 (-1 = unclassified) and the cut points."""
    n = len(sigR)
    lab = np.full(n, -1)
    c1, c2 = np.full(n, np.nan), np.full(n, np.nan)
    for t in range(start, n):
        past = sigR[:t] if window is None else sigR[max(0, t - window):t]
        past = past[np.isfinite(past)]
        if len(past) < 60 or not np.isfinite(sigR[t]):
            continue
        a, b = np.quantile(past, [1 / 3, 2 / 3])
        c1[t], c2[t] = a, b
        lab[t] = 0 if sigR[t] <= a else (1 if sigR[t] <= b else 2)
    return lab, c1, c2


QS = (0.10, 0.25, 0.50, 0.75, 0.90, 0.95)


def exc_rows(entry, window, up, down, n_label=None):
    rows = []
    for side, x in (("up", up), ("down", down)):
        x = x[np.isfinite(x)]
        if len(x) == 0:
            continue
        r = {"entry": entry, "window": window, "excursion": side, "n": len(x), "mean_pct": 100 * x.mean()}
        for q in QS:
            r[f"q{int(q*100)}_pct"] = 100 * np.quantile(x, q)
        r["mean_rs"] = x.mean() * RS
        for q in QS:
            r[f"q{int(q*100)}_rs"] = np.quantile(x, q) * RS
        rows.append(r)
    return rows


def part1(S: Sess, d: pd.DataFrame, outdir: Path):
    E = estimators(S)
    O, H, L, C = (a[0] for a in (S.O, S.H, S.L, S.C))
    n, i0 = S.n, S.i0
    up, down = H / O - 1, 1 - L / O
    lab_e, c1e, c2e = regime_labels(E["sigR"][0])
    lab_t, c1t, c2t = regime_labels(E["sigR"][0], window=500)
    REG = (("expanding", lab_e), ("trailing500_posthoc", lab_t))
    res = {}
    # ---- 1. excursions from the open
    rows = []
    for w in WINDOWS:
        wm = win_mask(S.dates, w) & (np.arange(n) >= i0)
        rows += exc_rows("open", w, up[wm], down[wm])
        for rname, lab in REG:
            for gi, gname in enumerate(("low", "mid", "high")):
                rr = exc_rows(f"open|regime={gname}|{rname}", w, up[wm & (lab == gi)], down[wm & (lab == gi)])
                rows += rr
    # ---- excursions from each hourly entry
    hp = S.hidx
    hh, hl, hc, ho = S.hh[0], S.hl[0], S.hc[0], S.ho[0]
    hdates = S.dates[hp]
    for k in range(0, 6):                                  # entry at the close of bar k+1 (10:15 ... 15:15)
        ent = hc[:, k]
        u = np.maximum(hh[:, k + 1:].max(1) / ent - 1, 0)
        dn = np.maximum(1 - hl[:, k + 1:].min(1) / ent, 0)
        label = f"{HOURS[k+1]}"
        for w in ("all", "val", "final", "cas"):
            wm = win_mask(hdates, w)
            rows += exc_rows(label, w, u[wm], dn[wm])
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_excursions.csv", index=False)
    # ---- 2. stop / target touch (daily bounds) by regime
    rows = []
    grid = (0.005, 0.01, 0.015, 0.02)
    for w, (rname, lab) in [(w_, r_) for w_ in WINDOWS for r_ in REG]:
        wm0 = win_mask(S.dates, w) & (np.arange(n) >= i0)
        for gname, gi in (("all", None), ("low", 0), ("mid", 1), ("high", 2)):
            if gname == "all" and rname != "expanding":
                continue
            wm = wm0 & ((lab >= 0) if gi is None else (lab == gi))
            if gname == "all":
                wm = wm0
            nn = int(wm.sum())
            for side in ("long", "short"):
                for x in grid:
                    for y in grid:
                        if side == "long":
                            st, tg = (down[wm] >= x - 1e-12), (up[wm] >= y - 1e-12)
                        else:
                            st, tg = (up[wm] >= x - 1e-12), (down[wm] >= y - 1e-12)
                        if nn == 0:
                            continue
                        S_only, T_only, both, neither = (st & ~tg).mean(), (tg & ~st).mean(), (st & tg).mean(), (~st & ~tg).mean()
                        rows.append({"window": w, "regime_def": rname, "regime": gname, "side": side, "stop_pct": 100 * x, "target_pct": 100 * y, "n": nn, "stop_touched": st.mean() if nn else np.nan, "target_touched": tg.mean() if nn else np.nan,
                                     "stop_only": S_only, "target_only": T_only, "both": both, "neither": neither,
                                     "p_stop_first_lo": S_only, "p_stop_first_hi": S_only + both, "p_target_first_lo": T_only, "p_target_first_hi": T_only + both})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_stop_target_daily.csv", index=False)
    # ---- 2b. hourly-resolved first touch (long and short) by regime, entry at the open
    rows = []
    for w, (rname, lab) in [(w_, r_) for w_ in ("all", "val", "final", "cas") for r_ in REG]:
        reg_h = lab[hp]
        wm0 = win_mask(hdates, w)
        for gname, gi in (("all", None), ("low", 0), ("mid", 1), ("high", 2)):
            if gname == "all" and rname != "expanding":
                continue
            wm = wm0 & ((reg_h >= 0) if gi is None else (reg_h == gi))
            if gname == "all":
                wm = wm0
            Oh = S.O[0][hp]
            for side in ("long", "short"):
                for x in grid:
                    for y in grid:
                        if side == "long":
                            sb = np.where((hl <= (Oh * (1 - x))[:, None] + 1e-9).any(1), (hl <= (Oh * (1 - x))[:, None] + 1e-9).argmax(1), 99)
                            tb = np.where((hh >= (Oh * (1 + y))[:, None] - 1e-9).any(1), (hh >= (Oh * (1 + y))[:, None] - 1e-9).argmax(1), 99)
                        else:
                            sb = np.where((hh >= (Oh * (1 + x))[:, None] - 1e-9).any(1), (hh >= (Oh * (1 + x))[:, None] - 1e-9).argmax(1), 99)
                            tb = np.where((hl <= (Oh * (1 - y))[:, None] + 1e-9).any(1), (hl <= (Oh * (1 - y))[:, None] + 1e-9).argmax(1), 99)
                        sb, tb = sb[wm], tb[wm]
                        nn = int(wm.sum())
                        if nn == 0:
                            continue
                        stop_first = ((sb < tb) & (sb < 99)).mean()
                        tgt_first = ((tb < sb) & (tb < 99)).mean()
                        same = ((sb == tb) & (sb < 99)).mean()
                        neither = ((sb == 99) & (tb == 99)).mean()
                        rows.append({"window": w, "regime_def": rname, "regime": gname, "side": side, "stop_pct": 100 * x, "target_pct": 100 * y, "n": nn, "stop_first": stop_first, "target_first": tgt_first, "same_bar_unknown_order": same, "neither": neither})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_stop_target_hourly.csv", index=False)
    # ---- 3a. open is the high / low (daily)
    rows = []
    for w in WINDOWS:
        wm = win_mask(S.dates, w) & (np.arange(n) >= i0)
        oh, ol = (np.abs(H - O) < 1e-6)[wm], (np.abs(L - O) < 1e-6)[wm]
        rows.append({"source": "daily official", "window": w, "n": int(wm.sum()), "open_is_high": oh.mean(), "open_is_low": ol.mean(), "open_is_high_or_low": (oh | ol).mean(),
                     "k_open_high": int(oh.sum()), "k_open_low": int(ol.sum())})
    # ---- 3b. first / last hour (hourly)
    hi_bar = np.where(hh.max(1)[:, None] - hh <= 1e-9, 1, 0).argmax(1)          # first bar attaining the max (ties -> first)
    lo_bar = np.where(hl - hl.min(1)[:, None] <= 1e-9, 1, 0).argmax(1)
    tie_hi = ((hh.max(1)[:, None] - hh <= 1e-9).sum(1) > 1)
    tie_lo = ((hl - hl.min(1)[:, None] <= 1e-9).sum(1) > 1)
    for w in ("all", "val", "final", "cas"):
        wm = win_mask(hdates, w)
        h1_, l1_ = (hi_bar == 0)[wm], (lo_bar == 0)[wm]
        rows.append({"source": "hourly bars", "window": w, "n": int(wm.sum()), "high_in_first_hour": h1_.mean(), "low_in_first_hour": l1_.mean(), "high_or_low_in_first_hour": (h1_ | l1_).mean(),
                     "high_and_low_in_first_hour": (h1_ & l1_).mean(), "high_in_last_bar": (hi_bar == 6)[wm].mean(), "low_in_last_bar": (lo_bar == 6)[wm].mean(),
                     "high_or_low_in_last_bar": ((hi_bar == 6) | (lo_bar == 6))[wm].mean(), "k_high_or_low_first_hour": int((h1_ | l1_).sum()), "sessions_with_tied_extreme": int((tie_hi | tie_lo)[wm].sum())})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_open_hl_real.csv", index=False)
    # hourly distribution of the high / low bar
    rows = []
    for w in ("all", "final", "cas"):
        wm = win_mask(hdates, w)
        for b in range(7):
            rows.append({"window": w, "n": int(wm.sum()), "bar_start": HOURS[b], "share_high_in_bar": (hi_bar == b)[wm].mean(), "share_low_in_bar": (lo_bar == b)[wm].mean()})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_extreme_bar.csv", index=False)
    # ---- 4. range already formed by each hour
    rows = []
    runh = np.maximum.accumulate(hh, axis=1)
    runl = np.minimum.accumulate(hl, axis=1)
    fh, fl = hh.max(1), hl.min(1)
    for w in ("all", "final", "cas"):
        wm = win_mask(hdates, w)
        for k in range(6):
            rows.append({"window": w, "n": int(wm.sum()), "at_end_of_bar_starting": HOURS[k], "clock": f"{(555 + 60*(k+1))//60:02d}:{(555 + 60*(k+1))%60:02d}",
                         "high_already_final": (np.abs(runh[:, k] - fh) < 1e-9)[wm].mean(), "low_already_final": (np.abs(runl[:, k] - fl) < 1e-9)[wm].mean(),
                         "both_already_final": ((np.abs(runh[:, k] - fh) < 1e-9) & (np.abs(runl[:, k] - fl) < 1e-9))[wm].mean(),
                         "median_share_of_range_formed": float(np.median(((runh[:, k] - runl[:, k]) / (fh - fl))[wm])), "mean_share_of_range_formed": float(np.mean(((runh[:, k] - runl[:, k]) / (fh - fl))[wm]))})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_range_formed.csv", index=False)
    # ---- 5. stop calibration (trailing 250 empirical quantile of the adverse excursion, from the open)
    rows = []
    for side, adv in (("long", down), ("short", up)):
        qq = roll_q(adv[None, :], [0.5, 0.75, 0.9])
        for j, q in enumerate((0.5, 0.75, 0.9)):
            dist = qq[j][0]
            for w in WINDOWS:
                wm = win_mask(S.dates, w) & (np.arange(n) >= i0) & np.isfinite(dist)
                touched = (adv >= dist - 1e-12)[wm]
                hit = (~touched).astype(int)                      # "stop not touched" is the coverage event with nominal probability q
                rows.append({"side": side, "stop_quantile": q, "window": w, "n": int(wm.sum()), "nominal_stop_touched": 1 - q, "observed_stop_touched": float(touched.mean()),
                             "kupiec_p": M.kupiec(hit, q), "mean_stop_distance_pct": 100 * dist[wm].mean(), "mean_stop_distance_rs": dist[wm].mean() * RS})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_stop_calibration.csv", index=False)
    # ---- today's regime
    sigR_next = float(np.sqrt(LAM * E["sigR"][0][-1] ** 2 + (1 - LAM) * np.log(C[-1] / S.P0[0][-1]) ** 2))   # sigma for 16 Oct (through the 15 Oct return)
    sr = E["sigR"][0]
    past_e = sr[np.isfinite(sr)]
    past_t = sr[-500:][np.isfinite(sr[-500:])]
    for rname, past in (("expanding", past_e), ("trailing500", past_t)):
        a, b = np.quantile(past, [1 / 3, 2 / 3])
        reg_now = "low" if sigR_next <= a else ("mid" if sigR_next <= b else "high")
        res.update({f"cut_low_mid_pct_{rname}": 100 * a, f"cut_mid_high_pct_{rname}": 100 * b, f"regime_for_16oct_{rname}": reg_now})
    res.update({"sigR_for_16oct_pct": 100 * sigR_next, "sigma_R_last_used_pct": 100 * float(sr[-1]),
                "share_sessions_by_regime_expanding_all": {k: float((lab_e[S.i0:] == i).mean()) for i, k in enumerate(("low", "mid", "high"))},
                "share_sessions_by_regime_trailing500_all": {k: float((lab_t[S.i0:] == i).mean()) for i, k in enumerate(("low", "mid", "high"))},
                "n_by_regime_final_expanding": {k: int(((lab_e == i) & win_mask(S.dates, "final")).sum()) for i, k in enumerate(("low", "mid", "high"))},
                "n_by_regime_final_trailing500": {k: int(((lab_t == i) & win_mask(S.dates, "final")).sum()) for i, k in enumerate(("low", "mid", "high"))}})
    return res, lab_e


# ----------------------------------------------------------------------------- data checks (Yahoo vs official)
def data_checks(S: Sess, d: pd.DataFrame, audit: dict, outdir: Path):
    hp = S.hidx
    hdates = S.dates[hp]
    rows = []
    O, H, L, C = (a[0][hp] for a in (S.O, S.H, S.L, S.C))
    yo, yh, yl, yc = S.ho[0][:, 0], S.hh[0].max(1), S.hl[0].min(1), S.hc[0][:, 6]
    def add(label, diff, mask):
        x = diff[mask]
        if len(x) == 0:
            return
        rows.append({"quantity": label, "n": int(len(x)), "mean_rs": x.mean(), "median_rs": np.median(x), "mean_abs_rs": np.abs(x).mean(), "p90_abs_rs": np.quantile(np.abs(x), 0.9), "p99_abs_rs": np.quantile(np.abs(x), 0.99),
                     "max_abs_rs": np.abs(x).max(), "share_equal": float((np.abs(x) < 1e-6).mean()), "share_abs_gt_5": float((np.abs(x) > 5).mean()), "share_abs_gt_10": float((np.abs(x) > 10).mean())})
    for tag, m_ in (("all hourly sessions", np.ones(len(hdates), bool)), ("from 2025-07-01", hdates >= FIN0), ("closing-auction slice", hdates >= CAS0)):
        add(f"Yahoo hourly high minus NSE official high, {tag}", yh - H, m_)
        add(f"Yahoo hourly low minus NSE official low, {tag}", yl - L, m_)
        add(f"Yahoo first printed open minus NSE official open, {tag}", yo - O, m_)
        add(f"Yahoo last-bar close minus NSE official close, {tag}", yc - C, m_)
    # scale check of the x3 adjustment
    rows.append({"quantity": "ratio Yahoo day high x factor / NSE high, before 2025-05-23 (median)", "n": int((hdates < EX_DATE).sum()), "mean_rs": float(np.median((yh / H)[hdates < EX_DATE]))})
    rows.append({"quantity": "ratio Yahoo day high / NSE high, from 2025-05-23 (median)", "n": int((hdates >= EX_DATE).sum()), "mean_rs": float(np.median((yh / H)[hdates >= EX_DATE]))})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_data_checks.csv", index=False)
    return audit


def open_equals_prev(S: Sess, outdir: Path):
    """How often the official open equals the previous official close (closing-auction regime check), by window (daily bars, from 2019-01-01)."""
    rows = []
    O, P0 = S.O[0], S.P0[0]
    for w in WINDOWS + ("final_pre",):
        wm = win_mask(S.dates, w) & (np.arange(S.n) >= S.i0)
        eq = np.abs(O - P0) < 1e-6
        g = np.abs(np.log(O / P0))
        rows.append({"window": w, "n_sessions": int(wm.sum()), "open_equals_prev_close": int(eq[wm].sum()), "share": float(eq[wm].mean()), "median_abs_gap_pct": 100 * float(np.median(g[wm])), "mean_abs_gap_pct": 100 * float(g[wm].mean())})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_open_equals_prev.csv", index=False)


# ----------------------------------------------------------------------------- cross-check: Yahoo-consistent execution for the open rules
def crosscheck(S: Sess, E, outdir: Path):
    """R1, R2, R5, R6 primaries on the hourly sample with Yahoo's first printed open, Yahoo's own extremes and Yahoo's last printed price,
    next to the same sessions with official prices (same levels' scale estimators)."""
    hp = S.hidx
    rows = []
    Oy, Hy, Ly, Cy = S.ho[0][:, 0][None], S.hh[0].max(1)[None], S.hl[0].min(1)[None], S.hc[0][:, 6][None]
    Oo, Ho, Lo, Co = (a[:, hp] for a in (S.O, S.H, S.L, S.C))
    sigL, sigH, sigG = E["sigL"][:, hp], E["sigH"][:, hp], E["sigG"][:, hp]
    P0 = S.P0[:, hp]
    variants = {}
    for src, (O, H, L, C) in (("official", (Oo, Ho, Lo, Co)), ("yahoo", (Oy, Hy, Ly, Cy)), ("official open+Yahoo extremes+official close", (Oo, Hy, Ly, Co))):
        lv = O * np.exp(-1.0 * sigL)
        variants[("R1_k1.0", src)] = (tt_buy(L, lv, 0), C / lv - 1)
        lv = O * np.exp(1.0 * sigH)
        variants[("R2_k1.0", src)] = (tt_sell(H, lv, 0), 1 - C / lv)
        zG = np.log(O / P0) / sigG
        buy, sell = zG <= -1.0, zG >= 1.0
        variants[("R5_z1.0", src)] = (buy | sell, np.where(buy, C / O - 1, 1 - C / O))
        hit_stop, hit_tgt = L <= O * 0.99, H > O * 1.02
        g = np.where(hit_stop, -0.01, np.where(hit_tgt, 0.02, C / O - 1))
        variants[("R6_long_s1_t2", src)] = (np.ones_like(g, bool), g)
    hdates = S.dates[hp]
    for (name, src), (f, g) in variants.items():
        for w in ("all", "val", "final", "cas"):
            wm = win_mask(hdates, w) & np.isfinite(sigL[0])
            fm = f[0] & wm
            x = g[0][fm] - COST
            rows.append({"variant": name, "price_source": src, "window": w, "n_sessions": int(wm.sum()), "n_trades": int(fm.sum()), "mean_net_pct": 100 * x.mean() if len(x) else np.nan,
                         "mean_gross_pct": 100 * (x.mean() + COST) if len(x) else np.nan})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_crosscheck.csv", index=False)


def bracket_resolved(S, E, outdir):
    """R6 on the hourly sample: ordering resolved with hourly bars (same-bar conflicts scored stop-first), plus conservative / optimistic daily readings on the same sessions."""
    hp = S.hidx
    O = S.O[0][hp]; C = S.C[0][hp]; Hd, Ld = S.H[0][hp], S.L[0][hp]
    hh, hl = S.hh[0], S.hl[0]
    rows = []
    hdates = S.dates[hp]
    for side, s, t in (("long", 0.01, 0.02), ("long", 0.02, 0.01), ("short", 0.01, 0.02), ("short", 0.02, 0.01)):
        if side == "long":
            sb = np.where((hl <= (O * (1 - s))[:, None]).any(1), (hl <= (O * (1 - s))[:, None]).argmax(1), 99)
            tb = np.where((hh > (O * (1 + t))[:, None]).any(1), (hh > (O * (1 + t))[:, None]).argmax(1), 99)
            close_ret = C / O - 1
        else:
            sb = np.where((hh >= (O * (1 + s))[:, None]).any(1), (hh >= (O * (1 + s))[:, None]).argmax(1), 99)
            tb = np.where((hl < (O * (1 - t))[:, None]).any(1), (hl < (O * (1 - t))[:, None]).argmax(1), 99)
            close_ret = 1 - C / O
        stop_first = (sb < tb) | ((sb == tb) & (sb < 99))                      # same bar -> stop first
        tgt_first = (tb < sb)
        g_res = np.where(stop_first, -s, np.where(tgt_first, t, close_ret))
        g_cons = np.where(sb < 99, -s, np.where(tb < 99, t, close_ret))        # any stop touch -> stop (daily conservative)
        g_opt = np.where(tb < 99, t, np.where(sb < 99, -s, close_ret))         # any target touch -> target (daily optimistic)
        for w in ("all", "val", "final", "cas"):
            wm = win_mask(hdates, w)
            both = ((sb < 99) & (tb < 99))[wm]
            rows.append({"variant": f"R6_{side}_s{int(s*100)}_t{int(t*100)}", "window": w, "n": int(wm.sum()), "share_both_levels_touched": both.mean(), "share_both_same_bar": ((sb == tb) & (sb < 99))[wm].mean(),
                         "mean_net_pct_hourly_resolved": 100 * (g_res[wm] - COST).mean(), "mean_net_pct_conservative": 100 * (g_cons[wm] - COST).mean(), "mean_net_pct_optimistic": 100 * (g_opt[wm] - COST).mean()})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_bracket_order.csv", index=False)


# ----------------------------------------------------------------------------- placebo
class Ctx:
    pass


def build_ctx(S: Sess, E, clock: str = "mean_ratio") -> Ctx:
    c = Ctx()
    n = S.n
    c.n, c.dates, c.hidx, c.i0 = n, S.dates, S.hidx, S.i0
    sI, sG = E["sigI"][0].copy(), E["sigG"][0].copy()
    first = np.where(np.isfinite(sI))[0][0]
    sI[:first], sG[:first] = sI[first], sG[first]
    c.sigI, c.sigG = sI, sG
    zI, zG = (E["I"][0] / E["sigI"][0])[S.i0:], (E["G"][0] / E["sigG"][0])[S.i0:]
    c.v2, c.v2g = float(np.log(np.nanmean(zI ** 2))), float(np.log(np.nanmean(zG ** 2)))
    # hourly variance clock (session-normalised squared hourly returns; first bar from its own open)
    hc, ho = S.hc[0], S.ho[0]
    r = np.column_stack([np.log(hc[:, 0] / ho[:, 0])] + [np.log(hc[:, k] / hc[:, k - 1]) for k in range(1, 7)])
    sh = (r ** 2) / (r ** 2).sum(1, keepdims=True)
    # "mean_ratio" = the pre-fixed clock (mean of session-normalised shares; biased toward 1/7 by ratio noise); "pooled" = ratio of sums (post-hoc sensitivity)
    c.share = sh.mean(0) if clock == "mean_ratio" else (r ** 2).sum(0) / (r ** 2).sum()
    w = np.zeros(K5)
    for k in range(7):
        a = BAR_STEPS[k]
        b = BAR_STEPS[k + 1] if k < 6 else K5
        w[a:b] = c.share[k] / (b - a)
    c.w = w
    # drift per partition (setting B)
    mu_G, mu_I = np.zeros(n), np.zeros(n)
    for wname, wm in (("dev", win_mask(S.dates, "dev")), ("val", win_mask(S.dates, "val")), ("final_pre", win_mask(S.dates, "final_pre")), ("cas", win_mask(S.dates, "cas"))):
        m_ = wm & (np.arange(n) >= S.i0)
        mu_G[wm], mu_I[wm] = E["G"][0][m_].mean(), E["I"][0][m_].mean()
    c.muG, c.muI = mu_G, mu_I
    c.model_rows = None
    return c


def simulate(rng: np.random.Generator, R: int, c: Ctx, drift: bool):
    n = c.n
    sI = c.sigI[None, :] * np.exp(rng.normal(-0.5 * c.v2, np.sqrt(c.v2), size=(R, n)))
    sG = c.sigG[None, :] * np.exp(rng.normal(-0.5 * c.v2g, np.sqrt(c.v2g), size=(R, n)))
    g = sG * rng.standard_normal((R, n)) + (c.muG[None, :] if drift else 0.0)
    z = rng.standard_normal((R, n, K5))
    u1 = 1.0 - rng.random((R, n, K5))
    u2 = 1.0 - rng.random((R, n, K5))
    sd = sI[:, :, None] * np.sqrt(c.w)[None, None, :]
    inc = sd * z
    if drift:
        inc += (c.muI[None, :, None] / K5)
    b = np.cumsum(inc, axis=-1)
    a = b - inc
    del z
    mx = 0.5 * (a + b + np.sqrt(inc * inc - 2 * sd * sd * np.log(u1)))
    mn = 0.5 * (a + b - np.sqrt(inc * inc - 2 * sd * sd * np.log(u2)))
    del u1, u2
    I = b[..., -1]
    lnC = np.cumsum(g + I, axis=1)
    lnP0 = np.concatenate([np.zeros((R, 1)), lnC[:, :-1]], axis=1)
    lnO = lnP0 + g
    P0, O = np.exp(lnP0) * 1000.0, np.exp(lnO) * 1000.0
    Hh = O * np.exp(mx.max(-1))
    Ll = O * np.exp(mn.min(-1))
    Cc = O * np.exp(I)
    # hourly bars for the real hourly sessions
    hp = c.hidx
    idx = np.array(BAR_STEPS)
    bo = a[:, hp][..., idx]                                                              # bar open = path value at bar start
    bcl = b[:, hp][..., np.r_[idx[1:] - 1, K5 - 1]]
    bh = np.maximum.reduceat(mx[:, hp], idx, axis=-1)
    bl = np.minimum.reduceat(mn[:, hp], idx, axis=-1)
    Ob = O[:, hp][..., None]
    S = Sess(c.dates, O, Hh, Ll, Cc, P0, hp, Ob * np.exp(bo), Ob * np.exp(bh), Ob * np.exp(bl), Ob * np.exp(bcl))
    return S


def placebo_stats(S: Sess, rec: dict) -> dict:
    """Per variant and window: [R, 4] arrays (n_trades, sum_gross, sum_net, sum_net^2), plus fills; F0, cost 0.10%."""
    out = {}
    for name, r in rec.items():
        dts = S.dates[r["pos"]]
        fill, gross = r["fill"], np.nan_to_num(r["gross"])
        for w in WINDOWS:
            wm = win_mask(dts, w)
            f = fill[:, wm]
            gg = gross[:, wm]
            nn = f.sum(1)
            sg = (gg * f).sum(1)
            net = (gg - COST) * f
            out[(name, w)] = np.stack([nn, sg, net.sum(1), (net ** 2).sum(1), (r["elig"][:, wm]).sum(1)], axis=1)
    return out


def timing_stats(S: Sess) -> dict:
    """Open / first-hour structure in simulated histories (hourly sessions)."""
    hp = S.hidx
    hh, hl = S.hh, S.hl
    hdates = S.dates[hp]
    hi_bar = np.where(hh.max(-1, keepdims=True) - hh <= 1e-9, 1, 0).argmax(-1)
    lo_bar = np.where(hl - hl.min(-1, keepdims=True) <= 1e-9, 1, 0).argmax(-1)
    out = {}
    for w in ("all", "val", "final", "cas"):
        wm = win_mask(hdates, w)
        h1, l1 = (hi_bar == 0)[:, wm], (lo_bar == 0)[:, wm]
        out[("hl_first_hour", w)] = np.stack([h1.mean(1), l1.mean(1), (h1 | l1).mean(1), (h1 & l1).mean(1), (hi_bar == 6)[:, wm].mean(1)], axis=1)
        wd = win_mask(S.dates, w) & (np.arange(S.n) >= S.i0)
        oh = (np.abs(S.H - S.O) < 0.5 * TICK * S.O)[:, wd].mean(1)
        ol = (np.abs(S.L - S.O) < 0.5 * TICK * S.O)[:, wd].mean(1)
        out[("open_is_hl", w)] = np.stack([oh, ol], axis=1)
    return out


def _placebo_worker(args):
    seed_seq, R, c, drift, hp_ready = args
    rng = np.random.default_rng(seed_seq)
    S = simulate(rng, R, c, drift)
    rec = run_variants(S, 0, None, with_model=False)
    rec.update(posthoc_variants(S, 0, None, with_model=False))
    return placebo_stats(S, rec), timing_stats(S)


# placebo settings: A / B are the pre-fixed ones; P0 / P1 repeat them with the pooled (ratio-of-sums) variance clock (post-hoc sensitivity, see report)
SETTINGS = (("A", False, "mean_ratio"), ("B", True, "mean_ratio"), ("P0", False, "pooled"), ("P1", True, "pooled"))


def placebo(S: Sess, E, reps: int, procs: int, chunk: int, path: Path):
    from multiprocessing import Pool
    ctxs = {clk: build_ctx(S, E, clk) for clk in ("mean_ratio", "pooled")}
    c = ctxs["mean_ratio"]
    nchunk = int(np.ceil(reps / chunk))
    ss = np.random.SeedSequence(SEED).spawn(nchunk)
    res = {}
    t0 = time.time()
    for tag, drift, clk in SETTINGS:
        jobs = [(ss[i], min(chunk, reps - i * chunk), ctxs[clk], drift, True) for i in range(nchunk)]
        with Pool(procs) as pool:
            outs = pool.map(_placebo_worker, jobs)
        agg, tim = {}, {}
        for (st, tm) in outs:
            for k, v in st.items():
                agg.setdefault(k, []).append(v)
            for k, v in tm.items():
                tim.setdefault(k, []).append(v)
        for k, v in agg.items():
            res[f"stat|{tag}|{k[0]}|{k[1]}"] = np.concatenate(v, axis=0)
        for k, v in tim.items():
            res[f"timing|{tag}|{k[0]}|{k[1]}"] = np.concatenate(v, axis=0)
        print(f"placebo setting {tag} (drift={drift}, clock={clk}) done, {reps} histories, {time.time()-t0:.0f}s")
    res["meta"] = np.array([c.v2, c.v2g] + list(c.share))
    res["meta_pooled_clock"] = np.array(ctxs["pooled"].share)
    TMP.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **res)
    return res


# ----------------------------------------------------------------------------- self tests
def selftest(S: Sess, d: pd.DataFrame, model):
    """(1) EWMA equals the project's sigma_ewma; (2) changing one session's high/low/close leaves every earlier variant output bit-identical and the session's own
    level unchanged; later sessions change (positive control); (3) zero-drift placebo gross mean ~ 0 for fill-conditional limit rules and brackets."""
    import models as P
    res = []
    r = np.log(d.close / d.prev).values
    mx = np.nanmax(np.abs(ewma_rms(r[None])[0] - P.sigma_ewma(r)))
    res.append(("ewma_equals_project_S1", bool(mx < 1e-12), mx))
    base = run_variants(S, 0, model)
    t0 = S.i0 + 700
    O, H, L, C, P0 = (a.copy() for a in (S.O, S.H, S.L, S.C, S.P0))
    H[0, t0] *= 1.05; L[0, t0] *= 0.95; C[0, t0] = O[0, t0] * 1.01
    P0[0, t0 + 1] = C[0, t0]
    S2 = Sess(S.dates, O, H, L, C, P0, S.hidx, S.ho, S.hh, S.hl, S.hc)
    alt = run_variants(S2, 0, model)
    bad_before, changed_after, own_level_ok = 0, 0, True
    for k in base:
        if k in HOURLY_VARIANTS:
            continue
        pos = base[k]["pos"]
        a, b = base[k], alt[k]
        before = pos < t0
        for key in ("fill", "gross"):
            x, y = a[key][0][before], b[key][0][before]
            if not np.array_equal(np.nan_to_num(x), np.nan_to_num(y)):
                bad_before += 1
        after = pos > t0 + 1
        if not np.array_equal(np.nan_to_num(a["gross"][0][after]), np.nan_to_num(b["gross"][0][after])):
            changed_after += 1
    res.append(("earlier_sessions_bit_identical_when_session_t_changed", bad_before == 0, bad_before))
    res.append(("later_sessions_change_positive_control_(variants)", changed_after > 0, changed_after))
    # level of session t0 itself uses only data before t0 and the open
    E1, E2 = estimators(S), estimators(S2)
    res.append(("sigma_and_level_inputs_of_session_t_unchanged_by_its_own_HLC", bool(np.array_equal(E1["sigL"][0][: t0 + 1], E2["sigL"][0][: t0 + 1], equal_nan=True) and np.array_equal(E1["sigG"][0][: t0 + 1], E2["sigG"][0][: t0 + 1], equal_nan=True)), 0))
    # hourly rules (R3, R4): (a) changing bars 2..7 of hourly session m0 must leave every earlier session AND the R3 signal / fill of m0 itself unchanged (R3 uses bar 1 only);
    # (b) changing the first bar's close of m0 must leave earlier sessions bit-identical and (positive control) change at least one later R3 outcome.
    m0 = 250
    hb = run_variants(S, 0, None, with_model=False)
    hh2, hl2, hc2, ho2 = S.hh.copy(), S.hl.copy(), S.hc.copy(), S.ho.copy()
    hh2[0, m0, 1:] *= 1.04; hl2[0, m0, 1:] *= 0.96; hc2[0, m0, 1:] *= 1.02
    ha = run_variants(Sess(S.dates, S.O, S.H, S.L, S.C, S.P0, S.hidx, ho2, hh2, hl2, hc2), 0, None, with_model=False)
    bad_h, r3_same_all = 0, True
    for k in HOURLY_VARIANTS:
        for key in ("fill", "gross"):
            x, y = np.nan_to_num(hb[k][key][0]), np.nan_to_num(ha[k][key][0])
            if not np.array_equal(x[:m0], y[:m0]):
                bad_h += 1
        if k.startswith("R3") and not np.array_equal(hb[k]["fill"][0], ha[k]["fill"][0]):
            r3_same_all = False
    res.append(("hourly_rules_earlier_sessions_bit_identical_when_later_bars_of_session_m0_change", bad_h == 0, bad_h))
    res.append(("R3_fill_signal_depends_on_first_bar_only (bars 2-7 of session m0 and all later fills unchanged)", r3_same_all, 0))
    hh3, hl3, hc3, ho3 = S.hh.copy(), S.hl.copy(), S.hc.copy(), S.ho.copy()
    hc3[0, m0, 0] = ho3[0, m0, 0] * 1.03
    hh3[0, m0, 0] = np.maximum(hh3[0, m0, 0], hc3[0, m0, 0])
    hc_alt = run_variants(Sess(S.dates, S.O, S.H, S.L, S.C, S.P0, S.hidx, ho3, hh3, hl3, hc3), 0, None, with_model=False)
    bad_b, chg_later = 0, 0
    for k in HOURLY_VARIANTS:
        for key in ("fill", "gross"):
            x, y = np.nan_to_num(hb[k][key][0]), np.nan_to_num(hc_alt[k][key][0])
            if not np.array_equal(x[:m0], y[:m0]):
                bad_b += 1
            if not np.array_equal(x[m0 + 1:], y[m0 + 1:]):
                chg_later += 1
    res.append(("hourly_rules_earlier_sessions_bit_identical_when_first_bar_of_session_m0_changes", bad_b == 0, bad_b))
    res.append(("hourly_rules_later_sessions_change_positive_control", chg_later > 0, chg_later))
    # model-variant check: changing H/L/C does not change the stored level inputs (predictions come from a file; just check the file's P0 equals prev)
    if model is not None:
        m = model.dropna(subset=["P0"])
        diff = np.nanmax(np.abs(m["P0"].values - pd.Series(S.P0[0], index=S.dates).reindex(m.index).values) / m["P0"].values)
        res.append(("stored_model_P0_equals_daily_prev", bool(diff < 1e-9), float(diff)))
    # placebo sanity (zero log drift): the LOG gross return given a fill must have mean ~ 0 (optional stopping); simple returns carry a small convexity term
    # (+/- sigma^2/2: long positive, short negative), and the conservative bracket convention is biased by construction (reported, not asserted).
    c = build_ctx(S, estimators(S))
    rng = np.random.default_rng(1)
    Sim = simulate(rng, 24, c, False)
    rec = run_variants(Sim, 0, None, with_model=False)
    msgs = []
    for k in ("R1_k1.0", "R2_k1.0", "R5_z1.0", "R3_z1.5", "R4a", "R4b", "R7_emp_q25", "R8_emp_q75"):
        f, g = rec[k]["fill"], np.nan_to_num(rec[k]["gross"])
        if k.startswith(("R2", "R8")):                       # single-sided short: log return = -ln(1 - simple short return)
            lg = np.where(f, -np.log1p(-g), 0.0)
        elif k.startswith(("R1", "R7")):
            lg = np.where(f, np.log1p(g), 0.0)
        else:                                                # mixed long / short: simple mean (convexity terms cancel to first order)
            lg = np.where(f, g, 0.0)
        gm = lg.sum() / f.sum()
        se = np.sqrt(((lg - gm * f) ** 2).sum()) / f.sum()
        msgs.append((k, 100 * gm, 100 * se, int(f.sum()), 100 * (g * f).sum() / f.sum()))
    ok = all(abs(m_[1]) < 4 * m_[2] + 1e-9 for m_ in msgs)
    res.append(("placebo_zero_drift_LOG_gross_mean_within_4se_of_zero", ok, str([(m_[0], round(m_[1], 4), round(m_[2], 4), m_[3], round(m_[4], 4)) for m_ in msgs])))
    cons, opt = [], []
    for side in ("long", "short"):
        for optimistic in (False, True):
            f, g, lg_, both = bracket(Sim, None, side, 0.01, 0.02, 0, optimistic=optimistic)
            (opt if optimistic else cons).append(100 * g[:, Sim.i0:].mean())
    res.append(("bracket_conservative_vs_optimistic_straddle_zero (info)", bool(max(cons) < 0 < min(opt)), f"conservative {np.round(cons, 3).tolist()}, optimistic {np.round(opt, 3).tolist()} (% gross per session, long, short)"))
    # tick / bridge check: simulated daily range vs the real one (shape check, info)
    rho_real = np.log(S.H[0][S.i0:] / S.L[0][S.i0:])
    rho_sim = np.log(Sim.H[:, Sim.i0:] / Sim.L[:, Sim.i0:])
    res.append(("sim_vs_real_median_daily_range_pct (info)", True, f"real {100*np.median(rho_real):.2f} sim {100*np.median(rho_sim):.2f}; mean real {100*rho_real.mean():.2f} sim {100*rho_sim.mean():.2f}"))
    out = pd.DataFrame(res, columns=["check", "passed", "detail"])
    return out


# ----------------------------------------------------------------------------- finish: merge placebo with the real results
def finish(S: Sess, d: pd.DataFrame, model, outdir: Path, extra: dict):
    R = pd.read_csv(outdir / "hl_trade_rules.csv")
    path = TMP / "placebo.npz"
    P = np.load(path) if path.exists() else None
    rows = []
    for (mode, w), g in R.groupby(["fill_mode", "window"]):
        pass
    prim = set(PRIMARY.values())
    out_rows = []
    for w in WINDOWS:
        for mode in (0, 1, 2):
            sub = R[(R.window == w) & (R.fill_mode == mode)].copy()
            sub["p_hac_net_for_holm"] = sub["p_hac_net"]
            sub["holm_hac"] = holm(sub["p_hac_net"].values)
            # placebo p
            for tag in ("A", "B"):
                pp = np.full(len(sub), np.nan)
                null_mean, null_sd, null_q95, null_gross, null_n = (np.full(len(sub), np.nan) for _ in range(5))
                if P is not None and mode == 0:
                    for i, (idx, row) in enumerate(sub.iterrows()):
                        key = f"stat|{tag}|{row['variant']}|{w}"
                        if key not in P.files or not np.isfinite(row.get("mean_net_pct", np.nan)) or row["n_trades"] < MIN_TRADES:
                            continue
                        arr = P[key]
                        with np.errstate(invalid="ignore", divide="ignore"):
                            mean_net = arr[:, 2] / arr[:, 0]
                            mean_gross = arr[:, 1] / arr[:, 0]
                        valid = arr[:, 0] >= 1
                        mn = np.where(valid, mean_net, -np.inf)
                        obs = row["mean_net_pct"] / 100
                        pp[i] = (1 + np.sum(mn >= obs - 1e-15)) / (len(mn) + 1)
                        null_mean[i], null_sd[i] = np.nanmean(mean_net[valid]) * 100, np.nanstd(mean_net[valid], ddof=1) * 100
                        null_q95[i] = np.nanquantile(mean_net[valid], 0.95) * 100
                        null_gross[i] = np.nanmean(mean_gross[valid]) * 100
                        null_n[i] = np.mean(arr[:, 0])
                sub[f"p_placebo_{tag}"] = pp
                sub[f"holm_placebo_{tag}"] = holm(pp) if np.isfinite(pp).any() else np.nan
                sub[f"null_mean_net_pct_{tag}"] = null_mean
                sub[f"null_sd_net_pct_{tag}"] = null_sd
                sub[f"null_q95_net_pct_{tag}"] = null_q95
                sub[f"null_mean_gross_pct_{tag}"] = null_gross
                sub[f"null_mean_trades_{tag}"] = null_n
            out_rows.append(sub)
    H = pd.concat(out_rows)
    H.to_csv(outdir / "hl_trade_holm.csv", index=False)
    # verdicts for primaries
    V = []
    for rule, name in PRIMARY.items():
        def g(w, mode=0):
            s = H[(H.variant == name) & (H.window == w) & (H.fill_mode == mode)]
            return s.iloc[0] if len(s) else None
        fin, val, dev, cas, fin1 = g("final"), g("val"), g("dev"), g("cas"), g("final", 1)
        def pos(row, col="mean_net_pct"):
            return row is not None and row.get("n_trades", 0) >= MIN_TRADES and np.isfinite(row.get(col, np.nan)) and row[col] > 0
        has_dev = name not in HOURLY_VARIANTS
        is_model = name.startswith(("R7_post", "R7_pre", "R8_post", "R8_pre"))
        c_final = bool(fin is not None and fin["n_trades"] >= MIN_TRADES and pos(fin) and fin["holm_hac"] < 0.05)
        c_pl = bool(fin is not None and np.isfinite(fin.get("holm_placebo_A", np.nan)) and fin["holm_placebo_A"] < 0.05 and fin["holm_placebo_B"] < 0.05)
        c_val = pos(val) and (pos(dev) if has_dev else True)
        c_f1 = pos(fin1)
        c_cas = not (cas is not None and cas["n_trades"] >= MIN_TRADES and cas["mean_net_pct"] < 0 and cas.get("p_hac_net", 1) > 0.95)
        validated = c_final and c_pl and c_val and c_f1 and c_cas and not is_model
        descriptive = False
        for w in ("dev", "val", "final"):
            r_ = g(w)
            if r_ is not None and r_["n_trades"] >= MIN_TRADES and r_.get("mean_gross_pct", -1) > 0 and r_.get("p_hac_gross", 1) < 0.05:
                descriptive = True
        if pos(fin):
            descriptive = True
        verdict = "validated" if validated else ("descriptive" if descriptive else "not found")
        V.append({"rule": rule, "primary_variant": name, "verdict": verdict, "final_n_trades": None if fin is None else int(fin["n_trades"]),
                  "final_mean_gross_pct": None if fin is None else fin.get("mean_gross_pct"), "final_mean_net_pct": None if fin is None else fin.get("mean_net_pct"),
                  "final_holm_hac": None if fin is None else fin.get("holm_hac"), "final_holm_placebo_A": None if fin is None else fin.get("holm_placebo_A"), "final_holm_placebo_B": None if fin is None else fin.get("holm_placebo_B"),
                  "cond_final_net_pos_and_holm": c_final, "cond_placebo_both": c_pl, "cond_val_dev_net_pos": bool(c_val), "cond_F1_net_pos": bool(c_f1), "cond_cas_not_sig_neg": bool(c_cas), "model_variant_no_placebo": is_model})
    Vdf = pd.DataFrame(V)
    Vdf.to_csv(outdir / "hl_trade_verdicts.csv", index=False)
    # open / first-hour comparison with placebo
    if P is not None:
        rows = []
        real = pd.read_csv(outdir / "hl_trade_open_hl_real.csv")
        for tag in ("A", "B"):
            for w in ("all", "val", "final", "cas"):
                kh = f"timing|{tag}|hl_first_hour|{w}"
                ko = f"timing|{tag}|open_is_hl|{w}"
                a = P[kh]
                o = P[ko]
                r_ = real[(real.source == "hourly bars") & (real.window == w)].iloc[0]
                rd = real[(real.source == "daily official") & (real.window == w)].iloc[0]
                n_ = int(r_["n"])
                rows.append({"placebo_setting": tag, "window": w, "n_hourly_sessions": n_,
                             "obs_high_in_first_hour": r_["high_in_first_hour"], "sim_high_in_first_hour": a[:, 0].mean(), "obs_low_in_first_hour": r_["low_in_first_hour"], "sim_low_in_first_hour": a[:, 1].mean(),
                             "obs_high_or_low_first_hour": r_["high_or_low_in_first_hour"], "sim_high_or_low_first_hour": a[:, 2].mean(), "sim_5pct": np.quantile(a[:, 2], 0.05), "sim_95pct": np.quantile(a[:, 2], 0.95),
                             "p_two_sided_obs_vs_sim": float(min(1.0, 2 * min((a[:, 2] >= r_["high_or_low_in_first_hour"] - 1e-12).mean(), (a[:, 2] <= r_["high_or_low_in_first_hour"] + 1e-12).mean()))),
                             "obs_high_and_low_first_hour": r_["high_and_low_in_first_hour"], "sim_high_and_low_first_hour": a[:, 3].mean(), "obs_high_in_last_bar": r_["high_in_last_bar"], "sim_high_in_last_bar": a[:, 4].mean(),
                             "n_daily_sessions": int(rd["n"]), "obs_open_is_high": rd["open_is_high"], "sim_open_is_high": o[:, 0].mean(), "obs_open_is_low": rd["open_is_low"], "sim_open_is_low": o[:, 1].mean()})
        pd.DataFrame(rows).to_csv(outdir / "hl_trade_open_hl.csv", index=False)
    return H, Vdf


# ----------------------------------------------------------------------------- post-hoc report and clock sensitivity
PTAGS = ("A", "B", "P0", "P1")


def _placebo_cols(P, tag: str, variant: str, w: str, obs_net_pct: float, n_trades: int) -> dict:
    """Placebo p (share of simulated histories, plus one, with a net mean at least as large as the observed one) and null summaries; same logic as finish()."""
    nan = {"p": np.nan, "null_mean": np.nan, "null_sd": np.nan, "null_q95": np.nan, "null_gross": np.nan, "null_n": np.nan}
    key = f"stat|{tag}|{variant}|{w}"
    if P is None or key not in P.files or not np.isfinite(obs_net_pct) or n_trades < MIN_TRADES:
        return nan
    arr = P[key]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_net = arr[:, 2] / arr[:, 0]
        mean_gross = arr[:, 1] / arr[:, 0]
    valid = arr[:, 0] >= 1
    mn = np.where(valid, mean_net, -np.inf)
    obs = obs_net_pct / 100
    return {"p": (1 + np.sum(mn >= obs - 1e-15)) / (len(mn) + 1), "null_mean": np.nanmean(mean_net[valid]) * 100, "null_sd": np.nanstd(mean_net[valid], ddof=1) * 100,
            "null_q95": np.nanquantile(mean_net[valid], 0.95) * 100, "null_gross": np.nanmean(mean_gross[valid]) * 100, "null_n": float(np.mean(arr[:, 0]))}


def posthoc_report(S: Sess, d: pd.DataFrame, model, outdir: Path):
    """(1) The 16 post-hoc variants on the real data, all windows and fill conventions, Holm over the joint family (31 pre-fixed + 16 post-hoc = 47) and
    placebo p under A, B (pre-fixed placebo) and P0, P1 (pooled variance clock).  (2) The 31 pre-fixed variants under the four placebo settings."""
    path = TMP / "placebo.npz"
    P = np.load(path) if path.exists() else None
    R = pd.read_csv(outdir / "hl_trade_rules.csv")
    rows = []
    for mode in (0, 1, 2):
        rec = posthoc_variants(S, mode, model)
        for name, r in rec.items():
            for w in WINDOWS:
                if name.startswith("R4a_") and w == "dev":
                    continue
                rows.append(summarize_one(name, r, S.dates, w, mode))
    PH = pd.DataFrame(rows)
    fam = N_FAMILY + PH["variant"].nunique()
    PH["family_size_for_holm"] = fam
    PH["holm_hac_joint_family"] = np.nan
    for (mode, w), g in PH.groupby(["fill_mode", "window"]):
        pre = R[(R.fill_mode == mode) & (R.window == w)]
        adj = holm(np.concatenate([pre["p_hac_net"].values, g["p_hac_net"].values]), m_total=fam)
        PH.loc[g.index, "holm_hac_joint_family"] = adj[len(pre):]
    # placebo columns (fill convention F0 only)
    for tag in PTAGS:
        for col in ("p", "null_mean", "null_sd", "null_q95", "null_gross", "null_n"):
            PH[f"placebo_{col}_{tag}"] = np.nan
        PH[f"holm_placebo_joint_{tag}"] = np.nan
    pre_p = {}                                                               # placebo p of the 31 pre-fixed variants (needed for the joint Holm)
    SENS = []
    for w in WINDOWS:
        sub = R[(R.fill_mode == 0) & (R.window == w)].copy()
        sub["holm_hac"] = holm(sub["p_hac_net"].values)
        for tag in PTAGS:
            cols = [_placebo_cols(P, tag, r_["variant"], w, r_.get("mean_net_pct", np.nan), r_["n_trades"]) for _, r_ in sub.iterrows()]
            sub[f"p_placebo_{tag}"] = [c_["p"] for c_ in cols]
            sub[f"null_mean_net_pct_{tag}"] = [c_["null_mean"] for c_ in cols]
            sub[f"null_sd_net_pct_{tag}"] = [c_["null_sd"] for c_ in cols]
            sub[f"null_mean_trades_{tag}"] = [c_["null_n"] for c_ in cols]
            sub[f"holm_placebo_{tag}"] = holm(sub[f"p_placebo_{tag}"].values)
            pre_p[(w, tag)] = sub[f"p_placebo_{tag}"].values
            g = PH[(PH.fill_mode == 0) & (PH.window == w)]
            cc = [_placebo_cols(P, tag, r_["variant"], w, r_.get("mean_net_pct", np.nan), r_["n_trades"]) for _, r_ in g.iterrows()]
            for col in ("p", "null_mean", "null_sd", "null_q95", "null_gross", "null_n"):
                PH.loc[g.index, f"placebo_{col}_{tag}"] = [c_[col] for c_ in cc]
            adj = holm(np.concatenate([pre_p[(w, tag)], np.array([c_["p"] for c_ in cc])]), m_total=fam)
            PH.loc[g.index, f"holm_placebo_joint_{tag}"] = adj[len(sub):]
        SENS.append(sub[["variant", "rule", "window", "n_sessions", "n_trades", "fill_rate", "mean_gross_pct", "mean_net_pct", "sd_net_pct", "p_hac_net", "holm_hac"]
                        + [f"{a}_{t}" for t in PTAGS for a in ("p_placebo", "holm_placebo", "null_mean_net_pct", "null_sd_net_pct", "null_mean_trades")]])
    PH.to_csv(outdir / "hl_trade_posthoc.csv", index=False)
    pd.concat(SENS).to_csv(outdir / "hl_trade_sensitivity_clock.csv", index=False)
    # by-year view of the post-hoc variants (F0, 0.10% round trip)
    rec0 = posthoc_variants(S, 0, model)
    yrows = []
    for name, r in rec0.items():
        dts = S.dates[r["pos"]]
        for y in sorted(set(dts.year)):
            wm = dts.year == y
            f = r["fill"][0] & wm
            g = r["gross"][0][f]
            if wm.sum() == 0:
                continue
            row = {"variant": name, "year": y, "n_sessions": int((wm & r["elig"][0]).sum()), "n_trades": int(f.sum())}
            if f.sum():
                row.update({"mean_gross_pct": 100 * g.mean(), "mean_net_pct": 100 * (g - COST).mean(), "win_rate": float(((g - COST) > 0).mean())})
            yrows.append(row)
    pd.DataFrame(yrows).to_csv(outdir / "hl_trade_posthoc_byyear.csv", index=False)
    # timing statistics under the four placebo settings
    if P is not None:
        real = pd.read_csv(outdir / "hl_trade_open_hl_real.csv")
        rows = []
        for tag in PTAGS:
            for w in ("all", "val", "final", "cas"):
                a = P[f"timing|{tag}|hl_first_hour|{w}"]
                o = P[f"timing|{tag}|open_is_hl|{w}"]
                r_ = real[(real.source == "hourly bars") & (real.window == w)].iloc[0]
                x = r_["high_or_low_in_first_hour"]
                rows.append({"placebo_setting": tag, "window": w, "n_hourly_sessions": int(r_["n"]), "obs_high_or_low_first_hour": x, "sim_mean": a[:, 2].mean(), "sim_5pct": np.quantile(a[:, 2], 0.05),
                             "sim_95pct": np.quantile(a[:, 2], 0.95), "p_two_sided": float(min(1.0, 2 * min((a[:, 2] >= x - 1e-12).mean(), (a[:, 2] <= x + 1e-12).mean()))),
                             "obs_high_and_low_first_hour": r_["high_and_low_in_first_hour"], "sim_high_and_low_first_hour": a[:, 3].mean(),
                             "obs_high_in_last_bar": r_["high_in_last_bar"], "sim_high_in_last_bar": a[:, 4].mean(), "sim_open_is_high": o[:, 0].mean(), "sim_open_is_low": o[:, 1].mean()})
        pd.DataFrame(rows).to_csv(outdir / "hl_trade_open_hl_clock.csv", index=False)
    return PH


# ----------------------------------------------------------------------------- the numbers for the next session (descriptive, uses data through 15 Oct 2026 only)
def today(S: Sess, d: pd.DataFrame, outdir: Path, summary: dict):
    E = estimators(S)
    n = S.n
    O, H, L, C = (a[0] for a in (S.O, S.H, S.L, S.C))
    last = n - 1
    nxt = {}
    for nm, x in (("sigR", "R"), ("sigG", "G"), ("sigI", "I"), ("sigL", "LO"), ("sigH", "HO")):
        nxt[nm] = float(np.sqrt(LAM * E[nm][0][last] ** 2 + (1 - LAM) * E[x][0][last] ** 2))
    ref = float(C[last])
    up, down = H / O - 1, 1 - L / O
    rows = []
    for label, sl in (("trailing 250 sessions to 15 Oct 2026", slice(n - 250, n)), ("Final window (2025-07-01 to 15 Oct 2026)", slice(int(np.searchsorted(S.dates.values, FIN0.to_datetime64())), n)),
                      ("since closing auction (2026-08-04 on)", slice(int(np.searchsorted(S.dates.values, CAS0.to_datetime64())), n))):
        for side, x in (("price falls below the open (adverse for a long)", down[sl]), ("price rises above the open (adverse for a short)", up[sl])):
            r = {"sample": label, "n_sessions": int(len(x)), "side": side}
            for q in (0.25, 0.5, 0.75, 0.9):
                r[f"q{int(q*100)}_pct"] = 100 * float(np.quantile(x, q))
                r[f"q{int(q*100)}_rs_at_{int(ref)}"] = float(np.quantile(x, q)) * ref
            r["mean_pct"], r["mean_rs"] = 100 * float(x.mean()), float(x.mean()) * ref
            rows.append(r)
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_today_2026-10-16.csv", index=False)
    out = {"data_through": str(S.dates[-1].date()), "reference_close_rs": ref, "next_session": "2026-10-16",
           "ewma_scales_for_16oct_pct": {k: 100 * v for k, v in nxt.items()},
           "ewma_scales_in_rupees_at_reference": {k: v * ref for k, v in nxt.items()},
           "R1_k1_level_offset_below_open": {"pct": 100 * (1 - np.exp(-nxt["sigL"])), "rs": ref * (1 - np.exp(-nxt["sigL"]))},
           "R2_k1_level_offset_above_open": {"pct": 100 * (np.exp(nxt["sigH"]) - 1), "rs": ref * (np.exp(nxt["sigH"]) - 1)},
           "regime_expanding_terciles": summary.get("regime_for_16oct_expanding"), "regime_trailing500_posthoc": summary.get("regime_for_16oct_trailing500"),
           "note": "descriptive; the open of 16 Oct is not known; all rupee figures are percent x the 15 Oct close"}
    (outdir / "hl_trade_today_2026-10-16.json").write_text(json.dumps(out, indent=1))
    return out


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "part1", "part2", "placebo", "finish", "posthoc", "today", "all"])
    ap.add_argument("--hourly", default=os.environ.get("HL_HOURLY", ""))
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=8)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    d = load_daily()
    S, audit = real_sess(d, a.hourly)
    model = load_model(S)
    E = estimators(S)
    cmds = ["selftest", "part1", "part2", "placebo", "finish", "posthoc", "today"] if a.cmd == "all" else [a.cmd]
    summary = json.loads((OUT / "hl_trade_summary.json").read_text()) if (OUT / "hl_trade_summary.json").exists() else {}
    for cmd in cmds:
        t0 = time.time()
        if cmd == "selftest":
            T = selftest(S, d, model)
            T.to_csv(OUT / "hl_trade_selftest.csv", index=False)
            print(T.to_string(index=False))
            summary["selftest_all_passed"] = bool(T.passed.all())
        elif cmd == "part1":
            audit = data_checks(S, d, audit, OUT)
            res, lab = part1(S, d, OUT)
            bracket_resolved(S, E, OUT)
            open_equals_prev(S, OUT)
            summary.update(res)
            summary["hourly_audit"] = audit
            print(json.dumps(res, indent=1))
        elif cmd == "part2":
            rec, R = part2(S, d, model, OUT, a.hourly)
            by_year(S, rec[0], OUT)
            baseline_longs(S, OUT)
            dm_and_kupiec(S, rec[0], OUT)
            crosscheck(S, E, OUT)
            summary["predictions_file_sha256"] = hashlib.sha256(PRED.read_bytes()).hexdigest()
            summary["hourly_file_sha256"] = hashlib.sha256(Path(a.hourly).read_bytes()).hexdigest()
            summary["hourly_file_note"] = "Yahoo chart API, symbol BSE.NS, range=2y, interval=60m, fetched 15 Oct 2026 (last bar 15:15 IST bar of 15 Oct); not stored in the repo"
            summary["daily_sessions"] = int(S.n)
            summary["hourly_sessions_used"] = int(len(S.hidx))
            print(R[(R.window == "final") & (R.fill_mode == 0)][["variant", "n_sessions", "n_trades", "fill_rate", "mean_gross_pct", "mean_net_pct", "p_hac_net"]].to_string(index=False))
        elif cmd == "placebo":
            placebo(S, E, a.reps, a.procs, a.chunk, TMP / "placebo.npz")
            summary["placebo_reps_per_setting"] = a.reps
        elif cmd == "finish":
            H, V = finish(S, d, model, OUT, summary)
            print(V.to_string(index=False))
        elif cmd == "posthoc":
            PH = posthoc_report(S, d, model, OUT)
            print(PH[(PH.fill_mode == 0) & (PH.window.isin(["final", "cas"]))][["variant", "window", "n_trades", "mean_gross_pct", "mean_net_pct", "p_hac_net", "holm_hac_joint_family", "placebo_p_A", "placebo_p_B", "placebo_p_P0", "placebo_p_P1"]].to_string(index=False))
        elif cmd == "today":
            print(json.dumps(today(S, d, OUT, summary), indent=1))
        print(f"[{cmd}] {time.time()-t0:.1f}s")
    (OUT / "hl_trade_summary.json").write_text(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
