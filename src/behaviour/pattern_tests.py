"""v2 workstream "patterns": momentum vs mean reversion, opening-gap continuation vs reversal, breakouts with volume and
liquidity, liquidity (Amihud) and calm / trending / stressed / event-driven regimes for NSE:BSE (BSE Ltd).

Run:  cd /home/user/pred_18 && PYTHONPATH=src python3 src/behaviour/pattern_tests.py          (writes results/behaviour/patterns.json)
Self-test on SIMULATED data only (no BSE outcome is touched):  PYTHONPATH=src python3 src/behaviour/pattern_tests.py --selftest
Reads data read-only and fetches NOTHING (information cutoff 2026-10-13 22:00 IST; the 14-Oct-2026 session is unseen; the
 only non-repo facts are the 2026-10-13 index row, copied from the constants of src/behaviour/linkages.py, see IDX_20261013).
The markdown report research/v2/04_momentum_gap_volume.md is written by hand from patterns.json.

=====================================================================================================================
PRE-REGISTRATION OF EVERY TEST.  This text was written BEFORE any return / gap / volume / regime statistic of BSE was
computed by this workstream (file mtime precedes the first execution; the SHA-256 of this file as run is stored in
patterns.json).  Thresholds are fixed here and never tuned on outcomes.  Every hypothesis test is entered in one registry
(REG) with a family label; Holm (FWER) and Benjamini-Hochberg (FDR) adjusted p-values are reported (a) within family and
(b) across the WHOLE registry (the stringent claim level).
=====================================================================================================================

PEEKING LOG (what had been seen before writing this text)
 * docs/V2_BRIEF.md, docs/PREREGISTRATION.md, docs/DEVIATIONS.md (first 80 lines), src/common.py, src/models.py (sigma_ewma,
   constants), src/episodes.py (E1-E5 definitions), src/conditional_day.py, README.
 * results/conditional_day.json (v1 gap table, first ~150 lines): full-sample P(I>0 | gap-up > 0.5 sd) = 0.359 (n 273) and
   0.714 (n 42) since 2024-07 -> the "gap effect flips sign between periods" hypothesis (Part 2) is INFORMED by v1, not blind;
   the break dates (2024-07-01 = v1 Validation start, 2026-08-03 = closing-auction start) come from the v1 protocol / exchange
   rule, not from my outcome search.  v1 reported no directional skill for ridge/logit.
 * results/forecasts_R.csv: head/tail rows and model counts only (no coverage or loss computed); the selected models of the
   frozen record (R: S6 blend; G: S4; I: S6; L0 location) from results/forecast_record_2026-10-14.json keys.
 * Data coverage only (no return statistics): 2,388 sessions 2017-02-06..2026-10-13; deliv_pct valid 2019-10-01..2026-10-12
   (missing 2022-08-08 and 2026-10-13); 566 sessions since 2024-07-01; 50 since 2026-08-03; index_daily ends 2026-10-12;
   share volume does not scale cleanly through the 2022-03-21 bonus (QA only) -> rupee turnover is used for relative volume.
 * src/behaviour/linkages.py header and constants (design text and the 2026-10-13 index row), NOT its results.
   results/behaviour/linkages.json and research/v2/03_market_linkages.md were not opened.

NOTATION. Sessions k = 0..N-1 (N = 2388; bse_daily.csv via common.load_bse()/targets()).  G = ln(open/prev), I = ln(close/open),
 R = G + I (prev is the bonus-adjusted previous kept close).  lc_k = sum_{j<=k} R_j = log bonus-adjusted close (price return).
 Adjusted log high/low of session k: lh_k = lc_{k-1} + Hp_k, ll_k = lc_{k-1} + Lp_k  (lc_{-1} = 0).
 "Known at close k" = uses sessions <= k only.  A state "S_k" is applied to session k+1.  Dates: EARLY = date < 2024-07-01,
 POST = date >= 2024-07-01, L1 = 2024-07-01 <= date < 2026-08-03, AUC = date >= 2026-08-03 (closing-auction close),
 FULL = k >= 60.  Dev/Val/Final of v1: Dev k<=2024-06-28, Val 2024-07-01..2025-06-30, Final 2025-07-01+.
 sig_k = sqrt(mean(R_{k-59..k}^2))  (RMS60, zero-mean, valid k>=59).  vol20_k = RMS of R_{k-19..k}.
 ex-ante expanding terciles: for a series x, at close k the cut points are the 1/3 and 2/3 quantiles of {x_j : j<=k, valid}
   (min 250 valid obs, otherwise undefined); state 0 = x_k <= q33, 2 = x_k > q67, 1 = otherwise.
 Stationary bootstrap: mean block 10, B = 2000, resampling time indices jointly (paired variables and cell masks stay
   aligned), seed 20261014.  Bootstrap p-values are Wald-type: z = (est - null)/SE_boot, two-sided normal (so p is not
   floored at 1/(B+1)); percentile 95% CIs are reported alongside.  HAC = Newey-West (Bartlett) with the stated lags.

PARTITIONS (all ex-ante: state at close k describes session k+1)
 PV  vol tercile of u_k = sig_k (expanding terciles, min 250 obs of u -> valid k>=308): lo / mid / hi.
 PN  Nifty-50 close_k > its 200-session simple average (index sessions, min 200) -> "above" else "below" (asof BSE date k).
 PD  BSE drawdown dd_k = exp(lc_k - max(lc_{k-249..k})) - 1 (min 120 obs): near_high dd > -10%; pullback -20% < dd <= -10%;
     deep dd <= -20%.  (-10% / -20% = conventional correction / bear thresholds, chosen before looking at BSE's dd; BSE's
     52-week-high from the pre-registration peeking log suggests it is near -24%, i.e. in "deep").
 RG  4-class regime (Part 5).

PART 1a  AUTOCORRELATION AND VARIANCE RATIOS BY REGIME  (family P1_acf, P1_vr)
 Rc = R - mean(R) (full-sample mean; centring only).  Cell c of partition P (or "all"): sessions k>=1 with state_{k-1} == c.
 rho_c = sum Rc_k Rc_{k-1} / sqrt(sum Rc_k^2 * sum Rc_{k-1}^2) over the cell.  H0: rho = 0.  Tests: 9 cells (all, PV x3, PN x2,
 PD x3) + 3 cell-difference tests (PV hi-lo, PN above-below, PD near_high-deep).  [12 tests]
 VR_c(q) = sum_{k in cell} S2_k / sum_{k in cell} Q_k with S2_k = (sum_{j<q} Rc_{k+j})^2, Q_k = sum_{j<q} Rc_{k+j}^2, window
 start k, cell = state_{k-1}, q in {5, 20}.  Null VR=1 (martingale difference; unbiased because the state is ex-ante).  9 cells x 2
 q + 3 differences x 2 q.  [24 tests]  Validation status of all these in-sample statistics: descriptive_only.

PART 1b  TIME-SERIES MOMENTUM / 1-DAY REVERSAL, WALK-FORWARD VS EXPANDING MEAN  (family P1_wf)
 y_k = R_k.  Signals known at close k-1: m1 = R_{k-1} (reversal), m5, m20, m60 = lc_{k-1} - lc_{k-1-h}.
 OOS sessions k = 500..N-1 (2019-02-15 first, as in v1).  Benchmark: expanding mean of y_j, j<k.  Model U (unconditional): OLS of
 y_j on [1, x_j] on pairs j<k (x_j = signal known at close j-1), prediction a+b*x_k, refit every session.  Model RC(P) (regime-
 conditional, P in PV, PN, PD): OLS using only training pairs whose state at close j-1 equals the state at close k-1 (min 100
 training pairs in the cell, else the benchmark forecast is used for that session).  These are 1- or 2-parameter-per-cell
 models of a single signal: the v1 ridge/logit features are not refit.
 Statistic: OOS R2 = 1 - SSE_model/SSE_bench; Clark-West (2007) one-sided t on f = e_b^2 - (e_m^2 - (yb-ym)^2), HAC 5 lags.
 16 CW tests (4 signals x {U, RC(PV), RC(PN), RC(PD)}).  Pesaran-Timmermann sign-independence test of sign(x_k) vs sign(R_k) on the
 OOS sessions for the 4 signals (two-sided; sign of the association says momentum vs reversal).  [4 tests] Total 20.
 Reported also: OOS R2 in the first/second half of the OOS sample, in Final (2025-07+), after dropping the 5 largest |R| sessions,
 and per cell (descriptive).  STATUS RULE (fixed now): validated_out_of_sample iff pooled OOS R2 > 0 AND within-family Holm-adjusted
 CW p < 0.05 AND R2 > 0 in both OOS halves AND R2 > 0 in Final AND R2(ex top-5 |R|) > 0; else not_found.

PART 2  GAP CONTINUATION VS REVERSAL  (families P2_gap, P2_gapregime, P2_flip)
 gz_k = G_k / sig_{k-1} (k>=60).  Valid for the sign test if |gz|>=0.25 and I != 0.  Size buckets by |gz|: S [0.25,0.5), M [0.5,1),
 L [1,inf).  Continuation C_k = 1[sign(I_k) = sign(G_k)].  Cells: dir in {up, down} x size {S, M, L} (6), dir-pooled |gz|>=0.25
 (2: "up_all", "down_all"), all-pooled |gz|>=0.25 (1) = 9 cells, in each of the periods FULL, POST, AUC.
 Benchmark/null: circular-shift permutation of the I series within the period (all shifts with margin 10): this breaks the G-I
 alignment but preserves the marginal P(I>0), the sign of the gap and serial dependence of I; null rate pi0 = mean of the shifted
 rates.  Test: continuation rate c vs pi0; p = empirical shift p (two-sided) if n_cell < 30, else normal-approximation p from the
 shift distribution (mean/SD).  Cells with n < 15 are reported but NOT tested.  CI: stationary-bootstrap 95% percentile CI of c.
 Also reported (descriptive): mean of sign(G)*I in %, P(I>0|up), P(I<0|down), flat-gap (|gz|<0.25) rows.
 Regime x gap (family P2_gapregime): cells = {RG class (4), PV (3), PN (2)} x {|gz|>=0.5 pooled over directions}, periods FULL and
 POST, same permutation test within the period (AUC reported as counts only).  [<= 18 tests]
 FLIP TESTS (family P2_flip; each run only if both groups have n >= 8):
   (i) Fisher exact two-sided tests of the continuation rate between periods EARLY vs L1, L1 vs AUC, EARLY vs AUC for cells
       up_M+L (gz>=0.5), down_M+L (gz<=-0.5) and pooled |gz|>=0.5  [<= 9 tests], each with a bootstrap CI of the rate difference.
   (ii) slope interaction I = a + b*G + (b_L1-b_E)*G*L1 + (b_AUC-b_E)*G*AUC; HAC 5 lags; tests b_L1 = b_E and b_AUC = b_L1  [2 tests].
   (iii) sup-Wald (unknown break date, 15% trimming) for a break in (a, b) of I = a + b*G; wild-bootstrap (Rademacher, fixed
       regressors, B = 999) p-value  [1 test].
 Descriptive: calendar-year table of P(I>0 | gz>=0.5) and of continuation for |gz|>=0.5; v1 replication using the v1 EWMA(0.94) sigma.
 STATUS RULE for "early-period gap rule" (trade in the direction of the EARLY sign of c - pi0): validated_out_of_sample iff the POST
 cell has the same sign and family-Holm p < 0.05; contradicted iff opposite sign and family-Holm p < 0.05 for the same cell;
 else not_found.  The flip itself: descriptive_only (in-sample structural difference) if flip tests reject (Holm family p<0.05),
 else "flip not established".

PART 3  BREAKOUTS  (families P3_breakout, P3_holdout)
 Up-breakout B+_k: lc_k > max(lh_{k-20..k-1}); down-breakout B-_k: lc_k < min(ll_{k-20..k-1}) (Donchian on adjusted intraday
 high/low, k>=20).  Forward log return F_h,k = lc_{k+h} - lc_k, h in {1,5,10} (needs k+h<=N-1).  Note: before 2026-08-03 the close is
 a 30-min VWAP, not a tradable auction price: F_h is an "close-to-close" statistic, not an executable return.
 Relative volume RV_k = turnover_cr_k / mean(turnover_cr_{k-20..k-1})  (rupee turnover is corporate-action free); RV terciles:
 ex-ante expanding (min 250).  Delivery: DP_k = deliv_pct_k level, expanding terciles over sessions with delivery data (min 250 ->
 from about 2020-10); sessions without delivery data are excluded from the DP scheme.
 Regressions (OLS, HAC lag h+5) of F_h on a constant and breakout dummies; coefficient = mean(F_h | breakout cell) - mean(F_h | day
 that is neither B+ nor B-) ("excess").  Scheme 0: [B+, B-].  Scheme RV: [B+/- x RV tercile (6)].  Scheme DP: [B+/- x DP tercile
 (6)].  Tests: scheme 0: 2 dir x 3 h = 6; scheme RV: 18; scheme DP: 18; high-minus-low tercile contrast: 2 dir x 3 h x {RV, DP} =
 12.  [54 tests, family P3_breakout]  Persistence vs reversal: up-breakout persistence if excess > 0, reversal if < 0; down-breakout
 persistence if excess < 0.  Also reported: mean/median F_h on breakout days, on all days, and on non-breakout days; share of
 breakout days with sign(F_h) = breakout direction; n (flagged days), n_clusters (spells separated by > h sessions), n_eff =
 n * (se_iid/se_HAC)^2 capped to [1, n].
 HOLDOUT (family P3_holdout): Dev = windows entirely before 2024-07-01; Holdout = k >= 2024-07-01.  For direction in {up, down},
 h in {1,5,10} and cell in {all breakouts, high-RV-tercile breakouts}: the sign of the Dev excess fixes the predicted direction;
 the one-sided HAC test of the holdout excess in that direction is the test.  [12 tests]  STATUS RULE: validated_out_of_sample iff
 holdout family-Holm p < 0.05 AND Dev excess nominal two-sided p < 0.10 in the same sign; else not_found; the in-sample table is
 descriptive_only.

PART 4  LIQUIDITY  (family P4_liq)
 T = turnover_cr.  TZ_k = (ln T_k - mean(ln T_{k-60..k-1})) / sd(ln T_{k-60..k-1}) (clipped to [-3,3]).  A_k = 100*|R_k|/T_k
 (% per Rs crore); A20_k = mean(A_{k-19..k}); LA_k = ln A20_k; ILZ_k = (LA_k - mean(LA_{k-250..k-1}))/sd(...) clipped [-3,3].
 IL state: expanding terciles of LA_k (0 liquid, 1, 2 illiquid).  TO state: expanding terciles of ln(mean(T_{k-19..k}) /
 median(T_{k-250..k-1})) (0 low turnover, 2 high).  ZA_k = |R_k| / sig_{k-1}.
 4a  volume-|return|: Spearman rho(TZ_k, ZA_k) (rank Pearson on within-cell ranks, bootstrap) overall and within cells of IL_{k-1}
     and TO_{k-1} (3 + 3), tests rho = 0 (7 tests) and hi-minus-lo difference for IL and TO (2 tests).  Reliability = rho, R2 of OLS
     ZA~TZ and their bootstrap CIs per cell.
 4b  price impact: Spearman(ln A_k, TZ_k) overall, EARLY, POST (3 tests).
 4c  volume-conditioned autocorrelation: R_k = a + b R_{k-1} + c R_{k-1}*TZ_{k-1} and with ILZ_{k-1}; HAC 5; test c = 0 (2 tests).
 4d  walk-forward (as Part 1b, OOS from k = 500): ZA_k on TZ_{k-1} and on ILZ_{k-1}, CW vs expanding mean (2 tests).
 Status: 4a-4c descriptive_only (association, not mechanism); 4d via the Part 1b rule.

PART 5  REGIMES (rules fixed here)  (family P5_calib)
 At close k:  mu20_k = lc_k - lc_{k-20};  tau_k = |mu20_k| / (sig_k*sqrt(20));  pv_k = expanding percentile rank of vol20_k among
 {vol20_j, j<=k} (valid with >=250 obs);  ndd_k = Nifty_k / max(Nifty over 250 index sessions, min 120) - 1;  VIX_k = India VIX
 close;  shock_k = [|R_k| >= 8%] or [|R_k - beta_k*Nifty_k| >= 3*rsd_k] with beta_k the 120-session rolling cov/var of (R, Nifty
 return) lagged one session and rsd_k the 60-session rolling SD of the residual lagged one session (exactly v1 E4a U E4b);
 ev_k = any shock in k-4..k.
   stressed  if ndd_k <= -10%  OR  VIX_k >= 25  OR (pv_k >= 0.90 AND mu20_k < 0)
   else event_driven  if ev_k
   else trending  if tau_k >= 1.0
   else calm  (residual; its share of high-vol sessions is reported).
 Thresholds -10%, VIX 25 and the 8% / 3-sd shock come from the v1 pre-registration; 0.90, 5-session window and tau >= 1.0 are new.
 Tabulation (session k+1 given regime at close k): n, spells, mean/median/SD R, mean |R|, mean/SD G, mean/SD I, mean range rho, P(R>0)
 (Wilson CI), R quantiles, SD of R/sig.
 Calibration: forecasts_R.csv models S6 (the frozen record's R model) and S0 (benchmark); session date k, regime at close k-1; coverage of
 central 50/80/90/95% intervals ([q.25,q.75], [q.10,q.90], [q.05,q.95], [q.025,q.975]) per regime, Kupiec POF LR test vs the
 nominal level (cells with n >= 20); tail balance P(y<q.05), P(y>q.95); mean pinball loss S6/S0.  2 models x 4 regimes x 4 levels = 32
 tests (family P5_calib).  STATUS: coverage rejected at family-Holm p < 0.05 -> "contradicted" (claim: intervals calibrated in this
 regime); otherwise descriptive_only (non-rejection is not proof).  forecasts_R.csv ends 2026-10-12: the 2026-10-13 outcome is not scored.

PART 6  CURRENT REGIME AS OF THE 2026-10-13 CLOSE  (family P6_current)
 Compute RG, PV, PN, PD, breakout flags, RV/TZ, ILZ and the momentum signals at k = N-1.  Historical next-day outcomes in the
 current RG class vs all sessions with a valid class: n, spells, mean/median/SD of R, P(R>0), mean |R|, quantiles; tests (4): difference
 in mean R, in SD (log ratio of SD), in P(R>0), in mean |R|, stationary-bootstrap Wald.  The index row for 2026-10-13 is copied
 from src/behaviour/linkages.py (NSE file published 19:50 IST, before the cutoff; not re-verified here).  A sensitivity run uses the
 2026-10-12 index state.

MULTIPLE TESTING.  REG collects (family, id, p).  Holm and BH are computed within family and over the whole registry.  A claim is
 called "supported" here only if its WHOLE-REGISTRY Holm-adjusted p < 0.05; family-level Holm p < 0.05 is called "supported within
 family"; BH q < 0.10 over the whole registry is called "FDR-suggestive".  n_tests, skipped tests and reasons are listed in the JSON.

AMENDMENTS (each entry states whether BSE outcomes had been seen when it was made):
 A1 (made while writing the code body, BEFORE any real run; no BSE outcome of this workstream seen): the EARLY-period (k>=60, date <
    2024-07-01) permutation cell statistics are also computed, descriptively and NOT registered, because the status rule for the
    "early-period gap rule" needs the EARLY sign of (c - pi0).  The sup-Wald wild bootstrap uses B = 1999 (p floored at 0.0005).
    Self-tests on simulated data (--selftest) were run before the real run; they touch no BSE data.
 A2 (made AFTER the first real run, whose script SHA-256 was c6dde21a99abe299d6f1b7b3dc0da00ef4378b5b731d031fdc6af85b2cb395ff, but BEFORE any
    breakout return, excess or p-value had been looked at; only cell counts had been printed): the pre-registered relative-volume and delivery
    terciles of the ALL-DAY distribution are degenerate for breakouts (up-breakouts: RV terciles lo/mid/hi = 1/20/129 of 150; delivery terciles
    lo/mid/hi = 108/17/4 of 129), so the high-minus-low contrast cannot be estimated.  Added: terciles among breakouts of the same direction with
    cut points fixed from the Dev-period (date < 2024-07-01) breakouts of that direction ("RVb", "DPb"; 2 dir x 3 h x (3 + 1 contrast) x 2 = 48
    tests, family P3_breakout together with the 6 scheme-0 tests = 54), and a holdout cell "RVbhi" (top within-breakout RV tercile, Dev cut
    points).  The original all-day-tercile tests (RV, DP, holdout RVhi) are KEPT, counted in the whole-registry adjustment, and reported in
    families P3_alldayterc / P3_holdout_alldayterc so they cannot be silently dropped.  Family P3_holdout = 'all' + 'RVbhi' cells (12 tests).
 A3 (made AFTER seeing the results of all registered tests, i.e. POST-HOC and exploratory; motivated by (i) the positive lag-1 autocorrelation of
    R and the weak-but-nominally-significant 1-day walk-forward skill that fails the Final-period gate, (ii) the Fisher flip test comparing raw
    continuation rates although the unconditional intraday drift also shifts between periods, (iii) the current regime being "stressed" through the
    Nifty-drawdown prong only, (iv) the close being a 30-min VWAP before 2026-08-03).  Function posthoc() adds, none of which changes a
    registered test: X1 lag-1 autocorrelation of R by era and calendar year, with Nifty-50 for context; X2 decomposition of the lag-1 autocovariance
    into G/I cross terms and the open-to-open autocorrelation (a VWAP-staleness diagnostic); X3 drift-adjusted flip = (c - pi0)_L1 - (c - pi0)_EARLY for
    up_ML, down_ML, pooled_ML (3 tests, family X_posthoc, counted in the whole-registry adjustment); X4 walk-forward OOS R2 by calendar year for the
    1-day signal and for the |R|/sigma ~ TZ model; X5 relative volume on breakout days; X6 the stressed class split into "Nifty-drawdown prong only"
    vs "other stress" (next-day outcomes and S6 90% coverage / kappa); X7 balance of the expanding vol terciles; X8 where BSE results-reaction
    days fall in the regime classification; X9 empirical frequency of the v1 'broadly unchanged' event |R| < 0.25*sigma_S6 by regime (Wilson CI)
    versus the 0.238 stated in the frozen record.  Only X3 carries p-values; everything else is descriptive with bootstrap intervals and no
    claim of significance.
 A4 (disclosure, no code or test change): the scratchpad contained an earlier attempt at this workstream (pattern_tests.py and patterns.json,
    file times 2026-10-13 16:56-16:57 UTC).  It was discovered when the scratchpad was listed after the first real run; only names and sizes were
    viewed until the registered and post-hoc results were final, after which I opened its header and its lag-1 autocorrelation table as a bug cross-check only (lag-1
    ACF all 0.104 on n=2079 from 2018-05 vs 0.105 on n=2387 here; Nifty below/above 200d 0.125/0.095 vs 0.124/0.097; deep drawdown 0.151 vs 0.162).
    Nothing was taken from it; agreement of two runs on the same data and the same v1 peeking is not independent confirmation.
 (amendments after the first real run are appended below, with the reason and whether outcomes were seen)
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from common import index_returns, load_bse, load_index, targets  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
OUT_JSON = ROOT / "results/behaviour/patterns.json"
SEED = 20261014
B_BOOT = 2000
BLOCK = 10
CUTOFF = pd.Timestamp("2026-10-13")
POST_START = pd.Timestamp("2024-07-01")
AUC_START = pd.Timestamp("2026-08-03")
FINAL_START = pd.Timestamp("2025-07-01")
OOS_START = 500
MIN_CELL_TRAIN = 100

# 2026-10-13 index row copied from src/behaviour/linkages.py (NSE ind_close_all_13102026.csv, Last-Modified 2026-10-13 14:20:38 GMT
# = 19:50 IST, before the 22:00 IST cutoff).  Not re-verified by this workstream (no fetching allowed / needed).
IDX_20261013 = {"nifty50": (22364.15, 22721.95), "next50": (68182.15, 68927.95), "nifty500": (21818.9, 22090.0),
                "midcap100": (58845.3, 59459.2), "smallcap100": (19429.5, 19447.4), "bank": (54907.55, 55481.05),
                "finserv": (24834.75, 25228.55), "vix": (15.2525, 14.12), "capmkts": (5259.65, 5285.75)}


# ----------------------------------------------------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------------------------------------------------
def holm(p):
    p = np.asarray(p, float); out = np.full(len(p), np.nan); ok = np.isfinite(p); m = ok.sum()
    if m == 0:
        return out
    o = np.argsort(p[ok]); adj = np.maximum.accumulate((m - np.arange(m)) * p[ok][o]); adj = np.minimum(adj, 1.0)
    tmp = np.empty(m); tmp[o] = adj; out[ok] = tmp
    return out


def bh(p):
    p = np.asarray(p, float); out = np.full(len(p), np.nan); ok = np.isfinite(p); m = ok.sum()
    if m == 0:
        return out
    o = np.argsort(p[ok]); ranked = p[ok][o] * m / (np.arange(m) + 1.0)
    adj = np.minimum(np.minimum.accumulate(ranked[::-1])[::-1], 1.0)
    tmp = np.empty(m); tmp[o] = adj; out[ok] = tmp
    return out


class Registry:
    """One row per hypothesis test: (family, id, label, raw p).  Adjusted p-values are attached by finalize()."""

    def __init__(self):
        self.rows: list[dict] = []
        self.skipped: list[dict] = []

    def add(self, family, tid, label, p, stat=None, n=None, note=None):
        if p is None or not np.isfinite(p):
            self.skipped.append({"family": family, "id": tid, "label": label, "reason": "p not finite"})
            return
        self.rows.append({"family": family, "id": tid, "label": label, "p": float(p), "stat": None if stat is None else float(stat),
                          "n": None if n is None else int(n), "note": note})

    def skip(self, family, tid, label, reason):
        self.skipped.append({"family": family, "id": tid, "label": label, "reason": reason})

    def finalize(self):
        df = pd.DataFrame(self.rows)
        df["holm_global"] = holm(df["p"].values); df["bh_global"] = bh(df["p"].values)
        df["holm_family"] = np.nan; df["bh_family"] = np.nan
        for fam, g in df.groupby("family"):
            df.loc[g.index, "holm_family"] = holm(g["p"].values); df.loc[g.index, "bh_family"] = bh(g["p"].values)
        self.df = df.set_index("id")
        return self.df

    def adj(self, tid):
        if tid not in self.df.index:
            return None
        r = self.df.loc[tid]
        return {"p_raw": float(r["p"]), "holm_family": float(r["holm_family"]), "bh_family": float(r["bh_family"]),
                "holm_global": float(r["holm_global"]), "bh_global": float(r["bh_global"])}


def z_p(z):
    return float(2 * stats.norm.sf(abs(z))) if np.isfinite(z) else np.nan


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(c - h), float(c + h))


_IDX_CACHE: dict = {}


def sb_idx(n, B=B_BOOT, block=BLOCK, seed=SEED):
    """Stationary-bootstrap index matrix (Politis-Romano), shape (B, n)."""
    key = (n, B, block, seed)
    if key not in _IDX_CACHE:
        rng = np.random.default_rng(seed + n)
        idx = np.empty((B, n), dtype=np.int32)
        idx[:, 0] = rng.integers(0, n, B)
        new = rng.random((B, n)) < 1.0 / block; starts = rng.integers(0, n, (B, n))
        for i in range(1, n):
            idx[:, i] = np.where(new[:, i], starts[:, i], (idx[:, i - 1] + 1) % n)
        _IDX_CACHE[key] = idx
    return _IDX_CACHE[key]


def boot_wald(est, bs, null=0.0):
    bs = np.asarray(bs, float); bs = bs[np.isfinite(bs)]
    if not np.isfinite(est) or len(bs) < 100:
        return {"est": _f(est), "se": None, "z": None, "p": None, "ci95": [None, None]}
    se = float(bs.std(ddof=1)); z = (est - null) / se if se > 0 else np.nan
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"est": _f(est), "se": _f(se), "z": _f(z), "p": _f(z_p(z)), "ci95": [_f(lo), _f(hi)]}


def _f(x, nd=6):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if np.isfinite(x) else None


def hac_mean_var(f, L):
    f = np.asarray(f, float); n = len(f); fc = f - f.mean(); s = fc @ fc / n
    for l in range(1, min(L, n - 1) + 1):
        s += 2 * (1 - l / (L + 1)) * (fc[l:] @ fc[:-l]) / n
    return s / n


def ols_hac(y, X, L):
    y = np.asarray(y, float); X = np.asarray(X, float); n, k = X.shape
    XtXi = np.linalg.pinv(X.T @ X); b = XtXi @ X.T @ y; e = y - X @ b
    U = X * e[:, None]; S = U.T @ U
    for l in range(1, min(L, n - 1) + 1):
        G = U[l:].T @ U[:-l]; S += (1 - l / (L + 1)) * (G + G.T)
    V = XtXi @ S @ XtXi * n / max(n - k, 1)
    s2 = e @ e / max(n - k, 1); V_iid = XtXi * s2
    return b, V, V_iid, e


def contrast(b, V, c):
    c = np.asarray(c, float); est = float(c @ b); se = float(np.sqrt(max(c @ V @ c, 0.0)))
    z = est / se if se > 0 else np.nan
    return est, se, z


def cw_stats(y, yb, ym, L=5):
    y, yb, ym = (np.asarray(a, float) for a in (y, yb, ym)); eb = y - yb; em = y - ym
    f = eb ** 2 - (em ** 2 - (yb - ym) ** 2); var = hac_mean_var(f, L)
    t = f.mean() / np.sqrt(var) if var > 0 else np.nan
    return {"n": int(len(y)), "r2": _f(1 - (em ** 2).sum() / (eb ** 2).sum()), "cw_t": _f(t), "cw_p_one_sided": _f(stats.norm.sf(t)) if np.isfinite(t) else None}


def pt_test(sx, sy):
    """Pesaran-Timmermann (1992) sign-association test; sx, sy are +-1 arrays.  Returns agreement rate, benchmark P*, z, two-sided p."""
    n = len(sx); p_hat = np.mean(sx == sy); py = np.mean(sy > 0); px = np.mean(sx > 0); ps = py * px + (1 - py) * (1 - px)
    v_hat = ps * (1 - ps) / n
    v_star = ((2 * py - 1) ** 2 * px * (1 - px) + (2 * px - 1) ** 2 * py * (1 - py)) / n + 4 * py * px * (1 - py) * (1 - px) / n ** 2
    den = v_hat - v_star
    z = (p_hat - ps) / np.sqrt(den) if den > 0 else np.nan
    return {"n": int(n), "agree": _f(p_hat), "benchmark_Pstar": _f(ps), "z": _f(z), "p_two_sided": _f(z_p(z)), "P_x_up": _f(px), "P_y_up": _f(py)}


def kupiec(x, n, p_miss):
    if n == 0:
        return np.nan, np.nan
    ph = x / n
    def ll(q):
        a = (n - x) * np.log(1 - q) if (n - x) > 0 else 0.0
        b = x * np.log(q) if x > 0 else 0.0
        return a + b
    lr = -2 * (ll(p_miss) - ll(ph)); return float(lr), float(stats.chi2.sf(lr, 1))


def expanding_terciles(x, min_obs=250):
    x = np.asarray(x, float); st = np.full(len(x), -1, dtype=int); ok = np.isfinite(x)
    for k in range(len(x)):
        if not ok[k]:
            continue
        h = x[: k + 1][ok[: k + 1]]
        if len(h) < min_obs:
            continue
        q1, q2 = np.quantile(h, [1 / 3, 2 / 3]); st[k] = 0 if x[k] <= q1 else (2 if x[k] > q2 else 1)
    return st


def expanding_pct_rank(x, min_obs=250):
    x = np.asarray(x, float); pr = np.full(len(x), np.nan); ok = np.isfinite(x)
    for k in range(len(x)):
        if not ok[k]:
            continue
        h = x[: k + 1][ok[: k + 1]]
        if len(h) >= min_obs:
            pr[k] = np.mean(h <= x[k])
    return pr


def runs(mask):
    """number of maximal runs of True in a boolean array"""
    m = np.asarray(mask, bool); return int((m & ~np.r_[False, m[:-1]]).sum())


def nclusters(flag_idx, h):
    """flagged session indices (sorted) -> number of clusters where consecutive flags within h sessions merge"""
    if len(flag_idx) == 0:
        return 0
    return int(1 + (np.diff(np.sort(flag_idx)) > h).sum())


PART_LABELS = {"PV": ["lo", "mid", "hi"], "PN": ["below", "above"], "PD": ["near_high", "pullback", "deep"],
               "RG": ["calm", "trending", "event_driven", "stressed"]}


# ----------------------------------------------------------------------------------------------------------------------
# data + state variables (everything "at close k" uses sessions <= k)
# ----------------------------------------------------------------------------------------------------------------------
def build():
    d = load_bse(); t = targets(d); N = len(d); dates = d.index
    assert dates.max() <= CUTOFF, "post-cutoff session present"
    ix = load_index(); assert ix.index.max() < CUTOFF
    row = {f"{k}_close": c for k, (o, c) in IDX_20261013.items()}
    ix = pd.concat([ix, pd.DataFrame([row], index=[CUTOFF])]).sort_index()
    ix = ix[~ix.index.duplicated(keep="last")]
    R = t["R"].values.astype(float); G = t["G"].values.astype(float); I = t["I"].values.astype(float)
    lc = np.cumsum(R); lcx = np.r_[0.0, lc]
    lh = lcx[:-1] + t["Hp"].values; ll = lcx[:-1] + t["Lp"].values
    nif = ix["nifty50_close"]; nif_b = nif.reindex(dates); assert nif_b.notna().all(), "index misaligned"
    vix_b = ix["vix_close"].reindex(dates); assert vix_b.notna().all()
    sma200 = nif.rolling(200, min_periods=200).mean().reindex(dates).values
    ndd = (nif / nif.rolling(250, min_periods=120).max() - 1).reindex(dates).values
    nr = np.log(nif_b).diff()
    Rs = pd.Series(R, index=dates)
    sig = np.sqrt((Rs ** 2).rolling(60).mean().values)          # RMS60 at close k
    vol20 = np.sqrt((Rs ** 2).rolling(20).mean().values)
    sig_prev = np.r_[np.nan, sig[:-1]]                            # sigma known when session k opens
    PV = expanding_terciles(sig, 250)
    PN = np.where(np.isfinite(sma200), (nif_b.values > sma200).astype(int), -1)
    dd = np.exp(lc - pd.Series(lc).rolling(250, min_periods=120).max().values) - 1
    PD = np.where(~np.isfinite(dd), -1, np.where(dd > -0.10, 0, np.where(dd > -0.20, 1, 2)))
    mu20 = lc - np.r_[np.full(20, np.nan), lc[:-20]]
    tau = np.abs(mu20) / (sig * np.sqrt(20))
    pv = expanding_pct_rank(vol20, 250)
    vix = vix_b.values
    beta = (Rs.rolling(120).cov(nr) / nr.rolling(120).var()).shift(1)
    resid = Rs - beta * nr; rsd = resid.rolling(60).std().shift(1)
    shock = ((Rs.abs() >= 0.08) | (resid.abs() >= 3 * rsd)).fillna(False).values
    ev = pd.Series(shock.astype(float)).rolling(5, min_periods=1).max().values > 0
    stressed = (ndd <= -0.10) | (vix >= 25) | ((pv >= 0.90) & (mu20 < 0))
    valid = np.isfinite(pv) & np.isfinite(ndd) & np.isfinite(vix) & np.isfinite(tau)
    RG = np.full(N, -1); RG[valid] = np.where(stressed, 3, np.where(ev, 2, np.where(tau >= 1.0, 1, 0)))[valid]
    # liquidity
    T = d["turnover_cr"].values.astype(float); LT = pd.Series(np.log(T))
    TZ = ((LT - LT.rolling(60).mean().shift(1)) / LT.rolling(60).std().shift(1)).clip(-3, 3).values
    A = 100 * np.abs(R) / T; LA = np.log(pd.Series(A).rolling(20).mean())
    ILZ = ((LA - LA.rolling(250, min_periods=120).mean().shift(1)) / LA.rolling(250, min_periods=120).std().shift(1)).clip(-3, 3).values
    IL = expanding_terciles(LA.values, 250)
    Ts = pd.Series(T); TOL = np.log(Ts.rolling(20).mean() / Ts.rolling(250, min_periods=120).median().shift(1)).values
    TO = expanding_terciles(TOL, 250)
    RV = (Ts / Ts.rolling(20).mean().shift(1)).values; RVs = expanding_terciles(RV, 250)
    DP = d["deliv_pct"].values.astype(float); DPs = expanding_terciles(DP, 250)
    ZA = np.abs(R) / sig_prev
    # breakouts
    hmax = pd.Series(lh).rolling(20).max().shift(1).values; lmin = pd.Series(ll).rolling(20).min().shift(1).values
    Bup = np.isfinite(hmax) & (lc > hmax); Bdn = np.isfinite(lmin) & (lc < lmin)
    # momentum signals known at close k
    m = {}
    for h in (1, 5, 20, 60):
        v = np.full(N, np.nan); v[h - 1:] = lcx[h:][: N - h + 1] - lcx[: N - h + 1]
        m[f"m{h}"] = v
    return dict(d=d, t=t, N=N, dates=dates, R=R, G=G, I=I, lc=lc, lcx=lcx, lh=lh, ll=ll, sig=sig, sig_prev=sig_prev, vol20=vol20,
                PV=PV, PN=PN, PD=PD, RG=RG, dd=dd, mu20=mu20, tau=tau, pv=pv, ndd=ndd, vix=vix, shock=shock, ev=ev, stressed=stressed,
                nif=nif_b.values, sma200=sma200, T=T, TZ=TZ, A=A, LA=LA.values, ILZ=ILZ, IL=IL, TO=TO, RV=RV, RVs=RVs, DP=DP, DPs=DPs,
                ZA=ZA, Bup=Bup, Bdn=Bdn, m=m, rho=t["rho"].values.astype(float), hmax=hmax, lmin=lmin)


def lagstate(S):
    """state applicable to session k = state at close k-1 (length N); first element -1"""
    return np.r_[-1, np.asarray(S)[:-1]].astype(int)


# ----------------------------------------------------------------------------------------------------------------------
# PART 1a: lag-1 autocorrelation and variance ratios by ex-ante regime
# ----------------------------------------------------------------------------------------------------------------------
def part1_acf_vr(D, reg):
    R = D["R"]; N = D["N"]; Rc = R - R.mean()
    cells = [("all", None, None)] + [(f"{p}:{lab}", p, c) for p in ("PV", "PN", "PD") for c, lab in enumerate(PART_LABELS[p])]
    diffs = [("PV", 2, 0), ("PN", 1, 0), ("PD", 0, 2)]      # (partition, code A, code B): A minus B
    out = {"acf": {}, "vr": {}, "acf_diff": {}, "vr_diff": {}}
    # ---- lag-1
    n1 = N - 1; ib = sb_idx(n1)
    prod = Rc[1:] * Rc[:-1]; s0 = Rc[1:] ** 2; s1 = Rc[:-1] ** 2
    pb, s0b, s1b = prod[ib], s0[ib], s1[ib]
    def mask1(p, c):
        return np.ones(n1, bool) if p is None else (D[p][:n1] == c)
    def rho_stat(m, boot):
        if boot:
            M = m[ib]; return (pb * M).sum(1) / np.sqrt((s0b * M).sum(1) * (s1b * M).sum(1))
        return (prod[m]).sum() / np.sqrt(s0[m].sum() * s1[m].sum())
    cache = {}
    for name, p, c in cells:
        m = mask1(p, c); est = rho_stat(m, False); bs = rho_stat(m, True); cache[(p, c)] = (est, bs, m)
        r = boot_wald(est, bs, 0.0); r["n"] = int(m.sum()); r["analytic_se_iid"] = _f(1 / np.sqrt(m.sum()))
        out["acf"][name] = r; reg.add("P1_acf", f"acf:{name}", f"lag-1 autocorr of R, cell {name}", r["p"], r["z"], m.sum())
    for p, a, b in diffs:
        ea, ba, ma = cache[(p, a)]; eb_, bb, mb = cache[(p, b)]
        r = boot_wald(ea - eb_, ba - bb, 0.0); r["n_A"] = int(ma.sum()); r["n_B"] = int(mb.sum()); r["A"] = PART_LABELS[p][a]; r["B"] = PART_LABELS[p][b]
        out["acf_diff"][p] = r; reg.add("P1_acf", f"acfdiff:{p}", f"lag-1 autocorr difference {r['A']} minus {r['B']} ({p})", r["p"], r["z"], ma.sum() + mb.sum())
    # ---- variance ratios
    Cs = np.cumsum(np.r_[0.0, Rc]); Cq = np.cumsum(np.r_[0.0, Rc ** 2])
    for q in (5, 20):
        nq = N - q; k = np.arange(1, N - q + 1)
        S2 = (Cs[k + q] - Cs[k]) ** 2; Q = Cq[k + q] - Cq[k]
        ibq = sb_idx(nq); S2b, Qb = S2[ibq], Q[ibq]; cacheq = {}
        def vr_stat(m, boot):
            if boot:
                M = m[ibq]; return (S2b * M).sum(1) / (Qb * M).sum(1)
            return S2[m].sum() / Q[m].sum()
        for name, p, c in cells:
            m = np.ones(nq, bool) if p is None else (D[p][:nq] == c)   # window start k, state at close k-1 == D[p][k-1]; index k-1 = 0..nq-1
            est = vr_stat(m, False); bs = vr_stat(m, True); cacheq[(p, c)] = (est, bs, m)
            r = boot_wald(est, bs, 1.0); r["n_windows"] = int(m.sum()); r["n_eff_nonoverlap"] = int(m.sum() // q)
            out["vr"].setdefault(f"q{q}", {})[name] = r
            reg.add("P1_vr", f"vr{q}:{name}", f"VR({q}) cell {name}", r["p"], r["z"], m.sum())
        for p, a, b in diffs:
            ea, ba, ma = cacheq[(p, a)]; eb_, bb, mb = cacheq[(p, b)]
            r = boot_wald(ea - eb_, ba - bb, 0.0); r["A"] = PART_LABELS[p][a]; r["B"] = PART_LABELS[p][b]
            out["vr_diff"].setdefault(f"q{q}", {})[p] = r
            reg.add("P1_vr", f"vrdiff{q}:{p}", f"VR({q}) difference {r['A']} minus {r['B']} ({p})", r["p"], r["z"], ma.sum() + mb.sum())
    return out


# ----------------------------------------------------------------------------------------------------------------------
# PART 1b / 4d: walk-forward predictive regressions vs the expanding mean (+ regime-conditional versions)
# ----------------------------------------------------------------------------------------------------------------------
def wf_predict(y, X, st=None, min_cell=MIN_CELL_TRAIN, min_train=30):
    """y, X length M (M = N or N+1; y may be NaN at the end).  X[j] = signal available for session j.  st[j] = state applicable to
    session j (state at close j-1), -1 = undefined.  Returns benchmark (expanding mean), unconditional OLS forecast and (if st) the
    regime-conditional OLS forecast, each for every session k using ONLY pairs j<k."""
    M = len(y); fin_y = np.isfinite(y)
    yb = np.full(M, np.nan); cy = np.cumsum(np.where(fin_y, y, 0.0)); cn = np.cumsum(fin_y.astype(float))
    yb[1:] = cy[:-1] / np.maximum(cn[:-1], 1)
    w = fin_y & np.isfinite(X); xx = np.where(w, X, 0.0); yy = np.where(w, y, 0.0)
    def fit(wm):
        n = np.r_[0.0, np.cumsum(wm.astype(float))[:-1]]; Sx = np.r_[0.0, np.cumsum(np.where(wm, xx, 0.0))[:-1]]
        Sy = np.r_[0.0, np.cumsum(np.where(wm, yy, 0.0))[:-1]]; Sxx = np.r_[0.0, np.cumsum(np.where(wm, xx * xx, 0.0))[:-1]]
        Sxy = np.r_[0.0, np.cumsum(np.where(wm, xx * yy, 0.0))[:-1]]
        den = n * Sxx - Sx ** 2; b = np.where(den > 1e-18, (n * Sxy - Sx * Sy) / np.where(den > 1e-18, den, 1), np.nan)
        a = (Sy - b * Sx) / np.maximum(n, 1)
        return n, a, b
    n, a, b = fit(w); yU = np.where((n >= min_train) & np.isfinite(X), a + b * np.nan_to_num(X), np.nan)
    out = {"yb": yb, "yU": yU}
    if st is not None:
        yRC = yb.copy(); ncell = np.zeros(M)
        for c in np.unique(st[st >= 0]):
            nc, ac, bc = fit(w & (st == c)); sel = (st == c) & (nc >= min_cell) & np.isfinite(bc) & np.isfinite(X)
            yRC[sel] = (ac + bc * np.nan_to_num(X))[sel]; ncell[st == c] = nc[st == c]
        out["yRC"] = yRC; out["ncell"] = ncell
    return out


def r2_of(y, yb, ym):
    return 1 - np.sum((y - ym) ** 2) / np.sum((y - yb) ** 2)


def wf_eval(y, yb, ym, dates, k0=OOS_START, st=None):
    """pooled + split statistics on sessions k0..N-1 (N = len(dates)); ym may be NaN where undefined (then excluded for all)"""
    N = len(dates); ks = np.arange(k0, N); ok = np.isfinite(y[ks]) & np.isfinite(yb[ks]) & np.isfinite(ym[ks]); ks = ks[ok]
    yy, b_, m_ = y[ks], yb[ks], ym[ks]; res = cw_stats(yy, b_, m_)
    half = len(ks) // 2; res["r2_first_half"] = _f(r2_of(yy[:half], b_[:half], m_[:half])); res["r2_second_half"] = _f(r2_of(yy[half:], b_[half:], m_[half:]))
    fin = dates[ks] >= FINAL_START; res["r2_final_2025_07_plus"] = _f(r2_of(yy[fin], b_[fin], m_[fin])); res["n_final"] = int(fin.sum())
    keep = np.ones(len(ks), bool); keep[np.argsort(-np.abs(yy))[:5]] = False
    res["r2_ex_top5_abs"] = _f(r2_of(yy[keep], b_[keep], m_[keep]))
    res["oos_start"] = str(dates[ks[0]].date()); res["oos_end"] = str(dates[ks[-1]].date())
    if st is not None:
        cells = {}
        for c in np.unique(st[ks][st[ks] >= 0]):
            s = st[ks] == c; cells[int(c)] = {"n": int(s.sum()), "r2": _f(r2_of(yy[s], b_[s], m_[s])), "sd_y_pct": _f(100 * yy[s].std())}
        res["cells"] = cells
    return res


def part1_wf(D, reg):
    N = D["N"]; dates = D["dates"]; R = D["R"]
    yext = np.r_[R, np.nan]
    S = {"PV": lagstate(D["PV"]), "PN": lagstate(D["PN"]), "PD": lagstate(D["PD"])}
    Sx = {p: np.r_[s, D[p][-1]] for p, s in S.items()}      # state applicable to the (not yet realised) session N = state at close N-1
    out = {"models": {}, "pt": {}, "next_session_forecast_pct": {}}
    for sname in ("m1", "m5", "m20", "m60"):
        xs = np.r_[np.nan, D["m"][sname]]                     # X[j] = signal at close j-1, length N+1
        # fits: U and RC for each partition
        for mname, st in (("U", None), ("RC_PV", Sx["PV"]), ("RC_PN", Sx["PN"]), ("RC_PD", Sx["PD"])):
            w = wf_predict(yext, xs, st)
            ym = w["yU"] if st is None else w["yRC"]
            res = wf_eval(R, w["yb"][:N], ym[:N], dates, st=None if st is None else st[:N])
            if st is not None:
                labs = PART_LABELS[mname[3:]]; res["cells"] = {labs[int(c)]: v for c, v in res["cells"].items()}
            tid = f"wf:{sname}:{mname}"
            res["next_session_pred_pct"] = _f(100 * ym[N]); res["bench_next_pred_pct"] = _f(100 * w["yb"][N]); res["signal_now"] = _f(xs[N])
            out["models"][tid] = res
            reg.add("P1_wf", tid, f"walk-forward {sname} {mname} vs expanding mean (CW)", res["cw_p_one_sided"], res["cw_t"], res["n"])
        # Pesaran-Timmermann on the OOS sessions
        ks = np.arange(OOS_START, N); x = xs[ks]; y = R[ks]; ok = np.isfinite(x) & (x != 0) & (y != 0)
        r = pt_test(np.sign(x[ok]), np.sign(y[ok])); out["pt"][sname] = r
        reg.add("P1_wf", f"pt:{sname}", f"Pesaran-Timmermann sign(m) vs sign(R), {sname}", r["p_two_sided"], r["z"], r["n"])
    return out


# ----------------------------------------------------------------------------------------------------------------------
# PART 2: opening-gap continuation vs reversal
# ----------------------------------------------------------------------------------------------------------------------
def gap_masks(gz, G, I):
    ok = np.isfinite(gz) & (np.abs(gz) >= 0.25) & (I != 0) & (G != 0); a = np.abs(gz); up = gz > 0; m = {}
    for dn, dm in (("up", up), ("down", ~up)):
        m[f"{dn}_S"] = ok & dm & (a < 0.5); m[f"{dn}_M"] = ok & dm & (a >= 0.5) & (a < 1.0); m[f"{dn}_L"] = ok & dm & (a >= 1.0); m[f"{dn}_all"] = ok & dm
    m["all"] = ok
    m["up_ML"] = ok & up & (a >= 0.5); m["down_ML"] = ok & ~up & (a >= 0.5); m["pooled_ML"] = ok & (a >= 0.5)
    return m


def perm_cells(signI, signG, masks, margin=10, min_n=15):
    """Circular-shift permutation of I against G inside one period.  Returns dict cell -> stats (None p when n < min_n)."""
    n = len(signI); shifts = np.arange(margin, n - margin); ind = (np.arange(n)[None, :] + shifts[:, None]) % n
    sI = signI[ind]; Cm = (sI == signG[None, :]); nz = (sI != 0); obsC = (signI == signG).astype(float)
    ib = sb_idx(n); res = {}
    for name, m in masks.items():
        nm = int(m.sum()); r = {"n": nm}
        if nm == 0:
            res[name] = r; continue
        c = float(obsC[m].mean()); M = m[ib]; cb = (obsC[ib] * M).sum(1) / np.maximum(M.sum(1), 1)
        lo, hi = np.percentile(cb[M.sum(1) > 0], [2.5, 97.5]); r.update(c=_f(c), ci95=[_f(lo), _f(hi)], n_cont=int(obsC[m].sum()))
        num = (Cm & nz & m[None, :]).sum(1); den = (nz & m[None, :]).sum(1); rate = num / np.maximum(den, 1)
        pi0 = float(rate.mean()); sd0 = float(rate.std(ddof=1)); p_emp = (1 + np.sum(np.abs(rate - pi0) >= abs(c - pi0) - 1e-12)) / (len(shifts) + 1)
        z = (c - pi0) / sd0 if sd0 > 0 else np.nan; p_z = z_p(z)
        r.update(pi0=_f(pi0), excess=_f(c - pi0), null_sd=_f(sd0), p_emp=_f(p_emp), p_norm=_f(p_z), z=_f(z))
        if nm >= min_n:
            r["p"] = _f(p_emp if nm < 30 else p_z); r["p_rule"] = "empirical shift p" if nm < 30 else "normal approx from shift distribution"
        else:
            r["p"] = None; r["note"] = f"n<{min_n}: not tested"
        res[name] = r
    return res


def part2_gap(D, reg):
    dates = D["dates"]; N = D["N"]; G, I = D["G"], D["I"]; gz = G / D["sig_prev"]; masks = gap_masks(gz, G, I)
    k60 = np.arange(N) >= 60
    periods = {"FULL": k60, "POST": dates >= POST_START, "AUC": dates >= AUC_START}
    out = {"cells": {}, "descriptive": {}, "regime": {}, "flip": {}, "calendar_year": {}, "sigma_unit": {}}
    sg = D["sig"][-1]
    out["sigma_unit"] = {"definition": "sig = RMS of the last 60 R", "sig_at_2026_10_13_close_pct": _f(100 * sg),
                         "gap_thresholds_rupees_from_P0_3375.40": {f"{z}sig_up": _f(3375.40 * (np.exp(z * sg) - 1), 1) for z in (0.25, 0.5, 1.0)}}
    for pn, pm in periods.items():
        pos = np.where(pm)[0]; sI = np.sign(I[pos]).astype(np.int8); sG = np.sign(G[pos]).astype(np.int8)
        mp = {name: m[pos] for name, m in masks.items() if name in ("up_S", "up_M", "up_L", "down_S", "down_M", "down_L", "up_all", "down_all", "all", "pooled_ML", "up_ML", "down_ML")}
        res = perm_cells(sI, sG, mp); out["cells"][pn] = res
        flat = np.isfinite(gz[pos]) & (np.abs(gz[pos]) < 0.25)
        out["descriptive"][pn] = {"n_period": int(len(pos)), "start": str(dates[pos[0]].date()), "end": str(dates[pos[-1]].date()),
                                  "P(I>0)_all_days": _f((I[pos] > 0).mean()), "mean_I_pct": _f(100 * I[pos].mean()), "mean_G_pct": _f(100 * G[pos].mean()),
                                  "flat_gap_n": int(flat.sum()), "flat_gap_P(I>0)": _f((I[pos][flat] > 0).mean()) if flat.any() else None}
        for name, m in mp.items():
            if m.sum():
                sgn = np.sign(G[pos][m]) * I[pos][m]; res[name]["mean_signed_I_pct"] = _f(100 * sgn.mean()); res[name]["median_signed_I_pct"] = _f(100 * np.median(sgn))
        for name in ("up_S", "up_M", "up_L", "down_S", "down_M", "down_L", "up_all", "down_all", "all"):
            r = res[name]
            if r.get("p") is not None:
                reg.add("P2_gap", f"gap:{pn}:{name}", f"continuation rate vs shift-null, {pn} {name}", r["p"], r.get("z"), r["n"])
            else:
                reg.skip("P2_gap", f"gap:{pn}:{name}", f"{pn} {name}", f"n={r['n']}<15")
        if pn == "FULL":
            pass
    # ---- regime x gap (|gz|>=0.5 pooled over directions)
    lag = {"RG": lagstate(D["RG"]), "PV": lagstate(D["PV"]), "PN": lagstate(D["PN"])}
    for pn in ("FULL", "POST", "AUC"):
        pos = np.where(periods[pn])[0]; sI = np.sign(I[pos]).astype(np.int8); sG = np.sign(G[pos]).astype(np.int8); base = masks["pooled_ML"][pos]
        mp = {}
        for part, st in lag.items():
            for c, lab in enumerate(PART_LABELS[part]):
                mp[f"{part}:{lab}"] = base & (st[pos] == c)
        res = perm_cells(sI, sG, mp, min_n=15)
        for name, r in res.items():
            if pn == "AUC":
                r["p"] = None; r["note"] = "AUC period: counts only"
            elif r.get("p") is not None:
                reg.add("P2_gapregime", f"gapreg:{pn}:{name}", f"continuation |gz|>=0.5, {pn}, regime {name}", r["p"], r.get("z"), r["n"])
            elif r["n"] > 0:
                reg.skip("P2_gapregime", f"gapreg:{pn}:{name}", f"{pn} {name}", f"n={r['n']}<15")
        out["regime"][pn] = res
    # ---- calendar-year descriptive table
    yrs = pd.DatetimeIndex(dates).year
    for y_ in sorted(set(yrs)):
        s = (yrs == y_) & k60; r = {}
        for nm, cond in (("up_ML", lambda x: x > 0), ("down_ML", lambda x: x < 0)):
            m = masks[nm] & s
            r[nm] = {"n": int(m.sum()), "continuation": _f(np.mean(cond(I[m]))) if m.sum() else None}
        r["P(I>0)_all"] = _f((I[s] > 0).mean()); r["n_days"] = int(s.sum()); out["calendar_year"][int(y_)] = r
    # ---- FLIP TESTS
    grp = {"EARLY": k60 & (dates < POST_START), "L1": (dates >= POST_START) & (dates < AUC_START), "AUC": dates >= AUC_START}
    Cfull = (np.sign(I) == np.sign(G)).astype(float)
    def rate_boot(g, m):
        pos = np.where(g)[0]; ib = sb_idx(len(pos)); M = m[pos][ib]; c = Cfull[pos][ib]
        return (c * M).sum(1) / np.maximum(M.sum(1), 1)
    out["flip"]["fisher"] = {}
    for cell in ("up_ML", "down_ML", "pooled_ML"):
        for a, b in (("EARLY", "L1"), ("L1", "AUC"), ("EARLY", "AUC")):
            ma, mb = masks[cell] & grp[a], masks[cell] & grp[b]; na, nb = int(ma.sum()), int(mb.sum()); tid = f"flip:{cell}:{a}_vs_{b}"
            r = {"n_A": na, "n_B": nb, "A": a, "B": b}
            if na and nb:
                ka, kb = int(Cfull[ma].sum()), int(Cfull[mb].sum()); r.update(rate_A=_f(ka / na), rate_B=_f(kb / nb))
            if min(na, nb) >= 8:
                tab = [[ka, na - ka], [kb, nb - kb]]; odds, pf = stats.fisher_exact(tab)
                d_b = rate_boot(grp[a], masks[cell]) - rate_boot(grp[b], masks[cell]); lo, hi = np.percentile(d_b[np.isfinite(d_b)], [2.5, 97.5])
                r.update(diff=_f(ka / na - kb / nb), diff_ci95_boot=[_f(lo), _f(hi)], fisher_p=_f(pf))
                reg.add("P2_flip", tid, f"continuation rate {cell}: {a} vs {b} (Fisher)", pf, None, na + nb)
            else:
                reg.skip("P2_flip", tid, f"{cell} {a} vs {b}", f"min(n)={min(na, nb)}<8")
            out["flip"]["fisher"][tid] = r
    # slope interaction
    s = k60 & np.isfinite(G) & np.isfinite(I); L1 = grp["L1"][s].astype(float); AU = grp["AUC"][s].astype(float); g = G[s]
    X = np.column_stack([np.ones(s.sum()), L1, AU, g, g * L1, g * AU]); b, V, Viid, e = ols_hac(I[s], X, 5)
    sl = {}
    sl["slope_EARLY"] = _f(b[3]); sl["slope_L1"] = _f(b[3] + b[4]); sl["slope_AUC"] = _f(b[3] + b[5])
    for nm, cvec in (("slope_L1_minus_EARLY", [0, 0, 0, 0, 1, 0]), ("slope_AUC_minus_L1", [0, 0, 0, 0, -1, 1]),
                     ("slope_EARLY_se", [0, 0, 0, 1, 0, 0])):
        est, se, z = contrast(b, V, cvec); sl[nm] = {"est": _f(est), "se": _f(se), "z": _f(z), "p": _f(z_p(z))}
    sl["se_L1"] = _f(contrast(b, V, [0, 0, 0, 1, 1, 0])[1]); sl["se_AUC"] = _f(contrast(b, V, [0, 0, 0, 1, 0, 1])[1])
    for nm in ("slope_L1_minus_EARLY", "slope_AUC_minus_L1"):
        reg.add("P2_flip", f"flip:{nm}", f"interaction {nm} (I on G, HAC5)", sl[nm]["p"], sl[nm]["z"], int(s.sum()))
    sl["n"] = int(s.sum()); out["flip"]["slope"] = sl
    # sup-Wald, wild bootstrap
    x, y = g, I[s]; F0, s0 = sup_wald(x, y); b0 = np.polyfit(x, y, 1); e0 = y - np.polyval(b0, x); rng = np.random.default_rng(SEED + 7); Fb = np.empty(1999)
    fit0 = np.polyval(b0, x)
    for i in range(len(Fb)):
        Fb[i] = sup_wald(x, fit0 + e0 * rng.choice([-1.0, 1.0], len(x)))[0]
    p_sw = (1 + np.sum(Fb >= F0)) / (len(Fb) + 1)
    out["flip"]["sup_wald"] = {"supF": _f(F0), "break_date": str(dates[s][s0].date()), "p_wild_bootstrap": _f(p_sw), "boot_crit_95": _f(np.percentile(Fb, 95)), "B": len(Fb), "n": int(len(x)),
                               "note": "p floored at 1/(B+1)=0.0005"}
    reg.add("P2_flip", "flip:supwald", "sup-Wald break in I~G (wild bootstrap)", p_sw, F0, len(x))
    return out


def sup_wald(x, y, trim=0.15):
    n = len(x); cs = np.cumsum
    Sx, Sy, Sxx, Sxy, Syy = cs(x), cs(y), cs(x * x), cs(x * y), cs(y * y)
    s = np.arange(int(trim * n), int((1 - trim) * n))
    def rss(m, sx, sy, sxx, sxy, syy):
        xb, yb = sx / m, sy / m; sxxc = sxx - m * xb * xb; sxyc = sxy - m * xb * yb; syyc = syy - m * yb * yb
        return syyc - sxyc ** 2 / sxxc
    m1 = s.astype(float); r1 = rss(m1, Sx[s - 1], Sy[s - 1], Sxx[s - 1], Sxy[s - 1], Syy[s - 1])
    m2 = n - m1; r2 = rss(m2, Sx[-1] - Sx[s - 1], Sy[-1] - Sy[s - 1], Sxx[-1] - Sxx[s - 1], Sxy[-1] - Sxy[s - 1], Syy[-1] - Syy[s - 1])
    r0 = rss(float(n), Sx[-1], Sy[-1], Sxx[-1], Sxy[-1], Syy[-1])
    F = ((r0 - r1 - r2) / 2) / ((r1 + r2) / (n - 4)); j = int(np.nanargmax(F))
    return float(F[j]), int(s[j])


def v1_replication(D):
    """Replicate v1 conditional_day.json numbers with the v1 EWMA(0.94) sigma (verification, not a hypothesis test)."""
    import models as P
    s = P.sigma_ewma(D["R"]); gz = D["G"] / s; I = D["I"]; dates = D["dates"]; ok = np.isfinite(gz)
    v1 = json.loads((ROOT / "results/conditional_day.json").read_text()); out = {}
    for wn, sel in (("full", ok), ("valfinal(2024-07+)", ok & (dates >= POST_START))):
        r = {}
        for lab, cond in (("gap_up_gt_0.5sd", gz > 0.5), ("gap_down_lt_-0.5sd", gz < -0.5), ("gap_up_gt_1sd", gz > 1.0)):
            m = sel & cond; r[lab] = {"n": int(m.sum()), "P(I>0)": _f((I[m] > 0).mean()), "v1_n": v1[wn][lab]["n"], "v1_P(I>0)": _f(v1[wn][lab]["P(I>0)"])}
        r["n_window"] = int(sel.sum()); r["v1_n_window"] = v1[wn]["n"]; out[wn] = r
    out["match"] = all(out[w][l]["n"] == out[w][l]["v1_n"] and abs(out[w][l]["P(I>0)"] - out[w][l]["v1_P(I>0)"]) < 1e-3 for w in ("full", "valfinal(2024-07+)") for l in ("gap_up_gt_0.5sd", "gap_down_lt_-0.5sd", "gap_up_gt_1sd"))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# PART 3: breakouts
# ----------------------------------------------------------------------------------------------------------------------
def _bo_reg(F, rows, dummies, h):
    """OLS of F on const + dummies (list of bool arrays over full index); HAC lag h+5; returns dict with coef/se/V and iid V."""
    X = np.column_stack([np.ones(rows.sum())] + [dm[rows].astype(float) for dm in dummies])
    b, V, Viid, e = ols_hac(F[rows], X, h + 5)
    return b, V, Viid, X


def part3_breakouts(D, reg):
    N = D["N"]; lc = D["lc"]; dates = D["dates"]; Bup, Bdn = D["Bup"], D["Bdn"]; hs = (1, 5, 10)
    Fh = {h: np.r_[lc[h:] - lc[:-h], np.full(h, np.nan)] for h in hs}
    kidx = np.arange(N); out = {"scheme0": {}, "RV": {}, "DP": {}, "contrast": {}, "descriptive": {}, "holdout": {}, "subperiod": {}, "counts": {}}
    out["counts"] = {"n_up_breakout_days": int(Bup.sum()), "n_down_breakout_days": int(Bdn.sum()), "first_valid_k": 20}
    for dirname, B, dsign in (("up", Bup, +1), ("down", Bdn, -1)):
        for h in hs:
            F = Fh[h]; rows = (kidx >= 20) & np.isfinite(F)
            nonbo = rows & ~Bup & ~Bdn; flagged = np.where(rows & B)[0]
            d_ = {"n": int(len(flagged)), "n_clusters": nclusters(flagged, h)}
            if len(flagged):
                d_.update(mean_F_breakout_pct=_f(100 * F[flagged].mean()), median_F_breakout_pct=_f(100 * np.median(F[flagged])),
                          mean_F_all_days_pct=_f(100 * F[rows].mean()), mean_F_nonbreakout_pct=_f(100 * F[nonbo].mean()),
                          share_sign_matches_direction_breakout=_f(np.mean(np.sign(F[flagged]) == dsign)),
                          share_sign_matches_direction_all_days=_f(np.mean(np.sign(F[rows]) == dsign)),
                          share_sign_matches_direction_nonbreakout=_f(np.mean(np.sign(F[nonbo]) == dsign)))
            out["descriptive"][f"{dirname}_h{h}"] = d_
    # scheme 0
    for h in hs:
        F = Fh[h]; rows = (kidx >= 20) & np.isfinite(F); b, V, Viid, X = _bo_reg(F, rows, [Bup, Bdn], h)
        for j, (dirname, B, dsign) in enumerate((("up", Bup, +1), ("down", Bdn, -1)), start=1):
            z = b[j] / np.sqrt(V[j, j]); nB = int((rows & B).sum()); neff = float(np.clip(nB * Viid[j, j] / V[j, j], 1, nB)) if nB else None
            persist = (b[j] * dsign) > 0
            r = {"excess_pct": _f(100 * b[j]), "se_pct": _f(100 * np.sqrt(V[j, j])), "z": _f(z), "p": _f(z_p(z)), "n": nB, "n_clusters": out["descriptive"][f"{dirname}_h{h}"]["n_clusters"],
                 "n_eff_hac": _f(neff, 1), "classification": "persistence" if persist else "reversal",
                 "ci95_pct": [_f(100 * (b[j] - 1.96 * np.sqrt(V[j, j]))), _f(100 * (b[j] + 1.96 * np.sqrt(V[j, j])))]}
            out["scheme0"][f"{dirname}_h{h}"] = r; reg.add("P3_breakout", f"bo0:{dirname}:h{h}", f"breakout {dirname} excess F{h} vs non-breakout days", r["p"], z, nB)
        # sub-period descriptive (not registered)
        for sp, spm in (("EARLY", dates < POST_START), ("POST", dates >= POST_START)):
            rws = rows & spm; bb, VV, VVi, _ = _bo_reg(F, rws, [Bup, Bdn], h)
            out["subperiod"][f"h{h}:{sp}"] = {"up": {"excess_pct": _f(100 * bb[1]), "se_pct": _f(100 * np.sqrt(VV[1, 1])), "n": int((rws & Bup).sum())},
                                              "down": {"excess_pct": _f(100 * bb[2]), "se_pct": _f(100 * np.sqrt(VV[2, 2])), "n": int((rws & Bdn).sum())}}
    # conditioned schemes.  RV / DP = terciles of the ALL-DAY distribution (as pre-registered; found degenerate, see AMENDMENT A2; kept and
    # counted in family P3_alldayterc).  RVb / DPb (AMENDMENT A2) = terciles among breakout days of the same direction, cut points fixed
    # from the Dev-period (date < 2024-07-01) breakouts of that direction (1/3 and 2/3 quantiles) and applied to all events.
    s0 = int(np.searchsorted(dates, POST_START))
    def within_states(B, V):
        st = np.full(N, -1); dev_ev = np.where(B & (kidx < s0) & np.isfinite(V))[0]
        c1, c2 = np.quantile(V[dev_ev], [1 / 3, 2 / 3]); ev_ = np.where(B & np.isfinite(V))[0]
        st[ev_] = np.where(V[ev_] <= c1, 0, np.where(V[ev_] > c2, 2, 1)); return st, {"cut_33": _f(c1, 4), "cut_67": _f(c2, 4), "n_dev_events": int(len(dev_ev)), "n_events_classified": int(len(ev_))}
    stUp_RV, cuUR = within_states(Bup, D["RV"]); stDn_RV, cuDR = within_states(Bdn, D["RV"])
    stUp_DP, cuUD = within_states(Bup, D["DP"]); stDn_DP, cuDD = within_states(Bdn, D["DP"])
    out["within_breakout_cutpoints"] = {"RV_up": cuUR, "RV_down": cuDR, "DP_up": cuUD, "DP_down": cuDD}
    first_dp = int(np.where(np.isfinite(D["DP"]))[0][0]); names = ["lo", "mid", "hi"]
    schemes = [("RV", D["RVs"], D["RVs"], None, "P3_alldayterc", True), ("DP", D["DPs"], D["DPs"], None, "P3_alldayterc", True),
               ("RVb", stUp_RV, stDn_RV, 20, "P3_breakout", False), ("DPb", stUp_DP, stDn_DP, first_dp, "P3_breakout", False)]
    for scheme, Sup, Sdn, kmin, fam, allday in schemes:
        out.setdefault(scheme, {})
        for h in hs:
            F = Fh[h]
            if allday:
                rows = (kidx >= 20) & np.isfinite(F) & (Sup >= 0)
            else:
                rows = (kidx >= kmin) & np.isfinite(F) & ~((Bup & (Sup < 0)) | (Bdn & (Sdn < 0)))
            dums = [Bup & (Sup == c) for c in range(3)] + [Bdn & (Sdn == c) for c in range(3)]
            b, V, Viid, X = _bo_reg(F, rows, dums, h)
            for j, (dirname, dsign) in enumerate([("up", +1)] * 3 + [("down", -1)] * 3, start=1):
                c = (j - 1) % 3; nB = int((rows & dums[j - 1]).sum()); tid = f"bo{scheme}:{dirname}:{names[c]}:h{h}"
                if nB < 5:
                    reg.skip(fam, tid, tid, f"n={nB}<5"); out[scheme][f"{dirname}_{names[c]}_h{h}"] = {"n": nB}; continue
                z = b[j] / np.sqrt(V[j, j]); neff = float(np.clip(nB * Viid[j, j] / V[j, j], 1, nB))
                fl = np.where(rows & dums[j - 1])[0]
                r = {"excess_pct": _f(100 * b[j]), "se_pct": _f(100 * np.sqrt(V[j, j])), "z": _f(z), "p": _f(z_p(z)), "n": nB, "n_clusters": nclusters(fl, h), "n_eff_hac": _f(neff, 1),
                     "classification": "persistence" if (b[j] * dsign) > 0 else "reversal", "mean_F_pct": _f(100 * F[fl].mean()),
                     "share_sign_matches_direction": _f(np.mean(np.sign(F[fl]) == dsign))}
                out[scheme][f"{dirname}_{names[c]}_h{h}"] = r; reg.add(fam, tid, f"breakout {dirname} {scheme}-{names[c]} excess F{h}", r["p"], z, nB)
            for dirname, off in (("up", 0), ("down", 3)):
                cvec = np.zeros(len(b)); cvec[off + 3] = 1; cvec[off + 1] = -1; est, se, z = contrast(b, V, cvec)
                tid = f"boC{scheme}:{dirname}:h{h}"; nlo = int((rows & dums[off]).sum()); nhi = int((rows & dums[off + 2]).sum())
                if min(nlo, nhi) < 5:
                    reg.skip(fam, tid, tid, f"n_lo={nlo} n_hi={nhi}"); continue
                out["contrast"][tid] = {"hi_minus_lo_pct": _f(100 * est), "se_pct": _f(100 * se), "z": _f(z), "p": _f(z_p(z)), "n_lo": nlo, "n_hi": nhi}
                reg.add(fam, tid, f"breakout {dirname} high minus low {scheme} tercile, F{h}", z_p(z), z, nlo + nhi)
    # ---- chronological holdout with fixed rules (Dev = events with k+h < index of 2024-07-01; Holdout = k >= that index)
    for dirname, B, O, dsign, stRV in (("up", Bup, Bdn, +1, stUp_RV), ("down", Bdn, Bup, -1, stDn_RV)):
        for h in hs:
            for cell, fam in (("all", "P3_holdout"), ("RVbhi", "P3_holdout"), ("RVhi", "P3_holdout_alldayterc")):
                F = Fh[h]; cd = B if cell == "all" else ((B & (stRV == 2)) if cell == "RVbhi" else (B & (D["RVs"] == 2))); other = (O | (B & ~cd))
                need = (D["RVs"] >= 0) if cell == "RVhi" else np.ones(N, bool)
                dev = (kidx >= 20) & (kidx + h < s0) & np.isfinite(F) & need
                hol = (kidx >= s0) & np.isfinite(F) & need
                tid = f"boH:{dirname}:{cell}:h{h}"; r = {"n_dev": int((dev & cd).sum()), "n_holdout": int((hol & cd).sum())}
                if min(r["n_dev"], r["n_holdout"]) < 5:
                    reg.skip(fam, tid, tid, f"n_dev={r['n_dev']} n_hol={r['n_holdout']}"); out["holdout"][tid] = r; continue
                bd, Vd, _, _ = _bo_reg(F, dev, [cd, other], h); bh_, Vh, Vhi, _ = _bo_reg(F, hol, [cd, other], h)
                zd = bd[1] / np.sqrt(Vd[1, 1]); sgn = np.sign(bd[1]); zh = sgn * bh_[1] / np.sqrt(Vh[1, 1]); p1 = float(stats.norm.sf(zh))
                r.update(dev_excess_pct=_f(100 * bd[1]), dev_se_pct=_f(100 * np.sqrt(Vd[1, 1])), dev_p_two_sided=_f(z_p(zd)), dev_sign=int(sgn),
                         holdout_excess_pct=_f(100 * bh_[1]), holdout_se_pct=_f(100 * np.sqrt(Vh[1, 1])), holdout_z_in_dev_direction=_f(zh), holdout_p_one_sided=_f(p1),
                         holdout_n_eff_hac=_f(float(np.clip(r["n_holdout"] * Vhi[1, 1] / Vh[1, 1], 1, r["n_holdout"])), 1),
                         dev_direction="persistence" if sgn * dsign > 0 else "reversal", family=fam)
                out["holdout"][tid] = r; reg.add(fam, tid, f"holdout {dirname} {cell} F{h}: dev-sign effect", p1, zh, r["n_holdout"])
    return out


def current_breakout_state(D):
    k = D["N"] - 1; lc = D["lc"]
    return {"close_adj_log_vs_prev20_high_pct": _f(100 * (lc[k] - D["hmax"][k])), "close_adj_log_vs_prev20_low_pct": _f(100 * (lc[k] - D["lmin"][k])),
            "up_breakout": bool(D["Bup"][k]), "down_breakout": bool(D["Bdn"][k]), "RV": _f(D["RV"][k]), "RV_tercile_code": int(D["RVs"][k]),
            "delivery_pct_available": bool(np.isfinite(D["DP"][k])), "prev20_high_price_equiv": _f(3375.40 * np.exp(D["hmax"][k] - lc[k]), 2)}


# ----------------------------------------------------------------------------------------------------------------------
# PART 4: liquidity / Amihud
# ----------------------------------------------------------------------------------------------------------------------
def _ranks(v):
    return stats.rankdata(v) if len(v) else v


def spearman_cells(x, y, cellmasks, ib, reg, family, tag, tests=True):
    """cellmasks: dict name -> bool array over the sample.  Within-cell ranks fixed; bootstrap resamples time indices jointly."""
    out = {}; boots = {}
    for name, m in cellmasks.items():
        n = int(m.sum()); r = {"n": n}
        if n < 30:
            out[name] = r; continue
        rx = np.zeros(len(x)); ry = np.zeros(len(x)); rx[m] = _ranks(x[m]); ry[m] = _ranks(y[m])
        def cor(M, rx=rx, ry=ry):
            n_ = M.sum(1); sx = (rx[ib] * M).sum(1); sy = (ry[ib] * M).sum(1); sxx = (rx[ib] ** 2 * M).sum(1); syy = (ry[ib] ** 2 * M).sum(1); sxy = (rx[ib] * ry[ib] * M).sum(1)
            return (n_ * sxy - sx * sy) / np.sqrt((n_ * sxx - sx ** 2) * (n_ * syy - sy ** 2))
        est = float(stats.spearmanr(x[m], y[m])[0]); bs = cor(m[ib].astype(float)); boots[name] = (est, bs)
        w = boot_wald(est, bs, 0.0); w.update(n=n, r2_pearson_raw=_f(np.corrcoef(x[m], y[m])[0, 1] ** 2), slope_ZA_on_TZ=_f(np.polyfit(x[m], y[m], 1)[0]) if tag.startswith("4a") else None)
        out[name] = w
        if tests:
            reg.add(family, f"{tag}:{name}", f"Spearman rho {tag} {name}", w["p"], w["z"], n)
    return out, boots


def part4_liquidity(D, reg):
    N = D["N"]; dates = D["dates"]; R = D["R"]; TZ, ZA = D["TZ"], D["ZA"]; out = {}
    base = np.isfinite(TZ) & np.isfinite(ZA); ib = sb_idx(N)
    lagIL, lagTO = lagstate(D["IL"]), lagstate(D["TO"])
    cm = {"all": base}
    for c, lab in enumerate(["liquid", "mid", "illiquid"]):
        cm[f"IL:{lab}"] = base & (lagIL == c)
    for c, lab in enumerate(["low_turnover", "mid", "high_turnover"]):
        cm[f"TO:{lab}"] = base & (lagTO == c)
    res, boots = spearman_cells(TZ, ZA, cm, ib, reg, "P4_liq", "4a")
    out["4a_volume_absret"] = res
    for part, (lo_, hi_) in (("IL", ("IL:liquid", "IL:illiquid")), ("TO", ("TO:low_turnover", "TO:high_turnover"))):
        if lo_ in boots and hi_ in boots:
            (e1, b1), (e2, b2) = boots[hi_], boots[lo_]; w = boot_wald(e1 - e2, b1 - b2, 0.0); w["hi_state"] = hi_; w["lo_state"] = lo_
            out.setdefault("4a_diff", {})[part] = w; reg.add("P4_liq", f"4a_diff:{part}", f"rho difference {hi_} minus {lo_}", w["p"], w["z"], res[hi_]["n"] + res[lo_]["n"])
    # 4b price impact
    lnA = np.log(np.where(D["A"] > 0, D["A"], np.nan)); b4 = np.isfinite(lnA) & np.isfinite(TZ)
    cm2 = {"all": b4, "EARLY": b4 & (dates < POST_START), "POST": b4 & (dates >= POST_START)}
    res2, _ = spearman_cells(TZ, np.where(np.isfinite(lnA), lnA, 0.0), cm2, ib, reg, "P4_liq", "4b"); out["4b_amihud_vs_turnover"] = res2
    # 4c volume-conditioned autocorrelation
    out["4c_interaction"] = {}
    for nm, st in (("TZ", TZ), ("ILZ", D["ILZ"])):
        y = R[2:]; r1 = R[1:-1]; z1 = st[1:-1]; ok = np.isfinite(z1) & np.isfinite(y) & np.isfinite(r1)
        X = np.column_stack([np.ones(ok.sum()), r1[ok], z1[ok], r1[ok] * z1[ok]]); b, V, _, _ = ols_hac(y[ok], X, 5); z = b[3] / np.sqrt(V[3, 3])
        out["4c_interaction"][nm] = {"b_R_lag": _f(b[1]), "se_R_lag": _f(np.sqrt(V[1, 1])), "b_interaction": _f(b[3]), "se_interaction": _f(np.sqrt(V[3, 3])), "z": _f(z), "p": _f(z_p(z)), "n": int(ok.sum())}
        reg.add("P4_liq", f"4c:{nm}", f"R_k on R_(k-1) x {nm}_(k-1) interaction", z_p(z), z, ok.sum())
    # 4d walk-forward
    out["4d_wf"] = {}
    yext = np.r_[ZA, np.nan]
    for nm, st in (("TZ", TZ), ("ILZ", D["ILZ"])):
        xs = np.r_[np.nan, st]; w = wf_predict(yext, xs, None); res = wf_eval(ZA, w["yb"][:N], w["yU"][:N], dates)
        res["next_pred"] = _f(w["yU"][N]); res["bench_next_pred"] = _f(w["yb"][N]); out["4d_wf"][nm] = res
        reg.add("P4_liq", f"wf:ZA:{nm}", f"walk-forward |R|/sigma on {nm}_(k-1) (CW)", res["cw_p_one_sided"], res["cw_t"], res["n"])
    k = N - 1
    out["current"] = {"TZ_2026_10_13": _f(TZ[k]), "RV_2026_10_13": _f(D["RV"][k]), "ILZ_2026_10_13": _f(D["ILZ"][k]), "IL_state_code": int(D["IL"][k]), "TO_state_code": int(D["TO"][k]),
                      "amihud_A20_2026_10_13_pct_per_cr": _f(np.exp(D["LA"][k]), 5), "turnover_cr_2026_10_13": _f(D["T"][k], 1)}
    return out


# ----------------------------------------------------------------------------------------------------------------------
# PART 5: regimes, tabulation and v1 interval calibration
# ----------------------------------------------------------------------------------------------------------------------
def stats_for(D, sel):
    R, G, I, rho, sp = D["R"][sel], D["G"][sel], D["I"][sel], D["rho"][sel], D["sig_prev"][sel]
    n = int(sel.sum()); r = {"n": n}
    if n == 0:
        return r
    k_up = int((R > 0).sum()); lo, hi = wilson(k_up, n); z = R / sp
    r.update(spells=runs(sel), mean_R_pct=_f(100 * R.mean(), 4), median_R_pct=_f(100 * np.median(R), 4), sd_R_pct=_f(100 * R.std(ddof=1), 4), mean_abs_R_pct=_f(100 * np.abs(R).mean(), 4),
             mean_G_pct=_f(100 * G.mean(), 4), sd_G_pct=_f(100 * G.std(ddof=1), 4), mean_I_pct=_f(100 * I.mean(), 4), sd_I_pct=_f(100 * I.std(ddof=1), 4),
             mean_range_pct=_f(100 * np.exp(rho).mean() - 100, 4), median_range_pct=_f(100 * (np.exp(np.median(rho)) - 1), 4), P_R_gt_0=_f(k_up / n), P_R_gt_0_wilson95=[_f(lo), _f(hi)],
             R_quantiles_pct={q: _f(100 * np.quantile(R, q), 3) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}, sd_R_over_sigma60=_f(np.nanstd(z, ddof=1)),
             skew_R=_f(stats.skew(R)), excess_kurt_R=_f(stats.kurtosis(R)))
    return r


def regime_tables(D):
    RG, RGl = D["RG"], lagstate(D["RG"]); labs = PART_LABELS["RG"]; out = {"next_session_given_regime": {}, "traits_same_session": {}, "shares": {}}
    valid = RGl >= 0; out["valid_sessions"] = int(valid.sum()); out["first_valid_date"] = str(D["dates"][np.where(valid)[0][0]].date())
    out["next_session_given_regime"]["ALL_VALID"] = stats_for(D, valid)
    for c, lab in enumerate(labs):
        out["next_session_given_regime"][lab] = stats_for(D, RGl == c); sc = RG == c
        out["traits_same_session"][lab] = {"n": int(sc.sum()), "mean_vol20_pct": _f(100 * np.nanmean(D["vol20"][sc]), 3), "mean_tau": _f(np.nanmean(D["tau"][sc]), 3),
                                           "mean_pv": _f(np.nanmean(D["pv"][sc]), 3), "mean_nifty_dd_pct": _f(100 * np.nanmean(D["ndd"][sc]), 2), "mean_vix": _f(np.nanmean(D["vix"][sc]), 2),
                                           "share_with_pv_gt_0.667": _f(np.mean(D["pv"][sc] > 2 / 3))}
        out["shares"][lab] = _f(sc.sum() / (RG >= 0).sum())
    # by calendar year share
    yrs = pd.DatetimeIndex(D["dates"]).year; out["share_by_year"] = {int(y): {lab: _f(np.mean(RG[(yrs == y) & (RG >= 0)] == c)) for c, lab in enumerate(labs)} for y in sorted(set(yrs)) if ((yrs == y) & (RG >= 0)).any()}
    # rule component frequencies
    v = RG >= 0
    out["component_frequencies"] = {"nifty_dd_le_10pct": _f(np.mean((D["ndd"] <= -0.10)[v])), "vix_ge_25": _f(np.mean((D["vix"] >= 25)[v])), "pv_ge_0.9_and_mu20_lt_0": _f(np.mean(((D["pv"] >= 0.9) & (D["mu20"] < 0))[v])),
                                    "event_window": _f(np.mean(D["ev"][v])), "tau_ge_1": _f(np.mean((D["tau"] >= 1.0)[v])), "shock_days_total": int(D["shock"].sum())}
    return out


LEVELS = {50: ("q0.25", "q0.75"), 80: ("q0.1", "q0.9"), 90: ("q0.05", "q0.95"), 95: ("q0.025", "q0.975")}
TAUS = np.array([0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975])


def calibration(D, reg):
    f = pd.read_csv(ROOT / "results/forecasts_R.csv", parse_dates=["date"]); RGl = pd.Series(lagstate(D["RG"]), index=D["dates"]); Rs = pd.Series(D["R"], index=D["dates"])
    labs = PART_LABELS["RG"]; out = {"consistency": {}, "models": {}}; qcols = [f"q{t}" for t in ("0.025", "0.05", "0.1", "0.25", "0.5", "0.75", "0.9", "0.95", "0.975")]
    pin = {}
    for model in ("S6", "S0"):
        g = f[f["model"] == model].set_index("date").sort_index(); out["consistency"][model] = {"n": int(len(g)), "first": str(g.index[0].date()), "last": str(g.index[-1].date()),
                                                                                      "max_abs_y_minus_R": _f(np.nanmax(np.abs(g["y"] - Rs.reindex(g.index))), 12)}
        g["rg"] = RGl.reindex(g.index).values; g = g[g["rg"] >= 0]
        res = {}
        y = g["y"].values; Q = g[qcols].values; loss = np.mean(np.maximum(TAUS * (y[:, None] - Q), (TAUS - 1) * (y[:, None] - Q)), axis=1); pin[model] = pd.Series(loss, index=g.index)
        for cls in ["ALL"] + labs:
            sel = np.ones(len(g), bool) if cls == "ALL" else (g["rg"].values == (labs.index(cls)))
            n = int(sel.sum()); r = {"n": n}
            for lev, (lo_c, hi_c) in LEVELS.items():
                lo, hi, mid = g[lo_c].values[sel], g[hi_c].values[sel], g["q0.5"].values[sel]; yy = y[sel]
                inside = (yy >= lo) & (yy <= hi); x_miss = int(n - inside.sum()); lr, p = kupiec(x_miss, n, 1 - lev / 100)
                rr = np.maximum((yy - mid) / (hi - mid), (mid - yy) / (mid - lo)); kap = float(np.quantile(rr, lev / 100)) if n else np.nan
                entry = {"coverage": _f(inside.mean()), "nominal": lev / 100, "miss": x_miss, "kupiec_lr": _f(lr), "kupiec_p": _f(p), "kappa_restoring_nominal": _f(kap, 3)}
                if n >= 40:
                    ibk = sb_idx(n); kb = np.quantile(rr[ibk], lev / 100, axis=1); entry["kappa_ci95"] = [_f(np.percentile(kb, 2.5), 3), _f(np.percentile(kb, 97.5), 3)]
                if lev == 90:
                    entry["P_below_q05"] = _f((yy < g["q0.05"].values[sel]).mean()); entry["P_above_q95"] = _f((yy > g["q0.95"].values[sel]).mean())
                if cls != "ALL" and n >= 20:
                    reg.add("P5_calib", f"cal:{model}:{cls}:{lev}", f"Kupiec coverage {model} {cls} {lev}%", p, lr, n)
                elif cls != "ALL":
                    reg.skip("P5_calib", f"cal:{model}:{cls}:{lev}", f"{model} {cls} {lev}", f"n={n}<20")
                r[f"L{lev}"] = entry
            r["mean_pinball_loss"] = _f(loss[sel].mean(), 6); res[cls] = r
        # by v1 period, 90% only (descriptive)
        per = {}
        for pn, sel in (("Dev<=2024-06-28", g.index <= "2024-06-28"), ("Val 2024-07..2025-06", (g.index >= "2024-07-01") & (g.index <= "2025-06-30")), ("Final 2025-07+", g.index >= "2025-07-01")):
            inside = ((y >= g["q0.05"].values) & (y <= g["q0.95"].values))[sel]; per[pn] = {"n": int(sel.sum()), "coverage90": _f(inside.mean())}
        res["by_v1_period_90"] = per; out["models"][model] = res
    both = pd.concat([pin["S6"], pin["S0"]], axis=1, keys=["S6", "S0"]).dropna(); both["rg"] = RGl.reindex(both.index).values
    out["pinball_ratio_S6_over_S0"] = {"ALL": _f(both["S6"].mean() / both["S0"].mean(), 4)}
    for c, lab in enumerate(labs):
        b = both[both["rg"] == c]; out["pinball_ratio_S6_over_S0"][lab] = _f(b["S6"].mean() / b["S0"].mean(), 4) if len(b) else None
    return out


# ----------------------------------------------------------------------------------------------------------------------
# PART 6: current regime
# ----------------------------------------------------------------------------------------------------------------------
def classify_at(D, k, ndd_k=None, vix_k=None):
    ndd_k = D["ndd"][k] if ndd_k is None else ndd_k; vix_k = D["vix"][k] if vix_k is None else vix_k
    prongs = {"nifty_dd_le_-10pct": bool(ndd_k <= -0.10), "vix_ge_25": bool(vix_k >= 25), "bse_highvol_and_falling": bool((D["pv"][k] >= 0.90) and (D["mu20"][k] < 0))}
    if any(prongs.values()):
        return "stressed", prongs
    if D["ev"][k]:
        return "event_driven", prongs
    if D["tau"][k] >= 1.0:
        return "trending", prongs
    return "calm", prongs


def part6_current(D, reg, p1):
    N = D["N"]; k = N - 1; labs = PART_LABELS["RG"]; dates = D["dates"]
    lab_now, prongs = classify_at(D, k); lab_stale, prongs_stale = classify_at(D, k, D["ndd"][k - 1], D["vix"][k - 1])
    c_now = labs.index(lab_now); RGl = lagstate(D["RG"]); valid = RGl >= 0
    shock_dates = [str(dates[j].date()) for j in range(max(0, k - 4), k + 1) if D["shock"][j]]
    cur = {"date": str(dates[k].date()), "regime": lab_now, "regime_code": c_now, "prongs_stressed": prongs, "event_window_active": bool(D["ev"][k]), "shock_dates_in_last_5_sessions": shock_dates,
           "tau": _f(D["tau"][k]), "tau_threshold": 1.0, "pv_vol20_pct_rank": _f(D["pv"][k]), "vol20_pct": _f(100 * D["vol20"][k]), "sig60_pct": _f(100 * D["sig"][k]), "mu20_pct": _f(100 * D["mu20"][k]),
           "nifty_close": _f(D["nif"][k], 2), "nifty_sma200": _f(D["sma200"][k], 2), "nifty_dd_from_250d_high_pct": _f(100 * D["ndd"][k]), "india_vix_close": _f(D["vix"][k], 3), "bse_dd_from_250d_high_pct": _f(100 * D["dd"][k]),
           "R_2026_10_13_pct": _f(100 * D["R"][k]), "G_pct": _f(100 * D["G"][k]), "I_pct": _f(100 * D["I"][k]),
           "regime_if_index_state_were_2026_10_12": lab_stale, "PV_state": PART_LABELS["PV"][D["PV"][k]], "PN_state": PART_LABELS["PN"][D["PN"][k]], "PD_state": PART_LABELS["PD"][D["PD"][k]],
           "signals": {s: _f(D["m"][s][k]) for s in ("m1", "m5", "m20", "m60")}, "momentum_model_next_session_pred_pct": {kk: v["next_session_pred_pct"] for kk, v in p1["wf"]["models"].items()},
           "breakout_state": current_breakout_state(D)}
    sel = RGl == c_now; allv = valid
    hist = {"regime": lab_now, "conditional": stats_for(D, sel), "unconditional_same_sample": stats_for(D, allv)}
    full = np.ones(N, bool); full[0] = False; hist["unconditional_full_sample_k>=1"] = stats_for(D, full)
    # bootstrap tests: conditional minus all-valid
    ib = sb_idx(N); R = D["R"]; absR = np.abs(R); up = (R > 0).astype(float)
    def cell_stats(m_b, v_b):
        out = {}
        for nm, arr in (("mean_R", R), ("mean_absR", absR), ("P_up", up)):
            a = (arr[ib] * m_b).sum(1) / np.maximum(m_b.sum(1), 1); b = (arr[ib] * v_b).sum(1) / np.maximum(v_b.sum(1), 1); out[nm] = (a, b)
        def sd(m):
            n_ = np.maximum(m.sum(1), 2); mu = (R[ib] * m).sum(1) / n_; return np.sqrt(np.maximum((R[ib] ** 2 * m).sum(1) / n_ - mu ** 2, 0) * n_ / (n_ - 1))
        out["log_sd"] = (np.log(sd(m_b)), np.log(sd(v_b))); return out
    mb, vb = sel[ib].astype(float), valid[ib].astype(float); cs = cell_stats(mb, vb)
    est = {"mean_R": R[sel].mean() - R[valid].mean(), "mean_absR": absR[sel].mean() - absR[valid].mean(), "P_up": up[sel].mean() - up[valid].mean(), "log_sd": np.log(R[sel].std(ddof=1)) - np.log(R[valid].std(ddof=1))}
    hist["tests"] = {}
    for nm in ("mean_R", "log_sd", "P_up", "mean_absR"):
        w = boot_wald(est[nm], cs[nm][0] - cs[nm][1], 0.0); w["note"] = "conditional minus unconditional (same sample)"; hist["tests"][nm] = w
        reg.add("P6_current", f"cur:{nm}", f"current regime ({lab_now}) vs all: {nm}", w["p"], w["z"], int(sel.sum()))
    q = {}
    for qq in (0.05, 0.25, 0.5, 0.75, 0.95):
        qb = np.array([np.quantile(R[ib[i]][sel[ib[i]]], qq) if sel[ib[i]].sum() > 20 else np.nan for i in range(0, 1000)])   # first 1000 draws (speed)
        q[str(qq)] = {"est_pct": _f(100 * np.quantile(R[sel], qq), 3), "ci95_pct": [_f(100 * np.nanpercentile(qb, 2.5), 3), _f(100 * np.nanpercentile(qb, 97.5), 3)]}
    hist["conditional_R_quantiles_boot_ci"] = q
    # all four classes' standardised next-day scale, for context
    hist["sd_by_class_pct"] = {lab: _f(100 * R[RGl == c].std(ddof=1), 3) for c, lab in enumerate(labs)}
    return {"current": cur, "history": hist}


# ----------------------------------------------------------------------------------------------------------------------
# POST-HOC diagnostics (AMENDMENT A3: exploratory, made after the registered results were seen)
# ----------------------------------------------------------------------------------------------------------------------
def _rho_cell(a, b, mask, ib, boot=True):
    """correlation of a (current) and b (lagged) over mask, with stationary-bootstrap SE/CI (pairs arrays have length n1)."""
    def cor(m, bt):
        if bt:
            M = m[ib]; n_ = M.sum(1); sa = (a[ib] * M).sum(1); sb = (b[ib] * M).sum(1); saa = (a[ib] ** 2 * M).sum(1); sbb = (b[ib] ** 2 * M).sum(1); sab = (a[ib] * b[ib] * M).sum(1)
            return (n_ * sab - sa * sb) / np.sqrt((n_ * saa - sa ** 2) * (n_ * sbb - sb ** 2))
        return np.corrcoef(a[m], b[m])[0, 1]
    est = cor(mask, False); bs = cor(mask, True); w = boot_wald(est, bs, 0.0); w["n"] = int(mask.sum()); return w


def posthoc(D, reg, R_):
    N = D["N"]; dates = D["dates"]; R, G, I = D["R"], D["G"], D["I"]; out = {}
    n1 = N - 1; ib = sb_idx(n1); d1 = dates[1:]
    Rc = R - R.mean(); Gc = G - G.mean(); Ic = I - I.mean()
    eras = {"EARLY": d1 < POST_START, "L1": (d1 >= POST_START) & (d1 < AUC_START), "AUC": d1 >= AUC_START}
    nr = np.r_[np.nan, np.diff(np.log(D["nif"]))]; nrc = np.nan_to_num(nr - np.nanmean(nr))
    # X1
    x1 = {"BSE_R_by_era": {k: _rho_cell(Rc[1:], Rc[:-1], m, ib) for k, m in eras.items()}, "Nifty50_by_era": {k: _rho_cell(nrc[1:], nrc[:-1], m & np.isfinite(nr[1:]) & np.isfinite(nr[:-1]), ib) for k, m in eras.items()},
          "BSE_R_by_year": {}, "Nifty50_all": _rho_cell(nrc[1:], nrc[:-1], np.isfinite(nr[1:]) & np.isfinite(nr[:-1]), ib)}
    yrs = pd.DatetimeIndex(d1).year
    for y_ in sorted(set(yrs)):
        x1["BSE_R_by_year"][int(y_)] = _rho_cell(Rc[1:], Rc[:-1], yrs == y_, ib)
    out["X1_acf_by_era_year"] = x1
    # X2 decomposition of lag-1 autocovariance and open-to-open
    allm = np.ones(n1, bool); tot = (Rc[1:] * Rc[:-1]).sum(); comp = {}
    for nm, a, b in (("G_k_vs_G_k-1", Gc, Gc), ("G_k_vs_I_k-1", Gc, Ic), ("I_k_vs_G_k-1", Ic, Gc), ("I_k_vs_I_k-1", Ic, Ic)):
        w = _rho_cell(a[1:], b[:-1], allm, ib); w["share_of_total_autocov"] = _f((a[1:] * b[:-1]).sum() / tot); comp[nm] = w
        for ek, em in eras.items():
            if ek != "AUC":
                comp[f"{nm}|{ek}"] = {**_rho_cell(a[1:], b[:-1], em, ib), "share_of_total_autocov_in_era": _f((a[1:][em] * b[:-1][em]).sum() / (Rc[1:][em] * Rc[:-1][em]).sum())}
    OO = I[:-1] + G[1:]; OOc = OO - OO.mean()          # open-to-open return of session k (k>=1) = I_{k-1} + G_k
    comp["open_to_open_lag1"] = _rho_cell(OOc[1:], OOc[:-1], np.ones(len(OOc) - 1, bool), sb_idx(len(OOc) - 1))
    out["X2_autocov_decomposition"] = comp
    # X3 drift-adjusted flip
    k60 = np.arange(N) >= 60; masks = gap_masks(D["G"] / D["sig_prev"], G, I); Cfull = (np.sign(I) == np.sign(G)).astype(float)
    g_E = k60 & (dates < POST_START); g_L1 = (dates >= POST_START) & (dates < AUC_START); x3 = {}
    posE, posL = np.where(g_E)[0], np.where(g_L1)[0]
    resE = perm_cells(np.sign(I[posE]).astype(np.int8), np.sign(G[posE]).astype(np.int8), {c: masks[c][posE] for c in ("up_ML", "down_ML", "pooled_ML")})
    resL = perm_cells(np.sign(I[posL]).astype(np.int8), np.sign(G[posL]).astype(np.int8), {c: masks[c][posL] for c in ("up_ML", "down_ML", "pooled_ML")})
    for cell in ("up_ML", "down_ML", "pooled_ML"):
        bsd = []
        for pos, res_ in ((posE, resE), (posL, resL)):
            ibp = sb_idx(len(pos)); M = masks[cell][pos][ibp]; cb = (Cfull[pos][ibp] * M).sum(1) / np.maximum(M.sum(1), 1); bsd.append(cb - res_[cell]["pi0"])
        est = resL[cell]["excess"] - resE[cell]["excess"]; w = boot_wald(est, bsd[1] - bsd[0], 0.0)
        w.update(excess_EARLY=resE[cell]["excess"], excess_L1=resL[cell]["excess"], n_EARLY=resE[cell]["n"], n_L1=resL[cell]["n"], c_EARLY=resE[cell]["c"], c_L1=resL[cell]["c"], pi0_EARLY=resE[cell]["pi0"], pi0_L1=resL[cell]["pi0"])
        x3[cell] = w; reg.add("X_posthoc", f"xflip:{cell}", f"drift-adjusted flip (c-pi0)_L1 - (c-pi0)_EARLY, {cell}", w["p"], w["z"], resE[cell]["n"] + resL[cell]["n"])
    out["X3_drift_adjusted_flip"] = x3
    # X4 walk-forward OOS R2 by calendar year
    x4 = {}
    for nm, y_arr, xs in (("m1_U_on_R", R, np.r_[np.nan, D["m"]["m1"]]), ("TZ_U_on_ZA", D["ZA"], np.r_[np.nan, D["TZ"]])):
        yext = np.r_[y_arr, np.nan]; w = wf_predict(yext, xs); ks = np.arange(OOS_START, N); yr = pd.DatetimeIndex(dates[ks]).year; row = {}
        for y_ in sorted(set(yr)):
            s = (yr == y_) & np.isfinite(y_arr[ks]) & np.isfinite(w["yU"][ks]); kk = ks[s]
            row[int(y_)] = {"n": int(s.sum()), "r2": _f(r2_of(y_arr[kk], w["yb"][kk], w["yU"][kk]), 5)}
        x4[nm] = row
    out["X4_oos_r2_by_year"] = x4
    # X5 relative volume on breakout days
    rv = D["RV"]; x5 = {}
    for nm, m in (("all_days", np.isfinite(rv)), ("up_breakout", D["Bup"] & np.isfinite(rv)), ("down_breakout", D["Bdn"] & np.isfinite(rv))):
        x5[nm] = {"n": int(m.sum()), "median_RV": _f(np.median(rv[m])), "mean_RV": _f(rv[m].mean()), "share_RV_gt_2": _f(np.mean(rv[m] > 2))}
    out["X5_relative_volume_on_breakouts"] = x5
    # X6 stressed sub-types
    RGl = lagstate(D["RG"]); p1 = np.r_[False, (D["ndd"] <= -0.10)[:-1]]; p2 = np.r_[False, (D["vix"] >= 25)[:-1]]; p3 = np.r_[False, ((D["pv"] >= 0.9) & (D["mu20"] < 0))[:-1]]
    st_ = RGl == 3; only = st_ & p1 & ~p2 & ~p3; other = st_ & ~only; x6 = {"nifty_dd_prong_only": stats_for(D, only), "other_stress": stats_for(D, other), "calm_for_reference": stats_for(D, RGl == 0)}
    f = pd.read_csv(ROOT / "results/forecasts_R.csv", parse_dates=["date"]); g = f[f["model"] == "S6"].set_index("date").sort_index(); Rl = pd.Series(RGl, index=dates)
    for nm, m in (("nifty_dd_prong_only", only), ("other_stress", other)):
        sel = g.index.isin(dates[m]); yy = g["y"].values[sel]; lo, hi, mid = g["q0.05"].values[sel], g["q0.95"].values[sel], g["q0.5"].values[sel]
        inside = (yy >= lo) & (yy <= hi); lr, p_ = kupiec(int(len(yy) - inside.sum()), len(yy), 0.10); rr = np.maximum((yy - mid) / (hi - mid), (mid - yy) / (mid - lo)); ibk = sb_idx(len(yy))
        kb = np.quantile(rr[ibk], 0.9, axis=1); x6[nm]["S6_90pct_interval"] = {"n": int(len(yy)), "coverage": _f(inside.mean()), "kupiec_p_descriptive": _f(p_), "kappa": _f(np.quantile(rr, 0.9), 3), "kappa_ci95": [_f(np.percentile(kb, 2.5), 3), _f(np.percentile(kb, 97.5), 3)],
                                                                             "mean_S6_sigma_pct": _f(100 * g["sigma"].values[sel].mean(), 3), "realised_sd_R_pct": _f(100 * yy.std(ddof=1), 3)}
    out["X6_stressed_subtypes"] = x6
    # X7 vol-tercile balance
    ks = np.arange(OOS_START, N); sh = {PART_LABELS["PV"][c]: _f(np.mean(lagstate(D["PV"])[ks] == c)) for c in range(3)}
    out["X7_expanding_vol_tercile_balance_OOS"] = sh
    # X8 results-reaction days
    rd = pd.read_csv(ROOT / "data/results_dates.csv", parse_dates=["first_tradable_session"]); x8 = []
    for q, d_ in zip(rd["quarter"], rd["first_tradable_session"]):
        if d_ in dates:
            k = int(dates.get_loc(d_)); x8.append({"quarter": q, "reaction_session": str(d_.date()), "R_pct": _f(100 * R[k], 3), "R_over_sigma60": _f(R[k] / D["sig_prev"][k], 2), "regime_at_prev_close": PART_LABELS["RG"][RGl[k]] if RGl[k] >= 0 else None,
                                                   "flagged_E4_shock_that_day": bool(D["shock"][k])})
    out["X8_results_reaction_days"] = x8
    # X9 'broadly unchanged' frequency |y| < 0.25 sigma_S6 by regime at the previous close
    gg = f[f["model"] == "S6"].set_index("date").sort_index(); rg = pd.Series(RGl, index=dates).reindex(gg.index).values; ev9 = (gg["y"].abs() < 0.25 * gg["sigma"]).values; x9 = {}
    for nm, m in (("ALL", rg >= 0), *[(lab, rg == c) for c, lab in enumerate(PART_LABELS["RG"])]):
        k_, n_ = int(ev9[m].sum()), int(m.sum()); lo, hi = wilson(k_, n_); x9[nm] = {"n": n_, "freq": _f(k_ / n_), "wilson95": [_f(lo), _f(hi)]}
    x9["v1_record_value_for_2026_10_14"] = 0.238; x9["note"] = "descriptive; the v1 value is the FHS-model mass for the 14-Oct sigma, the frequencies are realised shares over 2019-02..2026-10-12"
    out["X9_broadly_unchanged_frequency"] = x9
    return out


# ----------------------------------------------------------------------------------------------------------------------
# status rules (fixed in the header) + main
# ----------------------------------------------------------------------------------------------------------------------
def wf_status(res, holm_fam):
    ok = (res["r2"] is not None and res["r2"] > 0 and holm_fam is not None and holm_fam < 0.05 and (res["r2_first_half"] or -1) > 0 and (res["r2_second_half"] or -1) > 0
          and (res["r2_final_2025_07_plus"] or -1) > 0 and (res["r2_ex_top5_abs"] or -1) > 0)
    return "validated_out_of_sample" if ok else "not_found"


def apply_status_rules(R_, reg):
    st = {}
    for tid, res in R_["part1"]["wf"]["models"].items():
        st[tid] = wf_status(res, reg.adj(tid)["holm_family"])
    for tid, res in R_["part4"]["4d_wf"].items():
        t_ = f"wf:ZA:{tid}"; st[t_] = wf_status(res, reg.adj(t_)["holm_family"])
    # gap rule: EARLY sign vs POST / AUC
    cells = R_["part2"]["cells"]
    for per in ("POST", "AUC"):
        for name, r in cells[per].items():
            tid = f"gap:{per}:{name}"
            if tid not in reg.df.index:
                continue
            e = cells["EARLY"].get(name, {}).get("excess"); a = reg.adj(tid)
            if e is None or r.get("excess") is None:
                st[tid] = "not_found"; continue
            same = np.sign(e) == np.sign(r["excess"])
            st[tid] = ("validated_out_of_sample" if same else "contradicted") if a["holm_family"] < 0.05 else "not_found"
    for tid, r in R_["part3"]["holdout"].items():
        if tid not in reg.df.index:
            continue
        a = reg.adj(tid); st[tid] = "validated_out_of_sample" if (a["holm_family"] < 0.05 and r["dev_p_two_sided"] < 0.10) else "not_found"
    for tid in reg.df.index:
        if tid.startswith("cal:"):
            st[tid] = "contradicted" if reg.adj(tid)["holm_family"] < 0.05 else "descriptive_only"
    return st


def to_jsonable(o):
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def main():
    import time
    t0 = time.time(); reg = Registry(); D = build(); N = D["N"]; dates = D["dates"]; R_ = {}
    R_["meta"] = {"script": "src/behaviour/pattern_tests.py", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "seed": SEED, "B_boot": B_BOOT, "block_mean": BLOCK,
                  "information_cutoff": "2026-10-13T22:00:00+05:30", "reference_price_P0": 3375.40, "n_sessions": N, "first_session": str(dates[0].date()), "last_session": str(dates[-1].date()),
                  "post_cutoff_data_used": False, "cutoff_exposure": "none: no network access, no fetch_*.py run, no file dated after 2026-10-13 read (asserted max date <= 2026-10-13 for bse_daily and index_daily)",
                  "disclosures": ["earlier attempt of this workstream existed in the scratchpad; discovered after the first real run, content opened only after the results were final, for a lag-1 ACF cross-check (see AMENDMENT A4)", "amendments A2 (breakout terciles) and A3 (post-hoc diagnostics) were made after the first real run; A2 before any breakout outcome was seen, A3 after all registered results were seen"],
                  "index_row_2026_10_13": {"source": "copied from src/behaviour/linkages.py IDX_20261013 (NSE ind_close_all_13102026.csv, Last-Modified 19:50 IST 2026-10-13)", "values": IDX_20261013, "verified_here": False}}
    R_["data_coverage"] = {"deliv_pct_first_valid": str(dates[np.isfinite(D["DP"])][0].date()), "deliv_pct_valid_n": int(np.isfinite(D["DP"]).sum()), "n_since_2024_07_01": int((dates >= POST_START).sum()), "n_since_2026_08_03": int((dates >= AUC_START).sum()),
                           "regime_first_valid": str(dates[np.where(D["RG"] >= 0)[0][0]].date()), "PV_first_valid": str(dates[np.where(D["PV"] >= 0)[0][0]].date()),
                           "PN_first_valid": str(dates[np.where(D["PN"] >= 0)[0][0]].date()), "PD_first_valid": str(dates[np.where(D["PD"] >= 0)[0][0]].date()), "OOS_first": str(dates[OOS_START].date())}
    R_["v1_replication"] = v1_replication(D)
    R_["part1"] = {"acf_vr": part1_acf_vr(D, reg), "wf": part1_wf(D, reg)}; print("part1 done", round(time.time() - t0), "s", flush=True)
    # EARLY-period cell stats supply the sign for the status rule (descriptive, not registered; see AMENDMENTS A1)
    R_["part2"] = part2_gap(D, reg); print("part2 done", round(time.time() - t0), "s", flush=True)
    k60 = np.arange(N) >= 60; pos = np.where(k60 & (dates < POST_START))[0]; masks = gap_masks(D["G"] / D["sig_prev"], D["G"], D["I"])
    keep = ("up_S", "up_M", "up_L", "down_S", "down_M", "down_L", "up_all", "down_all", "all", "pooled_ML", "up_ML", "down_ML")
    R_["part2"]["cells"]["EARLY"] = perm_cells(np.sign(D["I"][pos]).astype(np.int8), np.sign(D["G"][pos]).astype(np.int8), {n_: masks[n_][pos] for n_ in keep})
    R_["part3"] = part3_breakouts(D, reg); print("part3 done", round(time.time() - t0), "s", flush=True)
    R_["part4"] = part4_liquidity(D, reg); print("part4 done", round(time.time() - t0), "s", flush=True)
    R_["part5"] = {"rules": "see module docstring PART 5", "tables": regime_tables(D), "calibration": calibration(D, reg)}
    R_["part6"] = part6_current(D, reg, R_["part1"]); print("part6 done", round(time.time() - t0), "s", flush=True)
    R_["posthoc_A3"] = posthoc(D, reg, R_); print("posthoc done", round(time.time() - t0), "s", flush=True)
    df = reg.finalize()
    R_["multiple_testing"] = {"n_tests": int(len(df)), "n_skipped": len(reg.skipped), "families": df.groupby("family").size().to_dict(),
                              "n_holm_global_lt_0.05": int((df["holm_global"] < 0.05).sum()), "n_bh_global_lt_0.10": int((df["bh_global"] < 0.10).sum()), "n_raw_p_lt_0.05": int((df["p"] < 0.05).sum()),
                              "expected_false_positives_at_0.05": _f(0.05 * len(df), 2),
                              "table": [{"id": i, **{k: _f(v, 6) if isinstance(v, float) else v for k, v in r.items()}} for i, r in df.reset_index().set_index("id").iterrows()], "skipped": reg.skipped}
    R_["status_rules_applied"] = apply_status_rules(R_, reg)
    R_["runtime_seconds"] = round(time.time() - t0, 1)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True); OUT_JSON.write_text(json.dumps(to_jsonable(R_), indent=1))
    print(f"wrote {OUT_JSON}  tests={len(df)}  runtime={R_['runtime_seconds']}s")
    return R_


# ----------------------------------------------------------------------------------------------------------------------
# self-test on SIMULATED data only
# ----------------------------------------------------------------------------------------------------------------------
def selftest():
    import statsmodels.api as sm
    from statsmodels.stats.multitest import multipletests
    rng = np.random.default_rng(11); ok = True
    def chk(name, cond, info=""):
        nonlocal ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name, info, flush=True)
    # (a) HAC vs statsmodels
    n = 800; X = np.column_stack([np.ones(n), rng.standard_normal(n)]); e = np.zeros(n)
    for i in range(1, n):
        e[i] = 0.4 * e[i - 1] + rng.standard_normal()
    y = X @ [0.1, 0.3] + e; b, V, _, _ = ols_hac(y, X, 6); m = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6, "use_correction": True})
    chk("HAC equals statsmodels", np.allclose(np.sqrt(np.diag(V)), m.bse, rtol=1e-6), f"{np.sqrt(np.diag(V))} vs {m.bse}")
    p = rng.random(60) ** 2
    chk("Holm equals statsmodels", np.allclose(holm(p), multipletests(p, method="holm")[1])); chk("BH equals statsmodels", np.allclose(bh(p), multipletests(p, method="fdr_bh")[1]))
    # (c) walk-forward vs brute force, and same-row perturbation
    M = 700; yy = rng.standard_normal(M) * 0.02; yy = np.r_[yy, np.nan]; xx = np.r_[np.nan, yy[:M - 1] * 0 + rng.standard_normal(M - 1), 0.5]
    st = np.r_[-1, rng.integers(0, 3, M)].astype(int)
    w = wf_predict(yy, xx, st, min_cell=40)
    for k in (300, 450, 600):
        tr = [j for j in range(k) if np.isfinite(xx[j]) and np.isfinite(yy[j])]; A = np.column_stack([np.ones(len(tr)), xx[tr]]); bb = np.linalg.lstsq(A, yy[tr], rcond=None)[0]
        chk(f"wf U equals brute force at k={k}", np.isclose(w["yU"][k], bb[0] + bb[1] * xx[k], atol=1e-10))
        trc = [j for j in tr if st[j] == st[k]]; A = np.column_stack([np.ones(len(trc)), xx[trc]]); bc = np.linalg.lstsq(A, yy[trc], rcond=None)[0]
        chk(f"wf RC equals brute force at k={k}", np.isclose(w["yRC"][k], bc[0] + bc[1] * xx[k], atol=1e-10))
        chk(f"wf bench equals expanding mean at k={k}", np.isclose(w["yb"][k], np.mean(yy[:k])))
    y2 = yy.copy(); y2[400] += 5.0; w2 = wf_predict(y2, xx, st, min_cell=40)
    chk("same-row perturbation: forecast for k=400 ignores y_400", w2["yU"][400] == w["yU"][400] and w2["yb"][400] == w["yb"][400] and w2["yRC"][400] == w["yRC"][400])
    chk("... but forecast for k=401 uses it", w2["yU"][401] != w["yU"][401])
    # expanding terciles: no look-ahead
    s = rng.standard_normal(600); t1 = expanding_terciles(s, 250); s2 = s.copy(); s2[400:] += 9; t2 = expanding_terciles(s2, 250)
    chk("expanding terciles ignore the future", np.array_equal(t1[:400], t2[:400]))
    # (d) CW / PT size and power
    rej = 0; ptrej = 0; reps = 150
    for r in range(reps):
        yv = rng.standard_t(5, 1500) * 0.02; xv = np.r_[np.nan, rng.standard_normal(1499)]; ww = wf_predict(yv, xv)
        k = np.arange(500, 1500); res = cw_stats(yv[k], ww["yb"][k], ww["yU"][k]); rej += (res["cw_p_one_sided"] < 0.05)
        pt = pt_test(np.sign(xv[k]), np.sign(yv[k])); ptrej += (pt["p_two_sided"] < 0.05)
    chk("CW null size about 5%", 0.0 <= rej / reps <= 0.12, f"{rej / reps:.3f}"); chk("PT null size about 5%", 0.01 <= ptrej / reps <= 0.12, f"{ptrej / reps:.3f}")
    yv = 0.02 * (0.5 * np.r_[np.nan, np.random.default_rng(3).standard_normal(1499)] * 0 + 0); xv = np.r_[np.nan, rng.standard_normal(1499)]; yv = 0.02 * (0.3 * np.nan_to_num(xv) + rng.standard_normal(1500))
    ww = wf_predict(yv, xv); k = np.arange(500, 1500); res = cw_stats(yv[k], ww["yb"][k], ww["yU"][k]); chk("CW detects an injected predictor", res["cw_p_one_sided"] < 0.01 and res["r2"] > 0, str(res))
    # (f) bootstrap ACF / VR size and power on one cell
    N_ = 1500; ibs = sb_idx(N_ - 1); rej = 0; reps = 60; pv_ = []
    for r in range(reps):
        x = rng.standard_t(5, N_) * 0.02; xc = x - x.mean(); pr = xc[1:] * xc[:-1]; s0_ = xc[1:] ** 2; s1_ = xc[:-1] ** 2
        est = pr.sum() / np.sqrt(s0_.sum() * s1_.sum()); bs = pr[ibs].sum(1) / np.sqrt(s0_[ibs].sum(1) * s1_[ibs].sum(1)); pv_.append(boot_wald(est, bs)["p"])
    pv_ = np.array(pv_); chk("bootstrap ACF null size", (pv_ < 0.05).mean() <= 0.15, f"rej={np.mean(pv_ < 0.05):.3f}")
    x = np.zeros(N_)
    for i in range(1, N_):
        x[i] = 0.15 * x[i - 1] + rng.standard_normal() * 0.02
    xc = x - x.mean(); pr = xc[1:] * xc[:-1]; s0_ = xc[1:] ** 2; s1_ = xc[:-1] ** 2; est = pr.sum() / np.sqrt(s0_.sum() * s1_.sum()); bs = pr[ibs].sum(1) / np.sqrt(s0_[ibs].sum(1) * s1_[ibs].sum(1))
    chk("bootstrap ACF detects rho=0.15", boot_wald(est, bs)["p"] < 0.01, f"{boot_wald(est, bs)}")
    # (g) permutation cell test: size and power
    nG = 1200; pvs = []
    for r in range(80):
        g = rng.standard_normal(nG); i_ = rng.standard_normal(nG) - 0.25; sI = np.sign(i_).astype(np.int8); sG = np.sign(g).astype(np.int8); m = np.abs(g) > 0.5
        pvs.append(perm_cells(sI, sG, {"c": m})["c"]["p"])
    pvs = np.array(pvs); chk("permutation null size", np.mean(pvs < 0.05) <= 0.14, f"rej={np.mean(pvs < 0.05):.3f}")
    g = rng.standard_normal(nG); i_ = 0.4 * g + rng.standard_normal(nG); r_ = perm_cells(np.sign(i_).astype(np.int8), np.sign(g).astype(np.int8), {"c": np.abs(g) > 0.5})["c"]
    chk("permutation detects injected continuation", r_["p"] < 0.001 and r_["c"] > r_["pi0"], str(r_))
    # (h) sup-Wald
    xg = rng.standard_normal(1000); yb_ = np.where(np.arange(1000) < 500, -0.3 * xg, 0.3 * xg) + rng.standard_normal(1000)
    F1, s1 = sup_wald(xg, yb_); F0, s0 = sup_wald(xg, 0 * xg + rng.standard_normal(1000))
    chk("sup-Wald finds break near 500", F1 > 20 and abs(s1 - 500) < 120 and F0 < 12, f"F1={F1:.1f} at {s1}; F0={F0:.1f}")
    # (i) Kupiec
    chk("Kupiec LR=0 at nominal", abs(kupiec(5, 100, 0.05)[0]) < 1e-9); chk("Kupiec rejects 15/100 vs 5%", kupiec(15, 100, 0.05)[1] < 0.01)
    # (j) breakout flags use only prior-window highs
    lcs = np.cumsum(rng.standard_normal(200) * 0.01); lhs = lcs + 0.005; mx = pd.Series(lhs).rolling(20).max().shift(1).values; Bu = np.isfinite(mx) & (lcs > mx)
    lhs2 = lhs.copy(); lhs2[150:] += 1.0; mx2 = pd.Series(lhs2).rolling(20).max().shift(1).values
    chk("breakout threshold at k unaffected by highs from k onward", np.allclose(mx[:150], mx2[:150], equal_nan=True))
    print("SELFTEST", "ALL PASS" if ok else "FAILURES")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(0 if selftest() else 1)
    main()
