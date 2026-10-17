"""v2 workstream "linkages": does BSE Ltd lead, follow or diverge from the market / sector, and how sensitive is it to
market declines, volatility, rates, currencies and commodities?

Run:  cd /home/user/pred_18 && PYTHONPATH=src python3 src/behaviour/linkages.py
Writes ONLY results/behaviour/linkages.json (the markdown report research/v2/03_market_linkages.md is written by hand
from that JSON).  Reads data read-only; fetches nothing (the few live-state facts fetched on 2026-10-13 are embedded as
constants with provenance below).

=====================================================================================================================
PRE-REGISTRATION OF EVERY TEST (written BEFORE any beta / correlation / regression for BSE was computed; only data
coverage, calendars and FRED date ranges had been inspected).  Thresholds are about the *market* (never tuned on BSE
outcomes).  Every test below is counted in REG (multiple-testing registry) and adjusted within its family (Holm = FWER,
Benjamini-Hochberg = FDR); the family is the unit of the claim.
=====================================================================================================================
NOTATION. BSE sessions k = 0..N-1 (bse_daily.csv, 2017-02-06 .. 2026-10-13), previous kept session d_{k-1}.
 G_k = ln(open/prev), I_k = ln(close/open), R_k = G_k + I_k (src/common.py targets(); prev is bonus-adjusted).
 Index/peer return on session k = ln(X(d_k) / X(d_{k-1})) using the same two BSE session dates (so Muhurat / special
 sessions that BSE drops are rolled into the next regular session for the index as well).  India VIX change = Δln VIX.
 Capital Markets index is used ONLY from 2024-09-13 (a single stray 2023-04-12 value is discarded).
 Peer corporate actions (bonus / split) are detected from close_{t-1}/close_t ≈ integer factor (2,5,10) and the return is
 computed on the adjusted close (NSE PREV_CLOSE is not re-based, see docs/DEVIATIONS.md #8).
 Index data for 2026-10-13 are taken from NSE ind_close_all_13102026.csv (Last-Modified 2026-10-13 14:20:38 GMT =
 19:50 IST, i.e. BEFORE the 22:00 IST cutoff; fetched 2026-10-13T16:03:26Z) and embedded below.

TIME-ZONE ALIGNMENT.  Indian session k covers 03:45-10:00 UTC on date d_k; R_k window = 10:00 UTC d_{k-1} -> 10:00 UTC d_k.
 US cash session of calendar date u closes 20:00/21:00 UTC on u  => it ends AFTER the Indian close of date u.
 'prior' window of session k  = sum of daily changes of US-dated observations with  d_{k-1} <= u < d_k  (all complete
        before the Indian open of d_k: usable to predict G_k and R_k; NaN if no observation falls in the window).
 'same'  window of session k  = observations with  d_{k-1} < u <= d_k  (only used for FX (Fed H.10 noon-NY rate, 16:00
        UTC) and Brent spot, as a CONTEMPORANEOUS ASSOCIATION; it contains information after the Indian close, so it
        is never used as a predictor).
 Indian-lag features for predicting session k use session k-1 (known at 15:30 IST of d_{k-1}).
 FRED publication lags are reported separately (the backtest uses event time; the live nowcast uses what the files hold).

(a) DESCRIPTIVE BETAS / CORRELATIONS (not a family of hypotheses; no p-value claims, HAC CIs only):
    R_k on each of Nifty50, Next50, Midcap100, Bank, FinServ, CapMkts(2024-09+), Δln India VIX, peers CDSL, MCX,
    ANGELONE, NUVAMA, CAMS, KFINTECH: full-sample OLS slope & correlation (HAC Newey-West 5 lags), by calendar year,
    rolling 250 and 60 sessions.  n_eff = n * se_iid^2 / se_HAC^2 (<= n).  Dimson (lags -1,0,+1) beta as robustness.
(b1) LEAD-LAG: corr(R_k, x_{k-lag}) for lag = -5..+5 (lag>0: x leads BSE by `lag` sessions; lag<0: BSE leads x),
    13 series (the 13 listed in (a)).  Family F1 = the 13 x 10 non-zero
    lags = 130 tests (HAC t-test, 5 lags) -> Holm & BH.  (The first draft of this text said 14 x 10 = 140: an arithmetic slip, corrected.)  lag 0 is reported as descriptive.  95% stationary-bootstrap CI
    (mean block 10, B=1000, rows resampled jointly) reported for every cell.
(b2) WALK-FORWARD predictive regressions, expanding window, one-step: y_k = a + b x_{k-1}(+...) with
    y in {R, G, I}; benchmark = expanding mean of y over the same training rows; training rows are j<k only; min training
    rows = 500 if the predictor has >=1500 paired rows else 250; OOS R2 = 1 - SSE_model/SSE_mean;
    Clark-West (2007) one-sided t-test (HAC 5 lags) on f_k = e_b^2 - (e_m^2 - (yhat_b - yhat_m)^2).
    Predictors (23): nifty50, next50, midcap100, bank, finserv, capmkts, dlnvix_in, cdsl, mcx, angelone, nuvama, cams,
    kfintech, bse_own(R_{k-1}), resid_nifty (R_{k-1} - beta_hat*nifty_{k-1}, beta from trailing 250 ending k-2),
    resid_capmkts (idem; 2024-09+), US prior-window: sp500, dlnvix_us, d10y_bp, dlnusdinr, dlnbrent; multivariate
    m_india = [nifty50, dlnvix_in], m_all = m_india + [sp500, dlnvix_us].  Families F2 (y=R), F3 (y=G), F4 (y=I),
    23 tests each; Holm within family.  Also OOS R2 in the first/second half of the OOS period.
    Status rule: validated_out_of_sample iff OOS R2>0 and Holm-adjusted CW p<0.05; else not_found.
(b3) CONDITIONAL (same-day) forecast: given the same-day Nifty move r_k, is a walk-forward beta forecast better than the
    mean?  y=R_k, X=[1, nifty_k] (and [1, nifty_k, capmkts_k] from 2024-09) vs [1].  Family F5 (2 tests).  This validates the
    use of beta for scenario mapping (it is not a prediction of the market).
(c) ASYMMETRY / REGIMES:
    c1  R_k = a + b_up*max(x,0) + b_dn*min(x,0) + e for x in {Nifty50, Midcap100, Bank, FinServ, CapMkts}; test b_dn = b_up
        (HAC).  Plus walk-forward asymmetric-vs-symmetric CW test (nested).  Family F6 (c1 equality tests: 5; CW: 5).
    c2  VIX regime: tercile of India VIX_{k-1} against an EXPANDING window of VIX_{<=k-1} (min 250 obs; ex-ante).  Beta on
        Nifty_k within each tercile; Wald test of equal slopes (interaction), walk-forward CW test of the interaction
        model vs constant beta.  Corr(R, Nifty) in top vs bottom tercile with Fisher-z / bootstrap CI and the
        Forbes-Rigobon heteroskedasticity-corrected correlation.  Family F6 (3 tests: Wald, CW, corr difference).
    c3  Market-decline days: Nifty_k <= -1.5% vs Nifty_k > -1.5% : slope of R on Nifty within each subsample (conditioning
        on the regressor does not bias slopes) and mean BSE return / mean Nifty return.  Descriptive.
(d) MACRO.
    d1  Contemporaneous association: R_k on each of {sp500 prior, dlnvix_us prior, d10y_bp prior, dlnusdinr prior and
        same, dlnbrent prior and same}, univariate and with Nifty_k as control: 7 vars x 2 specs = 14 tests, Holm (F7).
    d2  Predictive (event-time safe): walk-forward tests for the five 'prior' macro variables are inside F2/F3/F4.
    d3  PRIMARY S&P 500 -> BSE test: x = S&P500 prior-window log return (US session(s) completed before the Indian open).
        y = G_k and y = R_k.  (i) full-sample OLS slope with HAC CI; (ii) chronological split: train 2017-02-06..2022-12-30,
        test 2023-01-02..2026-10-13, fixed coefficients from train, OOS R2 vs train mean + CW; (iii) walk-forward (in F2/F3)
        ; (iv) stability: slope per calendar year and per three equal chronological blocks, interaction test
        test-vs-train; (v) robustness: excl. 2020-02-20..2020-04-30, winsorised 1/99.  Family F8 = {G,R} x {split CW,
        walk-forward CW} = 4 tests (Holm).  Positive control: same regression for the Nifty-50 opening gap.
        validated_out_of_sample requires split OOS R2>0 AND walk-forward OOS R2>0 AND Holm p<0.05 for the target.
(e) IDIOSYNCRATIC SHARE = 1 - R2 of R_k on [Nifty50] ; on [Nifty50, CapMkts] (2024-09+) ; on [Nifty50, peers_ew] (2020-10-06+, three peers CDSL, MCX, CAMS available;
    peers_ew = equal-weight mean of available peer returns, >=3 peers) ; overall, by year, last 250 / 120 sessions, 2025+;
    also for G and I components; stationary-bootstrap 95% CI; concentration of residual SS in the 10 largest days.
    Descriptive (no p-values).
=====================================================================================================================
ADDITIONS / CORRECTIONS MADE AFTER THE FIRST RUN (disclosed; the first run had already shown the F2-F8 outcomes)
 1. BUG FIX: finalize_d3 used `p_holm or 1`, which treated an adjusted p of exactly 0.0 (after rounding) as 1 and labelled the
    S&P -> G walk-forward as failing; fixed with explicit None checks; p-values are kept to 4 significant digits (_p).
 2. Bootstrap p-values are floored at 1/(B+1).
 3. F9_incremental (EXPLORATORY, 12 tests, Holm): does a validated predictor add to S&P 500 (nested walk-forward CW, restricted =
    [1, sp500])?  Added because several US-session predictors validated and are mechanically one signal (brief rule 5).
 4. Negative-control / placebo diagnostics for the S&P alignment (diagnostics, not hypothesis families).
 5. Extra robustness fields on every walk-forward test: OOS R2 without the 5 largest |y| sessions, CW effective n, and a STRICT gate
    (Holm p<0.05 AND OOS R2>0 in both halves AND >0 without the 5 largest |y| sessions; v1-style).  The label
    `validated_out_of_sample` is still assigned by the rule written above; `passes_strict_gate` is reported next to it.
 6. Live-state arithmetic (increments of validated predictors, the 13-Oct residual) and pre/post 2026-08-03 closing-method check of
    the own-lag effect (post sample is n=50: descriptive only).
 7. Sub-period split (halves) of the lead-lag cells that survive Holm (descriptive).
=====================================================================================================================
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from common import index_returns, load_bse, load_index, targets  # noqa: F401  (src/common.py, read-only)

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "behaviour" / "linkages.json"
MACRO = ROOT / "data" / "raw" / "macro"
PEERS = ["CDSL", "MCX", "ANGELONE", "NUVAMA", "CAMS", "KFINTECH"]
CAPMKTS_START = pd.Timestamp("2024-09-13")
SPLIT_DATE = pd.Timestamp("2023-01-01")
RNG_SEED = 20261013
B_BOOT = 1000
HAC_LAGS = 5
CUTOFF_IST = "2026-10-13T22:00:00+05:30"

# ---------------------------------------------------------------------------------------------------------------
# Embedded facts fetched on 2026-10-13 BEFORE the cutoff (provenance in each entry)
# ---------------------------------------------------------------------------------------------------------------
IDX_20261013 = {   # NSE ind_close_all_13102026.csv; columns open, close.  Last-Modified 2026-10-13 14:20:38 GMT (19:50 IST)
    "nifty50": (22364.15, 22721.95), "next50": (68182.15, 68927.95), "nifty500": (21818.9, 22090.0),
    "midcap100": (58845.3, 59459.2), "smallcap100": (19429.5, 19447.4), "bank": (54907.55, 55481.05),
    "finserv": (24834.75, 25228.55), "vix": (15.2525, 14.12), "capmkts": (5259.65, 5285.75),
}
IDX_20261013_SRC = {"url": "https://nsearchives.nseindia.com/content/indices/ind_close_all_13102026.csv",
                    "last_modified_utc": "2026-10-13T14:20:38Z", "last_modified_ist": "2026-10-13T19:50:38+05:30",
                    "fetched_utc": "2026-10-13T16:03:26Z", "fetched_ist": "2026-10-13T21:33:26+05:30",
                    "confidence": "high (official NSE archive; HTTP 200; row-level values matched Change(%) column)"}
# Yahoo Finance chart API (v8, interval=5m, includePrePost) fetched 2026-10-13T16:03:4xZ = 21:33 IST (27 min before cutoff)
LIVE_US = {
    "fetched_utc": "2026-10-13T16:17:42Z", "fetched_ist": "2026-10-13T21:47:42+05:30",
    "earlier_snapshots": [{"fetched_utc": "2026-10-13T16:03:43Z", "spx_last": 7797.15, "vix_last": 15.38, "tnx_last_pct": 5.227},
                          {"fetched_utc": "2026-10-13T16:13:43Z", "spx_last": 7795.57, "vix_last": 15.45, "tnx_last_pct": 5.223}],
    "source": "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=5m&range=5d&includePrePost=true (HTTP 200; one request per symbol)",
    "spx_last": 7797.72, "spx_last_time_utc": "2026-10-13T16:17:42Z", "spx_prev_close_12oct": 7807.24,
    "es_future_last": 7841.75, "es_future_last_time_utc": "2026-10-13T16:07:42Z", "es_future_prev_settle": 7858.0,
    "vix_last": 15.42, "vix_last_time_utc": "2026-10-13T16:02:31Z", "vix_prev_close": 15.21,
    "vix_prev_close_note": "FRED VIXCLS 2026-10-12 = 15.21; Yahoo meta previousClose 14.84 is the 2026-10-09 close and was NOT used",
    "tnx_last_pct": 5.223, "tnx_prev_pct": 5.2400002,
    "brent_front_future_last": 105.99, "brent_front_future_prev_settle": 106.65,
    "usdinr_yahoo_last": 95.27, "usdinr_yahoo_last_time_utc": "2026-10-13T14:18:26Z", "usdinr_yahoo_prev_close": 95.76, "usdinr_ecb_ref_20261013": 95.28,
    "usdinr_ecb_ref_20261012": 95.78, "usdinr_ecb_ref_20261009": 96.73,
    "ecb_source": "https://api.frankfurter.app/2026-10-01..2026-10-13?from=USD&to=INR (curl -L, HTTP 200; ECB reference fixed 14:10 CET)",
    "confidence": "medium (unofficial Yahoo quotes, 5-minute bars; the S&P value is ~2h47m into a 6.5h session; INR=X last tick 14:18 UTC is stale after Asian hours)",
}


# ---------------------------------------------------------------------------------------------------------------
# Generic statistics helpers
# ---------------------------------------------------------------------------------------------------------------
def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    adj = np.empty(n)
    run = 0.0
    for i, j in enumerate(o):
        run = max(run, (n - i) * p[j])
        adj[j] = min(1.0, run)
    return adj


def bh(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)[::-1]
    adj = np.empty(n)
    run = 1.0
    for rank_from_top, j in enumerate(o):
        i = n - rank_from_top
        run = min(run, p[j] * n / i)
        adj[j] = run
    return adj


class Registry:
    """Counts every hypothesis test and adjusts within families."""

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, family: str, name: str, p: float, **meta):
        self.rows.append({"family": family, "name": name, "p": float(p) if p == p else float("nan"), **meta})

    def adjust(self) -> dict:
        df = pd.DataFrame(self.rows)
        out = {}
        for fam, g in df.groupby("family", sort=False):
            ok = g["p"].notna().values
            ph = np.full(len(g), np.nan)
            pb = np.full(len(g), np.nan)
            if ok.sum():
                ph[ok] = holm(g["p"].values[ok])
                pb[ok] = bh(g["p"].values[ok])
            df.loc[g.index, "p_holm"] = ph
            df.loc[g.index, "p_bh"] = pb
            out[fam] = {"n_tests": int(len(g)), "n_nan": int((~ok).sum()),
                        "n_raw_p_lt_0.05": int((g["p"] < 0.05).sum()),
                        "n_holm_lt_0.05": int((df.loc[g.index, "p_holm"] < 0.05).sum()),
                        "n_bh_lt_0.05": int((df.loc[g.index, "p_bh"] < 0.05).sum())}
        self.df = df
        return out

    def lookup(self, family: str, name: str) -> dict:
        g = self.df[(self.df.family == family) & (self.df.name == name)]
        if len(g) != 1:
            raise KeyError((family, name))
        r = g.iloc[0]
        return {"p_raw": _p(r.p), "p_holm": _p(r.p_holm), "p_bh": _p(r.p_bh), "family": family,
                "family_size": int((self.df.family == family).sum())}


def _p(x):
    """p-values/CW stats: keep 4 significant digits (so 1e-11 is not rounded to 0)."""
    try:
        x = float(x)
    except Exception:
        return None
    if x != x or math.isinf(x):
        return None
    return float(f"{x:.4g}")


def _f(x, nd=6):
    if x is None:
        return None
    try:
        x = float(x)
    except Exception:
        return None
    if x != x or math.isinf(x):
        return None
    return round(x, nd)


def hac_fit(y, X, lags=HAC_LAGS):
    """OLS with Newey-West (Bartlett, small-sample corrected) covariance; rows with NaN dropped.  Returns dict."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    m = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[m], X[m]
    n = len(y)
    Xc = sm.add_constant(X, has_constant="add")
    res = sm.OLS(y, Xc).fit(cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True})
    res0 = sm.OLS(y, Xc).fit()
    se_h, se_i = res.bse, res0.bse
    ratio = (se_i / se_h) ** 2
    return {"n": int(n), "params": res.params, "se": se_h, "t": res.tvalues, "p": res.pvalues, "r2": float(res.rsquared),
            "r2_adj": float(res.rsquared_adj), "resid": res.resid, "n_eff": np.minimum(n * ratio, n), "mask": m,
            "cov": res.cov_params()}


def corr_hac(y, x, lags=HAC_LAGS):
    """Correlation of y and x (pairwise complete) with HAC t/p (slope of standardised regression)."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    n = int(m.sum())
    if n < 30:
        return None
    yy, xx = y[m], x[m]
    zy = (yy - yy.mean()) / yy.std(ddof=1)
    zx = (xx - xx.mean()) / xx.std(ddof=1)
    r = float(np.corrcoef(yy, xx)[0, 1])
    f = hac_fit(zy, zx, lags)
    se = float(f["se"][1])
    return {"n": n, "corr": r, "se_hac": se, "t": float(f["t"][1]), "p": float(f["p"][1]), "n_eff": float(f["n_eff"][1]),
            "ci95_hac": [r - 1.96 * se, r + 1.96 * se]}


def ols_slope(y, x, lags=HAC_LAGS):
    f = hac_fit(y, x, lags)
    b, se = float(f["params"][1]), float(f["se"][1])
    return {"n": f["n"], "beta": b, "se_hac": se, "ci95": [b - 1.96 * se, b + 1.96 * se], "t": float(f["t"][1]),
            "p": float(f["p"][1]), "r2": f["r2"], "alpha": float(f["params"][0]), "n_eff": float(f["n_eff"][1])}


def stationary_bootstrap_idx(n: int, B: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    p = 1.0 / mean_block
    start = rng.integers(0, n, size=(B, n))
    new = rng.random((B, n)) < p
    new[:, 0] = True
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = start[:, 0]
    for t in range(1, n):
        idx[:, t] = np.where(new[:, t], start[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def newey_west_mean_t(f: np.ndarray, lags: int = HAC_LAGS):
    f = np.asarray(f, float)
    f = f[np.isfinite(f)]
    n = len(f)
    if n < 30:
        return float("nan"), float("nan"), n
    mu = f.mean()
    e = f - mu
    s0 = e @ e / n
    s = s0
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    se = math.sqrt(max(s, 1e-30) / n)
    newey_west_mean_t.last_neff = float(min(n, n * s0 / max(s, 1e-30)))
    return float(mu), float(mu / se), n


# ---------------------------------------------------------------------------------------------------------------
# Walk-forward engine (expanding window, one-step, nested comparison with Clark-West)
# ---------------------------------------------------------------------------------------------------------------
def walk_forward(y: np.ndarray, Xr: np.ndarray, Xf: np.ndarray, min_train: int):
    """For each k with >= min_train valid training rows j<k (y_j and both designs finite) and valid row k:
    predict with restricted design Xr (benchmark) and full design Xf.  Designs include their own constants.
    Returns arrays (idx, y, yhat_r, yhat_f)."""
    N = len(y)
    pr, pf = Xr.shape[1], Xf.shape[1]
    A_r, b_r = np.zeros((pr, pr)), np.zeros(pr)
    A_f, b_f = np.zeros((pf, pf)), np.zeros(pf)
    cnt = 0
    ks, ys, yr, yf = [], [], [], []
    valid = np.isfinite(y) & np.isfinite(Xr).all(1) & np.isfinite(Xf).all(1)
    for k in range(N):
        if k > 0 and valid[k - 1]:
            xr, xf = Xr[k - 1], Xf[k - 1]
            A_r += np.outer(xr, xr)
            b_r += xr * y[k - 1]
            A_f += np.outer(xf, xf)
            b_f += xf * y[k - 1]
            cnt += 1
        if valid[k] and cnt >= min_train:
            try:
                wr = np.linalg.solve(A_r + 1e-12 * np.eye(pr), b_r)
                wf = np.linalg.solve(A_f + 1e-12 * np.eye(pf), b_f)
            except np.linalg.LinAlgError:
                continue
            ks.append(k)
            ys.append(y[k])
            yr.append(Xr[k] @ wr)
            yf.append(Xf[k] @ wf)
    return np.array(ks), np.array(ys), np.array(yr), np.array(yf)


def score_wf(ks, ys, yr, yf, dates):
    """OOS R2 of full vs restricted; Clark-West one-sided p; halves; per-year; ex-top-5; CW effective n."""
    if len(ks) < 60:
        return None
    er, ef = ys - yr, ys - yf
    sse_r, sse_f = float((er ** 2).sum()), float((ef ** 2).sum())
    r2 = 1 - sse_f / sse_r
    f = er ** 2 - (ef ** 2 - (yr - yf) ** 2)
    mu, t, n = newey_west_mean_t(f)
    neff = newey_west_mean_t.last_neff
    p = float(1 - stats.norm.cdf(t))
    d = dates[ks]
    half = len(ks) // 2
    r2h = []
    for sl in (slice(0, half), slice(half, None)):
        a, b = float((er[sl] ** 2).sum()), float((ef[sl] ** 2).sum())
        r2h.append(1 - b / a)
    yrs = pd.Series(d.year, index=range(len(ks)))
    pos_years = {}
    for yv in sorted(set(d.year)):
        mm = (yrs == yv).values
        if mm.sum() >= 40:
            pos_years[int(yv)] = _f(1 - (ef[mm] ** 2).sum() / (er[mm] ** 2).sum(), 4)
    # without the 5 largest |y| sessions in the OOS sample (v1-style robustness)
    keep = np.ones(len(ks), bool)
    keep[np.argsort(-np.abs(ys))[:5]] = False
    r2x = 1 - (ef[keep] ** 2).sum() / (er[keep] ** 2).sum()
    mu_x, t_x, _ = newey_west_mean_t(f[keep])
    # directional hit-rate of the model forecast deviation from benchmark
    dev = yf - yr
    sgn = np.sign(dev) * np.sign(ys - yr)
    hit = float((sgn[dev != 0] > 0).mean()) if (dev != 0).any() else float("nan")
    return {"n_oos": int(len(ks)), "cw_n_eff": _f(neff, 1), "first_oos": str(d[0].date()), "last_oos": str(d[-1].date()), "oos_r2": r2,
            "mspe_model": sse_f / len(ks), "mspe_bench": sse_r / len(ks), "cw_mean_f": mu, "cw_t": t, "cw_p_one_sided": _p(p),
            "oos_r2_first_half": r2h[0], "oos_r2_second_half": r2h[1], "oos_r2_by_year": pos_years,
            "oos_r2_ex_top5_abs_y": r2x, "cw_t_ex_top5_abs_y": t_x,
            "sign_agreement_dev_vs_realised_dev": hit}


# ---------------------------------------------------------------------------------------------------------------
# Data build
# ---------------------------------------------------------------------------------------------------------------
def read_fred(name: str) -> pd.Series:
    raw = pd.read_csv(MACRO / f"{name}.csv", index_col=0)
    s = pd.to_numeric(raw.iloc[:, 0], errors="coerce")
    s.index = pd.to_datetime(raw.index)
    return s.dropna()


def detect_peer_adjusted(p: pd.DataFrame, sym: str):
    """Adjusted close for a peer; ex-date factor f detected where close_{t-1}/close_t is near an integer (2,5,10)."""
    g = p[p.symbol == sym].drop_duplicates("date", keep="last").set_index("date").sort_index()
    c = g["close"].astype(float)
    ratio = c.shift(1) / c
    events = []
    f_cum = pd.Series(1.0, index=c.index)
    for dt, r in ratio.items():
        if not np.isfinite(r) or r < 1.5:
            continue
        for fct in (2, 3, 4, 5, 10):
            if abs(math.log(r) - math.log(fct)) < 0.15:
                events.append({"date": str(dt.date()), "ratio_prev_close_over_close": round(float(r), 3), "factor": fct})
                f_cum.loc[:dt - pd.Timedelta(days=1)] *= fct   # earlier closes divided by factor -> adjust back history
                break
    adj = c / f_cum
    return adj, events


def window_sum(change: pd.Series, d_prev: pd.DatetimeIndex, d_cur: pd.DatetimeIndex, mode: str):
    """sum of daily changes dated in [d_prev, d_cur) (mode 'prior') or (d_prev, d_cur] (mode 'same'); NaN if none."""
    dates = change.index.values
    c = change.fillna(0.0).values
    cs = np.concatenate([[0.0], np.cumsum(c)])
    cn = np.concatenate([[0], np.cumsum(change.notna().values.astype(int))])
    if mode == "prior":
        lo = np.searchsorted(dates, d_prev.values, side="left")
        hi = np.searchsorted(dates, d_cur.values, side="left")
    else:
        lo = np.searchsorted(dates, d_prev.values, side="right")
        hi = np.searchsorted(dates, d_cur.values, side="right")
    s = cs[hi] - cs[lo]
    n = cn[hi] - cn[lo]
    return np.where(n > 0, s, np.nan), n


def build_panel():
    d = load_bse()
    t = targets(d)
    sess = d.index
    ix = load_index()
    # embed 2026-10-13 index row from the NSE archive (published before the cutoff)
    row = {}
    for k, (o, c) in IDX_20261013.items():
        row[f"{k}_close"] = c
        row[f"{k}_open"] = o
    ix = pd.concat([ix, pd.DataFrame([row], index=[pd.Timestamp("2026-10-13")])]).sort_index()
    ix.loc[ix.index < CAPMKTS_START, ["capmkts_close", "capmkts_open"]] = np.nan   # stray 2023-04-12 value
    prev_dates = pd.DatetimeIndex([pd.Timestamp("2017-02-03")] + list(sess[:-1]))
    P = pd.DataFrame(index=sess)
    P["prev_date"] = prev_dates
    P["G"], P["I"], P["R"] = t["G"], t["I"], t["R"]
    names = {"nifty50": "nifty50", "next50": "next50", "midcap100": "midcap100", "bank": "bank", "finserv": "finserv",
             "capmkts": "capmkts", "nifty500": "nifty500", "smallcap100": "smallcap100", "vix": "vix"}
    for k in names:
        cl = ix[f"{k}_close"]
        a = cl.reindex(sess).values
        b = cl.reindex(prev_dates).values
        P[f"r_{k}"] = np.log(a / b)
    P["r_vix"] = P["r_vix"]   # already Δln VIX
    # nifty 50 gap / intraday for the positive control
    op = ix["nifty50_open"].reindex(sess).values
    cl_n = ix["nifty50_close"].reindex(sess).values
    pr_n = ix["nifty50_close"].reindex(prev_dates).values
    P["G_nifty50"] = np.log(op / pr_n)
    P["I_nifty50"] = np.log(cl_n / op)
    # peers
    pr = pd.read_csv(ROOT / "data/processed/peers_daily.csv", parse_dates=["date"]).sort_values(["symbol", "date"])
    peer_events = {}
    for sym in PEERS:
        adj, ev = detect_peer_adjusted(pr, sym)
        peer_events[sym] = ev
        a = adj.reindex(sess).values
        b = adj.reindex(prev_dates).values
        P[f"r_{sym.lower()}"] = np.log(a / b)
    pc = [f"r_{s.lower()}" for s in PEERS]
    pe = P[pc]
    P["r_peers_ew"] = pe.mean(axis=1).where(pe.notna().sum(axis=1) >= 3)
    # macro (FRED)
    mac = {}
    sp = read_fred("SP500")
    mac["sp500"] = np.log(sp).diff()
    vx = read_fred("VIXCLS")
    mac["dlnvix_us"] = np.log(vx).diff()
    dg = read_fred("DGS10")
    mac["d10y_bp"] = dg.diff() * 100.0
    fx = read_fred("DEXINUS")
    mac["dlnusdinr"] = np.log(fx).diff()
    br = read_fred("DCOILBRENTEU")
    br = br[br > 0]
    mac["dlnbrent"] = np.log(br).diff()
    last_obs = {"sp500": sp.index[-1], "dlnvix_us": vx.index[-1], "d10y_bp": dg.index[-1], "dlnusdinr": fx.index[-1],
                "dlnbrent": br.index[-1]}
    for k, ch in mac.items():
        ch = ch.dropna()
        P[f"{k}_prior"], P[f"{k}_prior_n"] = window_sum(ch, P["prev_date"], pd.DatetimeIndex(sess), "prior")
        P[f"{k}_same"], P[f"{k}_same_n"] = window_sum(ch, P["prev_date"], pd.DatetimeIndex(sess), "same")
    # beta-based residuals (trailing 250 sessions ending k-2 for the residual measured at k-1)
    for base in ("nifty50", "capmkts"):
        x = P[f"r_{base}"]
        cov = P["R"].rolling(250, min_periods=120).cov(x)
        var = x.rolling(250, min_periods=120).var()
        beta = (cov / var).shift(1)   # estimated through k-1 -> applied to residual at k (so for lag-1 feature shift again later)
        P[f"resid_{base}"] = P["R"] - beta * x
    return P, ix, peer_events, last_obs


# ---------------------------------------------------------------------------------------------------------------
# (a) betas and correlations
# ---------------------------------------------------------------------------------------------------------------
SERIES = [("nifty50", "Nifty 50"), ("next50", "Nifty Next 50"), ("midcap100", "Nifty Midcap 100"), ("bank", "Nifty Bank"),
          ("finserv", "Nifty Fin Services"), ("capmkts", "Nifty Capital Markets (2024-09+)"), ("vix", "India VIX Δln"),
          ("cdsl", "CDSL"), ("mcx", "MCX"), ("angelone", "Angel One"), ("nuvama", "Nuvama"), ("cams", "CAMS"),
          ("kfintech", "KFin Tech")]


def part_a(P: pd.DataFrame):
    out = {"full_sample": {}, "by_year": {}, "rolling": {}, "recent": {}}
    y = P["R"].values
    for key, label in SERIES:
        x = P[f"r_{key}"].values
        m = np.isfinite(x) & np.isfinite(y)
        s = ols_slope(y, x)
        c = corr_hac(y, x)
        # Dimson beta: x_{k-1}, x_k, x_{k+1}
        X3 = np.column_stack([pd.Series(x).shift(1).values, x, pd.Series(x).shift(-1).values])
        fd = hac_fit(y, X3)
        dim = float(fd["params"][1:].sum())
        cv = fd["cov"][1:, 1:]
        dim_se = float(math.sqrt(np.ones(3) @ cv @ np.ones(3)))
        idx = P.index[m]
        out["full_sample"][key] = {"label": label, "n": s["n"], "n_eff": _f(s["n_eff"], 1), "first": str(idx[0].date()),
                                   "last": str(idx[-1].date()), "beta": _f(s["beta"], 4), "beta_se_hac": _f(s["se_hac"], 4),
                                   "beta_ci95": [_f(v, 4) for v in s["ci95"]], "corr": _f(c["corr"], 4),
                                   "corr_ci95_hac": [_f(v, 4) for v in c["ci95_hac"]], "r2": _f(s["r2"], 4),
                                   "dimson_beta_lags_m1_0_p1": _f(dim, 4), "dimson_ci95": [_f(dim - 1.96 * dim_se, 4), _f(dim + 1.96 * dim_se, 4)]}
        # by calendar year
        yy = {}
        for yr in sorted(set(P.index.year)):
            mm = (P.index.year == yr) & m
            if mm.sum() >= 40:
                sl = ols_slope(y[mm], x[mm])
                cc = corr_hac(y[mm], x[mm])
                yy[int(yr)] = {"n": int(mm.sum()), "beta": _f(sl["beta"], 3), "ci95": [_f(v, 3) for v in sl["ci95"]], "corr": _f(cc["corr"], 3)}
        out["by_year"][key] = yy
        # rolling
        ys, xs = pd.Series(y, index=P.index), pd.Series(x, index=P.index)
        roll = {}
        for w in (250, 60):
            mp = max(40, int(0.8 * w))
            b = ys.rolling(w, min_periods=mp).cov(xs) / xs.rolling(w, min_periods=mp).var()
            r = ys.rolling(w, min_periods=mp).corr(xs)
            bv = b.dropna()
            roll[f"w{w}"] = {"last_beta": _f(b.iloc[-1], 3), "last_corr": _f(r.iloc[-1], 3), "last_date": str(P.index[-1].date()),
                             "beta_min": _f(bv.min(), 3), "beta_p10": _f(bv.quantile(.1), 3), "beta_median": _f(bv.median(), 3),
                             "beta_p90": _f(bv.quantile(.9), 3), "beta_max": _f(bv.max(), 3),
                             "n_windows": int(len(bv)), "n_independent_windows_approx": int(len(bv) // w)}
            if w == 250:
                me = b.resample("QE").last().dropna()
                roll["w250_quarter_end_beta"] = {str(i.date()): _f(v, 3) for i, v in me.items()}
        out["rolling"][key] = roll
        # recent windows
        rec = {}
        for lab, mask in (("2025_onward", P.index >= "2025-01-01"), ("last250", P.index >= P.index[-250]), ("last120", P.index >= P.index[-120]),
                          ("2024-09_onward", P.index >= CAPMKTS_START)):
            mm = mask & m
            if mm.sum() >= 40:
                sl = ols_slope(y[mm], x[mm])
                cc = corr_hac(y[mm], x[mm])
                rec[lab] = {"n": int(mm.sum()), "beta": _f(sl["beta"], 3), "ci95": [_f(v, 3) for v in sl["ci95"]], "corr": _f(cc["corr"], 3)}
        out["recent"][key] = rec
    # joint model Nifty + CapMkts (2024-09+) and Nifty + peers_ew
    j = {}
    for nm, cols, start in (("nifty50+capmkts", ["r_nifty50", "r_capmkts"], CAPMKTS_START), ("nifty50+peers_ew", ["r_nifty50", "r_peers_ew"], None)):
        X = P[cols].values
        f = hac_fit(y, X)
        idx = P.index[f["mask"]]
        j[nm] = {"n": f["n"], "first": str(idx[0].date()), "last": str(idx[-1].date()),
                 "coef": {c: {"beta": _f(f["params"][i + 1], 3), "ci95": [_f(f["params"][i + 1] - 1.96 * f["se"][i + 1], 3), _f(f["params"][i + 1] + 1.96 * f["se"][i + 1], 3)]} for i, c in enumerate(cols)},
                 "r2": _f(f["r2"], 4)}
    out["joint"] = j
    # G and I components vs Nifty gap / intraday
    comp = {}
    for tgt, xcol in (("G", "G_nifty50"), ("I", "I_nifty50")):
        s = ols_slope(P[tgt].values, P[xcol].values)
        c = corr_hac(P[tgt].values, P[xcol].values)
        comp[f"{tgt}_BSE_on_{xcol}"] = {"n": s["n"], "beta": _f(s["beta"], 3), "ci95": [_f(v, 3) for v in s["ci95"]], "corr": _f(c["corr"], 3), "r2": _f(s["r2"], 4)}
    out["gap_intraday_components_vs_nifty50"] = comp
    # divergence descriptives: sign agreement with Nifty when |nifty| >= 0.5%
    xn = P["r_nifty50"]
    big = xn.abs() >= 0.005
    agree = (np.sign(P["R"]) == np.sign(xn))[big & xn.notna()]
    nb = int(agree.size)
    kk = int(agree.sum())
    ci = stats.beta.interval(0.95, kk + .5, nb - kk + .5)   # Jeffreys
    base_rate = None
    out["sign_agreement_when_abs_nifty_ge_0.5pct"] = {"n": nb, "share_same_sign": _f(kk / nb, 4), "jeffreys_ci95": [_f(ci[0], 4), _f(ci[1], 4)],
                                                      "benchmark": "0.5 under independence of signs",
                                                      "binom_p_vs_0.5": _f(stats.binomtest(kk, nb, 0.5).pvalue, 6)}
    return out


# ---------------------------------------------------------------------------------------------------------------
# (b1) lead-lag cross-correlations
# ---------------------------------------------------------------------------------------------------------------
LAGS = list(range(-5, 6))


def part_b1(P: pd.DataFrame, REG: Registry):
    y = P["R"].values
    n = len(y)
    cols = []   # (key, lag)
    arrs = []
    for key, _ in SERIES:
        x = pd.Series(P[f"r_{key}"].values)
        for L in LAGS:
            arrs.append(x.shift(L).values)    # x_{k-L}: L>0 -> x leads
            cols.append((key, L))
    Z = np.column_stack([y] + arrs)    # n x (1+C)
    C = Z.shape[1] - 1
    # point estimates + HAC
    res = {}
    for ci_, (key, L) in enumerate(cols):
        r = corr_hac(y, Z[:, 1 + ci_])
        res[(key, L)] = r
        if L != 0:
            REG.add("F1_leadlag", f"{key}@{L}", r["p"])
    # joint stationary bootstrap of correlations
    rng = np.random.default_rng(RNG_SEED)
    idx = stationary_bootstrap_idx(n, B_BOOT, 10.0, rng)
    boots = np.empty((B_BOOT, C))
    M0 = np.isfinite(Z)
    for b in range(B_BOOT):
        Zb = Z[idx[b]]
        yb = Zb[:, 0:1]
        Xb = Zb[:, 1:]
        m = np.isfinite(Xb) & np.isfinite(yb)
        cnt = m.sum(0)
        Xz = np.where(m, Xb, 0.0)
        Yz = np.where(m, yb, 0.0)
        sx, sy = Xz.sum(0), Yz.sum(0)
        sxx, syy, sxy = (Xz ** 2).sum(0), (Yz ** 2).sum(0), (Xz * Yz).sum(0)
        cov = sxy / cnt - sx / cnt * sy / cnt
        vx = sxx / cnt - (sx / cnt) ** 2
        vy = syy / cnt - (sy / cnt) ** 2
        boots[b] = cov / np.sqrt(np.maximum(vx * vy, 1e-30))
    lo = np.nanpercentile(boots, 2.5, axis=0)
    hi = np.nanpercentile(boots, 97.5, axis=0)
    table = []
    for ci_, (key, L) in enumerate(cols):
        r = res[(key, L)]
        row = {"series": key, "lag": L, "n": r["n"], "n_eff": _f(r["n_eff"], 1), "corr": _f(r["corr"], 4), "se_hac": _f(r["se_hac"], 4),
               "ci95_hac": [_f(v, 4) for v in r["ci95_hac"]], "ci95_boot": [_f(lo[ci_], 4), _f(hi[ci_], 4)], "p_raw": _p(r["p"])}
        table.append(row)
    return table


def finalize_b1(table, REG):
    for r in table:
        if r["lag"] != 0:
            q = REG.lookup("F1_leadlag", f"{r['series']}@{r['lag']}")
            r["p_holm"], r["p_bh"] = q["p_holm"], q["p_bh"]
    return table


# ---------------------------------------------------------------------------------------------------------------
# (b2)/(b3) walk-forward predictive regressions
# ---------------------------------------------------------------------------------------------------------------
def predictor_frame(P: pd.DataFrame) -> pd.DataFrame:
    F = pd.DataFrame(index=P.index)
    for key in ("nifty50", "next50", "midcap100", "bank", "finserv", "capmkts", "cdsl", "mcx", "angelone", "nuvama", "cams", "kfintech"):
        F[key] = P[f"r_{key}"].shift(1)
    F["dlnvix_in"] = P["r_vix"].shift(1)
    F["bse_own"] = P["R"].shift(1)
    F["resid_nifty"] = P["resid_nifty50"].shift(1)
    F["resid_capmkts"] = P["resid_capmkts"].shift(1)
    F["sp500"] = P["sp500_prior"]
    F["dlnvix_us"] = P["dlnvix_us_prior"]
    F["d10y_bp"] = P["d10y_bp_prior"]
    F["dlnusdinr"] = P["dlnusdinr_prior"]
    F["dlnbrent"] = P["dlnbrent_prior"]
    return F


PRED_ORDER = ["nifty50", "next50", "midcap100", "bank", "finserv", "capmkts", "dlnvix_in", "cdsl", "mcx", "angelone", "nuvama", "cams",
              "kfintech", "bse_own", "resid_nifty", "resid_capmkts", "sp500", "dlnvix_us", "d10y_bp", "dlnusdinr", "dlnbrent", "m_india", "m_all"]
MULTI = {"m_india": ["nifty50", "dlnvix_in"], "m_all": ["nifty50", "dlnvix_in", "sp500", "dlnvix_us"]}


def part_b2(P: pd.DataFrame, REG: Registry):
    F = predictor_frame(P)
    dates = P.index
    out = {}
    for tgt, fam in (("R", "F2_wf_R"), ("G", "F3_wf_G"), ("I", "F4_wf_I")):
        y = P[tgt].values
        out[tgt] = {}
        for name in PRED_ORDER:
            cols = MULTI.get(name, [name])
            X = F[cols].values
            ok = np.isfinite(X).all(1) & np.isfinite(y)
            n_pair = int(ok.sum())
            min_train = 500 if n_pair >= 1500 else 250
            Xr = np.ones((len(y), 1))
            Xf = np.column_stack([np.ones(len(y)), X])
            ks, ys, yr, yf = walk_forward(y, Xr, Xf, min_train)
            sc = score_wf(ks, ys, yr, yf, dates)
            if sc is None:
                REG.add(fam, name, float("nan"))
                out[tgt][name] = {"n_pair": n_pair, "note": "insufficient OOS rows"}
                continue
            # final full-sample fit for coefficient report
            fit = hac_fit(y, X)
            sc.update({"n_pair": n_pair, "min_train": min_train,
                       "full_sample_coef_per_unit": [_f(v, 5) for v in fit["params"][1:]],
                       "full_sample_coef_ci95": [[_f(fit["params"][i + 1] - 1.96 * fit["se"][i + 1], 5), _f(fit["params"][i + 1] + 1.96 * fit["se"][i + 1], 5)] for i in range(len(cols))],
                       "full_sample_p_hac": [_f(v, 5) for v in fit["p"][1:]], "full_sample_insample_r2": _f(fit["r2"], 5), "predictor_cols": cols,
                       "n_eff_oos_hac": None})
            REG.add(fam, name, sc["cw_p_one_sided"])
            out[tgt][name] = sc
    return out


def finalize_b2(out, REG):
    for tgt, fam in (("R", "F2_wf_R"), ("G", "F3_wf_G"), ("I", "F4_wf_I")):
        for name, sc in out[tgt].items():
            if "cw_p_one_sided" not in sc:
                continue
            q = REG.lookup(fam, name)
            sc["cw_p_holm_family"], sc["cw_p_bh_family"] = q["p_holm"], q["p_bh"]
            sc["family"], sc["family_size"] = fam, q["family_size"]
            val = (sc["oos_r2"] > 0) and (q["p_holm"] is not None) and (q["p_holm"] < 0.05)
            sc["validation_status"] = "validated_out_of_sample" if val else "not_found"
            sc["both_halves_positive"] = bool(sc["oos_r2_first_half"] > 0 and sc["oos_r2_second_half"] > 0)
            sc["positive_ex_top5"] = bool(sc["oos_r2_ex_top5_abs_y"] > 0)
            sc["passes_strict_gate"] = bool(val and sc["both_halves_positive"] and sc["positive_ex_top5"])
    return out


def part_b3_conditional(P, REG):
    """Same-day nifty move -> BSE: walk-forward beta forecast vs mean (conditional forecast)."""
    y = P["R"].values
    dates = P.index
    res = {}
    for name, cols, minr in (("cond_nifty50", ["r_nifty50"], 250), ("cond_nifty50+capmkts", ["r_nifty50", "r_capmkts"], 250)):
        X = P[cols].values
        Xr = np.ones((len(y), 1))
        Xf = np.column_stack([np.ones(len(y)), X])
        ks, ys, yr, yf = walk_forward(y, Xr, Xf, minr)
        sc = score_wf(ks, ys, yr, yf, dates)
        REG.add("F5_conditional", name, sc["cw_p_one_sided"])
        res[name] = sc
    return res


def finalize_b3(res, REG):
    for name, sc in res.items():
        q = REG.lookup("F5_conditional", name)
        sc["cw_p_holm_family"], sc["cw_p_bh_family"] = q["p_holm"], q["p_bh"]
        sc["validation_status"] = "validated_out_of_sample" if (sc["oos_r2"] > 0 and q["p_holm"] < 0.05) else "not_found"
    return res


# ---------------------------------------------------------------------------------------------------------------
# (c) asymmetry and regimes
# ---------------------------------------------------------------------------------------------------------------
def expanding_terciles(v: np.ndarray, min_obs: int = 250):
    """v[k] is already the ex-ante state (VIX close at d_{k-1}).  class (0,1,2) of v[k] against the EXPANDING distribution of
    v[0..k] (known at the open of session k); NaN before min_obs observations."""
    import bisect
    N = len(v)
    cls = np.full(N, np.nan)
    srt: list[float] = []
    for k in range(N):
        if not np.isfinite(v[k]):
            continue
        bisect.insort(srt, v[k])
        if len(srt) >= min_obs:
            q1 = srt[int(len(srt) * 1 / 3)]
            q2 = srt[int(len(srt) * 2 / 3)]
            x = v[k]
            cls[k] = 0 if x <= q1 else (1 if x <= q2 else 2)
    return cls


def forbes_rigobon(rho, var_stress, var_calm):
    delta = var_stress / var_calm - 1.0
    return rho / math.sqrt(1 + delta * (1 - rho ** 2))


def part_c(P: pd.DataFrame, REG: Registry):
    y = P["R"].values
    dates = P.index
    out = {"up_down": {}, "vix_terciles": {}, "decline_days": {}}
    for key in ("nifty50", "midcap100", "bank", "finserv", "capmkts"):
        x = P[f"r_{key}"].values
        up, dn = np.maximum(x, 0.0), np.minimum(x, 0.0)
        f = hac_fit(y, np.column_stack([up, dn]))
        b_up, b_dn = f["params"][1], f["params"][2]
        L = np.array([0, -1.0, 1.0])
        diff = float(L @ f["params"])        # b_up - b_dn
        se = float(math.sqrt(L @ f["cov"] @ L))
        z = diff / se
        p = float(2 * (1 - stats.norm.cdf(abs(z))))
        m = np.isfinite(x) & np.isfinite(y)
        n_up, n_dn = int((x[m] > 0).sum()), int((x[m] < 0).sum())
        # walk-forward nested comparison: asymmetric vs symmetric
        Xr = np.column_stack([np.ones(len(y)), x])
        Xf = np.column_stack([np.ones(len(y)), x, dn])
        ks, ys, yr, yf = walk_forward(y, Xr, Xf, 250)
        sc = score_wf(ks, ys, yr, yf, dates)
        REG.add("F6_asym", f"updown_equal_{key}", p)
        REG.add("F6_asym", f"updown_wf_cw_{key}", sc["cw_p_one_sided"] if sc else float("nan"))
        out["up_down"][key] = {"n": f["n"], "n_up_days": n_up, "n_down_days": n_dn, "beta_up": _f(b_up, 3), "beta_down": _f(b_dn, 3),
                               "beta_up_ci95": [_f(b_up - 1.96 * f["se"][1], 3), _f(b_up + 1.96 * f["se"][1], 3)],
                               "beta_down_ci95": [_f(b_dn - 1.96 * f["se"][2], 3), _f(b_dn + 1.96 * f["se"][2], 3)],
                               "diff_up_minus_down": _f(diff, 3), "diff_ci95": [_f(diff - 1.96 * se, 3), _f(diff + 1.96 * se, 3)], "p_equal_slopes": _p(p),
                               "wf_asym_vs_sym": sc, "intercept_per_day": _f(f["params"][0], 5)}
    # VIX terciles (ex-ante, expanding)
    vlvl = pd.read_csv(ROOT / "data/processed/index_daily.csv", parse_dates=["date"]).set_index("date")["vix_close"]
    vlvl = pd.concat([vlvl, pd.Series({pd.Timestamp("2026-10-13"): IDX_20261013["vix"][1]})]).sort_index()
    v_prev = vlvl.reindex(P.index.to_series().shift(1).fillna(pd.Timestamp("2017-02-03")).values).values   # VIX close at d_{k-1}
    cls = expanding_terciles(v_prev, 250)
    for key in ("nifty50", "capmkts"):
        x = P[f"r_{key}"].values
        res = {}
        for c, lab in ((0, "low"), (1, "mid"), (2, "high")):
            m = (cls == c) & np.isfinite(x) & np.isfinite(y)
            if m.sum() >= 40:
                s = ols_slope(y[m], x[m])
                cc = corr_hac(y[m], x[m])
                res[lab] = {"n": int(m.sum()), "n_eff": _f(s["n_eff"], 1), "beta": _f(s["beta"], 3), "ci95": [_f(v, 3) for v in s["ci95"]],
                            "corr": _f(cc["corr"], 3), "sd_nifty": _f(x[m].std(ddof=1), 5), "vix_prev_range": [_f(np.nanmin(v_prev[m]), 2), _f(np.nanmax(v_prev[m]), 2)]}
        # interaction Wald test: equal slopes across terciles
        D1, D2 = (cls == 1).astype(float), (cls == 2).astype(float)
        valid = np.isfinite(cls)
        Xi = np.column_stack([x, D1, D2, x * D1, x * D2])
        yv = np.where(valid, y, np.nan)
        f = hac_fit(yv, np.where(valid[:, None], Xi, np.nan))
        # params: const, x, D1, D2, xD1, xD2
        R_ = np.zeros((2, len(f["params"])))
        R_[0, 4] = 1.0
        R_[1, 5] = 1.0
        diff = R_ @ f["params"]
        W = float(diff @ np.linalg.solve(R_ @ f["cov"] @ R_.T, diff))
        pw = float(1 - stats.chi2.cdf(W, 2))
        # walk-forward: interaction model vs constant beta
        Xr = np.column_stack([np.ones(len(y)), x])
        Xf = np.column_stack([np.ones(len(y)), x, D1, D2, x * D1, x * D2])
        Xf = np.where(valid[:, None], Xf, np.nan)
        ks, ys, yr, yf = walk_forward(y, Xr, Xf, 250)
        sc = score_wf(ks, ys, yr, yf, dates) if len(ks) > 60 else None
        REG.add("F6_asym", f"vix_tercile_wald_{key}", pw)
        REG.add("F6_asym", f"vix_tercile_wf_cw_{key}", sc["cw_p_one_sided"] if sc else float("nan"))
        # high vs low correlation difference: bootstrap on rows
        mlo, mhi = (cls == 0) & np.isfinite(x) & np.isfinite(y), (cls == 2) & np.isfinite(x) & np.isfinite(y)
        corr_diff = None
        if mlo.sum() >= 40 and mhi.sum() >= 40:
            rng = np.random.default_rng(RNG_SEED + 7)
            ilo, ihi = np.where(mlo)[0], np.where(mhi)[0]
            dif = []
            for _ in range(B_BOOT):
                a = ilo[stationary_bootstrap_idx(len(ilo), 1, 10.0, rng)[0]]
                b = ihi[stationary_bootstrap_idx(len(ihi), 1, 10.0, rng)[0]]
                dif.append(np.corrcoef(y[b], x[b])[0, 1] - np.corrcoef(y[a], x[a])[0, 1])
            dif = np.array(dif)
            r_hi, r_lo = float(np.corrcoef(y[mhi], x[mhi])[0, 1]), float(np.corrcoef(y[mlo], x[mlo])[0, 1])
            pb = float(min(1.0, max(2 * min((dif <= 0).mean(), (dif >= 0).mean()), 1.0 / (B_BOOT + 1))))
            fr = forbes_rigobon(r_hi, x[mhi].var(ddof=1), x[mlo].var(ddof=1))
            corr_diff = {"corr_high_tercile": _f(r_hi, 3), "corr_low_tercile": _f(r_lo, 3), "diff_high_minus_low": _f(r_hi - r_lo, 3),
                         "boot_ci95": [_f(np.percentile(dif, 2.5), 3), _f(np.percentile(dif, 97.5), 3)], "boot_p_two_sided": _f(pb, 4),
                         "forbes_rigobon_corrected_corr_high_vs_calm_variance": _f(fr, 3)}
            REG.add("F6_asym", f"vix_tercile_corrdiff_{key}", pb)
        out["vix_terciles"][key] = {"terciles": res, "wald_equal_slopes_chi2_2": _f(W, 3), "wald_p": _p(pw), "wf_interaction_vs_constant": sc,
                                    "corr_high_vs_low": corr_diff}
    # market-decline days (descriptive)
    for key in ("nifty50", "capmkts"):
        x = P[f"r_{key}"].values
        res = {}
        for lab, m in (("decline_le_-1.5pct", x <= -0.015), ("other_days", x > -0.015)):
            mm = m & np.isfinite(x) & np.isfinite(y)
            if mm.sum() >= 30:
                s = ols_slope(y[mm], x[mm])
                res[lab] = {"n": int(mm.sum()), "beta": _f(s["beta"], 3), "ci95": [_f(v, 3) for v in s["ci95"]], "mean_bse_ret": _f(y[mm].mean(), 5),
                            "mean_idx_ret": _f(x[mm].mean(), 5), "ratio_of_means": _f(y[mm].mean() / x[mm].mean(), 3),
                            "share_bse_down_more_than_index": _f(float((y[mm] < x[mm]).mean()), 3)}
        out["decline_days"][key] = res
    return out


def finalize_c(out, REG):
    for key, v in out["up_down"].items():
        v["p_equal_adj"] = REG.lookup("F6_asym", f"updown_equal_{key}")
        v["wf_p_adj"] = REG.lookup("F6_asym", f"updown_wf_cw_{key}")
    for key, v in out["vix_terciles"].items():
        v["wald_adj"] = REG.lookup("F6_asym", f"vix_tercile_wald_{key}")
        v["wf_adj"] = REG.lookup("F6_asym", f"vix_tercile_wf_cw_{key}")
        if v["corr_high_vs_low"] is not None:
            v["corr_high_vs_low"]["adj"] = REG.lookup("F6_asym", f"vix_tercile_corrdiff_{key}")
    return out


# ---------------------------------------------------------------------------------------------------------------
# (d) macro sensitivity and S&P 500 -> gap test
# ---------------------------------------------------------------------------------------------------------------
MACRO_UNITS = {"sp500": ("per +1% S&P 500 log return", 0.01), "dlnvix_us": ("per +10% US VIX (log change 0.10)", 0.10),
               "d10y_bp": ("per +10 bp US 10y yield", 10.0), "dlnusdinr": ("per +1% USD/INR (INR depreciation)", 0.01),
               "dlnbrent": ("per +10% Brent (log)", 0.10)}


def part_d1(P: pd.DataFrame, REG: Registry):
    y = P["R"].values
    xn = P["r_nifty50"].values
    out = {}
    specs = [("sp500", "prior"), ("dlnvix_us", "prior"), ("d10y_bp", "prior"), ("dlnusdinr", "prior"), ("dlnusdinr", "same"), ("dlnbrent", "prior"), ("dlnbrent", "same")]
    for var, mode in specs:
        x = P[f"{var}_{mode}"].values
        unit_lab, unit = MACRO_UNITS[var]
        m = np.isfinite(x) & np.isfinite(y)
        s = ols_slope(y, x)
        f2 = hac_fit(y, np.column_stack([x, xn]))
        b2, se2, p2 = f2["params"][1], f2["se"][1], f2["p"][1]
        REG.add("F7_macro_contemp", f"{var}_{mode}_uni", s["p"])
        REG.add("F7_macro_contemp", f"{var}_{mode}_ctrlNifty", p2)
        idx = P.index[m]
        out[f"{var}_{mode}"] = {"unit": unit_lab, "n": s["n"], "n_eff": _f(s["n_eff"], 1), "first": str(idx[0].date()), "last": str(idx[-1].date()),
                                "alignment": "prior: US/FX/commodity observations dated in [d_{k-1}, d_k): complete before the Indian open (predictive-safe)" if mode == "prior"
                                else "same: observations dated in (d_{k-1}, d_k]: partly AFTER the Indian close; association only",
                                "uni_bse_ret_pct_per_unit": _f(s["beta"] * unit * 100, 4), "uni_ci95_pct": [_f(v * unit * 100, 4) for v in s["ci95"]], "uni_corr": _f(math.sqrt(s["r2"]) * np.sign(s["beta"]), 4), "uni_r2": _f(s["r2"], 5),
                                "ctrl_nifty_bse_ret_pct_per_unit": _f(b2 * unit * 100, 4), "ctrl_nifty_ci95_pct": [_f((b2 - 1.96 * se2) * unit * 100, 4), _f((b2 + 1.96 * se2) * unit * 100, 4)],
                                "ctrl_nifty_r2": _f(f2["r2"], 5), "n_ctrl": f2["n"]}
    return out


def finalize_d1(out, REG):
    for k, v in out.items():
        v["uni_adj"] = REG.lookup("F7_macro_contemp", f"{k}_uni")
        v["ctrl_adj"] = REG.lookup("F7_macro_contemp", f"{k}_ctrlNifty")
    return out


def part_d3(P: pd.DataFrame, REG: Registry):
    """Pre-registered S&P 500 (prior window) -> BSE G and R."""
    out = {}
    x = P["sp500_prior"].values
    dates = P.index
    out["coverage"] = {"n_sessions": int(len(P)), "n_with_us_window": int(np.isfinite(x).sum()),
                       "n_without_us_session_in_window": int((~np.isfinite(x)).sum()),
                       "sp500_prior_sd_pct": _f(np.nanstd(x) * 100, 3)}
    train = dates < SPLIT_DATE
    for tgt in ("G", "R", "G_nifty50"):
        y = P[tgt].values
        m = np.isfinite(x) & np.isfinite(y)
        full = ols_slope(y, x)
        sub = {}
        # (i) full sample, robustness
        sub["full_sample"] = {"n": full["n"], "n_eff": _f(full["n_eff"], 1), "period": f"{dates[m][0].date()}..{dates[m][-1].date()}",
                              "beta_per_1pct_sp500_in_pct": _f(full["beta"], 4), "ci95": [_f(v, 4) for v in full["ci95"]], "t_hac": _f(full["t"], 3),
                              "p_hac": _p(full["p"]), "r2": _f(full["r2"], 5), "intercept_pct": _f(full["alpha"] * 100, 4)}
        # robustness
        m2 = m & ~((dates >= "2020-02-20") & (dates <= "2020-04-30"))
        r2s = ols_slope(y[m2], x[m2])
        lo, hi = np.nanpercentile(x[m], [1, 99])
        xw = np.clip(x, lo, hi)
        rw = ols_slope(y[m], xw[m])
        sub["robust_ex_covid"] = {"n": r2s["n"], "beta": _f(r2s["beta"], 4), "ci95": [_f(v, 4) for v in r2s["ci95"]], "p_hac": _p(r2s["p"])}
        sub["robust_winsor_1_99"] = {"n": rw["n"], "beta": _f(rw["beta"], 4), "ci95": [_f(v, 4) for v in rw["ci95"]], "p_hac": _p(rw["p"])}
        # (ii) chronological split: fixed coefficients from train
        mt, ms = m & train, m & ~train
        ft = ols_slope(y[mt], x[mt])
        fs = ols_slope(y[ms], x[ms])
        pred = ft["alpha"] + ft["beta"] * x[ms]
        bench = np.full(ms.sum(), y[mt].mean())
        e_m, e_b = y[ms] - pred, y[ms] - bench
        oos = 1 - (e_m ** 2).sum() / (e_b ** 2).sum()
        f_cw = e_b ** 2 - (e_m ** 2 - (bench - pred) ** 2)
        mu, tcw, ncw = newey_west_mean_t(f_cw)
        pcw = float(1 - stats.norm.cdf(tcw))
        # interaction test (stability of slope between train and test)
        post = (~train).astype(float)
        fi = hac_fit(y, np.column_stack([x, post, x * post]))
        out_i = {"beta_diff_test_minus_train": _f(fi["params"][3], 4), "se": _f(fi["se"][3], 4), "p": _f(fi["p"][3], 5)}
        sub["split"] = {"train": f"{dates[mt][0].date()}..{dates[mt][-1].date()}", "test": f"{dates[ms][0].date()}..{dates[ms][-1].date()}",
                        "n_train": int(mt.sum()), "n_test": int(ms.sum()), "beta_train": _f(ft["beta"], 4), "beta_train_ci95": [_f(v, 4) for v in ft["ci95"]],
                        "beta_test_refit": _f(fs["beta"], 4), "beta_test_ci95": [_f(v, 4) for v in fs["ci95"]], "p_test_refit": _p(fs["p"]),
                        "oos_r2_fixed_train_coef_vs_train_mean": _f(oos, 5), "cw_t": _f(tcw, 3), "cw_p_one_sided": _p(pcw),
                        "slope_stability_test": out_i}
        if tgt in ("G", "R"):
            REG.add("F8_sp500_gap", f"{tgt}_split_cw", pcw)
        # (iv) by year and thirds
        by_year = {}
        for yr in sorted(set(dates.year)):
            mm = m & (dates.year == yr)
            if mm.sum() >= 40:
                s = ols_slope(y[mm], x[mm])
                by_year[int(yr)] = {"n": s["n"], "beta": _f(s["beta"], 3), "ci95": [_f(v, 3) for v in s["ci95"]]}
        idx_m = np.where(m)[0]
        thirds = np.array_split(idx_m, 3)
        by_third = []
        for th in thirds:
            s = ols_slope(y[th], x[th])
            by_third.append({"period": f"{dates[th][0].date()}..{dates[th][-1].date()}", "n": s["n"], "beta": _f(s["beta"], 3), "ci95": [_f(v, 3) for v in s["ci95"]]})
        sub["by_year"] = by_year
        sub["by_third"] = by_third
        yrs_pos = sum(1 for v in by_year.values() if v["beta"] is not None and v["beta"] > 0)
        sub["years_with_positive_beta"] = f"{yrs_pos}/{len(by_year)}"
        # (iii) walk-forward expanding
        Xr = np.ones((len(y), 1))
        Xf = np.column_stack([np.ones(len(y)), x])
        ks, ys, yr_, yf_ = walk_forward(y, Xr, Xf, 500)
        sc = score_wf(ks, ys, yr_, yf_, dates)
        sub["walk_forward"] = sc
        if tgt in ("G", "R"):
            REG.add("F8_sp500_gap", f"{tgt}_wf_cw", sc["cw_p_one_sided"])
        out[tgt] = sub
    # large-move / asymmetry description for G (descriptive)
    y = P["G"].values
    m = np.isfinite(x) & np.isfinite(y)
    for lab, mm in (("S&P < -1%", m & (x < -0.01)), ("S&P in [-1%,+1%]", m & (np.abs(x) <= 0.01)), ("S&P > +1%", m & (x > 0.01))):
        out.setdefault("G_by_sp_bucket", {})[lab] = {"n": int(mm.sum()), "mean_G_pct": _f(y[mm].mean() * 100, 4), "median_G_pct": _f(np.median(y[mm]) * 100, 4),
                                                     "sd_G_pct": _f(y[mm].std(ddof=1) * 100, 4)}
    return out


def _lt(x, thr):
    return x is not None and x < thr


def finalize_d3(out, REG):
    for tgt in ("G", "R"):
        s = out[tgt]
        s["split"]["adj"] = REG.lookup("F8_sp500_gap", f"{tgt}_split_cw")
        s["walk_forward"]["adj"] = REG.lookup("F8_sp500_gap", f"{tgt}_wf_cw")
        ok_split = (s["split"]["oos_r2_fixed_train_coef_vs_train_mean"] is not None and s["split"]["oos_r2_fixed_train_coef_vs_train_mean"] > 0) and _lt(s["split"]["adj"]["p_holm"], 0.05)
        ok_wf = (s["walk_forward"]["oos_r2"] > 0) and _lt(s["walk_forward"]["adj"]["p_holm"], 0.05)
        s["validation_status"] = "validated_out_of_sample" if (ok_split and ok_wf) else "not_found"
        s["validation_rule"] = "split OOS R2>0 & Holm p<0.05 AND walk-forward OOS R2>0 & Holm p<0.05 (family F8, 4 tests)"
        s["split_passes"], s["wf_passes"] = bool(ok_split), bool(ok_wf)
    return out


# ---------------------------------------------------------------------------------------------------------------
# (e) idiosyncratic variance share
# ---------------------------------------------------------------------------------------------------------------
def r2_of(y, X):
    f = hac_fit(y, X)
    return f["r2"], f["r2_adj"], f["n"], f["resid"], f["mask"]


def part_e(P: pd.DataFrame):
    out = {}
    rng = np.random.default_rng(RNG_SEED + 11)
    specs = {"R~nifty50": ("R", ["r_nifty50"]), "R~nifty50+capmkts": ("R", ["r_nifty50", "r_capmkts"]), "R~nifty50+peers_ew": ("R", ["r_nifty50", "r_peers_ew"]),
             "G~nifty50_gap": ("G", ["G_nifty50"]), "I~nifty50_intraday": ("I", ["I_nifty50"]), "R~capmkts_only": ("R", ["r_capmkts"])}
    periods = {"full": P.index >= P.index[0], "2017-2019": P.index.year <= 2019, "2020": P.index.year == 2020, "2021": P.index.year == 2021, "2022": P.index.year == 2022,
               "2023": P.index.year == 2023, "2024": P.index.year == 2024, "2025": P.index.year == 2025, "2026_ytd": P.index.year == 2026,
               "2025_onward": P.index >= "2025-01-01", "last250": P.index >= P.index[-250], "last120": P.index >= P.index[-120], "2024-09_onward": P.index >= CAPMKTS_START}
    for sname, (tgt, cols) in specs.items():
        res = {}
        for pname, pm in periods.items():
            y = np.where(pm, P[tgt].values, np.nan)
            X = np.where(pm[:, None], P[cols].values, np.nan)
            ok = np.isfinite(y) & np.isfinite(X).all(1)
            if ok.sum() < 60:
                continue
            r2, r2a, n, resid, mk = r2_of(y, X)
            entry = {"n": int(n), "r2": _f(r2, 4), "idio_share": _f(1 - r2, 4), "idio_share_adj": _f(1 - r2a, 4)}
            if pname in ("full", "2025_onward", "last250", "2024-09_onward"):
                # bootstrap CI
                yy, XX = y[ok], X[ok]
                idx = stationary_bootstrap_idx(len(yy), 500, 10.0, rng)
                vals = []
                for b in range(idx.shape[0]):
                    Xb = np.column_stack([np.ones(len(yy)), XX[idx[b]]])
                    beta = np.linalg.lstsq(Xb, yy[idx[b]], rcond=None)[0]
                    e = yy[idx[b]] - Xb @ beta
                    vals.append(1 - (e ** 2).sum() / ((yy[idx[b]] - yy[idx[b]].mean()) ** 2).sum())
                entry["r2_boot_ci95"] = [_f(np.percentile(vals, 2.5), 4), _f(np.percentile(vals, 97.5), 4)]
                entry["idio_share_boot_ci95"] = [_f(1 - np.percentile(vals, 97.5), 4), _f(1 - np.percentile(vals, 2.5), 4)]
                # concentration of residual SS
                e2 = np.sort(resid ** 2)[::-1]
                entry["top10_days_share_of_resid_ss"] = _f(e2[:10].sum() / e2.sum(), 4)
                entry["top1pct_days_share_of_resid_ss"] = _f(e2[:max(1, int(0.01 * len(e2)))].sum() / e2.sum(), 4)
            res[pname] = entry
        out[sname] = res
    return out


# ---------------------------------------------------------------------------------------------------------------
# live state for the 14 Oct nowcast
# ---------------------------------------------------------------------------------------------------------------
SINGLE_GROUPS = {"sp500": "US risk-on/off", "dlnvix_us": "US risk-on/off", "dlnusdinr": "US risk-on/off (FX leg)", "d10y_bp": "US rates",
                 "dlnbrent": "commodity", "bse_own": "own momentum", "resid_nifty": "own momentum", "cdsl": "sector peers (Indian lag)", "mcx": "sector peers (Indian lag)"}


def part_f9(P: pd.DataFrame, REG: Registry):
    """EXPLORATORY: does a validated predictor add to S&P 500?  nested walk-forward vs [1, sp500]."""
    F = predictor_frame(P)
    out = {}
    base = ["sp500"]
    adds = ["dlnusdinr", "dlnvix_us", "bse_own", "cdsl", "mcx", "resid_nifty"]
    for tgt in ("G", "R"):
        y = P[tgt].values
        for a in adds:
            cols_f = base + [a]
            ok = np.isfinite(F[cols_f].values).all(1)
            Xr = np.column_stack([np.ones(len(y)), F[base].values])
            Xf = np.column_stack([np.ones(len(y)), F[cols_f].values])
            Xr = np.where(ok[:, None], Xr, np.nan)
            Xf = np.where(ok[:, None], Xf, np.nan)
            ks, ys, yr, yf = walk_forward(y, Xr, Xf, 500)
            sc = score_wf(ks, ys, yr, yf, P.index)
            fit = hac_fit(y, F[cols_f].values)
            sc["coef_added_full_sample"] = _f(fit["params"][2], 5)
            sc["coef_added_ci95"] = [_f(fit["params"][2] - 1.96 * fit["se"][2], 5), _f(fit["params"][2] + 1.96 * fit["se"][2], 5)]
            sc["coef_sp500_full_sample"] = _f(fit["params"][1], 5)
            REG.add("F9_incremental", f"{tgt}:+{a}", sc["cw_p_one_sided"])
            out[f"{tgt}:+{a}"] = sc
    return out


def finalize_f9(out, REG):
    for k, sc in out.items():
        q = REG.lookup("F9_incremental", k)
        sc["cw_p_holm_family"], sc["cw_p_bh_family"] = q["p_holm"], q["p_bh"]
        sc["adds_to_sp500"] = bool(sc["oos_r2"] > 0 and q["p_holm"] is not None and q["p_holm"] < 0.05)
    return out


def part_f10(P: pd.DataFrame, REG: Registry):
    """Does BSE lead others?  y = other series at session k, x = BSE R at k-1; nested walk-forward vs expanding mean (13 tests)."""
    out = {}
    x = P["R"].shift(1).values
    for key, label in SERIES:
        y = P[f"r_{key}"].values
        ok = np.isfinite(y) & np.isfinite(x)
        min_train = 500 if ok.sum() >= 1500 else 250
        Xr = np.ones((len(y), 1))
        Xf = np.column_stack([np.ones(len(y)), x])
        ks, ys, yr, yf = walk_forward(y, Xr, Xf, min_train)
        sc = score_wf(ks, ys, yr, yf, P.index)
        if sc is None:
            REG.add("F10_bse_leads", key, float("nan"))
            out[key] = {"note": "insufficient OOS rows"}
            continue
        fit = hac_fit(y, x)
        sc["coef_other_on_bse_lag1"] = _f(fit["params"][1], 5)
        sc["coef_ci95"] = [_f(fit["params"][1] - 1.96 * fit["se"][1], 5), _f(fit["params"][1] + 1.96 * fit["se"][1], 5)]
        sc["n_pair"] = int(ok.sum())
        REG.add("F10_bse_leads", key, sc["cw_p_one_sided"])
        out[key] = sc
    return out


def finalize_f10(out, REG):
    for k, sc in out.items():
        if "cw_p_one_sided" not in sc:
            continue
        q = REG.lookup("F10_bse_leads", k)
        sc["cw_p_holm_family"], sc["cw_p_bh_family"] = q["p_holm"], q["p_bh"]
        sc["validation_status"] = "validated_out_of_sample" if (sc["oos_r2"] > 0 and q["p_holm"] is not None and q["p_holm"] < 0.05) else "not_found"
    return out


def part_composite(P: pd.DataFrame, f9, spx_partial, vix_partial, x_live_extra):
    """EXPLORATORY composite: sp500 + every addition that passed F9 for that target.  Selected on the same sample the walk-forward
    scores, so its OOS R2 is optimistic; label descriptive_only.  Live increment with delta-method CI."""
    F = predictor_frame(P)
    out = {}
    last = P.index[-1]
    x_live_all = {"sp500": spx_partial, "dlnvix_us": vix_partial, "bse_own": P.loc[last, "R"], "cdsl": P.loc[last, "r_cdsl"], "mcx": P.loc[last, "r_mcx"],
                  "resid_nifty": P.loc[last, "resid_nifty50"], "dlnusdinr": x_live_extra["dlnusdinr"]}
    for tgt in ("G", "R"):
        adds = [a for a in ("dlnusdinr", "dlnvix_us", "bse_own", "cdsl", "mcx", "resid_nifty") if f9[f"{tgt}:+{a}"]["adds_to_sp500"]]
        cols = ["sp500"] + adds
        y = P[tgt].values
        X = F[cols].values
        ok = np.isfinite(X).all(1)
        Xr = np.where(ok[:, None], np.ones((len(y), 1)), np.nan)
        Xf = np.where(ok[:, None], np.column_stack([np.ones(len(y)), X]), np.nan)
        ks, ys, yr, yf = walk_forward(y, Xr, Xf, 500)
        sc_mean = score_wf(ks, ys, yr, yf, P.index)
        Xr2 = np.where(ok[:, None], np.column_stack([np.ones(len(y)), F[["sp500"]].values]), np.nan)
        ks2, ys2, yr2, yf2 = walk_forward(y, Xr2, Xf, 500)
        sc_sp = score_wf(ks2, ys2, yr2, yf2, P.index)
        fit = hac_fit(y, X)
        xm = np.nanmean(X[fit["mask"]], axis=0)
        xl = np.array([x_live_all[c] for c in cols])
        d = np.concatenate([[0.0], xl - xm])
        inc = float(fit["params"] @ d)
        se = float(math.sqrt(d @ fit["cov"] @ d))
        out[tgt] = {"columns": cols, "n_fit": fit["n"], "coef": [_f(v, 5) for v in fit["params"][1:]], "coef_se_hac": [_f(v, 5) for v in fit["se"][1:]],
                    "insample_r2": _f(fit["r2"], 4), "wf_vs_mean": sc_mean, "wf_vs_sp500_only": sc_sp,
                    "x_live_pct": {c: _f(v * 100, 4) for c, v in zip(cols, xl)}, "x_mean_pct": {c: _f(v * 100, 4) for c, v in zip(cols, xm)},
                    "live_increment_pct": _f(inc * 100, 4), "live_increment_ci95_pct": [_f((inc - 1.96 * se) * 100, 4), _f((inc + 1.96 * se) * 100, 4)],
                    "resid_sd_pct": _f(np.sqrt(np.mean(fit["resid"] ** 2)) * 100, 3), "sd_y_pct": _f(np.nanstd(y) * 100, 3),
                    "validation_status": "descriptive_only",
                    "caveat": "composition chosen after F9 on the same sample (data snooping): its OOS R2 is an upper bound; coefficients of correlated predictors are not individually interpretable"}
    return out


def part_diagnostics(P: pd.DataFrame):
    """Negative controls / placebo for the S&P alignment, own-lag pre/post closing-method split, lead-lag halves (descriptive)."""
    out = {}
    sp = P["sp500_prior"]
    pl = {}
    for lab, y, x in (("G on S&P window shifted back one more session (should be ~0)", P["G"], sp.shift(1)),
                      ("G on S&P dated d_k (US session AFTER the Indian open; common-shock association)", P["G"], P["sp500_same"]),
                      ("R on S&P dated d_k (US session after the Indian close)", P["R"], P["sp500_same"]),
                      ("R on the FOLLOWING session's prior window (US session after the Indian close; association, never usable)", P["R"], sp.shift(-1)),
                      ("I (open->close) on S&P prior window (info already in the open)", P["I"], sp)):
        s = ols_slope(y.values, x.values)
        c = corr_hac(y.values, x.values)
        pl[lab] = {"n": s["n"], "beta_pct_per_1pct": _f(s["beta"], 4), "ci95": [_f(v, 4) for v in s["ci95"]], "corr": _f(c["corr"], 4), "p_hac": _p(s["p"])}
    out["sp500_alignment_placebos"] = pl
    R = P["R"]
    pre, post = R[:"2026-08-02"], R["2026-08-03":]

    def ac(x):
        r = x.autocorr(1)
        n = len(x)
        z = np.arctanh(r)
        se = 1 / math.sqrt(n - 3)
        return {"n": int(n), "ac1": _f(r, 4), "ci95": [_f(math.tanh(z - 1.96 * se), 4), _f(math.tanh(z + 1.96 * se), 4)]}
    out["bse_R_autocorr_lag1_by_closing_method"] = {"vwap_close_era_to_2026-08-02": ac(pre), "closing_auction_era_from_2026-08-03": ac(post),
                                                    "note": "NSE close was a 30-minute VWAP until 2026-08-02; the auction-era sample is only 50 sessions (descriptive). A VWAP close mechanically pushes the end-of-day drift into the next gap."}
    by = {}
    for yv in sorted(set(R.index.year)):
        by[int(yv)] = _f(R[R.index.year == yv].autocorr(1), 3)
    out["bse_R_autocorr_lag1_by_year"] = by
    out["nifty50_R_autocorr_lag1_full"] = _f(P["r_nifty50"].autocorr(1), 4)
    post_m = (P.index >= "2026-08-03")
    sp_ = ols_slope(P["G"].values[post_m], sp.values[post_m])
    out["sp500_to_G_in_closing_auction_era"] = {"n": sp_["n"], "beta": _f(sp_["beta"], 3), "ci95": [_f(v, 3) for v in sp_["ci95"]], "period": f"2026-08-03..{P.index[-1].date()}",
                                                "note": "descriptive only (n=50): the S&P -> G relation does not depend on how the previous close is defined, the lagged-Indian-return relations might"}
    # mechanical overlap of BSE in the Capital Markets index: share of cov(R, capmkts) that is BSE's own weight * var(R)
    mm = P["r_capmkts"].notna()
    cov_ri = float(np.cov(P["R"][mm], P["r_capmkts"][mm])[0, 1])
    var_r = float(P["R"][mm].var(ddof=1))
    out["capmkts_mechanical_overlap"] = {w_lab: {"weight": w, "own_variance_share_of_cov_R_capmkts": _f(w * var_r / cov_ri, 3)} for w_lab, w in (("weight_15.09pct_AngelOne_article", 0.1509), ("weight_22.88pct_NSE_factsheet_2025-03-28_via_search_summary", 0.2288))}
    out["capmkts_mechanical_overlap"]["note"] = ("BSE Ltd is a constituent of NIFTY Capital Markets (weights quoted by a web-search summary of the NSE Indices factsheet dated 2025-03-28: 22.88%; an Angel One article: 15.09%; "
                                                   "NOT verified by this workstream - https://www.niftyindices.com/Factsheet/Factsheet_NiftyCapitalMarkets.pdf was not opened).  Share = w*var(R)/cov(R, index), "
                                                   "an upper-bound style guide for how much of the BSE-sector covariance is BSE's own contribution.")
    out["lag1_autocorr_by_series_full_sample"] = {k: _f(P[f"r_{k}"].autocorr(1), 4) for k, _ in SERIES}
    out["lag1_autocorr_by_series_note"] = ("positive own-lag autocorrelation across the sector peers is consistent with a common mechanism (e.g. VWAP-based closes, slow "
                                           "sector information diffusion) rather than BSE-specific leadership; the data cannot separate these")
    return out


def leadlag_halves(P: pd.DataFrame, table):
    res = []
    for r in table:
        if r["lag"] == 0 or r.get("p_holm") is None or r["p_holm"] >= 0.05:
            continue
        x = pd.Series(P[f"r_{r['series']}"].values, index=P.index).shift(r["lag"])
        m = x.notna() & P["R"].notna()
        idx = np.where(m.values)[0]
        mid = idx[len(idx) // 2]
        h = {}
        for lab, sl in (("first_half", idx[idx < mid]), ("second_half", idx[idx >= mid])):
            c = corr_hac(P["R"].values[sl], x.values[sl])
            h[lab] = {"period": f"{P.index[sl[0]].date()}..{P.index[sl[-1]].date()}", "n": c["n"], "corr": _f(c["corr"], 4), "ci95_hac": [_f(v, 4) for v in c["ci95_hac"]]}
        res.append({"series": r["series"], "lag": r["lag"], **h})
    return res


def live_state(P: pd.DataFrame, last_obs, b2, d3):
    last = P.index[-1]
    s = {"as_of_cutoff": CUTOFF_IST, "last_bse_session": str(last.date()), "index_13oct_source": IDX_20261013_SRC, "live_us": LIVE_US}
    r13 = {k: _f(P.loc[last, f"r_{k}"], 5) for k, _ in SERIES if f"r_{k}" in P.columns}
    s["returns_13oct"] = {"R_bse": _f(P.loc[last, "R"], 5), "G_bse": _f(P.loc[last, "G"], 5), "I_bse": _f(P.loc[last, "I"], 5), **{"r_" + k: v for k, v in r13.items()},
                          "r_nifty500": _f(P.loc[last, "r_nifty500"], 5), "r_smallcap100": _f(P.loc[last, "r_smallcap100"], 5)}
    for base in ("nifty50", "capmkts"):
        s[f"resid_13oct_vs_{base}_beta_through_12oct"] = _f(P.loc[last, f"resid_{base}"], 5)
    s["fred_last_obs"] = {k: str(v.date()) for k, v in last_obs.items()}
    s["fred_staleness_note"] = ("FRED files end: SP500/VIXCLS 2026-10-12, DGS10 2026-10-08, Brent 2026-10-06, DEXINUS 2026-10-02.  For the 13-Oct session's "
                                "'prior' window only S&P 500 and US VIX have an observation; US10y, USD/INR and Brent are stale by 3, 7 and 5 sessions "
                                "(H.15/H.10/EIA releases lag the event by days).  For the live nowcast the Yahoo/ECB quotes in live_us are used instead and "
                                "are unofficial and time-misaligned with the FRED definitions (e.g. Brent front future vs EIA spot).")
    spx_partial = math.log(LIVE_US["spx_last"] / LIVE_US["spx_prev_close_12oct"])
    vix_partial = math.log(LIVE_US["vix_last"] / LIVE_US["vix_prev_close"])
    fx_move = math.log(LIVE_US["usdinr_yahoo_last"] / LIVE_US["usdinr_yahoo_prev_close"])
    s["sp500_partial_return_13oct_logpct"] = _f(spx_partial * 100, 4)
    s["sp500_partial_note"] = (f"S&P 500 {LIVE_US['spx_last']} at {LIVE_US['spx_last_time_utc']} (about 2h47m into the session) vs the 12-Oct close "
                               f"{LIVE_US['spx_prev_close_12oct']} (equal to the FRED SP500 value).  The session closes 20:00 UTC = 01:30 IST on 14-Oct, after the cutoff; "
                               "E[full-day return | partial] = partial return, remainder unknown.")
    s["us_vix_partial_dln"] = _f(vix_partial, 4)
    s["usdinr_move_13oct_dln"] = _f(fx_move, 5)
    # live increments for single-predictor models (full-sample OLS), relative to the sample mean of x (the mean of y stays in the v1 centre)
    F = predictor_frame(P)
    x_live = {"nifty50": P.loc[last, "r_nifty50"], "next50": P.loc[last, "r_next50"], "midcap100": P.loc[last, "r_midcap100"], "bank": P.loc[last, "r_bank"],
              "finserv": P.loc[last, "r_finserv"], "capmkts": P.loc[last, "r_capmkts"], "dlnvix_in": P.loc[last, "r_vix"], "cdsl": P.loc[last, "r_cdsl"],
              "mcx": P.loc[last, "r_mcx"], "angelone": P.loc[last, "r_angelone"], "nuvama": P.loc[last, "r_nuvama"], "cams": P.loc[last, "r_cams"],
              "kfintech": P.loc[last, "r_kfintech"], "bse_own": P.loc[last, "R"], "resid_nifty": P.loc[last, "resid_nifty50"], "resid_capmkts": P.loc[last, "resid_capmkts"],
              "sp500": spx_partial, "dlnvix_us": vix_partial, "dlnusdinr": fx_move, "d10y_bp": (LIVE_US["tnx_last_pct"] - LIVE_US["tnx_prev_pct"]) * 100,
              "dlnbrent": math.log(LIVE_US["brent_front_future_last"] / LIVE_US["brent_front_future_prev_settle"])}
    inc = {}
    for tgt in ("R", "G"):
        inc[tgt] = {}
        for name, xl in x_live.items():
            if name not in F.columns or not np.isfinite(xl):
                continue
            fit = hac_fit(P[tgt].values, F[name].values)
            xm = float(np.nanmean(F[name].values[fit["mask"]]))
            b, se = float(fit["params"][1]), float(fit["se"][1])
            sc = b2[tgt].get(name, {})
            inc[tgt][name] = {"x_live_pct": _f(xl * 100, 4) if name != "d10y_bp" else _f(xl, 2), "x_sample_mean_pct": _f(xm * 100, 4) if name != "d10y_bp" else _f(xm, 3),
                              "coef": _f(b, 5), "increment_pct": _f(b * (xl - xm) * 100, 4),
                              "increment_ci95_pct": [_f((b - 1.96 * se) * (xl - xm) * 100, 4), _f((b + 1.96 * se) * (xl - xm) * 100, 4)],
                              "status": sc.get("validation_status"), "family_holm_p": sc.get("cw_p_holm_family"), "group": SINGLE_GROUPS.get(name, "other")}
    s["single_predictor_increments_for_14oct"] = inc
    s["increments_note"] = ("increment = coef * (x_live - sample mean of x): the shift of the 14-Oct conditional mean relative to the unconditional mean; "
                            "increments of predictors in the same group are one signal (overlap), do not add them up.")
    return s, spx_partial


def build_patterns(res: dict) -> list[dict]:
    """One record per claimed pattern: definition, n, n_eff, period, benchmark, exceptions, CI/p (family adjusted), validation status."""
    pats = []
    a, b1, b2 = res["a_beta_corr"], res["b1_lead_lag"], res["b2_walk_forward"]
    b3, c, d1, d3, e = res["b3_conditional_beta_forecast"], res["c_asymmetry_regimes"], res["d1_macro_contemporaneous"], res["d3_sp500_to_gap"], res["e_idiosyncratic"]

    def add(**kw):
        pats.append(kw)

    # ---- (a) contemporaneous betas / correlations
    for key in ("nifty50", "midcap100", "next50", "bank", "finserv", "capmkts", "vix", "cdsl", "mcx", "angelone", "nuvama", "cams", "kfintech"):
        f = a["full_sample"][key]
        yr = a["by_year"][key]
        bs = [v["beta"] for v in yr.values() if v["beta"] is not None]
        rl = a["rolling"][key]["w250"]
        add(id=f"A_beta_{key}", topic="(a) contemporaneous beta/correlation",
            definition=f"OLS slope of BSE R_k on {f['label']} return/change over the same two session dates (HAC 5 lags); correlation alongside",
            n=f["n"], n_eff=f["n_eff"], period=f"{f['first']}..{f['last']}", benchmark="beta=1 / zero correlation; no unconditional benchmark applies to an association",
            estimate={"beta": f["beta"], "corr": f["corr"], "dimson_beta": f["dimson_beta_lags_m1_0_p1"]}, ci95=f["beta_ci95"], p_family_adjusted=None,
            exceptions=(f"beta by calendar year ranges {min(bs)}..{max(bs)}; rolling-250 beta range {rl['beta_min']}..{rl['beta_max']} (now {rl['last_beta']}); "
                        f"last-120-session beta {a['recent'][key].get('last120', {}).get('beta')}") if bs else "short sample",
            validation_status="descriptive_only",
            effect_on_next_session_forecast=("none by itself (contemporaneous); gives scenario mapping once the index move is known; see A_conditional_*" if key in ("nifty50", "capmkts") else "none (contemporaneous association)"))
    for nm in ("cond_nifty50", "cond_nifty50+capmkts"):
        v = b3[nm]
        add(id=f"A_conditional_{nm}", topic="(a)/(b3) conditional forecast given the same-day index move",
            definition="Walk-forward OLS of BSE R_k on same-day Nifty 50 (and Capital Markets) return vs expanding mean; min 250 training rows",
            n=v["n_oos"], n_eff=v["cw_n_eff"], period=f"{v['first_oos']}..{v['last_oos']}", benchmark="expanding mean of R",
            estimate={"oos_r2": _f(v["oos_r2"], 4), "oos_r2_first_half": _f(v["oos_r2_first_half"], 4), "oos_r2_second_half": _f(v["oos_r2_second_half"], 4)},
            ci95=None, p_family_adjusted={"cw_t": _f(v["cw_t"], 2), "p_holm": v["cw_p_holm_family"], "family": "F5_conditional", "family_size": 2},
            exceptions=f"OOS R2 by year {v['oos_r2_by_year']}", validation_status=v["validation_status"],
            effect_on_next_session_forecast="usable for scenario analysis (if Nifty moves x, BSE's conditional mean is beta*x); it does not forecast the index")
    s_ = a["sign_agreement_when_abs_nifty_ge_0.5pct"]
    add(id="A_sign_agreement", topic="(a) follow vs diverge", definition="share of sessions with |Nifty 50 return|>=0.5% in which BSE R has the same sign",
        n=s_["n"], n_eff=None, period="2017-02-06..2026-10-13", benchmark="0.5 (independent signs)", estimate=s_["share_same_sign"], ci95=s_["jeffreys_ci95"],
        p_family_adjusted={"p_raw": s_["binom_p_vs_0.5"]}, exceptions=f"BSE diverges (opposite sign) on {round(100*(1-s_['share_same_sign']),1)}% of such sessions",
        validation_status="descriptive_only", effect_on_next_session_forecast="none (contemporaneous)")
    # ---- (b1) lead-lag
    sig = [r for r in b1 if r["lag"] != 0 and r.get("p_holm") is not None and r["p_holm"] < 0.05]
    halves = {(h["series"], h["lag"]): h for h in res["diagnostics"]["leadlag_holm_cells_halves"]}
    for r in sig:
        h = halves.get((r["series"], r["lag"]))
        add(id=f"B_leadlag_{r['series']}_{r['lag']}", topic="(b1) lead-lag cross-correlation",
            definition=f"corr(BSE R_k, {r['series']} at k{'-' if r['lag']>0 else '+'}{abs(r['lag'])}); lag>0 means the other series leads BSE, lag<0 means BSE leads it",
            n=r["n"], n_eff=r["n_eff"], period="full available sample of the pair", benchmark="zero correlation (HAC null); 130 cells tested",
            estimate=r["corr"], ci95=r["ci95_boot"], p_family_adjusted={"p_raw": r["p_raw"], "p_holm": r["p_holm"], "p_bh": r["p_bh"], "family": "F1_leadlag", "family_size": 130},
            exceptions=(f"halves: first {h['first_half']['corr']}, second {h['second_half']['corr']}" if h else ""), validation_status="descriptive_only",
            effect_on_next_session_forecast="in-sample correlation; the out-of-sample versions are the F2/F3/F10 walk-forward patterns")
    nlag_sig = len([r for r in b1 if r["lag"] != 0 and r["p_raw"] is not None and r["p_raw"] < 0.05])
    add(id="B_leadlag_summary", topic="(b1) lead-lag cross-correlation", definition="13 series x 10 non-zero lags (-5..+5 excluding 0)", n=2388, n_eff=None,
        period="2017-02-06..2026-10-13", benchmark="5% of 130 cells (6.5) expected below p<0.05 by chance",
        estimate={"cells_raw_p_lt_0.05": nlag_sig, "cells_holm_lt_0.05": len(sig)}, ci95=None, p_family_adjusted={"family": "F1_leadlag", "family_size": 130},
        exceptions="all Holm-surviving cells are lag +-1 and sector peers (CDSL, Angel One); no index (Nifty 50, Next 50, Midcap 100, Bank, FinServ, Capital Markets) or India VIX lead/lag survives; lags 2..5 are all null",
        validation_status="descriptive_only", effect_on_next_session_forecast="none beyond the peer walk-forward results below")
    # ---- (b2) walk-forward predictors of next-day R / G
    names = {"nifty50": "Nifty 50", "next50": "Next 50", "midcap100": "Midcap 100", "bank": "Bank", "finserv": "Fin Services", "capmkts": "Capital Markets", "dlnvix_in": "Δln India VIX",
             "cdsl": "CDSL", "mcx": "MCX", "angelone": "Angel One", "nuvama": "Nuvama", "cams": "CAMS", "kfintech": "KFin Tech", "bse_own": "BSE own lagged R",
             "resid_nifty": "BSE residual vs Nifty (lagged)", "resid_capmkts": "BSE residual vs Capital Markets (lagged)", "sp500": "S&P 500 prior US session(s)",
             "dlnvix_us": "Δln US VIX prior US session(s)", "d10y_bp": "Δ US 10y yield (bp) prior", "dlnusdinr": "Δln USD/INR prior (noon NY)", "dlnbrent": "Δln Brent spot prior",
             "m_india": "[Nifty 50, Δln India VIX] lagged", "m_all": "[Nifty 50, Δln India VIX, S&P 500, Δln US VIX]"}
    for tgt in ("R", "G"):
        for name in PRED_ORDER:
            v = b2[tgt][name]
            if "oos_r2" not in v:
                continue
            fam = {"R": "F2_wf_R", "G": "F3_wf_G"}[tgt]
            add(id=f"B_wf_{tgt}_{name}", topic=f"(b2) walk-forward predictor of next-session {tgt}",
                definition=f"expanding-window OLS of {tgt}_k on {names[name]} known before the open of session k; min train {v['min_train']}",
                n=v["n_oos"], n_eff=v["cw_n_eff"], period=f"{v['first_oos']}..{v['last_oos']}", benchmark="expanding mean of the same target (same training rows)",
                estimate={"oos_r2": _f(v["oos_r2"], 5), "coef": v["full_sample_coef_per_unit"], "insample_r2": v["full_sample_insample_r2"]}, ci95=v["full_sample_coef_ci95"],
                p_family_adjusted={"cw_t": _f(v["cw_t"], 2), "p_raw": v["cw_p_one_sided"], "p_holm": v["cw_p_holm_family"], "p_bh": v["cw_p_bh_family"], "family": fam, "family_size": v["family_size"]},
                exceptions=f"OOS R2 halves {_f(v['oos_r2_first_half'],4)}/{_f(v['oos_r2_second_half'],4)}; ex-top5 |y| {_f(v['oos_r2_ex_top5_abs_y'],4)}; by year {v['oos_r2_by_year']}; strict gate {'pass' if v['passes_strict_gate'] else 'fail'}",
                validation_status=v["validation_status"],
                effect_on_next_session_forecast="see live_state.single_predictor_increments_for_14oct")
    # ---- (b2) BSE leads others
    for key, v in res["f10_bse_leads_others"].items():
        if "oos_r2" not in v:
            continue
        add(id=f"B_bse_leads_{key}", topic="(b2) does BSE lead others? walk-forward",
            definition=f"expanding OLS of {key} return at k on BSE R at k-1 vs expanding mean", n=v["n_oos"], n_eff=v["cw_n_eff"], period=f"{v['first_oos']}..{v['last_oos']}",
            benchmark="expanding mean of the other series", estimate={"oos_r2": _f(v["oos_r2"], 5), "coef": v["coef_other_on_bse_lag1"]}, ci95=v["coef_ci95"],
            p_family_adjusted={"cw_t": _f(v["cw_t"], 2), "p_raw": v["cw_p_one_sided"], "p_holm": v["cw_p_holm_family"], "family": "F10_bse_leads", "family_size": 13},
            exceptions=f"halves {_f(v['oos_r2_first_half'],4)}/{_f(v['oos_r2_second_half'],4)}; by year {v['oos_r2_by_year']}", validation_status=v["validation_status"],
            effect_on_next_session_forecast="none for BSE's own forecast; relevant only for peers/sector read-through")
    # ---- (c) asymmetry / regimes
    for key, v in c["up_down"].items():
        add(id=f"C_updown_{key}", topic="(c) asymmetric beta",
            definition=f"R_k = a + b_up*max(x,0) + b_dn*min(x,0), x = {key} return; H0 b_up = b_dn (HAC); plus walk-forward asymmetric-vs-symmetric CW test",
            n=v["n"], n_eff=None, period="full available sample", benchmark="symmetric beta model", estimate={"beta_up": v["beta_up"], "beta_down": v["beta_down"], "n_up": v["n_up_days"], "n_down": v["n_down_days"]},
            ci95=v["diff_ci95"], p_family_adjusted={"p_equal_raw": v["p_equal_slopes"], "p_equal_holm": v["p_equal_adj"]["p_holm"], "wf_cw_holm": v["wf_p_adj"]["p_holm"], "family": "F6_asym", "family_size": 16},
            exceptions=("capital-markets sign is opposite to Nifty's (up beta > down beta)" if key == "capmkts" else "sign of up-down difference differs across indices"),
            validation_status="not_found", effect_on_next_session_forecast="none: no robust asymmetry; use symmetric beta")
    for key, v in c["vix_terciles"].items():
        t = v["terciles"]
        add(id=f"C_vix_terciles_{key}", topic="(c) beta in VIX terciles",
            definition=f"slope of R_k on {key} return within ex-ante terciles of India VIX at k-1 (expanding thresholds); Wald equal slopes + walk-forward interaction CW test",
            n=sum(x["n"] for x in t.values()), n_eff=sum(x["n_eff"] for x in t.values()), period="expanding terciles need 250 sessions: 2018-02..2026-10-13", benchmark="constant beta",
            estimate={k2: x["beta"] for k2, x in t.items()}, ci95={k2: x["ci95"] for k2, x in t.items()},
            p_family_adjusted={"wald_p": v["wald_p"], "wald_holm": v["wald_adj"]["p_holm"], "wf_cw_holm": v["wf_adj"]["p_holm"], "family": "F6_asym", "family_size": 16},
            exceptions="capital-markets terciles are dominated by the calm tercile because its sample starts in 2024-09 when VIX was low relative to the 2017+ history",
            validation_status="not_found", effect_on_next_session_forecast="none")
        cd = v["corr_high_vs_low"]
        if cd:
            add(id=f"C_stress_corr_{key}", topic="(c) correlation in stress vs calm",
                definition=f"corr(R_k, {key}) in the high vs low ex-ante India VIX tercile; difference by stationary bootstrap; Forbes-Rigobon heteroskedasticity correction",
                n=v["terciles"]["high"]["n"] + v["terciles"]["low"]["n"], n_eff=None, period="2018-02..2026-10-13", benchmark="same correlation in both regimes",
                estimate={"corr_high": cd["corr_high_tercile"], "corr_low": cd["corr_low_tercile"], "diff": cd["diff_high_minus_low"], "forbes_rigobon_corrected_high": cd["forbes_rigobon_corrected_corr_high_vs_calm_variance"]},
                ci95=cd["boot_ci95"], p_family_adjusted={"p_boot": cd["adj"]["p_raw"], "p_holm": cd["adj"]["p_holm"], "family": "F6_asym", "family_size": 16},
                exceptions="the raw difference is the statistical consequence of a larger index variance in stress; corrected correlation is about the calm-regime value",
                validation_status="descriptive_only", effect_on_next_session_forecast="none")
    dd = c["decline_days"]["nifty50"]
    add(id="C_decline_days_nifty50", topic="(c) market-decline days", definition="sessions with Nifty 50 <= -1.5% vs the rest: slope of BSE R on Nifty, mean returns",
        n=dd["decline_le_-1.5pct"]["n"], n_eff=None, period="2017-02-06..2026-10-13", benchmark="other days",
        estimate={"decline": dd["decline_le_-1.5pct"], "other": dd["other_days"]}, ci95=dd["decline_le_-1.5pct"]["ci95"], p_family_adjusted=None,
        exceptions="BSE fell more than the index on only 52% of decline days", validation_status="descriptive_only", effect_on_next_session_forecast="scenario: conditional on a Nifty decline of x%, BSE loses about 1.1x on average")
    # ---- (d) macro
    for k, v in d1.items():
        add(id=f"D_contemp_{k}", topic="(d) macro sensitivity (contemporaneous)", definition=f"OLS of BSE R_k on {k} window return ({v['alignment'][:5]}), univariate and controlling for Nifty 50; effect in percentage points of BSE return {v['unit']}",
            n=v["n"], n_eff=v["n_eff"], period=f"{v['first']}..{v['last']}", benchmark="zero slope", estimate={"uni_pp": v["uni_bse_ret_pct_per_unit"], "with_nifty_control_pp": v["ctrl_nifty_bse_ret_pct_per_unit"]},
            ci95={"uni": v["uni_ci95_pct"], "ctrl": v["ctrl_nifty_ci95_pct"]},
            p_family_adjusted={"uni_holm": v["uni_adj"]["p_holm"], "ctrl_holm": v["ctrl_adj"]["p_holm"], "family": "F7_macro_contemp", "family_size": 14},
            exceptions="association only; the effect disappears or shrinks once Nifty 50 is controlled" if k not in ("dlnbrent_prior", "dlnbrent_same", "d10y_bp_prior") else "no association",
            validation_status="descriptive_only", effect_on_next_session_forecast="none (contemporaneous)")
    for tgt in ("G", "R"):
        s2 = d3[tgt]
        add(id=f"D_sp500_{tgt}", topic="(d) PRIMARY test: previous US session S&P 500 -> next Indian session",
            definition=f"{tgt}_k = a + b * S&P500 log return over US sessions dated in [d_(k-1), d_k) (complete before the Indian open); b = pp of BSE {tgt} per +1% S&P",
            n=s2["full_sample"]["n"], n_eff=s2["full_sample"]["n_eff"], period=s2["full_sample"]["period"], benchmark="expanding/train mean of the same target",
            estimate={"beta_full": s2["full_sample"]["beta_per_1pct_sp500_in_pct"], "beta_train": s2["split"]["beta_train"], "beta_test_refit": s2["split"]["beta_test_refit"],
                      "split_oos_r2": s2["split"]["oos_r2_fixed_train_coef_vs_train_mean"], "wf_oos_r2": _f(s2["walk_forward"]["oos_r2"], 4), "in_sample_r2": s2["full_sample"]["r2"]},
            ci95=s2["full_sample"]["ci95"], p_family_adjusted={"split_cw_holm": s2["split"]["adj"]["p_holm"], "wf_cw_holm": s2["walk_forward"]["adj"]["p_holm"], "family": "F8_sp500_gap", "family_size": 4},
            exceptions=(f"beta by year {{{', '.join(f'{y}: {v[chr(98)+chr(101)+chr(116)+chr(97)]}' for y, v in s2['by_year'].items())}}}; by thirds {[t['beta'] for t in s2['by_third']]}; "
                        f"slope test-vs-train diff {s2['split']['slope_stability_test']['beta_diff_test_minus_train']} (p={s2['split']['slope_stability_test']['p']}); WF OOS R2 by year {s2['walk_forward']['oos_r2_by_year']}"),
            validation_status=s2["validation_status"], effect_on_next_session_forecast="mechanical adjustment of the 14-Oct gap by b*(partial S&P - mean); see live_state.gap_adjustment_14oct")
    # ---- (e) idiosyncratic
    for spec, lab in (("R~nifty50", "vs Nifty 50"), ("R~nifty50+peers_ew", "vs Nifty 50 + equal-weight peers"), ("R~nifty50+capmkts", "vs Nifty 50 + Capital Markets index (BSE is itself a constituent: mechanical overlap)"),
                      ("G~nifty50_gap", "opening gap vs Nifty gap"), ("I~nifty50_intraday", "open-to-close vs Nifty open-to-close")):
        v = e[spec]
        full = v["full"]
        rec = v.get("last250") or v.get("2024-09_onward")
        add(id=f"E_idio_{spec}", topic="(e) idiosyncratic variance share", definition=f"1 - R2 of BSE {spec}; {lab}", n=full["n"], n_eff=None,
            period="full available sample" + ("" if spec != "R~nifty50+capmkts" else " (2024-09-16..2026-10-13)"), benchmark="share=1 (no market explanation)",
            estimate={"idio_share_full": full["idio_share"], "idio_share_recent": {k: x["idio_share"] for k, x in v.items() if k in ("2025_onward", "last250", "last120", "2024-09_onward")},
                      "by_year": {k: x["idio_share"] for k, x in v.items() if k.isdigit() or k in ("2017-2019", "2026_ytd")}},
            ci95=full.get("idio_share_boot_ci95"), p_family_adjusted=None,
            exceptions="year-to-year range " + str((min(x['idio_share'] for k, x in v.items() if k.isdigit() or k in ('2017-2019', '2026_ytd')), max(x['idio_share'] for k, x in v.items() if k.isdigit() or k in ('2017-2019', '2026_ytd')))),
            validation_status="descriptive_only", effect_on_next_session_forecast="sets how much of the 14-Oct variance is market-driven: little (about 10-25%)")
    for pt in pats:
        if pt["id"].startswith("B_wf_") and any(pt["id"].endswith(sfx) for sfx in ("_bse_own", "_resid_nifty", "_cdsl", "_mcx", "_nifty50", "_angelone", "_cams", "_kfintech", "_nuvama", "_next50", "_midcap100", "_bank", "_finserv", "_capmkts", "_dlnvix_in", "_m_india")):
            pt["caveat"] = ("estimated almost entirely in the 30-minute-VWAP-close era (to 2026-08-02); the closing-auction era has n=50 sessions (lag-1 own autocorrelation 0.018, CI -0.26..0.29), "
                            "so persistence of this lagged-Indian-return effect after the close-method change is untested")
        if pt["id"].startswith("B_bse_leads_"):
            pt["caveat"] = "cross-autocorrelations are positive for most sector peers (not only BSE); a common mechanism (VWAP closes, slow sector news diffusion) cannot be separated from BSE leadership"
    return pats


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o)
    return str(o)


def main():
    P, ix, peer_events, last_obs = build_panel()
    REG = Registry()
    res = {"meta": {}}
    res["meta"] = {
        "stock": "BSE Ltd (NSE: BSE)", "target_session": "2026-10-14", "P0": 3375.40, "cutoff_ist": CUTOFF_IST,
        "sample": {"first": str(P.index[0].date()), "last": str(P.index[-1].date()), "n_sessions": int(len(P))},
        "returns_def": "log returns vs bonus-adjusted previous kept close: G=ln(open/prev), I=ln(close/open), R=G+I; index/peer returns over the same two BSE session dates",
        "hac": f"Newey-West Bartlett, {HAC_LAGS} lags, small-sample correction", "bootstrap": f"stationary bootstrap mean block 10, B={B_BOOT}, seed {RNG_SEED}",
        "capmkts_available_from": str(CAPMKTS_START.date()), "peer_corporate_actions_detected": peer_events,
        "prereg": "see module docstring of src/behaviour/linkages.py (written before outcomes were computed)",
        "data_notes": {
            "index_last_in_file": "2026-10-12 (index_daily.csv); 2026-10-13 row embedded from NSE ind_close_all_13102026.csv, Last-Modified 19:50 IST",
            "n_nan_by_column": {c: int(P[c].isna().sum()) for c in ["r_nifty50", "r_next50", "r_midcap100", "r_bank", "r_finserv", "r_capmkts", "r_vix", "r_cdsl", "r_mcx", "r_angelone", "r_nuvama", "r_cams", "r_kfintech", "r_peers_ew", "sp500_prior", "dlnvix_us_prior", "d10y_bp_prior", "dlnusdinr_prior", "dlnbrent_prior"]},
            "fred_publication_lag_note": "FRED values are used at EVENT time (dated u is assumed known after the close of u); the live state cannot use them because the files are stale",
        },
    }
    mc = {}
    for nm in ("SP500", "VIXCLS", "DGS10", "DEXINUS", "DCOILBRENTEU", "DTWEXBGS"):
        ss = read_fred(nm)
        mc[nm] = {"last_obs": str(ss.index[-1].date()), "n_since_2017-02": int((ss.index >= "2017-02-01").sum()),
                  "sessions_stale_vs_2026-10-13_bday": int(len(pd.bdate_range(ss.index[-1], "2026-10-13")) - 1)}
    res["meta"]["macro_coverage"] = mc
    res["meta"]["macro_event_times"] = {"SP500": "NYSE close 16:00 ET (20:00 UTC EDT) of the dated day", "VIXCLS": "CBOE VIX close 16:15 ET", "DGS10": "H.15 constant-maturity 10y, end of US day (bond market closed on 2026-10-12 Columbus Day: no obs)",
                                          "DEXINUS": "Fed H.10 noon buying rate New York (12:00 ET = 16:00 UTC = 21:30 IST) of the dated day", "DCOILBRENTEU": "EIA Europe Brent spot FOB, daily (assessed around the London close)",
                                          "indian_session": "03:45-10:00 UTC (09:15-15:30 IST)"}
    res["meta"]["access_log"] = [
        {"source": "data/raw/macro/*.csv (FRED)", "result": "read as supplied; deliberately NOT re-downloaded (a refresh could contain post-cutoff observations)"},
        {"source": "data/raw/macro/usdinr_ecb_2017_2026.json", "result": "FAILED: file contains an HTML '301 Moved Permanently' page, not data; not used"},
        {"source": "https://api.frankfurter.app/2026-10-01..2026-10-13?from=USD&to=INR", "result": "OK with curl -L; ECB reference rates, used only for the live-state USD/INR check"},
        {"source": "https://nsearchives.nseindia.com/content/indices/ind_close_all_13102026.csv", "result": "OK HTTP 200, Last-Modified 2026-10-13 14:20:38 GMT (19:50 IST) - before the cutoff; supplies the 13-Oct index row"},
        {"source": "https://query1.finance.yahoo.com/v8/finance/chart/{^GSPC,ES=F,^VIX,^TNX,BZ=F,INR=X}?interval=5m&range=5d&includePrePost=true", "result": "OK HTTP 200 (one request per symbol, 3 rounds, no 429); unofficial quotes; Yahoo meta previousClose for ^VIX (14.84) is the 2026-10-09 close and was replaced by FRED's 2026-10-12 close 15.21"},
        {"source": "https://stooq.com/q/l/?s=^spx", "result": "FAILED: connection reset by peer (proxy: ws_closed_mid_exchange); not used"},
        {"source": "WebSearch: NIFTY Capital Markets constituents/weights", "result": "summary only (BSE weight 22.88% in the 2025-03-28 NSE factsheet per the summary, 15.09% per an Angel One article); the PDF itself was not opened -> unverified"},
        {"source": "GIFT Nifty / SGX Nifty, Asian index futures, Nifty options overnight", "result": "NOT obtained and not in the supplied data; the S&P effect may be partly subsumed by them (cannot test)"},
    ]
    res["a_beta_corr"] = part_a(P)
    b1 = part_b1(P, REG)
    b2 = part_b2(P, REG)
    b3 = part_b3_conditional(P, REG)
    c = part_c(P, REG)
    d1 = part_d1(P, REG)
    d3 = part_d3(P, REG)
    e = part_e(P)
    f9 = part_f9(P, REG)
    f10 = part_f10(P, REG)
    res["multiple_testing_families"] = REG.adjust()
    res["b1_lead_lag"] = finalize_b1(b1, REG)
    res["b2_walk_forward"] = finalize_b2(b2, REG)
    res["b3_conditional_beta_forecast"] = finalize_b3(b3, REG)
    res["c_asymmetry_regimes"] = finalize_c(c, REG)
    res["d1_macro_contemporaneous"] = finalize_d1(d1, REG)
    res["d3_sp500_to_gap"] = finalize_d3(d3, REG)
    res["e_idiosyncratic"] = e
    res["f9_incremental_exploratory"] = finalize_f9(f9, REG)
    res["f10_bse_leads_others"] = finalize_f10(f10, REG)
    res["diagnostics"] = part_diagnostics(P)
    res["diagnostics"]["leadlag_holm_cells_halves"] = leadlag_halves(P, res["b1_lead_lag"])
    ls, spx_partial = live_state(P, last_obs, b2, d3)
    # conditional adjustment arithmetic for the 14-Oct gap (only meaningful if validated)
    g = d3["G"]
    xs = P["sp500_prior"].dropna()
    xbar = float(xs.mean())
    x_recent = P["sp500_prior"].iloc[-250:].dropna()
    b_full = g["full_sample"]["beta_per_1pct_sp500_in_pct"]
    b_recent = ols_slope(P["G"].values[-250:], P["sp500_prior"].values[-250:])
    inc = lambda b: _f(b * (spx_partial - xbar) * 100, 4)   # incremental to the unconditional centre (mean G stays in the v1 centre)
    ls["gap_adjustment_14oct"] = {
        "validated": g["validation_status"], "model": "G_k = a + b * SP500_prior_window; adjustment = b * (partial S&P return - sample mean S&P window return)",
        "sample_mean_sp500_window_logpct": _f(xbar * 100, 4), "partial_sp500_logpct": _f(spx_partial * 100, 4),
        "beta_full_sample": b_full, "beta_ci95": g["full_sample"]["ci95"],
        "beta_last250": _f(b_recent["beta"], 3), "beta_last250_ci95": [_f(v, 3) for v in b_recent["ci95"]],
        "adjustment_pct_full_beta": inc(b_full), "adjustment_pct_ci95_full_beta": [inc(v) for v in g["full_sample"]["ci95"]],
        "adjustment_pct_last250_beta": inc(b_recent["beta"]),
        "sd_G_pct_unconditional": _f(np.nanstd(P["G"].values) * 100, 3), "sd_G_pct_residual_after_sp500": _f(np.sqrt(np.nanmean(hac_fit(P["G"].values, P["sp500_prior"].values)["resid"] ** 2)) * 100, 3),
        "sensitivity_per_1pct_sp500_close": b_full,
        "remaining_session_uncertainty": "the S&P 500 value is a partial-session observation; E[full-day return | partial] = partial return (martingale), so the adjustment uses the partial return directly; the unobserved remainder only adds variance",
        "recommendation": ("apply the mechanical adjustment (validated); effect is tiny relative to sd of G" if g["validation_status"] == "validated_out_of_sample"
                           else "do not apply (not validated): leave the 14-Oct gap centred as in v1"),
    }
    fx_live = math.log(LIVE_US["usdinr_yahoo_last"] / LIVE_US["usdinr_yahoo_prev_close"])
    vix_live = math.log(LIVE_US["vix_last"] / LIVE_US["vix_prev_close"])
    res["composite_exploratory"] = part_composite(P, res["f9_incremental_exploratory"], spx_partial, vix_live, {"dlnusdinr": fx_live})
    res["live_state"] = ls
    res["patterns"] = build_patterns(res)
    res["n_tests_total"] = int(len(REG.rows))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1, default=_json_default)
    print("wrote", OUT, "tests:", len(REG.rows))
    print(json.dumps(res["multiple_testing_families"], indent=1))


if __name__ == "__main__":
    main()
