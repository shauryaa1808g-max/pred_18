"""Specialist C: can the high / low estimates be traded?  (NSE:BSE)

Part 1 (descriptive): excursions, stop / target hit probabilities by volatility regime, how often the open / first hour holds the day's extremes.
Part 2 (inferential): eight pre-fixed rules (31 variants), walk-forward, costs, fill conventions, Holm, and a random-walk placebo.
The design is written in research/hl/C_tradeability.md section 0 BEFORE any result was computed.

Run from the repo root (python3; no network; reads data/processed/*.csv, results/hl_eval_predictions.csv, the hourly Yahoo json):
  python3 src/hl_trade_study.py selftest --hourly <h60_BSE.NS.json>
  python3 src/hl_trade_study.py part1  --hourly <h60_BSE.NS.json>
  python3 src/hl_trade_study.py part2  --hourly <h60_BSE.NS.json>
  python3 src/hl_trade_study.py placebo --hourly <h60_BSE.NS.json> --reps 2000 [--procs 4]
  python3 src/hl_trade_study.py finish --hourly <h60_BSE.NS.json>
  python3 src/hl_trade_study.py posthoc --hourly <h60_BSE.NS.json>   (post-hoc variants + pooled-clock placebo sensitivity; needs the placebo output)
  python3 src/hl_trade_study.py today --hourly <h60_BSE.NS.json>     (numbers for 16 Oct 2026)
  python3 src/hl_trade_study.py indepcheck --hourly <h60_BSE.NS.json>  (plain-loop re-computation of headline numbers, no use of the functions above)
  python3 src/hl_trade_study.py diag --hourly <h60_BSE.NS.json>        (how the placebo differs from the real data; tick-rounding sensitivity)
  python3 src/hl_trade_study.py report                                (writes the results sections of research/hl/C_tradeability.md from the result files only)
(`all` = selftest, part1, part2, placebo, finish, posthoc, today, indepcheck, diag, report.)  Temporary placebo output goes to $HL_TRADE_TMP (default /tmp/hl_trade).
Data cut-off: nothing dated after 15 Oct 2026 is read (sessions later than CUTOFF are dropped with a printed note).
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
CUTOFF = pd.Timestamp("2026-10-15")                    # last session whose data may be used (the study is run before the 16 Oct 2026 open)


# ----------------------------------------------------------------------------- loading
def load_daily() -> pd.DataFrame:
    """bse_daily.csv + bse_daily_extra.csv, no network (same table official_bars.load_bse_ext() returns after its download step)."""
    d = load_bse()
    e = pd.read_csv("data/processed/bse_daily_extra.csv", index_col=0, parse_dates=True)
    e = e[~e.index.isin(d.index)].reindex(columns=d.columns)
    d = pd.concat([d, e]).sort_index()
    if (d.index > CUTOFF).any():
        print(f"[cutoff] dropping {int((d.index > CUTOFF).sum())} daily session(s) dated after {CUTOFF.date()}")
        d = d[d.index <= CUTOFF]
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
    if (df.date > CUTOFF).any():
        print(f"[cutoff] dropping {int((df.date > CUTOFF).sum())} hourly bar(s) dated after {CUTOFF.date()}")
        df = df[df.date <= CUTOFF]
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
                     "mean_gap_pct": 100 * (np.log(S.O[0] / S.P0[0])[wm]).mean(), "mean_close_to_close_pct": 100 * (S.C[0] / S.P0[0] - 1)[wm].mean(),
                     "buy_and_hold_multiple_over_window": float(np.exp(np.log(S.C[0] / S.P0[0])[wm].sum()))})
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


def regime_labels_full(sigR: np.ndarray, i0: int):
    """POST-HOC descriptive definition: terciles of sigR over ALL sessions from 2019-01-01 (cut points use the whole sample, including the future of
    each session, so it is not a tradable classification; it is used only to describe how swings differ between calm and busy days)."""
    lab = np.full(len(sigR), -1)
    x = sigR[i0:]
    a, b = np.quantile(x[np.isfinite(x)], [1 / 3, 2 / 3])
    ok = np.isfinite(sigR)
    ok[:i0] = False
    lab[ok] = np.where(sigR[ok] <= a, 0, np.where(sigR[ok] <= b, 1, 2))
    return lab, float(a), float(b)


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
    lab_f, cfa, cfb = regime_labels_full(E["sigR"][0], i0)
    REG = (("expanding", lab_e), ("trailing500_posthoc", lab_t), ("fullsample_posthoc", lab_f))
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
                rows.append({"side": side, "stop_quantile": q, "window": w, "n": int(wm.sum()), "nominal_stop_touched": round(1 - q, 2), "observed_stop_touched": float(touched.mean()),
                             "kupiec_p": M.kupiec(hit, q), "mean_stop_distance_pct": 100 * dist[wm].mean(), "mean_stop_distance_rs": dist[wm].mean() * RS})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_stop_calibration.csv", index=False)
    # ---- today's regime
    sigR_next = float(np.sqrt(LAM * E["sigR"][0][-1] ** 2 + (1 - LAM) * np.log(C[-1] / S.P0[0][-1]) ** 2))   # sigma for 16 Oct (through the 15 Oct return)
    sr = E["sigR"][0]
    past_e = sr[np.isfinite(sr)]
    past_t = sr[-500:][np.isfinite(sr[-500:])]
    past_f = sr[i0:][np.isfinite(sr[i0:])]
    for rname, past in (("expanding", past_e), ("trailing500", past_t), ("fullsample", past_f)):
        a, b = np.quantile(past, [1 / 3, 2 / 3])
        reg_now = "low" if sigR_next <= a else ("mid" if sigR_next <= b else "high")
        res.update({f"cut_low_mid_pct_{rname}": 100 * a, f"cut_mid_high_pct_{rname}": 100 * b, f"regime_for_16oct_{rname}": reg_now})
    res.update({"sigR_for_16oct_pct": 100 * sigR_next, "sigma_R_last_used_pct": 100 * float(sr[-1]),
                "share_sessions_by_regime_expanding_all": {k: float((lab_e[S.i0:] == i).mean()) for i, k in enumerate(("low", "mid", "high"))},
                "share_sessions_by_regime_trailing500_all": {k: float((lab_t[S.i0:] == i).mean()) for i, k in enumerate(("low", "mid", "high"))},
                "n_by_regime_final_expanding": {k: int(((lab_e == i) & win_mask(S.dates, "final")).sum()) for i, k in enumerate(("low", "mid", "high"))},
                "n_by_regime_final_trailing500": {k: int(((lab_t == i) & win_mask(S.dates, "final")).sum()) for i, k in enumerate(("low", "mid", "high"))},
                "n_by_regime_final_fullsample": {k: int(((lab_f == i) & win_mask(S.dates, "final")).sum()) for i, k in enumerate(("low", "mid", "high"))},
                "n_by_regime_cas_fullsample": {k: int(((lab_f == i) & win_mask(S.dates, "cas")).sum()) for i, k in enumerate(("low", "mid", "high"))},
                "n_by_regime_all_fullsample": {k: int(((lab_f == i) & (np.arange(n) >= i0)).sum()) for i, k in enumerate(("low", "mid", "high"))}})
    return res, lab_e


def clock_table(S: Sess, outdir: Path):
    """The intraday variance clock used by the placebo: share of the day's squared hourly returns falling in each bar (hourly sample).
    'mean_ratio' = mean of session-normalised shares (pre-fixed placebo clock); 'pooled' = ratio of sums (post-hoc sensitivity)."""
    hc, ho = S.hc[0], S.ho[0]
    r = np.column_stack([np.log(hc[:, 0] / ho[:, 0])] + [np.log(hc[:, k] / hc[:, k - 1]) for k in range(1, 7)])
    sh = (r ** 2) / (r ** 2).sum(1, keepdims=True)
    pooled = (r ** 2).sum(0) / (r ** 2).sum()
    rows = [{"bar_start": HOURS[k], "bar_minutes": 60 if k < 6 else 15, "n_sessions": int(len(r)), "share_variance_mean_ratio_clock": float(sh.mean(0)[k]), "share_variance_pooled_clock": float(pooled[k])} for k in range(7)]
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_clock.csv", index=False)


def stop_forecast_eval(S: Sess, outdir: Path):
    """ADDED AFTER THE PRE-FIXED SECTION (not one of the 31 variants; descriptive): how well can the distance a stop must sit from the open be forecast?
    The adverse excursion a (long: ln(O/L), short: ln(H/O)) is forecast at q = 0.50 / 0.75 / 0.90 from sessions before t by
    T250 = trailing-250-session empirical quantile (the pre-fixed one of section 0.8 item 5), EXPANDING = empirical quantile of all earlier sessions (constant scale),
    EWMA_SCALED = (EWMA sigma of a, lambda 0.94, known at t-1) x (expanding empirical quantile of a / sigma).  Pinball loss (percent of price), touch frequency with Kupiec,
    Diebold-Mariano (lag 5, HLN) of each alternative against T250, Holm over the 12 comparisons (2 sides x 3 quantiles x 2 alternatives) per window."""
    E = estimators(S)
    n, i0 = S.n, S.i0
    rows = []
    for side in ("long", "short"):
        a = -E["LO"][0] if side == "long" else E["HO"][0]
        sig = E["sigL"][0] if side == "long" else E["sigH"][0]
        z = a / sig
        simple = (lambda f: 1 - np.exp(-f)) if side == "long" else (lambda f: np.exp(f) - 1)
        a_s = simple(a)
        for q in (0.5, 0.75, 0.9):
            T = roll_q(a[None, :], [q])[0][0]
            Ex, Sc = np.full(n, np.nan), np.full(n, np.nan)
            for tt in range(60, n):
                Ex[tt] = np.quantile(a[:tt], q)
                zz = z[:tt][np.isfinite(z[:tt])]
                if len(zz) >= 60 and np.isfinite(sig[tt]):
                    Sc[tt] = sig[tt] * np.quantile(zz, q)
            fcs = {"T250": T, "EXPANDING": Ex, "EWMA_SCALED": Sc}
            ok = np.isfinite(T) & np.isfinite(Ex) & np.isfinite(Sc) & (np.arange(n) >= i0)
            loss = {}
            for name, fc in fcs.items():
                u = a_s - simple(fc)
                loss[name] = np.where(u >= 0, q * u, (q - 1) * u)
            for w in WINDOWS:
                wm = ok & win_mask(S.dates, w)
                if wm.sum() < 20:
                    continue
                for name, fc in fcs.items():
                    touched = (a >= fc - 1e-12)[wm]
                    r = {"side": side, "stop_quantile": q, "method": name, "window": w, "n": int(wm.sum()), "nominal_touch": round(1 - q, 2), "touch_freq": float(touched.mean()),
                         "kupiec_p": M.kupiec((~touched).astype(int), q), "mean_pinball_pct_of_price": float(100 * loss[name][wm].mean()),
                         "mean_stop_distance_pct": float(100 * simple(fc)[wm].mean()), "mean_stop_distance_rs": float(simple(fc)[wm].mean() * RS)}
                    if name != "T250":
                        md, tstat, pone = M.diebold_mariano(loss[name][wm], loss["T250"][wm], lag=5)
                        r.update({"dm_mean_loss_gain_vs_T250_pct": float(100 * md), "dm_t_vs_T250": tstat, "dm_p_one_sided_better": pone,
                                  "dm_p_two_sided": float(2 * min(pone, 1 - pone)) if np.isfinite(pone) else np.nan})
                    rows.append(r)
    D = pd.DataFrame(rows)
    D["holm_one_sided_12"] = np.nan
    for w, g in D[D.method != "T250"].groupby("window"):
        D.loc[g.index, "holm_one_sided_12"] = holm(g["dm_p_one_sided_better"].values, m_total=12)
    D.to_csv(outdir / "hl_trade_stop_forecast.csv", index=False)
    return D


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
    # hourly rules R3 / R4: official close as exit (as in the study) against Yahoo's last printed price as exit (the closing-price sensitivity of section 0.5)
    C2 = S.C.copy()
    C2[0, hp] = S.hc[0][:, 6]
    S2 = Sess(S.dates, S.O, S.H, S.L, C2, S.P0, S.hidx, S.ho, S.hh, S.hl, S.hc)
    rec_o, rec_y = run_variants(S, 0, None, with_model=False), run_variants(S2, 0, None, with_model=False)
    for name in ("R3_z1.5", "R3_z1.0", "R3_z2.0", "R4a", "R4b"):
        for src, rec in (("hourly rule, exit at official close", rec_o), ("hourly rule, exit at Yahoo last printed price", rec_y)):
            for w in ("all", "val", "final", "cas"):
                sm = summarize_one(name, rec[name], S.dates, w, 0)
                rows.append({"variant": name, "price_source": src, "window": w, "n_sessions": sm["n_sessions"], "n_trades": sm["n_trades"],
                             "mean_net_pct": sm.get("mean_net_pct", np.nan), "mean_gross_pct": sm.get("mean_gross_pct", np.nan)})
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
    c.tick_round = False
    return c


def _tick_round(x):
    """Round prices to a grid of relative width TICK (Rs 0.10 at Rs 3,428) in log space; monotone, so high >= open, close >= low is preserved."""
    return np.exp(np.round(np.log(x) / TICK) * TICK)


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
    rd = _tick_round if getattr(c, "tick_round", False) else (lambda x: x)           # tick_round is a sensitivity option only (diag command); the pre-fixed placebo does not round
    S = Sess(c.dates, rd(O), rd(Hh), rd(Ll), rd(Cc), rd(P0), hp, rd(Ob * np.exp(bo)), rd(Ob * np.exp(bh)), rd(Ob * np.exp(bl)), rd(Ob * np.exp(bcl)))
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


def pooled_trade_sd(arr: np.ndarray) -> float:
    """Standard deviation (percent) of the net return of a single simulated trade, pooled over all simulated histories (arr columns: n, sum gross, sum net, sum net^2, eligible)."""
    n, s, ss = arr[:, 0].sum(), arr[:, 2].sum(), arr[:, 3].sum()
    return float(100 * np.sqrt(max(ss / n - (s / n) ** 2, 0.0))) if n > 0 else np.nan


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


# ----------------------------------------------------------------------------- typical miss of the stored model medians (context for the trade results)
def model_miss(S: Sess, model: pd.DataFrame | None, outdir: Path):
    """Typical miss of specialist A's stored median forecasts of the day's high and low, recomputed from the stored file and the official bars:
    mean / median of |ln(actual / forecast)| x Rs 3,428, signed bias, with the 'price stays' (previous close) and 'open stays' benchmarks.  Not a new model result."""
    if model is None:
        return
    rows = []
    H, L, O, P0 = S.H[0], S.L[0], S.O[0], S.P0[0]
    have = np.isfinite(model["W_I6_L_q25"].values)
    fc = {"pre-open model median (P_S6, known 22:00 the evening before)": {"H": model["P_S6_H_q50"].values, "L": model["P_S6_L_q50"].values},
          "post-open model median (W_I6, known 09:08)": {"H": model["W_I6_H_q50"].values, "L": model["W_I6_L_q50"].values},
          "benchmark 'price stays' (previous close)": {"H": P0, "L": P0},
          "benchmark 'open stays' (official open)": {"H": O, "L": O}}
    for w in ("all", "dev", "val", "final", "cas"):
        wm = win_mask(S.dates, w) & have
        for name, d_ in fc.items():
            for tgt, act in (("high", H), ("low", L)):
                f = d_["H" if tgt == "high" else "L"]
                e = np.log(act[wm] / f[wm])
                a = np.abs(e)
                rows.append({"window": w, "n": int(wm.sum()), "forecast": name, "target": tgt, "mean_abs_miss_rs": float(a.mean() * RS), "se_mean_abs_miss_rs": float(a.std(ddof=1) / np.sqrt(len(a)) * RS),
                             "median_abs_miss_rs": float(np.median(a) * RS), "p90_abs_miss_rs": float(np.quantile(a, 0.9) * RS), "mean_signed_miss_rs_actual_minus_forecast": float(e.mean() * RS),
                             "share_actual_above_forecast": float((e > 0).mean())})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_model_miss.csv", index=False)


# ----------------------------------------------------------------------------- how the placebo differs from the real data; tick-rounding sensitivity
def _day_metrics(X: Sess, w: str) -> dict:
    """Per-history values (arrays of length R) of daily-bar summaries in window w."""
    wm = win_mask(X.dates, w) & (np.arange(X.n) >= X.i0)
    up, dn = (X.H / X.O - 1)[..., wm], (1 - X.L / X.O)[..., wm]
    I = np.log(X.C / X.O)[..., wm]
    rg = np.log(X.H / X.L)[..., wm]
    h = 0.5 * TICK * X.O[..., wm]
    out = {"median_log_range_pct": 100 * np.median(rg, axis=-1), "mean_log_range_pct": 100 * rg.mean(-1),
           "sd_open_to_close_pct": 100 * I.std(-1), "mean_abs_open_to_close_pct": 100 * np.abs(I).mean(-1),
           "directional_efficiency_mean_abs_OC_over_range": (np.abs(I) / rg).mean(-1),
           "mean_high_above_open_pct": 100 * up.mean(-1), "mean_low_below_open_pct": 100 * dn.mean(-1),
           "share_high_ge_1pct_above_open": (up >= 0.01).mean(-1), "share_low_ge_1pct_below_open": (dn >= 0.01).mean(-1),
           "share_high_ge_2pct_above_open": (up >= 0.02).mean(-1), "share_low_ge_2pct_below_open": (dn >= 0.02).mean(-1),
           "share_both_low_ge_1pct_and_high_ge_2pct (long 1%/2% bracket both touched)": ((dn >= 0.01) & (up >= 0.02)).mean(-1),
           "share_both_high_ge_1pct_and_low_ge_2pct (short 1%/2% bracket both touched)": ((up >= 0.01) & (dn >= 0.02)).mean(-1),
           "share_open_is_high": (np.abs(X.H - X.O)[..., wm] < h).mean(-1), "share_open_is_low": (np.abs(X.L - X.O)[..., wm] < h).mean(-1)}
    return {k: np.atleast_1d(v) for k, v in out.items()}


def _tick_worker(args):
    seed_seq, R, c, drift, tick = args
    c.tick_round = tick
    rng = np.random.default_rng(seed_seq)
    S = simulate(rng, R, c, drift)
    rec = run_variants(S, 0, None, with_model=False)
    return placebo_stats(S, rec)


def placebo_diag(S: Sess, E, outdir: Path, reps: int = 400, procs: int = 4, chunk: int = 8):
    """(1) real versus simulated daily-bar summaries per window (where the random-walk placebo is not like the data);
    (2) paired sensitivity to rounding simulated prices to the tick (section 0.7 says prices are rounded; the main placebo does not round):
    the first `reps` histories of the main placebo (same seeds, zero drift) are re-run with rounding and compared one by one."""
    from multiprocessing import Pool
    c = build_ctx(S, E)
    sim = simulate(np.random.default_rng(7), 200, c, False)
    rows = []
    for w in WINDOWS:
        real, sm = _day_metrics(S, w), _day_metrics(sim, w)
        nreal = int((win_mask(S.dates, w) & (np.arange(S.n) >= S.i0)).sum())
        for k in real:
            v = sm[k]
            rows.append({"metric": k, "window": w, "n_sessions": nreal, "real": float(real[k][0]), "sim_mean": float(v.mean()), "sim_p05": float(np.quantile(v, 0.05)), "sim_p95": float(np.quantile(v, 0.95)),
                         "sim_histories": int(len(v)), "real_minus_sim": float(real[k][0] - v.mean())})
    pd.DataFrame(rows).to_csv(outdir / "hl_trade_placebo_diag.csv", index=False)
    # (2) tick rounding, paired
    nchunk = int(np.ceil(reps / chunk))
    ss = np.random.SeedSequence(SEED).spawn(nchunk)
    res = {}
    for tick in (False, True):
        jobs = [(ss[i], min(chunk, reps - i * chunk), c, False, tick) for i in range(nchunk)]
        with Pool(procs) as pool:
            outs = pool.map(_tick_worker, jobs)
        agg = {}
        for st in outs:
            for k, v in st.items():
                agg.setdefault(k, []).append(v)
        res[tick] = {k: np.concatenate(v, axis=0) for k, v in agg.items()}
    R0 = pd.read_csv(outdir / "hl_trade_rules.csv")
    R0 = R0[R0.fill_mode == 0]
    out = []
    for (name, w), a0 in res[False].items():
        if w not in ("final", "all") or name not in PRIMARY.values() and name not in ("R4b", "R3_z1.0", "R3_z2.0", "R1_k0.5", "R2_k0.5"):
            continue
        a1 = res[True][(name, w)]
        with np.errstate(invalid="ignore", divide="ignore"):
            m0, m1 = a0[:, 2] / a0[:, 0], a1[:, 2] / a1[:, 0]
        ok = (a0[:, 0] >= 1) & (a1[:, 0] >= 1)
        obs = R0[(R0.variant == name) & (R0.window == w)]
        o = float(obs.mean_net_pct.iloc[0]) / 100 if len(obs) and np.isfinite(obs.mean_net_pct.iloc[0]) else np.nan
        def pp(m, valid):
            mm = np.where(valid, m, -np.inf)
            return (1 + np.sum(mm >= o - 1e-15)) / (len(mm) + 1) if np.isfinite(o) else np.nan
        out.append({"variant": name, "window": w, "histories": int(len(m0)), "observed_net_pct": 100 * o if np.isfinite(o) else np.nan,
                    "mean_trades_unrounded": float(a0[:, 0].mean()), "mean_trades_rounded": float(a1[:, 0].mean()),
                    "null_mean_net_pct_unrounded": float(100 * np.nanmean(m0[ok])), "null_mean_net_pct_rounded": float(100 * np.nanmean(m1[ok])),
                    "paired_diff_mean_pct": float(100 * np.nanmean((m1 - m0)[ok])), "paired_diff_sd_pct": float(100 * np.nanstd((m1 - m0)[ok], ddof=1)),
                    "p_placebo_unrounded": pp(m0, a0[:, 0] >= 1), "p_placebo_rounded": pp(m1, a1[:, 0] >= 1)})
    pd.DataFrame(out).to_csv(outdir / "hl_trade_sensitivity_tick.csv", index=False)


# ----------------------------------------------------------------------------- independent re-computation (plain loops; does not call run_variants, estimators or the statistics helpers)
def indepcheck(hpath: str, outdir: Path):
    """Re-implements the headline numbers with plain Python loops straight from the raw files and compares them with the result files.
    It checks the coding and the arithmetic of the vectorised study, not the design (it is the same rules typed a second time)."""
    import math
    a = pd.read_csv("data/processed/bse_daily.csv", parse_dates=["date"]).set_index("date")
    b = pd.read_csv("data/processed/bse_daily_extra.csv", parse_dates=["date"]).set_index("date")
    b = b[~b.index.isin(a.index)]
    cols = ["open", "high", "low", "close", "prev"]
    d = pd.concat([a[cols], b[cols]]).sort_index()
    d = d[d.index <= CUTOFF]
    dates = list(d.index)
    O, H, L, C, P0 = (d[c].values.astype(float).tolist() for c in cols)
    n = len(d)
    lam = 0.94

    def ewma(x, warm=30):
        s = [float("nan")] * len(x)
        v = sum(u * u for u in x[:warm]) / warm
        for i in range(warm, len(x)):
            s[i] = math.sqrt(v)
            v = lam * v + (1 - lam) * x[i] ** 2
        return s
    LO = [math.log(L[i] / O[i]) for i in range(n)]
    HO = [math.log(H[i] / O[i]) for i in range(n)]
    G = [math.log(O[i] / P0[i]) for i in range(n)]
    sL, sH, sG = ewma(LO), ewma(HO), ewma(G)
    i0 = next(i for i, x in enumerate(dates) if x >= D0)
    wins = {"all": lambda x: x >= D0, "dev": lambda x: x < VAL0, "val": lambda x: VAL0 <= x < FIN0, "final": lambda x: x >= FIN0, "cas": lambda x: x >= CAS0}
    gr = {(v, w): [] for v in ("R1_k1.0", "R2_k1.0", "R5_z1.0", "R6_long_s1_t2", "R7_emp_q25") for w in wins}
    for i in range(i0, n):
        lv1, lv2 = O[i] * math.exp(-sL[i]), O[i] * math.exp(sH[i])
        z = G[i] / sG[i]
        r = {}
        if L[i] < lv1:
            r["R1_k1.0"] = C[i] / lv1 - 1
        if H[i] > lv2:
            r["R2_k1.0"] = 1 - C[i] / lv2
        if z <= -1:
            r["R5_z1.0"] = C[i] / O[i] - 1
        elif z >= 1:
            r["R5_z1.0"] = 1 - C[i] / O[i]
        r["R6_long_s1_t2"] = -0.01 if L[i] <= O[i] * 0.99 else (0.02 if H[i] > O[i] * 1.02 else C[i] / O[i] - 1)
        if i >= 250:
            lvq = O[i] * math.exp(float(np.quantile(LO[i - 250:i], 0.25)))
            if L[i] < lvq:
                r["R7_emp_q25"] = C[i] / lvq - 1
        for v, g in r.items():
            for w, f in wins.items():
                if f(dates[i]):
                    gr[(v, w)].append(g)
    # hourly rules
    jj = json.load(open(hpath))["chart"]["result"][0]
    q = jj["indicators"]["quote"][0]
    T = pd.to_datetime(jj["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata")
    bars = {}
    for k, tt in enumerate(T):
        if None in (q["open"][k], q["high"][k], q["low"][k], q["close"][k]) or tt.tz_localize(None).normalize() > CUTOFF:
            continue
        bars.setdefault(tt.strftime("%Y-%m-%d"), []).append((tt.strftime("%H:%M"), q["open"][k], q["high"][k], q["low"][k], q["close"][k]))
    sess = []
    for ds, bl in sorted(bars.items()):
        ts = pd.Timestamp(ds)
        bl = sorted(bl)
        if ts not in d.index or [x[0] for x in bl] != HOURS:
            continue
        fct = 3.0 if ts < EX_DATE else 1.0
        sess.append((ts, [(o * fct, h * fct, l * fct, c * fct) for (_, o, h, l, c) in bl]))
    r1 = [math.log(s[1][0][3] / s[1][0][0]) for s in sess]
    sig1 = ewma(r1, warm=40)
    hg = {(v, w): [] for v in ("R3_z1.5", "R4a") for w in wins}
    ex_up10, ex_dn10 = [], []
    for idx, (ts, bl) in enumerate(sess):
        close = C[dates.index(ts)]
        if ts >= FIN0:                                                         # 10:15 entry excursions (Final)
            ent = bl[0][3]
            ex_up10.append(max(max(x[1] for x in bl[1:]) / ent - 1, 0.0))
            ex_dn10.append(max(1 - min(x[2] for x in bl[1:]) / ent, 0.0))
        if not np.isfinite(sig1[idx]):
            continue
        z1 = r1[idx] / sig1[idx]
        rr = {}
        if z1 >= 1.5:
            rr["R3_z1.5"] = 1 - close / bl[0][3]
        elif z1 <= -1.5:
            rr["R3_z1.5"] = close / bl[0][3] - 1
        h1, l1 = bl[0][1], bl[0][2]
        for k in range(1, 5):
            ok_, hk, lk, ck = bl[k]
            lb, sb = hk > h1, lk < l1
            if lb or sb:
                el, es = max(h1, ok_), min(l1, ok_)
                rl, rs = close / el - 1, 1 - close / es
                rr["R4a"] = min(rl, rs) if (lb and sb) else (rl if lb else rs)
                break
        for v, g in rr.items():
            for w, f in wins.items():
                if f(ts):
                    hg[(v, w)].append(g)
    # model-quantile rules
    m = pd.read_csv(PRED, parse_dates=["date"]).set_index("date")
    for v, col, side in (("R7_post_q25", "W_I6_L_q25", "L"), ("R8_post_q75", "W_I6_H_q75", "H")):
        for w in wins:
            gr[(v, w)] = []
        for ts, row in m.iterrows():
            i = dates.index(ts)
            lvl = row[col]
            if side == "L" and L[i] < lvl:
                g = C[i] / lvl - 1
            elif side == "H" and H[i] > lvl:
                g = 1 - C[i] / lvl
            else:
                continue
            for w, f in wins.items():
                if f(ts):
                    gr[(v, w)].append(g)
    allg = {**gr, **hg}
    R = pd.read_csv(outdir / "hl_trade_rules.csv")
    R = R[R.fill_mode == 0]
    rows = []

    def add(check, ind, sto, tol=1e-7):
        ok = (ind == sto) if isinstance(ind, (int, np.integer)) and isinstance(sto, (int, np.integer)) else bool(abs(ind - sto) <= tol)
        rows.append({"check": check, "independent": ind, "stored": sto, "abs_diff": abs(ind - sto), "passed": bool(ok)})
    add("daily sessions in file (to cut-off)", n, int(len(load_daily())))
    for (v, w), g in allg.items():
        if w == "dev" and v in HOURLY_VARIANTS:
            continue
        sr = R[(R.variant == v) & (R.window == w)]
        if len(sr) == 0:
            continue
        add(f"{v} {w}: number of trades", len(g), int(sr.n_trades.iloc[0]))
        if len(g):
            add(f"{v} {w}: mean gross return % per trade", 100 * float(np.mean(g)), float(sr.mean_gross_pct.iloc[0]))
            add(f"{v} {w}: mean net return % per trade (0.10% cost)", 100 * float(np.mean(g) - COST), float(sr.mean_net_pct.iloc[0]))
    # Newey-West (Bartlett, lag 5) one-sided p of R4a net, Final: plain loops
    for v, w in (("R4a", "final"), ("R1_k1.0", "final"), ("R7_post_q25", "final")):
        x = [g - COST for g in allg[(v, w)]]
        nn = len(x)
        mu = sum(x) / nn
        dd = [u - mu for u in x]
        s = sum(u * u for u in dd) / nn
        for k in range(1, 6):
            s += 2 * (1 - k / 6) * sum(dd[i] * dd[i - k] for i in range(k, nn)) / nn
        tstat = mu / math.sqrt(s / nn)
        sr = R[(R.variant == v) & (R.window == w)].iloc[0]
        add(f"{v} {w}: HAC t of net mean", tstat, float(sr.t_hac_net), tol=1e-6)
        add(f"{v} {w}: HAC one-sided p of net mean", float(stats.t.sf(tstat, nn - 1)), float(sr.p_hac_net), tol=1e-7)
    # open is the high / low; Final median excursions from the open; 10:15 excursions
    add("open equals day high, sessions from 2019-01-01", sum(1 for i in range(i0, n) if abs(H[i] - O[i]) < 1e-6), int(round(pd.read_csv(outdir / "hl_trade_open_hl_real.csv").query("source=='daily official' and window=='all'").k_open_high.iloc[0])))
    add("open equals day low, sessions from 2019-01-01", sum(1 for i in range(i0, n) if abs(L[i] - O[i]) < 1e-6), int(round(pd.read_csv(outdir / "hl_trade_open_hl_real.csv").query("source=='daily official' and window=='all'").k_open_low.iloc[0])))
    EXs = pd.read_csv(outdir / "hl_trade_excursions.csv")
    fi = [i for i in range(i0, n) if dates[i] >= FIN0]
    add("Final median high above open (%)", 100 * float(np.median([H[i] / O[i] - 1 for i in fi])), float(EXs.query("entry=='open' and window=='final' and excursion=='up'").q50_pct.iloc[0]))
    add("Final median low below open (%)", 100 * float(np.median([1 - L[i] / O[i] for i in fi])), float(EXs.query("entry=='open' and window=='final' and excursion=='down'").q50_pct.iloc[0]))
    add("Final 90th pct low below open (%)", 100 * float(np.quantile([1 - L[i] / O[i] for i in fi], 0.9)), float(EXs.query("entry=='open' and window=='final' and excursion=='down'").q90_pct.iloc[0]))
    add("10:15 entry, Final median room above (%)", 100 * float(np.median(ex_up10)), float(EXs.query("entry=='10:15' and window=='final' and excursion=='up'").q50_pct.iloc[0]))
    add("10:15 entry, Final median room below (%)", 100 * float(np.median(ex_dn10)), float(EXs.query("entry=='10:15' and window=='final' and excursion=='down'").q50_pct.iloc[0]))
    # Kupiec of the fill frequency of the model low order, Final
    xs = [(1 if L[dates.index(ts)] < row["W_I6_L_q25"] else 0) for ts, row in m.iterrows() if ts >= FIN0]
    nn, xx = len(xs), sum(xs)
    ph = xx / nn
    ll = lambda pp_: xx * math.log(pp_) + (nn - xx) * math.log(1 - pp_)
    lr = -2 * (ll(0.25) - ll(ph))
    ku = pd.read_csv(outdir / "hl_trade_kupiec_fill.csv").query("variant=='R7_post_q25' and window=='final'").iloc[0]
    add("R7_post_q25 Final: fill frequency", ph, float(ku.observed_fill))
    add("R7_post_q25 Final: Kupiec p of the fill frequency", math.erfc(math.sqrt(lr / 2)), float(ku.kupiec_p), tol=1e-7)
    out = pd.DataFrame(rows)
    out.to_csv(outdir / "hl_trade_indepcheck.csv", index=False, float_format="%.10g")
    print(f"independent re-computation: {int(out.passed.sum())} of {len(out)} comparisons agree")
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
                null_mean, null_sd, null_q95, null_gross, null_n, null_tsd = (np.full(len(sub), np.nan) for _ in range(6))
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
                        null_tsd[i] = pooled_trade_sd(arr)
                sub[f"p_placebo_{tag}"] = pp
                sub[f"holm_placebo_{tag}"] = holm(pp) if np.isfinite(pp).any() else np.nan
                sub[f"null_mean_net_pct_{tag}"] = null_mean
                sub[f"null_sd_net_pct_{tag}"] = null_sd
                sub[f"null_q95_net_pct_{tag}"] = null_q95
                sub[f"null_mean_gross_pct_{tag}"] = null_gross
                sub[f"null_mean_trades_{tag}"] = null_n
                sub[f"null_trade_sd_pct_{tag}"] = null_tsd
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
    nan = {"p": np.nan, "null_mean": np.nan, "null_sd": np.nan, "null_q95": np.nan, "null_gross": np.nan, "null_n": np.nan, "null_tsd": np.nan}
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
            "null_q95": np.nanquantile(mean_net[valid], 0.95) * 100, "null_gross": np.nanmean(mean_gross[valid]) * 100, "null_n": float(np.mean(arr[:, 0])), "null_tsd": pooled_trade_sd(arr)}


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
        for col in ("p", "null_mean", "null_sd", "null_q95", "null_gross", "null_n", "null_tsd"):
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
            sub[f"null_trade_sd_pct_{tag}"] = [c_["null_tsd"] for c_ in cols]
            sub[f"holm_placebo_{tag}"] = holm(sub[f"p_placebo_{tag}"].values)
            pre_p[(w, tag)] = sub[f"p_placebo_{tag}"].values
            g = PH[(PH.fill_mode == 0) & (PH.window == w)]
            cc = [_placebo_cols(P, tag, r_["variant"], w, r_.get("mean_net_pct", np.nan), r_["n_trades"]) for _, r_ in g.iterrows()]
            for col in ("p", "null_mean", "null_sd", "null_q95", "null_gross", "null_n", "null_tsd"):
                PH.loc[g.index, f"placebo_{col}_{tag}"] = [c_[col] for c_ in cc]
            adj = holm(np.concatenate([pre_p[(w, tag)], np.array([c_["p"] for c_ in cc])]), m_total=fam)
            PH.loc[g.index, f"holm_placebo_joint_{tag}"] = adj[len(sub):]
        SENS.append(sub[["variant", "rule", "window", "n_sessions", "n_trades", "fill_rate", "mean_gross_pct", "mean_net_pct", "sd_net_pct", "p_hac_net", "holm_hac"]
                        + [f"{a}_{t}" for t in PTAGS for a in ("p_placebo", "holm_placebo", "null_mean_net_pct", "null_sd_net_pct", "null_mean_trades", "null_trade_sd_pct")]])
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
    # stop distances for the next session from the three estimators of stop_forecast_eval (using sessions through 15 Oct only)
    srows = []
    for side in ("long", "short"):
        a = -E["LO"][0] if side == "long" else E["HO"][0]
        sg_ = E["sigL"][0] if side == "long" else E["sigH"][0]
        zz = (a / sg_)[np.isfinite(a / sg_)]
        sig_next = nxt["sigL"] if side == "long" else nxt["sigH"]
        simple = (lambda f: 1 - np.exp(-f)) if side == "long" else (lambda f: np.exp(f) - 1)
        for q in (0.5, 0.75, 0.9):
            for name, f_ in (("T250", float(np.quantile(a[n - 250:n], q))), ("EXPANDING", float(np.quantile(a, q))), ("EWMA_SCALED", float(sig_next * np.quantile(zz, q)))):
                srows.append({"side": side, "stop_quantile": q, "nominal_touch_share": round(1 - q, 2), "method": name, "distance_pct_of_open": 100 * float(simple(f_)), "distance_rs_at_reference": float(simple(f_) * ref)})
    pd.DataFrame(srows).to_csv(outdir / "hl_trade_today_stops_2026-10-16.csv", index=False)
    out = {"data_through": str(S.dates[-1].date()), "reference_close_rs": ref, "next_session": "2026-10-16",
           "ewma_scales_for_16oct_pct": {k: 100 * v for k, v in nxt.items()},
           "ewma_scales_in_rupees_at_reference": {k: v * ref for k, v in nxt.items()},
           "R1_k1_level_offset_below_open": {"pct": 100 * (1 - np.exp(-nxt["sigL"])), "rs": ref * (1 - np.exp(-nxt["sigL"]))},
           "R2_k1_level_offset_above_open": {"pct": 100 * (np.exp(nxt["sigH"]) - 1), "rs": ref * (np.exp(nxt["sigH"]) - 1)},
           "regime_expanding_terciles": summary.get("regime_for_16oct_expanding"), "regime_trailing500_posthoc": summary.get("regime_for_16oct_trailing500"),
           "regime_fullsample_posthoc": summary.get("regime_for_16oct_fullsample"),
           "note": "descriptive; uses nothing dated after the 15 Oct 2026 close (the 16 Oct open and session are not used); all rupee figures are percent x the 15 Oct close"}
    (outdir / "hl_trade_today_2026-10-16.json").write_text(json.dumps(out, indent=1))
    return out


# ----------------------------------------------------------------------------- report builder (reads result files only; every number in the text comes from them)
REPORT = Path("research/hl/C_tradeability.md")
SECTION0_END = "*END OF PRE-FIXED SECTION*"
SECTION0_SHA256 = "4f8bd8aa1a07ffd01b8bb3fe59054f20d0112e98d975aa507e3233b430b2cc19"   # SHA-256 of the report text up to and including SECTION0_END, written to a file at 17:03:06 UTC on 15 Oct 2026


def build_report(outdir: Path, report_path: Path | None = None):
    """Writes the results sections of research/hl/C_tradeability.md.  Section 0 (everything up to and including the 'END OF PRE-FIXED SECTION' line) is kept
    byte-identical (its SHA-256 is checked).  Every number in the text is read from results/hl_trade_*.csv / .json; qualitative sentences are guarded by `chk`,
    which stops the build if the files do not support them."""
    report_path = report_path or REPORT
    rd = lambda n: pd.read_csv(outdir / n)
    R, HM, V = rd("hl_trade_rules.csv"), rd("hl_trade_holm.csv"), rd("hl_trade_verdicts.csv")
    EX, STD, STH = rd("hl_trade_excursions.csv"), rd("hl_trade_stop_target_daily.csv"), rd("hl_trade_stop_target_hourly.csv")
    OH, OHP, OHC = rd("hl_trade_open_hl_real.csv"), rd("hl_trade_open_hl.csv"), rd("hl_trade_open_hl_clock.csv")
    RF, SC, BY, EB = rd("hl_trade_range_formed.csv"), rd("hl_trade_stop_calibration.csv"), rd("hl_trade_byyear.csv"), rd("hl_trade_extreme_bar.csv")
    DM, KU, BO, XC, DC = rd("hl_trade_dm.csv"), rd("hl_trade_kupiec_fill.csv"), rd("hl_trade_bracket_order.csv"), rd("hl_trade_crosscheck.csv"), rd("hl_trade_data_checks.csv")
    PH, PHY, SENS = rd("hl_trade_posthoc.csv"), rd("hl_trade_posthoc_byyear.csv"), rd("hl_trade_sensitivity_clock.csv")
    REF, TODAY, EQ, ST = rd("hl_trade_reference_drift.csv"), rd("hl_trade_today_2026-10-16.csv"), rd("hl_trade_open_equals_prev.csv"), rd("hl_trade_selftest.csv")
    SF, TSTOP = rd("hl_trade_stop_forecast.csv"), rd("hl_trade_today_stops_2026-10-16.csv")
    MM, DG, TK, CL, IC = rd("hl_trade_model_miss.csv"), rd("hl_trade_placebo_diag.csv"), rd("hl_trade_sensitivity_tick.csv"), rd("hl_trade_clock.csv"), rd("hl_trade_indepcheck.csv")
    SUM = json.load(open(outdir / "hl_trade_summary.json"))
    TJ = json.load(open(outdir / "hl_trade_today_2026-10-16.json"))
    R0, HM0, PH0 = R[R.fill_mode == 0], HM[HM.fill_mode == 0], PH[PH.fill_mode == 0]

    def f(x, d=2):
        return "n/a" if pd.isna(x) else f"{x:.{d}f}"

    def sg(x, d=2):
        return "n/a" if pd.isna(x) else f"{x:+.{d}f}"

    def rs(x, sign=False):
        if pd.isna(x):
            return "n/a"
        s = f"{abs(x):,.0f}" if abs(x) >= 10 else f"{abs(x):.1f}"
        return (("+" if x >= 0 else "-") if sign else ("-" if x < 0 else "")) + s

    def rup(x, d=1):
        """signed rupee amount, e.g. -Rs 14 or +Rs 1.3"""
        if pd.isna(x):
            return "n/a"
        return ("-" if x < 0 else "+") + "Rs " + (f"{abs(x):,.0f}" if abs(x) >= 10 else f"{abs(x):.{d}f}")

    def pv(p):
        if pd.isna(p):
            return "n/a"
        return "<0.001" if p < 0.001 else f"{p:.3f}"

    def peq(p):
        """'= 0.035' or '< 0.001', to follow the word p"""
        return "n/a" if pd.isna(p) else ("< 0.001" if p < 0.001 else f"= {p:.3f}")

    def pc(x, d=0):
        return "n/a" if pd.isna(x) else f"{100 * x:.{d}f}%"

    def table(head, rows):
        out_ = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
        for r_ in rows:
            out_.append("| " + " | ".join(str(c) for c in r_) + " |")
        return "\n".join(out_)

    def one(df, **kw):
        m_ = np.ones(len(df), bool)
        for k, v in kw.items():
            m_ &= (df[k] == v).values
        if not m_.any():
            raise KeyError(kw)
        return df[m_].iloc[0]

    def chk(cond, msg):
        if not bool(cond):
            raise AssertionError("report claim not supported by the result files: " + msg)

    WN = {"all": "all 2019-2026", "dev": "Development", "val": "Validation", "final": "Final", "cas": "post-closing-auction"}
    WNH = {"all": "whole hourly sample (Oct 2024 - Oct 2026)", "val": "Validation (Oct 2024 - Jun 2025)", "final": "Final", "cas": "post-closing-auction"}
    PRIM = PRIMARY
    RULETXT = {"R1": "(a) limit buy 1 sigma below the open, exit at the close", "R2": "(b) limit sell (short) 1 sigma above the open, exit at the close",
               "R3": "(c) fade a first-hour move beyond 1.5 sigma, exit at the close", "R4": "(d) follow a breakout of the first-hour range, exit at the close",
               "R5": "(e) trade against a gap larger than 1 sigma, open to close", "R6": "(f) long from the open, stop 1%, target 2%, else close",
               "R7": "limit buy at the project's estimated low (25% level, known after the open)", "R8": "limit sell at the project's estimated high (75% level, known after the open)"}
    out = []
    w = out.append
    fin = {k: one(HM0, variant=v, window="final") for k, v in PRIM.items()}
    cas = {k: one(HM0, variant=v, window="cas") for k, v in PRIM.items()}
    val = {k: one(HM0, variant=v, window="val") for k, v in PRIM.items()}
    VD = {r_.rule: r_.verdict for r_ in V.itertuples()}
    nd = {k: int(one(R0, variant="R6_long_s1_t2", window=k).n_sessions) for k in ("all", "dev", "val", "final", "cas")}
    nh = {k: int(one(R0, variant="R4a", window=k).n_sessions) for k in ("all", "val", "final", "cas")}
    nh_all_sessions = int(SUM["hourly_sessions_used"])
    nhf, nhc = int(one(EX, entry="10:15", window="final", excursion="up").n), int(one(EX, entry="10:15", window="cas", excursion="up").n)
    chk(nd["final"] == 320 and nd["cas"] == 51, "sample sizes of the Final and post-auction windows changed")
    r4v, r4f, r4c = val["R4"], fin["R4"], cas["R4"]
    r4_all = one(HM0, variant="R4a", window="all")
    r4b_all = one(HM0, variant="R4b", window="all")
    p5_005 = float(stats.t.sf((fin["R5"].mean_gross_pct - 0.05) / fin["R5"].se_hac_pct, int(fin["R5"].n_trades) - 1))
    pmin_005 = min(float(stats.t.sf((fin[k].mean_gross_pct - 0.05) / fin[k].se_hac_pct, int(fin[k].n_trades) - 1)) for k in PRIM)
    chk(pmin_005 > 0.05, "a primary rule would become significant at a 0.05% cost")
    mde_lo, mde_hi = min(fin[k].mde_80pct_power_pct for k in PRIM), max(fin[k].mde_80pct_power_pct for k in PRIM)
    k7, k8 = one(KU, variant="R7_post_q25", window="final"), one(KU, variant="R8_post_q75", window="final")
    n_neg = sum(1 for k in PRIM if fin[k].mean_net_pct < 0)
    chk(n_neg == 7 and fin["R4"].mean_net_pct > 0, "seven of the eight primary rules should have a negative net mean in Final and R4 a positive one")
    chk(all(VD[k] == "not found" for k in PRIM if k != "R4") and VD["R4"] == "descriptive", "verdicts changed")
    chk(all(fin[k].holm_hac >= 0.999 for k in PRIM), "a primary rule has a Holm-adjusted p below 1 in Final")
    chk(r4v.holm_hac < 0.05 and r4v.mean_net_pct > 0, "R4 should be Holm-significant in Validation")

    # ===================================================================================================================== 1. short answer
    w("## 1. Short answer, in plain words\n")
    w("**Can the estimated high and low of the next session be turned into a profitable intraday trade? On this evidence, no.** "
      f"I fixed eight rules in advance (section 0; 31 variants counting the neighbours of each rule), tested them in time order with a 0.10% round-trip cost, "
      f"and compared them with a random-walk placebo of {SUM['placebo_reps_per_setting']:,} simulated histories. **No rule meets the bar for the word 'validated'.** "
      f"In the Final window (sessions from 1 Jul 2025: {nd['final']} daily sessions, {nh['final']} with usable hourly bars) {n_neg} of the 8 primary rules had a negative mean return after costs. "
      f"The eighth, 'follow a breakout of the first-hour range' (R4), is labelled **descriptive**: that word only means its Final-window mean was above zero, "
      f"at {sg(r4f.mean_net_pct)}% (Rs {f(r4f.mean_net_rs, 1)}) per trade net, n = {int(r4f.n_trades)} trades, p = {f(r4f.p_hac_net, 2)}, which is nothing. "
      f"It earned {sg(r4v.mean_net_pct)}% per trade net in the Validation half-year (n = {int(r4v.n_trades)} trades, Holm-adjusted p = {f(r4v.holm_hac, 3)}), "
      f"then {sg(r4f.mean_net_pct)}% in Final and {sg(r4c.mean_net_pct)}% in the {int(r4c.n_trades)} trades since the closing auction began. "
      "That is the pattern of something that was there for a while and went away, not of something to build on.\n")
    rows = []
    for k, v in PRIM.items():
        a = fin[k]
        rows.append([k, RULETXT[k], int(a.n_sessions), int(a.n_trades), sg(a.mean_gross_pct), sg(a.mean_net_pct), sg(a.mean_net_rs, 1), pv(a.p_hac_net), f(a.holm_hac, 2), f"**{VD[k]}**"])
    w("Final window, primary variant of each rule, strict fill convention (the extreme must trade through the level), 0.10% round-trip cost. All variants are in section 4.\n")
    w(table(["rule", "what it does", "sessions", "trades", "gross % per trade", "net % per trade", "net Rs per trade", "p (net mean > 0)", "Holm p", "verdict"], rows))
    w("\n'Net Rs per trade' is net % times Rs 3,428 (the 15 Oct close). p is one-sided with a Newey-West (autocorrelation-robust) standard error. Holm corrects for trying 31 variants in the same window. "
      "R7 and R8 are the project's own estimated-low and estimated-high levels (specialist A's stored out-of-sample quantiles); R1 and R2 are the same idea with a plain past-only scale. "
      "R7 and R8 cannot be re-fitted inside a simulation, so they have no placebo and could never be called validated (pre-fixed in 0.7).\n")
    r7, r8 = fin["R7"], fin["R8"]
    chk(r7.mean_net_pct < 0 and r8.mean_net_pct < 0 and k7.kupiec_p > 0.05 and k8.kupiec_p > 0.05, "R7/R8 fill-frequency or sign claim")
    w(f"**The estimated levels themselves are not the problem.** The post-open 25% low level was traded through on {pc(k7.observed_fill, 1)} of the {int(k7.n)} Final sessions "
      f"(promised 25%, Kupiec p = {f(k7.kupiec_p, 2)}) and the 75% high level on {pc(k8.observed_fill, 1)} (promised 25%, p = {f(k8.kupiec_p, 2)}). "
      f"A level that is touched as often as promised is still not a bargain: a buyer at the estimated low lost Rs {rs(-r7.mean_net_rs)} per share on average per fill "
      f"({sg(r7.mean_net_pct)}% net, {sg(r7.mean_gross_pct)}% before cost, n = {int(r7.n_trades)}), and a seller at the estimated high lost Rs {rs(-r8.mean_net_rs)} "
      f"({sg(r8.mean_net_pct)}% net, n = {int(r8.n_trades)}). Once the price reached those levels it showed no tendency to turn back (gross mean per fill {sg(r7.mean_gross_pct)}% for the low level and {sg(r8.mean_gross_pct)}% for the high level in Final; {sg(one(HM0, variant='R7_post_q25', window='all').mean_gross_pct)}% and {sg(one(HM0, variant='R8_post_q75', window='all').mean_gross_pct)}% over 2020-2026, where a turn would show as a positive number). "
      "The same was true of the transparent versions (R1, R2). The opposite-direction look (trade with the breach instead of against it) is post hoc and is in section 5.\n")
    w("**What the estimates are good for** is risk management, not entries: how far a stop has to be to survive an ordinary day, how large a position that implies, and how little room is left late in the day (sections 3 and 7). "
      "**What they cannot do** is tell you where to buy or sell for a profit.\n")
    w("**Words used.** *Net* = after the 0.10% round-trip cost (Rs 3.4 a share at today's price). *Fill* = a resting limit order counts as executed only if the day's price trades strictly through its level. "
      "*p-value* = the chance of a result at least this good if there were no edge at all; small (under 0.05) means unlikely to be luck, and *Holm* tightens that after correcting for the number of variants tried. "
      "*Placebo* = the same rule run on 2,000 invented random-walk histories with the same volatility pattern, to show what luck alone produces. "
      "*Final window* = sessions from 1 Jul 2025; the rules were fixed in section 0, so this window was not used to choose a rule (section 2 says what can and cannot be checked about that; the one exception is the project's own model behind R7 and R8, which the project chose using it). "
      "*Descriptive* = something happened in this sample; it does not mean tradable.\n")
    w("**In three lines for a trader.** "
      f"(1) Do not place orders at the estimated high or low expecting a turn: in the {nd['final']} Final sessions that lost Rs {rs(-r7.mean_net_rs)} (buying at the low) and Rs {rs(-r8.mean_net_rs)} (selling at the high) a share per fill after costs. "
      f"(2) Do use them, and the swing tables in 3.1, to decide how far a stop must sit and how many shares that allows: from the open the low has been at least Rs {rs(one(EX, entry='open', window='final', excursion='down').q50_rs)} below on half the days and Rs {rs(one(EX, entry='open', window='final', excursion='down').q90_rs)} below on one day in ten. "
      f"(3) After about 13:15 there is little left to gain (median Rs {rs(one(EX, entry='13:15', window='final', excursion='up').q50_rs)}-{rs(one(EX, entry='13:15', window='final', excursion='down').q50_rs)} of room against a Rs {f(0.001 * RS, 1)} round trip), so late entries rarely pay their costs.\n")
    w(f"**How much would have been visible.** With {int(min(fin[k].n_trades for k in PRIM))}-{int(max(fin[k].n_trades for k in PRIM))} trades per rule in the Final window, a true edge smaller than about {f(mde_lo)}-{f(mde_hi)}% net per trade "
      "could not have been detected with 80% power (column 'MDE' in 4.1). So 'not found' means 'no edge large enough to see', not 'proven absent'. "
      "An edge of 0.1-0.2% per trade, the size that would matter after costs, would need on the order of a thousand trades per rule to confirm or to rule out.\n")

    # ===================================================================================================================== 2. what was built
    w("## 2. What was built, where it came from, and what changed after the first look\n")
    w("* **Code**: `src/hl_trade_study.py` (commands `selftest`, `part1`, `part2`, `placebo`, `finish`, `posthoc`, `today`, `indepcheck`, `diag`, `report`; `all` runs them in that order; no network). "
      "**Outputs**: `results/hl_trade_*.csv` and `.json` (section 10). **This report** is written by `report` from those files only.")
    w(f"* **Inputs** (nothing dated after 15 Oct 2026; the code drops later bars if they ever appear): `data/processed/bse_daily.csv` + `bse_daily_extra.csv` ({SUM['daily_sessions']:,} sessions, last official bar 15 Oct 2026: open 3,342.0, high 3,445.0, low 3,315.2, close 3,428.0; "
      f"`common.load_bse()` alone ends on 13 Oct, so the extra file is needed); the Yahoo 1-hour file for BSE.NS (range 2y, fetched 15 Oct, SHA-256 `{SUM['hourly_file_sha256'][:16]}...`, last bar the 15:15 bar of 15 Oct, {SUM['hourly_sessions_used']} complete 7-bar sessions used; not stored in the repo); "
      f"specialist A's stored out-of-sample quantiles `results/hl_eval_predictions.csv` (SHA-256 `{SUM['predictions_file_sha256'][:16]}...`).")
    w("* **When, and what was not used.** The study was re-run and this report written on the morning of Fri 16 Oct 2026; the last full run finished at about 09:23 IST, after the 09:15 open, so the wording 'before the open' used in the brief no longer applies to the run time. "
      "That does not matter for the data: the data cut-off is the 15 Oct 2026 close, the code drops any later bar (the hourly file's last bar is the 15:15 bar of 15 Oct), and no 16 Oct price enters any number. "
      "I did see, in a git commit message of the repository history, that a pre-open snapshot of 16 Oct exists and what opening price it records; I did not open that file or use the figure, and nothing in this report depends on it.")
    w("* **Provenance, stated plainly.** An earlier attempt at this task stopped part-way (usage limit) and left code, 28 result files and section 0. I trusted none of its numbers. I re-ran its unchanged code from scratch "
      "(self-test, Part 1, Part 2, the 2,000-history placebo in four settings, the finishing step, the post-hoc step) and compared every result file by SHA-256 with the file on disk: all 28 were byte-for-byte identical (same seeds give the same placebo). "
      "That comparison was done in the session scratchpad and is not reproducible from the repository alone. I then made the additions listed below, re-ran everything, and rebuilt this report from the files.")
    w(f"* **Is section 0 really pre-fixed?** Its text is unchanged: its SHA-256 (`{SECTION0_SHA256[:16]}...`, checked by `report` every time it runs) is the value that was written to a file five seconds after the report file was last modified, at 17:03:06 UTC on 15 Oct 2026, "
      "and the first commit containing any result file is dated 17:13 UTC. Section 0 itself states that no result had been computed when it was written. I cannot audit that statement from the repository (the same limit the independent verifier of specialist A noted for A's report); "
      "what can be checked is that no variant, window, cost or verdict rule has changed since, and that everything added later is listed here.")
    w("* **Changes and additions after the first look** (none changes a pre-fixed rule, window, cost, fill convention or the verdict rule; items 1-6 come from the earlier attempt's own notes and code comments, items 7-10 are mine):")
    w("  1. The two-sided placebo p-value for the first-hour share is capped at 1, because ties can push it above 1 (`hl_trade_open_hl.csv`).")
    w("  2. A Holm-adjusted two-sided column was added to the Diebold-Mariano table (`hl_trade_dm.csv`).")
    w("  3. The hourly rules R3/R4 were added to the no-look-ahead self-test.")
    w("  4. Volatility regime for Part 1: the pre-fixed expanding terciles leave almost no 'low' sessions in the Final window "
      f"({SUM['n_by_regime_final_expanding']['low']} of {nd['final']}), so two **post-hoc** definitions were added and labelled: terciles of the trailing 500 sessions (from the earlier attempt), and terciles of all sessions (mine; descriptive only: the cut points use the whole sample, so it is not a classification a trader could have used in real time).")
    w("  5. A placebo sensitivity with a different variance clock (settings P0 and P1, section 5.3), after I found that the pre-fixed clock under-weights the first hour (`hl_trade_clock.csv`).")
    w("  6. 16 post-hoc variants (section 5) and the numbers for 16 Oct (section 8).")
    tk = TK
    w("  7. **Section 0.7 says simulated prices are 'rounded to the tick'. The placebo code does not round.** I found this while re-reading; it is a mismatch between the pre-fixed text and the code, and the main placebo results stand as run. "
      f"To see whether it matters I re-ran the first {int(tk.histories.iloc[0])} placebo histories (same seeds) with prices rounded to Rs 0.10 at today's price and compared them one by one: the null mean net return per trade moved by at most "
      f"{f(tk.paired_diff_mean_pct.abs().max(), 4)} percentage points and no placebo p-value for the variants listed moved by more than {f((tk.p_placebo_rounded - tk.p_placebo_unrounded).abs().max(), 3)} (`hl_trade_sensitivity_tick.csv`). The omission has no visible effect.")
    w("  8. The closing-price sensitivity that section 0.5 promised ('exit at Yahoo's last printed price') was run for R1, R2, R5, R6 at first; I extended it to the hourly rules R3 and R4 (`hl_trade_crosscheck.csv`).")
    w("  9. A table of the typical miss of the stored median forecasts (`hl_trade_model_miss.csv`), the placebo-versus-reality diagnostics (`hl_trade_placebo_diag.csv`), the plain-loop re-computation (`hl_trade_indepcheck.csv`) and a data cut-off guard were added.")
    w("  10. Section 3.7 (which stop-distance estimator works best, with Diebold-Mariano and Holm over 12 comparisons) and the stop distances for 16 Oct were added after the pre-fixed section; they are descriptive and not among the 31 variants (`hl_trade_stop_forecast.csv`, `hl_trade_today_stops_2026-10-16.csv`).")
    st_ok = int(ST.passed.astype(str).str.lower().eq("true").sum())
    chk(st_ok == len(ST) and bool(IC.passed.all()), "a self-test or independent check failed")
    n_info = int(ST.check.str.contains(r"\(info\)").sum())
    w(f"* **Checks that passed.** Self-test (`hl_trade_selftest.csv`, {st_ok} of {len(ST)} rows true, {len(ST) - n_info} real checks and {n_info} informational rows that are always true): the exponentially weighted scale equals the project's `sigma_ewma`; changing one session's high, low, close or hourly bars leaves every earlier trade bit-identical (daily and hourly rules); "
      "the scale and level used on session t do not change when session t's own high, low or close change; later sessions do change (positive control); the stored model levels use the same previous close as the daily file; "
      "under zero drift the placebo's mean log return per fill is within 4 standard errors of zero for R1, R2, R3, R4a, R4b, R5 and the trailing-quantile siblings of R7/R8. "
      f"**Independent re-computation** (`hl_trade_indepcheck.csv`, command `indepcheck`): the headline numbers re-typed with plain loops that call none of the study's functions: {int(IC.passed.sum())} of {len(IC)} comparisons agree "
      "(trade counts and mean returns of R1, R2, R3, R4a, R5, R6, R7 and R8 in every window, three Newey-West t and p values, open-equals-high/low counts, Final excursion quantiles, the 10:15 excursions, one Kupiec test). "
      "It checks the coding and the arithmetic, not the design, because it is my own second typing of the same rules.")
    w("* **Costs, fills, windows** are as pre-fixed in sections 0.2 and 0.5: Development (to 30 Jun 2024), Validation (to 30 Jun 2025), Final (from 1 Jul 2025), post-closing-auction slice (from 4 Aug 2026; "
      f"{nd['cas']} daily and {nh['cas']} hourly sessions); fill F0 = the extreme must trade strictly through the level, F1 = one tick (Rs 0.10) through, F2 = 0.10% through; "
      "cost 0.10% round trip, stress S1 adds 0.05% per marketable leg (market orders, stop entries, the exit at the close).")
    cav = one(EQ, window="cas")
    chk(int(cav.open_equals_prev_close) == 9 and int(cav.n_sessions) == 51, "the 9 of 51 open-equals-previous-close count changed")
    w(f"* **Closing-auction regime check**: since 4 Aug 2026 the official open equals the previous close on {int(cav.open_equals_prev_close)} of {int(cav.n_sessions)} sessions ({pc(cav.share, 1)}), against {pc(one(EQ, window='final_pre').share, 1)} "
      f"({int(one(EQ, window='final_pre').open_equals_prev_close)} of {int(one(EQ, window='final_pre').n_sessions)}) in the rest of the Final window and {pc(one(EQ, window='dev').share, 1)} in Development (`hl_trade_open_equals_prev.csv`). "
      f"That is a real change in how the day starts, but {int(cav.n_sessions)} sessions are too few to say what it does to any rule.\n")

    # ===================================================================================================================== 3. part 1
    w("## 3. Part 1 (descriptive, for risk management)\n")
    w("Everything here describes what happened; none of it is a forecast or a trading signal. Rupee figures are percent times Rs 3,428 (the 15 Oct close), so they are 'what it would be at today's price'. "
      "Daily figures use the official NSE open, high, low and close; hourly figures use Yahoo's hourly bars (section 4.9 measures how far the two sources differ).\n")
    w("### 3.1 How far the price travels from the official open (daily bars)\n")
    w("'Up' is the day's high above the open; 'down' is the day's low below the open. For a long entered at the open, 'down' is the worst drawdown you would have sat through (the maximum adverse excursion) and 'up' the best moment to take profit (the maximum favourable excursion); for a short, swap them. "
      "Cells are percent (rupees).\n")
    rows = []
    for win in ("all", "dev", "val", "final", "cas"):
        for side in ("up", "down"):
            e = one(EX, entry="open", window=win, excursion=side)
            rows.append([f"{WN[win]} (n={int(e.n)})", side] + [f"{f(e[c + '_pct'])}% ({rs(e[c + '_rs'])})" for c in ("mean", "q25", "q50", "q75", "q90", "q95")])
    w(table(["window", "side", "mean", "25th pct", "median", "75th pct", "90th pct", "95th pct"], rows))
    e1, e2 = one(EX, entry="open", window="final", excursion="up"), one(EX, entry="open", window="final", excursion="down")
    w(f"\nPlain reading (Final, n = {int(e1.n)}): on half of the sessions the high is at least Rs {rs(e1.q50_rs)} above the open and the low at least Rs {rs(e2.q50_rs)} below it; "
      f"on one session in ten the high is Rs {rs(e1.q90_rs)} or more above the open, and on one in ten the low is Rs {rs(e2.q90_rs)} or more below it. The distributions are skewed, so the mean is above the median. "
      f"The Validation year (2024-25) was far more violent (median low Rs {rs(one(EX, entry='open', window='val', excursion='down').q50_rs)} below the open) than Final.\n")

    w("### 3.2 Entering at 10:15 or later (hourly bars): how much room is left\n")
    w(f"Entry price = the close of the hourly bar shown (so '10:15' is the close of the 09:15-10:15 bar). Favourable and adverse excursions are measured on the remaining bars to 15:30, from Yahoo's hourly extremes. "
      f"Hourly sample: {nh_all_sessions} sessions in all, {nhf} in Final, {nhc} since the closing auction. Cells are percent (rupees).\n")
    rows = []
    for win in ("all", "val", "final", "cas"):
        for side in ("up", "down"):
            e = one(EX, entry="10:15", window=win, excursion=side)
            rows.append([f"{WNH[win]} (n={int(e.n)})", side] + [f"{f(e[c + '_pct'])}% ({rs(e[c + '_rs'])})" for c in ("mean", "q25", "q50", "q75", "q90", "q95")])
    w("**Entry at 10:15, full distribution:**\n")
    w(table(["window", "side", "mean", "25th pct", "median", "75th pct", "90th pct", "95th pct"], rows))
    w("\n**Later entry hours, Final window** (median and 90th percentile of the remaining room):\n")
    rows = []
    for ent in ("10:15", "11:15", "12:15", "13:15", "14:15", "15:15"):
        a, b = one(EX, entry=ent, window="final", excursion="up"), one(EX, entry=ent, window="final", excursion="down")
        rows.append([ent, f"{f(a.q50_pct)}% ({rs(a.q50_rs)})", f"{f(a.q90_pct)}% ({rs(a.q90_rs)})", f"{f(b.q50_pct)}% ({rs(b.q50_rs)})", f"{f(b.q90_pct)}% ({rs(b.q90_rs)})"])
    w(table(["entry at", "room above: median", "room above: 90th pct", "room below: median", "room below: 90th pct"], rows))
    a13, b13 = one(EX, entry="13:15", window="final", excursion="up"), one(EX, entry="13:15", window="final", excursion="down")
    a14, b14 = one(EX, entry="14:15", window="final", excursion="up"), one(EX, entry="14:15", window="final", excursion="down")
    w(f"\nPlain reading: after 13:15 the median remaining swing is only about Rs {rs(a13.q50_rs)}-{rs(b13.q50_rs)} either way, after 14:15 about Rs {rs(a14.q50_rs)}-{rs(b14.q50_rs)}, against a round-trip cost of about Rs {f(0.001 * RS, 1)} (0.10%). "
      "Late in the day there is little left to gain or lose.\n")

    w("### 3.3 Where a stop and a target of a given size get hit (entry at the official open)\n")
    w("Cells show **S** = share of sessions in which the stop was touched first, **T** = the target was touched first, **N** = neither was touched. 'Touched' means the day's extreme reached the level. "
      "A daily bar cannot tell which came first when both levels were reached on the same day, so S and T are shown as ranges (the lower end gives the ambiguous days to the other side); N is exact. "
      "The long side has the stop below the open and the target above; the short side the reverse.\n")

    def cell(r_):
        return f"S {100 * r_.p_stop_first_lo:.0f}-{100 * r_.p_stop_first_hi:.0f} / T {100 * r_.p_target_first_lo:.0f}-{100 * r_.p_target_first_hi:.0f} / N {100 * r_.neither:.0f}"

    for win, side, title in (("all", "long", "Long side, all 2019-2026"), ("final", "long", "Long side, Final window"), ("final", "short", "Short side, Final window")):
        s = STD[(STD.window == win) & (STD.regime == "all") & (STD.regime_def == "expanding") & (STD.side == side)]
        w(f"**{title}, n = {int(s.n.iloc[0])} sessions** (rows: stop size; columns: target size; in % of the open)\n")
        rows = []
        for x in (0.5, 1.0, 1.5, 2.0):
            rows.append([f"stop {x:g}% (Rs {rs(x / 100 * RS)})"] + [cell(one(s, stop_pct=x, target_pct=y)) for y in (0.5, 1.0, 1.5, 2.0)])
        w(table(["", "target 0.5%", "target 1%", "target 1.5%", "target 2%"], rows))
        w("")
    sl = STD[(STD.window == "final") & (STD.regime == "all") & (STD.regime_def == "expanding") & (STD.side == "long")]
    s12 = one(sl, stop_pct=1.0, target_pct=2.0)
    st05 = one(sl, stop_pct=0.5, target_pct=0.5)
    chk(st05.stop_touched > 0.7, "a 0.5% stop should be touched on most Final days")
    w(f"Plain reading (Final, long): a 1% stop with a 2% target from the open was stopped first in {100 * s12.p_stop_first_lo:.0f}-{100 * s12.p_stop_first_hi:.0f}% of sessions, reached its target first in {100 * s12.p_target_first_lo:.0f}-{100 * s12.p_target_first_hi:.0f}%, "
      f"and ended without either in {100 * s12.neither:.0f}%. A 0.5% stop (Rs {rs(0.005 * RS)}) was touched on {pc(st05.stop_touched)} of days: ordinary noise takes out a stop that tight on most days.\n")
    w(f"**Order resolved with the hourly bars** (Final, long side, hourly sample n = {nhf}; 'same hour' = both levels were reached inside one hourly bar, so the order is unknown). Cells: stop first / target first / same hour / neither, in %:\n")
    sh = STH[(STH.window == "final") & (STH.regime == "all") & (STH.regime_def == "expanding") & (STH.side == "long")]
    rows = []
    for x in (0.5, 1.0, 1.5, 2.0):
        row = [f"stop {x:g}%"]
        for y in (0.5, 1.0, 1.5, 2.0):
            c_ = one(sh, stop_pct=x, target_pct=y)
            row.append(f"{100 * c_.stop_first:.0f} / {100 * c_.target_first:.0f} / {100 * c_.same_bar_unknown_order:.0f} / {100 * c_.neither:.0f}")
        rows.append(row)
    w(table(["", "target 0.5%", "target 1%", "target 1.5%", "target 2%"], rows))
    w("")

    w("**By volatility regime.** Regime = tercile (lowest, middle, highest third) of the exponentially weighted close-to-close volatility known the evening before. Three definitions are shown because they disagree (the first is the pre-fixed one; the other two are post hoc):\n")
    w("* `expanding`: cut points from all earlier sessions (no look-ahead). Because volatility rose a lot in 2024-25, most recent sessions count as 'high' or 'mid'.\n"
      "* `trailing500_posthoc`: cut points from the previous 500 sessions only.\n"
      "* `fullsample_posthoc`: cut points from all sessions 2019-2026 (descriptive; uses the future to set the cut points, so it is not a rule a trader could have followed in real time, but it gives usable counts in every cell).\n")
    shr = SUM["share_sessions_by_regime_expanding_all"]
    nfe, nft, nff = SUM["n_by_regime_final_expanding"], SUM["n_by_regime_final_trailing500"], SUM["n_by_regime_final_fullsample"]
    w(f"Sessions in the Final window by regime (low / mid / high): expanding {nfe['low']} / {nfe['mid']} / {nfe['high']}; trailing-500 {nft['low']} / {nft['mid']} / {nft['high']}; full-sample {nff['low']} / {nff['mid']} / {nff['high']} "
      f"(cut points of the full-sample definition: {f(SUM['cut_low_mid_pct_fullsample'])}% and {f(SUM['cut_mid_high_pct_fullsample'])}% a day). Over all years the expanding definition gives {pc(shr['low'])} low, {pc(shr['mid'])} mid, {pc(shr['high'])} high.\n")
    pairs = [(1.0, 2.0), (1.0, 1.0), (2.0, 1.0), (0.5, 1.0)]
    rows = []
    for win, rdn, regs in (("final", "fullsample_posthoc", ("low", "mid", "high")), ("all", "fullsample_posthoc", ("low", "mid", "high")), ("all", "expanding", ("low", "mid", "high")), ("final", "expanding", ("low", "mid", "high")),
                           ("all", "trailing500_posthoc", ("low", "mid", "high")), ("final", "trailing500_posthoc", ("low", "mid", "high"))):
        for reg in regs:
            s = STD[(STD.window == win) & (STD.regime == reg) & (STD.regime_def == rdn) & (STD.side == "long")]
            if len(s) == 0 or int(s.n.iloc[0]) == 0:
                rows.append([f"{WN[win]}, {rdn}, {reg}", 0] + ["no sessions"] * len(pairs))
                continue
            rows.append([f"{WN[win]}, {rdn}, {reg}", int(s.n.iloc[0])] + [cell(one(s, stop_pct=x, target_pct=y)) for x, y in pairs])
    w(table(["sample (long side)", "n", "stop 1% / target 2%", "stop 1% / target 1%", "stop 2% / target 1%", "stop 0.5% / target 1%"], rows))
    w("\nWhere n is under about 30 the cell is an anecdote (for example the 'low' regime of the expanding definition in Final). The robust, non-controversial pattern is that busier regimes have wider swings (next table), so the same stop is touched more often.\n")
    w("**Size of the swing by regime** (full-sample terciles; median and 90th percentile of the day's high above / low below the open; percent (rupees at Rs 3,428)):\n")
    rows = []
    for win in ("all", "final"):
        for reg in ("low", "mid", "high"):
            a, b = one(EX, entry=f"open|regime={reg}|fullsample_posthoc", window=win, excursion="up"), one(EX, entry=f"open|regime={reg}|fullsample_posthoc", window=win, excursion="down")
            rows.append([WN[win], reg, int(a.n), f"{f(a.q50_pct)}% ({rs(a.q50_rs)})", f"{f(a.q90_pct)}% ({rs(a.q90_rs)})", f"{f(b.q50_pct)}% ({rs(b.q50_rs)})", f"{f(b.q90_pct)}% ({rs(b.q90_rs)})"])
    w(table(["window", "regime", "n", "high above open: median", "high: 90th pct", "low below open: median", "low: 90th pct"], rows))
    lo_, hi_ = one(EX, entry="open|regime=low|fullsample_posthoc", window="all", excursion="down"), one(EX, entry="open|regime=high|fullsample_posthoc", window="all", excursion="down")
    chk(hi_.q50_pct > 1.5 * lo_.q50_pct, "high-volatility days should have clearly larger swings than low-volatility days")
    w(f"\n**Which regime is Friday 16 Oct?** The scale going into 16 Oct is {f(TJ['ewma_scales_for_16oct_pct']['sigR'])}% a day: **{SUM['regime_for_16oct_expanding']}** by the pre-fixed expanding definition, **{SUM['regime_for_16oct_fullsample']}** by the full-sample one, "
      f"**{SUM['regime_for_16oct_trailing500']}** by the trailing-500 one (cut points {f(SUM['cut_low_mid_pct_trailing500'])}% and {f(SUM['cut_mid_high_pct_trailing500'])}%, because 2024-25 was so volatile). "
      "Two of three definitions say 'mid'; the disagreement is a warning that the regime label is a matter of definition. The Final-window rows are the fair guide for the 16 Oct session.\n")

    w("### 3.4 Is the open, or the first hour, the high or the low of the day?\n")
    w("The project's earlier finding (research/v2/05_intraday_structure.md) was that 83.8% (31 of 37) of post-closing-auction sessions had their high or low in the first hour, and that a random walk with the same U-shaped variance profile gives 84.9%, so it is not a pattern. "
      "Here is the larger-sample check, with the placebo (histories with the real variance profile; setting A = the pre-fixed clock, P0 = a pooled clock, section 5.3). 'High or low in first hour' counts a session if either extreme falls in the 09:15-10:15 bar.\n")
    rows = []
    for win in ("all", "val", "final", "cas"):
        o = one(OH, source="hourly bars", window=win)
        a, p0 = one(OHC, placebo_setting="A", window=win), one(OHC, placebo_setting="P0", window=win)
        rows.append([WNH[win], int(o.n), f"{pc(o.high_or_low_in_first_hour, 1)} ({int(o.k_high_or_low_first_hour)})", f"{pc(a.sim_mean, 1)} ({pc(a.sim_5pct, 0)}-{pc(a.sim_95pct, 0)})", pv(a.p_two_sided),
                     f"{pc(p0.sim_mean, 1)} ({pc(p0.sim_5pct, 0)}-{pc(p0.sim_95pct, 0)})", pv(p0.p_two_sided), pc(o.high_and_low_in_first_hour, 1), pc(p0.sim_high_and_low_first_hour, 1)])
    w(table(["window", "hourly sessions", "observed: high or low in first hour (count)", "placebo A: mean (5-95%)", "p (two-sided)", "placebo P0: mean (5-95%)", "p (two-sided)", "observed: BOTH in first hour", "placebo P0: both"], rows))
    oall, ofin, ocas = one(OH, source="hourly bars", window="all"), one(OH, source="hourly bars", window="final"), one(OH, source="hourly bars", window="cas")
    pa, pp0 = one(OHC, placebo_setting="A", window="all"), one(OHC, placebo_setting="P0", window="all")
    chk(abs(ocas.high_or_low_in_first_hour - 35 / 42) < 1e-9, "post-auction first-hour count changed")
    w(f"\nPlain reading: {pc(ocas.high_or_low_in_first_hour, 1)} ({int(ocas.k_high_or_low_first_hour)} of {int(ocas.n)}) of post-auction sessions had the high or the low in the first hour (the project's 31 of 37 is {pc(31 / 37, 1)}), "
      f"{pc(ofin.high_or_low_in_first_hour, 1)} in Final and {pc(oall.high_or_low_in_first_hour, 1)} in all {int(oall.n)} hourly sessions. A random walk with the same variance profile gives {pc(pa.sim_mean, 1)} (pre-fixed clock) to {pc(pp0.sim_mean, 1)} (pooled clock). "
      "The observed share sits between the two, so this is **not a pattern you can trade**: the first hour simply carries a large part of the day's variance. The exact verdict depends on how the profile is estimated (section 5.3). "
      f"One honest wrinkle: days on which BOTH extremes fall in the first hour are more frequent in the data ({pc(oall.high_and_low_in_first_hour, 1)}) than in the placebo ({pc(pa.sim_high_and_low_first_hour, 1)} to {pc(pp0.sim_high_and_low_first_hour, 1)}); real days are lumpier than the simulation, which is a limit of the placebo (section 6).\n")
    oo = {k: one(OH, source="daily official", window=k) for k in ("all", "final", "cas")}
    w(f"**The open itself** (the official NSE open, which is the pre-open call-auction price): it is the day's high in {pc(oo['all'].open_is_high, 1)} and the day's low in {pc(oo['all'].open_is_low, 1)} of all {int(oo['all'].n)} sessions "
      f"({pc(oo['all'].open_is_high_or_low, 1)} either; {int(oo['all'].k_open_high)} and {int(oo['all'].k_open_low)} sessions), {pc(oo['final'].open_is_high_or_low, 1)} in Final (n = {int(oo['final'].n)}) and {pc(oo['cas'].open_is_high_or_low, 1)} since the closing auction (n = {int(oo['cas'].n)}). "
      f"The placebo cannot say anything about this (it gives {pc(one(OHP, placebo_setting='A', window='all').sim_open_is_high, 2)}), because its paths are continuous and the real open is an auction print, not the first trade of a path; so I report it as a fact and not as a pattern or a non-pattern: "
      f"on about one session in {1 / oo['all'].open_is_high_or_low:.0f} over all years, and one in {1 / oo['final'].open_is_high_or_low:.0f} in Final, no price after the open ever improves on the open on one side.\n")
    eb = EB[EB.window == "final"]
    w(f"**Hour by hour (Final, hourly sample n = {nhf}):** the share of sessions whose high falls in each hourly bar is "
      + ", ".join(f"{r_.bar_start} {pc(r_.share_high_in_bar)}" for r_ in eb.itertuples()) + "; for the low "
      + ", ".join(f"{r_.bar_start} {pc(r_.share_low_in_bar)}" for r_ in eb.itertuples()) + ". The extremes cluster at the start and at the end (the 14:15 and 15:15 bars), the usual U-shape.\n")

    w("### 3.5 How much of the day's range is already in place\n")
    w(f"Share of sessions in which the day's final high (low) has already been printed by the time shown, Final window (hourly sample, n = {nhf}), and the median share of the final range already formed.\n")
    rows = []
    for k in RF[RF.window == "final"].itertuples():
        rows.append([k.clock, pc(k.high_already_final), pc(k.low_already_final), pc(k.both_already_final), pc(k.median_share_of_range_formed)])
    w(table(["by", "final high already set", "final low already set", "both already set", "median share of range formed"], rows))
    r1415, r1515 = one(RF, window="final", clock="14:15"), one(RF, window="final", clock="15:15")
    chk(0.7 < r1415.high_already_final < 0.85 and r1515.high_already_final > 0.88 and 0.45 < r1415.both_already_final < 0.6, "range-formed wording")
    w(f"\nPlain reading: by 14:15 the day's high is already in for {pc(r1415.high_already_final)} of sessions and the low for {pc(r1415.low_already_final)}, both extremes for {pc(r1415.both_already_final)}; by 15:15 for {pc(r1515.high_already_final)}, {pc(r1515.low_already_final)} and {pc(r1515.both_already_final)}. "
      "A fresh high or low late in the day is a minority event.\n")

    w("### 3.6 Placing a stop from the trailing history (walk-forward)\n")
    w("Stop distance = the trailing 250-session empirical quantile q of the adverse excursion from the open (sessions before the day only). If the history were a perfect guide, the stop would be touched on a share 1 - q of days. "
      "Kupiec tests whether the observed share equals the nominal one (a small p means it does not).\n")
    rows = []
    for win in ("all", "dev", "val", "final", "cas"):
        for side in ("long", "short"):
            for q in (0.5, 0.75, 0.9):
                c = one(SC, side=side, stop_quantile=q, window=win)
                rows.append([WN[win], side, f"{int(q * 100)}th pct", int(c.n), f"{f(c.mean_stop_distance_pct)}% (Rs {rs(c.mean_stop_distance_rs)})", pc(c.nominal_stop_touched), pc(c.observed_stop_touched, 1), pv(c.kupiec_p)])
    w(table(["window", "side", "stop at trailing", "n", "average stop distance", "nominal touch", "observed touch", "Kupiec p"], rows))
    l90f, s90f, l90d, s90d = one(SC, side="long", stop_quantile=0.9, window="final"), one(SC, side="short", stop_quantile=0.9, window="final"), one(SC, side="long", stop_quantile=0.9, window="dev"), one(SC, side="short", stop_quantile=0.9, window="dev")
    chk(l90f.observed_stop_touched < 0.08 and s90f.observed_stop_touched < 0.08 and l90d.observed_stop_touched > 0.11 and s90d.observed_stop_touched > 0.11, "stop-calibration wording")
    w(f"\nPlain reading: the trailing history is a decent guide but not a precise one. In Final the stops at the 90th percentile were touched less often than nominal ({pc(l90f.observed_stop_touched, 1)} long and {pc(s90f.observed_stop_touched, 1)} short against 10%; Kupiec p {pv(l90f.kupiec_p)} and {pv(s90f.kupiec_p)}) "
      f"probably because the Final window is calmer than the earlier years that dominate a 250-session history; in the Development window they were touched more often ({pc(l90d.observed_stop_touched, 1)} and {pc(s90d.observed_stop_touched, 1)}; p {pv(l90d.kupiec_p)} and {pv(s90d.kupiec_p)}). "
      f"Expect the realised touch frequency to be within about five percentage points of the nominal one (the largest gap in Final was {f(float(((SC[SC.window == 'final'].observed_stop_touched - SC[SC.window == 'final'].nominal_stop_touched).abs() * 100).max()), 1)} points), not exactly equal.\n")

    w("### 3.7 Which estimate of the stop distance works best? (added after the pre-fixed section; descriptive)\n")
    w("Same question as 3.6 with two more candidates, forecast from earlier sessions only. **T250** = the trailing-250-session quantile of 3.6. **EXPANDING** = the quantile of all earlier sessions (a constant scale: it ignores whether the market is calm or wild). "
      "**EWMA_SCALED** = the recent volatility of the day's swing (exponentially weighted, lambda 0.94, known the evening before) times the all-history quantile of the swing measured in units of that volatility. "
      "Scored by pinball loss (the standard loss for a quantile forecast; lower is better, in percent of price), by how often the stop was touched against the promised share (Kupiec), and by Diebold-Mariano against T250 "
      "(Holm over the 12 comparisons of each window). This is a small side study with a family of 12 tests, not one of the 31 variants.\n")
    rows = []
    for side in ("long", "short"):
        for q in (0.5, 0.75, 0.9):
            for m_ in ("T250", "EXPANDING", "EWMA_SCALED"):
                row = [side, f"{int(q * 100)}th pct", m_]
                for win in ("all", "final"):
                    c_ = one(SF, side=side, stop_quantile=q, method=m_, window=win)
                    row += [f"{pc(c_.touch_freq, 1)} (p {pv(c_.kupiec_p)})", f(c_.mean_pinball_pct_of_price, 3), "-" if m_ == "T250" else f"t {f(c_.dm_t_vs_T250, 1)} (Holm {f(c_.holm_one_sided_12, 2)})"]
                rows.append(row)
    nall, nfin = int(one(SF, side="long", stop_quantile=0.5, method="T250", window="all").n), int(one(SF, side="long", stop_quantile=0.5, method="T250", window="final").n)
    w(table(["side", "stop at", "method", f"all years (n={nall}): touched (Kupiec p)", "pinball", "DM vs T250", f"Final (n={nfin}): touched (Kupiec p)", "pinball ", "DM vs T250 "], rows))
    sfa = SF[(SF.window == "all") & (SF.method == "EXPANDING")]
    sfe = SF[(SF.window == "all") & (SF.method == "EWMA_SCALED")]
    sft = SF[(SF.window == "all") & (SF.method == "T250")].set_index(["side", "stop_quantile"])
    sff = SF[(SF.window == "final") & (SF.method != "T250")]
    chk((sfa.kupiec_p < 0.001).all() and (sfa.touch_freq > sfa.nominal_touch).all(), "EXPANDING stops should be too tight in every all-years cell")
    chk(all(r_.mean_pinball_pct_of_price < sft.loc[(r_.side, r_.stop_quantile)].mean_pinball_pct_of_price for r_ in sfe.itertuples()), "EWMA_SCALED should have the lowest pinball loss of the two in the all-years window")
    n_sig = int((sfe.holm_one_sided_12 < 0.05).sum())
    e_hi = sfe[sfe.stop_quantile >= 0.75]
    chk((e_hi.kupiec_p > 0.2).all(), "EWMA_SCALED 75% / 90% stops should be well calibrated over all years")
    chk((sff.holm_one_sided_12 > 0.05).all(), "no alternative should beat T250 in Final")
    chk((SF[(SF.window.isin(["val", "final", "cas"])) & (SF.method != "T250")].holm_one_sided_12 > 0.05).all(), "no alternative should beat T250 significantly after Dev")
    chk((SF[(SF.window == "dev") & (SF.method == "EWMA_SCALED") & (SF.holm_one_sided_12 < 0.05)].shape[0]) >= 3, "EWMA_SCALED should beat T250 in the Development window")
    mx_dev = float(((SF[SF.window == "final"].touch_freq - SF[SF.window == "final"].nominal_touch).abs() * 100).max())
    f90 = SF[(SF.window == "final") & (SF.stop_quantile == 0.9)].set_index(["side", "method"])
    f75s = one(SF, side="short", stop_quantile=0.75, method="EWMA_SCALED", window="final")
    w(f"\nPlain reading: (1) the constant-scale stop (EXPANDING) is too tight in every case over 2019-2026, because it ignores that the market has been far busier at times: its stops were touched on {pc(sfa.touch_freq.min())}-{pc(sfa.touch_freq.max())} of days against promised {pc(sfa.nominal_touch.min())}-{pc(sfa.nominal_touch.max())} (Kupiec p < 0.001 each). "
      f"(2) Scaling by recent volatility (EWMA_SCALED) had a lower pinball loss than T250 in all six side-and-level combinations over 2019-2026, significantly so (Holm-adjusted p < 0.05) in {n_sig} of them (two of those only just: {f(sfe[sfe.holm_one_sided_12 < 0.05].holm_one_sided_12.max(), 3)}), all of it coming from the Development years (to mid-2024; in Validation and Final no gain is significant), and its 75% and 90% stops were touched about as often as promised (Kupiec p above 0.2 in all four). "
      f"(3) In the Final window nothing beat T250 (smallest Holm p {f(sff.holm_one_sided_12.min(), 2)}). T250's 90% stops were touched on {pc(f90.loc[('long', 'T250')].touch_freq, 1)} (long) and {pc(f90.loc[('short', 'T250')].touch_freq, 1)} (short) of Final days against 10%, "
      f"EWMA_SCALED's on {pc(f90.loc[('long', 'EWMA_SCALED')].touch_freq, 1)} and {pc(f90.loc[('short', 'EWMA_SCALED')].touch_freq, 1)}; but EWMA_SCALED's 75% short stops were touched on {pc(f75s.touch_freq, 1)} of Final days against 25% (p {pv(f75s.kupiec_p)}). "
      "In words: after a wild year the trailing-year history sets stops too wide, and a volatility-scaled stop corrects most of that; no method was clearly best in the last fifteen months, so treat any single stop distance as good to within roughly five to seven percentage points of the promised touch rate (the largest deviation in Final was {f(mx_dev, 1)} points), and do not read the difference between T250 and EWMA_SCALED as proven.\n")

    # ===================================================================================================================== 4. part 2
    w("## 4. Part 2 (inferential): do rules that trade the levels make money after costs?\n")
    w("Method exactly as in section 0 (31 variants, walk-forward past-only scales, F0/F1/F2 fills, 0.10% cost, Newey-West p, Holm over the 31 variants per window and fill convention, a placebo in two drift settings, Diebold-Mariano and Kupiec for the model-level rules). "
      "Net = gross minus 0.10%. **Hourly rules (R3, R4) have no Development window** (the hourly file starts in Oct 2024) and their Validation window is Dec 2024 - Jun 2025 (the first-hour scale needs 40 sessions to start).\n")
    w("### 4.1 Primary variants: Final window in detail, and which verdict conditions failed\n")
    rows = []
    for k, v in PRIM.items():
        a = fin[k]
        rows.append([k, v, int(a.n_sessions), int(a.n_trades), pc(a.fill_rate), sg(a.mean_gross_pct), sg(a.mean_net_pct), rs(a.mean_net_rs, True), pc(a.win_rate), pv(a.p_hac_net), f(a.holm_hac, 2),
                     f(a.p_placebo_A, 3) if not pd.isna(a.p_placebo_A) else "none", f(a.p_placebo_B, 3) if not pd.isna(a.p_placebo_B) else "none", f(a.mde_80pct_power_pct)])
    w(table(["rule", "variant", "sessions", "trades", "fill rate", "gross %", "net %", "net Rs", "win rate", "p HAC", "Holm p", "placebo p (A)", "placebo p (B)", "MDE % (80% power)"], rows))
    w("\nMDE = the smallest true mean net return per trade that would be detected with 80% power at one-sided 5% (2.49 times the Newey-West standard error). Placebo p = share of simulated no-edge histories whose net mean is at least the observed one; A = zero drift, B = drift matched to the window.\n")
    ck = {"cond_final_net_pos_and_holm": "Final net > 0 and Holm p < 0.05", "cond_placebo_both": "Holm placebo p < 0.05 (A and B)", "cond_val_dev_net_pos": "net > 0 in Validation (and Development)",
          "cond_F1_net_pos": "net > 0 with 1-tick fill", "cond_cas_not_sig_neg": "post-auction slice not significantly negative"}
    mk = lambda b_: "yes" if bool(b_) else "NO"
    rows = [[r_.rule, r_.primary_variant] + [mk(getattr(r_, c)) for c in ck] + ["not possible (no placebo)" if r_.model_variant_no_placebo else "possible", f"**{r_.verdict}**"] for r_ in V.itertuples()]
    w("The verdict is **validated** only if every condition below holds (fixed in 0.6):\n")
    w(table(["rule", "variant"] + list(ck.values()) + ["placebo available", "verdict"], rows))
    w("\n**descriptive** = gross mean above zero with unadjusted p < 0.05 in some window, or net above zero in Final without meeting every condition; it means 'something happened in this sample', not 'tradable'. **not found** = anything else.\n")

    w("### 4.2 Primary variants across the four windows (net % per trade; number of trades in brackets)\n")
    rows = []
    for k, v in PRIM.items():
        row = [k, v]
        for win in ("dev", "val", "final", "cas"):
            sub_ = HM0[(HM0.variant == v) & (HM0.window == win)]
            a = sub_.iloc[0] if len(sub_) else None
            row.append("no hourly data" if a is None else (f"{sg(a.mean_net_pct)} ({int(a.n_trades)})" + (" p=" + pv(a.p_hac_net) if win in ("val", "final") and not pd.isna(a.p_hac_net) else "")))
        rows.append(row)
    w(table(["rule", "variant", "Development", "Validation", "Final", "post-closing-auction"], rows))
    w(f"\nThe post-closing-auction slice has {nd['cas']} daily and {nhc} hourly sessions; most cells there have 5-35 trades, and no p-value is shown below the 10-trade floor. It is a check for gross failure, not a test.\n")

    w("### 4.3 All 31 variants, Final window, strict fill (F0)\n")
    rows = []
    for v in list(R0[R0.window == "final"].variant):
        a = one(HM0, variant=v, window="final")
        rows.append([v, int(a.n_trades), pc(a.fill_rate), sg(a.mean_gross_pct), sg(a.mean_net_pct), sg(a.mean_net_s1_pct), pv(a.p_hac_net), f(a.holm_hac, 2),
                     f(a.p_placebo_A, 3) if not pd.isna(a.p_placebo_A) else "none", f(a.p_placebo_B, 3) if not pd.isna(a.p_placebo_B) else "none"])
    w(table(["variant", "trades", "fill rate", "gross %", "net %", "net % with 0.05% extra per marketable leg", "p HAC", "Holm p", "placebo p A", "placebo p B"], rows))
    fin_all = HM0[(HM0.window == "final") & HM0.variant.isin(R0[R0.window == "final"].variant)]
    chk((fin_all.holm_hac >= 0.999).all(), "some variant has a Holm p below 1 in Final")
    pos_ = fin_all[fin_all.mean_net_pct > 0]
    w(f"\nNo variant has a Holm-adjusted p below 1.0 in the Final window. {len(pos_)} of the {len(fin_all)} variants have a positive net mean ({', '.join(pos_.sort_values('p_hac_net').variant)}); the smallest unadjusted p among them is {pv(pos_.p_hac_net.min())}. "
      "Windows other than Final, fill conventions F1 and F2, and every statistic are in `hl_trade_holm.csv` and `hl_trade_rules.csv`; the table in Appendix A gives net % and trades for every variant in every window.\n")

    w("### 4.4 By calendar year (primary variants, net % per trade, trades in brackets, F0)\n")
    yrs = sorted(BY.year.unique())
    rows = []
    npos = {}
    for k, v in PRIM.items():
        row = [k, v]
        pos_y = tot_y = 0
        for y in yrs:
            s = BY[(BY.variant == v) & (BY.year == y)]
            if len(s) == 0 or s.n_trades.iloc[0] == 0:
                row.append("-")
            else:
                row.append(f"{sg(s.mean_net_pct.iloc[0])} ({int(s.n_trades.iloc[0])})")
                tot_y += 1
                pos_y += int(s.mean_net_pct.iloc[0] > 0)
        npos[k] = (pos_y, tot_y)
        rows.append(row)
    w(table(["rule", "variant"] + [str(y) + (" (to 15 Oct)" if y == 2026 else "") for y in yrs], rows))
    chk(all(npos[k][0] * 2 < npos[k][1] for k in PRIM if k != "R4"), "a rule other than R4 is positive in most years")
    chk(BY[(BY.variant == "R4a") & (BY.year == 2026)].mean_net_pct.iloc[0] < 0.1 < BY[(BY.variant == "R4a") & (BY.year == 2025)].mean_net_pct.iloc[0], "R4a should fade from 2025 to 2026")
    w("\nYears in which the net mean was positive: " + ", ".join(f"{k} {npos[k][0]} of {npos[k][1]}" for k in PRIM) + ". "
      "R4 has data only for late 2024 to 2026 and fades in 2026. Years with 45-70 trades have a standard error of 0.15-0.3% per year, so single-year differences are mostly noise.\n")

    w("### 4.5 Fill conventions and cost stress (Final, net % per trade, trades in brackets)\n")
    rows = []
    for k, v in PRIM.items():
        row = [k, v]
        for m_ in (0, 1, 2):
            a = one(R, variant=v, window="final", fill_mode=m_)
            row.append(f"{sg(a.mean_net_pct)} ({int(a.n_trades)})")
        a0 = one(R, variant=v, window="final", fill_mode=0)
        row.append(sg(a0.mean_net_s1_pct))
        row.append(sg(a0.mean_gross_pct))
        rows.append(row)
    w(table(["rule", "variant", "F0: strictly through", "F1: one tick through", "F2: 0.10% through", "F0 with extra 0.05% per marketable leg", "F0 gross (no cost)"], rows))
    r4_f0, r4_f2 = one(R, variant="R4a", window="final", fill_mode=0), one(R, variant="R4a", window="final", fill_mode=2)
    w("\n**Do not read F2 for the stop-entry rule R4a as a conservative case.** F2 keeps only breakouts that went at least 0.10% beyond the range, yet assumes the fill at the range edge; "
      "that selects trades by what the price did after entry, which flatters a breakout rule (R4a net rises from "
      f"{sg(r4_f0.mean_net_pct)}% to {sg(r4_f2.mean_net_pct)}%, p {peq(r4_f2.p_hac_net)} unadjusted). "
      "A real stop order would have been filled on the marginal breakouts too, and those are the ones that fail. F2 is a fair stress only for resting limit orders (R1, R2, R7, R8), where it makes results worse, as the table shows. "
      "The pre-fixed verdict uses F0 for the test and F1 for the robustness condition, so this does not touch any verdict.\n")

    w("### 4.6 What a rule with no edge looks like (placebo)\n")
    w(f"{SUM['placebo_reps_per_setting']:,} simulated random-walk histories per setting (same dates, same past-only scale estimators, same variance profile across the day, same fill rules, same 0.10% cost). Final window, F0. "
      "'Null' = the distribution, over the simulated histories, of the net mean per trade. The per-trade standard deviations are shown so that the simulated and the real trades can be compared.\n")
    rows = []
    for k, v in PRIM.items():
        a = fin[k]
        if pd.isna(a.null_mean_net_pct_A):
            rows.append([k, v, sg(a.mean_net_pct), "none (model quantiles cannot be re-fitted inside a simulation)", "", "", "", "", ""])
            continue
        rows.append([k, v, sg(a.mean_net_pct), sg(a.null_mean_net_pct_A), f(a.null_sd_net_pct_A), sg(a.null_q95_net_pct_A), sg(a.null_q95_net_pct_B), f"{a.null_mean_trades_A:.0f} vs {int(a.n_trades)}", f"{f(a.null_trade_sd_pct_A)} vs {f(a.sd_net_pct)}"])
    w(table(["rule", "variant", "observed net %", "null mean net % (A)", "null sd of the mean (A)", "null 95th pct (A)", "null 95th pct (B)", "mean simulated trades vs real trades", "per-trade sd %: simulated vs real"], rows))
    nulls = [fin[k].null_mean_net_pct_A for k in PRIM if not pd.isna(fin[k].null_mean_net_pct_A) and k != "R6"]
    chk(min(nulls) > -0.2 and max(nulls) < -0.05, "placebo null means should sit near minus the cost")
    q95s = [fin[k].null_q95_net_pct_A for k in ("R1", "R2", "R3", "R5")]
    gr_ = [fin[k].null_mean_gross_pct_A for k in ("R1", "R2", "R5")]
    chk(max(abs(x) for x in gr_) < 0.05, "fill-conditional selection produced a visible gross edge in the placebo")
    r6n = fin["R6"].null_mean_net_pct_A
    w(f"\nPlain reading: a rule with no edge earns roughly minus the cost ({f(min(nulls))}% to {f(max(nulls))}% net for the single-fill limit and entry rules; the fixed bracket R6 sits near {f(r6n)}% because the conservative 'stop first when both levels are touched' reading is pessimistic by construction). "
      f"**Fill-conditional selection did not manufacture an edge here**: the simulated gross mean per fill is within {f(max(abs(x) for x in gr_), 3)} percentage points of zero for R1, R2 and R5 (`hl_trade_holm.csv`, column `null_mean_gross_pct_A`). "
      f"The luck range matters more than any bias: with {min(fin[k].null_mean_trades_A for k in ('R1', 'R2', 'R3', 'R5')):.0f}-{max(fin[k].null_mean_trades_A for k in ('R1', 'R2', 'R3', 'R5')):.0f} trades a pure-noise rule has a 95th percentile of {sg(min(q95s))}% to {sg(max(q95s))}% net per trade, so a single window showing +0.2% means nothing. "
      "The R6 placebo p-values must not be read as evidence: the placebo's days are more two-sided than real days (section 6), which makes the conservative reading look worse in the simulation than in the data; "
      f"the short 1%/2% bracket has a placebo p of {f(one(HM0, variant='R6_short_s1_t2', window='final').p_placebo_A, 3)} in Final while its observed net mean is {sg(one(HM0, variant='R6_short_s1_t2', window='final').mean_net_pct)}% (Newey-West p {f(one(HM0, variant='R6_short_s1_t2', window='final').p_hac_net, 2)}); it lost money.\n")

    w("### 4.7 The project's estimated levels against a plain trailing-quantile level (R7/R8 versus the 250-session empirical quantile)\n")
    w("Diebold-Mariano (Harvey-Leybourne-Newbold, lag 5) on the daily net profit and loss of the limit order at the model's post-open quantile versus the same order at the trailing-250-session empirical quantile of the same variable; no-fill days count as zero. "
      "Positive DM t means the model level did better. Kupiec tests whether the fill frequency matches the promised quantile. The profit-and-loss differences are sparse and heavy-tailed, so treat the t values as indicative.\n")
    rows = []
    for pair in (("R7_post_q25", "R7_emp_q25"), ("R7_post_q10", "R7_emp_q10"), ("R8_post_q75", "R8_emp_q75"), ("R8_post_q90", "R8_emp_q90")):
        for win in ("final", "cas"):
            d_ = one(DM, model_variant=pair[0], benchmark=pair[1], window=win)
            km, ke = one(KU, variant=pair[0], window=win), one(KU, variant=pair[1], window=win)
            rows.append([pair[0], pair[1], WN[win], int(d_.n), sg(d_.mean_daily_net_pnl_model_pct, 3), sg(d_.mean_daily_net_pnl_bench_pct, 3), f(d_.dm_t, 2), pv(d_.p_two_sided), pv(d_.holm_two_sided_over_all_rows),
                         f"{pc(km.observed_fill, 1)} (p {f(km.kupiec_p, 2)})", f"{pc(ke.observed_fill, 1)} (p {f(ke.kupiec_p, 2)})", pc(km.nominal_fill)])
    w(table(["model variant", "benchmark", "window", "days", "model: mean daily net P&L %", "benchmark: mean daily net P&L %", "DM t", "p (two-sided)", f"Holm p (all {len(DM)} rows)", "model fill rate (Kupiec p)", "benchmark fill rate (Kupiec p)", "promised"], rows))
    post = KU[KU.variant.str.contains("_post_")]
    bad = KU[KU.variant.str.contains("_pre_|_post_") & (KU.kupiec_p < 0.05)]
    emp_bad = KU[KU.variant.str.contains("_emp_") & (KU.kupiec_p < 0.05)]
    d25 = one(DM, model_variant="R7_post_q25", benchmark="R7_emp_q25", window="final")
    d25c = one(DM, model_variant="R7_post_q25", benchmark="R7_emp_q25", window="cas")
    chk(post.kupiec_p.min() > 0.05 and d25.dm_t < -2, "DM / Kupiec wording")
    chk((DM[DM.window == "final"].mean_daily_net_pnl_model_pct < 0).all() and (DM[DM.window == "final"].mean_daily_net_pnl_bench_pct < 0).all(), "a Final-window order made money on average")
    pre_bad = bad[bad.variant.str.contains("_pre_")]
    pre_txt = ("; among the pre-open model levels only " + ", ".join(f"{r_.variant} in the {WN[r_.window]} slice ({pc(r_.observed_fill, 1)} against {pc(r_.nominal_fill)}, n = {int(r_.n)}, p = {f(r_.kupiec_p, 3)})" for r_ in pre_bad.itertuples()) + " departs") if len(pre_bad) else "; no pre-open model level departs either"
    w(f"\nPlain reading: (1) the model's post-open levels are touched about as often as promised in every window (smallest Kupiec p {f(post.kupiec_p.min(), 2)})" + pre_txt
      + f". The trailing-quantile benchmark is off more often ({len(emp_bad)} of {len(KU[KU.variant.str.contains('_emp_')])} variant-window cells have p < 0.05: {int((emp_bad.window == 'dev').sum())} in the Development window and {int((emp_bad.window == 'final').sum())} in Final; its 10% and 90% levels were touched on only 6-7% of Final days against 10%). "
      f"(2) In Final neither the model's nor the benchmark's resting orders made money (every mean daily net P&L in the Final rows above is negative); the positive means in the 51-day slice rest on 5-16 fills each. (3) For the 25% low order the model level did **worse** than the plain trailing quantile in Final (DM t = {f(d25.dm_t, 1)}, Holm p {peq(d25.holm_two_sided_over_all_rows)}, {int(d25.n)} days) "
      f"and in the post-auction slice (t = {f(d25c.dm_t, 1)}, Holm p {peq(d25c.holm_two_sided_over_all_rows)}, {int(d25c.n)} days); for the other three pairs there is no difference. "
      "This is about the profit and loss of an order, not about the accuracy of the quantile (pinball loss and coverage of the levels themselves are specialist A's tables).\n")

    w("### 4.8 Fixed brackets from the open (R6): does the order of events matter?\n")
    w(f"On the hourly sample (n = {nh_all_sessions}; {nhf} in Final) the order of the stop and the target can be resolved whenever they fall in different hours. Net % per session, stop and target as shown (same-hour conflicts scored stop-first in the resolved column).\n")
    rows = []
    for v in ("R6_long_s1_t2", "R6_long_s2_t1", "R6_short_s1_t2", "R6_short_s2_t1"):
        for win in ("final", "cas"):
            b = one(BO, variant=v, window=win)
            rows.append([v, WN[win], int(b.n), pc(b.share_both_levels_touched, 1), pc(b.share_both_same_bar, 1), sg(b.mean_net_pct_conservative), sg(b.mean_net_pct_hourly_resolved), sg(b.mean_net_pct_optimistic)])
    w(table(["bracket", "window", "sessions", "both levels touched", "both in the same hour", "net % conservative (stop first)", "net % hourly-resolved", "net % optimistic (target first)"], rows))
    bf = BO[BO.window == "final"]
    nneg = int((bf.mean_net_pct_hourly_resolved < 0).sum())
    pos_b = bf[bf.mean_net_pct_hourly_resolved >= 0]
    chk(nneg == 3 and len(bf) == 4 and len(pos_b) == 1, "bracket count wording")
    w(f"\nThe hourly-resolved result lies between the two bounds and is negative for {nneg} of the {len(bf)} brackets in Final (the exception is {pos_b.variant.iloc[0]} at {sg(pos_b.mean_net_pct_hourly_resolved.iloc[0])}%, n = {int(pos_b.n.iloc[0])}, which is not distinguishable from zero). "
      "A trader who 'always uses a bracket from the open' paid the cost and got nothing in return. "
      f"The result depends on the ordering convention by more than the whole cost: in Final the conservative and optimistic readings differ by {f((bf.mean_net_pct_optimistic - bf.mean_net_pct_conservative).min())}-{f((bf.mean_net_pct_optimistic - bf.mean_net_pct_conservative).max())} percentage points against a cost of 0.10.\n")

    w("### 4.9 Does the choice of price source matter? (Yahoo against the official NSE bars)\n")
    w("The hourly file is Yahoo's; the daily file is NSE's official bar. Differences in rupees, Yahoo minus NSE, same sessions:\n")
    rows = []
    for q_ in DC.itertuples():
        if str(q_.quantity).startswith("ratio"):
            continue
        rows.append([q_.quantity, int(q_.n), f(q_.mean_rs, 1), f(q_.mean_abs_rs, 1), f(q_.p90_abs_rs, 1), f(q_.p99_abs_rs, 1), f(q_.max_abs_rs, 1), pc(q_.share_abs_gt_5)])
    w(table(["quantity", "n", "mean Rs", "mean absolute Rs", "90th pct of absolute", "99th pct of absolute", "max absolute", "share above Rs 5"], rows))
    dh, dl = one(DC, quantity="Yahoo hourly high minus NSE official high, all hourly sessions"), one(DC, quantity="Yahoo hourly low minus NSE official low, all hourly sessions")
    do = one(DC, quantity="Yahoo first printed open minus NSE official open, all hourly sessions")
    dcl = one(DC, quantity="Yahoo last-bar close minus NSE official close, all hourly sessions")
    dcc = one(DC, quantity="Yahoo last-bar close minus NSE official close, closing-auction slice")
    w(f"\nPlain reading: Yahoo's hourly high is on average Rs {f(-dh.mean_rs, 1)} below NSE's official high and Yahoo's low Rs {f(dl.mean_rs, 1)} above NSE's official low (Yahoo's range is about Rs {f(-dh.mean_rs + dl.mean_rs, 0)} narrower). "
      f"On nine sessions in ten the gap is within Rs {f(dh.p90_abs_rs, 1)} (high) and Rs {f(dl.p90_abs_rs, 1)} (low), which is close to the 'up to about Rs 4' in the project's input audit (docs/INPUT_AUDIT.md); but {pc(dh.share_abs_gt_5)} (high) and {pc(dl.share_abs_gt_5)} (low) of sessions differ by more than Rs 5, and the largest gaps are Rs {f(dh.max_abs_rs, 0)} and Rs {f(dl.max_abs_rs, 0)}. "
      f"Yahoo's first printed open differs from the official open by Rs {f(do.mean_abs_rs, 1)} on average (up to Rs {f(do.max_abs_rs, 0)}; {pc(do.share_abs_gt_5)} of sessions by more than Rs 5), "
      f"and its last bar from the official close by Rs {f(dcl.mean_abs_rs, 1)} on average before the closing auction and by Rs {f(dcc.mean_abs_rs, 1)} since (the close is then the auction price). "
      "So a rule that depends on 'the open', 'the high' or 'the close' needs a precise definition: I use the official NSE open, high, low and close wherever the rule allows it, and the official open can be traded only through the pre-open call auction (orders by 09:08).\n")
    xo = lambda v, s, wn="final": one(XC, variant=v, price_source=s, window=wn).mean_net_pct
    diffs = [abs(xo(v, "yahoo") - xo(v, "official")) for v in ("R1_k1.0", "R2_k1.0", "R5_z1.0", "R6_long_s1_t2")]
    hd = [abs(xo(v, "hourly rule, exit at Yahoo last printed price") - xo(v, "hourly rule, exit at official close")) for v in ("R3_z1.5", "R3_z1.0", "R3_z2.0", "R4a", "R4b")]
    w(f"Re-running R1, R2, R5 and R6 on the hourly sample with Yahoo's own open, extremes and last price instead of the official ones changed the Final-window net means by {f(min(diffs))} to {f(max(diffs))} percentage points "
      f"(R1 {sg(xo('R1_k1.0', 'official'))} vs {sg(xo('R1_k1.0', 'yahoo'))}; R2 {sg(xo('R2_k1.0', 'official'))} vs {sg(xo('R2_k1.0', 'yahoo'))}; "
      f"R5 {sg(xo('R5_z1.0', 'official'))} vs {sg(xo('R5_z1.0', 'yahoo'))}; R6 long 1%/2% {sg(xo('R6_long_s1_t2', 'official'))} vs {sg(xo('R6_long_s1_t2', 'yahoo'))}). "
      f"For the hourly rules, exiting at Yahoo's last printed price instead of the official close changed the Final net means by {f(min(hd))} to {f(max(hd))} percentage points "
      f"(R4a {sg(xo('R4a', 'hourly rule, exit at official close'))} vs {sg(xo('R4a', 'hourly rule, exit at Yahoo last printed price'))}). `hl_trade_crosscheck.csv`. No verdict depends on the price source; R5 flips from slightly positive to slightly negative, which is noise around zero.\n")

    rf = REF[REF.window == "all"].iloc[0]
    rff = REF[REF.window == "final"].iloc[0]
    w("### 4.10 A reference point: where the stock's average return comes from\n")
    w(f"Buying at every official open and selling at every official close (gross, no cost) averaged {sg(rf.mean_pct, 3)}% per day over all {int(rf.n)} sessions (Newey-West t = {f(rf.t_hac, 2)}) and {sg(rff.mean_pct, 3)}% in Final (n = {int(rff.n)}, t = {f(rff.t_hac, 2)}), "
      f"while the average gap (previous close to open) was {sg(rf.mean_gap_pct, 3)}% per day (all) and {sg(rff.mean_gap_pct, 3)}% (Final). In this sample the stock's gain came overnight; the trading day itself was flat on average. "
      f"Buying and holding from 1 Jan 2019 multiplied the (bonus-adjusted) price {f(rf.buy_and_hold_multiple_over_window, 1)} times, {f(REF[REF.window == 'val'].iloc[0].buy_and_hold_multiple_over_window, 1)} times in the Validation year and {f(rff.buy_and_hold_multiple_over_window, 2)} times in Final. "
      "That is a description of the past, not an overnight trading rule (it was not one of the eight rules). A stock that rose about fifty-fold has a large drift in any sample, "
      f"which is a likely reason the sell-the-spike rules R2 and R8 lost money before costs (gross {sg(fin['R2'].mean_gross_pct)}% and {sg(fin['R8'].mean_gross_pct)}% per trade in Final) even though their levels were reached as often as promised; I did not test that explanation.\n")

    # ===================================================================================================================== 5. post hoc
    w("## 5. Post-hoc looks (exploratory; found after seeing the results; cannot change a verdict)\n")
    w("Every number in this section comes from rules written down only after seeing that R2 and R8 lost money in a consistent direction. They are the mirror image of the failed rules (trade WITH the move through the level instead of against it) plus R4a split into long and short. "
      "I counted all 16 post-hoc variants, so the Holm family below is 31 + 16 = 47. The stop-entry is assumed filled at the level (generous for a stop order). Two marketable legs, so the 'extra slippage' column charges 0.10% in all.\n")
    w("### 5.1 The mirror of the failed rules (buy when the high trades through the upper level; sell short when the low trades through the lower level)\n")
    rows = []
    lab = {"M2_k1.0": "M2: buy-stop at open + 1 sigma_H", "M2_k0.5": "M2: buy-stop at open + 0.5 sigma_H", "M2_k1.5": "M2: buy-stop at open + 1.5 sigma_H", "M1_k1.0": "M1: sell-stop at open - 1 sigma_L", "M1_k0.5": "M1: sell-stop at open - 0.5 sigma_L",
           "M1_k1.5": "M1: sell-stop at open - 1.5 sigma_L", "M8_emp_q75": "M8: buy-stop at trailing 75% high level", "M8_emp_q90": "M8: buy-stop at trailing 90% high level", "M7_emp_q25": "M7: sell-stop at trailing 25% low level",
           "M7_emp_q10": "M7: sell-stop at trailing 10% low level", "M8_post_q75": "M8: buy-stop at the model's 75% high", "M8_post_q90": "M8: buy-stop at the model's 90% high", "M7_post_q25": "M7: sell-stop at the model's 25% low", "M7_post_q10": "M7: sell-stop at the model's 10% low",
           "R4a_long": "R4a long breakouts only", "R4a_short": "R4a short breakouts only"}
    for v in lab:
        row = [lab[v], v]
        for win in ("dev", "val", "final", "cas"):
            s = PH0[(PH0.variant == v) & (PH0.window == win)]
            row.append("-" if len(s) == 0 or s.n_trades.iloc[0] == 0 else f"{sg(s.mean_net_pct.iloc[0])} ({int(s.n_trades.iloc[0])})")
        a = one(PH0, variant=v, window="final")
        row += [pv(a.p_hac_net), f(a.holm_hac_joint_family, 2), (f(a.placebo_p_A, 3) if not pd.isna(a.placebo_p_A) else "none"), (f(a.placebo_p_P0, 3) if not pd.isna(a.placebo_p_P0) else "none"), sg(a.mean_net_s1_pct)]
        rows.append(row)
    w(table(["variant", "id", "Development net % (n)", "Validation net % (n)", "Final net % (n)", "post-auction net % (n)", "Final p HAC", "Final Holm p (47)", "Final placebo p (A)", "Final placebo p (P0)", "Final net % with 0.10% extra slippage"], rows))
    m21, m2a = one(PH0, variant="M2_k1.0", window="final"), one(PH0, variant="M2_k1.0", window="all")
    m8a, m8f = one(PH0, variant="M8_post_q75", window="all"), one(PH0, variant="M8_post_q75", window="final")
    chk(m2a.mean_net_pct > 0.2 and m21.holm_hac_joint_family >= 0.99, "post-hoc M2 wording")
    yrs_big = [int(y) for y in sorted(PHY.year.unique()) if (lambda s: len(s) and s.mean_net_pct.iloc[0] > 0.4)(PHY[(PHY.variant == "M2_k1.0") & (PHY.year == y)])]
    y26 = PHY[(PHY.variant == "M2_k1.0") & (PHY.year == 2026)].mean_net_pct.iloc[0]
    w(f"\nPlain reading: the mirror of R2 (buy when the high trades 1 sigma above the open) shows {sg(m2a.mean_net_pct)}% net per trade over all years (n = {int(m2a.n_trades)}, unadjusted p {pv(m2a.p_hac_net)}, Holm over the 47 variants {f(m2a.holm_hac_joint_family, 2)}; "
      f"the same idea at the model's post-open 75% high level, M8: {sg(m8a.mean_net_pct)}%, n = {int(m8a.n_trades)}, p {pv(m8a.p_hac_net)}, Holm {f(m8a.holm_hac_joint_family, 2)}) "
      f"and {sg(m21.mean_net_pct)}% in Final (n = {int(m21.n_trades)}, p {pv(m21.p_hac_net)}; M8 {sg(m8f.mean_net_pct)}%, p {pv(m8f.p_hac_net)}). With the 0.10% extra slippage that a stop order realistically pays, the Final result of M2 is {sg(m21.mean_net_s1_pct)}%. "
      f"The gains are bunched in {', '.join(str(y) for y in yrs_big)} (below); in 2026 M2 earned {sg(y26)}%. "
      "The pattern fits 'a strongly trending stock keeps going once it breaks out of its usual daily range', which is a statement about a bull market, not about the quality of the high/low estimates. "
      f"**Suggestive only.** It cannot be validated on the data in hand: it was found after looking, the smallest Holm-adjusted p over the 47 variants is {f(PH0[PH0.window == 'all'].holm_hac_joint_family.min(), 2)} for all years and {f(PH0[PH0.window == 'final'].holm_hac_joint_family.min(), 2)} in Final, "
      "and no pre-fixed momentum rule (R4) held up in Final either.\n")
    rows = []
    for v in ("M2_k1.0", "M2_k0.5", "M1_k0.5", "M8_post_q75", "R4a_long", "R4a_short"):
        row = [v]
        for y in sorted(PHY.year.unique()):
            s = PHY[(PHY.variant == v) & (PHY.year == y)]
            row.append("-" if len(s) == 0 or s.n_trades.iloc[0] == 0 else f"{sg(s.mean_net_pct.iloc[0])} ({int(s.n_trades.iloc[0])})")
        rows.append(row)
    w("By calendar year (net % per trade, F0; trades in brackets):\n")
    w(table(["variant"] + [str(y) for y in sorted(PHY.year.unique())], rows))
    w("")
    w("### 5.2 R4 (the one descriptive rule) split by direction, and pooled\n")
    r4l, r4s = {win: one(PH0, variant="R4a_long", window=win) for win in ("val", "final")}, {win: one(PH0, variant="R4a_short", window=win) for win in ("val", "final")}
    w(f"R4a long and R4a short each look like the whole: in Validation {sg(r4l['val'].mean_net_pct)}% (n = {int(r4l['val'].n_trades)}) and {sg(r4s['val'].mean_net_pct)}% (n = {int(r4s['val'].n_trades)}), "
      f"in Final {sg(r4l['final'].mean_net_pct)}% (n = {int(r4l['final'].n_trades)}) and {sg(r4s['final'].mean_net_pct)}% (n = {int(r4s['final'].n_trades)}), "
      "so the Validation result was not just a bull-market long bias, and the Final-window fade affects both sides. "
      f"Pooled over every eligible hourly session ({nh['all']} sessions), R4a earned {sg(r4_all.mean_net_pct)}% net per trade (n = {int(r4_all.n_trades)}; Newey-West p {f(r4_all.p_hac_net, 3)}, Holm over 31 variants {f(r4_all.holm_hac, 2)}; placebo p {f(r4_all.p_placebo_A, 3)}) "
      f"and its neighbour R4b {sg(r4b_all.mean_net_pct)}% (n = {int(r4b_all.n_trades)}; p {f(r4b_all.p_hac_net, 3)}, Holm {f(r4b_all.holm_hac, 2)}, Holm-adjusted placebo p {f(r4b_all.holm_placebo_A, 3)}). "
      "So, pooled, the rule looks significant; split in time, it was concentrated in the Validation half-year and is gone in Final. The pre-fixed test is the Final window, and I follow it: a pooled number dominated by one half-year is not validation. "
      "The project's own earlier note (docs/LIVE_TOOLS.md: 'follow the first-hour move: +0.8% per trade, t 3.3 in the first 60% of the sample, about zero in the last 40%') describes the same fade independently.\n")

    w("### 5.3 Does the placebo's variance clock change the conclusions? (settings P0 and P1)\n")
    c0, cp = CL.share_variance_mean_ratio_clock.iloc[0], CL.share_variance_pooled_clock.iloc[0]
    w("The pre-fixed placebo (A, B) builds the intraday variance clock as the mean of session-normalised squared hourly returns. That estimator is biased toward an equal split because of ratio noise. "
      f"A pooled ratio-of-sums clock gives the first hourly bar a larger share ({f(cp)} against {f(c0)} of the day's variance; the whole clock is in `hl_trade_clock.csv`). I re-ran the whole placebo with it (P0 = zero drift, P1 = matched drift; same seeds). Result for the rules that matter:\n")
    rows = []
    for v in ("R4a", "R4b", "R1_k1.0", "R2_k1.0", "R3_z1.5", "R5_z1.0", "R6_long_s1_t2"):
        for win in ("val", "final"):
            s = one(SENS, variant=v, window=win)
            rows.append([v, win, int(s.n_trades), sg(s.mean_net_pct), f(s.p_placebo_A, 3), f(s.p_placebo_B, 3), f(s.p_placebo_P0, 3), f(s.p_placebo_P1, 3)])
    w(table(["variant", "window", "trades", "net %", "placebo p: A", "B", "P0 (pooled clock)", "P1"], rows))
    w(f"\nThe placebo p-values barely move with the clock, and the conclusion for every rule is unchanged. What does depend on the clock is the first-hour comparison in section 3.4: with the pre-fixed clock the observed share of sessions with the high or low in the first hour looks slightly high "
      f"(p {pv(pa.p_two_sided)} for all years, {pv(one(OHC, placebo_setting='A', window='final').p_two_sided)} in Final), with the pooled clock it looks about equal (p {pv(pp0.p_two_sided)} all years, {pv(one(OHC, placebo_setting='P0', window='final').p_two_sided)} in Final). "
      "The honest summary is 'consistent with a random walk with a U-shaped variance profile; the exact verdict depends on how that profile is estimated'.\n")

    # ===================================================================================================================== 6. failed / limits
    w("## 6. What failed, and honest limits\n")
    w("* **Nothing was validated.** R1, R2, R3, R5, R6, R7 and R8 are 'not found'; R4 is 'descriptive' because its Final-window net mean is above zero, but it is not distinguishable from zero there and turns negative with a further 0.05% per leg "
      f"({sg(r4f.mean_net_s1_pct)}%).")
    w(f"* **Power is low.** Final-window MDEs for the primary variants range from {f(mde_lo)}% ({min(PRIM, key=lambda k: fin[k].mde_80pct_power_pct)}, {int(fin[min(PRIM, key=lambda k: fin[k].mde_80pct_power_pct)].n_trades)} trades) to "
      f"{f(mde_hi)}% ({max(PRIM, key=lambda k: fin[k].mde_80pct_power_pct)}, {int(fin[max(PRIM, key=lambda k: fin[k].mde_80pct_power_pct)].n_trades)} trades) per trade. Effects of the size that survive costs (0.1-0.2% per trade) are below the detection limit of every rule. "
      f"The daily sample has {nd['all']:,} sessions, but only {pc(min(one(R0, variant=v_, window='all').fill_rate for v_ in ('R1_k1.0', 'R2_k1.0')))}-{pc(max(one(R0, variant=v_, window='all').fill_rate for v_ in ('R1_k1.0', 'R2_k1.0')))} of them produce a fill for the 1-sigma limit rules; the hourly sample has {nh_all_sessions} sessions.")
    w(f"* **Two years of hourly data are one market episode** (the price multiplied {f(REF[REF.window == 'val'].iloc[0].buy_and_hold_multiple_over_window, 1)} times in the Validation year and {f(rff.buy_and_hold_multiple_over_window, 2)} times in Final, section 4.10). Any rule that needs a trend, or the lack of one, is confounded with that episode.")
    dgf = lambda m_, w_: one(DG, metric=m_, window=w_)
    mlr = "share_both_low_ge_1pct_and_high_ge_2pct (long 1%/2% bracket both touched)"
    msr = "share_both_high_ge_1pct_and_low_ge_2pct (short 1%/2% bracket both touched)"
    chk(all(dgf("median_log_range_pct", w_).sim_mean > dgf("median_log_range_pct", w_).real for w_ in ("all", "dev", "val", "final")), "the placebo should have wider days than the data in the long windows")
    w("* **The placebo is a random walk with a fitted variance clock, not reality** (`hl_trade_placebo_diag.csv`). In the all-years, Development, Validation and Final windows its days are wider than the real ones (in the 51-session auction slice the two agree) "
      f"(median high-to-low range {f(dgf('median_log_range_pct', 'all').real)}% real against {f(dgf('median_log_range_pct', 'all').sim_mean)}% simulated, 5-95% band of the simulation {f(dgf('median_log_range_pct', 'all').sim_p05)}-{f(dgf('median_log_range_pct', 'all').sim_p95)}%) "
      f"and more two-sided: the share of sessions that reach both -1% and +2% from the open is {pc(dgf(mlr, 'final').real, 1)} in Final against {pc(dgf(mlr, 'final').sim_mean, 1)} simulated (short side {pc(dgf(msr, 'final').real, 1)} against {pc(dgf(msr, 'final').sim_mean, 1)}). "
      f"Real trades are also less noisy than simulated ones for the limit-order and first-hour rules (per-trade sd in Final: R1 {f(one(HM0, variant='R1_k1.0', window='final').sd_net_pct)}% real against {f(one(HM0, variant='R1_k1.0', window='final').null_trade_sd_pct_A)}% simulated; "
      f"R4a {f(one(HM0, variant='R4a', window='final').sd_net_pct)}% against {f(one(HM0, variant='R4a', window='final').null_trade_sd_pct_A)}%). Placebo p-values are therefore somewhat conservative for the limit-order rules and not meaningful for the fixed brackets (4.6). "
      f"The real days are also lumpier: both extremes in the first hour on {pc(oall.high_and_low_in_first_hour, 1)} of sessions against {pc(pa.sim_high_and_low_first_hour, 1)}-{pc(pp0.sim_high_and_low_first_hour, 1)}. "
      f"The real open is an auction print and is the day's high or low on {pc(oo['all'].open_is_high_or_low, 1)} of sessions, which a continuous-path placebo cannot reproduce. "
      "For rules whose observed means are negative none of this matters; the verdicts rest on the Newey-West tests, with the placebo as a second, necessary condition.")
    w("* **Execution is idealised.** Limit and stop orders fill at the level when the extreme trades through it; no queue position, no partial fills, no market impact (not measured), no slippage except the S1 stress. "
      f"Entering 'at the official open' needs the pre-open call auction (orders by 09:08) or a first-print market order; the first printed open differs from the official one by Rs {f(do.mean_abs_rs, 1)} on average. "
      "The close is a 30-minute VWAP before 3 Aug 2026 and an auction price after it; a trader cannot always exit at it.")
    w("* **The 0.10% round-trip cost is the assigned conservative figure**, not a measured cost for any particular account. Gross numbers are shown beside every net number so the reader can substitute their own. "
      f"With a cost of 0.05% instead of 0.10% the best primary variant in Final would be R4a at {sg(fin['R4'].mean_gross_pct - 0.05)}% per trade, unadjusted p = {f(pmin_005, 2)}; no primary variant would reach p < 0.05 (R5 would turn slightly positive, {sg(fin['R5'].mean_gross_pct - 0.05)}%, p = {f(p5_005, 2)}).")
    w("* **R7 and R8 use specialist A's model, which was chosen by the project using the Validation and Final windows** (A's independent verifier, item 9), so Final is not completely untouched for them. If that matters at all it flatters R7/R8, and they lost money anyway.")
    w("* **Not tested**: any use of news, index, peers, options or volume; positions held overnight; sizing rules as strategies (section 7 is descriptive); intraday exits other than the close, the stop and the target listed; model quantiles at levels other than the four stored ones. "
      "The pinball loss, coverage and Kupiec tests of the high and low quantiles themselves are specialist A's tables, not repeated here.")
    w("* **Contradictions with earlier project claims**: none found. This work agrees with the project's statement that the first-hour concentration of highs and lows is a random-walk feature, with its note that the 10:15 follow-the-first-hour rule faded, with DEVIATIONS item 30 (buying the predicted low and selling the predicted high lost money after a 0.10% cost; breakout entries roughly broke even) and with items 31 and 33 (rules that looked good early in a sample reversed later). "
      "It adds that the first-hour share depends on the placebo clock (5.3) and that the opening print is the day's extreme about one session in ten (not a random-walk feature).\n")

    # ===================================================================================================================== 7. what a trader can do
    w("## 7. What a trader can honestly do with a good high/low estimate\n")
    w("These are uses that the data support as description (Part 1), not as a source of profit.\n")
    e = {k: one(EX, entry="open", window="final", excursion=k) for k in ("up", "down")}
    c75, c50, c90 = (one(SC, side="long", stop_quantile=q, window="final") for q in (0.75, 0.5, 0.9))
    mmf = lambda f_, t_, w_="final": one(MM, forecast=f_, target=t_, window=w_)
    pre, post_ = "pre-open model median (P_S6, known 22:00 the evening before)", "post-open model median (W_I6, known 09:08)"
    ost = "benchmark 'open stays' (official open)"
    w("1. **Know how far an ordinary day travels and size accordingly.** From the open, the day's low was a median Rs "
      f"{rs(e['down'].q50_rs)} and a 90th percentile Rs {rs(e['down'].q90_rs)} below it; the high a median Rs {rs(e['up'].q50_rs)} and Rs {rs(e['up'].q90_rs)} above (Final, n = {int(e['up'].n)}). "
      f"Swings differ with the regime: the median low-below-open is Rs {rs(lo_.q50_rs)} in the calmest third of sessions and Rs {rs(hi_.q50_rs)} in the busiest (all years, full-sample terciles). "
      "If you risk a fixed rupee amount per trade, the share count should shrink as the swing grows: shares = rupee risk / stop distance in rupees. Example with a Rs 10,000 risk budget on a long: "
      f"a stop at the median adverse swing (Rs {rs(e['down'].q50_rs)}, hit on about half the days) allows {int(10000 // e['down'].q50_rs)} shares; a stop at the 75th percentile (Rs {rs(e['down'].q75_rs)}, hit on about one day in four) allows {int(10000 // e['down'].q75_rs)}; "
      f"at the 90th percentile (Rs {rs(e['down'].q90_rs)}) {int(10000 // e['down'].q90_rs)}. This is arithmetic on the table in 3.1, not a recommended risk size.")
    stp = lambda x_: one(STD, window="final", regime="all", regime_def="expanding", side="long", stop_pct=x_, target_pct=0.5).stop_touched
    w(f"2. **Place the stop outside ordinary noise, or accept being stopped.** Entering at the open, a stop 0.5% below (Rs {rs(0.005 * RS)}) was touched on {pc(stp(0.5))} of Final sessions, 1% (Rs {rs(0.01 * RS)}) on {pc(stp(1.0))}, 1.5% on {pc(stp(1.5))}, 2% (Rs {rs(0.02 * RS)}) on {pc(stp(2.0))}. "
      f"A stop at the trailing-250-session 75th percentile of the adverse swing (about Rs {rs(c75.mean_stop_distance_rs)}, {f(c75.mean_stop_distance_pct, 1)}%) was touched on {pc(c75.observed_stop_touched, 1)} of Final days against 25% nominal (Kupiec p = {f(c75.kupiec_p, 2)}); "
      f"at the median distance (Rs {rs(c50.mean_stop_distance_rs)}) on {pc(c50.observed_stop_touched, 1)} (p = {f(c50.kupiec_p, 2)}). A stop is the price of insurance, not a profit centre: a wider stop lowers the chance of being stopped but raises the loss when it is hit, and the fixed brackets (R6) did not pay.")
    w(f"3. **Do not enter late hoping for a fresh extreme.** After 13:15 the median remaining swing is about Rs {rs(a13.q50_rs)}-{rs(b13.q50_rs)} either way (Final), after 14:15 about Rs {rs(a14.q50_rs)}-{rs(b14.q50_rs)}, and by 14:15 the day's high is already in on {pc(r1415.high_already_final)} of sessions (3.5). "
      f"The round trip costs about Rs {f(0.001 * RS, 1)} at 0.10%.")
    w("4. **Use the estimate to set expectations, not to enter against the move.** "
      f"How good is the estimate? Recomputed here from specialist A's stored file (`hl_trade_model_miss.csv`, Final, n = {int(mmf(pre, 'high').n)}): the pre-open median forecast of the high is off by Rs {rs(mmf(pre, 'high').mean_abs_miss_rs)} on average (Rs {rs(mmf(pre, 'high').median_abs_miss_rs)} typical, i.e. half the time within that), the low by Rs {rs(mmf(pre, 'low').mean_abs_miss_rs)} (Rs {rs(mmf(pre, 'low').median_abs_miss_rs)}); "
      f"after the open is known the misses are Rs {rs(mmf(post_, 'high').mean_abs_miss_rs)} (high) and Rs {rs(mmf(post_, 'low').mean_abs_miss_rs)} (low), against Rs {rs(mmf(ost, 'high').mean_abs_miss_rs)} / Rs {rs(mmf(ost, 'low').mean_abs_miss_rs)} for 'the open is the high / low'. "
      "That is smaller than the naive guesses (specialist A's tests, not mine, say the improvement is statistically solid) and the levels are calibrated (reached as often as promised), but the miss is of the same order as the swing it is trying to locate: "
      f"the median swing from the open is Rs {rs(e['up'].q50_rs)}-{rs(e['down'].q50_rs)}, the typical (median) miss of the estimate Rs {rs(min(mmf(pre, 'high').median_abs_miss_rs, mmf(pre, 'low').median_abs_miss_rs, mmf(post_, 'high').median_abs_miss_rs, mmf(post_, 'low').median_abs_miss_rs))}-{rs(max(mmf(pre, 'high').median_abs_miss_rs, mmf(pre, 'low').median_abs_miss_rs, mmf(post_, 'high').median_abs_miss_rs, mmf(post_, 'low').median_abs_miss_rs))}, and the cost only Rs {f(0.001 * RS, 1)}. "
      f"A target at the estimated high is a reasonable place to think about taking profit on a long you already hold; selling short at the estimated high is a rule that lost money (R2, R8: Final {sg(fin['R2'].mean_net_pct)}% and {sg(fin['R8'].mean_net_pct)}% net per trade, n = {int(fin['R2'].n_trades)} and {int(fin['R8'].n_trades)}), and so is buying at the estimated low (R1, R7: {sg(fin['R1'].mean_net_pct)}% and {sg(fin['R7'].mean_net_pct)}%).")
    w(f"5. **Count costs at your own number.** At 0.10% a round trip costs about Rs {f(0.001 * RS, 1)} a share at today's price; a single 1% stop-out is Rs {rs(0.01 * RS)}, ten times that. The costs are small next to the swing; what is missing is a direction edge, not a cheaper broker.")
    w("6. **Beware of the one result that looks like an edge.** Following a breakout of the first-hour range made money in the Dec 2024 - Jun 2025 sample and then stopped; if you try it, treat it as an experiment with a known fade, paper-trade it, and expect about zero until proven otherwise (section 5.2).")
    w("\n**What it cannot do**: it cannot tell you the direction; it cannot say whether the stock will touch the estimated high or low before the close with more certainty than the quantile says (it is calibrated to be touched 25% of the time at the 25% level, and is); it cannot turn that touch into a reversal entry (R1, R2, R7, R8 and R3 failed); "
      "it cannot time the day (the first-hour concentration is a variance-profile feature); it cannot be improved by a bracket (R6); and with the data available it cannot support a claim of an edge smaller than about "
      f"{f(mde_lo, 1)}-{f(mde_hi, 1)}% per trade.\n")

    # ===================================================================================================================== 8. for 16 Oct
    w("## 8. Applying Part 1 to the Friday 16 Oct 2026 session (descriptive; uses nothing dated after the 15 Oct close)\n")
    sg_ = TJ["ewma_scales_for_16oct_pct"]
    w(f"Reference price: Rs {TJ['reference_close_rs']:,.0f} (15 Oct official close; open 3,342.0, high 3,445.0, low 3,315.2). Scales going into 16 Oct (exponentially weighted, lambda 0.94, through the 15 Oct session): close-to-close {f(sg_['sigR'])}% (Rs {rs(TJ['ewma_scales_in_rupees_at_reference']['sigR'])}), "
      f"gap {f(sg_['sigG'])}% (Rs {rs(TJ['ewma_scales_in_rupees_at_reference']['sigG'])}), open-to-close {f(sg_['sigI'])}% (Rs {rs(TJ['ewma_scales_in_rupees_at_reference']['sigI'])}), "
      f"open-to-low {f(sg_['sigL'])}% (Rs {rs(TJ['ewma_scales_in_rupees_at_reference']['sigL'])}), open-to-high {f(sg_['sigH'])}% (Rs {rs(TJ['ewma_scales_in_rupees_at_reference']['sigH'])}). "
      f"Volatility regime: {TJ['regime_expanding_terciles']} (pre-fixed expanding terciles), {TJ['regime_fullsample_posthoc']} (full-sample, post hoc), {TJ['regime_trailing500_posthoc']} (trailing-500, post hoc).\n")
    rows = []
    for t_ in TODAY.itertuples():
        rows.append([t_.sample, int(t_.n_sessions), t_.side.split(" (")[0], f"{f(t_.q25_pct)}% ({rs(t_.q25_rs_at_3428)})", f"{f(t_.q50_pct)}% ({rs(t_.q50_rs_at_3428)})", f"{f(t_.q75_pct)}% ({rs(t_.q75_rs_at_3428)})", f"{f(t_.q90_pct)}% ({rs(t_.q90_rs_at_3428)})"])
    w("How far the day's low (high) has been from the open, in percent and rupees at Rs 3,428 (`hl_trade_today_2026-10-16.csv`):\n")
    w(table(["sample", "sessions", "extreme", "25th pct", "median", "75th pct", "90th pct"], rows))
    w("\n**Stop distance from the 16 Oct open** under the three estimators of 3.7 (distance in percent of the open and in rupees at Rs 3,428; the share is how often a stop at that distance has been touched, by promise). `hl_trade_today_stops_2026-10-16.csv`:\n")
    rows = []
    for side in ("long", "short"):
        for q in (0.5, 0.75, 0.9):
            row = [side + (" (stop below the open)" if side == "long" else " (stop above the open)"), pc(1 - q)]
            for m_ in ("T250", "EXPANDING", "EWMA_SCALED"):
                c_ = one(TSTOP, side=side, stop_quantile=q, method=m_)
                row.append(f"Rs {rs(c_.distance_rs_at_reference)} ({f(c_.distance_pct_of_open)}%)")
            rows.append(row)
    w(table(["side", "touched on about", "T250", "EXPANDING", "EWMA_SCALED"], rows))
    fl = one(TODAY, sample="Final window (2025-07-01 to 15 Oct 2026)", side="price falls below the open (adverse for a long)")
    fh = one(TODAY, sample="Final window (2025-07-01 to 15 Oct 2026)", side="price rises above the open (adverse for a short)")
    w(f"\nHow to read it for the 16 Oct session: whatever the open is, a long entered there has had its low at least Rs {rs(fl.q25_rs_at_3428)} below it on three days in four, at least Rs {rs(fl.q50_rs_at_3428)} below on one day in two and Rs {rs(fl.q90_rs_at_3428)} or more on one day in ten (Final window); "
      f"for a short, the high was at least Rs {rs(fh.q25_rs_at_3428)}, Rs {rs(fh.q50_rs_at_3428)} and Rs {rs(fh.q90_rs_at_3428)} above the open on three days in four, one in two and one in ten. "
      f"Rule R1 would place a buy limit 1 sigma below the open, i.e. about Rs {rs(TJ['R1_k1_level_offset_below_open']['rs'])} ({f(TJ['R1_k1_level_offset_below_open']['pct'])}%) below, and R2 a sell limit about Rs {rs(TJ['R2_k1_level_offset_above_open']['rs'])} ({f(TJ['R2_k1_level_offset_above_open']['pct'])}%) above; "
      "this report does not recommend either (both lost money in Final). "
      "For the estimated high and low of 16 Oct itself, see specialist A's report and `results/hl_dayahead_2026-10-16.json` (not mine); the relevant fact from this study is that touching those levels has not been a profitable place to trade against the move.\n")

    # ===================================================================================================================== 9 numbers to quote
    w("## 9. Numbers to quote\n")
    nq = []
    nq.append("No rule validated: 0 of 8 pre-fixed rules (31 variants) passed (`hl_trade_verdicts.csv`); 7 'not found', 1 ('follow the first-hour breakout', R4) 'descriptive' (net +" + f"{f(r4f.mean_net_pct)}% in Final, p = {f(r4f.p_hac_net, 2)}).")
    nq.append(f"Estimated-low limit buy (R7, post-open 25% level), Final window: {int(r7.n_trades)} fills in {int(r7.n_sessions)} sessions, {sg(r7.mean_gross_pct)}% gross, {sg(r7.mean_net_pct)}% net = {rup(r7.mean_net_rs)} per share per trade (`hl_trade_rules.csv`).")
    nq.append(f"Estimated-high limit sell (R8, post-open 75% level), Final window: {int(r8.n_trades)} fills, {sg(r8.mean_net_pct)}% net = {rup(r8.mean_net_rs)} per share per trade.")
    nq.append(f"Fill frequency of the model's levels in Final matched the promise: {pc(k7.observed_fill, 1)} against 25% (low, n = {int(k7.n)}, Kupiec p = {f(k7.kupiec_p, 2)}) and {pc(k8.observed_fill, 1)} against 25% (high, Kupiec p = {f(k8.kupiec_p, 2)}) (`hl_trade_kupiec_fill.csv`).")
    nq.append(f"The model's 25% low level did worse than a plain trailing-quantile level in Final (DM t = {f(d25.dm_t, 1)}, Holm p {peq(d25.holm_two_sided_over_all_rows)}, {int(d25.n)} days); no difference for the other three pairs (`hl_trade_dm.csv`).")
    nq.append(f"Follow-the-breakout (R4a): Validation {sg(r4v.mean_net_pct)}% net per trade (n = {int(r4v.n_trades)}, Holm p = {f(r4v.holm_hac, 3)}), Final {sg(r4f.mean_net_pct)}% (n = {int(r4f.n_trades)}, p = {f(r4f.p_hac_net, 2)}), since the closing auction {sg(r4c.mean_net_pct)}% (n = {int(r4c.n_trades)}); with a further 0.05% per marketable leg the Final figure is {sg(r4f.mean_net_s1_pct)}%.")
    nq.append(f"Typical swing from the official open, Final (n = {int(e['up'].n)}): median high Rs {rs(e['up'].q50_rs)} above, median low Rs {rs(e['down'].q50_rs)} below; 90th percentile Rs {rs(e['up'].q90_rs)} / Rs {rs(e['down'].q90_rs)} (`hl_trade_excursions.csv`).")
    nq.append(f"Entering at 10:15: median room left Rs {rs(one(EX, entry='10:15', window='final', excursion='up').q50_rs)} up / Rs {rs(one(EX, entry='10:15', window='final', excursion='down').q50_rs)} down (Final, n = {nhf}); entering at 13:15: Rs {rs(a13.q50_rs)} / Rs {rs(b13.q50_rs)}.")
    nq.append(f"A 1% stop with a 2% target from the open (long): stopped first {100 * s12.p_stop_first_lo:.0f}-{100 * s12.p_stop_first_hi:.0f}%, target first {100 * s12.p_target_first_lo:.0f}-{100 * s12.p_target_first_hi:.0f}%, neither {100 * s12.neither:.0f}% (Final, n = {int(s12.n)}; daily bars give ranges because the order within a day is unknown).")
    nq.append(f"A 0.5% stop (Rs {rs(0.005 * RS)}) is touched on {pc(st05.stop_touched)} of Final sessions; a 1% stop (Rs {rs(0.01 * RS)}) on {pc(stp(1.0))}; a 2% stop (Rs {rs(0.02 * RS)}) on {pc(stp(2.0))}.")
    nq.append(f"High or low set in the first hour: {pc(ocas.high_or_low_in_first_hour, 1)} post-auction ({int(ocas.k_high_or_low_first_hour)} of {int(ocas.n)}), {pc(ofin.high_or_low_in_first_hour, 1)} in Final (n = {int(ofin.n)}), {pc(oall.high_or_low_in_first_hour, 1)} in all hourly sessions (n = {int(oall.n)}); random-walk placebo {pc(pa.sim_mean, 1)} (A) to {pc(pp0.sim_mean, 1)} (P0). Not a pattern.")
    nq.append(f"Official open equals the day's high or low in {pc(oo['all'].open_is_high_or_low, 1)} of {int(oo['all'].n)} sessions ({pc(oo['cas'].open_is_high_or_low, 1)} of {int(oo['cas'].n)} since the closing auction); open equals the previous close on {int(cav.open_equals_prev_close)} of {int(cav.n_sessions)} post-auction sessions.")
    nq.append(f"Yahoo hourly extremes against NSE official: mean absolute difference Rs {f(dh.mean_abs_rs, 1)} (high) and Rs {f(dl.mean_abs_rs, 1)} (low), 90th percentile Rs {f(dh.p90_abs_rs, 1)} / Rs {f(dl.p90_abs_rs, 1)}, maximum Rs {f(dh.max_abs_rs, 0)} / Rs {f(dl.max_abs_rs, 0)}; Yahoo's first printed open differs from the official open by Rs {f(do.mean_abs_rs, 1)} on average (n = {int(dh.n)}).")
    nq.append(f"Typical miss of A's median forecasts, Final (n = {int(mmf(pre, 'high').n)}): pre-open high Rs {rs(mmf(pre, 'high').mean_abs_miss_rs)} / low Rs {rs(mmf(pre, 'low').mean_abs_miss_rs)}; post-open Rs {rs(mmf(post_, 'high').mean_abs_miss_rs)} / Rs {rs(mmf(post_, 'low').mean_abs_miss_rs)} (recomputed in `hl_trade_model_miss.csv`; specialist A's own tables are the primary source).")
    nq.append(f"Power: Final-window MDE (80% power) {f(mde_lo)}% to {f(mde_hi)}% net per trade across the primary variants; 'not found' does not rule out smaller edges.")
    nq.append(f"Stock return split (all {int(rf.n)} sessions): average gap {sg(rf.mean_gap_pct, 2)}% per day, average open-to-close {sg(rf.mean_pct, 2)}% (Newey-West t {f(rf.t_hac, 2)}); the price multiplied {f(rf.buy_and_hold_multiple_over_window, 1)} times.")
    nq.append(f"Checks: self-test {st_ok} of {len(ST)} passed; independent plain-loop re-computation {int(IC.passed.sum())} of {len(IC)} comparisons agree.")
    for s_ in nq:
        w("* " + s_)
    w("")

    # ===================================================================================================================== 10 reproduce
    w("## 10. Files and exact commands to reproduce every number\n")
    w("All commands from the repository root; the hourly file is `h60_BSE.NS.json` (Yahoo chart API, `BSE.NS`, range 2y, interval 60m, fetched 15 Oct 2026, SHA-256 in `results/hl_trade_summary.json`; Yahoo's rolling window means a later download will not be identical, and a later download would also contain bars after the 15 Oct cut-off, which the code drops). "
      "`HL_TRADE_TMP` is where the placebo draws are kept between steps (default `/tmp/hl_trade`).\n")
    w("```\nexport HL_TRADE_TMP=/tmp/hl_trade\nH=<path>/h60_BSE.NS.json\npython3 src/hl_trade_study.py all --hourly $H --reps 2000 --procs 4        # everything below plus this report; about 4 minutes on 4 cores\n```\n")
    w(table(["numbers", "command (all run by `all`, in this order)", "files"], [
        ["no-look-ahead and arithmetic checks (section 2)", "`python3 src/hl_trade_study.py selftest --hourly $H`", "hl_trade_selftest.csv"],
        ["Part 1: excursions, stop/target, open and first hour, range formed, stop calibration and stop-distance estimators, Yahoo vs NSE, variance clock, open = previous close, regime for 16 Oct (sections 3, 4.9)", "`python3 src/hl_trade_study.py part1 --hourly $H`",
         "hl_trade_excursions.csv, hl_trade_stop_target_daily.csv, hl_trade_stop_target_hourly.csv, hl_trade_open_hl_real.csv, hl_trade_extreme_bar.csv, hl_trade_range_formed.csv, hl_trade_stop_calibration.csv, hl_trade_data_checks.csv, hl_trade_bracket_order.csv, hl_trade_open_equals_prev.csv, hl_trade_clock.csv, hl_trade_stop_forecast.csv, hl_trade_summary.json"],
        ["Part 2 real-data results: 31 variants x 5 windows x 3 fill conventions, trades, by year, DM, Kupiec, Yahoo cross-check, typical miss of the stored forecasts, reference drift (sections 1, 4, 7)", "`python3 src/hl_trade_study.py part2 --hourly $H`",
         "hl_trade_rules.csv, hl_trade_trades.csv, hl_trade_byyear.csv, hl_trade_dm.csv, hl_trade_kupiec_fill.csv, hl_trade_crosscheck.csv, hl_trade_model_miss.csv, hl_trade_reference_drift.csv"],
        ["placebo draws (4 settings x 2,000 histories; seed 20261015)", "`python3 src/hl_trade_study.py placebo --hourly $H --reps 2000 --procs 4`", "$HL_TRADE_TMP/placebo.npz (not kept in results/)"],
        ["Holm, placebo p-values, verdicts, first-hour comparison with the placebo (sections 1, 3.4, 4.1-4.6)", "`python3 src/hl_trade_study.py finish --hourly $H`", "hl_trade_holm.csv, hl_trade_verdicts.csv, hl_trade_open_hl.csv"],
        ["post-hoc variants, joint Holm, clock sensitivity P0/P1 (section 5)", "`python3 src/hl_trade_study.py posthoc --hourly $H`", "hl_trade_posthoc.csv, hl_trade_posthoc_byyear.csv, hl_trade_sensitivity_clock.csv, hl_trade_open_hl_clock.csv"],
        ["numbers for 16 Oct (section 8)", "`python3 src/hl_trade_study.py today --hourly $H`", "hl_trade_today_2026-10-16.csv, hl_trade_today_stops_2026-10-16.csv, hl_trade_today_2026-10-16.json"],
        ["independent plain-loop re-computation (section 2)", "`python3 src/hl_trade_study.py indepcheck --hourly $H`", "hl_trade_indepcheck.csv"],
        ["placebo versus reality, tick-rounding sensitivity (sections 2, 6)", "`python3 src/hl_trade_study.py diag --hourly $H`", "hl_trade_placebo_diag.csv, hl_trade_sensitivity_tick.csv"],
        ["this report's tables and text (every number is read from the files above; qualitative sentences are guarded by checks that stop the build if the files disagree)", "`python3 src/hl_trade_study.py report`", "research/hl/C_tradeability.md"],
    ]))
    w("\n*Research on past data for a risk-management question; not investment advice.*\n")

    # ===================================================================================================================== appendix
    w("## Appendix A. Every variant in every window (F0, net % per trade after 0.10%; trades in brackets)\n")
    w("Development has no hourly rules (R3, R4); for R3/R4 the first column is the hourly sample after its 40-session burn-in (Dec 2024 - Oct 2026). Post-hoc variants are in section 5.\n")
    rows = []
    for v in list(R0[R0.window == "final"].variant):
        row = [v]
        for win in ("all", "dev", "val", "final", "cas"):
            s = HM0[(HM0.variant == v) & (HM0.window == win)]
            row.append("-" if len(s) == 0 or s.n_trades.iloc[0] == 0 else f"{sg(s.mean_net_pct.iloc[0])} ({int(s.n_trades.iloc[0])})")
        rows.append(row)
    w(table(["variant", "all 2019-2026", "Development", "Validation", "Final", "post-closing-auction"], rows))
    w("")

    body = "\n".join(out)
    text = report_path.read_text()
    i_ = text.index(SECTION0_END) + len(SECTION0_END)
    head = text[:i_]
    import hashlib as _h
    if _h.sha256(head.encode()).hexdigest() != SECTION0_SHA256:
        raise AssertionError("section 0 of the report has been modified")
    report_path.write_text(head + "\n\n---\n\n" + body + "\n")
    print(f"report written: {report_path} ({len(body.splitlines())} lines of results sections)")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "part1", "part2", "placebo", "finish", "posthoc", "today", "indepcheck", "diag", "report", "all"])
    ap.add_argument("--hourly", default=os.environ.get("HL_HOURLY", ""))
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=8)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.cmd == "report":
        build_report(OUT)
        return
    d = load_daily()
    S, audit = real_sess(d, a.hourly)
    model = load_model(S)
    E = estimators(S)
    cmds = ["selftest", "part1", "part2", "placebo", "finish", "posthoc", "today", "indepcheck", "diag", "report"] if a.cmd == "all" else [a.cmd]
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
            clock_table(S, OUT)
            res, lab = part1(S, d, OUT)
            stop_forecast_eval(S, OUT)
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
            model_miss(S, model, OUT)
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
        elif cmd == "indepcheck":
            X = indepcheck(a.hourly, OUT)
            print(X[~X.passed].to_string(index=False) if (~X.passed).any() else "all comparisons agree")
            summary["indepcheck_passed"], summary["indepcheck_total"] = int(X.passed.sum()), int(len(X))
        elif cmd == "diag":
            placebo_diag(S, E, OUT, procs=a.procs, chunk=a.chunk)
        elif cmd == "report":
            (OUT / "hl_trade_summary.json").write_text(json.dumps(summary, indent=1, default=str))
            build_report(OUT)
        print(f"[{cmd}] {time.time()-t0:.1f}s")
    (OUT / "hl_trade_summary.json").write_text(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
