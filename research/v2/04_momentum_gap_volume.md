# v2 workstream "patterns": momentum vs reversal, opening gaps, breakouts, liquidity and regimes (NSE:BSE, session 2026-10-14)

Code: `src/behaviour/pattern_tests.py` (definitions and thresholds are in its module docstring, written before any BSE statistic was computed).
Numbers: `results/behaviour/patterns.json` (every figure below is read from it; JSON paths are given as `part1`, `part2`, ... `posthoc_A3`, `multiple_testing`).
Reference price P0 = Rs 3,375.40 (NSE close 2026-10-13). v2 information cutoff 2026-10-13 22:00 IST. Nothing here is investment advice.

## 0. Provenance, order of work, cutoff exposure

| item | value |
|---|---|
| pre-registration header written | 2026-10-14 07:15:21 UTC (file mtime), before any BSE return, gap, volume or regime statistic was computed by this workstream |
| first real run (script SHA-256 `c6dde21a...`) | 2026-10-14 ~07:22 UTC, 202 tests |
| final run (script SHA-256 `a45ea8ff691778266cc7b3d3273257058f8a90b52e8544c989dae60541043696`) | 2026-10-14 07:38 UTC (wording-only header edit after the 07:32 run; numeric results unchanged), 259 tests, 20 s, seed 20261014, stationary bootstrap B = 2000 (mean block 10), wild bootstrap B = 1999 |
| self-test on simulated data (`--selftest`) | 26 checks pass: HAC equals statsmodels, Holm/BH equal statsmodels, walk-forward fits equal brute-force OLS, same-row perturbation shows no leak, CW/PT/bootstrap/permutation null sizes about 5% and injected effects detected, sup-Wald finds an injected break |
| independent re-computation (plain pandas/numpy, not the script's functions) | lag-1 ACF 0.10515, VR(5) 1.2133, m1 OOS R2 0.009535, CW t 3.5236, gap cell n/rates, breakout counts 158/165 (also with price-adjusted highs), S6 90% coverage 0.8877, Nifty drawdown -13.698%, BSE drawdown -23.344%: all equal the script |
| v1 replication | `conditional_day.json` gap-up/down tables reproduced exactly with the v1 EWMA sigma (n 273/106/77 full, 42/31/12 since 2024-07, same P(I>0)); window sizes differ by one row (2358 vs 2357, v1 dropped a NaN row) |

**Cutoff exposure: none.** No network access, no `src/fetch_*.py`, no refresh of `data/raw/macro`. Inputs: `bse_daily.csv` (last session 2026-10-13, asserted), `index_daily.csv` (last row 2026-10-12, asserted), `forecasts_R.csv` (last row 2026-10-12), `data/results_dates.csv`, `results/conditional_day.json`, and the v1 record keys. The only non-repo facts are the 2026-10-13 index row (Nifty 50 22,721.95, India VIX 14.12), copied from the constants of `src/behaviour/linkages.py` (NSE file Last-Modified 19:50 IST on 2026-10-13, before the cutoff); I did not re-verify them (regime label is unchanged if the 2026-10-12 index state is used instead: Nifty drawdown -15.06% instead of -13.70%, still "stressed"). The sandbox clock reads 14 Oct 2026 (session in progress); no 14-Oct bar, quote, headline or file was opened. The 14-Oct session is unseen.

**Amendments (all in the script header).** A1 (before the first run): EARLY-period permutation cells computed to give the sign for the status rule. A2 (after the first run, before any breakout return or p-value was looked at; only cell counts had been printed): the pre-registered relative-volume and delivery terciles taken over ALL days are degenerate for breakouts (up-breakouts fall 1/20/129 into low/mid/high relative-volume terciles and 108/17/4 into low/mid/high delivery terciles), so terciles among breakouts of the same direction with cut points fixed on pre-2024-07 breakouts were added; the original all-day tests are kept, counted, and reported as families P3_alldayterc and P3_holdout_alldayterc. A3 (after all registered results were seen): post-hoc diagnostics X1-X9, only X3 (3 tests) carries p-values and is counted. A4: an earlier attempt of this workstream existed in the scratchpad; I found it by listing the scratchpad after the first real run, viewed only names and sizes until my results were final, then opened its header and lag-1 autocorrelation table were opened as a bug cross-check (lag-1 ACF all 0.104 vs 0.105 here; below/above 200-day 0.125/0.095 vs 0.124/0.097; deep drawdown 0.151 vs 0.162). Agreement of two runs on the same data is not independent confirmation.

**Peeking log.** Before pre-registration I had seen v1's `conditional_day.json` gap table (full sample P(I>0 | gap-up > 0.5 sd) = 0.359; since 2024-07 = 0.714), so the "gap effect flips" hypothesis is informed by v1, not blind. The break dates 2024-07-01 (v1 Validation start) and 2026-08-03 (closing auction) come from the v1 protocol and the exchange rule.

## 1. Bottom line for the 2026-10-14 forecast (numbers, not adjectives)

1. **Direction: no validated edge from any pattern in this family.** Of 259 registered tests, 16 survive whole-registry Holm (adjusted p < 0.05), and none of the 16 is a directional predictor of next-day R that passed its fixed out-of-sample gate. The nearest case is the previous-day return: walk-forward OOS R2 +0.95% (Clark-West t 3.52, one-sided p 0.0002; Holm within family 0.004, whole registry 0.052), positive in 7 of 8 calendar years, but R2 is -0.68% in the Final window (2025-07+; -2.83% in 2025-H2, +0.85% in 2026) so it fails the gate fixed in advance. Its model-implied next-session mean is +0.27% against +0.14% for the expanding mean: a shift of +0.13 pp = 0.05 sigma (sigma_R 2.478%). Location stays L0; P(close > P0) stays 0.50 (v1: 0.50 / 0.532 with drift).
2. **Scale: v1's sigma_R = 2.478% stands.** The session is classified "stressed" at the 2026-10-13 close through a single prong (Nifty 50 is 13.70% below its 250-day high of 26,328.55 and below its 200-day average 24,232.8; India VIX 14.12 < 25; BSE 20-day volatility is at the 0.56 percentile of its history; BSE 20-day return -0.25%). Historically, S6's 90% interval needs a scale factor kappa = 1.039 [0.996, 1.075] overall, 1.054 [0.957, 1.263] in the whole "stressed" class and 1.037 [0.919, 1.222] in the "Nifty-drawdown prong only" subtype (145 scored sessions; 165 sessions in 31 spells in the regime table); so at most a 4-5% widening, inside the noise. The 50% body is narrow overall (kappa50 = 1.098 [1.024, 1.157]) and in the stressed class (1.262 [1.141, 1.390]; Kupiec p 0.0015, Holm within family 0.041, whole registry 0.34). The "broadly unchanged" event |R| < 0.25 sigma has realised frequency 0.256 [0.237, 0.277] overall and 0.230 [0.191, 0.275] in stressed sessions versus 0.238 stated in the frozen record: not overstated.
3. **Gap rule (only usable if the 09:15 open were known; it is not at the cutoff).** 1 sigma60 = 2.153% (Rs 73.5 from P0; 0.5 sigma = Rs 36.5; 0.25 sigma = Rs 18.2). After a gap-up of at least 0.5 sigma the intraday move had the gap's sign 32.6% of the time before 2024-07 (n 230), 69.4% from 2024-07 to 2026-08-02 (n 36), 50% since the closing auction (n 4). Down-gaps: 45.1% (n 82), 46.2% (n 26), 71% (n 7). The sign flip for up-gaps is real as a difference between periods (Fisher p 6e-5, whole-registry Holm 0.015) but it is not a stable predictor and the auction-era sample is too small to say anything.
4. **Breakouts and liquidity do not change tomorrow's forecast.** 13 Oct was not a breakout (close 2.26% below the prior-20-day adjusted high, about Rs 3,452.7; 11.79% above the 20-day low) and turnover was typical (relative volume 0.735, turnover z +0.08, Rs 1,377 crore).

## 2. Protocol in one page

* Returns, G, I, R, bonus adjustment, P0: as in the v2 brief (`common.targets`). sig = RMS of the last 60 R. Gap size gz = G / sig (sig known when the session opens). "Ex-ante" states use sessions up to the previous close only.
* Partitions (state at close k applies to session k+1). PV: expanding terciles of sig (min 250 obs). PN: Nifty 50 above/below its 200-session average. PD: BSE drawdown from its 250-session closing high, near-high > -10%, pullback (-20%, -10%], deep <= -20%. RG (4-class regime, Part 5).
* One registry; every test belongs to a family; Holm and Benjamini-Hochberg adjusted p-values are computed within each family and across the whole registry. "Supported" below means whole-registry Holm < 0.05; "supported within family" means family Holm < 0.05; "FDR-suggestive" means whole-registry BH < 0.10.
* Counts: 259 tests (P1_acf 12, P1_vr 24, P1_wf 20, P2_gap 17, P2_gapregime 15, P2_flip 8, P3_breakout 54, P3_alldayterc 36, P3_holdout 12, P3_holdout_alldayterc 6, P4_liq 16, P5_calib 32, P6_current 4, X_posthoc 3); 28 further tests were specified but not run because a cell had too few observations (listed in `multiple_testing.skipped`). Raw p < 0.05: 73 (about 13 expected by chance); whole-registry Holm < 0.05: 16; whole-registry BH < 0.10: 57.
* Whole-registry Holm survivors: lag-1 autocorrelation (all sessions, deep-drawdown cell), regime-conditional 1-day walk-forward (RC_PD), the up-gap EARLY-vs-L1 flip, the seven volume-|return| rank correlations, the turnover-z walk-forward for |R|/sigma, and four S0 (untimed benchmark) coverage failures in the stressed class.
* Status labels follow fixed rules in the header: `validated_out_of_sample` needs pooled OOS R2 > 0, within-family Holm < 0.05, R2 > 0 in both halves, in Final and after dropping the five largest |R|; otherwise `not_found`.

## 3. Part 1: autocorrelation, variance ratios, momentum and reversal

### 3.1 Lag-1 autocorrelation and variance ratios by ex-ante regime (in-sample, `descriptive_only`)

Rc = R minus its mean; cell = sessions whose state at the previous close equals the cell. VR(q) = sum of squared q-day sums / sum of q-day sums of squares, null 1. 95% CIs are percentile intervals of the stationary bootstrap; p is Wald-type from the bootstrap SE. Sample 2017-02-06 to 2026-10-13.

| cell | n | lag-1 rho [95% CI] | p | Holm fam | Holm all | VR(5) [CI] | p | Holm all | VR(20) [CI] | p | Holm all |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 2387 | +0.105 [+0.049, +0.155] | 0.0001 | 0.001 | 0.025 | 1.21 [1.10, 1.33] | 0.0004 | 0.086 | 1.36 [1.13, 1.63] | 0.0052 | 1.000 |
| PV:lo | 136 | +0.165 [+0.030, +0.297] | 0.018 | 0.107 | 1.000 | 1.33 [0.98, 1.59] | 0.032 | 1.000 | 3.14 [1.36, 4.74] | 0.018 | 1.000 |
| PV:mid | 680 | +0.074 [+0.009, +0.136] | 0.024 | 0.121 | 1.000 | 1.00 [0.84, 1.14] | 0.974 | 1.000 | 1.14 [0.91, 1.37] | 0.218 | 1.000 |
| PV:hi | 1263 | +0.112 [+0.041, +0.174] | 0.0012 | 0.012 | 0.272 | 1.28 [1.13, 1.43] | 0.0003 | 0.062 | 1.37 [1.07, 1.74] | 0.026 | 1.000 |
| PN:below | 551 | +0.124 [+0.038, +0.198] | 0.0020 | 0.018 | 0.464 | 1.35 [1.10, 1.57] | 0.0034 | 0.774 | 1.32 [1.03, 1.63] | 0.036 | 1.000 |
| PN:above | 1640 | +0.097 [+0.026, +0.163] | 0.0063 | 0.050 | 1.000 | 1.16 [1.03, 1.29] | 0.020 | 1.000 | 1.37 [1.10, 1.71] | 0.016 | 1.000 |
| PD:near_high | 698 | +0.130 [+0.031, +0.218] | 0.0066 | 0.050 | 1.000 | 1.22 [1.06, 1.40] | 0.013 | 1.000 | 1.24 [0.96, 1.56] | 0.111 | 1.000 |
| PD:pullback | 597 | -0.026 [-0.115, +0.061] | 0.567 | 1.000 | 1.000 | 1.14 [0.95, 1.34] | 0.162 | 1.000 | 1.35 [0.98, 1.84] | 0.116 | 1.000 |
| PD:deep | 973 | +0.162 [+0.093, +0.221] | <1e-4 | <1e-4 | 0.0003 | 1.28 [1.10, 1.50] | 0.0040 | 0.898 | 1.57 [1.20, 2.01] | 0.0057 | 1.000 |

Between-regime differences (the thing a "regime-dependent momentum" claim needs): PV hi minus lo -0.053 [-0.211, +0.103] (p 0.50); PN above minus below -0.028 [-0.128, +0.078] (p 0.61); PD near-high minus deep -0.031 [-0.144, +0.084] (p 0.59). VR(5) differences: -0.05, -0.20, -0.06 (p 0.75, 0.15, 0.62); VR(20): -1.76 [-3.39, +0.05] (p 0.054), +0.05, -0.33 (p 0.79, 0.21). **No regime-dependence of autocorrelation is established**; the pooled positive autocorrelation is. Non-overlapping windows: about 476 (q = 5) and 118 (q = 20) in the "all" cell, so VR(20) rests on about 118 independent windows. Expanding terciles are unbalanced in this sample (out-of-sample sessions: 2.7% lo, 33.6% mid, 63.7% hi volatility) because BSE's volatility level rose after 2018; the "lo" cell is only 136 pairs.

What the positive autocorrelation is made of (post-hoc X1/X2, descriptive, no claim of significance):

* By era: EARLY (to 2024-06-28, n 1,821) +0.142 [+0.092, +0.190]; 2024-07-01 to 2026-08-02 (n 516) +0.036 [-0.085, +0.150]; closing-auction era (n 50) -0.007 [-0.388, +0.226]. By calendar year +0.06, +0.10, +0.15, +0.11, +0.10, +0.15, +0.22 (2017-2023), -0.01 (2024), +0.08 (2025), +0.10 (2026).
* Nifty 50 on the same sessions: -0.043 [-0.115, +0.048]; so the pattern is not a market-wide one.
* Decomposition of the lag-1 autocovariance of R = G + I: 51.6% comes from corr(G_k, I_{k-1}) = +0.138 [+0.090, +0.189] (the previous day's open-to-close move continues into the next opening gap), 18.4% from corr(I_k, G_{k-1}) = +0.049, 28.4% from corr(I_k, I_{k-1}) = +0.035 (CI includes 0), 1.6% from corr(G_k, G_{k-1}) = +0.009. The open-to-open return (I_{k-1} + G_k, which never uses a close) has lag-1 autocorrelation +0.001 [-0.052, +0.050].
* Reading: before 2026-08-03 the close is a 30-minute VWAP, and a VWAP close lags the last traded price, so part of the last half hour's move shows up in the next gap. The open-to-open result is consistent with a close-definition component, but daily data cannot separate that from genuine overnight continuation, and the auction era has too few sessions (50) to test it. This is an observation, not a demonstrated mechanism.

### 3.2 Walk-forward time-series momentum and 1-day reversal against the expanding mean

OOS sessions 2019-02-15 to 2026-10-13 (n 1,888), models refit every session on pairs j < k only; benchmark = expanding mean of R. U = unconditional OLS on one signal; RC = same OLS fitted separately by ex-ante state (min 100 training pairs per cell, else benchmark forecast). The v1 ridge/logit features are not refit. Status column applies the fixed rule. The last column is the model's forecast of tomorrow's mean R (benchmark +0.140%).

| signal | model | OOS R2 | 1st half | 2nd half | Final 2025-07+ | ex top-5 abs R | CW t | CW p (1-sided) | Holm fam | Holm all | next-session mean % | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| m1 (yesterday's R) | U | +0.95% | +1.42% | +0.60% | -0.68% | +0.93% | +3.52 | 0.0002 | 0.004 | 0.052 | +0.269 | not_found |
| m1 | RC_PV | +0.92% | +1.07% | +0.82% | -0.37% | +0.90% | +3.42 | 0.0003 | 0.006 | 0.074 | +0.128 | not_found |
| m1 | RC_PN | +0.58% | +0.71% | +0.48% | -1.07% | +0.50% | +3.21 | 0.0007 | 0.011 | 0.156 | +0.308 | not_found |
| m1 | RC_PD | +1.00% | +1.24% | +0.82% | -0.23% | +0.90% | +3.66 | 0.0001 | 0.003 | 0.031 | +0.245 | not_found |
| m5 | U | +0.30% | +0.77% | -0.06% | -0.23% | +0.20% | +2.22 | 0.013 | 0.171 | 1.000 | +0.183 | not_found |
| m5 | RC_PV | +0.26% | +0.46% | +0.11% | +0.12% | +0.16% | +2.41 | 0.0079 | 0.110 | 1.000 | +0.051 | not_found |
| m5 | RC_PN | -0.15% | +0.01% | -0.27% | -0.64% | -0.37% | +1.87 | 0.030 | 0.332 | 1.000 | +0.235 | not_found |
| m5 | RC_PD | +0.33% | +0.60% | +0.13% | +0.01% | +0.22% | +2.53 | 0.0057 | 0.086 | 1.000 | +0.148 | not_found |
| m20 | U | +0.20% | -0.07% | +0.40% | +0.10% | +0.27% | +1.74 | 0.041 | 0.366 | 1.000 | +0.109 | not_found |
| m20 | RC_PV | +0.15% | -0.32% | +0.51% | -0.37% | +0.15% | +1.92 | 0.028 | 0.332 | 1.000 | +0.025 | not_found |
| m20 | RC_PN | -0.14% | -0.64% | +0.24% | +0.04% | -0.12% | +1.29 | 0.098 | 0.684 | 1.000 | +0.169 | not_found |
| m20 | RC_PD | -0.29% | -0.79% | +0.08% | -0.89% | -0.32% | +1.22 | 0.110 | 0.684 | 1.000 | +0.026 | not_found |
| m60 | U | +0.03% | -0.25% | +0.23% | -0.54% | +0.08% | +1.08 | 0.140 | 0.693 | 1.000 | +0.077 | not_found |
| m60 | RC_PV | -0.08% | -0.57% | +0.28% | -0.60% | -0.08% | +1.09 | 0.139 | 0.693 | 1.000 | +0.021 | not_found |
| m60 | RC_PN | -0.34% | -1.08% | +0.22% | -0.77% | -0.33% | +0.76 | 0.224 | 0.693 | 1.000 | +0.140 | not_found |
| m60 | RC_PD | -0.62% | -1.28% | -0.12% | -1.49% | -0.67% | +0.37 | 0.355 | 0.710 | 1.000 | -0.003 | not_found |

Signal values now: m1 = +1.348%, m5 = +2.108%, m20 = -0.255%, m60 = -5.935%. Pesaran-Timmermann sign association (OOS): m1 agreement 53.9% vs 50.0% expected, z +3.41, p 0.0006 (Holm within family 0.011, whole registry 0.154); m5 50.3% (p 0.78); m20 52.5% (p 0.029, Holm 0.33); m60 52.1% (p 0.052, Holm 0.42). Cell detail for RC models (OOS R2 by cell): m1 by drawdown state: near-high +1.37% (n 685), pullback -0.62% (n 496), deep +1.53% (n 707); by Nifty state: below +0.23%, above +0.74%.

Reading. (i) The only horizon with any out-of-sample content is one day, and its sign is momentum, not reversal (slope positive; PT agreement above 50%). (ii) It is small (R2 about 1%, a 0.05-sigma shift for today's input), decays in the Final window, is positive in 7 of 8 calendar years (R2 by year 2019-2026: +1.75%, +0.95%, +1.32%, +1.91%, +4.90%, -1.95%, +0.46%, +0.85%) and is concentrated in drawdown states "near-high" and "deep" with a negative R2 in "pullback". (iii) It matches v1's pattern for ridge/logit (Dev R2 +1.4%, Val -2.5%, Final -1.5%), now with one transparent feature, which confirms rather than extends v1's "no validated directional skill" (the pooled result is borderline-significant but unstable). (iv) The post-hoc autocovariance decomposition in 3.1 says the effect lives in the G_k vs I_{k-1} link, which is exactly where a VWAP-close construction would act. The 5-, 20- and 60-day signals and all 12 regime-conditional versions of them show no usable skill (best +0.33% R2, Holm within family >= 0.086). **Validation status: `not_found` for every signal and model under the fixed rule.**

## 4. Part 2: opening-gap continuation vs reversal

Cells by |gz| = |G| / sig: S [0.25, 0.5), M [0.5, 1), L >= 1; ML = |gz| >= 0.5. Continuation C = 1 when sign(I) = sign(G). Null: circular-shift permutation of I inside the period, which keeps P(I>0) and the gap signs (the null differs by direction because the intraday drift is negative: pi0 = 0.41 for up-gaps, 0.59 for down-gaps in the full sample). c - pi0 in percentage points; CI is a stationary-bootstrap percentile interval; p two-sided (empirical shift p if n < 30, else normal approximation from the shift distribution). Periods: EARLY = before 2024-07-01 (p* not registered; used only for the sign), FULL = k >= 60 (from 2017-05-08, n 2,328), POST = 2024-07-01 onwards (n 566), AUC = closing-auction era (n 50). Brackets give Holm within family / whole registry for the 9 registered cells per period.

| cell | EARLY n, c, c-pi0, p* | FULL n, c, c-pi0, p [Holm fam / all] | POST n, c, c-pi0, p [Holm fam / all] | AUC n, c |
|---|---|---|---|---|
| up_S | 346, 0.370, -1.9, 0.428 | 422, 0.403, -0.9, 0.682 [1.000 / 1.000] | 76, 0.553, +6.7, 0.201 [1.000 / 1.000] | 9, 0.44 |
| up_M | 176, 0.301, -8.8, 0.031 | 204, 0.343, -6.9, 0.069 [0.891 / 1.000] | 28, 0.607, +12.1, 0.236 [1.000 / 1.000] | 3, 0.33 |
| up_L | 54, 0.407, +1.9, 0.795 | 66, 0.485, +7.3, 0.270 [1.000 / 1.000] | 12, 0.833, +35.0, not tested (n<15) | 1, 1.00 |
| up_all | 576, 0.352, -3.6, 0.060 | 692, 0.393, -1.9, 0.314 [1.000 / 1.000] | 116, 0.595, +10.9, 0.0070 [0.112 / 1.000] | 13, 0.46 |
| down_S | 87, 0.529, -8.3, 0.105 | 114, 0.509, -7.9, 0.076 [0.908 / 1.000] | 27, 0.444, -7.0, 0.537 [1.000 / 1.000] | 2, 0.50 |
| down_M | 56, 0.429, -18.3, 0.0043 | 83, 0.458, -13.0, 0.013 [0.195 / 1.000] | 27, 0.519, +0.4, 1.000 [1.000 / 1.000] | 6, 0.67 |
| down_L | 26, 0.500, -11.1, 0.302 | 32, 0.500, -8.8, 0.311 [1.000 / 1.000] | 6, 0.500, -1.6, not tested | 1, 1.00 |
| down_all | 169, 0.491, -12.1, 0.0009 | 229, 0.489, -9.9, 0.0017 [0.030 / 0.404] | 60, 0.483, -3.1, 0.613 [1.000 / 1.000] | 9, 0.67 |
| all (abs gz >= 0.25) | 745, 0.384, -5.5, 0.0028 | 921, 0.417, -3.9, 0.025 [0.344 / 1.000] | 176, 0.557, +6.1, 0.101 [1.000 / 1.000] | 22, 0.55 |
| up_ML (not registered alone) | 230, 0.326, -6.3, 0.090 | 270, 0.378, -3.5, 0.325 | 40, 0.675, +19.0, 0.011 | 4, 0.50 |
| down_ML | 82, 0.451, -16.1, 0.0027 | 115, 0.470, -11.9, 0.0088 | 33, 0.515, +0.0, 0.996 | 7, 0.71 |
| pooled_ML | 312, 0.359, -8.9, 0.0048 | 385, 0.405, -6.0, 0.032 | 73, 0.603, +10.4, 0.064 | 11, 0.64 |

Findings.
* **Before 2024-07 gaps faded** (continuation below the shift null): strongest for down-gaps (down_all -12.1 pp, n 169; down_ML -16.1 pp, n 82) and for ML gaps pooled (-8.9 pp, n 312). Across the full sample only down_all survives within-family Holm (0.030; whole registry 0.404). **Since 2024-07 up-gaps continued** (up_all +10.9 pp, n 116, p 0.007; up_ML +19.0 pp, n 40) but this is not significant after adjustment (Holm within family 0.112), and down-gaps show no effect (-3.1 pp). So the early-period fade rule fails the status test in POST (no cell has the early sign and adjusted p < 0.05; for up-gaps the sign is opposite and not adjusted-significant): `not_found` out of sample; the in-sample tables are `descriptive_only`.
* **Closing-auction era (2026-08-03 onwards): untestable.** 50 sessions, 22 with |gz| >= 0.25, 11 with |gz| >= 0.5; every cell has n <= 13 except "all" (n 22, c 0.545, p 0.84). Estimates exist in the JSON but carry no inference.
* **Mean intraday move in the gap direction** (sign(G) x I): FULL -0.22% for ML gaps pooled; POST +0.75% for up_ML (n 40) and -0.67% for down_ML (n 33), i.e. down-gap days kept falling in POST on average but with a continuation rate of 51.5% (a few large moves, not a hit-rate effect).

### 4.1 Formal test of the sign flip

| cell (gz thresholds) | A vs B | n_A / n_B | rate A | rate B | diff [bootstrap CI] | Fisher p | Holm fam | Holm all |
|---|---|---|---|---|---|---|---|---|
| up_ML (gz >= 0.5) | EARLY vs L1 | 230 / 36 | 0.326 | 0.694 | -36.8 pp [-53.7, -18.9] | 6e-5 | 0.0005 | 0.015 |
| down_ML (gz <= -0.5) | EARLY vs L1 | 82 / 26 | 0.451 | 0.462 | -1.0 pp [-24.8, +23.7] | 1.000 | 1.000 | 1.000 |
| pooled_ML | EARLY vs L1 | 312 / 62 | 0.359 | 0.597 | -23.8 pp [-37.0, -9.3] | 0.0006 | 0.004 | 0.147 |
| pooled_ML | L1 vs AUC | 62 / 11 | 0.597 | 0.636 | -4.0 pp [-28.6, +26.5] | 1.000 | 1.000 | 1.000 |
| pooled_ML | EARLY vs AUC | 312 / 11 | 0.359 | 0.636 | -27.7 pp [-49.8, +1.2] | 0.107 | 0.534 | 1.000 |

Four further comparisons involving the auction era were not run (min n < 8: up_ML AUC n 4, down_ML AUC n 7).

* **Up-gap flip: supported** as a difference in raw continuation rates (whole-registry Holm 0.015). **Down-gap flip: absent** (45.1% vs 46.2%). Pooled ML: supported within family (0.004), not across the registry (0.147).
* The raw comparison mixes two things: the unconditional intraday drift also moved (P(I>0) over all days: 0.309 in 2017, 0.278 in 2018, 0.52 in 2023, 0.50 in 2026; 0.486 in POST), so the shift-null pi0 rose from 0.389 to 0.488 for up-gaps. **Drift-adjusted (post-hoc X3):** up_ML c - pi0 went from -6.3 pp (EARLY) to +20.7 pp (2024-07 to 2026-08-02), difference +27.0 pp [+9.0, +43.9], p 0.0022 (Holm within X_posthoc 0.007, whole registry 0.51); pooled_ML -8.9 to +9.9 pp, difference +18.7 pp [+4.2, +31.9], p 0.006 (whole registry 1.0); down_ML -16.1 to -5.1 pp, difference +10.9 pp [-13.8, +34.7], p 0.38.
* **Continuous-slope version does not reject:** I = a + b G, slope b = -0.160 (se 0.088) before 2024-07, +0.043 (se 0.103) from 2024-07 to 2026-08-02, +0.067 (se 0.272) in the auction era; slope change at 2024-07 +0.204 (se 0.136, p 0.133); change at the auction +0.023 (se 0.291, p 0.94). **Unknown-break sup-Wald** (15% trimming, wild bootstrap B 1,999): supF 9.60, 95% bootstrap critical value 9.88, p 0.0585, best break date 2021-03-26 (not 2024-07).
* Calendar-year continuation after up-gaps of >= 0.5 sigma (n): 2017 0.21 (24), 2018 0.25 (80), 2019 0.31 (35), 2020 0.44 (27), 2021 0.33 (21), 2022 0.37 (19), 2023 0.65 (17), 2024 0.40 (15), 2025 0.60 (15), 2026 0.82 (17). After down-gaps: 0.29, 0.42, 0.64, 0.61, 0.33, 0.44, 0.33, 0.44, 0.50, 0.47. The drift is gradual and noisy, not a clean step at 2024-07.
* **Verdict.** The sign change for up-gaps is real in the data (period difference, not a fluke at the whole-registry level for the Fisher test) but its form is a drift in the intraday return level plus a gap-conditional shift of about +20 pp that is only family-level significant; the two continuous-time tests do not reject. It is `descriptive_only`; it is not an out-of-sample validated rule in either direction.

### 4.2 Gap x regime (ML gaps pooled over direction; family P2_gapregime)

| period | state | n | c | pi0 | c-pi0 (pp) | p | Holm fam | Holm all |
|---|---|---|---|---|---|---|---|---|
| FULL | calm | 139 | 0.360 | 0.468 | -10.8 | 0.011 | 0.167 | 1.000 |
| FULL | trending | 74 | 0.419 | 0.451 | -3.2 | 0.586 | 1.000 | 1.000 |
| FULL | event_driven | 36 | 0.500 | 0.470 | +3.0 | 0.726 | 1.000 | 1.000 |
| FULL | stressed | 81 | 0.531 | 0.484 | +4.7 | 0.378 | 1.000 | 1.000 |
| FULL | PN above 200d | 254 | 0.374 | 0.458 | -8.4 | 0.019 | 0.259 | 1.000 |
| FULL | PN below 200d | 109 | 0.505 | 0.483 | +2.1 | 0.640 | 1.000 | 1.000 |
| POST | calm | 31 | 0.484 | 0.498 | -1.5 | 0.874 | 1.000 | 1.000 |
| POST | stressed | 26 | 0.654 | 0.499 | +15.5 | 0.119 | 1.000 | 1.000 |
| POST | PN below 200d | 44 | 0.636 | 0.499 | +13.7 | 0.066 | 0.787 | 1.000 |

No regime cell is significant after adjustment (lowest raw p 0.011). Fading is concentrated in calm and above-200-day states in the full sample and continuation in stressed/below-200-day states in POST, but the contrasts are not tested to be different and the POST cells have 6 to 44 observations. Cells with n < 15 (POST trending n 10, event-driven n 6) were not tested. `descriptive_only` / `not_found`.

## 5. Part 3: breakouts, relative volume and delivery

Up-breakout: adjusted close above the highest adjusted intraday high of the previous 20 sessions; down-breakout: below the lowest adjusted low (k >= 20). n = 158 up and 165 down. F_h = log return from the breakout close to h = 1, 5, 10 sessions later (the pre-2026-08-03 close is a VWAP, so F_h is a close-to-close statistic, not an executable one). Excess = mean F_h on breakout days minus mean F_h on days that are neither up- nor down-breakouts (OLS, HAC lag h+5). n_clusters = distinct episodes (flags within h sessions merged). n_eff = n x var_iid/var_HAC capped at n. Sample k >= 20 to 2026-10-13 minus the last h sessions.

| direction | h | n days | n clusters | n_eff (HAC) | mean F breakout % | mean F non-breakout % | mean F all days % | excess % [95% CI] | p | Holm fam | Holm all | sign |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| up | 1 | 158 | 103 | 87.1 | +0.56 | +0.14 | +0.15 | +0.41 [-0.15, +0.98] | 0.152 | 1.000 | 1.000 | persistence |
| up | 5 | 158 | 67 | 97.8 | +0.84 | +0.80 | +0.73 | +0.05 [-1.28, +1.37] | 0.947 | 1.000 | 1.000 | persistence |
| up | 10 | 158 | 50 | 108.8 | +1.77 | +1.60 | +1.46 | +0.17 [-1.64, +1.98] | 0.854 | 1.000 | 1.000 | persistence |
| down | 1 | 165 | 96 | 165.0 | -0.17 | +0.14 | +0.15 | -0.32 [-0.68, +0.05] | 0.088 | 1.000 | 1.000 | persistence |
| down | 5 | 165 | 64 | 78.4 | -0.17 | +0.80 | +0.73 | -0.97 [-2.45, +0.51] | 0.198 | 1.000 | 1.000 | persistence |
| down | 10 | 164 | 44 | 49.3 | -0.63 | +1.60 | +1.46 | -2.23 [-4.92, +0.46] | 0.104 | 1.000 | 1.000 | persistence |

Share of breakout days whose F_h has the breakout's sign (all days / non-breakout days in brackets): up h1 53.8% (48.0 / 47.8), h5 53.2% (50.3 / 50.4), h10 55.7% (50.6 / 50.8); down h1 54.5% (51.8 / 52.1), h5 53.9% (49.7 / 49.6), h10 56.7% (49.4 / 49.2). All excesses have the persistence sign and none is significant.

* **Conditioning on volume and delivery.** Up-breakouts happen on high volume (median relative volume 2.11 vs 0.80 on all days; 54% above 2x), down-breakouts do not (median 0.97; 6.7% above 2x). Delivery % on breakout days: up-breakouts mostly in the low tercile (108 of 129 classified), down-breakouts mostly in the high tercile (38 of 79) of the all-day distribution; the delivery figure for 2026-10-13 is not in the repo (so today could not be classified even if it were a breakout). Hence the all-day terciles are degenerate for the contrast (amendment A2). Within-breakout terciles (cut points from pre-2024-07 breakouts: RV up 2.06 / 3.95, down 0.83 / 1.13; delivery % up 25.1 / 32.2, down 49.4 / 56.2) give high-minus-low contrasts of +0.58% (h1), +0.87% (h5), +1.25% (h10) for up-breakouts on relative volume and +0.55%, +0.11%, +0.89% for down-breakouts, all with p >= 0.19 (Holm within family 1.0); delivery contrasts all with p >= 0.25. The three raw p < 0.05 in the superseded all-day family (down-breakouts in the lowest relative-volume tercile, n 14: h1 p 0.0069, h10 p 0.0197; a contrast p 0.018) have Holm-within-family 0.248 to 0.669.
* **Sub-periods (descriptive).** Down-breakout h1 excess was -0.51% (se 0.18, n 138) before 2024-07 and +0.72% (se 0.56, n 27) after; up-breakout h10 +1.19% before, -2.29% after.
* **Chronological holdout with fixed rules** (Dev = windows ending before 2024-07-01; sign taken from Dev, one-sided test on the holdout; 12 registered tests plus 6 superseded): the Dev effect is persistence in all cells (strongest: down-breakouts h1, Dev -0.51%, p 0.005), the holdout has the opposite sign in 10 of 12 cells and never reaches p < 0.05 (smallest one-sided p: 0.277); all 12 are `not_found`. Holdout n is 5 to 53 (effective n 3.5 to 53).
* **Verdict: `not_found`.** No breakout pattern, with or without volume or delivery confirmation, is validated; the descriptive Dev-period persistence for down-breakouts does not survive 2024-07 onwards. Today (2026-10-13) is not a breakout.

## 6. Part 4: liquidity and the volume-return relationship

TZ = z-score of ln rupee turnover against the previous 60 sessions (clipped +-3). Amihud A = 100 x |R| / turnover (% per Rs crore), A20 its 20-day mean, IL state = expanding terciles of ln A20 (liquid = low), TO state = expanding terciles of 20-day turnover relative to its trailing-year median. ZA = |R| / sig.

| cell (state at previous close) | n | Spearman rho(TZ, ZA) [95% CI] | R2 (raw Pearson) | slope | Holm all |
|---|---|---|---|---|---|
| all | 2328 | 0.417 [0.383, 0.454] | 0.258 | 0.354 | <1e-4 |
| IL liquid | 1442 | 0.457 [0.417, 0.499] | 0.300 | 0.372 | <1e-4 |
| IL mid | 227 | 0.304 [0.149, 0.427] | 0.180 | 0.340 | 0.007 |
| IL illiquid | 450 | 0.372 [0.284, 0.456] | 0.205 | 0.326 | <1e-4 |
| TO low | 519 | 0.457 [0.386, 0.527] | 0.308 | 0.390 | <1e-4 |
| TO mid | 591 | 0.473 [0.397, 0.544] | 0.281 | 0.359 | <1e-4 |
| TO high | 908 | 0.446 [0.397, 0.498] | 0.285 | 0.399 | <1e-4 |

* **The volume-|return| link is strong and its strength does not change with liquidity state.** Illiquid minus liquid: -0.085 [-0.184, +0.006] (p 0.081, Holm within family 0.41); high minus low turnover: -0.010 [-0.097, +0.080] (p 0.81). The correlation is the largest effect in the registry and is a contemporaneous association (large moves and heavy turnover coincide); it carries no direction and no causal reading. The IL partition is lopsided (62% liquid / 10% mid / 19% illiquid of the 2,328 analysed sessions) because rupee turnover rose over the years, so "illiquid" means "illiquid relative to a growing history".
* **Price impact (4b).** Spearman(ln A_k, TZ_k) = -0.129 [-0.210, -0.046] overall (p 0.0026; Holm within family 0.016, whole registry 0.59); -0.167 [-0.255, -0.076] before 2024-07 (p 0.0003; whole registry 0.067); +0.043 [-0.042, +0.123] from 2024-07 (p 0.31). Amihud impact per rupee was lower on heavy-turnover days before 2024-07 and shows no relation after.
* **Volume-conditioned autocorrelation (4c).** R_k = a + b R_{k-1} + c R_{k-1} x TZ_{k-1}: b = +0.181 (se 0.035), c = -0.071 (se 0.022, p 0.0015, Holm within family 0.011, whole registry 0.36). After a day with turnover z of +2.5 the lag-1 coefficient falls to about 0 (0.181 - 0.071 x 2.5 = +0.004). The same with the Amihud z: c = +0.027 (p 0.24). Direction consistent with the textbook idea that heavy-volume days carry less continuation; association only.
* **Does turnover forecast the next day's absolute move? (4d, walk-forward).** TZ_{k-1} on |R_k|/sig: OOS R2 +0.91% (CW t 4.28, p 1e-5, Holm within family 0.0001, whole registry 0.0025) but Final-window R2 -2.50% (by year: +2.99%, -0.50%, +0.98%, +2.23%, +1.39%, +2.02%, -2.58%, -0.91% for 2019-2026) so it fails the fixed gate: `not_found`. Amihud z: R2 -0.71%. Today's TZ = +0.08, relative volume 0.735, Amihud z -0.41: the model-implied next-day |R|/sig is 0.763 vs 0.760 for the benchmark, i.e. no change.

## 7. Part 5: regimes and calibration of the v1 scale model

### 7.1 Rules (fixed before looking at outcomes; header "PART 5")

At close k: stressed if Nifty 50 is >= 10% below its 250-session high, or India VIX >= 25, or (BSE 20-day volatility percentile >= 0.90 and BSE 20-day return < 0); else event-driven if any v1 "E4" shock occurred in the last 5 sessions (|R| >= 8% or |R - beta Nifty| >= 3 residual SD); else trending if |20-day return| / (sig sqrt 20) >= 1.0; else calm (residual). Valid from 2018-03-12 (2,119 sessions). Rule components fire on 15.2% (Nifty drawdown), 6.2% (VIX >= 25), 7.7% (BSE high-vol falling), 12.9% (event window), 38.2% (trend >= 1) of valid sessions; 59 shock days in total. The four classes are mutually exclusive by priority and exhaustive.

Next-session statistics given the class at the previous close (n = sessions, spells = distinct runs):

| class | share | n | spells | mean R % | median R % | SD R % | mean abs R % | mean G % (SD) | mean I % (SD) | mean range % | P(R>0) [Wilson] | R 5% / 95% quantile % | SD of R/sig |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| calm | 47.4% | 1004 | 121 | +0.08 | -0.07 | 2.36 | 1.60 | +0.25 (0.89) | -0.16 (2.23) | 3.19 | 0.476 [0.445, 0.507] | -3.44 / +4.03 | 1.00 |
| trending | 24.2% | 513 | 106 | +0.39 | +0.04 | 2.69 | 1.82 | +0.35 (0.91) | +0.04 (2.51) | 3.54 | 0.507 [0.464, 0.550] | -3.00 / +5.27 | 1.13 |
| event_driven | 8.5% | 181 | 38 | +0.28 | +0.07 | 3.40 | 2.38 | +0.29 (1.74) | -0.01 (3.08) | 4.68 | 0.519 [0.447, 0.591] | -4.86 / +5.79 | 1.18 |
| stressed | 19.9% | 421 | 43 | +0.07 | -0.04 | 3.20 | 2.30 | +0.26 (1.60) | -0.19 (2.85) | 4.18 | 0.492 [0.444, 0.539] | -4.53 / +5.39 | 1.13 |
| all valid | | 2119 | | +0.17 | -0.04 | 2.72 | 1.86 | +0.28 (1.16) | -0.11 (2.51) | 3.60 | 0.490 [0.469, 0.512] | -3.73 / +4.76 | 1.08 |

The classes separate scale (SD 2.36% to 3.40%; gap SD 0.89% to 1.74%; range 3.2% to 4.7%) but not direction (P(R>0) 0.476 to 0.519, all CIs include 0.49). Caveats: the residual "calm" class is not low-volatility in absolute terms (mean 20-day volatility 1.99%, 40% of its sessions above the 0.667 volatility percentile), "stressed" is dominated by 43 spells (2020 alone is 46% stressed), and the event rule is reactive: of the 7 known results-reaction sessions since 2024-11, 4 were classified calm at the prior close, 2 trending, 1 event-driven, and only one (2026-02-10, +6.14%) was itself a shock day. Regime shares by year are in `part5.tables.share_by_year`.

### 7.2 Where the v1 intervals fail (`forecasts_R.csv`, 2019-02-15 to 2026-10-12, n = 1,887; regime of the previous close)

Coverage of the central 50/80/90/95% intervals with Kupiec p; in brackets Kupiec p and Holm within the 32-test calibration family (both models); kappa = scale factor that restores nominal 90% coverage (95% CI).

| model | class | n | 50% | 80% | 90% | 95% | kappa90 [CI] | P(y<q.05) / P(y>q.95) |
|---|---|---|---|---|---|---|---|---|
| S6 (frozen record's R model) | all (unregistered) | 1887 | 0.468 (p 0.005) | 0.774 (p 0.006) | 0.888 (p 0.079) | 0.942 (p 0.131) | 1.039 [0.996, 1.075] | 0.059 / 0.053 |
| S6 | calm | 881 | 0.476 (0.147; 1.00) | 0.758 (0.0025; 0.067) | 0.884 (0.127; 1.00) | 0.938 (0.103; 1.00) | 1.057 [0.994, 1.134] | 0.065 / 0.051 |
| S6 | trending | 449 | 0.481 (0.422; 1.00) | 0.804 (0.831; 1.00) | 0.889 (0.430; 1.00) | 0.947 (0.740; 1.00) | 1.031 [0.914, 1.144] | 0.049 / 0.062 |
| S6 | event_driven | 175 | 0.503 (0.940; 1.00) | 0.823 (0.443; 1.00) | 0.937 (0.081; 1.00) | 0.966 (0.313; 1.00) | 0.909 [0.744, 0.999] | 0.034 / 0.029 |
| S6 | stressed | 382 | **0.419 (0.0015; 0.041)** | 0.754 (0.028; 0.644) | 0.872 (0.076; 1.00) | 0.937 (0.268; 1.00) | 1.054 [0.957, 1.263] | 0.071 / 0.058 |
| S0 (untimed benchmark) | calm | 881 | 0.543 (0.011; 0.298) | 0.830 (0.024; 0.610) | 0.922 (0.026; 0.632) | 0.961 (0.106; 1.00) | 0.887 [0.782, 0.999] | 0.039 / 0.040 |
| S0 | trending | 449 | 0.490 (0.671; 1.00) | 0.817 (0.352; 1.00) | 0.898 (0.863; 1.00) | 0.944 (0.587; 1.00) | 1.005 [0.802, 1.203] | 0.042 / 0.060 |
| S0 | event_driven | 175 | 0.417 (0.028; 0.644) | 0.731 (0.029; 0.644) | 0.851 (0.044; 0.881) | 0.926 (0.168; 1.00) | 1.096 [0.945, 1.431] | 0.074 / 0.074 |
| S0 | stressed | 382 | 0.369 (<1e-6; <1e-4) | 0.696 (2e-6; <1e-4) | 0.825 (7e-6; 0.0002) | 0.895 (2e-5; 0.0005) | 1.35 [1.075, 1.621] | 0.094 / 0.081 |

* **Where coverage fails.** (i) The untimed benchmark S0 fails in the stressed class at all four levels (whole-registry Holm 7e-5, 4e-4, 0.0018, 0.0041); S6 repairs that (90% coverage 0.872, kappa 1.05) which is the evidence that the volatility-timing in S6 is doing real work in stress. (ii) S6's 50% body is too narrow in the stressed class (coverage 0.419, Holm within family 0.041, whole registry 0.34) and, as an unregistered pooled figure, overall (0.468; kappa50 = 1.098 [1.024, 1.157], kappa80 = 1.069 [1.012, 1.120]); the calm 80% interval is narrow (0.758, raw p 0.0025, Holm within family 0.067). (iii) Event-driven sessions are over-covered (0.937 at 90%, kappa 0.909, CI upper bound 0.999) on 175 sessions. (iv) Tail balance is slightly lopsided: S6 breaches the lower 5% quantile 5.9% overall (7.1% stressed, 6.5% calm) and the upper one 5.3%. (v) The 90% and 95% levels are statistically compatible with nominal in every class. Pinball loss S6 / S0 = 0.973 overall (0.983 calm, 0.968 trending, 0.975 event, 0.961 stressed).
* By v1 period, S6 90% coverage: 0.884 (Dev, n 1,322), 0.867 (Val 2024-07 to 2025-06, n 248), 0.918 (Final 2025-07+, n 317).
* Status: S6 stressed 50% coverage `contradicted` (claim "calibrated in this regime" rejected at within-family Holm 0.041, not at the whole-registry level); all other S6 cells `descriptive_only` (non-rejection is not proof; power to detect 2-3 pp coverage errors in 175-450 sessions is low). S0 stressed: `contradicted` at the whole-registry level.

## 8. Part 6: the regime at the 2026-10-13 close and what history says about the next day

* **Regime: stressed**, through the first prong only: Nifty 50 22,721.95 vs 250-day closing high 26,328.55 (2026-01-02) = -13.70%; below its 200-day average (24,232.79; PN "below"); India VIX 14.12 (prong at 25); BSE 20-day volatility percentile 0.557 (prong at 0.90 with a falling 20-day return; BSE 20-day return -0.25%); trend statistic tau = 0.026 (threshold 1.0); no shock day in the last five sessions. Other states: PV "mid", PD "deep" (BSE -23.34% from its 250-day closing high 4,403.3 of 2026-05-26 in bonus-adjusted terms). The session itself: R +1.35%, G +0.05%, I +1.29%, relative volume 0.735.
* **Historical next-day distribution in the "stressed" class** (n 421 sessions, 43 spells, from 2018-03-12) against all 2,119 valid sessions: SD of R 3.20% vs 2.72% (log ratio +0.162 [+0.026, +0.273], p 0.0088, Holm within family 0.026, whole registry 1.0); mean |R| 2.30% vs 1.86% (difference +0.44 pp [+0.17, +0.72], p 0.0014, within family 0.006, whole registry 0.34); mean R +0.07% vs +0.17% (difference -0.10 pp [-0.44, +0.26], p 0.58); P(R>0) 0.492 vs 0.490 (difference +0.1 pp [-4.9, +4.9], p 0.96). Quantiles of R in the class with 95% bootstrap CI: 5% -4.53% [-5.76, -3.56] (Rs 3,226), 25% -1.78% [-2.09, -1.33], 50% -0.04% [-0.42, +0.16], 75% +1.69% [+1.19, +2.18], 95% +5.39% [+4.30, +6.14] (Rs 3,562).
* **These raw numbers overstate today's scale**, because the class is dominated by high-volatility episodes (mean 20-day volatility 3.0%, mean VIX 23.1), while today's volatility is mid-range (sig60 2.15%, vol20 2.34%) and VIX 14.1. The relevant subset (post-hoc X6: stressed through the Nifty-drawdown prong only, VIX < 25, no BSE high-vol decline; n 165 sessions, 31 spells): SD of R 2.79%, mean |R| 2.13%, mean R -0.10%, P(R>0) 0.509 [0.433, 0.584], 5% / 95% quantiles -4.93% / +3.87%; the other stress sessions (n 256) have SD 3.44%. S6's own mean sigma in the Nifty-drawdown-only subset was 3.07% against a realised SD of 2.94% (90% coverage 0.883, kappa 1.037 [0.919, 1.222]), so S6 already tracked that subset; tomorrow's S6 sigma is 2.478%.
* **Reading for the forecast.** The regime label adds no directional information (P(R>0) is indistinguishable from the unconditional 0.49) and adds scale information only through quantities S6 already uses; the empirical correction to S6 in this regime is a factor of about 1.04-1.05 on the 90% interval (CI includes 1) and about 1.10-1.26 on the 50% body. If the v2 write-up reports a 50% interval, widening it by 10% is the data-supported hedge; the 90% interval (Rs 3,247 to 3,508) needs at most +4% and the evidence does not require it.

## 9. Pattern register

Status vocabulary as in the brief. "Eff. n" is given where observations overlap. Adjusted p-values from the registry: Holm within family / whole registry.

| ID | pattern (association only) | definition | n (eff. n) | period | benchmark | estimate [95% CI] | exceptions / sub-periods | adj. p | status | effect on the 2026-10-14 forecast |
|---|---|---|---|---|---|---|---|---|---|---|
| P-01 | daily R is positively autocorrelated at lag 1 | corr(Rc_k, Rc_{k-1}) | 2,387 pairs | 2017-02-06 to 2026-10-13 | 0; Nifty 50 -0.043 | +0.105 [+0.049, +0.155] | era: +0.142 / +0.036 / -0.007 (n 50); 2024 -0.01; pullback state -0.026; open-to-open +0.001; 52% of autocovariance is G_k x I_{k-1} | 0.001 / 0.025 | descriptive_only | none (see P-03) |
| P-02 | multi-day variance exceeds the random-walk scaling | VR(q), windows starting after the state is known | 2,383 (about 476 non-overlap) q=5; 2,368 (about 118) q=20 | same | 1 | VR5 1.21 [1.10, 1.33]; VR20 1.36 [1.13, 1.63] | not different by regime (differences p >= 0.054); VR20 PV-lo 3.14 on 136 windows | 0.008 / 0.086 (VR5); 0.10 / 1.0 (VR20) | descriptive_only | none (one-day horizon) |
| P-03 | yesterday's return predicts today's (momentum) | walk-forward OLS vs expanding mean | 1,888 OOS sessions | 2019-02-15 to 2026-10-13 | expanding mean | OOS R2 +0.95% (CW t 3.52); PT agreement 53.9% | Final window -0.68%; 2024 -1.95%; "pullback" cell -0.62% | 0.004 / 0.052 (U); 0.003 / 0.031 (RC_PD) | not_found (fails Final-window gate) | mean +0.27% vs +0.14% (0.05 sigma): ignore, keep L0 |
| P-04 | 5/20/60-day time-series momentum | same, signals m5, m20, m60 | 1,888 | same | expanding mean | R2 +0.30%, +0.20%, +0.03% | 12 regime-conditional versions: -0.62% to +0.33% | >= 0.086 / 1.0 | not_found | none |
| P-05 | gaps faded before 2024-07 | continuation rate vs circular-shift null | e.g. down_all 169; pooled_ML 312 | to 2024-06-28 | shift null (pi0 0.41-0.61) | down_all 0.491 vs 0.612 (-12.1 pp); pooled_ML 0.359 vs 0.448 (-8.9 pp) | up-gaps S/L cells about null; p* unregistered | FULL down_all 0.030 / 0.40 | descriptive_only; early-period fade rule out of sample: not_found | none (open unknown at cutoff) |
| P-06 | up-gaps continue since 2024-07 | same | up_all 116; up_ML 40 | 2024-07-01 to 2026-10-13 | shift null | up_all +10.9 pp; up_ML +19.0 pp [c 0.675, CI 0.51-0.83] | down-gaps -3.1 pp; AUC era n 4-13 | 0.112 / 1.0 | not_found | none |
| P-07 | the up-gap sign flips between periods | Fisher; drift-adjusted bootstrap; slope interaction; sup-Wald | 230 vs 36 up_ML | EARLY vs 2024-07..2026-08-02 | equal rates | 32.6% vs 69.4% (-36.8 pp [-53.7, -18.9]); drift-adjusted +27.0 pp [+9.0, +43.9] | down-gap flip absent (45.1% vs 46.2%); slope change p 0.13; sup-Wald p 0.0585 at 2021-03-26; AUC era untestable (50 sessions) | 0.0005 / 0.015 (Fisher); 0.007 / 0.51 (drift-adj.) | descriptive_only | none |
| P-08 | gap behaviour depends on regime | continuation of ML gaps by state | 6 to 254 per cell | FULL, POST | shift null | FULL calm -10.8 pp, above-200d -8.4 pp; POST stressed +15.5 pp | cells n < 15 untested | >= 0.167 / 1.0 | not_found | none |
| P-09 | breakouts persist (up) or reverse | excess F_h vs non-breakout days | up 158 (50-103 clusters); down 165 (44-96) | k >= 20 to 2026-10-13 | non-breakout and all days | up +0.41 / +0.05 / +0.17%; down -0.32 / -0.97 / -2.23% (h 1/5/10) | persistence sign in Dev, reversed in holdout (down h1 -0.51% to +0.72%) | all 1.0 | not_found | 13 Oct not a breakout: none |
| P-10 | volume confirmation / delivery conditions breakouts | within-breakout terciles (Dev cut points) | 24 to 76 per tercile | same | low tercile | hi-lo up RV +0.58 / +0.87 / +1.25%; delivery +0.15 / +0.11 / -0.28% | up-breakouts have median relative volume 2.11, down-breakouts 0.97 | 1.0 | not_found | none |
| P-11 | volume and abs R move together; strength unchanged across liquidity | Spearman(TZ_k, abs R_k/sig) | 2,328; cells 227 to 1,442 | 2017-05 to 2026-10-13 | 0 | 0.417 [0.383, 0.454]; illiquid-liquid -0.085 [-0.184, +0.006] | IL "mid" 0.304 [0.149, 0.427] | <1e-4 / <1e-4 | descriptive_only | none |
| P-12 | heavy-turnover days carry less continuation | interaction R_{k-1} x TZ_{k-1} | 2,327 | same | interaction 0 | -0.071 (se 0.022) | Amihud-state interaction +0.027 (ns) | 0.011 / 0.36 | descriptive_only | none (TZ now +0.08) |
| P-13 | turnover predicts tomorrow's abs R / sigma | walk-forward vs expanding mean | 1,888 | 2019-02 to 2026-10 | expanding mean | OOS R2 +0.91% | Final -2.50%; 2025 -2.58% | 0.0001 / 0.0025 | not_found (fails Final gate) | next-day abs R / sig 0.763 vs 0.760: none |
| P-14 | regime classes differ in next-day scale | calm / trending / event / stressed | 1004 / 513 / 181 / 421 (121 / 106 / 38 / 43 spells) | 2018-03-12 to 2026-10-13 | all valid sessions | SD 2.36 / 2.69 / 3.40 / 3.20% vs 2.72% | direction indistinguishable (P(R>0) 0.476 to 0.519) | stressed vs all: SD 0.026 / 1.0 | descriptive_only | none beyond S6 |
| P-15 | S6 intervals are calibrated within each regime | Kupiec coverage by regime | 175 to 881 | 2019-02-15 to 2026-10-12 | nominal | 90%: 0.884 / 0.889 / 0.937 / 0.872; stressed 50%: 0.419 | S0 fails stress at all levels | stressed 50%: 0.041 / 0.34 | contradicted (stressed 50% only); else descriptive_only | optional +10% on a 50% interval; 90% unchanged |
| P-16 | today is a "stressed" session | rules in section 7.1 | 421 historical (43 spells); Nifty-drawdown-only subset 165 (31) | | all valid sessions | SD 3.20% (subset 2.79%); P(R>0) 0.492 (0.509) | class dominated by high-VIX episodes | log SD ratio 0.026 / 1.0 | descriptive_only | sigma 2.478% unchanged (kappa 1.04 [0.92, 1.22]) |

## 10. Contrary evidence and what would reverse each conclusion

* **"No directional skill"** is contradicted in part by a pooled, nominal, small, borderline-FWER walk-forward effect for yesterday's return (P-03; RC_PD survives whole-registry Holm at 0.031, U at 0.052) and by 53.9% sign agreement. It would be upgraded if the same one-feature model has positive OOS R2 over the next 250 sessions of auction-priced closes (the Final window is 318 sessions and negative now). It would be abandoned as an artefact if the auction-era lag-1 autocorrelation stays near zero (currently -0.007, n 50, CI -0.39 to +0.23: uninformative) while open-to-open stays at 0.
* **"The gap effect flips"** is supported by the Fisher test (whole-registry Holm 0.015) and the drift-adjusted bootstrap (family 0.007), and contradicted by the continuous-slope test (p 0.13) and the unknown-break test (p 0.059, best break 2021, not 2024). Illustratively, a gap-conditional excess of 20 pp would need on the order of 60 auction-era gap-ups of >= 0.5 sigma to be resolved (standard error about 6.5 pp; currently 4).
* **"The v1 scale model is calibrated"** holds at the 90% and 95% levels in every regime, fails in the 50% body (overall kappa50 1.098 [1.024, 1.157]; stressed 1.262), and over-covers event-driven sessions. It would be reversed if 90% coverage in such sessions fell towards the untimed benchmark's stressed-class level (S0: 0.825).
* **Regime call.** "Stressed" would become broad stress (and the SD of 3.2% to 3.4% relevant) if India VIX rose above 25 or BSE's 20-day volatility percentile exceeded 0.90 with a negative 20-day return; it would drop to "trending/calm" if the Nifty recovered to within 10% of 26,328.55 (above about 23,696) with no shock.
* Several of these statistics are one signal seen through different cuts (lag-1 ACF, VR, m1 walk-forward, PT, the G_k x I_{k-1} term, the previous-day interaction in 4c are all the same serial-dependence feature); they are not independent confirmations, and neither is the agreement with the earlier attempt noted in A4.

## 11. Limits, gaps, failed attempts

* The close is a 30-minute VWAP before 2026-08-03 and the closing-auction price from 2026-08-03 (50 sessions). Every close-based statistic (R, I, ACF, breakout level, F_h) is a mixture; the auction era is far too short to test anything alone. Direction-of-causality statements (VWAP staleness, liquidity provision) are untested hypotheses.
* Expanding terciles are unbalanced (PV 3% / 34% / 64% out of sample; IL 62% / 10% / 19%) because BSE's volatility and turnover grew; the 4-class regime carries the volatility information more evenly.
* Cell counts: AUC-era cells, POST large-gap cells (up_L 12, down_L 6) and POST regime cells with n < 15 are untested; 28 specified tests were skipped for that reason (list in the JSON). Power is low everywhere below n of about 100.
* Delivery % for 2026-10-13 and 2022-08-08 is missing; delivery terciles start about 2020-10. Share volume is not used (the 2022 bonus does not scale cleanly through it); relative volume uses rupee turnover.
* Walk-forward "OOS" statistics reuse choices I made after v1 (signals, partitions), but all thresholds were fixed before the first run and amendments are logged; family-wide multiplicity is controlled with 259 tests, so p-values near 0.01 do not survive.
* The 2026-10-13 index row and its VIX come from another workstream's embedded constants, unverified here. Calibration cannot score 2026-10-13 because `forecasts_R.csv` ends on 2026-10-12.
* Failed or not attempted: no external source was contacted (none was needed); no TradingView data (none supplied; its terms prohibit fetching).

## 12. Reproduce

`cd /home/user/pred_18 && PYTHONPATH=src python3 src/behaviour/pattern_tests.py` (about 20 s; writes `results/behaviour/patterns.json`), `--selftest` for the simulated-data checks. The script reads `data/processed/bse_daily.csv`, `index_daily.csv`, `results/forecasts_R.csv`, `results/conditional_day.json`, `data/results_dates.csv` and nothing else.
