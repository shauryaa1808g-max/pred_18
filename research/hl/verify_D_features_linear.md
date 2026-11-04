# Independent verification of specialist D (extra parameters for the day's high and low)

Verifier report on `research/hl/D_features.md`, `src/hl_model2.py` and the 32 files `results/hl2_*`. Written Sun 18 Oct 2026. I edited no file except this one. Every script I wrote is in the scratchpad `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vD/` (list in Section 10). The repo working tree was clean before and after my runs (`git status` empty).

## 0. Verdict

**Pass with fixes needed. Severity: minor.** The builder's central result holds: **no extra parameter met the pre-fixed adoption rule for any of the four targets (0 of 46 variant-target pairs)**, so the baseline stays. I rebuilt the baseline, the whole 58-feature panel and the walk-forward engine from the raw files with my own code and got the builder's numbers: pinball, rupee misses, DM p-values, Holm values and all five conditions agree pair by pair (largest difference 1e-10 in any gain, p-value or Holm value; quantiles agree to 5e-7, which is the 6-digit rounding of the stored file). I found **no look-ahead** and no arithmetic error. The fixes are wording and bookkeeping (Section 8): one over-reaching sentence in the plain-words section, a wrong variant count in the builder's pointer summary (not in the report), the point that the order "rule written before results" rests on the builder's own record, and a few presentation details.

Plain words for the lead: the report's headline is right. More parameters did not make the high or low forecast more precise by any amount that passes the rule we fixed beforehand. The best pair (pre-open high, everything added as scale and shift) is 2.36% better in pinball loss and 0.9 rupees better in the typical miss, and that is not distinguishable from luck after correcting for the 46 comparisons tried. What the study can and cannot say is in Section 7.

## 1. What I did

1. Read the project docs, `A_dayahead.md`, `verify_A_dayahead.md`, `B_liveintraday.md`, `src/hl_model.py`, `models.py`, `metrics.py`, `common.py`, `eval_hl.py`, and all of `D_features.md` and `hl_model2.py` (1,423 lines).
2. **Baseline from scratch** (`own_base.py`): own targets, own GARCH(1,1)-t x HAR S6 sigma (only the `arch` package for the likelihood), own filtered historical simulation, own pinball / coverage / Kupiec / Diebold-Mariano (Bartlett long-run variance, lag 5, Harvey-Leybourne-Newbold factor) / Holm. Did not import `hl_model*.py`, `models.py`, `metrics.py` or `common.py`.
3. **Feature panel from scratch** (`own_features.py`): all 58 features plus the 10 placebo columns, from the raw and processed input files and the fill files, following the timestamp rules of D Section 0.3. Compared with `results/hl2_features_panel.csv.gz` for **every session and every feature** (the builder's own spot check used 64 sessions).
4. **Engine from scratch** (`own_engine.py`): log-link Poisson ridge for the scale multiplier, ridge OLS for the location shift, forward-chaining cross-validation of the ridge strength, refit every 20 sessions, first refit at session 640, trailing-500 residual pool. Written from D Section 0.4; where the text does not say (for example how often the ridge strength is re-chosen) I followed the code, so this checks the builder's implementation, arithmetic and look-ahead, not whether the design choices are wise. Run for all 23 pre-fixed variants, the 2 placebos and the 21 post hoc variants (46 variants, 92 pairs).
5. Applied the five-condition rule myself, to my own numbers and again to the builder's result files.
6. Ran my own leakage test on the builder's code with a different kind of junk (extreme multiples, not bootstrap noise).
7. Ran `hl2_forecast('2026-10-16', 3450.0)` and rebuilt the live baseline independently.
8. Checked the date meaning of every input table against known values, checked the filled rows against FRED, regenerated the report's tables from the result files, and read the report line by line for over-claims.

## 2. Recomputed numbers (all Final window, 1 Jul 2025 to 15 Oct 2026, n = 320, unless stated; rupees = log error x Rs 3,428)

| number | builder | mine (own code, raw files) |
|---|---|---|
| Baseline pre-open pinball x1e4, high / low | 31.15 / 36.58 | 31.152 / 36.579 |
| Baseline typical miss pre-open, high / low | Rs 42.7 / 47.7 | Rs 42.69 / 47.67 |
| Baseline after-open pinball x1e4, HO / LO | 23.85 / 28.03 | 23.853 / 28.030 |
| Baseline typical miss after open, HO / LO | Rs 34.8 / 37.4 | Rs 34.81 / 37.42 |
| 'Price stays' miss, high / low; 'open stays' miss HO / LO | 62.9 / 61.3; 51.3 / 59.0 | 62.87 / 61.30; 51.25 / 58.96 |
| Trailing-250 empirical quantiles, pinball x1e4 H / L (not in the report's headline) | - | 32.739 / 36.587 (miss Rs 43.69 / 47.55); after open 25.009 / 28.053 (Rs 35.37 / 37.62) |
| Baseline 90% band hit, pre-open high / low | 90.3% / 88.8% | 289/320 = 90.31% (Kupiec p 0.851) / 284/320 = 88.75% (p 0.464) |
| Baseline 50% band hit, pre-open high / low; after open HO / LO | 46.9 / 50.3; 49.4 / 50.3 | 150/320 = 46.88% / 161/320 = 50.31%; 49.38% / 50.31% |
| After-open high 90% band (atom at zero) | 95.0%, plain Kupiec p 0.001, nominal 92.7% | 95.00%, plain Kupiec p 0.001 (reproduced) |
| Auction slice (since 3 Aug 2026, n = 52) baseline pinball x1e4 | 31.22 / 34.02; 22.34 / 25.86 | 31.219 / 34.020; 22.342 / 25.859 |
| Best pre-fixed pair, pre-open high `P_SL_f`: pinball, gain, DM t, raw p, Holm over 46 | 30.42, +2.36%, -, 0.072, 1.00 | 30.416, +2.360%, t 1.806, p 0.0719 (one-sided 0.036), Holm 1.000 |
| `P_SL_f` pre-open high typical miss; 50% / 90% band hit | Rs 41.8; dev -0.9 / +0.9 points | Rs 41.79 (baseline 42.69); 157/320 = 49.06%, 291/320 = 90.94% |
| Best on Final, pre-open low `P_LO_f` | +1.55%, p 0.312, Rs 47.1 | +1.552%, p 0.312, Rs 47.13 |
| Best on Final, after-open high `W_SC_fo` | +1.20%, p 0.058, Rs 34.3 | +1.203%, p 0.0578, Rs 34.29 |
| Best on Final, after-open low `W_SC_s` | +0.22%, p 0.197, Rs 37.4 | +0.218%, p 0.197, Rs 37.38 |
| Worst, after-open low `W_SL_fo` | -3.86%, Holm 0.004, Rs 38.6 | -3.856%, p 0.0001, Holm 0.0040, Rs 38.62 |
| Post hoc `P_LO_sp` (S&P shift), high / low | +2.14% / +2.94%; Rs 41.6 / 46.3 | +2.140% / +2.938%; Rs 41.60 / 46.33; raw p 0.0707 / 0.0030 |
| Holm over all 92 pairs, `P_LO_sp` high / low; `P_LO_b` low | 1.00 / 0.25; 0.18 | 1.000 / 0.251; 0.178 (max difference over all 92 Holm values 1e-11) |
| Variants / pairs in the Holm family / features / post hoc variants | 23 / 46 / 58 / 21 | 23 (11 pre-open, 12 after-open) / 46 / 58 (40 scale, 28 location, 10 in both, 7 blocks) / 21 (92 pairs with the 2 placebos) |
| Pairs: positive Final gain / identical to baseline / gain >= 2% / raw p < 0.05 and better / Holm < 0.05 and better / raw p < 0.05 and worse / Holm < 0.05 and worse | 22 / 4 / 1 / 1 / 0 / 8 / 1 | 22 / 4 / 1 / 1 / 0 / 8 / 1 |

**Agreement of the engines.** My engine on my panel against the builder's stored predictions, 19 variants (38 pairs): largest quantile difference 5.0e-7 (the file stores 6 significant digits); largest difference in pinball 6e-12, in rupee miss 1e-11, in DM p-value 9e-11. For all 92 pairs the Final gain agrees to 5e-10 and the 92-pair Holm to 1e-11. For the 46 pre-fixed pairs every input of the rule agrees with `hl2_adoption.csv`: Final gain and p-value (2e-11, 9e-11), Validation gain (1.5e-11), auction ratio (5e-13), the 50% and 90% coverage deviations of variant and baseline, including the atom-aware nominal for the after-open targets (0.0), typical miss (1e-11), Holm over 46 (6e-17).

**Feature panel.** 68 columns (58 features + 10 placebo) x 2,390 sessions: the pattern of missing values is identical in every column, and the largest relative difference is 5e-6 (storage rounding). The 16 Oct row is not in the panel (it is built live).

**Report tables.** I regenerated the report's Section 4.1 and 4.3 tables with `python3 src/hl_model2.py --tables`: all 138 table rows appear in `D_features.md` word for word.

## 3. Data checks I made on the inputs (the meaning of each row's date)

A leakage test cannot catch a table whose dates are shifted by a day, so I checked the meaning of the dates directly:
* `index_daily`: Nifty 50 close on 23 Mar 2020 is 7,610.25 in the file (the known value); India VIX close on that date 71.99. Correlation of the Nifty return with the BSE return: same day 0.35, one day lagged 0.06, one day ahead -0.00. So the date is the trading date.
* `breadth_daily`: correlation of the advance share with the Nifty return on the same date 0.70, with a one-day lag 0.02. Trading date.
* `bse_iv_daily`: on every one of the 460 dates present in the bars, the IV table's `spot` equals that day's BSE official close exactly. `peers_daily`: its BSE rows equal the bars' close on all 2,388 common dates.
* FRED `SP500`: 16 Mar 2020 = 2,386.13 (the known close), `VIXCLS` 82.69. The gap-to-S&P correlation is +0.29 for the last US session strictly before the IST date and +0.04 for the US session of the same calendar date, which closes after the Indian session; the feature uses the former. S&P and US VIX closes are public at 01:30 to 02:30 IST, before the 09:15 open, so lag zero is right for the information content.
* Yahoo fill rows (13-15 Oct) against FRED on the 62 overlapping dates: S&P largest difference 0.0002 index points, VIX 1e-6. ECB USD/INR rebuilt from Frankfurter against the Fed's `DEXINUS`: level correlation 0.9999, correlation of daily log changes 0.86 (different fixing times). The repo's own `usdinr_ecb_2017_2026.json` is an HTML error page (confirmed), so this series depends on a network fetch that I cannot re-fetch; the cross-check says it is sane.
* Bonus adjustment: `prev` is adjusted on the two ex-dates (21 Mar 2022 factor 3, 23 May 2025 factor 3), levels are raw. The panel builds price-level features through the chain of adjusted log returns. I printed `dist_hi250`, `dist_lo250`, `ret5`, `ret20`, `close_loc_c`, `pk10_rel` around both ex-dates: no jump (for example `dist_hi250` goes -0.038, -0.081, -0.033 across 23 May 2025, not -1.1).

## 4. The five-condition rule applied by me

Family: the 46 pre-fixed pairs, Holm on the two-sided Diebold-Mariano p-values of the Final window (family size 46). On my own numbers and, separately, on the builder's result files (`hl2_eval_dm_holm.csv`, `hl2_eval_summary.csv`, `hl2_leakage.csv`), with the builder's operational reading of the conditions (Section 0.2 of the report):

| target | variants | (i) gain >= 2% and Holm < 0.05 | (ii) Validation same sign | (iii) coverage not worse and Kupiec / atom-aware p > 0.05 | (iv) auction slice <= 5% worse | (v) leakage | all five |
|---|---|---|---|---|---|---|---|
| pre-open high | 11 | 0 | 3 | 5 | 11 | 11 | **0** |
| pre-open low | 11 | 0 | 9 | 1 | 11 | 11 | **0** |
| after-open high (HO) | 12 | 0 | 5 | 6 | 12 | 12 | **0** |
| after-open low (LO) | 12 | 0 | 0 | 5 | 12 | 12 | **0** |
| total | 46 | 0 | 17 | 17 | 46 | 46 | **0** |

* My own recomputation (own forecasts, own Holm) reproduces the builder's verdict on every one of the 46 pairs for each of conditions (i), (ii), (iii), (iv): 46 of 46 agree each, and the four totals 0 / 17 / 17 / 46.
* **The result does not depend on how conditions (ii) to (v) are read.** Condition (i) fails for all 46 pairs: the only pair with a gain of 2% or more (`P_SL_f` high, +2.36%) has raw p 0.072 two-sided (0.036 one-sided), and the rule asks for Holm over 46, which gives 1.00 (a one-sided test would still need a raw p below about 0.001 to survive 46 comparisons). With the 92-pair family (all post hoc and placebo pairs counted) the only pair below Holm 0.05 is `W_SL_fo` low, which is worse (Holm 0.008).
* **Power, in plain words.** The standard error of a pinball gain for the all-block variants is about 1.3 points (`P_SL_f` high: 2.36 / 1.806). To pass Holm over 46 a gain needs t of about 3.3, i.e. roughly 4 points of pinball loss (about Rs 1.7 to 1.8 on the Rs 43 miss, if pinball percent map one-for-one to the miss, which they only roughly do). So the study can reject large gains, not small ones; it cannot exclude true gains of 1% to 3% (Rs 0.4 to 1.3). The report says this (Sections 4.6 and 11); the plain-words sentence in Section 2 does not (Section 8).

## 5. Code review: look-ahead, timestamps, off-by-one, arithmetic

Read line by line; each item below was also tested by running code.

* **Targets and scale.** Targets and `prev` are those of `common.py`. `block_fit` trains on rows strictly before the block start `b0` (`rows_all` is built from `sig[:b0]`, `V[:b0]`); the ridge strength is chosen on rows before the first block of its 100-session group (`rows_all < FIT_START + k0 * BLOCK`, never later than `b0`); the cache key contains the group, so it cannot be recomputed with later rows. The Final window (and Validation) is never used to choose anything: the blocks, the ridge grid, the clip and the CV folds are fixed in the text hashed in Section 0, and all 46 pre-fixed results in the first commit that holds them (`68032e4`, 16 Oct 08:27 UTC) are identical to the final files (largest difference in gain, p and Holm 0.0).
* **Standardisation.** `Prep` winsorises at the 1st / 99th percentile of the training rows, standardises with training mean and standard deviation, sets missing to zero (= training mean); the location target is winsorised on training rows only. No future data.
* **Pool of residuals.** For session t the draws use rows t-500 .. t-1 divided by the CURRENT block's multiplier (`E = V/S - SH`); every row used was known at t-1. The multiplier uses the features of the pool rows (known then) and the current coefficients (fitted on rows before the block): in-sample for the pool, as is usual for filtered historical simulation, not a leak.
* **Rolling windows.** Every rolling statistic is computed on the full series and then lagged one session (`_lag`) or read from the table row of the previous BSE session (`at_prev`); I rebuilt all of them with a different style of code (date lookups, explicit loops) and every value matches in all 2,390 sessions. `pk10_rel` / `pk20_rel` use the baseline sigma of the session itself, known at the previous close.
* **US and FX series.** Last observation dated strictly before the IST session date (`searchsorted(..., side='left') - 1`); my explicit-loop version gives identical values.
* **FRED publication lags.** S&P 500, US VIX and the ECB USD/INR rate: lag zero is right for what was knowable (Section 3). Brent, the broad dollar index and the 10-year yield are shifted one more observation back. For the dollar index (a weekly Fed release of daily values) one observation may not cover the real posting delay, so "no look-ahead" is not provable for those three series. Two things make this harmless for the verdict: the information they summarise (FX and oil prices, bond yields) was public in real time, and they sit in the null block `b` and in `P_LO_f`/`P_SL_f`, which do not reach significance; the one signal that matters, `P_LO_sp`, uses only the S&P 500. The three FRED files stop on 2 Oct (dollar index), 6 Oct (Brent) and 8 Oct (10-year), so these features are stale or missing in the last sessions and on the live day (the report says so).
* **Bonus adjustment.** Handled through the log-return chain (Section 3, no jump at either ex-date).
* **Calendar flags.** `exp_day` uses expiry dates read from contract rows; the builder's own check shows each first appeared in a contract list at least 27 days earlier (`hl2_expiry_advance_check.csv`). `results_next` uses `data/results_dates.csv`; announcements are after market on the day before the first tradable session; the block covers 7 events and is a short-sample block anyway.
* **Conformal calibration.** There is none in this study (no conformal step, no calibration window); the quantiles come only from the filtered historical simulation.
* **Off-by-one.** Checked: `_lag` shifts, the 250-session window (`i-250 .. i-1`, at least 120 observations), the 60-session z-scores (minimum 40 or 30 observations), `ret5` = ln(C[t-1]/C[t-6]), block boundaries (`FIT_START + ((t - FIT_START) // 20) * 20`), CV fold cuts (50%, 62.5%, 75%, 87.5%, 100% of the rows; the first fold is skipped below 60 rows). No error found.
* **DM and Holm.** `metrics.diebold_mariano` (reused from the project) agrees with my independent version (Bartlett lag 5, factor sqrt((n-1)/n), t with n-1 degrees of freedom, two-sided p = 2 min(p1, 1-p1)); Holm is monotone and treats identical-to-baseline pairs (variance zero, p undefined) as p = 1 inside the family, which keeps the family size at 46 (conservative).
* **Minor code points.** A stale comment says "74 pairs" where the file holds 92 (the report says 92, correctly). The ridge-activation shares in report Section 4.2 for the combined location variants are the mean of the shares of the components (`P_SL_f`: mean of 94%, 100% and 82% = 92%), not the share of refits where any feature was on (100%).

## 6. Leakage test

* **Builder's** (`hl2_leakage.csv`, 657 rows): 417 of 417 comparisons identical (largest difference 0.0); positive controls change 189 of 240 forecasts (all 120 when the BSE bars are junked from the day before; 69 of 120 when the other tables are). 12 target sessions (3 Development, 3 Validation, 6 Final of which 3 in the auction slice; 21 Mar 2022 and 23 May 2025 are the two bonus ex-dates); 30 variants including baseline, placebos and the post hoc location variants. Re-counted by me from the file.
* **Mine, on the builder's code** (`poison_test.py`, `poison_results.csv`): for 7 target sessions (16 Jun 2021, 14 Feb 2024, 23 May 2025 (bonus ex-date), 12 Nov 2025, 3 Aug 2026, 22 Sep 2026, 15 Oct 2026) I replaced EVERYTHING dated from the target session on by extreme multiples (bars x3.7 / x0.31 / x9, index, breadth, peers, IV x6.5 + 13, US/FX series x4.4 + 7), kept the open and previous close of the target session for the after-open variants, and rebuilt the whole pipeline (sigma paths, panel, ridge, CV, quantiles) for the baseline and nine variants (`P_SL_f`, `P_LO_sp`, `P_SC_fs`, `P_TS_f`, `P_LO_f`, `W_SC_fo`, `W_SL_fo`, `W_LO_fo`): **70 of 70 comparisons identical, largest difference 0.0**. Positive control (same junk starting one session earlier): 28 of 28 forecasts changed (largest change 0.077 log points). So condition (v) is met for every variant tested, and the test can see a leak.
* **Live 16 Oct.** The forecast function cuts every table at the day before the forecast date; with the real 16 Oct bar (which `bse_daily_extra.csv` now holds) present and the cap switched off, the forecast is unchanged (largest difference Rs 0.0).

## 7. The 16 Oct 2026 forecast (`hl2_forecast('2026-10-16', 3450.0)`)

Output is sane and equals the baseline, as it should since nothing was adopted: `variants_used` = P_S6 for high and low, W_I6 for HO and LO; `adopted_variants` = none.

| | median | 50% band | 90% band | typical miss shown |
|---|---|---|---|---|
| pre-open high | 3,475.01 | 3,449.38 to 3,512.63 | 3,421.15 to 3,590.57 | Rs 42.7 |
| pre-open low | 3,390.07 | 3,351.83 to 3,418.79 | 3,268.73 to 3,449.85 | Rs 47.7 |
| after-open high (open 3,450.0) | 3,488.48 | 3,467.62 to 3,526.22 | 3,450.95 to 3,591.49 | Rs 35.0 (at the open) |
| after-open low | 3,409.87 | 3,373.59 to 3,429.64 | 3,294.26 to 3,447.12 | Rs 37.7 (at the open) |

* Difference to `hl_model.hl_forecast` over every printed quantile: Rs 0.00. Stored `results/hl2_2026-10-16.json` against a fresh run: Rs 0.00.
* **I rebuilt this baseline forecast independently** (own GARCH x HAR next-session sigma 2.4348% close-to-close and 2.2159% open-to-close, own trailing-500 residual pool): all 16 numbers above agree to the paisa. It uses BSE bars through the 15 Oct close and the open of 3,450.0 and nothing else.
* **What the function reads beyond that.** For the non-default `all_variants` comparison it also reads the 15 Oct India VIX, breadth, peers, delivery and IV rows (known by the evening of 15 Oct), the ECB USD/INR rate of 15 Oct (fixed 14:15 CET) and the S&P 500 / US VIX closes of the 15 Oct US session, which closed at 01:30 to 01:45 IST on 16 Oct, i.e. after a strict 22:00 IST cut-off on 15 Oct. That is legitimate for a user trading at 11:00 IST (the information was public before the open) and the brief's own rule ("dated strictly before the Indian session date"), but the headline forecast does not use it; the post hoc S&P numbers (3,478.6 / 3,394.9) do. Four features (Brent, dollar index, levels and changes) are missing on the live day and count as zero effect.
* `words2()` prints a caution about the closing-auction slice (the pre-open high fell below its 5% level on 15% of the 52 sessions) as `hl_model.words()` does. It drops the touch-probability lines and the gap line, and says "19 days in 20 below Rs q95 (5% quantile Rs q5)" for the low too, which reads oddly. Not used while the baseline stays.
* **Fresh day, 16 Oct (n = 1, descriptive).** Realised high 3,455.0, low 3,310.6 (from `bse_daily_extra.csv`): baseline medians miss by Rs 20.0, 79.5, 33.5, 99.3; both extremes inside the 90% bands; variants split both ways (best +9.2%, worst -20.6% pinball). I re-derived the misses and the position in each distribution from the stored forecasts and the bar; the counts of variants better / worse / identical (4 / 7 / 2, 0 / 11 / 2, 2 / 8 / 3, 6 / 4 / 3) match the file. One session ranks nothing.

## 8. Over-claims, selection, small samples, contradictions

**Corrections to make (all minor):**
1. **Pre-registration order is the builder's own record.** The SHA-256 of Section 0 (`1274b181...`) is unchanged: I recomputed it from the working-tree file and from the first commit that holds the report (`68032e4`, 16 Oct 08:27:36 UTC). But that commit holds Section 0 AND the first results (`hl2_eval_dm_holm.csv`, `hl2_adoption.csv`, ...) together, and the file timestamps of the first run were overwritten on 17 Oct, so git cannot show that the text was written before the results. What I can show: the 46 pre-fixed pairs have identical results in that commit and now; the 21 post hoc variants appear only in later commits; I diffed the first committed `hl_model2.py` against the current one: the changes are additions (leakage test, forecast function, post hoc variants, extra tables), the 15 Oct 2026 data cap, a refactor of the adoption code into a function with the same expressions, and the stricter 'features used' definition for the two own-window variants (disclosed in the report's Section 1). No window, loss, test or condition of the rule was changed. Say "rule fixed in a hashed text before the final run, order as recorded by the builder", not "independently time-stamped".
2. **Over-reaching sentence in Section 2** ("most of what is left is the genuine day-to-day randomness of where the extremes land, not information I failed to feed in"). The study shows that these inputs, through a log-linear scale multiplier and a linear shift on top of S6, do not detectably sharpen the forecast; it did not show what the remaining miss consists of. Untested: GIFT Nifty, NSE pre-open order book, FII/DII flows, non-linear or quantile-regression models (other specialists), and gains of 1% to 3% (Section 4). Suggested wording: "the extra inputs I tried change the typical miss by at most about Rs 1 (not established); this test could not detect smaller changes".
3. **Builder's pointer summary counts**: "10 pre-open and 13 post-open variants" is wrong. The code and Section 0.5 have 11 pre-open and 12 after-open (23 in all). The report itself does not repeat the wrong split.
4. **Implied volatility wording.** "BSE option-implied vol adds nothing (+0.01 / +0.00%)" is a weak test as built: the walk-forward fits all earlier rows with the IV features set to zero (history before Dec 2024), so the ridge sees about 1,800 uninformative rows next to 120 to 300 informative ones, and the cross-validated block was first active on 9 Mar 2026. I re-tested with a true own-window fit (only rows where IV exists, at least 120 rows, refit every 20 sessions, cross-validated or fixed ridge, 3 IV features / IV-minus-realised spread alone / all six short-sample features): on 280 to 320 Final sessions the pre-open gains are between -0.52% and +0.73% (all p >= 0.26), the after-open gains between -0.84% and +0.91% (all p >= 0.085), the rupee change of the typical miss at most Rs 0.3. So the null stands, now on a better-designed test, but it is "about 300 sessions, no detectable gain", not "proved to add nothing". The univariate association is real (Spearman +0.27 in Final, n = 319, reproduced) and did not become a forecast gain.
5. **One placebo draw.** "The pipeline does not manufacture gains out of noise" rests on one set of 10 random columns (seed 20261016) plus the forced-in fixed-ridge versions (Final gains between -0.62% and +0.62%). That is a fair noise floor but a single draw; do not quote it as a false-positive rate.
6. **Post hoc S&P shift.** The report labels it correctly. Quote it only as post hoc. The p-values (0.0707 / 0.0030, 0.049 / 0.019 for the rupee miss, "<0.001" pooled) are optimistic because the S&P return was singled out from a coefficient table that covers every block including the Final window; the honest number is Holm 0.25 over the 92 pairs tried (low) and 1.00 (high). What is solid: the direction is the same in Development, Validation, Final and the auction slice and in 6 of 7 calendar years (I reproduced the year table exactly), the effect is a few rupees (Rs 1.1 / 1.3 off the typical miss), and the relationship has an independent basis in the project's v2 report (previous US session to gap, slope 0.276 pp per 1%, out-of-sample R2 +7.85%, independently reproduced). That same v2 row says the **slope is unstable** (0.03 in 2019 to 0.68 in 2026); the D report's Section 5 should cite this, because it matches the weak years 2021, 2024 and 2025 in its own table.
7. **Selection note.** Reported correctly: 46 pairs in the Holm family, 92 counted with post hoc and placebo pairs; the "best of 23 on Final (hindsight)" column is labelled optimistic. I found no unadjusted selection presented as a result.
8. **Presentation (trivial).** The activation shares of combined variants (Section 5), the stale "74 pairs" comment, and `words2()` wording.

**Checked and found fine:** no contradiction with `A_dayahead.md` or `verify_A_dayahead.md` (weekday and gap-size nulls agree; A listed the S&P cue as "about Rs 2 on the median, not used on purpose", D finds Rs 1.1 to 1.3 on the typical miss, same order); `B_liveintraday.md` (realised volatility so far and range so far did not help the live bands) agrees in spirit; `FORECAST_REPORT.md` line 145 ("options-implied 2.43% per day: on par with S6, p = 0.76, 339 sessions") is quoted correctly. The coverage statements, the 50% and 90% band tables, the auction-slice ratios (worst 1.034 `W_TS_fo` HO, best 0.979 `P_SL_f` L), the 16 numbers of the live table, and all counts in Section 12 of the report are right. The 90% band of the after-open high is not a 90% band (95.0% in Final; atom at zero); the report handles this correctly with the atom-aware check.

## 9. What the lead may quote

**As they stand (each reproduced by my own code unless marked):**
* Baseline typical miss, Final n = 320, at Rs 3,428: pre-open high Rs 42.7, low Rs 47.7; after the 09:08 open Rs 34.8 / 37.4; 'price stays' Rs 62.9 / 61.3; 'open stays' Rs 51.3 / 59.0.
* "No extra parameter met the pre-fixed rule for any of the four targets: 0 of 46 variant-target pairs (23 variants, 58 features in 7 blocks, Holm family of 46)."
* Best pre-fixed pair: pre-open high with everything as scale and shift, +2.36% pinball, raw p 0.072, Holm 1.00, typical miss Rs 41.8 against Rs 42.7. Largest improvement of the typical miss by any pre-fixed variant: Rs 0.9 pre-open, Rs 0.5 after the open; largest worsening Rs 1.2 (after-open low, Holm 0.004).
* Counts: of 46 pairs, 22 positive in Final (4 identical to the baseline), 1 reaches 2%, 1 has raw p < 0.05 in the right direction, 0 after Holm; 8 worse at raw p < 0.05, 1 worse after Holm.
* Block results as pre-open Final gains high / low: India VIX 0.00 / 0.00%, US overnight block -0.17 / +0.07%, Indian market and peers +0.66 / -0.40%, BSE own history +0.11 / -0.15%, calendar -0.05 / -0.14%, all five +0.60 / -0.09%; after the open all blocks plus gap +1.20 / -1.93%. Quote with "n = 320, none distinguishable from zero".
* After the open the extras hurt the low (-1.9% to -3.9% pinball, typical miss up to Rs 1.2 worse): reproduced.
* Leakage and timestamps: 417 of 417 builder comparisons identical, plus my own 70 of 70 (different junk) with positive controls 28 of 28; panel against independent rebuild: every value of 68 columns in 2,390 sessions.
* 16 Oct forecast (baseline): pre-open high 3,475 (50%: 3,449 to 3,513; 90%: 3,421 to 3,591), low 3,390 (3,352 to 3,419; 3,269 to 3,450); after the 3,450.0 open high 3,488 (3,468 to 3,526), low 3,410 (3,374 to 3,430).
* S&P shift, only as: "a post hoc candidate, not adopted: +2.1% / +2.9% pinball, about Rs 1.1 / 1.3 off the typical pre-open miss, same sign in 6 of 7 years, zero effect after the open; to be scored forward".

**To correct before quoting:**
* "10 pre-open and 13 post-open variants" -> 11 pre-open and 12 after-open.
* "More parameters do not sharpen that, because most of what is left is genuine randomness" -> "the extra inputs tried change the typical miss by at most about Rs 1, which this test cannot establish; gains under about 4% of pinball loss (Rs 1.7) could not have been detected".
* "Implied volatility adds nothing" -> "about 300 sessions with option data: no detectable gain (two different tests)".
* "Section 0 was written before any result" -> "fixed in a hashed text before the final run; the order is the builder's own record".
* Ridge "share of refits" for combined variants: "mean over the components".

**Do not quote:**
* The raw p-values of the post hoc S&P variants as evidence (0.049, 0.019, 0.003, "< 0.001"); use Holm 0.25 (low) / 1.00 (high) over 92 pairs, or nothing.
* Any ranking of variants from the single day of 16 Oct (best +9.2%, worst -20.6%; n = 1).
* "Validated", "proved no effect", "implied volatility is useless", "the S&P effect is real and adopted".
* The 'best on Final (hindsight)' column as an expectation: it is picked with hindsight.
* `words2()` text in place of `hl_model.words()`.

## 10. Limits of this verification, and how to reproduce it

Not checked: the raw NSE files themselves (I trust the project's data build; I checked internal consistency and known values); the Frankfurter / Yahoo rows beyond the FRED overlap and a plausibility cross-check; the coefficient tables of report Section 8 beyond the S&P coefficient and the Spearman screen (reproduced: `sp_ret` +0.185 / +0.226 high, +0.218 / +0.271 low, US VIX change -0.14 / -0.24 and -0.17 / -0.26, IV-minus-realised +0.19 (n = 143) / +0.27 (n = 319), `abs_sp` +0.08 / +0.06); the original 08:24 UTC result stamps (overwritten). My engine follows the builder's documented design, so it confirms implementation, arithmetic and look-ahead, not that a different design (quantile regression, boosted trees, analogue days) could not do better; that is for the other specialists. 320 Final sessions and one market regime; the auction slice (52 sessions) is one drawdown episode.

Scratch scripts (all in `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vD/`; run from that directory unless stated; about 3 minutes in all, plus 4 minutes for the poison test):
```
python3 own_base.py          # own baseline sigma paths and quantiles          -> own_base.npz
python3 chk_base.py          # baseline Final / auction metrics, benchmarks, comparison with stored project files
python3 own_features.py      # own 68-column panel + comparison with results/hl2_features_panel.csv.gz
python3 run_own_variants.py  # own engine, 46 variants (92 pairs)              -> own_Q_*.npy, own_N_*.npy
python3 cmp_variants.py      # own vs builder: quantiles, gain, p, miss, pinball
python3 apply_rule.py        # five-condition rule on my own numbers, Holm over 46
python3 posthoc_check.py     # 92-pair Holm, S&P shift windows / years / lags / paired miss test, S&P bucket table
python3 iv_ownwindow.py      # true own-window implied-vol re-test
cd /home/user/pred_18 && python3 <scratchpad>/vD/poison_test.py     # my leakage test of the builder's code (about 4 min; writes nothing in the repo)
cd /home/user/pred_18 && python3 <scratchpad>/vD/live_check.py      # hl2_forecast vs hl_model vs stored JSON
```
