# Independent verification of specialist E (quantile regression, boosted trees, forest, conformal, stacks) for the day's HIGH and LOW

Verifier report on `research/hl/E_quantile.md`, `src/hl_ml.py` and `results/hl3_*`. Written Sun 18 Oct 2026 (morning, machine clock 08:xx UTC). No number of mine uses data dated after the 15 Oct 2026 close: every script of mine cuts the bar files at "before 2026-10-16". The 16 Oct bar is in the repository (the session has finished); I read it only (a) to confirm that the builder's single-day look quotes it correctly and (b) as the thing I deliberately corrupted in the contamination test (Section 4). I edited no file except this one. Everything that writes (re-runs, contaminated copies) was done in copies under the scratchpad.

## 0. Verdict

**Pass with fixes needed. Severity: minor.** The result stands: **no variant meets the pre-fixed adoption rule for any of the four targets, and I can reproduce that with my own code.** Every number I tested reproduces from the raw files (baseline to 1e-14; the 72 variant-target scores, DM tests and Holm adjustments to 1e-6 or better; eight variant-target forecast sets refitted by me with a different solver and my own feature code land within 0.11 percentage points of the builder's gains, same sign everywhere). I found no look-ahead and no arithmetic error. What needs fixing is the *explanation* around the result: several statements that claim more than the numbers support or that mix up two different things (Section 5, items 1 to 8), the most important being that the "significantly worse" variants are mostly worse because they swap the baseline's trailing-500 window for an expanding window, not because of the extra parameters.

Plain words for the lead:
* **Nothing in the menu (62 pre-open / 67 post-open known-in-advance parameters, 18 model variants) makes the day's high and low measurably more precise than the baseline.** The typical miss of the median at Rs 3,428 stays at Rs 42.7 / 47.7 before the open and Rs 34.8 / 37.4 after it (n = 320); no variant is better by more than Rs 1.3 or worse by more than Rs 1.65, and the best-looking one (+Rs 1.3) uses US overnight data timed in a way the builder could not prove.
* "No gain shown" is not the same as "proved no gain": the rule needs about +2.6% pinball gain to clear Holm over 72 pairs, and would adopt a true +2% effect only about 23% of the time (I recomputed this). The fair headline is "no variant shown to improve", not a flat "NO".
* The properly timed US-overnight test (V18) and a second specialist (D, which picked an S&P-only shift after seeing its coefficients, so post hoc) both put the S&P 500 cue at about Rs 1 to 1.3 off the pre-open miss. E's V18 is not significant after 72 tests (Holm 1.0) and was not adoptable under the rule; D's cannot be adopted either. It is the one lead worth scoring forward, as D also recommends.

## 1. What I checked and how

My code is in `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/verE/`. `ind.py` (baseline, scoring, DM, Holm, Kupiec) imports nothing from `src/`; I retyped the S6 volatility specification after reading `src/models.py` (a second typing of the same specification, as verify_A did), so the baseline is independent in code but not in specification. `myfeat.py` (41 features) and `qr_wf.py` (exact-LP quantile-regression walk-forward) are also my own; where I import the builder's `hl_ml` it is explicitly to test that code (truncation, contamination and junk tests, recomputing cached tasks).

| step | what I did | result |
|---|---|---|
| A. baseline | own S6 sigma, trailing-500 filtered historical simulation, scoring of all windows from the raw bar files | matches the project's stored tables `hl_eval_preopen/postopen.csv` (P_S6, W_I6) to 3.6e-15 (pinball), 1.4e-14 (rupees), 20 rows; matches the builder's stored baseline quantiles to 8e-8 in log units (explained in item 11 of Section 5) |
| B. all 72 pairs | scored the builder's stored out-of-sample quantile sets (`hl3_oos_predictions.csv`) with my own pinball, mean and median rupee miss, coverage, Kupiec, DM (HAC lag 5, Harvey-Leybourne-Newbold) and Holm over 72, against my own baseline and my own targets from the raw bars | `y_realised` differs from my targets by 1e-16; gain, raw p and Holm p match `hl3_dm_holm.csv` to 1.1e-6 / 6e-6 / 1.2e-6; rupee misses to 4e-14; coverage and Kupiec exactly |
| C. adoption rule | applied the five conditions myself to all 72 pairs (also from the full walk-forward pickle for Validation and the closing-auction slice) | 0 pairs pass (i); 0 adopted; every condition column equals `hl3_adoption.csv` (Section 3) |
| D. independent refits | wrote my own feature builder and my own walk-forward with the EXACT linear-programming solver (scikit-learn / HiGHS), same pre-fixed design (nested 3-fold CV, penalty grid, null choice, B-offset), for V01 (all four targets), V07 and V18 (pre-open high and low) | within 0.11 point of the builder's gains (table in Section 2); same sign everywhere |
| E. conformalised baseline V11 | rebuilt from my own baseline for all 1,640 sessions, four targets | identical quantiles (difference 0.0), identical gains, raw p and post-hoc Holm |
| F. features | (i) my 41 features (OWN, FLOW, CAL, US at lag 2 and lag 1) over all 2,390 sessions against the builder's matrix; (ii) 107 cells recomputed directly from raw files; (iii) truncation test of the builder's `build_features` at 68 sessions; (iv) breadth rule rebuilt from the raw 13 Oct bhavcopy zip against the project's file | (i) 0 of 41 columns differ (1e-8, same missing pattern); (ii) max difference 1.9e-14; (iii) 10,812 cells, only 4 sessions differ and all four are harness or calendar artefacts, none a look-ahead of values (Section 4); (iv) identical |
| G. leakage | the builder's junk test re-run by me at two NEW sessions with a different random seed (777 instead of 123); contamination test of the live forecast on a corrupted copy of the repository; two walk-forward tasks recomputed from scratch against the cache | 2026-03-18: 72 of 72 forecasts bit-identical, positive control 72 of 72; 2024-09-11: 72 of 72 bit-identical, positive control 68 of the 68 defined (V17 does not exist before it has 120 IV sessions); live forecast identical in all 886 numeric fields; tasks identical (difference 0) |
| H. report vs files | parsed every cell of tables 4.1 to 4.4 (611 cells), 5.1, 6.1 (216), 6.2 (64), 6.3 (212), 7.2, 7.3, the tercile and importance tables and the numbers-to-quote lines against the CSV/JSON files | 0 mismatches |
| I. provenance | SHA-256 of the pre-fixed section against git commit 2072844; code and input hashes against `hl3_meta.json`; file times | pre-fixed section is byte-identical to the commit (`aa026b73e547...`); the commit (08:00:49 UTC, 16 Oct) precedes the first computed file (`hl3_solver_validation.csv` 08:17:32 UTC; the walk-forward cache 08:19 to 08:45 UTC); code and all 12 input files match the hashes in `hl3_meta.json` |

## 2. Headline numbers recomputed (mine from raw files vs the builder's report)

Final window 1 Jul 2025 to 15 Oct 2026, n = 320 unless stated; rupees = mean absolute error of the 50% quantile times Rs 3,428.

| claim | builder | mine | difference |
|---|---|---|---|
| Baseline pinball x1e4, pre-open high / low | 31.152 / 36.579 | 31.1516 / 36.5788 | rounding |
| Baseline pinball x1e4, post-open high / low | 23.853 / 28.030 | 23.8531 / 28.0298 | rounding |
| Baseline typical miss Rs, pre-open high / low | 42.7 / 47.7 | 42.69 / 47.67 (s.e. 2.25 / 2.91) | rounding |
| Baseline typical miss Rs, post-open high / low | 34.8 / 37.4 | 34.81 / 37.42 (s.e. 1.77 / 2.57) | rounding |
| "Price stays" / "open stays" Rs | 62.9 / 61.3 ; 51.3 / 59.0 | 62.9 / 61.3 ; 51.3 / 59.0 | 0 |
| Trailing-250 empirical, Rs and pinball x1e4 | 43.7 / 47.5 / 35.4 / 37.6 ; 32.739 / 36.587 / 25.009 / 28.053 | same | 0 |
| Coverage 50% / 90%, high pre-open | 0.469 / 0.903 | 0.4688 / 0.9031 (Kupiec p 0.85) | 0 |
| Coverage 50% / 90%, low pre-open | 0.503 / 0.887 | 0.5031 / 0.8875 (Kupiec p 0.46) | 0 |
| Coverage 50% / 90%, post-open high / low | 0.494 / 0.950 ; 0.503 / 0.894 | 0.4938 / 0.9500 (Kupiec p 0.0011, the atom at zero) ; 0.5031 / 0.8938 | 0 |
| Family size for Holm | 72 (18 x 4) | 72; my Holm equals theirs to 1.2e-6 | 0 |
| Features: pre-open / post-open / distinct | 62 / 67 / 82 | 62 / 67 / 82 (counted in the code: OWN 21 + ln sigma 1, FLOW 4, CAL 7, IDX 10, BRD 5, PEER 6, US 8 = 62; +5 GAP; +7 IV +8 US lag-1) | 0 |
| Effective configurations per target per refit | 96 | 9x4 + 3x7 + 1 + 3x11 + 5 = 96 | 0 |
| Pairs better / worse than baseline (any size) | 21 / 51 | 21 / 51, median -0.394% | 0 |
| Pairs significantly worse after Holm | 5 (V01 H, V01 HO, V10 HO, V12 LO, V13 LO) | same five | 0 |
| Largest Final gain, any pair | +2.86% (V18, pre-open high), raw p 0.024, Holm 1.0 | +2.856%, raw p 0.0239, Holm 1.0 | 0 |
| Largest Final gain, eligible pair | +1.45% (V07, pre-open high), raw p 0.093 | +1.448%, 0.0929, Validation -0.27% | 0 |
| Rupee miss, best / worst variant vs baseline | better by at most 1.3, worse by at most 1.6 | 1.309 and 1.649 (V18 H and V13 LO) | 0 |
| Power of the rule | needs +2.6%; a true +2% adopted ~23% | s.e. of gain median 0.75% (range 0.11 to 1.26), first Holm step needs t 3.43, gain 2.57%, P(adopt a true 2%) = 0.234 | 0 |

Independent refits with my own features and the exact solver (Final, n = 320; gain = percentage change of mean pinball against the baseline, positive = better; p = DM two-sided, HAC lag 5):

| pair | mine: pinball x1e4 / gain / p / miss Rs | builder: gain / p / miss Rs |
|---|---|---|
| V01 pre-open high | 32.110 / -3.08% / <0.0001 / 43.09 | -3.08% / <0.0001 / 43.1 |
| V01 pre-open low | 36.322 / +0.70% / 0.0028 / 47.49 | +0.69% / 0.0030 / 47.5 |
| V01 post-open high | 24.584 / -3.06% / <0.0001 / 34.64 | -3.04% / <0.0001 / 34.6 |
| V01 post-open low | 27.904 / +0.45% / 0.110 / 37.38 | +0.45% / 0.107 / 37.4 |
| V07 pre-open high (best eligible) | 30.713 / +1.41% / 0.109 / 42.27 | +1.45% / 0.093 / 42.2 |
| V07 pre-open low | 36.694 / -0.32% / 0.533 / 47.98 | -0.29% / 0.566 / 48.0 |
| V18 pre-open high (best of all) | 30.269 / +2.83% / 0.027 / 41.37 | +2.86% / 0.024 / 41.4 |
| V18 pre-open low | 35.930 / +1.78% / 0.084 / 46.61 | +1.67% / 0.109 / 46.6 |

The small differences are the solver (the builder's smoothed approximate solver against the exact one; the builder's own validation put it within 0.44% of the optimum) and a few nested-CV choices that flip (for example my V07 high chooses "do nothing" in two blocks). None changes a verdict.

Sensitivity of the DM p-values to the HAC lag (Final, builder's forecasts): V18 high 0.008 / 0.024 / 0.034 / 0.071 at lag 0 / 5 / 10 / 20; V07 high 0.070 / 0.093 / 0.099 / 0.125; V04 high 0.098 / 0.119 / 0.124 / 0.149; V01 low 0.0024 / 0.0030 / 0.0034 / 0.0058. Even the smallest, multiplied by 72, stays above 0.17, so the null does not depend on the lag.

## 3. The pre-fixed five-condition rule, applied by me

Family size = 72 variant-target pairs (18 variants x 4 targets). Number of features searched = 62 pre-open, 67 post-open, 82 distinct columns. My counts over all 72 pairs equal the builder's: (i) gain >= 2% and Holm p < 0.05: **0**; (ii) Validation same sign: 56; (iii) coverage: 13; (iv) closing-auction slice within 5%: 68; (v) leakage: 72; all five: **0**.

| target | pairs | pass (i) | best Final gain (pair, raw p, Holm, Validation) | best eligible pair | rule met? |
|---|---|---|---|---|---|
| pre-open HIGH | 18 | 0 | V18 +2.86% (0.024, 1.0, +0.69%); fails (iii) by one session (286 of 320 inside its 90% band against the baseline's 289; it needed 287) | V07 +1.45% (0.093, 1.0, **-0.27%**) | **No** |
| pre-open LOW | 18 | 0 | V18 +1.67% (0.109, 1.0, +1.59%); fails (iii) | V01 +0.69% (0.003, **Holm 0.19**, +0.70%) | **No** |
| post-open HIGH | 18 | 0 | V03 +0.71% (0.47, 1.0, +0.74%) | V03 | **No** |
| post-open LOW | 18 | 0 | V01 +0.45% (0.107, 1.0, -0.39%) | V01 | **No** |

Robustness of "no": no eligible pair has a gain of 2% or more at all (maximum 1.45%), so the multiplicity correction is not what decides it. With NO multiplicity correction one pair has gain >= 2% and raw p < 0.05 (V18 high, ineligible). At a raw 5% level 16 of the 72 pairs are "significant", but 14 of them are significantly WORSE and only two better (V18 high, V01 low), against 3.6 expected by chance in each direction if everything were null.

## 4. Look-ahead and arithmetic review

Method: I read all of `src/hl_ml.py` (1,736 lines) against `src/hl_model.py`, `src/models.py`, `src/common.py`, `src/metrics.py`, then tested the reading with code.

Timestamp rule of every feature group against what the code does (all features are built on session s = t-1 and shifted one row; rolling windows are trailing and include s):

| group | rule in the report | code | my check |
|---|---|---|---|
| OWN (21 + ln sigma) | bhavcopy of s, ~16:34 IST | `S(x) = x.shift(1)` on every term; 250-day high/low distance built from the corporate-action-adjusted close chain (`R.cumsum()`), so the 2022 and 2025 bonus ex-dates do not distort levels | recomputed by me, identical over all 2,390 sessions |
| FLOW (4) | bhavcopy and delivery file of s | turnover and trades in rupees and counts (not bonus-affected), delivery %, 60-session trailing z-scores, shifted | recomputed, identical |
| CAL (7) | calendar | weekday dummies, days since previous session, month start/end from the weekday calendar (ignores exchange holidays; stated) | recomputed, identical |
| IDX (10) | index file of s, published after the close | reindexed to BSE sessions then shifted; z-scores use trailing 60 | file ends 12 Oct, so 14 and 15 Oct and the live row are "no information" (stated); spot cells identical |
| BRD, PEER (5 + 6) | bhavcopy of s | read from the project files; 14 and 15 Oct rebuilt from the raw zips with the project's own breadth rule | the rule applied to the 13 Oct zip equals the project's 13 Oct row exactly |
| US (8), lag 2 | FRED observations dated at most D-2 | `searchsorted(cutoff, side='right') - 1`, observation must be at most 7 days old | recomputed, identical. The file dates are event dates (S&P 500 close of 16 Mar 2020 = 2,386.13 is dated 16 Mar), so an observation dated D-1 is public before the Indian open (New York closes at about 01:30 IST) and lag 2 is **one US session staler than necessary on Tuesday to Friday** (Section 5, item 3) |
| GAP (5, post-open) | official open, final at 09:08 | open of row t only; `ob = c.shift(1) + G` vs `h.shift(1)`, `l.shift(1)` | consistent chain levels |
| IV (7, V17 only) | previous session | shifted; expiry flags from the F&O contract calendar | see Section 5, item 2 |
| Standardisation, winsorising, imputation | training window only | `prep()` uses the training mean and sd (inside each CV fold too); missing set to 0 | correct. The report says "training median"; the code uses the training mean (0 after standardising). Wording only |
| Hyper-parameters / feature choice | nested CV inside the training window | 3 folds at 55/70/85% with a 5-session embargo; GBM choice re-made every 4th refit from data before the block; stack weights from the previous at most 250 out-of-sample sessions; conformal calibration block taken from training rows before the block | none touches the Final window. The "display variant" for 16 Oct is picked on Validation+Final pooled, which is outside the adoption path and labelled descriptive |
| Block structure | train on sessions before the block, refit every 20 | `tr = arange(530, b0)`, `sess = arange(b0, b0+20)`; no off-by-one | confirmed by my own re-implementation, which uses the same indices and reproduces the builder's numbers |

Tests of the reading:
* **Truncation test of the feature code** (my script `feat_trunc.py`): for 68 sessions (60 random between 2019 and 2026 plus 2022-03-21 and 2025-05-23 ex-dates, 2026-08-03 first closing-auction day, 14 and 15 Oct, the first evaluated session, and the IV start) I rebuilt the features after DELETING all input rows dated on or after the session (placeholder row with the official open kept) and compared row t with the full-sample matrix: 10,812 cells; 4 sessions differ, none a look-ahead of values: (a) on the two bonus ex-dates the post-open GAP block differs because the placeholder row's previous close is the raw close, not the bonus-adjusted one (the live function would give a wrong gap on a future ex-date; the baseline `hl_forecast` has the same limitation; irrelevant for 16 Oct); (b) on 23 Jan 2026 `iv_day_before_expiry` looks at the date of the next session in the data (a holiday-calendar fact, 0 on the live row; V17 only).
* **Junk test** (builder's `leak_test`, my seed, two sessions the builder did not use): 2026-03-18 (Final, 18th of 20 in its block) 72 of 72 forecasts (18 variants x 2 phases x 2 targets) bit-identical, positive control (later sessions of the block change) 72 of 72; 2024-09-11 (Validation, 3rd of 20 in its block) 72 of 72 bit-identical, largest difference 0.0, positive control 68 of the 68 forecasts that exist (the four V17 forecasts are undefined in Sep 2024 in both runs). With the builder's 6 sessions that is 8 sessions, 576 forecasts, all identical.
* **Contamination test of the live forecast**: in a copy of the repository I changed the 16 Oct bar (high 3,999, low 2,000, close 2,100, volume 99,999,999), appended junk bars dated 19 and 20 Oct, appended junk rows dated 16 to 20 Oct to all six FRED files, the index, breadth, peers and IV files, swapped the 16 Oct bhavcopy zip for another day's and added a 16 Oct F&O file. `ml_forecast('2026-10-16', open_price=3450.0)` on that copy equals the same call on a clean copy in all 886 numeric fields (largest difference 0.0). So the forecast uses nothing dated 16 Oct or later except the supplied open.
* **Cache = current code**: I recomputed two walk-forward tasks from scratch with the current `hl_ml.py` (pre-open low, group 19; post-open high, group 10): 116 variant-by-block arrays against the cached ones, difference 0. Note the cache files are all stamped 16 Oct 08:19 to 08:45 UTC (the first run); the report says the tables come from the second run (13:39 to 14:21 UTC); because the builder reports and I confirm the two are identical, nothing depends on it, but the sentence in 8.1 is imprecise.
* **Baseline determinism**: `hl_ml.py` sets one BLAS thread. In my environment one thread changes the S6 sigma by up to 1.5e-5 relative compared with the default threads, which is the "unexplained 1e-7" the builder mentions in Section 2 of the report.

Arithmetic and logic found correct: pinball, coverage, Kupiec, DM sign and HLN factor, Holm, the block bootstrap, the rupee conversions, the condition (iii) distance rule including the atom-aware check for the post-open high, the conformal rank `ceil((n+1) tau)`, the stack weight grid, `finalize` (sort then clip), and the live row indexing.

## 5. Overclaims, confounds and defects

Ranked. Each gives the corrected wording.

1. **"Significantly worse" and "51 of 72 worse" mix up the extra parameters with a change of window.** The direct ("A") variants (V01, V02, V08, V10, V12, V13) estimate the standardised quantiles from the EXPANDING window since 2019, while the baseline uses the trailing 500 sessions. I computed the featureless version of that (unconditional quantile of y/sigma over the expanding window, times sigma): against the baseline it is **-3.16% (pre-open high) and -2.79% (post-open high) in the Final window, p < 0.0001**, while for the highs it was +0.09% / +0.06% in Development and +0.38% / +0.17% in Validation (for the lows: -0.35% / -0.47% in Development, +0.24% / -0.27% in Validation, +0.34% / +0.30% in Final). So V01's "-3.08% / -3.04%" is the window, not "letting the scale enter with its own elasticity", and V01 has no extra parameters at all. Split the 72 pairs by design: the 36 pairs of the nine variants tied to the baseline (offset form: V03 to V07, V09, V11, V17, V18) have 17 better, median gain **-0.01%**, mean +0.11%; the 24 direct pairs have 3 better, median -1.60%; the 12 stacks have 1 better. Corrected sentence: "Tied to the baseline, the extra parameters neither helped nor hurt on average (median -0.01%, 17 of 36 better); the direct models lose mainly because they replace the baseline's 500-session window by an expanding window." The same confound inflates Section 6.1: "42 of 68 pairs gain in Validation and lose in Final (average +0.87% then -0.63%)" is 19 of 24 for the direct models but 12 of 32 for the baseline-tied ones (the eight offset variants without V17, whose Validation window has 20 sessions; average +0.51% then +0.13%). The "break around July 2025" that the report could not explain is, at least for the highs, a level shift of the standardised high (high divided by the baseline's sigma): median 0.54 against 0.64 and 95% point 1.80 against 2.51 in the Final window (n = 320) compared with the sessions up to June 2025 (n = 1,540), while the standardised lows did not move (median -0.47 against -0.45; 5% point -1.93 against -1.94). Models that learn the 2019-2025 distribution therefore over-predict the highs in Final; the baseline's trailing window adapts. This is descriptive and my own, not a tested cause.
2. **Implied volatility was effectively not tested, so "changes the Final gain by at most 0.011 points, i.e. nothing" is misleading.** I refitted V17 at four Final blocks for each target: in 15 non-null fits the IV coefficients were exactly zero in 13 and at most 0.004 sigma per standard deviation in the other two. The cause is the design: only 143 to 442 of the 1,500 to 1,900 training rows have IV and the rest are set to 0, so the L1 penalty removes the block; V17 is V03 with unused columns. The brief asked for the IV to be tested on its own window. I did that (post-hoc, my design, 3 features: IV level against own trailing volatility, IV minus realised, skew; offset form; trained only on rows that have IV, 140 to 439 rows; Final n = 320): high **+0.80%** (p 0.54), low **0.00%** (never used), post-open high **-0.59%** (p 0.52), post-open low **-1.25%** (p 0.044, worse). So IV does not help on its own window either, but with 140 to 440 training sessions and one look this is a weak test. Corrected sentence: "Implied volatility (462 sessions) is untested in the pooled model because the model ignored it; an own-window test shows no gain (n = 320, low power)."
3. **The US overnight block was tested with stale data in every eligible variant, and the importance table inherits that.** Lag 2 means a Tuesday to Friday session sees the US close of two US sessions ago, not last night's. Only V18 (lag 1) carries last night's S&P 500, VIX, dollar, rupee, Brent and yield, and the report excludes it only because the FRED posting time "cannot be proven"; in real time the S&P 500 and the US VIX close are public before the Indian open, while the FRED H.10/H.15 series (rupee, dollar index, 10-year yield) are posted with a delay but their markets are observable. Hence "US VIX, dollar, rupee, US 10-year at the noise floor" (the report's Section 7.1) is a statement about two-session-old data. Corrected sentence: "With last night's US data (V18) the pre-open high improves by +2.86% (p 0.024, Holm 1.0) and the low by +1.67% (p 0.11), about Rs 1.3 and 1.0; not significant after 72 tests, not provable timing, concentrated in 2026 (-1.52%, +6.07%, +4.25% by half-year); specialist D's independent post-hoc S&P shift is of the same size (Rs 1.1 and 1.3)."
4. **"The relationships reversed in the Final window"** (breadth, Section 1 and 7.4). I reproduced the numbers (high 0.577 vs 0.706 sigma, low 0.642 vs 0.349 deeper before the Final window; 0.713 vs 0.447 and 0.449 vs 0.449 in it). Tested: before the Final window both differences are overwhelming (Mann-Whitney p 0.0001 and < 0.0001); in the Final window the high difference is -0.27 sigma with a 90% bootstrap interval of -0.41 to -0.03 and p = 0.09, and the low difference is 0.00 (p 0.86). So: low "vanished", high "vanished or reversed (p 0.09)". "Reversed" should not be stated as fact.
5. **Headline "NO"** is stronger than the evidence ("no variant shown to improve"; Section 11.1 of the report says this correctly). At a raw 5% level with no multiplicity correction the same rule would adopt a true +2% effect 76% of the time, with Holm over 72 only 23%.
6. **Best-variant rupee misses "Rs 41.4 / 46.6"** are V18 and were picked after seeing the Final window among 18; the eligible best are 42.1 / 47.5 / 34.3 / 37.4. They are labelled descriptive in the report; do not present them as achievable gains.
7. **Post-hoc lead "V10/V16 improve the pre-open low by about 2% (post-hoc Holm 0.0066)"** uses HAC lag 5 on losses whose forecasts are refitted every 20 sessions. I re-ran it: raw p 0.00009 / 0.00010 / 0.00035 / 0.00135 at lag 5 / 10 / 20 / 40 and 0.0033 with a 40-session block bootstrap, i.e. Holm over the 72 post-hoc tests about 0.007 / 0.007 / 0.025 / 0.10 / 0.23. Keep it a "lead for a pre-registered test", and add that it is not significant at long lags. The same applies to the conformalised baseline V11 ("significantly worse on all four, Holm 0.013 / 0.003 / 0.002 / 0.025"): reproduced exactly at lag 5; at lag 40 only the post-open high stays below 0.05 after Holm.
8. **The single-day look at 16 Oct uses the 16 Oct bar**, which the brief forbade for any study (written when the session was in progress). It was made after the decision, is labelled n = 1 and touches no adoption number, and I checked its arithmetic (misses -20.0, -79.5, -33.5, -99.3 Rs; counts of variants better/worse 3/13, 9/9, 0/12, 12/2 with ties). It should not be quoted.
9. **Condition (iii) is tie-sensitive**: V18 high fails it by one session of 320. Immaterial here because it fails (i), but the lead should know the rule can reject on a 0.3 percentage-point coverage difference.
10. **The baseline was itself chosen by the project on Validation+Final** (verify_A items 9 and 10), so the Final window is not neutral ground; this favours the baseline slightly. The report does not mention it. It does not change a verdict.
11. Small items: "22 of 68 pairs positive in the closing-auction slice" counts four ties at +0.0000% as not positive (26 if floating-point noise counts); the pre-fixed section's miscount (24/12 instead of 22/10 columns) is disclosed and harmless; the report says missing values become the training median, the code uses the mean; the 1e-7 baseline differences are the single BLAS thread (Section 4).

No contradiction with `A_dayahead.md` or `verify_A_dayahead.md` found. E's long-run finding that conformal repair of the baseline is worse supports A's decision not to recalibrate the high's median. A's suspicion that the pre-open high runs a little high is not contradicted: all nine baseline-tied variants gain +0.4% to +2.9% on the high in Final, which could be a small level correction, but none is significant. Specialist D's report (`D_features.md`) also finds no adoptable variant and the same S&P cue of about Rs 1.

## 6. The 16 Oct forecast (run by me)

`ml_forecast('2026-10-16', 3450.0)` (about 90 s on 4 cores) reproduces `results/hl3_2026-10-16.json` in all 886 numeric fields, difference 0.0, in a clean copy and in the contaminated copy. Its baseline block equals `hl_model.hl_forecast('2026-10-16', 3450.0)` to the cent for every quantile of all four targets, and sigma agrees to 3e-7 relative (2.4348% before the open, 2.2159% after). Data used: sessions through the 15 Oct close (2,390), breadth and peers for 14 and 15 Oct from the raw bhavcopy zips (published the evening of the day), the official open Rs 3,450.0 (09:08 auction), nothing dated 16 Oct or later. Sanity: all 18 variants' quantile vectors are monotone; post-open high quantiles are at least the open and post-open low quantiles at most the open; the 18 medians lie within Rs 3,473.7 to 3,485.3 (pre-open high; baseline 3,475.0), 3,387.0 to 3,394.4 (low; 3,390.1), 3,488.5 to 3,501.4 (post-open high; 3,488.5) and 3,403.0 to 3,412.6 (post-open low; 3,409.9), largest departure Rs 12.9. 22 input columns are "no information" today (index/VIX file ends 12 Oct, rupee/dollar/Brent end 2 and 6 Oct, IV ends 12 Oct), so the flexible variants are less informed than in the backtest, as the report says. The baseline is the right pin-point: pre-open high median Rs 3,475 (half the time 3,449 to 3,513; 90% band 3,421 to 3,591), low Rs 3,390 (3,352 to 3,419; 3,269 to 3,450); after the open high Rs 3,488 (3,468 to 3,526; 3,451 to 3,591), low Rs 3,410 (3,374 to 3,430; 3,294 to 3,447). The 90% band for the post-open high is a 95% edge, as verify_A said.

## 7. What the lead may quote, must correct, must not quote

### 7.1 May be quoted as they stand (reproduced by me; n beside each)
* Baseline, Final n = 320, at Rs 3,428: typical miss pre-open high 42.7 / low 47.7, post-open high 34.8 / low 37.4 (s.e. 2.2 / 2.9 / 1.8 / 2.6 as if independent; block-bootstrap 2.8 / 3.0 / 1.8 / 2.3 per verify_A); half the time within 33.6 / 32.2 / 29.1 / 26.6; "price stays" 62.9 / 61.3; "open stays" 51.3 / 59.0; trailing-250 history 43.7 / 47.5 / 35.4 / 37.6.
* Coverage, Final n = 320: 90% band 90.3% (high) and 88.8% (low) pre-open, 50% band 46.9% / 50.3%.
* Study size: 18 variants x 4 targets = 72 pairs tried (Holm family); 62 pre-open and 67 post-open parameters, 82 distinct columns; 96 effective configurations per target per refit; 82 refits; 1,640 evaluation sessions; Final n = 320, Validation 248, closing-auction slice 52.
* **0 of 72 pairs reach the first adoption condition; no variant is adopted for any target.** No eligible pair has a gain above 1.45%; the only pair above 2% is V18, pre-open high (+2.86%, raw p 0.024, Holm 1.0; ineligible timing).
* In rupees every variant is within +1.65 / -1.31 of the baseline's typical miss (n = 320), inside the figures' own standard errors.
* The rule needs about +2.6% to clear Holm over 72 pairs; a true +2% would be adopted about 23% of the time. So the result is "no demonstrated gain", not "no gain exists".
* Leakage: 8 sessions (builder 6, me 2 new) with all data from the session onward replaced by junk: all 576 forecasts bit-identical; the live forecast is unchanged when every file is corrupted after 15 Oct.
* Descriptive (label as such): permutation importance is small (best group, breadth for the LOW, raises held-out loss by at most 0.64 on 37.3, 1.7%); the three random columns are at 0.05 or less; India VIX level at most 0.011.
* 16 Oct baseline numbers in Section 6.

### 7.2 Must be corrected before quoting (corrected value or wording)
1. "5 pairs significantly worse (e.g. QR on volatility alone -3.1%)" -> "V01 (no extra parameters) is -3.1% on the highs because it uses an expanding window; the featureless expanding-window version alone is -3.2% / -2.8% (n = 320, p < 0.0001). Of the 36 pairs tied to the baseline, 17 are better, median -0.01%".
2. "21 of 72 better, 51 worse, median pair -0.39%" -> add the split in item 1 (the 51 are mostly direct models).
3. "Validation average +0.87% then Final -0.63%; 42 of 68 gain then lose" -> "19 of 24 direct pairs, 12 of 32 baseline-tied pairs (average +0.51% then +0.13%)".
4. "Implied volatility changes the gain by at most 0.011 points" -> "the pooled model gave implied volatility zero weight, so it is untested there; own-window test (verifier, post-hoc, n = 320): high +0.80%, low 0.00%, post-open high -0.59%, post-open low -1.25%, none helpful".
5. "VIX level, VIX-RV spread, US VIX, dollar, rupee, US 10-year at the noise floor" -> true for India VIX level (0.011) and the spread (0.039); for the US items it is true of two-session-old data only.
6. "Relationships reversed in Final" -> "gone for the low (difference 0.00, p 0.86); gone or reversed for the high (-0.27 sigma, p 0.09)".
7. Headline "NO" -> "No variant shown to improve under the pre-fixed rule".
8. "V10 pre-open low +2.08%, post-hoc Holm 0.0066" -> "Holm 0.0066 at HAC lag 5, about 0.025 at lag 20 and 0.10 at lag 40; a lead only". Same caveat for V11 "significantly worse".
9. Section 8.1 "the second run is the one in the tables" -> "the tables come from the cache written 16 Oct 08:19 to 08:45 UTC (first run); the second run reproduced it".
10. Closing-auction count "22 of 68 positive" -> "22 of 68 positive, 4 ties at zero".

### 7.3 Must not be quoted
* The single-day look at 16 Oct (n = 1, uses the 16 Oct bar, after the decision) and the display variants' 16 Oct numbers as forecasts (picked on Validation+Final).
* "Best variant" misses 41.4 / 46.6 as an achievable improvement (V18, chosen among 18 after the fact).
* The half-year table, the tercile "Final" columns with 36 to 39 sessions, and the partial-dependence readings as evidence (descriptive, in-sample, small cells).
* V17 as a test of implied volatility.
* Any statement that the US overnight cue "does not matter": it is untested at the correct timing under the rule; the only correctly timed variant has the largest gain, not significant.
* The post-hoc "all sessions" Holm values as established findings.

## 8. Commands to reproduce my verification numbers

`S=/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/verE`; run from `$S` (scripts that import `hl_ml` change the working directory to the repo, so they write nothing relative):
```
cd $S
python3 ind.py                  # own S6 sigma and baseline quantiles from raw files -> base.pkl (10 s)
python3 base_check.py           # baseline windows vs project tables (3.6e-15) and vs builder BASE quantiles (8e-8)
python3 score_variants.py       # all 72 pairs: pinball, DM, Holm, rupees, coverage vs hl3_dm_holm.csv / hl3_eval_variants.csv
python3 rule.py                 # the five conditions on all 72 pairs (uses the builder's walk-forward pickle for Validation and CAS)
python3 feat_cmp.py             # my 41 features vs the builder's matrix (writes myfeat.pkl)
python3 feat_indep.py           # 107 cells straight from raw files
python3 feat_trunc.py           # truncation test of build_features at 68 sessions
python3 qr_wf.py V07 H final    # own exact-LP walk-forward (also V01 H/L/HO/LO, V07 L, V18 H/L); then python3 cmp_qr.py V07 H
python3 v11.py                  # conformalised baseline V11, all sessions
python3 hac_robust.py           # HAC lag and block-bootstrap sensitivity of the post-hoc tests
python3 anull.py                # expanding-window null vs baseline (item 1 of Section 5)
python3 iv_own.py               # own-window implied-volatility test
python3 v17_coef.py             # IV coefficients inside V17
python3 tercile_test.py         # breadth terciles with tests
sh make_repos.sh                # repoC = isolated clean copy, repoJ = copy with everything dated 16 Oct or later corrupted
python3 run_fc.py $S/repoC $S/fc_clean.json ; python3 run_fc.py $S/repoJ $S/fc_junk.json ; python3 cmp_json.py fc_junk.json fc_clean.json ; python3 cmp_json.py fc_clean.json /home/user/pred_18/results/hl3_2026-10-16.json
(cd repoC && python3 src/hl_ml.py --baseline-check)        # the builder's own baseline check, in the copy
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 thr_test.py   # single-thread BLAS changes sigma by 1.5e-5
python3 leak_new.py 2026-03-18 2024-09-11     # builder's junk leakage test, seed 777 (about 10 minutes per session)
python3 recompute_task.py       # two walk-forward tasks recomputed against the cache
python3 report_vs_files.py ; python3 report_vs_files2.py   # report tables vs CSV files
```
