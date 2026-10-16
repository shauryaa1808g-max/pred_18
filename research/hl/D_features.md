# Specialist D: do extra parameters make the day's high and low more precise? (NSE:BSE)

*Status: SECTION 0 (the pre-fixed rule, the feature menu with timestamp rules, the model, and the list of variants) was written BEFORE any variant was evaluated on the real data. Clock when written: Fri 16 Oct 2026 08:18 UTC = 13:48 IST (the brief said "about 11:00 IST"; the machine clock is the one used). The session of 16 Oct is in progress: nothing dated 16 Oct is used anywhere (official history through the 15 Oct close; US data through the 15 Oct US session, which closed at 01:30 IST on 16 Oct). The results sections are appended below Section 0.*

**What had been run before this text was written (disclosed):** the baseline reproduction (Section 0.9, identical to the stored numbers); a timing and sanity run of five variants on sessions 1700 to 1759 (only "finite" and "quantiles ordered" were printed, no loss was looked at); synthetic-data tests of the regression code (a known effect is recovered, pure noise is shrunk); coverage and timestamp spot checks of the feature panel (share of non-missing values, a few dates compared by hand with the source tables). No pinball, coverage or miss of any variant on real data had been seen.

## 0. Pre-fixed section

### 0.1 Question, targets, windows
Does adding information beyond the baseline (src/hl_model.py: S6 volatility x filtered historical simulation) make the forecast of the session HIGH and LOW more precise, for the four targets
* pre-open high Hp = ln(H/P0) and low Lp = ln(L/P0) (information to the previous official close P0), baseline `P_S6`;
* post-open high HO = ln(H/O) and low LO = ln(L/O) (plus the official open O, final 09:08 IST), baseline `W_I6`.

Evaluation sessions: walk-forward, expanding, session 750 onward (25 Feb 2020, as the baseline) to 15 Oct 2026 (n = 1,640). Windows (by target date): Validation 2024-07-01 to 2025-06-30 (n = 248), Final 2025-07-01 to 2026-10-15 (n = 320), Development before 2024-07-01 (n = 1,072, descriptive), post closing-auction slice from 2026-08-03 (n = 52). Rupees: log errors times Rs 3,428 (the 15 Oct close). The baseline is the benchmark; "price stays" and the trailing-250 empirical quantiles (`P_EMP250`, `W_EMP250`) are reported as additional benchmarks.

### 0.2 Adoption rule (verbatim from the brief, with my operational reading)
A variant counts as an improvement for a target ONLY IF ALL hold:
1. **(i)** pinball loss (mean over the 9-level grid 2.5 ... 97.5%) in the Final window is at least 2% lower than the baseline's, with Diebold-Mariano (HAC lag 5, Harvey-Leybourne-Newbold, `src/metrics.py`) two-sided p < 0.05 AFTER Holm across EVERY variant-target pair tried. *Reading:* gain >= 2.0%, DM statistic positive, Holm-adjusted two-sided Final-window p < 0.05, Holm over all **46** pairs of Section 0.5 (the 23 candidate variants x their 2 targets). The two placebo diagnostics are not candidates, are not in the family and cannot be adopted.
2. **(ii)** the Validation window shows the same sign of improvement. *Reading:* the variant's mean pinball in Validation is strictly lower than the baseline's. For the own-window variants (short samples, 0.4) the variant must also have used at least one feature on at least half of the Validation sessions; otherwise (ii) is "not testable" = not met.
3. **(iii)** Final coverage of the 50% and 90% central bands is not worse than the baseline's and Kupiec p > 0.05. *Reading:* for BOTH bands, |coverage - nominal| of the variant <= |coverage - nominal| of the baseline, AND the unconditional-coverage p-value > 0.05. Pre-open targets: nominal 50% / 90% and the Kupiec test of `src/metrics.py`. Post-open targets (HO and LO have an atom at zero because the open is the day's high / low on about 4% / 2% of sessions, so the 5-95% band of HO is not a 90% band): the **atom-at-zero-aware check**, i.e. nominal = the coverage the model's OWN draws assign to the band on each day (P(draws <= q_hi) - P(draws < q_lo)), and a z-test on sum(hits) - sum(nominal) with Poisson-binomial variance; this is also what the "nominal" and "dev" columns report for all targets.
4. **(iv)** in the post-closing-auction slice (2026-08-03 on, n = 52) the pinball loss is not more than 5% worse than the baseline's (ratio <= 1.05).
5. **(v)** a leakage test passes: all input data from the target session onward is replaced by junk (random OHLC for BSE, index, breadth, peers, F&O IV, US and FRED series, expiry and results flags; for post-open variants the target session's own open and previous close are kept because they are legitimately known), the whole pipeline is rerun and the forecasts for the target session must be unchanged (max absolute difference < 1e-9 in log points) for EVERY variant. Sessions tested: spread over Development, Validation, Final and the auction slice, plus the live 16 Oct forecast.

The adoption decision is made separately for each of the four targets. Only a variant that meets all five for a target may replace the baseline for that target. Everything else is reported as a tie, a null or worse. Also reported for every variant: the typical rupee miss of the median (mean absolute error of the 50% quantile at Rs 3,428) and the half-the-time miss.

### 0.3 Feature menu and timestamp rule of every feature (each is known before the t open at 09:00 IST unless marked)
Dates are IST sessions; "t-1" = the previous BSE session. A table dated t-1 is read at exactly that date (a missing t-1 row makes the feature missing, never stale). All rolling windows end at t-1. Full per-feature table with first valid date and counts: `results/hl2_feature_timestamps.csv` (written by the run); the panel itself: `results/hl2_features_panel.csv.gz`.

| block | features (scale model) | timestamp rule |
|---|---|---|
| **a** implied / VIX | ln India VIX, ln change of VIX, VIX-minus-realised-vol spread (ln(VIX/100/sqrt 252) - ln Nifty 10-session daily vol) | India VIX close of t-1 (value fixed at 15:30 IST t-1) |
| **b** US overnight | abs S&P 500 return, ln US VIX, ln change US VIX, abs change USD/INR, abs Brent, abs dollar index, abs US 10y change | last observation dated STRICTLY BEFORE the IST date of t. S&P 500 (closes 01:30 IST) and US VIX (01:45 IST): the closing fact is public before the IST open, lag zero. USD/INR: ECB reference rate (fixed 14:15 CET, posted 16:00 CET), lag zero; **the repo's `usdinr_ecb_2017_2026.json` is an HTML error page, so the series is rebuilt from Frankfurter/ECB (`results/hl2_data_usdinr_ecb.csv`)**. Brent (EIA), broad dollar index (weekly Fed release), US 10y (H.15, next day): FRED publication lag is NOT provably zero, so the value is shifted ONE MORE observation back; an observation older than 9 days (6 days for the zero-lag series) is treated as missing. |
| **c** Indian market / peers | Nifty 50 ln range and abs return, Bank Nifty ln range, share of names with abs return >= 5%, abs(advance share - 0.5), median of peers' ln range relative to each peer's own 60-session mean (CDSL MCX ANGELONE CAMS IEX KFINTECH NUVAMA MOTILALOFS ANANDRATHI, >= 3 listed), z-score of ln total turnover | index file / bhavcopy of t-1 (index file posted ~23:20 IST t-1, bhavcopy ~16:34 IST t-1) |
| **d** BSE own / microstructure | ln ln(H/L) of t-1, abs gap of t-1, z-score (60 sessions) of ln turnover and of delivery %, ln Parkinson vol (10 and 20 sessions) minus ln sigma_S6,t, distance of the adjusted close from the 250-session high and low | BSE official bars of t-1 (bhavcopy ~16:34 IST; delivery file ~18:00 IST). Prices are bonus-adjusted through the log-return chain (only `prev` in the processed file is adjusted; OHLC levels are raw traded prices) |
| **e** calendar | Tue/Wed/Thu/Fri dummies (Monday is the reference), one of the last two weekdays of the month, previous session >= 4 calendar days earlier | exchange calendar, known in advance |
| **s** SHORT samples | ln ATM implied vol of BSE options, put-minus-call IV skew, IV-minus-realised-vol (BSE 20 sessions), F&O expiry-day flag, results-next-session flag, ln range of the Nifty Capital Markets index | IV: NSE F&O settlement prices of t-1 (bhavcopy ~17:00 IST), **data only from 2024-11-29 (462 sessions)**; expiry dates read from the contract rows in `data/raw/fo_bse` (from 2024-11-18); results flag from `data/results_dates.csv` (7 events, from 2024-11-13); Capital Markets index high/low exist from 2024-11-11. **Tested only on its own window and labelled so.** |
| **o** post-open (09:08 IST) | abs gap in sigma units |G_t|/sigma_S6,t (capped 4), open beyond yesterday's high or low, abs distance of the open from the middle of yesterday's range | official open O_t (NSE pre-open auction, final 09:08 IST), sigma_S6,t and yesterday's bar |

Signed features for the **location** model (shift of the median of H and L): b: signed S&P 500 return, USD/INR change, US VIX change, Brent / dollar / US10y changes (same lag rules); c: Nifty and Bank Nifty returns of t-1, advance share - 0.5, median peer return (each clipped +-15%), ln change of VIX; d: BSE returns of t-1 / 5 / 20 sessions, close location in the range, distance from the 250-session high / low, up-down streak (capped +-5), BSE minus Nifty; e: the calendar dummies; o: signed gap in sigma units, position of the open in yesterday's range, +1/-1/0 for open beyond yesterday's high/low.

**Count of features searched: 58 distinct a-priori features (40 in the scale models, 28 in the location models, 10 in both), in 7 blocks, entering 23 candidate variants.** Menu items NOT entered, and why: GIFT Nifty, NSE pre-open order book (2 snapshots only), FII/DII flows (no dated series in `data/`): untested. Volume z-score (collinear with the turnover z-score, so not entered separately), 5-day Parkinson/Garman-Klass and 1-5-22 day realised variance (already inside the baseline's HAR term: only the 10/20-day Parkinson vol RELATIVE to the baseline sigma enters), Capital Markets index return (only its range, from 2024-11), individual peers (only the median). The 13-15 Oct 2026 rows missing from the repo's processed index, breadth, peers, IV, delivery and US files were filled from NSE archives, local UDiFF files, Yahoo (S&P 500, US VIX) and Frankfurter/ECB (`results/hl2_fill_*.csv`, rebuilt by `--refresh-fill`). **Live 16 Oct caveat:** the FRED files end 6 Oct (Brent), 2 Oct (dollar index), 8 Oct (US 10y), so those three features are missing (= zero effect) in the 16 Oct forecast; they exist for all backtest sessions.

### 0.4 Model (identical machinery for every variant; "no features" reproduces the baseline exactly)
* **Scale.** sigma'_t = sigma_S6,t x exp(clip(z_t' gamma, -1, 1)), z = standardised features (winsorised at the 1st / 99th percentile of the training rows, 0/1 columns not winsorised, missing = 0 = training mean; a column needs >= 120 non-missing training rows). gamma from a log-link (Poisson pseudo-ML) ridge regression of the ratio r_s = y_s / sigma_S6,s on z_s, intercept unpenalised: min mean[exp(a + z'g) - r (a + z'g)] + (lambda/2)|g|^2. The baseline's own GARCH and HAR terms are in the offset sigma_S6, so the regression measures the INCREMENTAL effect of the features. y = max(Hp,0) + max(-Lp,0) (pre-open, range of the path P0 -> day) or HO - LO = ln(H/L) (post-open) for the symmetric variants; the tail-specific variants (`TS`) regress the high side (max(Hp,0) or HO) and the low side (max(-Lp,0) or -LO) separately (each with its own ridge strength). (The log-link mean regression is used instead of OLS on ln y because the one-sided excursions can be exactly zero.)
* **Ridge strength.** lambda in {0.01, 0.03, 0.1, 0.3, 1, 3, 10, infinity}; infinity = no features = baseline. Chosen by forward-chaining CV inside the training rows (train on the first 50%, 62.5%, 75%, 87.5% of the rows, validate on the next 12.5%; features standardised inside each fold; pooled Poisson loss; ties go to stronger shrinkage), re-selected every 5th refit (every 100 sessions), coefficients refitted every 20 sessions on sessions strictly before the block (first refit at session 640; the baseline's sigma exists from session 500).
* **Location.** The same walk-forward ridge, but ordinary least squares on the winsorised standardised residual u_s = V_s / sigma'_s of H and of L (separately), ridge strength by the same forward-chaining CV on squared error (infinity = no shift). The quantiles are those of sigma'_t x (e_s + shift_t) where e_s = u_s - shift_s are the shift-corrected residuals of the trailing 500 sessions; post-open draws are clipped at HO >= 0 and LO <= 0 before the quantiles are taken.
* **Quantiles.** The baseline's filtered historical simulation: trailing 500 sessions of V_s / sigma'_s (the current block's multiplier applied to all pool rows), times sigma'_t. Baseline sigma_S6 is the project's own (src/models.py) for the close-to-close return R (pre-open) and for the open-to-close return I with Garman-Klass (post-open).
* **Live forecast.** `hl2_forecast(date, open_price)` refits the regressions at the forecast session (one step fresher than the evaluated blocks, as `hl_model.hl_forecast` does) and, for any target where no variant was adopted, returns the baseline numbers.

### 0.5 Variants (23 candidates = 46 variant-target pairs = the Holm family; all tried, all reported)
| pre-open (baseline `P_S6`; targets H, L) | features |
|---|---|
| `P_SC_a`, `P_SC_b`, `P_SC_c`, `P_SC_d`, `P_SC_e` | symmetric scale from block a / b / c / d / e alone |
| `P_SC_f` | symmetric scale, all of a + b + c + d + e (ridge) |
| `P_SC_s` | block s alone, own window (from the first refit with >= 120 rows of the IV features, about May 2025) |
| `P_SC_fs` | all of a + b + c + d + e + s, own window |
| `P_TS_f` | tail-specific scale (separate high-side and low-side regressions), all of a to e |
| `P_LO_f` | location only, all signed features (b, c, d, e) |
| `P_SL_f` | scale (a to e) + location (b, c, d, e) |

| post-open (baseline `W_I6`; targets HO, LO) | features |
|---|---|
| `W_SC_a` ... `W_SC_e` | symmetric scale from block a / b / c / d / e alone (5 variants) |
| `W_SC_o` | post-open block alone |
| `W_SC_fo` | all of a to e + o |
| `W_SC_s`, `W_SC_fso` | block s alone / a to e + s + o, own window |
| `W_TS_fo` | tail-specific scale, a to e + o |
| `W_LO_fo` | location only, b to e + o |
| `W_SL_fo` | scale (a to e + o) + location (b to e + o) |

Diagnostics, NOT candidates, not in the family, cannot be adopted: `P_PLACEBO`, `W_PLACEBO` = ten N(0,1) columns (fixed seed 20261016) through the identical symmetric-scale machinery (what the ridge + CV pipeline does on pure noise).

### 0.6 Rules for the report
Every variant x target x window is reported (n beside it). Tested results (DM, Holm, adoption) are labelled tested; coefficient tables, correlations, by-year tables and anything else are labelled descriptive and cannot lead to adoption. If a variant is added after the first results it is labelled post hoc and the family size reported with it is increased. A result that contradicts a project claim is flagged explicitly. Feature selection happens only inside the walk-forward (the CV picks the ridge strength; the blocks and features were fixed here, a priori, not chosen on the Final window).

### 0.7 What counts as a null
A variant is a **tie** if its pinball gain is positive but the rule is not met, **worse** if the baseline is better, and a **null** for a block if all its variants are ties or worse. A block that helps in the own-window comparison but cannot meet (ii) is reported as "own-window result, not adoptable".

### 0.8 Reproduction commands
See the last section of this file.

### 0.9 Baseline reproduction (run before any variant; `results/hl2_baseline_repro.csv`)
The engine with no features reproduces `hl_model.build()` quantiles to 0.0 (max absolute difference, 1,640 sessions, pre- and post-open) and the stored Final-window numbers exactly: pre-open P_S6 pinball x1e4 31.15 (high) / 36.58 (low), typical miss Rs 42.7 / 47.7 (Rs 42.69 / 47.67), 90% coverage 90.3% / 88.8%; post-open W_I6 pinball 23.85 / 28.03, typical miss Rs 34.8 / 37.4. (n = 320.)

