"""v2 workstream "intraday": intraday structure and session patterns of NSE:BSE from ONE deduplicated 15-minute dataset.

Run:  cd /home/user/pred_18 && PYTHONPATH=src python3 src/behaviour/intraday.py
Writes ONLY  data/processed/intraday_union_15m.csv  and  results/behaviour/intraday.json
(the markdown report research/v2/05_intraday_structure.md is written by hand from the JSON).
Reads local files read-only; fetches NOTHING (no network code in this file).  Every input file is asserted to end on or
before the v2 information cutoff date 2026-10-13 (cutoff 22:00 IST); nothing dated 14-Oct-2026 can enter.

=====================================================================================================================
DATA RULES (fixed before any outcome statistic was computed on the union)
=====================================================================================================================
D1  Source A (preferred) = data/processed/xlsx_15m_clean.csv (user workbook = Yahoo API values, 20 sessions 15-Sep..13-Oct).
    Source B = data/raw/intraday/*.csv (earlier fetched bars), used ONLY for sessions that are not in the workbook; the
    bars of B that overlap A are used for a cross-check, never for values.  Rows with NaN in B are feed-null rows (the
    missing 15:15 bars) and are dropped, not imputed.
D2  A session enters the union only if it passes the checks of src/validate_intraday.py, re-implemented here with the SAME
    constants (CLOSE_TOL 0.0002, HL_TOL 0.0025, VOL 0.80-1.02, >=24 bars, row OHLC consistency +-0.06, volume>0 except last
    row, bar-open within 0.4% of previous bar close).  The original script is not edited and its output file
    data/processed/intraday_validation.csv is not overwritten (it predates the 13-Oct daily row).
D3  Prices of B are float32 artefacts (e.g. 3266.10009765625): snapped to the 0.05 tick after verifying the deviation < 0.001.
D4  Official open / close / high / low / volume / turnover / previous close = data/processed/bse_daily.csv (NSE bhavcopy).

=====================================================================================================================
PRE-REGISTRATION OF EVERY TEST (written BEFORE any statistic of the union was computed; the v1 summary numbers in
results/intraday_profile.json had been read, and 36 of the 37 union sessions are the same sessions as v1, so nothing here
is an independent confirmation of v1).  Unit of analysis = one session (non-overlapping calendar days).  Bars inside a
session are NOT independent, so the effective sample of every bar-based statistic is the number of sessions.
=====================================================================================================================
NOTATION  slot k=0..24 is the bar starting 09:15+15k min (k=3 -> 10:00 bar, ends 10:15; k=23 -> 15:00; k=24 -> 15:15 bar =
 closing-auction window).  O_off, C_off, H_off, L_off, prev = official NSE open/close/high/low and bonus-adjusted previous
 close.  C_k = close of slot k.
 G = ln(O_off/prev);  FH = ln(C_3/O_off) (first hour, from the official open);  Rest = ln(C_off/C_3);  I = FH + Rest = ln(C_off/O_off).
 FH_bar = ln(C_3/O_0) (v1 definition, from the first printed bar open).
 first hour = slots 0-3 (09:15-10:14), last hour = slots 21-24 (14:30-15:29), midday = slots 4-20.
 Sessions without the 15:15 bar (feed omits it) carry the closing print in the 15:00 bar: slots 23 and 24 are therefore only
 comparable as the COMBINED window 15:00-15:30, return ln(C_off/C_22).

FAMILY (25 tests = the 23 below + R01, R02 defined further down in the code; two-sided; Holm = FWER and Benjamini-Hochberg = FDR across the whole family, reported for each):
 Timing (benchmark = driftless martingale observed on the EMPIRICAL variance clock, Monte-Carlo 200,000 paths, 1-minute
 steps; clock = mean over sessions of the session-normalised squared 15-min returns, last 30 min as one block):
  T01 share of sessions with the session HIGH in the first hour          exact binomial vs MC probability
  T02 share with the LOW in the first hour
  T03 share with the HIGH in the last hour
  T04 share with the LOW in the last hour
  T05 mean share of the session bar-range already formed by 10:15      (MC distribution of the mean of n sessions)
  T06 mean share of the session bar-range already formed by 11:15
 Continuation / gap:
  T07 Pearson corr(FH, Rest) != 0                                       t-test
  T08 P(sign Rest = sign FH) != 0.5                                      exact binomial (zeros dropped)
  T09 mean of sign(G)*I != 0 (gap continuation if >0, gap fade if <0)  t-test, sessions with G != 0
  C01 sessions with G>0: mean Rest != 0 (t);   C02 sessions with G<0: mean Rest != 0 (t)
  C03 large-gap sessions (|G| >= median |G| of the union, rule fixed now): mean sign(G)*I != 0 (t)
  C04 small-gap sessions (|G| < median): mean sign(G)*I != 0 (t)
  (C01-C04 are the "conditional on gap sign / size" request; exploratory, counted.)
 VWAP / levels (origin = official open, sigma_i = RMS of I over the 20 previous sessions of the DAILY file, zero-mean
  reflection principle: P(session touches a level at log-distance d>0) = 2*(1-Phi(d/sigma_i)); d<=0 -> 1; observed touch
  uses the official daily high/low; null of the count = Poisson-binomial, exact):
  V01 P(C_off > exchange session VWAP = turnover/volume) != 0.5          exact binomial
  V02 Spearman(ln(C_7/VWAP_bars to 11:15), ln(C_off/C_7)) != 0           checkpoint 11:15
  V03 same at checkpoint 13:15 (slot 15)
  L01 touch of previous CLOSE (gap fill) observed count vs Poisson-binomial expectation (sessions with G != 0)
  L02 touch of previous-day HIGH (H_off >= H_off of previous session, adjusted)
  L03 touch of previous-day LOW
 Auction bar (sessions with a 15:15 bar):
  A01 Pearson corr( ln(C_23/C_22), ln(C_24/O_24) ) != 0
  A02 mean ln(C_24/O_24) != 0
 Chronological walk-forward (fixed rule, first 10 sessions = training only, expanding window, one step ahead; benchmark =
  sign of the expanding mean of the target; exact McNemar test on discordant sessions):
  S01 rule: predict sign(Rest) = s_k*sign(FH), s_k = sign of corr(FH,Rest) over earlier sessions
  S02 rule: predict sign(I) = s_k*sign(G),  s_k = sign of corr(G,I) over earlier sessions
 CHANGE LOG (honest process record).  First run = the 23 tests above (no change to any definition).  After seeing that output I
  added, before computing them: R01/R02 (rejection vs breakthrough at the previous-day extremes, long daily history), follow-ups F1/F2
  (contrary checks of the two nominally interesting cells C04 and L01 on the long history), sensitivity (A) clock with the first-bar
  return measured from the first printed open, sensitivity (B) extremes that include the official open.  None of these changes a
  registered result; they are labelled as post-first-run additions in the JSON/report.
 Everything else (time-of-day profiles, anatomy, top-volume bars, auction-move distribution, persistence rates, timeframe
 cross-checks) is DESCRIPTIVE: confidence intervals but no hypothesis test and no claim.
 CIs: percentile bootstrap over sessions (B=10,000, seed 20261013; iid and circular block length 3 for serial dependence),
 Wilson for proportions.  Power is computed for the n actually available.  A pattern is validated_out_of_sample ONLY if a
 chronological split / walk-forward whose rule is fixed on the training part beats the benchmark in the test part with a
 Holm-adjusted p<0.05 (the test counted in the family); otherwise descriptive_only / not_found / untested / contradicted.
"""
from __future__ import annotations

import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "src")
from common import load_bse  # noqa: E402

OUT_JSON = Path("results/behaviour/intraday.json")
OUT_CSV = Path("data/processed/intraday_union_15m.csv")
XLSX = "data/raw/tradingview/BSE_intraday_30d_1.xlsx"
CUTOFF = pd.Timestamp("2026-10-13")
SEED = 20261013
NBOOT = 10000
NMC = 200_000
# validator constants (identical to src/validate_intraday.py)
CLOSE_TOL, HL_TOL, VOL_LO, VOL_HI = 0.0002, 0.0025, 0.80, 1.02
rng = np.random.default_rng(SEED)
RES: dict = {}
TESTS: list[dict] = []


# ----------------------------------------------------------------------------------------------------- helpers
def wilson(k, n, z=1.959964):
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(c - h), float(c + h)]


def boot_idx(n, block=1, nboot=NBOOT):
    if block == 1:
        return rng.integers(0, n, size=(nboot, n))
    nb = math.ceil(n / block)
    starts = rng.integers(0, n, size=(nboot, nb))
    return ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(nboot, -1)[:, :n]


def ci_stat(x, fn=np.mean, block=1, alpha=0.05):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 3:
        return [float("nan"), float("nan")]
    idx = boot_idx(len(x), block)
    v = fn(x[idx], axis=1)
    return [float(np.quantile(v, alpha / 2)), float(np.quantile(v, 1 - alpha / 2))]


def summ(x, pct=True):
    """mean, median, sd, n, iid and block-3 bootstrap CI of the mean (values scaled to % if pct)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    f = 100.0 if pct else 1.0
    return {"n": int(len(x)), "mean": float(f * x.mean()), "median": float(f * np.median(x)), "sd": float(f * x.std(ddof=1)) if len(x) > 1 else None,
            "ci95_mean_iid": [f * v for v in ci_stat(x)], "ci95_mean_block3": [f * v for v in ci_stat(x, block=3)],
            "ci95_median_iid": [f * v for v in ci_stat(x, np.median)]}


def corr_boot(x, y, fn=stats.pearsonr):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    idx = boot_idx(n)
    xb, yb = x[idx], y[idx]
    xm, ym = xb - xb.mean(1, keepdims=True), yb - yb.mean(1, keepdims=True)
    den = np.sqrt((xm ** 2).sum(1) * (ym ** 2).sum(1))
    r = (xm * ym).sum(1) / np.where(den == 0, np.nan, den)
    return [float(np.nanquantile(r, 0.025)), float(np.nanquantile(r, 0.975))]


def fisher_ci(r, n):
    if n < 4:
        return [float("nan")] * 2
    z, se = np.arctanh(r), 1 / math.sqrt(n - 3)
    return [float(np.tanh(z - 1.959964 * se)), float(np.tanh(z + 1.959964 * se))]


def register(tid, label, p, n, extra=None):
    TESTS.append({"id": tid, "label": label, "p_raw": float(p), "n": int(n), **(extra or {})})


def holm_bh(tests):
    m = len(tests)
    p = np.array([t["p_raw"] for t in tests])
    order = np.argsort(p)
    holm = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * p[i])
        holm[i] = min(1.0, run)
    bh = np.empty(m)
    run = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        run = min(run, p[i] * m / (rank + 1))
        bh[i] = run
    for t, h, b in zip(tests, holm, bh):
        t["p_holm"], t["p_bh"] = float(h), float(b)
        t["significant_holm_5pct"] = bool(h < 0.05)
        t["significant_bh_5pct"] = bool(b < 0.05)


def binom2(k, n, p0):
    return float(stats.binomtest(int(k), int(n), p0, alternative="two-sided").pvalue)


def poisson_binomial_pmf(p):
    pmf = np.array([1.0])
    for pi in p:
        pmf = np.convolve(pmf, [1 - pi, pi])
    return pmf


def pb_two_sided(obs, p):
    pmf = poisson_binomial_pmf(np.asarray(p))
    cdf = np.cumsum(pmf)
    lo = cdf[int(obs)]
    hi = 1 - (cdf[int(obs) - 1] if obs > 0 else 0.0)
    return float(min(1.0, 2 * min(lo, hi))), float(np.dot(np.arange(len(pmf)), pmf)), float(np.sqrt(np.dot((np.arange(len(pmf)) ** 2), pmf) - np.dot(np.arange(len(pmf)), pmf) ** 2))


def mcnemar_exact(hit_rule, hit_bench):
    b = int(np.sum(hit_rule & ~hit_bench))
    c = int(np.sum(~hit_rule & hit_bench))
    p = 1.0 if b + c == 0 else binom2(b, b + c, 0.5)
    return p, b, c


def pct(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else float(100 * x)


def jdefault(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def clean(o):
    """convert NaN to None recursively so the JSON is strict."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if (np.isnan(o) or np.isinf(o)) else float(o)
    return o


# ----------------------------------------------------------------------------------------------------- 1. load + validate
daily = load_bse()
assert daily.index.max() <= CUTOFF, "daily file extends beyond the cutoff date"
xl = pd.read_csv("data/processed/xlsx_15m_clean.csv", parse_dates=["date"])
raw_frames = [pd.read_csv(f) for f in sorted(glob.glob("data/raw/intraday/*.csv"))]
raw_all = pd.concat(raw_frames)
n_raw_rows, n_raw_null_rows = len(raw_all), int(raw_all[["open", "high", "low", "close", "volume"]].isna().any(axis=1).sum())
raw = raw_all.drop_duplicates("ts").dropna().sort_values("ts").copy()
raw["dt"] = pd.to_datetime(raw["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
raw["date"] = raw["dt"].dt.tz_localize(None).dt.normalize()
raw["time"] = raw["dt"].dt.strftime("%H:%M")
null_rows = raw_all[raw_all[["open", "high", "low", "close", "volume"]].isna().any(axis=1)].copy()
null_rows["dt"] = pd.to_datetime(null_rows["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
null_rows["date"] = null_rows["dt"].dt.tz_localize(None).dt.normalize()
null_rows["time"] = null_rows["dt"].dt.strftime("%H:%M")
for nm, mx in (("xlsx_15m_clean.csv", xl["date"].max()), ("data/raw/intraday", raw["date"].max())):
    assert mx <= CUTOFF, f"{nm} extends beyond cutoff: {mx}"
snap_dev = float(max(((raw[c] * 20).round() / 20 - raw[c]).abs().max() for c in ("open", "high", "low", "close")))
assert snap_dev < 0.001
for c in ("open", "high", "low", "close"):
    raw[c] = (raw[c] * 20).round() / 20


def validate_session(g: pd.DataFrame, r) -> dict:
    """re-implementation of src/validate_intraday.py (same constants and tests); g sorted by time."""
    g2 = g.reset_index(drop=True)
    agg = dict(high=g2["high"].max(), low=g2["low"].min(), close=g2["close"].iloc[-1], vol=g2["volume"].sum(), n=len(g2))
    chk_close = abs(agg["close"] - r["close"]) <= CLOSE_TOL * r["close"]
    chk_hi = abs(agg["high"] - r["high"]) <= HL_TOL * r["close"]
    chk_lo = abs(agg["low"] - r["low"]) <= HL_TOL * r["close"]
    ratio = agg["vol"] / r["vol"]
    chk_vol = VOL_LO <= ratio <= VOL_HI
    chk_n = agg["n"] >= 24
    bad_rows = int(((g2["low"] > g2[["open", "close"]].min(axis=1) + 0.06) | (g2["high"] < g2[["open", "close"]].max(axis=1) - 0.06)
                    | ((g2["volume"] <= 0) & (g2.index < len(g2) - 1))).sum())
    cont = g2["open"].iloc[1:].values / g2["close"].iloc[:-1].values - 1
    bad_cont = int((np.abs(cont) > 0.004).sum())
    ok = bool(chk_close and chk_hi and chk_lo and chk_vol and chk_n and bad_rows == 0 and bad_cont == 0)
    failed = [nm for nm, v in (("close", chk_close), ("high", chk_hi), ("low", chk_lo), ("volume_ratio", chk_vol), ("n_bars>=24", chk_n)) if not v]
    if bad_rows:
        failed.append(f"row_ohlc/zero_volume({bad_rows})")
    if bad_cont:
        failed.append(f"bar_continuity({bad_cont})")
    return {"status": "PASS" if ok else "FAIL", "failed_checks": failed, "n_bars": int(agg["n"]), "vol_ratio": float(ratio),
            "d_high": float(agg["high"] - r["high"]), "d_low": float(agg["low"] - r["low"]), "d_close": float(agg["close"] - r["close"])}


val_xl = {day: validate_session(g.sort_values("time"), daily.loc[day]) for day, g in xl.groupby("date")}
val_raw = {day: validate_session(g.sort_values("time"), daily.loc[day]) for day, g in raw.groupby("date")}
xl_days = set(xl["date"].unique())
use_xl = sorted(d for d, v in val_xl.items() if v["status"] == "PASS")
use_raw = sorted(d for d, v in val_raw.items() if v["status"] == "PASS" and d not in xl_days)
excluded = [{"date": str(d.date()), "source": "xlsx_workbook" if d in xl_days else "earlier_fetch", "failed_checks": (val_xl if d in xl_days else val_raw)[d]["failed_checks"]}
            for d in sorted(set(val_xl) | set(val_raw)) if (d in xl_days and val_xl[d]["status"] == "FAIL") or (d not in xl_days and val_raw[d]["status"] == "FAIL")]

# overlap cross-check workbook vs earlier fetch (same timestamps)
xk = xl.assign(key=xl["date"].dt.strftime("%Y-%m-%d") + " " + xl["time"])
rk = raw.assign(key=raw["date"].dt.strftime("%Y-%m-%d") + " " + raw["time"])
mg = xk.merge(rk, on="key", suffixes=("", "_e"))
overlap = {"bars_in_both": int(len(mg)), "bars_only_in_workbook": int((~xk["key"].isin(rk["key"])).sum()),
           "price_mismatch_gt_0.051": int(sum(((mg[c] - mg[c + "_e"]).abs() > 0.051).sum() for c in ("open", "high", "low", "close"))),
           "volume_mismatch_gt_1pct": int(((mg["volume"] / mg["volume_e"].replace(0, np.nan) - 1).abs() > 0.01).sum() + ((mg["volume"] == 0) != (mg["volume_e"] == 0)).sum())}
vm = mg[((mg["volume"] / mg["volume_e"].replace(0, np.nan) - 1).abs() > 0.01)]
overlap["volume_mismatch_bars"] = [{"date": str(r["date"].date()), "time": r["time"], "workbook": int(r["volume"]), "earlier_fetch": int(r["volume_e"]),
                                    "ratio": float(r["volume"] / r["volume_e"]),
                                    "session_vol_ratio_with_workbook_value": float(val_xl[r["date"]]["vol_ratio"]),
                                    "session_vol_ratio_if_earlier_value": float(val_xl[r["date"]]["vol_ratio"] - (r["volume"] - r["volume_e"]) / daily.loc[r["date"], "vol"])}
                                   for _, r in vm.iterrows()]
alt_vol = dict(zip(rk["key"], rk["volume"]))
alt_vol_x = dict(zip(xk["key"], xk["volume"]))

parts = []
a = xl[xl["date"].isin(use_xl)].copy()
a["source"] = "xlsx_workbook"
a["vol_other_source"] = (a["date"].dt.strftime("%Y-%m-%d") + " " + a["time"]).map(alt_vol)
b = raw[raw["date"].isin(use_raw)][["date", "time", "open", "high", "low", "close", "volume"]].copy()
b["source"] = "earlier_fetch"
b["vol_other_source"] = np.nan
U = pd.concat([a[["date", "time", "open", "high", "low", "close", "volume", "source", "vol_other_source"]], b]).sort_values(["date", "time"]).reset_index(drop=True)
nb = U.groupby("date")["time"].transform("size")
U["session_bars"] = nb
U["has_1515_bar"] = U.groupby("date")["time"].transform(lambda s: bool((s == "15:15").any()))
U["slot"] = U["time"].map(lambda t: (int(t[:2]) * 60 + int(t[3:]) - 555) // 15)
assert U.groupby(["date", "time"]).size().max() == 1 and U["date"].max() <= CUTOFF
out = U[["date", "time", "open", "high", "low", "close", "volume", "source", "session_bars", "has_1515_bar", "vol_other_source"]].copy()
out["date"] = out["date"].dt.strftime("%Y-%m-%d")
out["volume"] = out["volume"].astype(int)
out["vol_other_source"] = out["vol_other_source"].astype("Int64")
for c in ("open", "high", "low", "close"):
    out[c] = out[c].round(2)
out.to_csv(OUT_CSV, index=False)
dates = sorted(U["date"].unique())
N = len(dates)

RES["meta"] = {"script": "src/behaviour/intraday.py", "cutoff": "2026-10-13 22:00 IST", "max_date_in_inputs": str(max(xl["date"].max(), raw["date"].max(), daily.index.max()).date()),
               "seed": SEED, "bootstrap_B": NBOOT, "mc_paths": NMC, "n_sessions_union": N, "first": str(dates[0].date()), "last": str(dates[-1].date())}
RES["data"] = {
    "workbook_sessions": len(xl_days), "workbook_sessions_pass": len(use_xl), "workbook_bars": int(len(xl)),
    "earlier_fetch_rows": int(n_raw_rows), "earlier_fetch_null_rows": n_raw_null_rows, "earlier_fetch_sessions": int(raw["date"].nunique()),
    "earlier_fetch_sessions_not_in_workbook": int(len(set(raw["date"]) - xl_days)),
    "earlier_fetch_sessions_used": len(use_raw), "union_sessions": N, "union_bars": int(len(U)), "union_sessions_by_source": U.groupby("source")["date"].nunique().to_dict(),
    "excluded_sessions": excluded, "validator_constants": {"CLOSE_TOL": CLOSE_TOL, "HL_TOL": HL_TOL, "VOL_LO": VOL_LO, "VOL_HI": VOL_HI},
    "float32_snap_max_deviation": snap_dev, "overlap_workbook_vs_earlier_fetch": overlap,
    "null_rows_in_earlier_fetch": [{"date": str(r["date"].date()), "time": r["time"]} for _, r in null_rows.sort_values("date").iterrows()],
    "sessions_with_24_bars": [str(d.date()) for d in dates if (U[U["date"] == d]["session_bars"].iloc[0] == 24)],
    "validation": [{"date": str(d.date()), "source": "xlsx_workbook" if d in xl_days else "earlier_fetch", **(val_xl if d in xl_days else val_raw)[d]} for d in sorted(set(val_xl) | set(val_raw))],
}

# ----------------------------------------------------------------------------------------------------- 2. arrays
nS = N
O = np.full((nS, 25), np.nan); H = O.copy(); L = O.copy(); C = O.copy(); V = O.copy()
for i, dd in enumerate(dates):
    g = U[U["date"] == dd]
    O[i, g["slot"]], H[i, g["slot"]], L[i, g["slot"]], C[i, g["slot"]], V[i, g["slot"]] = g["open"].values, g["high"].values, g["low"].values, g["close"].values, g["volume"].values
D = daily.loc[dates]
Ooff, Coff, Hoff, Loff, prev = D["open"].values, D["close"].values, D["high"].values, D["low"].values, D["prev"].values
has15 = ~np.isnan(C[:, 24])
last_close = np.array([C[i, 24] if has15[i] else C[i, 23] for i in range(nS)])
vwap_ex = D["turnover_cr"].values * 1e7 / D["vol"].values
tot_vol = np.nansum(V, axis=1)
tp = (H + L + C) / 3
cumv = np.cumsum(np.nan_to_num(V), axis=1)
vwap_run = np.cumsum(np.nan_to_num(tp * V), axis=1) / np.where(cumv == 0, np.nan, cumv)
vwap_bar = vwap_run[:, 24].copy()
vwap_bar[~has15] = vwap_run[~has15, 23]
# 15-min close-to-close log returns (slot 0 measured from the official open)
Cprev = np.full((nS, 25), np.nan)
Cprev[:, 0] = Ooff
Cprev[:, 1:] = C[:, :-1]
RET = np.log(C / Cprev)
RET[~has15, 24] = np.nan
RETC = np.log(last_close / C[:, 22])  # combined 15:00-15:30 window, comparable in all sessions
RNG = np.log(H / L)
G = np.log(Ooff / prev)
FH = np.log(C[:, 3] / Ooff)
FHbar = np.log(C[:, 3] / O[:, 0])
REST = np.log(Coff / C[:, 3])
I = np.log(Coff / Ooff)
assert np.allclose(G + FH + REST, np.log(Coff / prev))
assert np.nanmax(np.abs(last_close - Coff)) <= 0.05 + 1e-9, "last bar close != official close"

# ----------------------------------------------------------------------------------------------------- 3. pitfalls of the workbook
pit: dict = {}
pit["sessions_without_1515_bar"] = int((~has15).sum())
pit["sessions_without_1515_bar_dates"] = [str(dates[i].date()) for i in np.where(~has15)[0]]
pit["last_bar_close_equals_official_close_all_sessions"] = {"n": nS, "max_abs_diff": float(np.nanmax(np.abs(last_close - Coff))), "n_within_0.05": int((np.abs(last_close - Coff) <= 0.05 + 1e-9).sum())}
pit["last_bar_close_is_slot"] = {"15:15 bar (sessions that have it)": int(has15.sum()), "15:00 bar (sessions without 15:15 bar)": int((~has15).sum())}
c23_eq = np.abs(C[:, 23] - Coff) <= 0.05 + 1e-9
pit["close_of_1500_bar_equals_official_close"] = {"sessions_with_1515": {"n": int(has15.sum()), "n_equal": int(c23_eq[has15].sum())}, "sessions_without_1515": {"n": int((~has15).sum()), "n_equal": int(c23_eq[~has15].sum())}}
pit["daily_file_last_equals_close"] = {"n": nS, "n_equal": int((D["last"].values == D["close"].values).sum())}
# structure of the 15:15 bar
b15 = np.where(has15)[0]
env = np.array([(H[i, 24] == max(O[i, 24], C[i, 24])) and (L[i, 24] == min(O[i, 24], C[i, 24])) for i in b15])
pit["bar_1515"] = {"n": int(len(b15)), "volume_zero": int((V[b15, 24] == 0).sum()), "high_low_equal_envelope_of_open_close": int(env.sum()),
                   "open_equals_prev_bar_close": int((np.abs(O[b15, 24] - C[b15, 23]) <= 0.05 + 1e-9).sum()),
                   "open_minus_prev_close_abs_mean_rs": float(np.mean(np.abs(O[b15, 24] - C[b15, 23]))), "open_minus_prev_close_abs_max_rs": float(np.max(np.abs(O[b15, 24] - C[b15, 23]))),
                   "volume_share_of_session_bars_mean_pct": float(100 * np.mean(V[b15, 24] / tot_vol[b15])), "volume_share_median_pct": float(100 * np.median(V[b15, 24] / tot_vol[b15])),
                   "close_equals_open": int((C[b15, 24] == O[b15, 24]).sum())}
zero_bars = U[U["volume"] <= 0]
pit["zero_volume_bars_union"] = {"n": int(len(zero_bars)), "by_slot_time": zero_bars["time"].value_counts().to_dict(), "all_are_1515": bool((zero_bars["time"] == "15:15").all())}
ratio = tot_vol / D["vol"].values
pit["bar_volume_vs_nse_daily"] = {"mean_ratio": float(ratio.mean()), "min": float(ratio.min()), "max": float(ratio.max()),
                                  "mean_ratio_sessions_with_1515": float(ratio[has15].mean()), "mean_ratio_sessions_without_1515": float(ratio[~has15].mean()),
                                  "unattributed_volume_mean_pct_of_daily": float(100 * (1 - ratio).mean()),
                                  "corr_unattributed_share_vs_abs_auction_move": None}
pit["first_bar_volume_mismatch"] = overlap["volume_mismatch_bars"]
# high/low shortfall of the bars vs official extremes
dH = Hoff - np.nanmax(H, axis=1)
dL = np.nanmin(L, axis=1) - Loff
pit["bar_extremes_vs_official"] = {"high_shortfall_rs": {"mean": float(dH.mean()), "max": float(dH.max()), "n_sessions_exact": int((np.abs(dH) < 1e-9).sum())},
                                   "low_shortfall_rs": {"mean": float(dL.mean()), "max": float(dL.max()), "n_sessions_exact": int((np.abs(dL) < 1e-9).sum())},
                                   "share_of_sessions_with_any_shortfall": float(((dH > 1e-9) | (dL > 1e-9)).mean())}
# bar VWAP vs exchange VWAP
verr = 1e4 * (vwap_bar / vwap_ex - 1)
pit["bar_vwap_vs_exchange_vwap_bps"] = {"mean": float(verr.mean()), "mean_abs": float(np.abs(verr).mean()), "max_abs": float(np.abs(verr).max()), "max_abs_session": str(dates[int(np.argmax(np.abs(verr)))].date())}
c23_hi, c23_lo = C[:, 23] == H[:, 23], C[:, 23] == L[:, 23]
ext = c23_hi | c23_lo
pit["bar_1500_close_is_bar_extreme"] = {"sessions_with_1515": {"n": int(has15.sum()), "close_is_bar_high": int(c23_hi[has15].sum()), "close_is_bar_low": int(c23_lo[has15].sum())},
                                        "sessions_without_1515": {"n": int((~has15).sum()), "close_is_bar_high": int(c23_hi[~has15].sum()), "close_is_bar_low": int(c23_lo[~has15].sum())},
                                        "fisher_exact_p_extreme_by_group_descriptive": float(stats.fisher_exact([[int(ext[has15].sum()), int((~ext[has15]).sum())], [int(ext[~has15].sum()), int((~ext[~has15]).sum())]])[1]),
                                        "reading": "in the 8 sessions without a 15:15 bar the 15:00 bar closes AT the official close and (5 of 8) that close is also the bar high: the closing print is attached to the 15:00 bar"}
pit["official_open_vs_first_printed_bar_open"] = {"mean_signed_pct": float(100 * np.mean(np.log(O[:, 0] / Ooff))), "mean_abs_pct": float(100 * np.mean(np.abs(np.log(O[:, 0] / Ooff)))), "max_abs_rs": float(np.max(np.abs(O[:, 0] - Ooff))),
                                                  "sessions_equal": int((np.abs(O[:, 0] - Ooff) < 0.051).sum()), "n": nS}
pit["weekday_of_sessions_without_1515"] = [dates[i].day_name() for i in np.where(~has15)[0]]
pit["weekday_counts_all_sessions"] = pd.Series([d_.day_name() for d_ in dates]).value_counts().to_dict()
RES["pitfalls"] = pit

# ----------------------------------------------------------------------------------------------------- 4. timeframes cross-check (workbook sheets)
tf: dict = {}
sheets = {}
for nm in ("15 min", "30 min", "1 hour"):
    s = pd.read_excel(XLSX, sheet_name=nm)
    s.columns = ["date", "time", "open", "high", "low", "close", "volume"]
    s["date"] = pd.to_datetime(s["date"])
    assert s["date"].max() <= CUTOFF
    sheets[nm] = s
x15 = sheets["15 min"].copy()
x15["slot"] = x15["time"].map(lambda t: (int(t[:2]) * 60 + int(t[3:]) - 555) // 15)


def rebuild(minutes):
    z = x15.copy()
    z["b"] = (z["slot"] * 15 // minutes) * minutes
    z["bh"] = 9 * 60 + 15 + z["b"]
    z["bt"] = z["bh"].map(lambda m: f"{m // 60:02d}:{m % 60:02d}")
    return z.sort_values(["date", "slot"]).groupby(["date", "bt"]).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum"), n=("open", "size")).reset_index().rename(columns={"bt": "time"})


for nm, mins in (("30 min", 30), ("1 hour", 60)):
    rb = rebuild(mins)
    sh = sheets[nm].merge(rb, on=["date", "time"], how="outer", suffixes=("", "_rb"), indicator=True)
    both = sh[sh["_merge"] == "both"]
    full = both[both["n"] == (mins // 15)]
    # the last hourly/half-hourly bar of the 15:15 window: 15:15 bar only (n=1) is complete by construction
    full_all = both[(both["n"] == mins // 15) | (both["time"] == "15:15")]
    pm = lambda c: int(((full_all[c] - full_all[c + "_rb"]).abs() > 0.051).sum())
    tf[nm] = {"sheet_bars": int(len(sheets[nm])), "bars_matched_to_15m_buckets": int(len(both)), "bars_only_in_sheet": int((sh["_merge"] == "left_only").sum()), "bars_only_in_rebuild": int((sh["_merge"] == "right_only").sum()),
              "bars_compared_complete": int(len(full_all)), "mismatch_open": pm("open"), "mismatch_high": pm("high"), "mismatch_low": pm("low"), "mismatch_close": pm("close"),
              "volume_mismatch_gt1pct": int(((full_all["volume"] - full_all["volume_rb"]).abs() > 0.01 * full_all["volume_rb"].clip(lower=1)).sum()),
              "volume_zero_in_sheet_but_positive_in_15m": int(((full_all["volume"] == 0) & (full_all["volume_rb"] > 0)).sum()),
              "zero_volume_bars_by_start_time": sheets[nm][sheets[nm]["volume"] == 0]["time"].value_counts().to_dict(),
              "incomplete_buckets_excluding_1515": int(((both["n"] < (mins // 15)) & (both["time"] != "15:15")).sum())}
# derive the key timing quantities from each sheet and compare with the 15-minute data on the 20 workbook sessions
def sheet_stats(s, first_hour_bars):
    rows = {}
    for day, g in s.groupby("date"):
        g = g.sort_values("time").reset_index(drop=True)
        hi, lo = int(g["high"].values.argmax()), int(g["low"].values.argmin())
        rows[day] = {"hi_first": hi < first_hour_bars, "lo_first": lo < first_hour_bars, "rs_1015": float((g.iloc[:first_hour_bars]["high"].max() - g.iloc[:first_hour_bars]["low"].min()) / (g["high"].max() - g["low"].min()))}
    return pd.DataFrame(rows).T


ref = sheet_stats(sheets["15 min"], 4)
for nm, nbar in (("30 min", 2), ("1 hour", 1)):
    st = sheet_stats(sheets[nm], nbar)
    j = ref.join(st, rsuffix="_s")
    tf[nm]["timing_check_vs_15m"] = {"sessions": int(len(j)), "high_first_hour_classification_differs": int((j["hi_first"] != j["hi_first_s"]).sum()), "low_first_hour_classification_differs": int((j["lo_first"] != j["lo_first_s"]).sum()),
                                     "max_abs_diff_range_share_by_1015": float((j["rs_1015"].astype(float) - j["rs_1015_s"].astype(float)).abs().max())}
# 1-hour 09:15 volume defect
h1 = sheets["1 hour"]
tf["1 hour"]["first_hourly_bar_volume_zero_sessions"] = int(((h1["time"] == "09:15") & (h1["volume"] == 0)).sum())
tf["1 hour"]["first_hourly_bar_sessions"] = int((h1["time"] == "09:15").sum())
tf["sessions_covered"] = int(sheets["15 min"]["date"].nunique())
tf["same_sessions_for_all_three_sheets"] = bool(set(sheets["15 min"]["date"]) == set(sheets["30 min"]["date"]) == set(sheets["1 hour"]["date"]))
tf["sheet_window"] = [str(sheets["15 min"]["date"].min().date()), str(sheets["15 min"]["date"].max().date())]
RES["timeframes"] = tf

# ----------------------------------------------------------------------------------------------------- 5. (1) time-of-day profiles
times = [f"{(555 + 15 * k) // 60:02d}:{(555 + 15 * k) % 60:02d}" for k in range(25)]
VS = V / tot_vol[:, None]
idx0929 = [i for i, d in enumerate(dates) if d == pd.Timestamp("2026-09-29")]
keep = np.ones(nS, bool)
keep[idx0929] = False
RET2 = RET ** 2
RET2c = RET2.copy()
RET2c[:, 23] = RETC ** 2  # slot 23 carries the combined window, slot 24 dropped
RET2c[:, 24] = np.nan
rv_tot = np.nansum(RET2c, axis=1)
RVS = RET2c / rv_tot[:, None]
slots = []
for k in range(25):
    m = ~np.isnan(VS[:, k])
    row = {"slot": k, "bar_start": times[k], "n_sessions": int(m.sum()),
           "vol_share_pct": summ(VS[m, k]), "vol_share_mean_pct_ex_0929": float(100 * np.nanmean(VS[keep & m, k])),
           "range_pct_mean": float(100 * np.nanmean(RNG[m, k])), "abs_ret_pct": summ(np.abs(RET[m, k]))}
    row["abs_ret_pct"] = {kk: row["abs_ret_pct"][kk] for kk in ("n", "mean", "median", "ci95_mean_iid")}
    row["vol_share_pct"] = {kk: row["vol_share_pct"][kk] for kk in ("n", "mean", "median", "ci95_mean_iid", "ci95_mean_block3")}
    row["var_share_pct_mean"] = float(100 * np.nanmean(RVS[m, k])) if k < 24 else None
    slots.append(row)
# windows
W = {"open_0915_1015": range(0, 4), "late_morning_1015_1115": range(4, 8), "midday_1115_1415": range(8, 20), "afternoon_1415_1500": range(20, 23), "close_1500_1530": [23, 24]}
win = {}
for wn, ks in W.items():
    ks = list(ks)
    vsh = np.nansum(VS[:, ks], axis=1)  # missing 15:15 bar contributes 0 (its print is folded into the 15:00 bar)
    if wn == "close_1500_1530":
        rv = RETC ** 2 / rv_tot
        ab = np.abs(RETC)
        nb15 = 2
    else:
        rv = np.nansum(RET2c[:, ks], axis=1) / rv_tot
        ab = np.nanmean(np.abs(RET[:, ks]), axis=1)
    win[wn] = {"n_bars_per_session": len(ks), "vol_share_pct": summ(vsh), "vol_share_pct_ex_0929": summ(vsh[keep]), "var_share_pct": summ(rv), "abs_ret_pct_per_bar" if wn != "close_1500_1530" else "abs_ret_pct_30min_window": summ(ab),
               "frac_sessions_vol_share_above_uniform": float(np.mean(vsh > len(ks) / 25 if wn != "close_1500_1530" else vsh > 2 / 25))}
mid_per_bar = np.nansum(VS[:, 8:20], axis=1) / 12
fh_per_bar = np.nansum(VS[:, 0:4], axis=1) / 4
win["ratio_open_hour_to_midday_volume_per_bar"] = {"mean_ratio_of_means": float(fh_per_bar.mean() / mid_per_bar.mean()), "frac_sessions_open_per_bar_gt_midday_per_bar": float(np.mean(fh_per_bar > mid_per_bar)),
                                                  "ci95_ratio_of_means": [float(q) for q in np.quantile((lambda ix: fh_per_bar[ix].mean(axis=1) / mid_per_bar[ix].mean(axis=1))(np.random.default_rng(SEED + 5).integers(0, nS, size=(NBOOT, nS))), [0.025, 0.975])],
                                                  "mean_of_session_ratios": float(np.mean(fh_per_bar / mid_per_bar))}
win["ratio_first_bar_to_midday_abs_ret"] = float(np.nanmean(np.abs(RET[:, 0])) / np.nanmean(np.abs(RET[:, 8:20])))
win["unit_note"] = "volume shares are shares of the SUM OF BAR VOLUME of the session (87-100% of NSE daily volume); a session without a 15:15 bar contributes 0 to that slot (print folded into the 15:00 bar)."
combined_1500 = np.nansum(VS[:, [23, 24]], axis=1)
RES["profile"] = {"slots": slots, "windows": win,
                  "slot_1500_and_1515_combined_vol_share_pct": summ(combined_1500),
                  "slot_1500_pure_sessions_with_1515_vol_share_pct": summ(VS[has15, 23]), "slot_1500_sessions_without_1515_vol_share_pct": summ(VS[~has15, 23]),
                  "n_sessions": nS, "effective_sample": "sessions (n=37); bars within a session are dependent. Slot 15:15 n=29."}
# peak-slot ranking
mean_vs = np.array([np.nanmean(VS[:, k]) for k in range(25)])
RES["profile"]["top5_volume_slots"] = [{"bar_start": times[k], "mean_share_pct": float(100 * mean_vs[k])} for k in np.argsort(-mean_vs)[:5]]
RES["profile"]["lowest5_volume_slots_excluding_1515"] = [{"bar_start": times[k], "mean_share_pct": float(100 * mean_vs[k])} for k in [kk for kk in np.argsort(mean_vs) if kk != 24][:5]]

# ----------------------------------------------------------------------------------------------------- 6. (2) timing of highs and lows + MC benchmark
Hm, Lm = np.where(np.isnan(H), -np.inf, H), np.where(np.isnan(L), np.inf, L)
hi_slot = Hm.argmax(axis=1)
lo_slot = Lm.argmin(axis=1)
hi_ties = (np.isclose(Hm, Hm.max(axis=1, keepdims=True))).sum(axis=1)
lo_ties = (np.isclose(Lm, Lm.min(axis=1, keepdims=True))).sum(axis=1)


def win3(s):
    return np.where(s <= 3, "first_hour", np.where(s >= 21, "last_hour", "midday"))


hi_w, lo_w = win3(hi_slot), win3(lo_slot)
# MC variance-clock benchmark
def run_mc(clock_vec, seed):
    clk = np.asarray(clock_vec, float) / np.sum(clock_vec)
    sd = np.concatenate([np.repeat(np.sqrt(clk[:23] / 15.0), 15), np.repeat(np.sqrt(clk[23] / 30.0), 30)])
    assert len(sd) == 375
    out_ = {k: [] for k in ("hi_first", "lo_first", "hi_last", "lo_last", "rs60", "rs120")}
    mr = np.random.default_rng(seed)
    chunk = 20000
    for _ in range(NMC // chunk):
        z = mr.standard_normal((chunk, 375)) * sd
        pth = np.concatenate([np.zeros((chunk, 1)), np.cumsum(z, axis=1)], axis=1)
        jh, jl = pth.argmax(axis=1), pth.argmin(axis=1)
        rg = pth.max(axis=1) - pth.min(axis=1)
        out_["hi_first"].append(jh <= 60); out_["lo_first"].append(jl <= 60); out_["hi_last"].append(jh >= 316); out_["lo_last"].append(jl >= 316)
        out_["rs60"].append((pth[:, :61].max(1) - pth[:, :61].min(1)) / rg); out_["rs120"].append((pth[:, :121].max(1) - pth[:, :121].min(1)) / rg)
    return {k: np.concatenate(v) for k, v in out_.items()}


clock = np.append(np.nanmean(RVS[:, :23], axis=0), np.nanmean(RETC ** 2 / rv_tot))
clock = clock / clock.sum()
mc = run_mc(clock, SEED + 1)
pb = {k: float(mc[k].mean()) for k in ("hi_first", "lo_first", "hi_last", "lo_last")}
pb_sym = {"first_hour": float((pb["hi_first"] + pb["lo_first"]) / 2), "last_hour": float((pb["hi_last"] + pb["lo_last"]) / 2)}
arcsine_uniform_clock = {"first_hour": float(2 / math.pi * math.asin(math.sqrt(60 / 375))), "last_hour": float(2 / math.pi * math.asin(math.sqrt(60 / 375)))}
# observed
rs = []
for kk in (3, 7):
    hh = np.fmax.accumulate(np.nan_to_num(H, nan=-np.inf), axis=1)[:, kk]
    ll = np.fmin.accumulate(np.nan_to_num(L, nan=np.inf), axis=1)[:, kk]
    rs.append((hh - ll) / (np.nanmax(H, axis=1) - np.nanmin(L, axis=1)))
RS1015, RS1115 = rs
tm = {"clock": {"first_hour_variance_share": float(clock[:4].sum()), "last_hour_variance_share": float(clock[21:23].sum() + clock[23]), "slot_shares_pct": [float(100 * c) for c in clock]}}
tm["benchmark_probabilities_mc"] = {**pb, "note": "driftless martingale on the empirical variance clock; arcsine law with a uniform clock would give 0.262 for any 16% window"}
tm["arcsine_uniform_clock_first_or_last_hour"] = arcsine_uniform_clock["first_hour"]


def bucket_hist(slot_arr):
    b = np.where(slot_arr == 24, 6, np.minimum(slot_arr // 4, 5))
    lab = ["09:15-10:14", "10:15-11:14", "11:15-12:14", "12:15-13:14", "13:15-14:14", "14:15-15:14", "15:15-15:29"]
    return {lab[j]: int((b == j).sum()) for j in range(7)}


def prop_row(k, n, pbench, tid, label, uniform):
    lo, hi = wilson(k, n)
    p = binom2(k, n, pbench)
    register(tid, label, p, n, {"observed": k / n, "benchmark": pbench})
    return {"k": int(k), "n": int(n), "share": k / n, "wilson95": [lo, hi], "benchmark_variance_clock": pbench, "benchmark_uniform_time": uniform, "p_binom_vs_variance_clock": p}


tm["high"] = {"first_hour": prop_row(int((hi_w == "first_hour").sum()), nS, pb["hi_first"], "T01", "session high in first hour", 4 / 25),
              "last_hour": prop_row(int((hi_w == "last_hour").sum()), nS, pb["hi_last"], "T03", "session high in last hour", 4 / 25),
              "midday": int((hi_w == "midday").sum()), "hourly_histogram": bucket_hist(hi_slot)}
tm["low"] = {"first_hour": prop_row(int((lo_w == "first_hour").sum()), nS, pb["lo_first"], "T02", "session low in first hour", 4 / 25),
             "last_hour": prop_row(int((lo_w == "last_hour").sum()), nS, pb["lo_last"], "T04", "session low in last hour", 4 / 25),
             "midday": int((lo_w == "midday").sum()), "hourly_histogram": bucket_hist(lo_slot)}
either = ((hi_w == "first_hour") | (lo_w == "first_hour"))
pb_either = float(((mc["hi_first"]) | (mc["lo_first"])).mean())
tm["high_or_low_in_first_hour"] = {"k": int(either.sum()), "n": nS, "share": float(either.mean()), "wilson95": wilson(int(either.sum()), nS), "benchmark_variance_clock": pb_either, "p_binom_descriptive_not_in_family": binom2(int(either.sum()), nS, pb_either)}
both_first = ((hi_w == "first_hour") & (lo_w == "first_hour"))
tm["high_and_low_both_in_first_hour"] = {"k": int(both_first.sum()), "share": float(both_first.mean()), "benchmark_variance_clock": float((mc["hi_first"] & mc["lo_first"]).mean())}
tm["high_or_low_in_last_hour"] = {"k": int(((hi_w == "last_hour") | (lo_w == "last_hour")).sum()), "share": float(((hi_w == "last_hour") | (lo_w == "last_hour")).mean()),
                                  "benchmark_variance_clock": float((mc["hi_last"] | mc["lo_last"]).mean())}
# robustness of the classification to missed ticks: bars within the official-minus-bar shortfall of the bar maximum
amb_hi = amb_lo = 0
hi_first_lb = hi_first_ub = lo_first_lb = lo_first_ub = 0
for i in range(nS):
    tol_h, tol_l = max(dH[i], 0.05), max(dL[i], 0.05)
    near_h = np.where(np.nan_to_num(H[i], nan=-np.inf) >= np.nanmax(H[i]) - tol_h - 1e-9)[0]
    near_l = np.where(np.nan_to_num(L[i], nan=np.inf) <= np.nanmin(L[i]) + tol_l + 1e-9)[0]
    wh = set(win3(near_h)); wl = set(win3(near_l))
    amb_hi += len(wh) > 1; amb_lo += len(wl) > 1
    hi_first_lb += wh == {"first_hour"}; hi_first_ub += "first_hour" in wh
    lo_first_lb += wl == {"first_hour"}; lo_first_ub += "first_hour" in wl
tm["missed_tick_sensitivity"] = {"rule": "bars whose high (low) is within max(official shortfall, 1 tick) of the bar maximum (minimum) are treated as possible holders of the extreme",
                                 "sessions_with_ambiguous_high_window": int(amb_hi), "sessions_with_ambiguous_low_window": int(amb_lo),
                                 "high_in_first_hour_bounds": [hi_first_lb / nS, hi_first_ub / nS], "low_in_first_hour_bounds": [lo_first_lb / nS, lo_first_ub / nS],
                                 "sessions_with_tied_bar_maximum": int((hi_ties > 1).sum()), "sessions_with_tied_bar_minimum": int((lo_ties > 1).sum())}
# range share formed by 10:15, 11:15
sim_idx = np.random.default_rng(SEED + 2).integers(0, NMC, size=(20000, nS))


def range_row(obs, simvals, tid, label):
    simmean = simvals[sim_idx].mean(axis=1)
    p = float(min(1.0, 2 * min((simmean <= obs.mean()).mean(), (simmean >= obs.mean()).mean())))
    register(tid, label, max(p, 1 / 20000), nS, {"observed": float(obs.mean()), "benchmark": float(simvals.mean())})
    return {"mean": float(obs.mean()), "median": float(np.median(obs)), "ci95_mean_iid": ci_stat(obs), "ci95_mean_block3": ci_stat(obs, block=3), "ci95_median_iid": ci_stat(obs, np.median),
            "benchmark_mean_variance_clock": float(simvals.mean()), "benchmark_median_variance_clock": float(np.median(simvals)), "benchmark_sampling_95pct_of_mean_of_n": [float(np.quantile(simmean, .025)), float(np.quantile(simmean, .975))],
            "p_mc_two_sided": p, "frac_sessions_ge_0.5": float(np.mean(obs >= 0.5)), "frac_sessions_ge_0.75": float(np.mean(obs >= 0.75))}


tm["range_share_by_1015"] = range_row(RS1015, mc["rs60"], "T05", "mean share of range formed by 10:15")
tm["range_share_by_1115"] = range_row(RS1115, mc["rs120"], "T06", "mean share of range formed by 11:15")
tm["range_note"] = "ranges are bar highs/lows (the bars miss up to Rs 5 of the official extremes in some sessions); MC range uses 1-minute steps (slight downward bias of the simulated range)."
tm["daily_range_context"] = {"rho_pct_log_high_low_union": summ(np.log(Hoff / Loff)), "bar_range_over_official_range_mean": float(np.mean(np.log(np.nanmax(H, 1) / np.nanmin(L, 1)) / np.log(Hoff / Loff)))}
# --- sensitivities declared after the first run (not in the registry): (A) alternative clock with the first-bar return measured from the
# first printed bar open instead of the official open; (B) extremes that include the official open as a path point (the official daily
# high/low contain the pre-open auction price, the bars do not).
RET2_alt = RET2c.copy()
RET2_alt[:, 0] = np.log(C[:, 0] / O[:, 0]) ** 2
RVS_alt = RET2_alt / np.nansum(RET2_alt, axis=1)[:, None]
clock_alt = np.append(np.nanmean(RVS_alt[:, :23], axis=0), np.nanmean(RETC ** 2 / np.nansum(RET2_alt, axis=1)))
mc_alt = run_mc(clock_alt, SEED + 3)
H0, L0 = H.copy(), L.copy()
H0[:, 0] = np.fmax(H[:, 0], Ooff)
L0[:, 0] = np.fmin(L[:, 0], Ooff)
hi0, lo0 = np.where(np.isnan(H0), -np.inf, H0).argmax(axis=1), np.where(np.isnan(L0), np.inf, L0).argmin(axis=1)
hw0, lw0 = win3(hi0), win3(lo0)
rs0 = []
for kk in (3, 7):
    hh_ = np.fmax.accumulate(np.nan_to_num(H0, nan=-np.inf), axis=1)[:, kk]
    ll_ = np.fmin.accumulate(np.nan_to_num(L0, nan=np.inf), axis=1)[:, kk]
    rs0.append((hh_ - ll_) / (np.nanmax(H0, axis=1) - np.nanmin(L0, axis=1)))


def prop_sens(w_arr, key, bench):
    k_ = int((w_arr == key).sum())
    return {"k": k_, "n": nS, "share": k_ / nS, "benchmark": bench, "p_binom": binom2(k_, nS, bench)}


tm["sensitivity_alt_clock_first_print"] = {
    "first_hour_variance_share": float(clock_alt[:4].sum()), "benchmark_probabilities": {k: float(mc_alt[k].mean()) for k in ("hi_first", "lo_first", "hi_last", "lo_last")},
    "high_first_hour": prop_sens(hi_w, "first_hour", float(mc_alt["hi_first"].mean())), "low_first_hour": prop_sens(lo_w, "first_hour", float(mc_alt["lo_first"].mean())),
    "high_last_hour": prop_sens(hi_w, "last_hour", float(mc_alt["hi_last"].mean())), "low_last_hour": prop_sens(lo_w, "last_hour", float(mc_alt["lo_last"].mean())),
    "high_or_low_first_hour_benchmark": float((mc_alt["hi_first"] | mc_alt["lo_first"]).mean()),
    "range_by_1015_benchmark_mean": float(mc_alt["rs60"].mean()), "range_by_1115_benchmark_mean": float(mc_alt["rs120"].mean())}
tm["sensitivity_official_open_in_extremes"] = {
    "sessions_whose_high_window_changes": int((hw0 != hi_w).sum()), "sessions_whose_low_window_changes": int((lw0 != lo_w).sum()),
    "sessions_official_open_is_official_high": int((np.isclose(Ooff, Hoff)).sum()), "sessions_official_open_is_official_low": int((np.isclose(Ooff, Loff)).sum()),
    "high_first_hour": prop_sens(hw0, "first_hour", pb["hi_first"]), "low_first_hour": prop_sens(lw0, "first_hour", pb["lo_first"]),
    "high_last_hour": prop_sens(hw0, "last_hour", pb["hi_last"]), "low_last_hour": prop_sens(lw0, "last_hour", pb["lo_last"]),
    "high_or_low_first_hour_share": float(((hw0 == "first_hour") | (lw0 == "first_hour")).mean()),
    "range_share_by_1015_mean": float(rs0[0].mean()), "range_share_by_1115_mean": float(rs0[1].mean()), "range_share_by_1015_median": float(np.median(rs0[0]))}
RES["timing"] = tm

# ----------------------------------------------------------------------------------------------------- 7. (3) first hour vs rest of day, gap conditioning
cont: dict = {}
r_p, p_p = stats.pearsonr(FH, REST)
r_s, p_s = stats.spearmanr(FH, REST)
register("T07", "corr(FH, Rest)", p_p, nS, {"observed": float(r_p)})
sgn_agree = (np.sign(FH) == np.sign(REST))
k_agree, n_nz = int(sgn_agree.sum()), int(((FH != 0) & (REST != 0)).sum())
p_sign = binom2(k_agree, n_nz, 0.5)
register("T08", "P(sign Rest = sign FH)", p_sign, n_nz, {"observed": k_agree / n_nz})
r_b, p_b = stats.pearsonr(FHbar, REST)
cont["definitions"] = {"FH": "ln(C_10:00bar / official open)", "FH_bar": "ln(C_10:00bar / first bar open) (v1)", "Rest": "ln(official close / C_10:00bar)", "G": "ln(official open / adjusted prev close)"}
cont["corr_FH_Rest"] = {"pearson": float(r_p), "p": float(p_p), "ci95_bootstrap": corr_boot(FH, REST), "ci95_fisher": fisher_ci(r_p, nS), "spearman": float(r_s), "spearman_p": float(p_s), "n": nS,
                        "pearson_with_FH_bar_v1_definition": float(r_b), "p_FH_bar": float(p_b)}
cont["sign_concordance"] = {"k": k_agree, "n": n_nz, "share": k_agree / n_nz, "wilson95": wilson(k_agree, n_nz), "p": p_sign, "continuation_share_if_FH_positive": float(np.mean(REST[FH > 0] > 0)), "n_FH_pos": int((FH > 0).sum()),
                            "continuation_share_if_FH_negative": float(np.mean(REST[FH < 0] < 0)), "n_FH_neg": int((FH < 0).sum())}
cont["slope_Rest_on_FH"] = {k: float(v) for k, v in zip(("slope", "intercept", "r", "p", "se"), stats.linregress(FH, REST))}
cont["FH_abs_distribution_pct"] = {"mean_abs": float(100 * np.mean(np.abs(FH))), "median_abs": float(100 * np.median(np.abs(FH))), "p90_abs": float(100 * np.quantile(np.abs(FH), .9)),
                                   "share_abs_ge_1.0pct": float(np.mean(np.abs(FH) >= 0.01)), "share_abs_ge_1.5pct": float(np.mean(np.abs(FH) >= 0.015)), "n_abs_ge_1.5pct": int((np.abs(FH) >= 0.015).sum()),
                                   "wilson95_share_abs_ge_1.5pct": wilson(int((np.abs(FH) >= 0.015).sum()), nS)}
big = np.abs(FH) >= 0.015
cont["FH_abs_ge_1.5pct_sessions"] = [{"date": str(dates[i].date()), "FH_pct": float(100 * FH[i]), "Rest_pct": float(100 * REST[i]), "FH_vol_share_pct": float(100 * np.nansum(VS[i, :4])), "abs_I_pct": float(100 * abs(I[i]))} for i in np.where(big)[0]]
fhv_abs = np.nansum(V[:, :4], axis=1)
fhv_med = float(np.median(fhv_abs))
big_vol = big & (fhv_abs > 2 * fhv_med)
cont["v1_invalidation_trigger_first_hour_gt_1.5pct_on_gt_2x_volume"] = {
    "rule": "|FH| >= 1.5% and first-hour bar volume > 2x the median first-hour volume of the union sessions", "median_first_hour_volume": fhv_med,
    "n_abs_FH_ge_1.5pct": int(big.sum()), "n_with_volume_gt_2x_median": int(big_vol.sum()), "share_of_sessions": float(big_vol.mean()), "wilson95": wilson(int(big_vol.sum()), nS),
    "dates_with_volume_gt_2x": [str(dates[i].date()) for i in np.where(big_vol)[0]], "mean_Rest_pct_after_such_starts": float(100 * REST[big_vol].mean()) if big_vol.any() else None,
    "mean_abs_I_pct_when_triggered": float(100 * np.abs(I[big_vol]).mean()) if big_vol.any() else None, "mean_abs_I_pct_other_sessions": float(100 * np.abs(I[~big_vol]).mean())}
# gap
gnz = G != 0
cont["gap"] = {"n_up": int((G > 0).sum()), "n_down": int((G < 0).sum()), "n_zero": int((G == 0).sum()), "abs_G_pct": summ(np.abs(G)), "median_abs_G_pct": float(100 * np.median(np.abs(G)))}
aligned_I = np.sign(G) * I
aligned_FH = np.sign(G) * FH
aligned_R = np.sign(G) * REST
t9 = stats.ttest_1samp(aligned_I[gnz], 0.0)
register("T09", "mean sign(G)*I", t9.pvalue, int(gnz.sum()), {"observed": float(aligned_I[gnz].mean())})
cont["gap_continuation"] = {"mean_signG_x_I_pct": summ(aligned_I[gnz]), "p_t": float(t9.pvalue), "share_sessions_I_in_gap_direction": float(np.mean(aligned_I[gnz] > 0)), "wilson95": wilson(int((aligned_I[gnz] > 0).sum()), int(gnz.sum())),
                            "mean_signG_x_FH_pct": float(100 * aligned_FH[gnz].mean()), "mean_signG_x_Rest_pct": float(100 * aligned_R[gnz].mean()),
                            "corr_G_I": float(stats.pearsonr(G, I)[0]), "corr_G_I_p": float(stats.pearsonr(G, I)[1]), "spearman_G_I": float(stats.spearmanr(G, I)[0]),
                            "long_history_daily_corr_G_I_v1": "-0.043 (n=2357, results/conditional_day.json)"}
medabs = np.median(np.abs(G))
big_gap, small_gap = np.abs(G) >= medabs, np.abs(G) < medabs


def cond_block(mask, tid, label, series, name):
    x = series[mask]
    t = stats.ttest_1samp(x, 0.0)
    register(tid, label, t.pvalue, int(mask.sum()), {"observed": float(x.mean())})
    return {"n": int(mask.sum()), name + "_mean_pct": float(100 * x.mean()), "ci95_iid_pct": [100 * v for v in ci_stat(x)], "p_t": float(t.pvalue), "share_positive": float(np.mean(x > 0))}


cont["conditional"] = {
    "gap_up": {**cond_block(G > 0, "C01", "G>0: mean Rest", REST, "Rest"), "mean_FH_pct": float(100 * FH[G > 0].mean()), "mean_I_pct": float(100 * I[G > 0].mean()), "corr_FH_Rest": float(stats.pearsonr(FH[G > 0], REST[G > 0])[0]) if (G > 0).sum() > 3 else None,
               "sign_agree": [int(sgn_agree[G > 0].sum()), int((G > 0).sum())]},
    "gap_down": {**cond_block(G < 0, "C02", "G<0: mean Rest", REST, "Rest"), "mean_FH_pct": float(100 * FH[G < 0].mean()), "mean_I_pct": float(100 * I[G < 0].mean()), "corr_FH_Rest": float(stats.pearsonr(FH[G < 0], REST[G < 0])[0]) if (G < 0).sum() > 3 else None,
                 "sign_agree": [int(sgn_agree[G < 0].sum()), int((G < 0).sum())]},
    "large_gap": {**cond_block(big_gap & gnz, "C03", "large |G|: mean sign(G)*I", aligned_I, "signG_x_I"), "threshold_abs_G_pct": float(100 * medabs), "corr_FH_Rest": float(stats.pearsonr(FH[big_gap], REST[big_gap])[0]),
                  "sign_agree": [int(sgn_agree[big_gap].sum()), int(big_gap.sum())]},
    "small_gap": {**cond_block(small_gap & gnz, "C04", "small |G|: mean sign(G)*I", aligned_I, "signG_x_I"), "corr_FH_Rest": float(stats.pearsonr(FH[small_gap], REST[small_gap])[0]),
                  "sign_agree": [int(sgn_agree[small_gap].sum()), int(small_gap.sum())]}}
# walk-forward S01/S02 (first 10 sessions training only)


def walk_forward(sig, tgt, name_id, label, kmin=10):
    hits_rule, hits_bench, rows = [], [], []
    for k in range(kmin, nS):
        s = np.sign(stats.pearsonr(sig[:k], tgt[:k])[0]) or 1.0
        pred_rule = s * np.sign(sig[k])
        pred_b = np.sign(tgt[:k].mean()) or 1.0
        hits_rule.append(np.sign(tgt[k]) == pred_rule)
        hits_bench.append(np.sign(tgt[k]) == pred_b)
        rows.append((str(dates[k].date()), float(s)))
    hr, hb = np.array(hits_rule), np.array(hits_bench)
    p, b, c = mcnemar_exact(hr, hb)
    register(name_id, label, p, len(hr), {"observed": float(hr.mean()), "benchmark": float(hb.mean())})
    pbin = float(stats.binomtest(int(hr.sum()), len(hr), 0.5, alternative="greater").pvalue)
    return {"n_test": int(len(hr)), "hit_rate_rule": float(hr.mean()), "hit_rate_benchmark_expanding_mean_sign": float(hb.mean()), "wilson95_rule": wilson(int(hr.sum()), len(hr)),
            "mcnemar_exact_p": p, "rule_only_correct": b, "benchmark_only_correct": c, "binom_p_rule_gt_0.5_one_sided_descriptive": pbin,
            "share_of_test_sessions_where_sign_rule_chose_continuation": float(np.mean([s > 0 for _, s in rows]))}


cont["walk_forward_S01_FH_to_Rest"] = walk_forward(FH, REST, "S01", "walk-forward sign(Rest) from FH", 10)
cont["walk_forward_S02_gap_to_I"] = walk_forward(G, I, "S02", "walk-forward sign(I) from G", 10)
RES["continuation"] = cont

# ----------------------------------------------------------------------------------------------------- 8. (4) VWAP and levels
lev: dict = {}
above_ex = Coff > vwap_ex
above_bar = Coff > vwap_bar
p_v1 = binom2(int(above_ex.sum()), nS, 0.5)
register("V01", "P(close > exchange VWAP)", p_v1, nS, {"observed": float(above_ex.mean())})
lev["close_vs_vwap"] = {"exchange_vwap": {"k": int(above_ex.sum()), "n": nS, "share": float(above_ex.mean()), "wilson95": wilson(int(above_ex.sum()), nS), "p_binom": p_v1,
                                        "mean_ln_close_over_vwap_pct": summ(np.log(Coff / vwap_ex))},
                        "bar_vwap_typical_price": {"k": int(above_bar.sum()), "share": float(above_bar.mean()), "wilson95": wilson(int(above_bar.sum()), nS)},
                        "note": "closing price is the closing-auction price; exchange VWAP = turnover/volume (bhavcopy)"}
for tid, kk, nm in (("V02", 7, "11:15"), ("V03", 15, "13:15")):
    s_state = np.log(C[:, kk] / vwap_run[:, kk])
    out_ = np.log(Coff / C[:, kk])
    rr, pp = stats.spearmanr(s_state, out_)
    register(tid, f"Spearman(price-vs-VWAP at {nm}, rest of day)", pp, nS, {"observed": float(rr)})
    lev[f"vwap_checkpoint_{nm}"] = {"spearman": float(rr), "p": float(pp), "ci95_bootstrap_pearson": corr_boot(s_state, out_), "pearson": float(stats.pearsonr(s_state, out_)[0]), "n": nS,
                                    "share_above_vwap_at_checkpoint": float(np.mean(s_state > 0)),
                                    "mean_rest_pct_if_above": float(100 * out_[s_state > 0].mean()), "n_above": int((s_state > 0).sum()), "mean_rest_pct_if_below": float(100 * out_[s_state <= 0].mean()), "n_below": int((s_state <= 0).sum())}
# time spent above running VWAP per slot
lev["share_sessions_close_above_running_vwap_by_slot"] = {times[k]: float(np.nanmean(C[:, k] > vwap_run[:, k])) for k in (3, 7, 11, 15, 19, 22, 23)}
# side persistence relative to previous close
pers = {}
for k in (3, 7, 11, 15, 19):
    side_k = np.sign(C[:, k] - prev)
    same = side_k == np.sign(Coff - prev)
    pers[f"state_at_{(555 + 15 * (k + 1)) // 60:02d}:{(555 + 15 * (k + 1)) % 60:02d}"] = {"k": int(same.sum()), "n": nS, "share": float(same.mean()), "wilson95": wilson(int(same.sum()), nS)}
lev["close_side_vs_prev_close_same_as_at_checkpoint"] = pers
# touch tests: sigma_i = RMS of daily I over previous 20 sessions
dI = np.log(daily["close"] / daily["open"])
sig20 = np.sqrt((dI ** 2).rolling(20).mean().shift(1))
sig_i = sig20.loc[dates].values
assert not np.isnan(sig_i).any()
prevH = (daily["high"].shift(1) / daily["ca_factor"]).loc[dates].values
prevL = (daily["low"].shift(1) / daily["ca_factor"]).loc[dates].values


def touch_test(tid, label, obs, dist, mask=None):
    mask = np.ones(nS, bool) if mask is None else mask
    d_ = dist[mask]
    pr = np.where(d_ <= 0, 1.0, 2 * (1 - stats.norm.cdf(np.maximum(d_, 1e-12) / sig_i[mask])))
    ob = obs[mask]
    p, ex, sd = pb_two_sided(int(ob.sum()), pr)
    register(tid, label, p, int(mask.sum()), {"observed": float(ob.sum()), "benchmark": ex})
    return {"n": int(mask.sum()), "touched": int(ob.sum()), "touch_share": float(ob.mean()), "wilson95": wilson(int(ob.sum()), int(mask.sum())), "expected_touches_reflection_benchmark": ex, "expected_share": ex / mask.sum(), "benchmark_sd": sd, "p_two_sided": p}


gap_dist = np.abs(np.log(prev / Ooff))
touch_prev = np.where(G > 0, Loff <= prev, np.where(G < 0, Hoff >= prev, True))
lev["touch_previous_close_gap_fill"] = touch_test("L01", "touch of prev close (G != 0)", touch_prev, gap_dist, gnz)
dist_H = np.log(prevH / Ooff)
dist_L = np.log(Ooff / prevL)
lev["touch_previous_day_high"] = touch_test("L02", "touch prev-day high", Hoff >= prevH - 1e-9, dist_H)
lev["touch_previous_day_low"] = touch_test("L03", "touch prev-day low", Loff <= prevL + 1e-9, dist_L)
lev["touch_previous_day_high"]["open_already_above_level"] = int((dist_H <= 0).sum())
lev["touch_previous_day_low"]["open_already_below_level"] = int((dist_L <= 0).sum())
lev["touch_note"] = "benchmark = zero-drift reflection principle from the official open with sigma_i = RMS of the previous 20 daily open-to-close log returns; it ignores jumps, fat tails and the overnight gap beyond the open."
# gap fill and extreme formation by gap sign (descriptive)
lev["gap_fill_by_sign"] = {"gap_up": {"n": int((G > 0).sum()), "filled": int(touch_prev[G > 0].sum())}, "gap_down": {"n": int((G < 0).sum()), "filled": int(touch_prev[G < 0].sum())}}
# long daily history: prev-day high/low touch calibration with the previous CLOSE as origin (relevant for 14-Oct: origin P0)
dd = daily.copy()
sigR = np.sqrt((np.log(dd["close"] / dd["prev"]) ** 2).rolling(20).mean().shift(1))
pH = dd["high"].shift(1) / dd["ca_factor"]
pL = dd["low"].shift(1) / dd["ca_factor"]
hist = pd.DataFrame({"dH": np.log(pH / dd["prev"]), "dL": np.log(dd["prev"] / pL), "tH": dd["high"] >= pH - 1e-9, "tL": dd["low"] <= pL + 1e-9, "sig": sigR}).dropna()
hist["xH"], hist["xL"] = hist["dH"] / hist["sig"], hist["dL"] / hist["sig"]
hist["bH"] = np.where(hist["xH"] <= 0, 1.0, 2 * (1 - stats.norm.cdf(hist["xH"].clip(lower=1e-9))))
hist["bL"] = np.where(hist["xL"] <= 0, 1.0, 2 * (1 - stats.norm.cdf(hist["xL"].clip(lower=1e-9))))
cut = hist.index[int(len(hist) * 0.6)]
sigma_14 = float(np.sqrt((np.log(daily["close"] / daily["prev"]) ** 2).tail(20).mean()))  # known at the cutoff
P0 = 3375.40
x14H, x14L = math.log(3403.2 / P0) / sigma_14, math.log(P0 / 3290.2) / sigma_14


def calib(h, col_x, col_t, col_b, centre, width):
    s = h[(h[col_x] >= centre - width) & (h[col_x] <= centre + width)]
    return {"n": int(len(s)), "touch_share": float(s[col_t].mean()) if len(s) else None, "wilson95": wilson(int(s[col_t].sum()), len(s)), "benchmark_mean": float(s[col_b].mean()) if len(s) else None}


lev["long_history_prev_close_origin"] = {"n_sessions": int(len(hist)), "first": str(hist.index.min().date()), "last": str(hist.index.max().date()), "split_date_60_40": str(cut.date()),
                                         "sigma_R_trailing20_at_cutoff_pct": 100 * sigma_14, "levels_14oct_in_sigma": {"prev_high_3403.2": x14H, "prev_low_3290.2": x14L,
                                                                                                                             "distance_to_high_pct": 100 * math.log(3403.2 / P0), "distance_to_low_pct": 100 * math.log(3290.2 / P0)}}
for nm, hh in (("all", hist), ("first60pct", hist[hist.index < cut]), ("last40pct", hist[hist.index >= cut])):
    lev["long_history_prev_close_origin"][nm] = {
        "touch_prev_high": {"n": int(len(hh)), "observed_share": float(hh["tH"].mean()), "benchmark_share": float(hh["bH"].mean()), "wilson95": wilson(int(hh["tH"].sum()), len(hh))},
        "touch_prev_low": {"observed_share": float(hh["tL"].mean()), "benchmark_share": float(hh["bL"].mean()), "wilson95": wilson(int(hh["tL"].sum()), len(hh))},
        "near_14oct_high_distance (|x - %.2f| <= 0.15 sigma)" % x14H: calib(hh, "xH", "tH", "bH", x14H, 0.15),
        "near_14oct_low_distance (|x - %.2f| <= 0.20 sigma)" % x14L: calib(hh, "xL", "tL", "bL", x14L, 0.20)}
# sensitivity: the v1 sigma_R of 2.48%/day instead of the trailing-20 RMS at the cutoff
x14H_v1, x14L_v1 = math.log(3403.2 / P0) / 0.0248, math.log(P0 / 3290.2) / 0.0248
lev["long_history_prev_close_origin"]["sensitivity_sigma_2.48pct"] = {"x_high": x14H_v1, "x_low": x14L_v1, "near_high": calib(hist, "xH", "tH", "bH", x14H_v1, 0.15), "near_low": calib(hist, "xL", "tL", "bL", x14L_v1, 0.20)}
bins = [-np.inf, 0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, np.inf]
for side, xc, tc, bc in (("high", "xH", "tH", "bH"), ("low", "xL", "tL", "bL")):
    tab = []
    hh = hist.copy()
    hh["bin"] = pd.cut(hh[xc], bins)
    for bn, g in hh.groupby("bin", observed=True):
        tab.append({"bin_sigma": str(bn), "n": int(len(g)), "observed": float(g[tc].mean()), "benchmark": float(g[bc].mean()), "wilson95": wilson(int(g[tc].sum()), len(g))})
    lev["long_history_prev_close_origin"][f"calibration_by_distance_{side}"] = tab


# --- added after the first run, each DEFINED before being computed ---------------------------------------------------------------
# R01/R02 (registered): rejection vs breakthrough at the previous-day extremes on the long daily history (previous-close origin).
#   R01: sessions whose open is below the previous-day high and whose high touched it; breakthrough = close above the level.
#        Under a zero-drift continuous martingale P(close beyond level | touched) = 0.5 exactly (reflection principle); a rejection
#        ("resistance") regularity means P < 0.5.  R02 mirrors this for the previous-day low (open above, low touched, close below).
#   exact two-sided binomial vs 0.5 on the full history; chronological split 60/40 reported (direction fixed by the first 60%).
# F1 (not registered, descriptive): gap-fill calibration of the reflection benchmark on the long history, by period and gap size.
# F2 (not registered, descriptive): sign(G)*I for small/large gaps on the long history by period (contrary check of C04).
dd2 = dd.assign(pH=pH, pL=pL).dropna(subset=["pH", "pL"])
selH = (dd2["open"] < dd2["pH"]) & (dd2["high"] >= dd2["pH"] - 1e-9)
selL = (dd2["open"] > dd2["pL"]) & (dd2["low"] <= dd2["pL"] + 1e-9)
brk = {"R01": (dd2["close"] > dd2["pH"])[selH], "R02": (dd2["close"] < dd2["pL"])[selL]}
cut2 = dd2.index[int(len(dd2) * 0.6)]
rej: dict = {}
for tid, lab in (("R01", "previous-day HIGH: P(close above | touched from below)"), ("R02", "previous-day LOW: P(close below | touched from above)")):
    x_ = brk[tid]
    k_, n_ = int(x_.sum()), int(len(x_))
    p_ = binom2(k_, n_, 0.5)
    register(tid, lab, p_, n_, {"observed": k_ / n_, "benchmark": 0.5})
    a_, b_ = x_[x_.index < cut2], x_[x_.index >= cut2]
    w_ = x_[x_.index >= dates[0]]
    rej[tid] = {"label": lab, "n_touch": n_, "breakthrough_share": k_ / n_, "wilson95": wilson(k_, n_), "p_binom_vs_0.5": p_,
                "first60pct": {"n": int(len(a_)), "share": float(a_.mean()), "wilson95": wilson(int(a_.sum()), len(a_)), "p": binom2(int(a_.sum()), len(a_), 0.5)},
                "last40pct": {"n": int(len(b_)), "share": float(b_.mean()), "wilson95": wilson(int(b_.sum()), len(b_)), "p": binom2(int(b_.sum()), len(b_), 0.5)},
                "union_window_sessions": {"n": int(len(w_)), "breakthrough": int(w_.sum())}}
# drift-adjusted benchmark (descriptive follow-up, not registered): BM with drift mu_i (trailing-250 mean of daily open->close log return) and vol sigma_i
# (trailing-20 RMS) from the open; closed form P(X_T > a | max >= a) = P(X_T > a) / P(max >= a) for a level a above the open.
_Ihist = np.log(dd["close"] / dd["open"])
mu250 = _Ihist.rolling(250, min_periods=100).mean().shift(1)
sig20h = np.sqrt((_Ihist ** 2).rolling(20).mean().shift(1))


def cond_break(a, mu, sg):
    pT = 1 - stats.norm.cdf((a - mu) / sg)
    pM = pT + np.exp(2 * mu * a / sg ** 2) * stats.norm.cdf((-a - mu) / sg)
    return pT / pM


for tid, sel_, up in (("R01", selH, True), ("R02", selL, False)):
    sub = dd2[sel_].assign(mu=mu250, sg=sig20h).dropna(subset=["mu", "sg"])
    a_ = np.log(sub["pH"] / sub["open"]) if up else np.log(sub["open"] / sub["pL"])
    pr_ = cond_break(a_.values, (sub["mu"] if up else -sub["mu"]).values, sub["sg"].values)
    ob_ = brk[tid].loc[sub.index]
    pp_, ex_, sd_ = pb_two_sided(int(ob_.sum()), pr_)
    rej[tid]["drift_adjusted_benchmark"] = {"n": int(len(sub)), "observed_breakthroughs": int(ob_.sum()), "observed_share": float(ob_.mean()), "expected_share": float(ex_ / len(sub)), "benchmark_sd_count": float(sd_), "p_two_sided_descriptive": pp_,
                                            "mean_drift_mu_pct_per_day": float(100 * sub["mu"].mean()),
                                            "first60pct": {"n": int((sub.index < cut2).sum()), "observed_share": float(ob_[sub.index < cut2].mean()), "expected_share": float(pr_[sub.index < cut2].mean())},
                                            "last40pct": {"n": int((sub.index >= cut2).sum()), "observed_share": float(ob_[sub.index >= cut2].mean()), "expected_share": float(pr_[sub.index >= cut2].mean())}}
rej["split_date"] = str(cut2.date())
rej["n_history_sessions"] = int(len(dd2))
lev["rejection_vs_breakthrough_long_history"] = rej
Gh = np.log(dd["open"] / dd["prev"])
Ih = np.log(dd["close"] / dd["open"])
sigIh = np.sqrt((Ih ** 2).rolling(20).mean().shift(1))
hf = pd.DataFrame({"G": Gh, "I": Ih, "sig": sigIh, "low": dd["low"], "high": dd["high"], "prev": dd["prev"], "open": dd["open"]}).dropna()
hf = hf[hf["G"] != 0].copy()
hf["touch"] = np.where(hf["G"] > 0, hf["low"] <= hf["prev"], hf["high"] >= hf["prev"])
hf["bench"] = 2 * (1 - stats.norm.cdf(np.abs(np.log(hf["prev"] / hf["open"])) / hf["sig"]))
medh = hf.loc[hf.index < dates[0], "G"].abs().median()
hf["small"] = hf["G"].abs() < medh
hf["aligned"] = np.sign(hf["G"]) * hf["I"]


def fill_row(h):
    return {"n": int(len(h)), "observed_fill_share": float(h["touch"].mean()), "benchmark_share": float(h["bench"].mean()), "wilson95": wilson(int(h["touch"].sum()), len(h))}


def cont_row(h):
    return {"n": int(len(h)), "mean_signG_x_I_pct": float(100 * h["aligned"].mean()), "share_I_in_gap_direction": float((h["aligned"] > 0).mean()), "p_t": float(stats.ttest_1samp(h["aligned"], 0.0).pvalue) if len(h) > 2 else None}


pre_ = hf[hf.index < dates[0]]
periods = {"pre_window_2017_to_2026-08-17": pre_, "2017-2020": hf.loc["2017":"2020"], "2021-2023": hf.loc["2021":"2023"], "2024-to-2026-08-17": hf.loc["2024":"2026-08-17"], "2025-05-24-to-2026-08-17": hf.loc["2025-05-24":"2026-08-17"],
           "union_window": hf[hf.index >= dates[0]]}
lev["follow_up_F1_gap_fill_calibration_long_history"] = {nm: {"all": fill_row(h), "small_gap": fill_row(h[h["small"]]), "large_gap": fill_row(h[~h["small"]])} for nm, h in periods.items()}
lev["follow_up_F1_gap_fill_calibration_long_history"]["median_abs_G_pre_window_pct"] = float(100 * medh)
lev["follow_up_F2_gap_continuation_long_history"] = {nm: {"all": cont_row(h), "small_gap": cont_row(h[h["small"]]), "large_gap": cont_row(h[~h["small"]])} for nm, h in periods.items()}
lev["follow_up_note"] = "pre-2026-08-03 closes are 30-minute VWAP, not the closing-auction price, so open-to-close in the long history is not the same quantity as in the union window"
RES["levels"] = lev

# ----------------------------------------------------------------------------------------------------- 9. (5) auction bar
au: dict = {}
m25 = has15
a_move = np.log(C[m25, 24] / O[m25, 24])
b_move = np.log(O[m25, 24] / C[m25, 23])
c_move = np.log(C[m25, 24] / C[m25, 23])
r1500 = np.log(C[m25, 23] / C[m25, 22])
typical_abs = np.nanmean(np.abs(RET[:, 8:23]))
pa, ppa = stats.pearsonr(r1500, a_move)
register("A01", "corr(15:00 bar return, auction-bar move)", ppa, int(m25.sum()), {"observed": float(pa)})
t_a = stats.ttest_1samp(a_move, 0.0)
register("A02", "mean auction-bar move ln(C/O)", t_a.pvalue, int(m25.sum()), {"observed": float(a_move.mean())})
au["definitions"] = {"auction_move": "ln(C_15:15bar / O_15:15bar)", "gap_between_bars": "ln(O_15:15bar / C_15:00bar)", "move_from_1500_close": "ln(C_15:15bar / C_15:00bar) = ln(official close / 15:00 close)", "window_all_sessions": "ln(official close / C_14:45bar)"}
au["n_sessions_with_1515_bar"] = int(m25.sum())
au["auction_move_pct"] = {**summ(a_move), "mean_abs_pct": float(100 * np.mean(np.abs(a_move))), "ci95_mean_abs_iid": [100 * v for v in ci_stat(np.abs(a_move))], "median_abs_pct": float(100 * np.median(np.abs(a_move))),
                          "p90_abs_pct": float(100 * np.quantile(np.abs(a_move), .9)), "max_abs_pct": float(100 * np.abs(a_move).max()), "share_zero": float(np.mean(a_move == 0)),
                          "share_abs_ge_0.25pct": float(np.mean(np.abs(a_move) >= 0.0025)), "share_abs_ge_0.5pct": float(np.mean(np.abs(a_move) >= 0.005)),
                          "share_positive": float(np.mean(a_move > 0)), "p_mean_t": float(t_a.pvalue)}
au["gap_between_1500_close_and_1515_open_pct"] = {**summ(b_move), "mean_abs_pct": float(100 * np.mean(np.abs(b_move)))}
au["move_from_1500_close_to_official_close_pct"] = {**summ(c_move), "mean_abs_pct": float(100 * np.mean(np.abs(c_move))), "ci95_mean_abs_iid": [100 * v for v in ci_stat(np.abs(c_move))]}
au["comparison_scale"] = {"typical_abs_15min_close_to_close_return_1115_to_1500_pct": float(100 * typical_abs), "abs_15_00_bar_return_pure_sessions_pct": float(100 * np.mean(np.abs(r1500))),
                          "ratio_mean_abs_auction_move_to_typical_15min": float(np.mean(np.abs(a_move)) / typical_abs), "ratio_mean_abs_move_from_1500_close_to_typical_15min": float(np.mean(np.abs(c_move)) / typical_abs)}
au["corr_1500_bar_return_vs_auction_move"] = {"pearson": float(pa), "p": float(ppa), "ci95_bootstrap": corr_boot(r1500, a_move), "n": int(m25.sum()), "spearman": float(stats.spearmanr(r1500, a_move)[0]),
                                              "share_auction_move_reverses_1500_bar_direction": float(np.mean(np.sign(a_move[(a_move != 0) & (r1500 != 0)]) != np.sign(r1500[(a_move != 0) & (r1500 != 0)]))),
                                              "n_nonzero_pairs": int(((a_move != 0) & (r1500 != 0)).sum())}
w_all = RETC
au["window_1445_close_to_official_close_all_sessions_pct"] = {**summ(w_all), "mean_abs_pct": float(100 * np.mean(np.abs(w_all))), "ci95_mean_abs_iid": [100 * v for v in ci_stat(np.abs(w_all))],
                                                           "typical_abs_30min_return_pct_1115_1445": float(100 * np.mean([np.nanmean(np.abs(np.log(C[:, k + 1] / C[:, k - 1]))) for k in range(8, 22, 2)]))}
vz = V[m25, 24] == 0
au["zero_volume_vs_positive_volume_1515_bar"] = {"n_zero": int(vz.sum()), "n_positive": int((~vz).sum()), "mean_abs_auction_move_pct_zero_volume": float(100 * np.mean(np.abs(a_move[vz]))), "mean_abs_auction_move_pct_positive_volume": float(100 * np.mean(np.abs(a_move[~vz]))),
                                                 "note": "volume in this bar is feed volume, not the auction volume (auction volume is not identifiable in this dataset)"}
unattr = 1 - ratio
pit["bar_volume_vs_nse_daily"]["corr_unattributed_share_vs_abs_auction_move"] = float(stats.pearsonr(unattr[m25], np.abs(a_move))[0])
pit["bar_volume_vs_nse_daily"]["corr_unattributed_share_vs_abs_auction_move_p"] = float(stats.pearsonr(unattr[m25], np.abs(a_move))[1])
# sensitivity: add the 15:15 bars of validator-failed sessions (valid individual bars)
sens = []
rawk = raw.assign(slot=raw["time"].map(lambda t: (int(t[:2]) * 60 + int(t[3:]) - 555) // 15))
for e in excluded:
    dday = pd.Timestamp(e["date"])
    g = rawk[rawk["date"] == dday].set_index("slot")
    if 24 in g.index:
        sens.append({"date": e["date"], "failed_checks": e["failed_checks"], "auction_move_pct": float(100 * np.log(g.loc[24, "close"] / g.loc[24, "open"])), "move_from_1500_close_pct": float(100 * np.log(g.loc[24, "close"] / g.loc[23, "close"]))})
am2 = np.append(a_move, [s["auction_move_pct"] / 100 for s in sens])
cm2 = np.append(c_move, [s["move_from_1500_close_pct"] / 100 for s in sens])
au["sensitivity_including_failed_sessions_1515_bars"] = {"added": sens, "n": int(len(am2)), "mean_abs_auction_move_pct": float(100 * np.mean(np.abs(am2))), "mean_abs_move_from_1500_close_pct": float(100 * np.mean(np.abs(cm2))),
                                                        "note": "10-Sep fails the validator ONLY on the bar-continuity rule: its 15:15 bar opens at the auction price (3306.0 vs 15:00 close 3286.1 = +0.60%), i.e. a large genuine auction jump is excluded by that rule"}
au["identity_with_official_close"] = {"n_sessions": nS, "last_bar_close_equals_official_close": pit["last_bar_close_equals_official_close_all_sessions"], "daily_last_equals_close": pit["daily_file_last_equals_close"]}
au["largest_auction_moves"] = [{"date": str(np.array(dates)[m25][i].date()), "auction_move_pct": float(100 * a_move[i]), "from_1500_close_pct": float(100 * c_move[i]), "vol_1515": int(V[m25, 24][i])} for i in np.argsort(-np.abs(c_move))[:6]]
RES["auction"] = au

# ----------------------------------------------------------------------------------------------------- 10. (6) anatomy and largest-volume bars
def loo_slot_median(i, k):
    m = np.ones(nS, bool)
    m[i] = False
    v = V[m, k]
    return float(np.nanmedian(v))


def anatomy(day):
    i = dates.index(pd.Timestamp(day))
    rows = []
    run_h, run_l = -np.inf, np.inf
    for k in range(25):
        if np.isnan(C[i, k]):
            continue
        run_h, run_l = max(run_h, H[i, k]), min(run_l, L[i, k])
        med = loo_slot_median(i, k)
        rows.append({"bar_start": times[k], "open": float(O[i, k]), "high": float(H[i, k]), "low": float(L[i, k]), "close": float(C[i, k]), "volume": int(V[i, k]), "vol_x_slot_median_other_sessions": float(V[i, k] / med) if med > 0 else None,
                     "vol_share_pct": float(100 * V[i, k] / tot_vol[i]), "cum_vol_share_pct": float(100 * np.nansum(V[i, :k + 1]) / tot_vol[i]), "ret_close_to_close_pct": float(100 * RET[i, k]) if not np.isnan(RET[i, k]) else None,
                     "range_pct": float(100 * RNG[i, k]), "running_high": float(run_h), "running_low": float(run_l), "running_vwap": float(vwap_run[i, k]), "close_vs_running_vwap_pct": float(100 * np.log(C[i, k] / vwap_run[i, k]))})
    return {"date": day, "prev_close": float(prev[i]), "official_open": float(Ooff[i]), "official_high": float(Hoff[i]), "official_low": float(Loff[i]), "official_close": float(Coff[i]), "G_pct": float(100 * G[i]), "FH_pct": float(100 * FH[i]), "Rest_pct": float(100 * REST[i]),
            "I_pct": float(100 * I[i]), "R_pct": float(100 * np.log(Coff[i] / prev[i])), "first_bar_open": float(O[i, 0]), "bars_sum_volume": int(tot_vol[i]), "official_volume": int(D["vol"].values[i]), "high_slot": times[hi_slot[i]], "low_slot": times[lo_slot[i]],
            "range_share_by_1015": float(RS1015[i]), "range_share_by_1115": float(RS1115[i]), "close_position_in_official_range": float((Coff[i] - Loff[i]) / (Hoff[i] - Loff[i])), "exchange_vwap": float(vwap_ex[i]), "bars": rows}


an13 = anatomy("2026-10-13")
an29 = anatomy("2026-09-29")
i13 = dates.index(pd.Timestamp("2026-10-13"))
xl_idx = [i for i, d_ in enumerate(dates) if d_ in xl_days and i != i13]
an13["spike_1415_bar_vs_other_19_workbook_sessions"] = {"slot_median_volume": float(np.nanmedian(V[xl_idx, 20])), "ratio": float(V[i13, 20] / np.nanmedian(V[xl_idx, 20])), "n_other": len(xl_idx)}
an13["volume_share_1415_to_1515_pct"] = float(100 * np.nansum(V[i13, 20:24]) / tot_vol[i13])
others = [i for i in range(nS) if i != i13]
sh_late = np.array([np.nansum(V[i, 20:25]) / tot_vol[i] for i in range(nS)])
an13["late_volume_share_1415_1530_percentile_among_sessions"] = {"value_pct": float(100 * sh_late[i13]), "rank_desc": int((sh_late > sh_late[i13]).sum() + 1), "of": nS, "median_other_sessions_pct": float(100 * np.median(sh_late[others])),
                                                                 "median_other_sessions_ex_0929_pct": float(100 * np.median(sh_late[[i for i in others if i not in idx0929]]))}
an13["range_share_by_1015_rank"] = {"value": float(RS1015[i13]), "rank_asc_among_sessions": int((RS1015 < RS1015[i13]).sum() + 1), "of": nS}
an13["bars_vs_official_extremes"] = {"bar_max_high": float(np.nanmax(H[i13])), "official_high": float(Hoff[i13]), "bar_min_low": float(np.nanmin(L[i13])), "official_low": float(Loff[i13])}
an29["note"] = "15:15 bar absent; the 15:00 bar close 3200.0 equals the official close and the 15:00 bar volume (22.5M) is 75% of NSE daily volume"
an29["share_of_daily_volume_in_1500_bar_pct"] = float(100 * V[dates.index(pd.Timestamp('2026-09-29')), 23] / D["vol"].values[dates.index(pd.Timestamp('2026-09-29'))])
vol_ratio_slot = np.full((nS, 25), np.nan)
for i in range(nS):
    for k in range(25):
        if not np.isnan(V[i, k]):
            med = loo_slot_median(i, k)
            vol_ratio_slot[i, k] = V[i, k] / med if med > 0 else np.nan
flat = [(V[i, k], i, k) for i in range(nS) for k in range(25) if not np.isnan(V[i, k])]
top_vol = sorted(flat, reverse=True)[:12]


def bar_row(i, k):
    nxt = float(100 * RET[i, k + 1]) if k + 1 < 25 and not np.isnan(RET[i, k + 1]) else None
    return {"date": str(dates[i].date()), "bar_start": times[k], "volume": int(V[i, k]), "vol_x_slot_median_other_sessions": float(vol_ratio_slot[i, k]), "ret_pct": float(100 * RET[i, k]), "range_pct": float(100 * RNG[i, k]), "next_bar_ret_pct": nxt,
            "same_direction_as_bar_next_bar": (None if nxt is None or RET[i, k] == 0 else bool(np.sign(RET[i, k + 1]) == np.sign(RET[i, k]))), "session_R_pct": float(100 * np.log(Coff[i] / prev[i])), "session_vol_share_pct": float(100 * V[i, k] / tot_vol[i])}


top_ratio = sorted([(vol_ratio_slot[i, k], i, k) for i in range(nS) for k in range(24) if not np.isnan(vol_ratio_slot[i, k])], reverse=True)[:12]
spikes = [(i, k) for i in range(nS) for k in range(24) if not np.isnan(vol_ratio_slot[i, k]) and vol_ratio_slot[i, k] >= 5 and RNG[i, k] >= 0.02]
tot_ret_after = []
for (i, k) in spikes:
    if k + 1 < 24 and not np.isnan(C[i, k + 1]):
        tot_ret_after.append((str(dates[i].date()), times[k], float(100 * np.log(Coff[i] / C[i, k])), float(100 * np.log(C[i, k] / O[i, k]))))
RES["anatomy"] = {"session_2026-10-13": an13, "session_2026-09-29": an29, "top12_bars_by_volume": [bar_row(i, k) for _, i, k in top_vol], "top12_bars_by_ratio_to_slot_median": [bar_row(i, k) for _, i, k in top_ratio],
                  "spike_rule_fixed_in_advance": "volume >= 5x slot median of other sessions and bar range >= 2%", "spike_bars": [bar_row(i, k) for i, k in spikes],
                  "spike_bars_then_move_to_official_close_pct": tot_ret_after,
                  "largest_sessions_by_volume": [{"date": str(dates[i].date()), "volume_nse": int(D["vol"].values[i]), "x_median_session": float(D["vol"].values[i] / np.median(D["vol"].values)), "R_pct": float(100 * np.log(Coff[i] / prev[i]))} for i in np.argsort(-D["vol"].values)[:6]]}

# ----------------------------------------------------------------------------------------------------- 11. (7) v1 recomputation
def v1_stats(bars: pd.DataFrame) -> dict:
    """verbatim logic of src/intraday_profile.py (v1) on a bar frame with columns date, open, high, low, close, volume sorted by time."""
    rows = []
    for day, g in bars.groupby("date"):
        g = g.reset_index(drop=True)
        if len(g) < 24:
            continue
        tot = g["volume"].sum()
        tp_ = (g["high"] + g["low"] + g["close"]) / 3
        vwap = float((tp_ * g["volume"]).sum() / tot)
        hi_i, lo_i = int(g["high"].idxmax()), int(g["low"].idxmin())
        rng_ = g["high"].max() - g["low"].min()
        fh = g.iloc[:4]
        r_fh = float(np.log(fh["close"].iloc[-1] / fh["open"].iloc[0]))
        r_rest = float(np.log(g["close"].iloc[-1] / fh["close"].iloc[-1]))
        rows.append({"vol_first_bar": g["volume"].iloc[0] / tot, "vol_first_hour": fh["volume"].sum() / tot, "vol_last_hour": g["volume"].iloc[-4:].sum() / tot, "vol_last_bar": g["volume"].iloc[-1] / tot, "hi_bar": hi_i, "lo_bar": lo_i,
                     "r_fh": r_fh, "r_rest": r_rest, "range_share_by_1015": (fh["high"].max() - fh["low"].min()) / rng_, "close_vs_vwap": float(g["close"].iloc[-1] / vwap - 1), "last_bar_move": float(np.log(g["close"].iloc[-1] / g["close"].iloc[-2]))})
    S = pd.DataFrame(rows)
    n = len(S)
    o = {"n_sessions": n}
    o["volume_share_first_bar_pct"] = float(100 * S["vol_first_bar"].mean()); o["volume_share_first_hour_pct"] = float(100 * S["vol_first_hour"].mean())
    o["volume_share_last_hour_pct"] = float(100 * S["vol_last_hour"].mean()); o["volume_share_last_bar_1515_pct"] = float(100 * S["vol_last_bar"].mean())
    o["high_in_first_hour_share"] = float((S["hi_bar"] < 4).mean()); o["low_in_first_hour_share"] = float((S["lo_bar"] < 4).mean())
    o["high_in_last_hour_share"] = float((S["hi_bar"] >= 21).mean()); o["low_in_last_hour_share"] = float((S["lo_bar"] >= 21).mean())
    o["high_or_low_in_first_hour_share"] = float(((S["hi_bar"] < 4) | (S["lo_bar"] < 4)).mean())
    o["median_range_share_formed_by_10:15"] = float(S["range_share_by_1015"].median())
    r_, p_ = stats.pearsonr(S["r_fh"], S["r_rest"]); o["corr_firsthour_vs_restofday"] = {"r": float(r_), "p": float(p_), "n": n}
    o["P(rest-of-day continues first-hour direction)"] = float((np.sign(S["r_fh"]) == np.sign(S["r_rest"])).mean())
    o["P(close above bar-VWAP)"] = float((S["close_vs_vwap"] > 0).mean())
    o["last_bar_1515_abs_move_mean_pct"] = float(100 * S["last_bar_move"].abs().mean()); o["last_bar_1515_move_mean_pct"] = float(100 * S["last_bar_move"].mean())
    return o


v1_json = json.load(open("results/intraday_profile.json"))
val_old = pd.read_csv("data/processed/intraday_validation.csv", parse_dates=["date"]).set_index("date")["status"]
v1_days = [d_ for d_, s in val_old.items() if s == "PASS"]
raw_v1 = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("data/raw/intraday/*.csv"))]).drop_duplicates("ts").dropna().sort_values("ts")
raw_v1["date"] = pd.to_datetime(raw_v1["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None).dt.normalize()
repro = v1_stats(raw_v1[raw_v1["date"].isin(v1_days)])
diff_keys = {k: (repro[k], v1_json[k]) for k in v1_json if k not in ("first", "last") and (abs(repro[k] - v1_json[k]) > 1e-9 if not isinstance(v1_json[k], dict) else any(abs(repro[k][kk] - v1_json[k][kk]) > 1e-9 for kk in ("r", "p", "n")))}
union_v1def = v1_stats(U[["date", "open", "high", "low", "close", "volume"]])
# corrected definitions on the union
last_hour_share = np.nansum(VS[:, 21:25], axis=1)
corr = {
    "n_sessions": nS,
    "volume_share_first_bar_pct": float(100 * np.nanmean(VS[:, 0])),
    "volume_share_first_hour_pct": float(100 * np.nansum(VS[:, :4], axis=1).mean()),
    "volume_share_last_hour_1430_1530_pct": float(100 * last_hour_share.mean()),
    "volume_share_1500_bar_pct_sessions_with_1515": float(100 * VS[has15, 23].mean()),
    "volume_share_1500_plus_1515_all_sessions_pct": float(100 * combined_1500.mean()),
    "volume_share_1515_bar_pct_sessions_with_it": float(100 * VS[has15, 24].mean()),
    "volume_share_1515_bar_pct_all_sessions_missing_as_zero": float(100 * np.nansum(VS[:, 24:25], axis=1).mean()),
    "high_in_first_hour_share": float(tm["high"]["first_hour"]["share"]), "low_in_first_hour_share": float(tm["low"]["first_hour"]["share"]),
    "high_in_last_hour_share": float(tm["high"]["last_hour"]["share"]), "low_in_last_hour_share": float(tm["low"]["last_hour"]["share"]),
    "high_or_low_in_first_hour_share": float(tm["high_or_low_in_first_hour"]["share"]),
    "median_range_share_formed_by_10:15": float(np.median(RS1015)),
    "corr_FH_official_open_vs_rest": float(r_p), "P(sign Rest = sign FH)": k_agree / n_nz,
    "P(close above exchange VWAP)": float(above_ex.mean()), "P(close above bar-VWAP)": float(above_bar.mean()),
    "auction_bar_abs_move_mean_pct_within_bar": au["auction_move_pct"]["mean_abs_pct"], "auction_bar_move_mean_pct_within_bar": au["auction_move_pct"]["mean"],
    "move_from_1500_close_to_official_close_abs_mean_pct": au["move_from_1500_close_to_official_close_pct"]["mean_abs_pct"], "move_from_1500_close_to_official_close_mean_pct": au["move_from_1500_close_to_official_close_pct"]["mean"],
    "window_1445_close_to_official_close_abs_mean_pct_all_sessions": au["window_1445_close_to_official_close_all_sessions_pct"]["mean_abs_pct"]}
RES["v1_comparison"] = {"v1_json": v1_json, "v1_code_reproduced_on_v1_sample": {"n": repro["n_sessions"], "differences_vs_published_json": diff_keys, "reproduces_exactly": len(diff_keys) == 0},
                        "v1_definitions_on_union": union_v1def, "corrected_definitions_on_union": corr,
                        "defects_in_v1_definitions": [
                            "volume_share_last_bar_1515_pct = volume of the LAST ROW / total: that row is the 15:15 bar in 28 sessions but the 15:00 bar in 8 sessions (feed omits 15:15), so the 4.4% mixes two different bars; the pure 15:15 bar share is 0.87% (v1's own time-profile csv) and the 15:00 bar is ~9%",
                            "volume_share_last_hour_pct uses the last four ROWS: 14:30-15:15 in 28 sessions but 14:15-15:00 in 8 sessions (misaligned)",
                            "last_bar_1515_abs_move = |ln(close[-1]/close[-2])|: for 15:15-bar sessions it is |ln(official close/15:00 close)| (includes the jump between the 15:00 close and the 15:15 bar open), for 24-bar sessions it is the 15:00 bar's own close-to-close move; neither is the within-bar auction move",
                            "first-hour return starts at the first printed bar open (not the official open); the 'rest' leg is unaffected",
                            "P(close above bar-VWAP) uses typical-price bar VWAP, which differs from the exchange VWAP (turnover/volume) by 6 bps on average and by -36 bps on 29-Sep"]}
for k_ in ("volume_share_first_bar_pct", "volume_share_first_hour_pct"):
    pass

# ----------------------------------------------------------------------------------------------------- 12. power
def power_corr(n, rho, alpha=0.05):
    z = np.arctanh(rho) * math.sqrt(n - 3)
    zc = stats.norm.ppf(1 - alpha / 2)
    return float(stats.norm.sf(zc - z) + stats.norm.cdf(-zc - z))


def power_binom(n, p1, p0=0.5, alpha=0.05):
    ks = np.arange(n + 1)
    pm = stats.binom.pmf(ks, n, p0)
    rej = np.array([stats.binomtest(int(k), n, p0).pvalue < alpha for k in ks])
    return float((stats.binom.pmf(ks, n, p1) * rej).sum())


r_crit = lambda n: float(math.tanh(stats.norm.ppf(0.975) / math.sqrt(n - 3)))
RES["power"] = {"n_sessions": nS,
                "corr_critical_abs_r_5pct": r_crit(nS), "corr_power_rho_0.3": power_corr(nS, 0.3), "corr_power_rho_0.5": power_corr(nS, 0.5),
                "sign_test_power_p1_0.6_n36": power_binom(36, 0.6), "sign_test_power_p1_0.7_n36": power_binom(36, 0.7),
                "walk_forward_hit_rate_power_p1_0.6_n27": power_binom(27, 0.6), "walk_forward_hit_rate_power_p1_0.7_n27": power_binom(27, 0.7),
                "touch_test_note": "each touch test is a sum of 37 Bernoulli outcomes with benchmark probabilities spread over 0.05-1.0; a 10-point shift in the touch rate is not detectable",
                "bootstrap_independence": "iid session bootstrap and circular block (3) bootstrap; sessions are consecutive trading days Aug-18..Oct-13 (one regime: closing-auction era, 3-Aug onward)."}
RES["effective_sample"] = {"sessions": nS, "first": str(dates[0].date()), "last": str(dates[-1].date()), "trading_days_span": int(len(daily.loc[dates[0]:dates[-1]])), "sessions_missing_from_span": int(len(daily.loc[dates[0]:dates[-1]]) - nS),
                           "sessions_with_1515_bar": int(has15.sum()), "non_overlapping": True,
                           "note": "37 non-overlapping sessions; every bar-level statistic has the 37 (29 for the 15:15 bar) sessions as its effective sample; 36 of the 37 sessions are the sessions of v1 (v1: 36) so union results are not independent of v1."}

# ----------------------------------------------------------------------------------------------------- 13. registry, per-session table, write
holm_bh(TESTS)
RES["test_registry"] = {"n_tests": len(TESTS), "tests": TESTS, "note": "all p-values two-sided; Holm (FWER) and Benjamini-Hochberg (FDR) are applied across the whole registered family"}
sess_rows = []
for i, dd_ in enumerate(dates):
    sess_rows.append({"date": str(dd_.date()), "source": U[U["date"] == dd_]["source"].iloc[0], "n_bars": int(np.sum(~np.isnan(C[i]))), "has_1515": bool(has15[i]), "G_pct": float(100 * G[i]), "FH_pct": float(100 * FH[i]), "Rest_pct": float(100 * REST[i]), "I_pct": float(100 * I[i]),
                      "R_pct": float(100 * np.log(Coff[i] / prev[i])), "high_slot": times[hi_slot[i]], "low_slot": times[lo_slot[i]], "range_share_1015": float(RS1015[i]), "range_share_1115": float(RS1115[i]), "vol_share_first_hour_pct": float(100 * np.nansum(VS[i, :4])),
                      "vol_share_last_hour_pct": float(100 * np.nansum(VS[i, 21:25])), "bars_over_nse_volume": float(ratio[i]), "close_over_exchange_vwap_pct": float(100 * np.log(Coff[i] / vwap_ex[i])),
                      "auction_move_pct": float(100 * np.log(C[i, 24] / O[i, 24])) if has15[i] else None, "window_1445_to_close_pct": float(100 * RETC[i])})
RES["sessions"] = sess_rows
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(clean(RES), indent=1, default=jdefault, allow_nan=False))
print("union sessions", N, "bars", len(U), "| excluded", [e["date"] for e in excluded], "| 24-bar sessions", RES["data"]["sessions_with_24_bars"])
print("v1 repro exact:", RES["v1_comparison"]["v1_code_reproduced_on_v1_sample"]["reproduces_exactly"], diff_keys)
print(json.dumps({t["id"]: (round(t["p_raw"], 4), round(t["p_holm"], 4), round(t["p_bh"], 4)) for t in TESTS}))
print("wrote", OUT_JSON, OUT_CSV)
