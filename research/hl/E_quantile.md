# Specialist E: flexible (quantile-regression, boosting, forest, conformal, stacked) models for the day's HIGH and LOW of NSE:BSE

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
