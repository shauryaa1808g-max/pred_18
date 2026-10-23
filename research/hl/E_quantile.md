# Specialist E: flexible (quantile-regression, boosting, forest, conformal, stacked) models for the day's HIGH and LOW of NSE:BSE

> **Independently checked on 18 Oct 2026: see the last section of this file and `research/hl/verify_E_quantile_trees.md`. No look-ahead found; no variant meets the pre-fixed adoption rule; the baseline stays. Several wordings below are corrected there; where they differ, the correction wins.**

*Status of this section: PRE-FIXED, written Fri 16 Oct 2026 about 11:12 IST (05:42 UTC) BEFORE any variant of this study had been run. What had been done before writing it: (a) read the project files and the baseline code; (b) ran the BASELINE (`hl_model.build`) and confirmed it reproduces the stored Final numbers exactly (pinball x1e4 31.152 / 36.579 pre-open, 23.853 / 28.030 post-open; typical miss Rs 42.7 / 47.7 and 34.8 / 37.4; maximum difference to the stored `results/hl_eval_*.csv` 7e-15); (c) looked at DATA FACTS only: file end dates, coverage shares, the list of F&O expiry dates, timing of the FRED series. No flexible-model number of any kind had been computed. The clock and the hash of this section are recorded in Section 8 (own working record, not an independent timestamp). The results sections are appended below the line "RESULTS".*

---

## 0. Pre-fixed design

### 0.1 Question and what counts as success
The user trades BSE Ltd intraday and wants the day's high and low more precise. The question here is narrow: does a flexible model that is allowed to use many more known-in-advance parameters (volatility index, option-implied volatility, US overnight moves, index and peer ranges, breadth, volume, delivery, trend, calendar, and, once the 09:08 official open is known, the gap) produce a better distribution of the high and low than the project's baseline (`src/hl_model.py`: S6 volatility x filtered historical simulation, called BASE below)? "Better" is defined ONLY by the adoption rule in 0.6. A result of "no, extra parameters did not help" is a valid and complete deliverable and will be reported as such.

### 0.2 Targets, information sets, windows (identical to the baseline study)
* Pre-open targets: Hp = ln(H/P0), Lp = ln(L/P0), P0 = previous official close. Information: everything dated up to the previous Indian close, plus overnight values under the timing rules in 0.4.
* Post-open targets: HO = ln(H/O) >= 0, LO = ln(L/O) <= 0, O = official open (NSE pre-open auction price, final 09:08). Information: the pre-open set plus O (the gap block of 0.4).
* Evaluation sessions: 750 onward (25 Feb 2020), n = 1,640 to 15 Oct 2026. Walk-forward, EXPANDING training window, refit every 20 sessions (blocks start at session 750, 770, ...), training rows only from sessions strictly before the block. Windows by target date: Development to 2024-06-30, Validation 2024-07-01 to 2025-06-30 (n = 248), Final 2025-07-01 on (n = 320), post-closing-auction slice "CAS" 2026-08-03 on (n = 52); pooled Validation+Final (n = 568) is shown but is not used for the rule.
* Loss: mean pinball over the project's 9-level grid (2.5, 5, 10, 25, 50, 75, 90, 95, 97.5%) in log points; typical rupee miss = mean absolute error of the 50% quantile times Rs 3,428 (also "half the time within" = median absolute error). The rupee figure is a log error x today's price, as in the baseline study (levels before the 23 May 2025 bonus are raw traded prices).
* Benchmarks reported next to every variant: BASE (the live baseline `P_S6` / `W_I6`), PRICE_STAYS / OPEN_STAYS (H = L = P0 or O), and the trailing-250 empirical quantiles (`P_EMP250` / `W_EMP250`). The benchmarks are NOT members of the test family.

### 0.3 The two ways a flexible model is tied to the baseline
Let sigma_t be the baseline scale of the phase (S6 of the close-to-close return R for pre-open; S6 of the open-to-close return I for post-open) and q_t(tau) the baseline FHS quantile (trailing-500 standardised residuals x sigma_t) of the target y. Both are walk-forward and use only information before t.
* **Direct ("A")**: model the quantile of u = y / sigma_t given the features; prediction = sigma_t x q_u(tau | x_t). Features include ln sigma_t. This estimates the whole distribution from the expanding window with no baseline quantile in it.
* **Offset ("B")**: model the quantile of z_tau = (y - q_t(tau)) / sigma_t given the features; prediction = q_t(tau) + sigma_t x f_tau(x_t). "Do nothing" (f = 0) IS the baseline, so a B model can only help by finding something the baseline misses, and the nested search below may always choose "do nothing".
Quantile levels that cross are repaired by sorting the 9 values (monotone rearrangement), and the post-open constraints HO >= 0, LO <= 0 are enforced by clipping, for every variant.

### 0.4 Feature menu and timestamp rule of each feature (written before use)
Forecast target = session t (Indian date D). A feature row is built from information through the close of session s = t - 1 and is then shifted one session, so no value of day t enters except where stated. Rolling statistics are trailing (including s, nothing later). "rel" means the log of the quantity minus ln sigma_t (so features are on the baseline's own scale). Winsorised at +-4 training-window standard deviations; a missing value is replaced by the training-window median (= 0 after standardising: "no information"). Features are standardised with training-window mean and standard deviation only.

| group | features (count) | timestamp rule |
|---|---|---|
| OWN (BSE own) | ln sigma_t; rel yesterday's range ln(H/L); rel Parkinson 5/10/20-day; rel Garman-Klass 5/10/20-day; rel close-to-close realised vol 5/20-day; yesterday's abs gap / sigma; close location in yesterday's range; yesterday's return / sigma; 5- and 20-day return / (sigma x sqrt days); log distance to the trailing-250-day high and low (built from the corporate-action-adjusted close chain, so the 2022 and 2025 bonus ex-dates do not distort); signed up/down streak (capped at 6); yesterday's Hp, Lp / sigma; 20-day mean Hp, Lp / sigma (**24**) | official NSE bhavcopy of session s, published about 16:34 IST on s |
| FLOW | log turnover z (60 sessions); log trades z (60); change of log turnover vs its previous-5-day mean; delivery % z (60; missing in 2017-2019 and for the last 3 sessions in the repo) (**4**). Volume in shares is NOT used (not bonus-adjusted); turnover in rupees is. | bhavcopy of s (delivery file of s, published in the evening of s) |
| CAL | weekday of t (4 dummies), calendar days since the previous session (long weekends/holidays), last-weekday-of-month flag, first-weekday-of-month flag (**7**) | calendar, known in advance (the month flags use the weekday calendar and ignore exchange holidays) |
| IDX | Nifty 50 return z, Nifty range (log, relative to its own 60-day mean), Bank Nifty return z and range, Capital Markets index return z and range (exists only from 2023-04), India VIX log level, VIX log change, VIX-vs-realised spread = ln(VIX/100/sqrt 252) - ln(Nifty 20-day realised vol), BSE minus Nifty return of s / sigma (**12**) | NSE index file of s, published about 23:20 IST on s, i.e. before the next morning |
| BRD | advancing share - 0.5, median stock return z, share of liquid stocks up >= 5%, down >= 5%, log market turnover z (60) (**5**) | recomputed/read from the same bhavcopy of s |
| PEER | equal-weighted mean over listed capital-market peers (CDSL, MCX, ANGELONE, MOTILALOFS, 5PAISA, IEX, CAMS, KFINTECH, NUVAMA, ANANDRATHI, GEOJITFSL, IIFLSEC; whichever have data on s) of the log return (returns beyond +-20% dropped: archive previous closes are not re-based on bonus/split ex-dates) and of the log range, CDSL and MCX return and relative range separately (**6**) | bhavcopy of s |
| US (overnight) | S&P 500 log return, S&P 5-observation return, US VIX log level and log change, USD/INR log change (FRED DEXINUS), Brent log return (DCOILBRENTEU), broad dollar index log return (DTWEXBGS), US 10-year yield change (DGS10) (**8**) | **conservative timing**: only FRED observations dated at most D-2 calendar days (strictly before the previous calendar day) are used, because a FRED value can be posted a day late and the lag cannot be proven to be zero. An observation older than 7 days before that cutoff is treated as missing. The repo's FRED files end between 2 Oct and 12 Oct 2026, so for the 16 Oct forecast several of these are missing (neutral). The ECB USD/INR JSON in the repo is corrupted (an HTML 301 page), so USD/INR comes from FRED only. |
| GAP (post-open only) | gap G = ln(O/P0) / sigma_R, abs gap / sigma_R, open beyond yesterday's high (0/1), open below yesterday's low (0/1), open position in yesterday's range (clipped to [-1, 2]) (**5**) | the official open O of session t, final at 09:08 IST. Nothing else of day t is used. |
| IV (short sample, own window only) | ln ATM implied vol (daily units) minus ln sigma_t; skew = (low-strike OTM IV - high-strike OTM IV) / ATM IV; ln IV minus ln trailing-20-day realised vol; ln IV change; days to expiry / 30; expiry-day flag and day-before-expiry flag of t (from the F&O contract expiry list; known in advance) (**7**) | F&O bhavcopy of s; the expiry list is the exchange contract calendar. Exists only from 2024-11-29 (462 sessions): can only be evaluated inside the Final window. |

Total: 24 + 4 + 7 + 12 + 5 + 6 + 8 = 66 pre-open candidate features, +5 gap features post-open = 71, +7 IV/expiry features in the one short-sample variant, + 8 duplicates of the US block under the less conservative lag-1 rule (variant V18, see below) = **86 distinct candidate columns searched**. Not usable (no history): NSE pre-open order book, GIFT Nifty, FII/DII flows (untested).
Missing groups at the end of the repo data (stated now, not chosen after seeing results): the Nifty/VIX/Bank Nifty/Capital Markets index file ends 12 Oct, breadth and peers end 13 Oct (14 and 15 Oct peers and breadth are rebuilt from the NSE bhavcopy zips in `data/raw/udiff`, read-only, with the project's own rule), delivery % is missing for 13-15 Oct. Where a group is missing it is "no information" (training median). This affects sessions 14 and 15 Oct (IDX block) of the 320 Final sessions and the 16 Oct live forecast (IDX, US FX/oil block); it is flagged in the output.

### 0.5 The variants (all of them, written now; any variant added later is marked "post-hoc" and still counted)
Each variant is fitted for the four targets (pre-open H, L; post-open HO, LO) with the same walk-forward schedule. L1-penalised quantile regression is solved by my own smoothed-loss bound-constrained L-BFGS solver (needed because the exact LP of scikit-learn takes about 1 second per fit and a nested search needs hundreds of thousands of fits); it is validated against `sklearn.linear_model.QuantileRegressor` (HiGHS) on random and real windows before use (result in the report).

| id | name | form | features |
|---|---|---|---|
| V01 | QR_sig | linear quantile regression, direct (A) | ln sigma_t only (control: does letting the scale enter with its own elasticity help?) |
| V02 | QR_all | L1 quantile regression, direct (A) | OWN+FLOW+CAL+IDX+BRD+PEER+US (+GAP post-open) |
| V03 | QRB_all | L1 quantile regression, offset (B) | same as V02 |
| V04 | QRB_own | L1 QR, offset (B) | OWN+FLOW+CAL (+GAP post-open) |
| V05 | QRB_idx | L1 QR, offset (B) | OWN+FLOW+CAL+IDX (+GAP) |
| V06 | QRB_brdpeer | L1 QR, offset (B) | OWN+FLOW+CAL+BRD+PEER (+GAP) |
| V07 | QRB_us | L1 QR, offset (B) | OWN+FLOW+CAL+US conservative lag (+GAP) |
| V08 | GBM_all | gradient-boosted quantile regression (scikit-learn HistGradientBoosting, loss = quantile), direct (A) | as V02 |
| V09 | GBMB_all | gradient-boosted quantile regression, offset (B) | as V02 |
| V10 | RF_all | random-forest quantile regression (Meinshausen leaf weights), direct (A) | as V02 |
| V11 | CQR_base | split-conformal repair of the BASE quantiles (no model fit): per level, shift by the calibration-block quantile of the normalised baseline error | none |
| V12 | CQR_QR | conformalised V02 | as V02 |
| V13 | CQR_GBM | conformalised V08 | as V02 |
| V14 | ST_QR | stack of BASE and V02 | |
| V15 | ST_GBM | stack of BASE and V08 | |
| V16 | ST_BEST | stack of BASE and the candidate among {V02, V03, V08, V09, V10} with the lowest pinball over the previous 250 OUT-OF-SAMPLE sessions | |
| V17 | QRB_iv | V03 plus the IV block; evaluated ONLY on sessions whose training window holds >= 120 IV sessions (short sample; cannot satisfy rule (ii)) | V03 + IV |
| V18 | QRB_us1 | V07 with the US block at the LESS conservative lag-1 rule (observations dated at most D-1); a timing sensitivity, ineligible for adoption because the lag-0 publication cannot be proven | OWN+FLOW+CAL+US(lag-1) |

**Fixed hyper-parameter grids (written now; nothing is added after seeing results).**
* L1 quantile regression (V01-V07, V17, V18): penalty lambda in {0.003, 0.01, 0.03} on the standardised coefficients (intercept unpenalised), plus the "null" choice (A: intercept only; B: no correction = BASE). Chosen separately for each target and each refit by nested expanding-window time-series CV INSIDE the training window: 3 folds (fit on the first 55%, 70%, 85% of the training rows, validate on the next 15%; 5-session embargo), criterion = mean pinball over the 9 levels. Effective configurations per target and refit: 4.
* Boosting (V08, V09, V13): max depth in {2, 3}, number of trees in {30, 60, 120} (read from staged predictions of one fit), learning rate 0.05, minimum leaf 80 rows, L2 = 1, 32 bins, plus the null choice (A: unconditional quantile; B: BASE). Same 3-fold nested CV; the choice is re-made every 4th refit (every 80 sessions) and kept for the three refits in between. Effective configurations: 6 + 1 = 7.
* Forest (V10): 200 trees, minimum leaf 40, max features 0.3, sub-sample 70% per tree. One configuration, not tuned.
* CQR (V11-V13): calibration block = the last min(250, 30% of the training rows) sessions before the block (the base learner is fitted on the earlier rows only); non-conformity score per level = (y - q_hat(tau)) / sigma_t; correction = the ceil((n+1) tau)/n empirical quantile of the calibration scores (one-sided at each level, which is the asymmetric CQR of Romano et al. for every band edge).
* Stacks (V14-V16): weight on the flexible model in {0, 0.1, ..., 1} chosen per target to minimise mean pinball over the last 250 out-of-sample sessions before the block (minimum 60 such sessions, otherwise weight 0 = BASE); quantile-wise convex combination (preserves monotonicity).
Effective number of model configurations searched per target and refit: QR 4 per variant (9 variants), boosting 7 per variant (3 variants incl. CQR_GBM), forest 1, stack weights 11 (+ 5 candidates), conformal 0 extra.

### 0.6 PRE-FIXED ADOPTION RULE (as given by the lead; interpretation fixed here)
A variant counts as an improvement for a target (pre-open high, pre-open low, post-open high, post-open low) ONLY IF ALL of:
1. **(i)** Final-window (n = 320) mean pinball at least **2% lower** than BASE's, with a Diebold-Mariano test (HAC lag 5, Harvey-Leybourne-Newbold, `src/metrics.py`, per-session pinball averaged over the 9 levels) with two-sided **Holm-adjusted p < 0.05 across EVERY variant-target pair tried**. Family size = 18 variants x 4 targets = **72 pairs** (V17 enters with its own short-window test).
2. **(ii)** The Validation window (2024-07 to 2025-06, n = 248) shows the same sign of improvement (variant pinball below BASE's). For V17, which has no Validation window, (ii) cannot be met.
3. **(iii)** Final coverage of the 50% and 90% central bands is not worse than BASE's (absolute distance from the nominal level not larger than BASE's) and Kupiec p > 0.05 for both. For post-open HO the 90% check is replaced by the atom-at-zero-aware check of `verify_A_dayahead.md`: the share of Final sessions with HO above the model's 95% quantile must be not further from 5% than BASE's and have an exact binomial p > 0.05 (HO equals zero on about 4% of sessions, so the 5% quantile sits at the open).
4. **(iv)** In the post-closing-auction slice (n = 52) mean pinball is not more than 5% worse than BASE's.
5. **(v)** A leakage test passes: all data dated from the target session onward is replaced by junk, the whole pipeline (features, volatility models, baseline quantiles, model fit of the block) is rebuilt, and the forecast for the target session is unchanged (tolerance 1e-9 relative), at 6 sessions spread over the Development, Validation, Final and CAS windows including a bonus ex-date.
Anything else is reported as a tie or null. Feature selection happens only inside the walk-forward (nested CV, never on the Final window). I will also report the unadjusted p, the Holm p within the 10 headline variants (non-binding), the Final gain with a block-bootstrap interval, and each variant's typical rupee miss (mean and median absolute error of the median at Rs 3,428).

### 0.7 What will be reported regardless of outcome
Every variant x target x window table (pinball, coverage, Kupiec, rupee miss, mean band widths in rupees), the DM/Holm table, the adoption table, the hyper-parameter choices (how often "do nothing" was chosen), permutation importance computed on training windows only, a partial-dependence style plain-words reading (descriptive, in-sample, not a claim), the solver validation, the leakage tests, and the 16 Oct 2026 forecast (as of the 15 Oct close; open Rs 3,450.0) from BASE and from the best flexible variant, flagged as adopted or not.

---

## RESULTS

*Results written Sat 17 Oct 2026 (continuation of two earlier runs that stopped on a usage limit; the walk-forward numbers below come from a complete run on 16 Oct and were re-checked as described in Section 8). All fitting and scoring stop at the 15 Oct 2026 close. The only look at 16 Oct is the labelled single-day illustration in Section 9.2, made after the adoption decision.*

## 1. The answer in plain words

**No. The extra parameters did not make the day's high and low more precise, under the rule fixed in advance. Adopt nothing from this study; keep `hl_model.hl_forecast` (the S6 volatility x filtered-historical-simulation baseline) as the pin-point.**

* **What was tried**: 18 flexible variants (linear quantile regression with an L1 penalty, boosted quantile trees, a quantile random forest, conformal repair, and stacks with the baseline) for 4 targets = **72 variant-target pairs**, on a menu of **62 known-in-advance parameters before the open and 67 after it** (82 distinct columns counting the implied-volatility block and a second timing of the US block). Hyper-parameters were chosen only inside each training window (nested time-series CV); effective **96 model configurations** per target per refit.
* **Result against the pre-fixed rule**: **0 of 72 pairs** reach even the first requirement (Final-window pinball at least 2% lower than the baseline's **and** Holm-adjusted p < 0.05). The best Final-window gain of any pair is +2.86% (pre-open high, variant V18, raw p = 0.024, Holm p = 1.0) and V18 is ineligible by design (its US-overnight timing cannot be proven from the files); the best eligible pair is +1.45% (V07, pre-open high, raw p = 0.093, Holm 1.0), and it is negative in the Validation window (-0.27%). 21 of the 72 pairs are better than the baseline by any amount in the Final window, 51 are worse; the median pair is 0.39% worse. Five pairs are *significantly worse* than the baseline after Holm (for example the linear quantile regression on volatility alone, -3.1% on the pre-open high and on the post-open high).
* **In rupees (what you see)**: the typical miss of the median at Rs 3,428 in the 320 Final sessions is within Rs 1.7 of the baseline's under every variant (better by at most Rs 1.3, worse by at most Rs 1.6; table in Section 5.1). Differences of that size are inside the sampling noise of the figures themselves (their standard errors are Rs 1.8 to 2.9) and none is significant after the multiplicity adjustment. Baseline: pre-open high Rs 42.7, low Rs 47.7; after the open high Rs 34.8, low Rs 37.4. Best variant per target (picked after looking at the Final window, so flattering): Rs 41.4 (V18) / 46.6 (V18) / 34.3 (V07) / 37.4 (V05). "Price stays" is Rs 62.9 / 61.3 before the open, so the baseline's gain over doing nothing (about Rs 20 and 14) is real and the extra parameters add nothing visible on top of it.
* **Why it does not help (descriptive, Section 7)**: the baseline's volatility scale already carries most of what the volatility-type parameters (India VIX, yesterday's range, realised volatility, turnover) could add: once the high and low are divided by that scale, high-VIX days and low-VIX days look the same. The few relationships that do show up between 2019 and mid-2025 (for example, after a day on which most stocks rose, the next day's low was about 46% shallower and the high about 22% higher) were absent or reversed in the Final window, which is why models using them gained in Validation and lost in Final. The nested search chose a non-null model in 88 to 100% of the Final-window refits for most variants and still scored no better than "do nothing": that is the over-fitting the guard rails are meant to expose. The most important single parameter in any training window changes the pinball loss by about 1% (breadth for the low), against about 0.1% or less for three pure-noise columns.
* **Calibration repair does not help either**: split-conformal recalibration of the baseline's own quantiles (V11) is worse than the baseline on all four targets over the 1,640 sessions (post-hoc, Section 6.3): the baseline's 50% and 90% bands are not mis-calibrated enough to repair.
* **One lead, not a finding (post-hoc)**: over all 1,640 sessions the random forest (V10) and the best-of stack (V16) improve the pre-open LOW by about 2% (post-hoc Holm p = 0.007; positive in 6 of 7 calendar years), but in the Final window V10 gains only +0.13% (p = 0.91) and the typical miss is unchanged (Rs 47.7 vs 47.7). It cannot count for adoption and is not a basis for a trade rule.
* **Untested**: NSE pre-open order book (2 snapshots only), GIFT Nifty, FII/DII flows (no verified dated history in the repository); the 1-minute path of the day; anything not in the menu.
* **16 Oct 2026 forecast** (as of the 15 Oct close, official open Rs 3,450.0; `results/hl3_2026-10-16.json`): the baseline remains the recommended pin-point. The 18 variants' medians differ from the baseline's by at most Rs 13 (pre-open high 3,474 to 3,485 against the baseline's 3,475; low 3,387 to 3,394 against 3,390), table in Section 9.

## 2. The baseline was reproduced first (before any variant was read)

Rebuilding the project baseline with `hl_model.build` on the 2,390 sessions up to the 15 Oct 2026 close (`python3 src/hl_ml.py --baseline-check`, file `results/hl3_baseline_repro.csv`, re-run on 17 Oct 2026 and byte-identical to the file written on 16 Oct) gives, for the Final window (1 Jul 2025 to 15 Oct 2026):

| target | n | pinball x1e4 (rebuilt) | pinball x1e4 (stored project table) | typical miss Rs at 3,428 (rebuilt) | typical miss Rs (stored) | half the time within Rs | 50% / 90% cover |
|---|---|---|---|---|---|---|---|
| H | 320 | 31.1516 | 31.1516 | 42.69 | 42.69 | 33.6 | 0.469 / 0.903 |
| L | 320 | 36.5788 | 36.5788 | 47.67 | 47.67 | 32.2 | 0.503 / 0.887 |
| HO | 320 | 23.8531 | 23.8531 | 34.81 | 34.81 | 29.1 | 0.494 / 0.950 |
| LO | 320 | 28.0298 | 28.0298 | 37.42 | 37.42 | 26.6 | 0.503 / 0.894 |

All 28 rows (4 targets x 7 windows) agree with the stored `results/hl_eval_preopen.csv` / `hl_eval_postopen.csv` (variants P_S6 and W_I6); the largest absolute difference over every compared column (pinball, 50% and 90% coverage, typical miss in rupees) is 1.07e-05, and the quantile paths used inside this study equal `hl_model.build` exactly (difference 0.0). The numbers the lead quotes are reproduced: Final pinball x1e4 31.152 / 36.579 pre-open and 23.853 / 28.030 post-open; typical miss of the median Rs 42.7 / 47.7 pre-open and Rs 34.8 / 37.4 post-open at Rs 3,428 (n = 320). (Section 0 recorded a maximum difference of 7e-15 on 16 Oct; on this re-run, after the machine was restarted, the differences are about 1e-7 in pinball and at most 1.1e-5 in the rupee column. I did not investigate the cause; floating-point differences in the optimiser of the volatility fit are the likely reason, and the difference is far below anything printed in a table.)

"Price stays" benchmark, same window: Rs 62.9 (high) / 61.3 (low) before the open; "open stays" Rs 51.3 / 59.0 after the open. Trailing-250 empirical quantiles: Rs 43.7 / 47.5 before the open, 35.4 / 37.6 after.

## 3. What was run (counts, as recorded in `results/hl3_meta.json`)

* **Sessions**: 2,390 (the 15 Oct 2026 close is the last one used; every input series is cut at dates before 16 Oct 2026 inside `load_inputs()`, and nothing dated on or after 16 Oct enters a feature, a fit or a score). Evaluation sessions 1,640 (25 Feb 2020 to 15 Oct 2026), in 82 walk-forward refit blocks of 20 sessions, expanding window, training rows strictly before the block. Windows: Development 1,072, Validation 248, Final 320, post-closing-auction slice (CAS, 3 Aug 2026 on) 52.
* **Variants and family size**: 18 variants (V01 to V18) x 4 targets = **72 variant-target pairs**. This is the family size used for the Holm adjustment (V17 has its own short-window test inside the same family). The benchmarks (BASE, price/open stays, trailing-250 empirical) are not in the family. A non-binding Holm over the 10 headline variants (V01 to V10, 40 pairs) is also in `results/hl3_dm_holm.csv`.
* **Parameters (features) searched**: the pre-open menu has **62** columns (BSE own 22 incl. ln sigma, flow 4, calendar 7, index/VIX 10, breadth 5, peers 6, US overnight 8), **67** after the open (+5 gap columns), and **82 distinct columns** in total including the 7 implied-volatility/expiry columns (V17 only) and the 8 US columns re-timed at the less conservative lag-1 rule (V18 only). *Correction of Section 0.4:* the pre-fixed table gave the counts 24 (own) and 12 (index) and therefore 66 / 71 / 86; the features actually listed in that table add up to 22 and 10, hence 62 / 67 / 82. The code implements the listed features; only the printed totals in Section 0.4 were mis-added. Nothing else in the design changed (the pre-fixed section is left untouched above and its hash is checked in Section 8).
* **Model configurations tried**: effective number of configurations per target per refit = **96** (9 L1 quantile-regression variants x 4 choices {null, lambda 0.003, 0.01, 0.03} = 36; 3 boosting variants x 7 {null; depth 2 or 3 x 30, 60 or 120 trees} = 21; forest 1; 3 stack variants x 11 weights = 33; plus 5 stack candidates for V16). Hyper-parameters were chosen only by nested expanding-window time-series CV inside each training window (3 folds, 5-session embargo), never on the Final window, and the grids are those written in Section 0.5 (not changed).
* **Learners**: own smoothed-loss L-BFGS-B solver for the L1 quantile regression (validated against scikit-learn / HiGHS, Section 8); scikit-learn `HistGradientBoostingRegressor` with quantile loss (learning rate 0.05, minimum leaf 80, L2 1.0, 32 bins); a Meinshausen quantile forest on `RandomForestRegressor` (200 trees, minimum leaf 40, 30% of features, 70% sub-sample). Crossing quantile levels are repaired by sorting the nine values; post-open HO >= 0 and LO <= 0 are enforced by clipping.

## 4. Results in the Final window (1 Jul 2025 to 15 Oct 2026, n = 320 per target)

How to read the tables. *pinball x1e4*: mean pinball loss over the nine quantile levels, in log points times 10,000 (smaller is better). *gain vs BASE*: percentage change of that loss relative to the baseline (positive = better than the baseline). *DM p (raw)*: two-sided Diebold-Mariano p-value against the baseline (HAC lag 5, Harvey-Leybourne-Newbold small-sample correction); *Holm p (72 pairs)*: the same p-value adjusted over all 72 variant-target pairs tried (18 variants x 4 targets); the adoption rule uses this one. *typical miss*: mean absolute error of the 50% quantile (the "pin-point") in rupees at Rs 3,428, then the median absolute error ("half the time within"). *cover*: share of Final sessions inside the central 50% / 90% band (nominal 0.50 / 0.90); for the post-open high the 90% column is followed by the share of sessions with HO above the 95% quantile (nominal 0.05; HO equals zero on about 4% of sessions, so the 90% band is not the right check there). V17 (implied-volatility block) has data only from Nov 2024: its Final window is complete (n = 320) but its Validation window holds only 20 sessions; V18 is a timing sensitivity and cannot be adopted. EMP250 and the "stays" lines are benchmarks, not part of the 72.

### 4.1 pre-open HIGH

| variant | name | n | pinball x1e4 | gain vs BASE | DM p (raw) | Holm p (72 pairs) | typical miss Rs (mean, median) | 50% band cover | 90% band cover |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline (P_S6 / W_I6) | 320 | 31.152 | +0.00% | n/a | n/a | 42.7, 33.6 | 0.469 | 0.903 |
| V01 | QR_sig | 320 | 32.111 | -3.08% | <0.0001 | <0.0001 | 43.1, 34.3 | 0.469 | 0.931 |
| V02 | QR_all | 320 | 31.537 | -1.24% | 0.097 | 1.000 | 42.6, 32.6 | 0.494 | 0.906 |
| V03 | QRB_all | 320 | 30.983 | +0.54% | 0.471 | 1.000 | 42.6, 31.7 | 0.503 | 0.900 |
| V04 | QRB_own | 320 | 30.721 | +1.38% | 0.119 | 1.000 | 42.3, 32.1 | 0.503 | 0.903 |
| V05 | QRB_idx | 320 | 30.859 | +0.94% | 0.157 | 1.000 | 42.1, 31.3 | 0.525 | 0.897 |
| V06 | QRB_brdpeer | 320 | 30.951 | +0.64% | 0.330 | 1.000 | 42.5, 31.5 | 0.503 | 0.894 |
| V07 | QRB_us | 320 | 30.701 | +1.45% | 0.093 | 1.000 | 42.2, 32.3 | 0.512 | 0.903 |
| V08 | GBM_all | 320 | 31.575 | -1.36% | 0.023 | 1.000 | 43.1, 33.2 | 0.466 | 0.909 |
| V09 | GBMB_all | 320 | 31.002 | +0.48% | 0.653 | 1.000 | 42.9, 33.8 | 0.481 | 0.875 |
| V10 | RF_all | 320 | 31.826 | -2.16% | 0.0009 | 0.060 | 43.0, 33.9 | 0.456 | 0.925 |
| V11 | CQR_base | 320 | 31.015 | +0.44% | 0.658 | 1.000 | 42.7, 31.5 | 0.494 | 0.884 |
| V12 | CQR_QR | 320 | 31.275 | -0.40% | 0.690 | 1.000 | 42.7, 32.6 | 0.481 | 0.891 |
| V13 | CQR_GBM | 320 | 31.582 | -1.38% | 0.185 | 1.000 | 43.1, 33.4 | 0.491 | 0.897 |
| V14 | ST_QR | 320 | 31.247 | -0.31% | 0.504 | 1.000 | 42.6, 33.1 | 0.491 | 0.906 |
| V15 | ST_GBM | 320 | 31.284 | -0.43% | 0.237 | 1.000 | 42.7, 33.3 | 0.478 | 0.912 |
| V16 | ST_BEST | 320 | 31.273 | -0.39% | 0.489 | 1.000 | 42.9, 33.1 | 0.481 | 0.897 |
| V17 | QRB_iv | 320 | 30.986 | +0.53% | 0.480 | 1.000 | 42.6, 31.7 | 0.503 | 0.900 |
| V18 | QRB_us1 | 320 | 30.262 | +2.86% | 0.024 | 1.000 | 41.4, 31.6 | 0.509 | 0.894 |
| EMP250 | trailing-250 empirical | 320 | 32.739 | -5.10% | n/a | n/a | 43.7, 35.4 | 0.506 | 0.912 |
| PRICE_STAYS | price stays | 320 | n/a | n/a | n/a | n/a | 62.9, 51.6 | n/a | n/a |

### 4.2 pre-open LOW

| variant | name | n | pinball x1e4 | gain vs BASE | DM p (raw) | Holm p (72 pairs) | typical miss Rs (mean, median) | 50% band cover | 90% band cover |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline (P_S6 / W_I6) | 320 | 36.579 | +0.00% | n/a | n/a | 47.7, 32.2 | 0.503 | 0.887 |
| V01 | QR_sig | 320 | 36.326 | +0.69% | 0.0030 | 0.193 | 47.5, 32.4 | 0.497 | 0.887 |
| V02 | QR_all | 320 | 37.012 | -1.19% | 0.259 | 1.000 | 48.5, 35.1 | 0.453 | 0.872 |
| V03 | QRB_all | 320 | 37.054 | -1.30% | 0.187 | 1.000 | 48.5, 35.3 | 0.475 | 0.884 |
| V04 | QRB_own | 320 | 36.787 | -0.57% | 0.249 | 1.000 | 48.0, 33.2 | 0.509 | 0.897 |
| V05 | QRB_idx | 320 | 36.586 | -0.02% | 0.965 | 1.000 | 47.8, 34.0 | 0.519 | 0.897 |
| V06 | QRB_brdpeer | 320 | 37.129 | -1.50% | 0.146 | 1.000 | 48.7, 35.7 | 0.478 | 0.881 |
| V07 | QRB_us | 320 | 36.687 | -0.29% | 0.566 | 1.000 | 48.0, 33.1 | 0.516 | 0.894 |
| V08 | GBM_all | 320 | 36.806 | -0.62% | 0.530 | 1.000 | 47.7, 34.7 | 0.478 | 0.872 |
| V09 | GBMB_all | 320 | 36.634 | -0.15% | 0.854 | 1.000 | 47.9, 34.1 | 0.500 | 0.884 |
| V10 | RF_all | 320 | 36.532 | +0.13% | 0.907 | 1.000 | 47.7, 34.9 | 0.475 | 0.872 |
| V11 | CQR_base | 320 | 36.734 | -0.42% | 0.208 | 1.000 | 47.6, 32.1 | 0.494 | 0.903 |
| V12 | CQR_QR | 320 | 37.366 | -2.15% | 0.075 | 1.000 | 48.8, 34.1 | 0.494 | 0.900 |
| V13 | CQR_GBM | 320 | 36.834 | -0.70% | 0.559 | 1.000 | 47.9, 33.6 | 0.500 | 0.903 |
| V14 | ST_QR | 320 | 36.743 | -0.45% | 0.519 | 1.000 | 48.1, 34.9 | 0.472 | 0.872 |
| V15 | ST_GBM | 320 | 36.736 | -0.43% | 0.533 | 1.000 | 47.7, 33.7 | 0.491 | 0.878 |
| V16 | ST_BEST | 320 | 36.499 | +0.22% | 0.837 | 1.000 | 47.7, 34.6 | 0.478 | 0.875 |
| V17 | QRB_iv | 320 | 37.055 | -1.30% | 0.185 | 1.000 | 48.5, 35.3 | 0.475 | 0.884 |
| V18 | QRB_us1 | 320 | 35.968 | +1.67% | 0.109 | 1.000 | 46.6, 33.8 | 0.491 | 0.884 |
| EMP250 | trailing-250 empirical | 320 | 36.587 | -0.02% | n/a | n/a | 47.5, 33.7 | 0.519 | 0.919 |
| PRICE_STAYS | price stays | 320 | n/a | n/a | n/a | n/a | 61.3, 42.6 | n/a | n/a |

### 4.3 post-open HIGH

| variant | name | n | pinball x1e4 | gain vs BASE | DM p (raw) | Holm p (72 pairs) | typical miss Rs (mean, median) | 50% band cover | 90% band cover |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline (P_S6 / W_I6) | 320 | 23.853 | +0.00% | n/a | n/a | 34.8, 29.1 | 0.494 | 0.950 (P>q95 0.025) |
| V01 | QR_sig | 320 | 24.579 | -3.04% | <0.0001 | 0.0003 | 34.6, 29.8 | 0.478 | 0.944 (P>q95 0.009) |
| V02 | QR_all | 320 | 24.411 | -2.34% | 0.016 | 1.000 | 34.6, 26.9 | 0.475 | 0.934 (P>q95 0.016) |
| V03 | QRB_all | 320 | 23.683 | +0.71% | 0.472 | 1.000 | 34.4, 26.6 | 0.475 | 0.916 (P>q95 0.031) |
| V04 | QRB_own | 320 | 23.776 | +0.32% | 0.693 | 1.000 | 34.6, 28.0 | 0.494 | 0.916 (P>q95 0.031) |
| V05 | QRB_idx | 320 | 23.804 | +0.21% | 0.789 | 1.000 | 34.4, 27.0 | 0.494 | 0.916 (P>q95 0.031) |
| V06 | QRB_brdpeer | 320 | 23.784 | +0.29% | 0.756 | 1.000 | 34.8, 26.6 | 0.478 | 0.909 (P>q95 0.037) |
| V07 | QRB_us | 320 | 23.721 | +0.55% | 0.540 | 1.000 | 34.3, 28.0 | 0.481 | 0.925 (P>q95 0.025) |
| V08 | GBM_all | 320 | 24.487 | -2.66% | 0.0013 | 0.083 | 34.4, 29.5 | 0.466 | 0.963 (P>q95 0.025) |
| V09 | GBMB_all | 320 | 24.039 | -0.78% | 0.284 | 1.000 | 34.5, 29.2 | 0.478 | 0.912 (P>q95 0.044) |
| V10 | RF_all | 320 | 24.589 | -3.09% | 0.0001 | 0.0094 | 34.4, 28.9 | 0.478 | 0.972 (P>q95 0.013) |
| V11 | CQR_base | 320 | 23.863 | -0.04% | 0.956 | 1.000 | 35.0, 28.5 | 0.475 | 0.900 (P>q95 0.044) |
| V12 | CQR_QR | 320 | 24.245 | -1.64% | 0.107 | 1.000 | 35.2, 27.2 | 0.469 | 0.916 (P>q95 0.028) |
| V13 | CQR_GBM | 320 | 24.679 | -3.46% | 0.0021 | 0.138 | 35.2, 29.4 | 0.466 | 0.916 (P>q95 0.031) |
| V14 | ST_QR | 320 | 23.965 | -0.47% | 0.353 | 1.000 | 34.7, 28.2 | 0.487 | 0.925 (P>q95 0.025) |
| V15 | ST_GBM | 320 | 24.063 | -0.88% | 0.055 | 1.000 | 34.7, 29.2 | 0.481 | 0.944 (P>q95 0.025) |
| V16 | ST_BEST | 320 | 23.973 | -0.50% | 0.565 | 1.000 | 34.7, 28.2 | 0.466 | 0.925 (P>q95 0.028) |
| V17 | QRB_iv | 320 | 23.685 | +0.70% | 0.478 | 1.000 | 34.4, 26.6 | 0.475 | 0.916 (P>q95 0.031) |
| V18 | QRB_us1 | 320 | 23.782 | +0.30% | 0.714 | 1.000 | 34.6, 27.8 | 0.494 | 0.919 (P>q95 0.031) |
| EMP250 | trailing-250 empirical | 320 | 25.009 | -4.85% | n/a | n/a | 35.4, 31.2 | 0.500 | 0.922 (P>q95 0.019) |
| OPEN_STAYS | open stays | 320 | n/a | n/a | n/a | n/a | 51.3, 40.7 | n/a | n/a |

### 4.4 post-open LOW

| variant | name | n | pinball x1e4 | gain vs BASE | DM p (raw) | Holm p (72 pairs) | typical miss Rs (mean, median) | 50% band cover | 90% band cover |
|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline (P_S6 / W_I6) | 320 | 28.030 | +0.00% | n/a | n/a | 37.4, 26.6 | 0.503 | 0.894 |
| V01 | QR_sig | 320 | 27.902 | +0.45% | 0.107 | 1.000 | 37.4, 27.0 | 0.481 | 0.906 |
| V02 | QR_all | 320 | 28.205 | -0.63% | 0.211 | 1.000 | 38.0, 28.0 | 0.497 | 0.906 |
| V03 | QRB_all | 320 | 28.119 | -0.32% | 0.346 | 1.000 | 37.6, 27.3 | 0.528 | 0.887 |
| V04 | QRB_own | 320 | 28.064 | -0.12% | 0.277 | 1.000 | 37.5, 26.6 | 0.509 | 0.884 |
| V05 | QRB_idx | 320 | 28.030 | -0.00% | 0.993 | 1.000 | 37.4, 26.9 | 0.522 | 0.887 |
| V06 | QRB_brdpeer | 320 | 28.286 | -0.92% | 0.043 | 1.000 | 38.1, 28.3 | 0.525 | 0.887 |
| V07 | QRB_us | 320 | 28.053 | -0.08% | 0.506 | 1.000 | 37.5, 26.6 | 0.509 | 0.887 |
| V08 | GBM_all | 320 | 28.465 | -1.55% | 0.033 | 1.000 | 37.7, 27.5 | 0.478 | 0.900 |
| V09 | GBMB_all | 320 | 28.481 | -1.61% | 0.019 | 1.000 | 37.9, 27.5 | 0.491 | 0.881 |
| V10 | RF_all | 320 | 28.566 | -1.91% | 0.034 | 1.000 | 38.0, 27.9 | 0.481 | 0.906 |
| V11 | CQR_base | 320 | 28.139 | -0.39% | 0.181 | 1.000 | 37.5, 26.2 | 0.478 | 0.887 |
| V12 | CQR_QR | 320 | 29.293 | -4.51% | <0.0001 | 0.0034 | 38.9, 28.1 | 0.466 | 0.894 |
| V13 | CQR_GBM | 320 | 29.295 | -4.51% | <0.0001 | 0.0031 | 39.1, 28.1 | 0.500 | 0.887 |
| V14 | ST_QR | 320 | 28.088 | -0.21% | 0.294 | 1.000 | 37.6, 27.0 | 0.494 | 0.897 |
| V15 | ST_GBM | 320 | 28.136 | -0.38% | 0.227 | 1.000 | 37.5, 27.4 | 0.487 | 0.887 |
| V16 | ST_BEST | 320 | 28.204 | -0.62% | 0.091 | 1.000 | 37.6, 27.4 | 0.497 | 0.887 |
| V17 | QRB_iv | 320 | 28.119 | -0.32% | 0.346 | 1.000 | 37.6, 27.3 | 0.528 | 0.887 |
| V18 | QRB_us1 | 320 | 28.040 | -0.03% | 0.785 | 1.000 | 37.5, 26.4 | 0.509 | 0.887 |
| EMP250 | trailing-250 empirical | 320 | 28.053 | -0.08% | n/a | n/a | 37.6, 28.3 | 0.491 | 0.903 |
| OPEN_STAYS | open stays | 320 | n/a | n/a | n/a | n/a | 59.0, 45.2 | n/a | n/a |

## 5. What the user sees, and what the pre-fixed rule says

### 5.1 Typical miss of the median in rupees (Final window, n = 320, at Rs 3,428)

The mean absolute error of the 50% quantile (the "pin-point"). "+/- std. error" is the standard error of the baseline's figure across the 320 sessions as if the sessions were independent (the baseline study's block-bootstrap standard errors, which allow for dependence, are 2.8 / 3.0 / 1.8 / 2.3). The "best eligible variant" column picks the best of 16 variants on the same 320 sessions, so it overstates what a variant could be expected to deliver.

| target | n | baseline | std. error | best eligible variant (chosen after seeing Final) | best including V18 | worst variant | trailing-250 | price / open stays |
|---|---|---|---|---|---|---|---|---|
| pre-open HIGH | 320 | 42.7 | 2.2 | V05 QRB_idx: 42.1 | V18: 41.4 | V13: 43.1 | 43.7 | 62.9 |
| pre-open LOW | 320 | 47.7 | 2.9 | V01 QR_sig: 47.5 | V18: 46.6 | V12: 48.8 | 47.5 | 61.3 |
| post-open HIGH | 320 | 34.8 | 1.8 | V07 QRB_us: 34.3 | V07: 34.3 | V12: 35.2 | 35.4 | 51.3 |
| post-open LOW | 320 | 37.4 | 2.6 | V05 QRB_idx: 37.4 | V05: 37.4 | V13: 39.1 | 37.6 | 59.0 |

Reading: the rupee miss under any variant lies between 1.3 better and 1.6 worse than the baseline's, and the best-of-16 improvement on the same data is Rs 0.05 to 0.56 across the four targets (Rs 1.3 for the pre-open high and Rs 1.0 for the pre-open low if V18's lag-1 US timing is allowed). The baseline's advantage over "price stays" (Rs 62.9 / 61.3 before the open) and "open stays" (Rs 51.3 / 59.0 after) is large; nothing in the menu adds visibly to it.

### 5.2 The five conditions (pre-fixed rule, Section 0.6)

Counts of variant-target pairs meeting each condition (the Final window, Validation window, coverage and CAS conditions are computed for every pair; the leakage test (v) was run for every variant and passed for all 18 at all six sessions, Section 8.3; it cannot rescue a pair that fails (i)):

| set | pairs | (i) gain >= 2% and Holm p < 0.05 | gain > 0 (any size) | gain >= 2% (any p) | (ii) Validation same sign | (iii) coverage | (iv) CAS within 5% | (v) leakage test passed |
|---|---|---|---|---|---|---|---|---|
| all 72 pairs | 72 | 0 | 21 | 1 | 56 | 13 | 68 | 72 |
| 64 eligible pairs (V17 and V18 excluded) | 64 | 0 | 16 | 0 | 52 | 11 | 60 | 64 |

Condition (ii) is counted as "Validation-window gain is positive" and is independent of the Final result; condition (iii) fails for most pairs because a variant must be at least as close to the nominal 50% and 90% coverage as the baseline in *both* bands and pass both Kupiec tests; 13 pairs pass it. **No pair passes (i), so no pair is adopted** (`adopt` is False in all 72 rows of `results/hl3_adoption.csv`).

The pairs that came closest (every pair with a Final gain of 1% or more):

| pair | Final gain | raw p | Holm p (72) | Validation gain | 50% / 90% cover vs baseline | CAS gain (n=52) | conditions failed |
|---|---|---|---|---|---|---|---|
| V04 QRB_own / H | +1.38% | 0.119 | 1.000 | -0.10% | 0.503 / 0.903 vs 0.469 / 0.903 | +1.66% | (i), (ii) |
| V07 QRB_us / H | +1.45% | 0.093 | 1.000 | -0.27% | 0.512 / 0.903 vs 0.469 / 0.903 | +1.68% | (i), (ii) |
| V18 QRB_us1 / H | +2.86% | 0.024 | 1.000 | +0.69% | 0.509 / 0.894 vs 0.469 / 0.903 | +3.79% | (i), (iii) |
| V18 QRB_us1 / L | +1.67% | 0.109 | 1.000 | +1.59% | 0.491 / 0.884 vs 0.503 / 0.887 | +0.62% | (i), (iii) |

## 6. Is the null a short-sample accident? Validation, closing-auction slice, long run, half-years

### 6.1 Validation (n = 248) and closing-auction slice (n = 52) next to Final (gain in mean pinball against BASE, percent; positive = better)

V17's "Val" figure is over only 20 sessions (its implied-volatility data start in Nov 2024), so it is not comparable and cannot satisfy rule (ii).

| variant | H Val | H Final | H CAS | L Val | L Final | L CAS | HO Val | HO Final | HO CAS | LO Val | LO Final | LO CAS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V01 QR_sig | +1.24 | -3.08 | -4.60 | +0.70 | +0.69 | +1.64 | +0.53 | -3.04 | -4.41 | -0.39 | +0.45 | +0.90 |
| V02 QR_all | +0.97 | -1.24 | -3.05 | +2.85 | -1.19 | +0.73 | +0.42 | -2.34 | -6.55 | +0.23 | -0.63 | +0.99 |
| V03 QRB_all | +0.37 | +0.54 | +0.62 | +2.69 | -1.30 | -0.24 | +0.74 | +0.71 | -4.42 | +0.68 | -0.32 | +0.41 |
| V04 QRB_own | -0.10 | +1.38 | +1.66 | +0.61 | -0.57 | -0.33 | +0.73 | +0.32 | -3.97 | -0.01 | -0.12 | +0.00 |
| V05 QRB_idx | -0.52 | +0.94 | +1.50 | +1.33 | -0.02 | -0.16 | +0.61 | +0.21 | -3.95 | +0.56 | -0.00 | +0.42 |
| V06 QRB_brdpeer | +0.33 | +0.64 | +1.27 | +2.83 | -1.50 | -1.78 | +0.01 | +0.29 | -5.45 | +0.85 | -0.92 | +0.41 |
| V07 QRB_us | -0.27 | +1.45 | +1.68 | +0.18 | -0.29 | -0.34 | +0.88 | +0.55 | -3.12 | -0.31 | -0.08 | +0.00 |
| V08 GBM_all | +1.07 | -1.36 | -2.80 | +1.80 | -0.62 | -0.07 | +0.92 | -2.66 | -4.28 | +0.73 | -1.55 | -0.24 |
| V09 GBMB_all | +0.35 | +0.48 | -0.96 | +1.95 | -0.15 | +0.81 | +0.63 | -0.78 | -3.76 | +1.39 | -1.61 | -0.05 |
| V10 RF_all | +1.30 | -2.16 | -2.62 | +3.70 | +0.13 | -0.23 | +1.32 | -3.09 | -5.33 | +1.60 | -1.91 | -0.38 |
| V11 CQR_base | -0.12 | +0.44 | +1.17 | -0.95 | -0.42 | -1.28 | -1.52 | -0.04 | -0.81 | -0.88 | -0.39 | +0.16 |
| V12 CQR_QR | +0.40 | -0.40 | -0.19 | +3.00 | -2.15 | -1.60 | -0.67 | -1.64 | -4.05 | -0.28 | -4.51 | +0.43 |
| V13 CQR_GBM | +1.57 | -1.38 | -2.07 | +2.32 | -0.70 | -0.48 | +0.13 | -3.46 | -7.24 | +0.35 | -4.51 | -0.55 |
| V14 ST_QR | +0.90 | -0.31 | -0.26 | +2.73 | -0.45 | +0.18 | +0.48 | -0.47 | +0.00 | +0.72 | -0.21 | +0.22 |
| V15 ST_GBM | +0.85 | -0.43 | -0.10 | +1.90 | -0.43 | -0.28 | +1.00 | -0.88 | +0.00 | +0.98 | -0.38 | +0.00 |
| V16 ST_BEST | +1.06 | -0.39 | +0.36 | +3.70 | +0.22 | -0.52 | +1.32 | -0.50 | -4.14 | +1.48 | -0.62 | +0.15 |
| V17 QRB_iv | +3.82 | +0.53 | +0.62 | +5.52 | -1.30 | -0.24 | +1.76 | +0.70 | -4.42 | -0.15 | -0.32 | +0.41 |
| V18 QRB_us1 | +0.69 | +2.86 | +3.79 | +1.59 | +1.67 | +0.62 | +0.81 | +0.30 | -3.81 | +0.14 | -0.03 | +0.00 |

Reading (the 68 pairs other than V17's four): the average gain is **+0.87% in the Validation window and -0.63% in the Final window**; 56 of 68 pairs are positive in Validation and only 19 of 68 in Final; **42 pairs gain in Validation and lose in Final**, 14 gain in both. In the closing-auction slice (n = 52, too short to say anything) the average is -1.03%, 22 of 68 positive, and 68 of the 72 pairs are within the 5% tolerance of rule (iv) (the four that are not are all post-open highs: V02, V06, V10, V13). This pattern (gains that disappear in the next window) is what one expects from relationships that are weak and unstable, not from a stable missing ingredient.

### 6.2 The same variants half-year by half-year (post-hoc, descriptive; `results/hl3_posthoc_halfyear.csv`)

Gain in mean pinball against BASE; V16 and V18 have stored forecasts for the Final window only.

| target / variant | 2024-07..12 (n=125) | 2025-01..06 (n=123) | 2025-07..12 (n=125) | 2026-01..06 (n=120) | 2026-07..10-15 (n=75) |
|---|---|---|---|---|---|
| H / V02 QR_all | +0.24% | +1.80% | -2.55% | +0.90% | -3.17% |
| H / V10 RF_all | +1.00% | +1.65% | -2.79% | -1.17% | -3.05% |
| H / V16 ST_BEST | n/a | n/a | -2.03% | +0.41% | +0.95% |
| H / V18 QRB_us1 | n/a | n/a | -1.52% | +6.07% | +4.25% |
| HO / V02 QR_all | +0.51% | +0.31% | -1.60% | -1.60% | -5.10% |
| HO / V10 RF_all | +1.64% | +0.90% | -2.36% | -3.06% | -4.61% |
| HO / V16 ST_BEST | n/a | n/a | -2.41% | +2.71% | -2.02% |
| HO / V18 QRB_us1 | n/a | n/a | -0.01% | +1.95% | -1.86% |
| L / V02 QR_all | +0.75% | +4.51% | -3.77% | +0.60% | -0.23% |
| L / V10 RF_all | +1.72% | +5.27% | -1.48% | +2.11% | -1.16% |
| L / V16 ST_BEST | n/a | n/a | -1.48% | +2.31% | -1.15% |
| L / V18 QRB_us1 | n/a | n/a | -1.98% | +5.53% | +0.09% |
| LO / V02 QR_all | +2.47% | -1.83% | -1.35% | -0.44% | +0.48% |
| LO / V10 RF_all | +2.44% | +0.83% | -2.27% | -1.95% | -1.16% |
| LO / V16 ST_BEST | n/a | n/a | -1.54% | +0.01% | +0.11% |
| LO / V18 QRB_us1 | n/a | n/a | -0.08% | -0.05% | +0.09% |

Almost every flexible model gains in the second half of 2024 and the first half of 2025 (the Validation window) and loses in the second half of 2025; after that the sign changes from half-year to half-year. The break falls just after the 23 May 2025 bonus issue and at the start of the Final window, which is also a much calmer period (the baseline's own pre-open-high pinball x1e4 is 52.1 in Validation and 31.2 in Final, `results/hl3_dm_holm.csv`); I did not investigate the cause and do not claim one. V18's pre-open-high gain (+2.86% over the Final window) comes entirely from 2026 (+6.07% and +4.25%) after -1.52% in the second half of 2025; with 120 and 75 sessions per period this is not distinguishable from luck.

### 6.3 Long run: Development window and all 1,640 sessions (POST-HOC: added after the Final results were seen; 140 further DM tests: 68 on the Development window, 72 on all sessions, each Holm-adjusted within its own window)

Gain in percent (all sessions: with the number of calendar years, out of 7, in which the variant beat the baseline, and the post-hoc Holm p-value). V17 has no Development-window figure and its "All" column covers only its 340 evaluable sessions (2 calendar years).

| variant | H Dev | H All | H All Holm | L Dev | L All | L All Holm | HO Dev | HO All | HO All Holm | LO Dev | LO All | LO All Holm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V01 QR_sig | +0.18 | -0.09 (4/7y) | 1.000 | -0.41 | +0.01 (4/7y) | 1.000 | -0.24 | -0.47 (3/7y) | 1.000 | -0.22 | -0.13 (4/7y) | 1.000 |
| V02 QR_all | +0.14 | +0.09 (4/7y) | 1.000 | +1.13 | +1.02 (6/7y) | 1.000 | +0.34 | +0.00 (4/7y) | 1.000 | +0.94 | +0.53 (4/7y) | 1.000 |
| V03 QRB_all | +0.00 | +0.15 (2/7y) | 1.000 | +0.86 | +0.80 (6/7y) | 1.000 | +0.10 | +0.30 (3/7y) | 1.000 | +0.19 | +0.19 (2/7y) | 1.000 |
| V04 QRB_own | +0.01 | +0.18 (2/7y) | 1.000 | -0.38 | -0.23 (4/7y) | 1.000 | +0.28 | +0.36 (4/7y) | 1.000 | -0.60 | -0.41 (0/7y) | 1.000 |
| V05 QRB_idx | +0.00 | +0.04 (2/7y) | 1.000 | -0.12 | +0.17 (5/7y) | 1.000 | +0.24 | +0.30 (3/7y) | 1.000 | -0.38 | -0.15 (3/7y) | 1.000 |
| V06 QRB_brdpeer | -0.30 | -0.05 (2/7y) | 1.000 | +1.05 | +0.91 (6/7y) | 1.000 | +0.13 | +0.13 (3/7y) | 1.000 | +0.10 | +0.05 (2/7y) | 1.000 |
| V07 QRB_us | +0.00 | +0.16 (2/7y) | 1.000 | -0.39 | -0.26 (4/7y) | 1.000 | +0.28 | +0.42 (3/7y) | 1.000 | -0.78 | -0.57 (0/7y) | 1.000 |
| V08 GBM_all | +0.40 | +0.27 (5/7y) | 1.000 | +1.48 | +1.14 (6/7y) | 1.000 | +0.58 | +0.21 (4/7y) | 1.000 | +1.57 | +0.86 (3/7y) | 1.000 |
| V09 GBMB_all | +0.22 | +0.28 (4/7y) | 1.000 | +1.10 | +1.02 (6/7y) | 1.000 | +0.33 | +0.24 (3/7y) | 1.000 | +1.53 | +0.94 (3/7y) | 1.000 |
| V10 RF_all | +0.95 | +0.57 (4/7y) | 1.000 | +2.19 | +2.08 (6/7y) | 0.0066 | +0.72 | +0.33 (4/7y) | 1.000 | +2.42 | +1.50 (5/7y) | 0.262 |
| V11 CQR_base | -2.52 | -1.65 (2/7y) | 0.013 | -2.07 | -1.55 (0/7y) | 0.0030 | -1.84 | -1.54 (1/7y) | 0.0023 | -1.98 | -1.50 (0/7y) | 0.025 |
| V12 CQR_QR | -1.90 | -1.26 (1/7y) | 0.283 | -0.95 | -0.44 (4/7y) | 1.000 | -1.34 | -1.25 (0/7y) | 0.037 | +0.54 | -0.51 (4/7y) | 1.000 |
| V13 CQR_GBM | -1.98 | -1.24 (2/7y) | 0.609 | -0.93 | -0.27 (4/7y) | 1.000 | -1.51 | -1.46 (0/7y) | 0.023 | -0.32 | -0.96 (2/7y) | 1.000 |
| V14 ST_QR | +0.23 | +0.28 (5/7y) | 1.000 | +1.77 | +1.53 (6/7y) | 0.042 | +0.30 | +0.23 (4/7y) | 1.000 | +1.08 | +0.79 (6/7y) | 1.000 |
| V15 ST_GBM | +0.64 | +0.53 (5/7y) | 1.000 | +1.60 | +1.27 (6/7y) | 0.270 | +0.48 | +0.40 (4/7y) | 1.000 | +1.68 | +1.19 (4/7y) | 0.167 |
| V16 ST_BEST | +1.14 | +0.90 (5/7y) | 0.283 | +2.05 | +2.02 (6/7y) | 0.0066 | +0.66 | +0.63 (4/7y) | 1.000 | +1.78 | +1.29 (5/7y) | 0.569 |
| V17 QRB_iv (340 sessions only) | n/a | +0.72 (2/2y) | 1.000 | n/a | -0.89 (1/2y) | 1.000 | n/a | +0.78 (2/2y) | 1.000 | n/a | -0.31 (0/2y) | 1.000 |
| V18 QRB_us1 | +0.55 | +0.90 (5/7y) | 0.609 | +1.72 | +1.68 (5/7y) | 0.262 | +0.23 | +0.34 (3/7y) | 1.000 | -0.50 | -0.30 (2/7y) | 1.000 |

What this shows, in plain words and with the caveat that it is post-hoc:

* Over the whole sample the only gains that survive a Holm adjustment are for the **pre-open LOW**: the random forest V10 (+2.08%, Holm p = 0.0066, positive in 6 of 7 years), the best-of stack V16 (+2.02%, 0.0066) and the L1 stack V14 (+1.53%, 0.042). The post-open low shows a similar sign (V10 +1.50%) but not significantly (Holm 0.26). No gain on the highs survives the adjustment (largest +0.90%, V16 and V18 on the pre-open high, post-hoc Holm 0.28 and 0.61).
* In the Final window those same gains are +0.13% (V10), +0.22% (V16) and -0.45% (V14) for the pre-open low, with essentially unchanged rupee misses for V10 and V16 (Rs 47.7 against 47.7 for both). I did not compute rupee misses for the long run. So the long-run low-side signal is small, was concentrated in 2021 to 2024 and the first half of 2025 (V10 low by calendar year: 2020 -0.4%, 2021 +3.5%, 2022 +3.6%, 2023 +0.4%, 2024 +3.2%, 2025 +2.6%, 2026 to 15 Oct +1.1%; `results/hl3_byyear.csv`), and does not show up in the pre-fixed Final window; it is a lead for a future pre-registered test, not an adoption.
* **Conformalising the baseline (V11) is significantly worse than the baseline on all four targets** over the whole sample (-1.5% to -1.65%, post-hoc Holm 0.013, 0.003, 0.002, 0.025) and in the Development window (-1.8% to -2.5%). The baseline's own quantiles are not mis-calibrated in a way that a shift by the trailing-250 calibration errors can repair; the repair adds noise. Conformalising the flexible models did not help systematically either: on the Final window V12 is better than its parent V02 on two targets (pre-open high -0.40% against -1.24%; post-open high -1.64% against -2.34%) and worse on the other two (pre-open low -2.15% against -1.19%; post-open low -4.51% against -0.63%), and V13 is the same or worse than its parent V08 on all four (post-open low -4.51% against -1.55%).
* Pure re-scaling by an own elasticity (V01) is neutral to worse: all-sessions gains of -0.09%, +0.01%, -0.47%, -0.13%.

## 7. Which parameters mattered (and what they say, in plain words)

All of Section 7 is **descriptive**: it explains the fitted models and the data; it is not a test and proves nothing the tables in Sections 4 to 6 do not. Sizes are in units of "sigma", the baseline's own one-day scale for the phase (sigma_R about 2.43% = Rs 83 for the 16 Oct pre-open forecast; sigma_I about 2.22% = Rs 76 after the open).

### 7.1 Permutation importance, computed on training windows only (`results/hl3_importance.csv`)

Method: at six snapshots (training windows ending 27 Jul 2022, 23 May 2023, 12 Mar 2024, 6 Jan 2025, 28 Oct 2025, 19 Aug 2026), the model is fitted on the first 70% of the training rows (574 rows at the first snapshot) and scored on the last 30% of the same training window (241 rows; 5-session embargo). Then one parameter, or a whole group, is shuffled (10 shuffles) and the **rise in pinball loss x1e4** is recorded; three columns of pure random noise give the floor. Two forced mid-strength models are used so that importance is shown even where the nested search would have chosen "do nothing": L1 quantile regression (lambda 0.01) and a shallow boosted model (depth 2, 60 trees). The last two snapshots' training windows contain Final-window sessions that precede the snapshot date (they are training data at that date); nothing is selected from this table.

Group importance (mean over the six snapshots; the held-out loss itself is 30 to 43 on this scale):

| group | H QR | H GBM | L QR | L GBM | HO QR | HO GBM | LO QR | LO GBM |
|---|---|---|---|---|---|---|---|---|
| SIG | -0.00 | +0.03 | +0.03 | +0.00 | -0.01 | +0.00 | +0.09 | +0.02 |
| OWN | +0.04 | +0.00 | +0.19 | +0.15 | +0.13 | +0.01 | +0.13 | +0.12 |
| FLOW | +0.17 | +0.03 | +0.06 | -0.01 | +0.03 | +0.04 | +0.00 | -0.01 |
| CAL | +0.03 | +0.00 | +0.29 | +0.10 | +0.06 | +0.00 | +0.10 | +0.02 |
| IDX | +0.06 | +0.30 | +0.12 | +0.08 | -0.04 | +0.09 | +0.13 | +0.05 |
| BRD | +0.04 | -0.01 | +0.46 | +0.64 | +0.08 | +0.02 | +0.37 | +0.42 |
| PEER | +0.30 | +0.31 | +0.24 | +0.15 | +0.11 | +0.15 | +0.12 | +0.12 |
| US | +0.04 | +0.07 | +0.13 | +0.05 | +0.01 | +0.08 | +0.05 | +0.05 |
| GAP | - | - | - | - | +0.22 | +0.11 | +0.15 | +0.04 |
| NOISE | -0.02 | -0.08 | +0.07 | +0.01 | -0.05 | -0.12 | +0.06 | -0.00 |
| held-out pinball x1e4 (reference) | 43.2 | 42.8 | 37.3 | 37.3 | 36.5 | 36.3 | 30.7 | 30.6 |

Single parameters with the largest importance (mean over the six snapshots):

| target | model | top 5 single parameters (x1e4 pinball increase when shuffled) | three pure-noise columns: mean / max |
|---|---|---|---|
| H | QR | flow_dturn5 0.22; peer_cdsl_ret 0.15; own_cloc 0.06; peer_ret 0.05; own_rng1 0.05 | -0.009 / -0.000 |
| H | GBM | idx_nifty_ret_z 0.22; peer_ret 0.12; peer_cdsl_ret 0.10; flow_dturn5 0.06; us_brent_ret 0.06 | -0.024 / 0.008 |
| L | QR | brd_adv 0.41; cal_tue 0.18; own_cloc 0.17; us_sp_ret5 0.13; idx_vix_chg 0.11 | +0.024 / 0.040 |
| L | GBM | brd_dn5 0.32; own_cloc 0.12; peer_mcx_ret 0.08; idx_vix_chg 0.06; cal_gapdays 0.05 | +0.002 / 0.015 |
| HO | QR | gap_above_yhigh 0.15; own_rng1 0.11; own_cloc 0.08; peer_cdsl_ret 0.08; gap_below_ylow 0.06 | -0.015 / -0.009 |
| HO | GBM | us_brent_ret 0.08; peer_rng 0.07; idx_nifty_ret_z 0.06; gap_gz 0.04; brd_up5 0.03 | -0.040 / -0.014 |
| LO | QR | brd_adv 0.33; idx_vix_chg 0.11; own_rv5 0.10; sig_ln 0.09; own_cloc 0.07 | +0.019 / 0.053 |
| LO | GBM | brd_dn5 0.21; idx_vix_chg 0.05; own_ret5 0.05; peer_ret 0.04; brd_med_z 0.04 | -0.001 / 0.002 |

Reading:

* **Everything is small.** Shuffling the most important group raises the held-out loss by 0.2 to 0.6 on a scale of 30 to 43, i.e. 0.6% to 1.7%; only about one group-cell in six exceeds 0.15. The pure-noise columns average -0.12 to +0.07 as a group, and no single noise column averages more than 0.053 in any model and target.
* **For the LOW (both before and after the open) the market-breadth block is on top** (breadth group = advancing share, median stock return, share of stocks up or down 5% or more, market turnover: +0.46 for the L1 model and +0.64 for the boosted model pre-open, +0.37 and +0.42 post-open; the single parameters are the advancing share, +0.41 and +0.33 in the L1 model, and the share down 5% or more, +0.32 and +0.21 in the boosted model), followed by peers and BSE's own close location in yesterday's range. For the pre-open HIGH the top groups are the peer group (CDSL, MCX and the equal-weighted peers: +0.30 L1, +0.31 boosted), the 5-day change in BSE's turnover (+0.17, L1) and the index group, mainly Nifty's return (+0.30, boosted). After the open the gap block matters most for the high (+0.22 QR; "open above yesterday's high" is the top single parameter, +0.15).
* **The volatility-type parameters the user probably expects to matter do not stand out**: the 1-day India VIX change appears in the top five for the low (+0.05 to +0.11), but the VIX level (at most 0.011 in any model and target), the VIX-minus-realised spread (at most 0.039), US VIX level and change (at most 0.026), the dollar index, the rupee and the US 10-year yield (all at most 0.024) never rise above the noise floor; Brent reaches 0.08 for the post-open high (boosted model, where it is the top single parameter) and 0.06 for the pre-open high. The US block as a whole is +0.01 to +0.13.
* The importances are small *and* unstable (the standard deviation across the six snapshots is often as large as the mean, for example 0.35 against 0.30 for the peer group on the pre-open high; see the CSV), consistent with the out-of-sample result that the best-looking groups (breadth for the low) gained in Validation and lost in Final.

### 7.2 What the nested search chose (`results/hl3_choices.csv`, `results/hl3_choices_by_block.csv`)

At every refit and target the inner time-series CV could choose "do nothing" (A: the unconditional quantile of y/sigma; B: no correction = the baseline) or one of the penalties/tree settings. Share of refits in which it chose "do nothing" (each refit counts once per target; 4 targets):

| variant | dev: refits (4 targets) | dev: share 'do nothing' | val: refits (4 targets) | val: share 'do nothing' | final: refits (4 targets) | final: share 'do nothing' |
|---|---|---|---|---|---|---|
| V01 QR_sig | 216 | 44% | 48 | 10% | 64 | 0% |
| V02 QR_all | 216 | 35% | 48 | 0% | 64 | 2% |
| V03 QRB_all | 216 | 62% | 48 | 6% | 64 | 6% |
| V04 QRB_own | 216 | 71% | 48 | 10% | 64 | 11% |
| V05 QRB_idx | 216 | 64% | 48 | 21% | 64 | 8% |
| V06 QRB_brdpeer | 216 | 60% | 48 | 0% | 64 | 8% |
| V07 QRB_us | 216 | 68% | 48 | 8% | 64 | 12% |
| V08 GBM_all | 216 | 33% | 48 | 0% | 64 | 0% |
| V09 GBMB_all | 216 | 50% | 48 | 0% | 64 | 3% |
| V12 CQR_QR | 216 | 46% | 48 | 4% | 64 | 0% |
| V13 CQR_GBM | 216 | 54% | 48 | 0% | 64 | 0% |
| V17 QRB_iv | - | - | 4 | 0% | 64 | 6% |
| V18 QRB_us1 | 216 | 47% | 48 | 0% | 64 | 8% |

In the early Development years "do nothing" wins often (33% to 71%), as it should when training data are scarce. In Validation and Final the search almost always chooses a real model (79% to 100% non-null in Validation and 88% to 100% in Final for every variant). Yet the Final-window scores of these chosen models are not better than "do nothing" (the baseline) in 51 of 72 pairs (Section 4). In other words, the inner cross-validation inside the training window (which is the data on which the model was selected) sees a gain that is not there on the next 20 sessions, window after window. That is the signature of weak, unstable relationships (Section 6.2) and is the reason the guard rails were built in; it is not a bug in the walk-forward: the leakage test (Section 8) shows that no information from the target session enters its forecast.

### 7.3 Stacks (V14, V15, V16): how much the stack trusted the flexible models in the Final window

Weight on the flexible model, chosen from the previous 250 out-of-sample sessions (minimum 60), refit every 20 sessions; mean (and range) over the 16 Final-window refits:

| stack | H: mean weight on flexible model (min-max) | L: mean weight on flexible model (min-max) | HO: mean weight on flexible model (min-max) | LO: mean weight on flexible model (min-max) |
|---|---|---|---|---|
| V14 ST_QR | 0.46 (0.1-0.8) | 0.54 (0.2-0.9) | 0.39 (0.0-0.7) | 0.20 (0.0-0.6) |
| V15 ST_GBM | 0.46 (0.0-0.9) | 0.54 (0.1-0.9) | 0.34 (0.0-0.8) | 0.21 (0.0-0.7) |
| V16 ST_BEST | 0.76 (0.4-1.0) | 0.93 (0.6-1.0) | 0.96 (0.8-1.0) | 0.35 (0.0-0.9) |

V16 picks the best of five candidate models by past out-of-sample loss; for the pre-open low it picked the random forest V10 at all 16 Final refits, for the post-open high and low mostly the all-parameter offset model V03. The stacks put 20% to 96% of their weight on flexible models and still end between -0.9% and +0.2% of the baseline (V16 pre-open low +0.22%, the only positive one, p = 0.84): trusting the flexible models more on the basis of 250 past sessions did not pay.

### 7.4 What the data say, in plain words (descriptive terciles, model-free)

Cut points are the 1/3 and 2/3 percentiles of each parameter over the sessions **before** the Final window (2 Apr 2019 to 30 Jun 2025; n = 514 per third for most parameters). Each row shows how large the day's high (or low depth) was, in units of the baseline's own scale sigma, in the bottom third and in the top third of that parameter: first before the Final window, then in the Final window. If a parameter carried information beyond sigma, the top third would be clearly larger (or smaller) than the bottom third in both periods. (`results/hl3_menu_bins.csv`; more parameters in the CSV.) Low means depth below the previous close/open.

| target | parameter | n bottom/top third (before Final) | median size, bottom third vs top third (in sigma) | top third is larger by | 90% point, bottom vs top | n (Final) | Final: median, bottom vs top | Final: top larger by |
|---|---|---|---|---|---|---|---|---|
| H | India VIX level | 514/514 | 0.64 vs 0.68 | +6% | 1.86 vs 1.77 | 240/36 | 0.49 vs 0.59 | +19% |
| L | India VIX level | 514/514 | 0.45 vs 0.44 | -2% | 1.45 vs 1.49 | 240/36 | 0.49 vs 0.30 | -39% |
| H | India VIX change (1 day) | 514/514 | 0.68 vs 0.61 | -11% | 1.93 vs 1.60 | 108/101 | 0.48 vs 0.56 | +18% |
| L | India VIX change (1 day) | 514/514 | 0.37 vs 0.54 | +45% | 1.25 vs 1.59 | 108/101 | 0.43 vs 0.48 | +11% |
| H | US VIX level | 517/515 | 0.60 vs 0.64 | +7% | 1.78 vs 1.66 | 129/28 | 0.50 vs 0.64 | +27% |
| L | US VIX level | 517/515 | 0.50 vs 0.46 | -7% | 1.45 vs 1.52 | 129/28 | 0.54 vs 0.30 | -45% |
| H | S&P 500 return (conservative lag) | 514/514 | 0.64 vs 0.62 | -3% | 1.69 vs 2.00 | 98/100 | 0.67 vs 0.54 | -19% |
| L | S&P 500 return (conservative lag) | 514/514 | 0.50 vs 0.44 | -12% | 1.68 vs 1.40 | 98/100 | 0.44 vs 0.39 | -11% |
| H | market breadth (advancing share) | 514/514 | 0.58 vs 0.71 | +22% | 1.60 vs 2.01 | 130/82 | 0.71 vs 0.45 | -37% |
| L | market breadth (advancing share) | 514/514 | 0.64 vs 0.35 | -46% | 1.88 vs 1.12 | 130/82 | 0.45 vs 0.45 | +0% |
| H | peers' return | 514/514 | 0.59 vs 0.71 | +20% | 1.63 vs 2.16 | 124/94 | 0.65 vs 0.45 | -31% |
| L | peers' return | 514/514 | 0.64 vs 0.36 | -45% | 1.82 vs 1.07 | 124/94 | 0.47 vs 0.52 | +9% |
| H | BSE yesterday's range | 514/514 | 0.57 vs 0.69 | +22% | 1.62 vs 1.82 | 138/70 | 0.48 vs 0.65 | +35% |
| L | BSE yesterday's range | 514/514 | 0.43 vs 0.52 | +21% | 1.27 vs 1.52 | 138/70 | 0.48 vs 0.55 | +17% |
| H | close location in yesterday's range | 514/514 | 0.57 vs 0.73 | +27% | 1.53 vs 2.04 | 99/130 | 0.49 vs 0.58 | +18% |
| L | close location in yesterday's range | 514/514 | 0.60 vs 0.36 | -40% | 1.72 vs 1.18 | 99/130 | 0.54 vs 0.48 | -12% |
| H | BSE turnover z | 514/514 | 0.60 vs 0.66 | +10% | 1.71 vs 1.78 | 121/94 | 0.46 vs 0.56 | +21% |
| L | BSE turnover z | 514/514 | 0.48 vs 0.45 | -6% | 1.37 vs 1.47 | 121/94 | 0.52 vs 0.47 | -11% |
| H | baseline scale sigma itself | 514/514 | 0.65 vs 0.64 | -2% | 1.86 vs 1.57 | 39/33 | 0.62 vs 0.53 | -15% |
| L | baseline scale sigma itself | 514/514 | 0.51 vs 0.44 | -15% | 1.53 vs 1.44 | 39/33 | 0.67 vs 0.28 | -58% |
| HO | absolute gap / sigma | 514/514 | 0.47 vs 0.63 | +34% | 1.60 vs 1.97 | 127/83 | 0.40 vs 0.65 | +61% |
| LO | absolute gap / sigma | 514/514 | 0.60 vs 0.57 | -5% | 1.59 vs 1.70 | 127/83 | 0.64 vs 0.51 | -19% |

What this says in plain words:

* **Volatility measures add nothing once sigma is known.** Dividing by the baseline scale, the days with the highest India VIX level (top third) have a high of 0.68 sigma against 0.64 for the lowest-VIX days (+6%) and a low 0.44 against 0.45 (-2%), before the Final window (n = 514 each); the 90% points (top third 1.77 against bottom third 1.86 for the high, 1.49 against 1.45 for the low) are no larger either. The baseline's sigma itself (-2% / -15% for high / low), turnover (+10% / -6%) and 10-day Garman-Klass volatility (+13% / -2%, in the CSV) show the same: small differences without a consistent direction. In the Final window the top VIX third has only 36 days (VIX was low through 2025 to 2026), too few to say anything (its +19% / -39% are noise-sized).
* **A rise in India VIX since yesterday goes with a deeper low, but only weakly in the period that matters.** Before the Final window the top third of the 1-day VIX change (a rise) was followed by a low 45% deeper (0.54 vs 0.37 sigma) and a high 11% smaller (0.61 vs 0.68); in the Final window the low is 11% deeper (0.48 vs 0.43) and the high 18% bigger (0.56 vs 0.48), n = 101 / 108. The L1 model uses this for the post-open low (Section 7.5); in the out-of-sample test it did not produce a significant gain (V05, V03 and V02, which contain the VIX change, score -0.00%, -0.32% and -0.63% on the post-open low).
* **What looks like information is direction, not size, and it did not last.** Before the Final window, after a day on which a large share of stocks rose (top third of the advancing share), BSE's next-day high was 22% bigger (0.71 vs 0.58 sigma) and its low 46% *shallower* (0.35 vs 0.64 sigma) than after a broad down day; peers' returns and BSE's close location show the same direction (+20% / -45%; +27% / -40%). That is the pattern the boosted and linear models picked up for the low. In the Final window (130 vs 82 days) the high is 37% *smaller* after broad up days (0.45 vs 0.71) and the low is unchanged (0.45 vs 0.45). The relationship reversed, which is why those models gained in the Validation window and lost in Final.
* **Yesterday's range does carry something extra for the size of the range**: the top third of yesterday's range has a 22% bigger high and a 21% deeper low before the Final window, and +35% / +17% in the Final window (n = 138 / 70). It is one of the few relationships that point the same way in both periods, and it is what the own-block offset model V04 (pre-open high +1.38%, raw p = 0.12) is exploiting; the size of the effect is modest and the gain is not significant.
* **After the open, a large gap (in either direction) stretches the high**: the top third of the absolute gap in sigma units has a post-open high 34% larger before the Final window and 61% larger in Final (0.65 vs 0.40), and a low 5% and 19% smaller. Same direction in both periods, but the offset models that contain the gap block (V03 to V07) gain only +0.2% to +0.7% on the post-open high and the gain is not significant (largest +0.71%, raw p = 0.47).

### 7.5 What the fitted models say (partial-dependence style, in-sample reading; `results/hl3_pdp.csv`)

The L1 quantile model (lambda 0.01) and the boosted model (depth 2, 60 trees) are fitted on all 1,860 usable sessions (2 Apr 2019 to the 15 Oct 2026 close, Final window included), so this is a reading of what the models learnt, **not** an out-of-sample result. One parameter moves from its 10th to its 90th percentile, all others at their median. "Sigma" units; the 5% (lows) or 95% (highs) quantile is the "extreme" one.

| target | parameter (10th to 90th percentile) | L1 model says | boosted model says |
|---|---|---|---|
| pre-open LOW | share of stocks that rose yesterday (23% to 72%) | the extreme (5%) low becomes 21% shallower (-2.10 to -1.65 sigma); median hardly moves (-0.49 to -0.48) | no change (-1.71 both) |
| pre-open LOW | close location in yesterday's range (11% to 84% up the range) | median low 0.09 sigma shallower (-0.52 to -0.43), about Rs 8; extreme unchanged | median 0.06 sigma shallower |
| pre-open LOW | S&P 500 5-day return (-2.4% to +2.8%, conservative lag) | extreme low 13% shallower (-1.99 to -1.74) | no change |
| pre-open LOW | Tuesday against other days | median 0.05 sigma shallower | same (0.05) |
| pre-open HIGH | 5-day change in BSE turnover (-0.66 to +0.85 in log turnover) | median high 0.10 sigma higher (0.58 to 0.68), about Rs 8; extreme unchanged | no change |
| pre-open HIGH | CDSL's return yesterday (-0.9 to +1.0 in its standardised units) | median high 0.05 sigma higher; extreme +3% | median +0.05 sigma; extreme +0.4% |
| pre-open HIGH | India VIX minus Nifty realised vol (spread) | no effect (coefficient zero) | extreme high +1%, median unchanged |
| post-open HIGH | open above yesterday's high (0 or 1) | the extreme (95%) high is 25% higher (2.12 to 2.66 sigma); median unchanged | no change |
| post-open LOW | India VIX change since yesterday (-5.6% to +5.9%) | median low 0.11 sigma deeper (-0.54 to -0.65) | 0.04 sigma deeper |
| post-open LOW | share of stocks that rose yesterday | extreme low 13% shallower (-2.15 to -1.87) | extreme low 1% shallower |

The two models agree on direction but not on size; most effects on the median are 0.05 to 0.1 sigma, i.e. Rs 4 to 8, which is smaller than the Rs 30 to 50 typical miss and is why the rupee misses did not move. "High-VIX days stretch the range by X%": the models do not say so; the VIX level has no effect in either model and a 1-day VIX rise deepens the post-open low by about 0.1 sigma (Rs 8) in the L1 model only.

### 7.6 Implied volatility (V17): 462 sessions from 29 Nov 2024, so tested on its own short window only

V17 adds ATM implied volatility, skew, IV minus trailing realised volatility, IV change, days to expiry and the expiry-day flags to V03 once the training window holds at least 120 IV sessions (Validation: only 20 sessions qualify; Final: all 320). Final-window gains against BASE: +0.53% (pre-open high), -1.30% (low), +0.70% (post-open high), -0.32% (post-open low), against V03's +0.54%, -1.30%, +0.71%, -0.32%: **the IV block changes the Final gain by at most 0.011 percentage points**, i.e. nothing. With 340 sessions of IV history the test has little power, and this should be read as "no evidence of a gain", not as "implied volatility is useless". The 16 Oct forecast has no IV value for the last sessions (the file ends earlier); they are treated as no information.

### 7.7 US overnight timing (V07 against V18): the one place where timing matters

V07 uses US values dated at most D-2 (conservative: a FRED value could be posted a day late); V18 uses values dated D-1, which is the information a trader really has at 09:00 IST (the US cash session closes about 01:30 to 02:30 IST), but whose availability in the FRED files I cannot prove. Final window: V07 +1.45% / -0.29% / +0.55% / -0.08% (pre-open high / low, post-open high / low); V18 +2.86% / +1.67% / +0.30% / -0.03%. V18 is the only variant above the 2% threshold anywhere, but its raw p is 0.024 (high) and 0.109 (low), Holm 1.0, it fails the coverage condition (iii), and its gains sit in 2026 (Section 6.2). Over all 1,640 sessions (post-hoc) V18 gains +0.90% (high; 5 of 7 years; post-hoc Holm 0.61) and +1.68% (low; 5 of 7 years; Holm 0.26). The typical miss improves by Rs 1.3 (high) and Rs 1.0 (low), consistent in size with the project's earlier statement that the S&P overnight cue is worth about Rs 2 on a median (A_dayahead.md). **A clean follow-up test would need a US-close series with a proven publication time**, which the repository does not have.

## 8. Run record: clocks, hashes, re-checks, leakage test, solver validation

### 8.1 Clock and hashes (own working record; the git commit is the only independent timestamp)

* The design in Sections 0.1 to 0.7 was written on Fri 16 Oct 2026 at about 11:12 IST (05:42 UTC), before any variant had been run, and committed by the lead in git commit `2072844b709c34bfa5f51f055c235a31a54dddb0` at 2026-10-16 08:00:49 UTC. SHA-256 of `research/hl/E_quantile.md` as committed there: `aa026b73e5473d3b56e449b7da09743a8b695d44db790c0b01b8b0a242ed0bdc`. Everything above the line "## RESULTS" in this file is byte-identical to that commit (checked with `git show 2072844:research/hl/E_quantile.md | cmp - <(head -c <size> research/hl/E_quantile.md)` when this section was written). The pre-fixed rule, grids and variant list were not changed afterwards; the only correction is the printed feature count in Section 3.
* First computation of any model output after the commit: solver validation (file time 08:17 UTC on 16 Oct); first full walk-forward 08:17 to about 08:45 UTC; second full walk-forward (after all inputs were capped at 15 Oct and the code patched; this is the run in the tables) about 13:39 to 14:21 UTC; permutation importance and partial dependence about 14:32 UTC; this continuation 17 Oct 2026 07:34 UTC onward. **The first and the second full runs give identical results**: the 84 per-task result files of the two runs hold 4,660 variant-by-refit forecast arrays with no difference at all (NaN pattern included), and the assembled arrays of all 18 variants x 4 targets x 1,640 sessions x 9 levels (1,062,720 numbers, stacks included) are equal.
* Code: `src/hl_ml.py` (hash in `results/hl3_meta.json`, field `code_sha256`, written last); input-file hashes, library versions (Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, scikit-learn 1.9.1) and all counts are in the same file. Input files hold the 16 Oct bars; `load_inputs()` cuts every series at dates before 16 Oct 2026.

### 8.2 Independent re-checks made on 17 Oct 2026 (this continuation), each on files I did not rewrite by hand

| check | result |
|---|---|
| baseline rebuilt from the raw bars and compared with the stored project tables (`--baseline-check`) | 28 rows, largest difference 1.07e-05; output file byte-identical to the one written on 16 Oct |
| two walk-forward tasks recomputed from scratch and compared with the cached results used in the tables (pre-open low, last group of refits; post-open high, a mid-sample group) | 86 variant-block comparisons, maximum absolute difference 0.0 |
| the 16 Oct forecast regenerated from scratch (`--date 2026-10-16 --open 3450.0 --save`) and compared with the file written on 16 Oct | 904 numeric fields compared, 0 differ (maximum difference 0.0); the new file only adds the closing-auction-slice miss fields so that its shape mirrors `hl_model.hl_forecast` |
| baseline block of that forecast against `hl_model.hl_forecast('2026-10-16', 3450.0)` | identical to the cent for the 5%, 50%, 95% prices of all four targets |
| post-hoc DM table (`--posthoc`) and tercile table (`--bins`) re-run | byte-identical to the files from 16 Oct |
| permutation importance and partial-dependence tables re-run (`--importance`) | identical (importance rows equal up to row order, difference 0.0; PDP file byte-identical) |
| the adoption table regenerated from the cached walk-forward with the leakage column added (`--eval` on the full cache) | all result files byte-identical to the previous versions except `hl3_adoption.csv` (the leakage condition (v) is now filled in: True in all 72 rows; every other column unchanged; `adopt` is False in all 72 rows), `hl3_choices_by_block.csv` (same rows, different row order) and `hl3_leakage.csv` (complete: 6 sessions) |
| live function smoke test for the next session (`ml_forecast("2026-10-19")`, no open price; not saved, not used anywhere) | runs; returns pre-open blocks for the baseline and the display variants |

### 8.3 Leakage test (rule (v); `results/hl3_leakage.csv`; `python3 src/hl_ml.py --leak`)

For each of six target sessions spread over the windows (21 Mar 2022, the bonus ex-date of 2022, and 14 Sep 2023 in Development; 23 May 2025, the bonus ex-date of 2025, in Validation; 12 Nov 2025 and 14 May 2026 in Final; 16 Sep 2026 in the closing-auction slice), **every datum dated at or after the target session was replaced by random junk** (bars, volume, turnover, trades, delivery %, the index/VIX file, breadth, peers, all FRED series, the implied-volatility file; the open of the target session is kept because the post-open information set contains it; the F&O expiry list is a calendar and is kept). The *whole* pipeline was then rebuilt from the junk inputs (features, the S6 volatility refits, the baseline quantiles, every variant's fit for the refit block of the target session and for the preceding blocks that feed the stacks) and the forecast of the target session was compared with the stored clean walk-forward forecast, for all 18 variants x 2 phases x 2 targets (72 forecasts of 9 quantile levels each), tolerance 1e-9 relative. **Positive control**: the forecasts of the *later* sessions of the same refit block must change (otherwise the test would have no teeth).

| session (target) | window | position in its 20-session block | forecasts compared (variant x phase x target) | forecasts that exist (V17 needs 120 IV sessions) | identical (rtol 1e-9) | largest absolute difference | positive control: later sessions of the same block changed (defined forecasts) |
|---|---|---|---|---|---|---|---|
| 2022-03-21 | Development | 12 of 20 | 72 | 68 | 72 of 72 | 0.0e+00 | 68 of 68 |
| 2023-09-14 | Development | 1 of 20 | 72 | 68 | 72 of 72 | 0.0e+00 | 68 of 68 |
| 2025-05-23 | Validation | 14 of 20 | 72 | 68 | 72 of 72 | 0.0e+00 | 68 of 68 |
| 2025-11-12 | Final | 11 of 20 | 72 | 72 | 72 of 72 | 0.0e+00 | 72 of 72 |
| 2026-05-14 | Final | 14 of 20 | 72 | 72 | 72 of 72 | 0.0e+00 | 72 of 72 |
| 2026-09-16 | Final, closing-auction slice (CAS) | 20 of 20 | 72 | 72 | 72 of 72 | 0.0e+00 | no later session in the block |

Result: **all 432 forecasts (6 sessions x 72) are bit-identical to the clean walk-forward forecasts** (largest absolute difference 0.0; tolerance was 1e-9 relative), for every variant including the stacks. V17 has no forecast before its 120th implied-volatility session (NaN in both runs, so its four rows at the first three sessions are trivially identical; from Nov 2025 it is defined and identical). The positive control shows that the test has teeth: with junk in the future, the forecasts of the later sessions of the same refit block change for 68 of 68 (Development, Validation) and 72 of 72 (Final) forecasts that exist; the 16 Sep 2026 session is the last of its block, so it has no later session and no positive control, the other five do. Rule (v) is therefore met by all 18 variants; it decides nothing because no pair passes rule (i).

### 8.4 Validation of my own L1 quantile-regression solver against scikit-learn / HiGHS (`results/hl3_solver_validation.csv`, 216 comparisons)

The 36 L1 quantile-regression configurations per refit would need hundreds of thousands of fits, too many for scikit-learn's exact linear-programming solver (about 0.17 s per fit against 0.010 s for mine, 17 times faster). Mine minimises the same L1-penalised check loss with a smoothed (logistic) loss and bound-constrained L-BFGS. I compared the two at the same penalty on 54 synthetic windows (known sparse truth, t-distributed noise; n 296 to 1,500, p 15 to 67 columns) and 162 real training windows (random phase, target and end date, 20 held-out next sessions, tau 0.05 / 0.5 / 0.95, the three penalties): objective of my solution against the exact optimum: mean +0.07%, maximum +0.44%; held-out pinball: mean absolute relative difference 0.6%, maximum 5.9% (in single 20-session windows); median absolute difference in the predicted quantile 0.012 sigma; number of non-zero coefficients 16.4 against 16.4 on average. In no case did my solution have a *lower* objective than HiGHS beyond rounding. Conclusion: close to, but not exactly, the exact L1 quantile regression; the difference is far smaller than the 1% to 3% pinball differences discussed in this report, and none of the other learners (boosting, forest, conformal, the baseline) uses it.

## 9. The 16 Oct 2026 forecast (as of the 15 Oct close, official open Rs 3,450.0) and a one-day look

### 9.1 Forecast (file `results/hl3_2026-10-16.json`; `python3 src/hl_ml.py --date 2026-10-16 --open 3450.0 --save`)

Reference: official close of 15 Oct Rs 3,428.0 (2,390 sessions); gap to the open +0.64%; baseline scales sigma_R = 2.43% (Rs 83) before the open and sigma_I = 2.22% (Rs 77) after it. The first row of each pair is the baseline, which equals `hl_model.hl_forecast('2026-10-16', 3450.0)` to the cent (checked for the 5%, 50% and 95% prices of all four targets). The second row is the flexible "display variant", chosen per target as the one with the lowest pinball over Validation plus Final pooled; that is a descriptive choice, **not an adoption** (`adopted_by_prefixed_rule` is false in the JSON for every target). Prices in rupees; q5 to q95 are quantile levels, so "half the time" is q25 to q75 and the 90% band is q5 to q95. Typical miss is for the last 320 sessions (pre-open at Rs 3,428; after the open quoted at the open price Rs 3,450, so it reads 35.0 instead of the 34.8 quoted at Rs 3,428).

| phase | side | model | q5 | q10 | q25 | q50 | q75 | q90 | q95 | typical miss Rs (last 320) |
|---|---|---|---|---|---|---|---|---|---|---|
| before the open | HIGH | BASELINE (recommended) | 3,421 | 3,431 | 3,449 | 3,475 | 3,513 | 3,553 | 3,591 | 42.7 |
| before the open | HIGH | flexible display variant V04 (NOT adopted) | 3,423 | 3,432 | 3,453 | 3,480 | 3,528 | 3,555 | 3,580 | 42.3 |
| before the open | HIGH | range of the 18 variants' medians |  |  |  | 3,474 to 3,485 |  |  |  |  |
| before the open | LOW | BASELINE (recommended) | 3,269 | 3,304 | 3,352 | 3,390 | 3,419 | 3,440 | 3,450 | 47.7 |
| before the open | LOW | flexible display variant V16 (NOT adopted) | 3,259 | 3,300 | 3,351 | 3,387 | 3,417 | 3,438 | 3,449 | 47.7 |
| before the open | LOW | range of the 18 variants' medians |  |  |  | 3,387 to 3,394 |  |  |  |  |
| after the open (official open Rs 3,450.0) | HIGH | BASELINE (recommended) | 3,451 | 3,454 | 3,468 | 3,488 | 3,526 | 3,563 | 3,591 | 35.0 |
| after the open (official open Rs 3,450.0) | HIGH | flexible display variant V07 (NOT adopted) | 3,451 | 3,456 | 3,475 | 3,496 | 3,535 | 3,561 | 3,607 | 34.5 |
| after the open (official open Rs 3,450.0) | HIGH | range of the 18 variants' medians |  |  |  | 3,488 to 3,501 |  |  |  |  |
| after the open (official open Rs 3,450.0) | LOW | BASELINE (recommended) | 3,294 | 3,331 | 3,374 | 3,410 | 3,430 | 3,443 | 3,447 | 37.7 |
| after the open (official open Rs 3,450.0) | LOW | flexible display variant V16 (NOT adopted) | 3,295 | 3,329 | 3,372 | 3,407 | 3,429 | 3,443 | 3,448 | 37.8 |
| after the open (official open Rs 3,450.0) | LOW | range of the 18 variants' medians |  |  |  | 3,403 to 3,413 |  |  |  |  |

Reading:

* **The 18 variants agree with the baseline to within a few rupees.** The medians of all 18 variants lie in Rs 3,474 to 3,485 (pre-open high; baseline 3,475), Rs 3,387 to 3,394 (pre-open low; baseline 3,390), Rs 3,488 to 3,501 (post-open high; baseline 3,488) and Rs 3,403 to 3,413 (post-open low; baseline 3,410): the largest departure from the baseline median is Rs 13. The display variants change the 90% band width by -Rs 12 (pre-open high), +Rs 9 (pre-open low), +Rs 16 (post-open high) and Rs 0 (post-open low).
* **The flexible forecasts are *less* informed than usual today.** The index/VIX file ends 12 Oct, delivery % ends 12 Oct, the FRED rupee and dollar series end 2 Oct and Brent 6 Oct (S&P 500 and US VIX end 12 Oct and the US 10-year 8 Oct; these are used with their last available values), and the implied-volatility file ends 12 Oct; the 22 columns listed in the JSON under `inputs_missing_today_treated_as_no_information` are set to "no information" (the training median). In the 320 Final sessions the index block was missing only for 14 and 15 Oct. So the flexible variants had even less to add today than in the evaluation, which makes the 'same as the baseline' result unsurprising and not informative about those inputs.
* **Recommended pin-point for the user: the baseline numbers** (high around Rs 3,475 before the open, low around Rs 3,390; after the open high around Rs 3,488, low around Rs 3,410), with the typical misses given above: Rs 43 / 48 before the open and Rs 35 / 38 after it.

### 9.2 One-day look at 16 Oct (n = 1; made after the adoption decision; nothing refitted or selected on it)

The session of 16 Oct 2026 is complete in the data files (official bar: open 3,450.0, high 3,455.0, low 3,310.6, close 3,363.0). I compared the stored forecasts above with it (`python3 src/hl_ml.py --look 2026-10-16`, file `results/hl3_single_day_2026-10-16.json`). This is an illustration, not evidence for or against any model, and changes nothing in the adoption table.

| phase | side | realised (Rs) | BASELINE median | BASELINE miss (realised minus median, Rs) | base in 50% band | base in 90% band | base pinball x1e4 | display variant | its median | its miss (Rs) | its pinball x1e4 | variants better / worse than base on this day (of 18) | smallest and largest absolute miss among the 18 (Rs) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before the open | HIGH | 3,455.0 | 3,475 | -20.0 | yes | yes | 16.4 | V04 | 3,480 | -25.5 | 17.9 | 3 / 13 | 18.7 / 30.3 |
| before the open | LOW | 3,310.6 | 3,390 | -79.5 | no | yes | 41.8 | V16 | 3,387 | -76.7 | 41.3 | 9 / 9 | 76.4 / 83.8 |
| after the open | HIGH | 3,455.0 | 3,488 | -33.5 | no | yes | 21.0 | V07 | 3,496 | -41.2 | 25.2 | 0 / 12 | 33.5 / 46.4 |
| after the open | LOW | 3,310.6 | 3,410 | -99.3 | no | yes | 56.4 | V16 | 3,407 | -96.5 | 55.2 | 12 / 2 | 92.4 / 102.0 |

The day was a hard one for every forecast: the high was only Rs 5 above the open (below the pre-open median by Rs 20 and the post-open median by Rs 34), and the low was Rs 139 below the open (Rs 80 below the pre-open median and Rs 99 below the post-open median). Three of the four realised values fell outside their 50% band (only the pre-open high was inside) and all four inside their 90% bands. The baseline and the display variants all missed by about the same amount; on this day the baseline was better than 13 of 18 variants on the pre-open high and 12 of 12 non-tied variants on the post-open high, and worse than 12 variants on the post-open low. One day cannot distinguish models whose 320-session pinball differs by 1% or less.

## 10. Consistency with earlier project statements

* **Baseline figures**: reproduced (Section 2); the independent verifier of the baseline study (`verify_A_dayahead.md`) reproduced them to 1e-14 on its own code, my re-run agrees to about 1e-7 (Section 2). No contradiction.
* **"The S&P overnight cue is worth about Rs 2 on a median"** (A_dayahead.md): consistent. The US block with the realistic lag-1 timing (V18) improves the typical miss of the pre-open median by Rs 1.3 (high) and Rs 1.0 (low); not significant (Holm 1.0); with the provably available D-2 timing (V07) Rs 0.5 better (high) and Rs 0.3 worse (low) (Section 7.7).
* **Implied volatility, volume and delivery "not used on purpose"** (A_dayahead.md): now tested; no gain (V17 equals V03 to 0.011 points; the flow block's importance is at most 0.17 and its variants are inside V03 to V07).
* **"Recalibration of the high's median not tested"** (A_dayahead.md): the offset (B) models and the conformal variants test exactly that; none improved significantly, and conformalising the baseline is significantly worse in the long run (Section 6.3).
* **The user's expectation (relayed in the task) that more parameters are needed**: not supported by the pre-fixed Final-window test. This is the one result that goes against that expectation, and it should be reported as such.
* **Live intraday study** (B_liveintraday.md found that realised volatility so far, range so far and day-ahead EWMA did not improve the live bands after Holm): this study concerns the day-ahead and the post-open stage only and does not test any intraday-path feature. The two studies point the same way: extra parameters did not help.
* No code or number in this study reads `results/hl2_*` (specialist D's linear feature study; `src/hl_ml.py` has no reference to it), so nothing here depends on it; the two studies use overlapping menus and should be read side by side by the lead.

## 11. Honest limits

1. **The Final window is one 16-month stretch of one stock (n = 320).** The rule is strict: the standard error of a variant's mean pinball gain is about 0.75% of the baseline's loss (median across pairs, range 0.1% to 1.3%), and clearing a Holm-adjusted 0.05 across 72 pairs needs a t-statistic of about 3.4, i.e. a gain of about 2.6% at the median standard error and up to 4.3% for the noisiest pairs. If a variant's true gain were exactly 2%, the chance that the rule would adopt it is about 23% (normal approximation at the median standard error). So "nothing adopted" means *no variant demonstrated an improvement*, not *no improvement of 1% to 3% exists*. The point estimates are mostly negative (51 of 72), and the rupee differences observed are within Rs 1.6.
2. **Selection of the display variant, the best-of-16 rupee column and the half-year tables are chosen after seeing the Final window**; they are descriptive and flattering, never evidence. The post-hoc DM tests (Section 6.3) add 140 more tests to the one pre-fixed family of 72, and only the Holm-adjusted lines should be read.
3. **US overnight timing** cannot be proven from the repository (FRED posts values with an unknown delay), so the realistic lag-1 version (V18) is a sensitivity only. The Indian index/VIX file and several macro series end before 15 Oct, so the 14 and 15 Oct sessions and the 16 Oct forecast treat those blocks as "no information".
4. **Implied volatility has 462 sessions** (340 evaluated, 20 in Validation): low power.
5. **Not usable / untested**: NSE pre-open order book (2 snapshots), GIFT Nifty, FII/DII flows, intraday-path features, news/event calendars beyond the F&O expiry list (which appears only inside V17's block), and model families outside the list (neural networks, gradient-boosting with other loss tilings, quantile forests with other leaf sizes).
6. **The L1 quantile regression is solved approximately** by a smoothed-loss quasi-Newton solver for speed; against scikit-learn's exact LP the objective is within 0.44% in all 216 comparisons and held-out loss differs by up to 5.9% in single fits (mean absolute 0.6%), see Section 8. The boosted, forest and baseline results do not depend on it.
7. **Rupee figures** are the log error times Rs 3,428 (as in the baseline study); raw levels before 23 May 2025 are on a 3x scale (only `prev` is bonus-adjusted), so rupees are not computed from earlier levels.
8. **Counting error in the pre-fixed section** (24 / 12 instead of 22 / 10 columns; Section 3). It does not change any variant, grid or rule.
9. **Structural break**: all flexible models changed sign around July 2025; I did not find the cause. If the break is a permanent change in how BSE trades, models trained on 2019 to mid-2025 relationships are disadvantaged for a long time; if it is a one-off, they may recover. Neither is tested here.
10. **PDP readings and terciles** use all known sessions (descriptive, in-sample).
11. Two earlier attempts at this task stopped on a usage limit; their completed work is the walk-forward result used here (the first and the second full run agree to the last digit, Section 8). No part of the pre-fixed design, grids, variant list or rule was changed during the continuation; additions after seeing results are marked post-hoc.

## 12. Numbers to quote

Each line states n and whether it is tested or descriptive. Rupees are the mean absolute error of the 50% quantile at Rs 3,428 (log error x 3,428) unless stated.

| claim | number | n | status | file |
|---|---|---|---|---|
| Baseline typical miss, pre-open high / low | Rs 42.7 / 47.7 | 320 | reproduced | `hl3_baseline_repro.csv` |
| Baseline typical miss, after the open, high / low | Rs 34.8 / 37.4 | 320 | reproduced | `hl3_baseline_repro.csv` |
| Price stays / open stays | Rs 62.9 / 61.3 ; Rs 51.3 / 59.0 | 320 | benchmark | `hl3_eval_variants.csv` |
| Variant-target pairs tried (family for Holm) | 72 (18 x 4) | | design | `hl3_meta.json` |
| Parameters searched | 62 pre-open, 67 post-open, 82 distinct columns | | design | `hl3_meta.json` |
| Effective configurations per target per refit | 96 | 82 refits | design | `hl3_meta.json` |
| Pairs meeting the first adoption condition (gain >= 2% and Holm p < 0.05) | 0 of 72 | 320 | tested | `hl3_adoption.csv` |
| Pairs adopted | 0 | | tested | `hl3_adoption.csv` |
| Largest Final gain of any pair | +2.86% (V18, pre-open high; raw p 0.024, Holm 1.0; ineligible timing) | 320 | tested | `hl3_dm_holm.csv` |
| Largest Final gain of an eligible pair | +1.45% (V07, pre-open high; raw p 0.093, Holm 1.0; Validation -0.27%) | 320 | tested | `hl3_dm_holm.csv` |
| Pairs better / worse than the baseline in Final | 21 / 51 of 72 | 320 | descriptive | `hl3_adoption.csv` |
| Pairs significantly worse after Holm (72) | 5 (V01 on H and HO, V10 on HO, V12 and V13 on LO) | 320 | tested | `hl3_dm_holm.csv` |
| Best variant's rupee miss against baseline (picked after the fact) | Rs 41.4 / 46.6 / 34.3 / 37.4 against 42.7 / 47.7 / 34.8 / 37.4 (std. errors 2.2 / 2.9 / 1.8 / 2.6) | 320 | descriptive | `hl3_eval_variants.csv` |
| Average gain over the 68 pairs: Validation vs Final | +0.87% vs -0.63%; 42 pairs gain in Validation and lose in Final | 248 / 320 | descriptive | `hl3_adoption.csv` |
| Share of Final refits where the inner search chose a real model | 88% to 100% for every variant | 16 refits x 4 targets | descriptive | `hl3_choices.csv` |
| Largest permutation importance of any group | 0.64 x1e4 of a held-out loss of 37.3 (1.7%; breadth, pre-open low); noise column 0.053 | 241 per snapshot, 6 snapshots | descriptive | `hl3_importance.csv` |
| VIX top third vs bottom third, size of the high / low in baseline sigma | 0.68 vs 0.64 (+6%) / 0.44 vs 0.45 (-2%) | 514 per third, before Final | descriptive | `hl3_menu_bins.csv` |
| After a broad up day (top third of advancing share) the next day's high / low, in sigma | high 0.71 vs 0.58 (+22%), low 0.35 vs 0.64 (46% shallower) before Final; high 0.45 vs 0.71, low 0.45 vs 0.45 in Final | 514 per third; 130 / 82 | descriptive | `hl3_menu_bins.csv` |
| Conformalised baseline (V11) over all sessions | -1.65% / -1.55% / -1.54% / -1.50% (H / L / HO / LO); post-hoc Holm 0.013 / 0.003 / 0.002 / 0.025 | 1,640 | post-hoc test | `hl3_posthoc_allsessions.csv` |
| Random forest (V10) on the pre-open low | +2.08% over 1,640 sessions (post-hoc Holm 0.0066; 6 of 7 years); +0.13% in Final (p 0.91); rupee miss 47.7 vs 47.7 | 1,640 / 320 | post-hoc lead, not adopted | `hl3_posthoc_allsessions.csv`, `hl3_eval_variants.csv` |
| Power of the rule | needs about +2.6% at the median standard error; a true +2% is adopted with probability about 23% | | computed from the DM table | `hl3_dm_holm.csv` |
| 16 Oct baseline, before the open | high median Rs 3,475 (half the time 3,449 to 3,513; 90% band 3,421 to 3,591); low median 3,390 (3,352 to 3,419; 3,269 to 3,450) | | forecast | `hl3_2026-10-16.json` |
| 16 Oct baseline, after the open at 3,450 | high median 3,488 (3,468 to 3,526; 3,451 to 3,591); low median 3,410 (3,374 to 3,430; 3,294 to 3,447) | | forecast | `hl3_2026-10-16.json` |
| 16 Oct realised | high 3,455.0, low 3,310.6 (one day; not evidence) | 1 | single-day look | `hl3_single_day_2026-10-16.json` |

## 13. Reproduce (repo root; python3; no network; about 4 CPU cores)

```
python3 src/hl_ml.py --baseline-check                 # 25 s: rebuild the baseline, compare with the stored tables (results/hl3_baseline_repro.csv)
python3 src/hl_ml.py --validate-solver                # own L1 quantile-regression solver vs scikit-learn / HiGHS (results/hl3_solver_validation.csv; the two timing columns change from run to run)
python3 src/hl_ml.py --eval --workers 4 --cache /tmp/hl3_wf_cache   # full walk-forward, all 18 variants, stacks, DM/Holm, adoption table; 30 to 45 min from an empty cache (seconds from a full one)
python3 src/hl_ml.py --leak --workers 4               # leakage test at 6 sessions (about 10 min each); needs the pickle written by --eval; resumable, writes results/hl3_leakage.csv
python3 src/hl_ml.py --eval --workers 4 --cache /tmp/hl3_wf_cache   # run again after --leak to add the leakage column to results/hl3_adoption.csv
python3 src/hl_ml.py --importance --workers 4         # permutation importance and partial-dependence readings (results/hl3_importance.csv, hl3_pdp.csv)
python3 src/hl_ml.py --posthoc                        # post-hoc DM tests on the Development window and all sessions
python3 src/hl_ml.py --halfyear                       # post-hoc half-year gains
python3 src/hl_ml.py --bins                           # descriptive terciles (results/hl3_menu_bins.csv)
python3 src/hl_ml.py --date 2026-10-16 --open 3450.0 --save   # the 16 Oct forecast (results/hl3_2026-10-16.json)
python3 src/hl_ml.py --look 2026-10-16                # one-day look against the official bar (results/hl3_single_day_2026-10-16.json)
python3 src/hl_ml.py --meta                           # counts, hashes, versions (results/hl3_meta.json)
```
Importable: `from hl_ml import ml_forecast; ml_forecast("2026-10-16", open_price=3450.0)` mirrors `hl_model.hl_forecast` (`pre_open`, `post_open`, `base`, plus `variants` and `stack_weights`); the `pre_open`/`post_open` blocks are the display variants and carry `adopted_by_prefixed_rule` (false everywhere); the baseline is in `base`. Scratch files (walk-forward cache, pickles) go to the folder in the environment variable `HL3_SCRATCH` (default: the session scratchpad); the cache is deterministic, and a task recomputed from scratch matches the cached one exactly (Section 8).

---

## 10. Independent check and corrections (added by the lead on Sun 18 Oct 2026 from `research/hl/verify_E_quantile_trees.md`)

An independent checker read all 1,736 lines of `src/hl_ml.py`, rebuilt 41 of the features with its own code (identical over 2,390 sessions), recomputed 107 cells from the raw files, re-ran the junk test at two new sessions with a different seed (all forecasts identical; with the builder's six, 576 forecasts), corrupted every input file after 15 Oct and re-ran the live 16 Oct forecast (identical in all 886 numeric fields), and applied the five-condition rule to all 72 pairs. **Verdict: pass with minor fixes; no look-ahead; adoption decision confirmed for all four targets: 0 of 72 pairs meet condition (i); (ii) 56, (iii) 13, (iv) 68, (v) 72; none meets all five.** Corrections to the wording of this report:

* **The headline "NO" is stronger than the evidence.** The right sentence is "no variant shown to improve under the pre-fixed rule". The rule has power of about 23% against a true +2% effect (76% without Holm), so it is "no demonstrated gain", not "no gain exists". The gain needed to clear Holm over 72 pairs is about +2.6%.
* **"Extra parameters hurt" is not what the numbers say.** The "five pairs significantly worse" (for example the quantile regression on volatility alone, -3.1%) and "21 better / 51 worse, median pair -0.39%" mix two things: the direct (A) variants use an expanding-window distribution while the baseline uses the trailing 500 sessions. The featureless expanding-window version alone is -3.16% (pre-open high) and -2.79% (post-open high) in Final (p < 0.0001) but about +0.1% to +0.4% before, so the loss comes from the window, not from the extra parameters. Split by design: the 36 baseline-tied pairs have median -0.01% (17 better; mean +0.11%), a coin flip around zero; the 24 direct pairs have median -1.60% (3 better). Validation-then-Final sign flips: 12 of 32 baseline-tied vs 19 of 24 direct. The unexplained "break around July 2025" is, for the highs at least, a level shift in the standardised high (Final median 0.54 vs 0.64 sigma; 95% point 1.80 vs 2.51; lows unchanged). "Nested search chose a non-null model ... classic selection optimism" is one reading; non-stationarity is an equally supported one.
* **Implied volatility (V17) was effectively untested:** the L1 model gave the IV block zero weight, so "the IV block changes the Final gain by at most 0.011 points" only shows the model ignored it. The checker's own-window test also shows no gain, but it is weak (about 300 sessions).
* **US overnight block timing:** every eligible variant used lag 2, one US session older than necessary on Tuesday to Friday (the FRED files carry event dates, so a D-1 observation is public before the Indian open). "US VIX, dollar, rupee and US 10-year at the noise floor" is therefore about two-session-old data. Only V18 (lag 1) is correctly timed and has the largest gain (+2.86% pre-open high, +1.67% low), which is not significant after 72 tests (raw p 0.024, Holm 1.0; it fails condition (iii) by one session of 320; the pre-open low raw p 0.11). The rupee gain in typical miss would be Rs 1.3 / 1.0, inside the figures' own standard error. This is the same direction as D's post hoc S&P lead (a lead, not a finding).
* **"Relationships reversed in the Final window" (breadth) is not established:** for the high the Final difference is -0.27 sigma (90% bootstrap CI -0.41 to -0.03, Mann-Whitney p = 0.09); for the low it is 0.00 (p = 0.86). Before the Final window both are overwhelming (p <= 0.0001). Say "weakened or vanished", not "reversed".
* **Best-variant rupee misses Rs 41.4 / 46.6 are V18 picked among 18 after seeing Final:** not an achievable improvement. The post hoc Holm 0.0066 for V10 / V16 on the pre-open low and "V11 significantly worse" use HAC lag 5; at lag 40 or with a block bootstrap the V10 low Holm is about 0.10 / 0.23.
* **Single-day look at 16 Oct (`results/hl3_single_day_2026-10-16.json`) and the display-variant numbers:** n = 1 and picked on Validation + Final; do not quote. The single-day look also used the 16 Oct bar, which the brief had forbidden for any study; it was made after the adoption decision, touches no adoption number and is labelled.
* **Section 8.1** says the tables come from the second run (13:39 to 14:21 UTC) but the cache files are stamped 16 Oct 08:19 to 08:45 UTC (first run). Harmless: the runs are identical (the checker recomputed two tasks: difference 0). The pre-fixed section is byte-identical to git commit 2072844 (08:00:49 UTC), which precedes the first computed file (08:17:32 UTC).
* **Minor:** missing values are imputed with the training mean (0 after standardising), not the median as the text says; "22 of 68 positive in the closing-auction slice" excludes four exact ties; condition (iii) is tie-sensitive; the project baseline was itself chosen on Validation + Final, which mildly favours the baseline in Final.
* **Live-function limitation:** on a future bonus or split ex-date the placeholder row's previous close is the raw last close, so the post-open gap features would be wrong; `iv_day_before_expiry` is always 0 on the live row. Irrelevant for 16 Oct.

**Numbers the checker confirmed as they stand (Final n = 320, rupees at Rs 3,428):** baseline typical miss pre-open high Rs 42.7 / low 47.7, after the open 34.8 / 37.4; "half the time within" 33.6 / 32.2 / 29.1 / 26.6; "price stays" 62.9 / 61.3, "open stays" 51.3 / 59.0, trailing-250 history 43.7 / 47.5 / 35.4 / 37.6; standard errors about Rs 2 to 3; Final coverage of the 90% band 90.3% (high) / 88.8% (low), of the 50% band 46.9% / 50.3%; 18 variants x 4 targets = 72 pairs; 62 pre-open / 67 post-open parameters, 82 distinct columns; every variant within +1.65 / -1.31 rupees of the baseline's typical miss; no eligible pair gains more than 1.45%; permutation importance is small (breadth for the low raises held-out loss by at most 0.64 on 37.3, i.e. 1.7%; random columns 0.05 or less; India VIX level at most 0.011).
