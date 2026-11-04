# Independent verification of specialist G (comparable past days: "watch the past to shape the future")

Verifier report on `research/hl/G_analogue.md`, `src/hl_analog.py` and `results/hl5_*` (the 16 Oct 2026 JSON and CSVs included).
Written Sun 18 Oct 2026 by the sandbox clock; the brief's "now" is Fri 16 Oct 2026 about 11:00 IST. I did not edit any file except this one; every run that writes files was done in an isolated copy in the scratchpad (`.../scratchpad/verG2/copyA`, `copyB`, `copyC`, `copyB2`).

**Data cut, stated first.** `data/processed/bse_daily_extra.csv` already holds a row dated 16 Oct 2026. I read none of its values into any number below: every loader of mine drops dates on or after 2026-10-16 (assertion: last session 2026-10-15, 2,390 sessions), and in the isolation test (Section 5.3) that row, and everything dated after it, was replaced by junk. The only 16 Oct input anywhere is the official open Rs 3,450.0 that the lead passed in.

## 0. Verdict

**Pass with fixes needed. Severity: minor.** Every headline number I tested reproduces from the raw data files with my own code, to rounding or better (most to 1e-14). I found no look-ahead and no arithmetic error in the part of the study that decides the adoption question. The null result is real: **none of the four targets meets the pre-fixed adoption rule; condition (i) (at least 2% lower pinball loss) fails for all 172 variant-target pairs, the best being +0.78%.** The fixes needed are: (a) one secondary diagnostic (the ridge out-of-sample R-squared) is computed in mismatched units, so its quoted range "-0.07 to +0.03" is wrong (the correct range is about -0.02 to +0.02, depending on units; the conclusion "essentially no linear information" survives and is, if anything, stronger); (b) four sentences claim a little more than the numbers support (Section 6); (c) a design fragility in how late-ending macro files are handled (it can fake a "leak" in a leakage test and silently changes the feature set on Mondays in live use; it does not touch the display variant or any tested number); (d) several items on the user's feature menu are untested, which the report says, with reasons.

Plain-words summary of what the evidence supports (all of it the builder's own result, which I confirmed and extended):
* Matching today to comparable past days did not make the day's high or low more precise. In the 320 out-of-sample sessions of the Final window (1 Jul 2025 to 15 Oct 2026), the typical miss of the median stays between Rs 41.8 and 44.0 (pre-open high; baseline 42.7), 47.2 and 49.3 (low; baseline 47.7), 34.2 and 35.7 (high once the open is known; baseline 34.8) and 37.2 and 39.4 (low once the open is known; baseline 37.4), over all 43 variants.
* Analogue-alone versions are mostly worse than the baseline, partly because 80 neighbours are a smaller and older sample than the baseline's last 500 days. I tested that explanation with an extra probe the builder did not run (Section 7.1): re-weighting the baseline's own 500-day window by similarity gives at most +0.71% (pre-open low) and nothing is significant after Holm (smallest Holm p 0.35, family of 32). So the null does not depend on the "only 80 days" noise price.
* For 16 Oct the comparable-days and baseline medians differ by Rs 14 / 11 / 5 / 2 (pre-open high / low, after-open high / low), far less than the typical miss of Rs 35 to 48; nothing changes in practice.
* The list of "most similar days" is not a forecast and not stable: the five nearest days change from 2026-10-06, 2026-04-07, 2026-08-25, 2021-04-23, 2024-08-19 to 2021-04-23, 2024-08-19, 2023-06-13, 2026-03-17, 2020-09-15 when one missing input (delivery %) is filled, and the 80 nearest days are on median only about 27 separate episodes (Section 7.2).

## 1. What I checked and how

My code is in `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/verG2/`.

**Independence limit, stated plainly.** (1) The S6 volatility model is the project's own specification; I used `scratchpad/verA/indep.py`, a second typing of that specification by an earlier verifier (it matched the project's stored sigma to 1e-14 there), not the builder's code; my sigma path equals the builder's to 4e-16. (2) I read `src/hl_analog.py` before typing my own features and engine, so my code shares the builder's reading of the pre-fixed text (Section 0 of `G_analogue.md`); what it independently checks is that the code does what that text says, and that nothing in the text looks ahead. (3) I did not re-derive S6 from scratch.

| step | what I did | result |
|---|---|---|
| A. data cut | own loader: `bse_daily.csv` + extra bars, dates < 2026-10-16 | 2,390 sessions, last 2026-10-15 |
| B. baseline | S6 sigma (verA library) -> trailing-500 filtered historical simulation for all 1,640 evaluation sessions | max difference to the project's stored `hl_eval_predictions.csv`: 1.8e-12 rupees; next-session sigma 2.4348% (close-to-close), 2.2159% (open-to-close), as in the builder's JSON |
| C. features | typed all 43 features (38 pre-open + 5 post-open) from the pre-fixed timestamp rules | against the builder's matrix, sessions 500 to 2389: max absolute difference 3.6e-15 over every column, NaN pattern identical in all 43 columns |
| D. analogue engine | typed the walk-forward engine (blocks of 20 from session 750, standardisation, shrunk Mahalanobis or ridge-weighted distance, k40 / k80 / k160 / Gaussian kernel, blend weights, RAND80, POOL) | all 86 variant arrays (43 per phase) x 1,640 sessions x 2 targets x 9 quantiles equal the builder's: max difference 1.1e-14, 0 sessions differing |
| E. metrics and rule | pinball, DM (Newey-West lag 5, Harvey-Leybourne-Newbold; verA's independent `nw_dm`), Holm over the 172 pairs, Kupiec, atom-aware tail check for HO, validation sign, auction slice | gains, p-values, Holm, miss, c1 to c4 flags: max difference 3e-14, flags identical for all 172 pairs |
| F. text against numbers | parsed the 688 cells of the Section 3.3 variant tables and the 24 rows of Section 3.4 and compared with my numbers | 0 mismatches |
| G. secondary analyses | S1 (spaces against the volatility-only control), S2 (median of the 5 nearest), S4 (against random draws), by-year gains, power numbers, confidence intervals | all reproduce; S3 (ridge R-squared) does not (defect 1) |
| H. live day | own live-row code for 16 Oct (bars to 15 Oct, open 3,450.0) | nearest days for spaces V, A, B, C (pre- and after-open) and the 80-nearest and baseline quantiles equal the builder's JSON; the fill sensitivity also reproduces |
| I. leakage | own junk and own sessions (Section 5) | passed; positive controls move |
| J. byte reproducibility | re-ran `--eval`, `--adopt`, `--live`, `--leak`, `--check`, `--selfcheck` of the builder in an isolated copy | 15 `hl5_*` evaluation files, `hl5_adoption.csv`, `hl5_leakage.csv`, `hl5_live_checks.csv`, `hl5_selfchecks.csv`, `hl5_2026-10-16.json` and `_analogues.csv` byte-identical to the repo |
| K. pre-fixed text | `git show 2072844`; Section 0 compared with the final report | identical; both sha256 values quoted in the report reproduce (Section 6, items 10 and 11) |
| L. data alignment | correlation of BSE returns with the index, VIX, breadth and peer series at lag -1, 0, +1 sessions | all aligned on the same date (Section 3) |

## 2. Headline numbers recomputed (builder against mine; Final window n = 320 unless stated)

| claim | builder | mine | difference |
|---|---|---|---|
| sessions: Final / Validation / auction slice | 320 / 248 / 52 | 320 / 248 / 52 | 0 |
| baseline pinball x1e4: pre-open H / L; after-open HO / LO | 31.1516 / 36.5788; 23.8531 / 28.0298 | 31.1516 / 36.5788; 23.8531 / 28.0298 | < 1e-4 |
| baseline typical miss of the median, Rs at 3,428 | 42.7 / 47.7; 34.8 / 37.4 | 42.69 / 47.67; 34.81 / 37.42 | 0 |
| half the time within, Rs | 33.6 / 32.2; 29.1 / 26.6 | 33.6 / 32.2; 29.1 / 26.6 | 0 |
| "price stays" / "open stays" miss, Rs | 62.9 / 61.3; 51.3 / 59.0 | 62.87 / 61.30; 51.25 / 58.96 | 0 |
| trailing-250 empirical, pinball x1e4: H / L / HO / LO | 32.739 / 36.587 / 25.009 / 28.053 | same | 0 |
| coverage, baseline 90% band (H / L / HO / LO) | 0.903 / 0.887 / 0.950 / 0.894 | 0.9031 (289 of 320) / 0.8875 / 0.9500 / 0.8938 | 0 |
| coverage, baseline 50% band | 0.469 / 0.503 / 0.494 / 0.503 | 0.4688 / 0.5031 / 0.4938 / 0.5031 | 0 |
| display variant B (80 nearest) alone: pinball gain; typical miss Rs | -5.0 / -1.4 / -3.1 / -2.1 %; 43.4 / 47.6 / 34.4 / 37.5 | -5.02 / -1.37 / -3.15 / -2.13 %; 43.40 / 47.62 / 34.43 / 37.48 | 0 |
| display variant B blended: gain; miss Rs | -1.4 / -0.1 / -1.1 / -0.5 %; 42.8 / 47.4 / 34.5 / 37.2 | -1.38 / -0.11 / -1.09 / -0.54 %; 42.83 / 47.44 / 34.53 / 37.24 | 0 |
| DM p-value, display B alone, pre-open high (gain -5.02%) | not quoted | raw two-sided p 0.0008, Holm over 172: 0.107 | (new) |
| 90% coverage of the same variant, pre-open high | 0.884 | 0.8844 (283 of 320) against 0.9031 for the baseline | 0 |
| best Final gain of any of the 43 variants: H / L / HO / LO | +0.02 (C_k40_b) / +0.78 (A_k40_b) / +0.41 (C_k40_b) / +0.39 (V_ker_b) % | +0.018 / +0.779 / +0.412 / +0.390 %, same variants; Holm p 1.000 for all four | 0 |
| variants significantly worse than baseline (Holm < 0.05): H / L / HO / LO | 16 / 0 / 15 / 1 | 16 / 0 / 15 / 1 | 0 |
| validation sign (c2) holds for | 22 / 35 / 28 / 26 of 43 | 22 / 35 / 28 / 26 | 0 |
| calibration (c3) holds for | 6 / 3 / 0 / 3 | 6 / 3 / 0 / 3 | 0 |
| auction slice (c4) holds for | 30 / 40 / 30 / 37 | 30 / 40 / 30 / 37 | 0 |
| range of the typical miss over all 43 variants (Rs): H, L, HO, LO | 41.8-44.0, 47.2-49.3, 34.2-35.7, 37.2-39.4 | 41.8 (A_k40_a) to 44.0 (V_k40_a); 47.2 (B_k40_b) to 49.3 (L_k40_a); 34.2 (B_k40_a) to 35.7 (L_k40_a); 37.2 (V_k160_b) to 39.4 (A_k40_a) | 0 |
| median of the 5 nearest days, typical miss Rs (se): H / L / HO / LO | 46.2 / 51.9 / 40.5 / 41.9 | 46.2 (2.4) / 51.9 (2.8) / 40.5 (2.3) / 41.9 (2.6), ratios 1.083 / 1.088 / 1.164 / 1.120 | 0 |
| S1: 4 of 32 raw p < 0.05, 0 after Holm; set C against V, pre-open high | +4.5%, raw p 0.003, Holm 0.08 | 4 and 0; +4.45%, p 0.0025, Holm 0.0805 | 0 |
| power: Holm critical z; median standard error of a gain (pts) | 3.62; 0.63 / 0.83 / 0.83 / 0.64 | 3.623; 0.632 / 0.832 / 0.828 / 0.640 | 0 |
| 95% interval of the blended display gain, pts | -2.96 to 0.20 / -1.74 to 1.52 / -3.31 to 1.14 / -1.86 to 0.78 | same | 0 |
| 16 Oct: five nearest days, set B, before the open | 2026-10-06, 2026-04-07, 2026-08-25, 2021-04-23, 2024-08-19 | the same five, same order, same distances (1.488, 1.579, 1.632, 1.651, 1.668); pool 1,885, 13 of 14 features (delz missing) | 0 |
| 16 Oct: five nearest after the open | 2026-10-06, 2026-03-17, 2024-11-06, 2026-09-15, 2026-03-18 | the same | 0 |
| 16 Oct: 80-nearest (B) medians, Rs: pre-open H / L; after-open H / L | 3,489 / 3,401; 3,483 / 3,412 | 3,489.33 / 3,400.75; 3,483.29 / 3,411.87 | 0 |
| 16 Oct: baseline medians (and 5%-95% bands) | 3,475 (3,421-3,591), 3,390 (3,269-3,450); 3,488, 3,410 | 3,475.01 (3,421.15-3,590.57), 3,390.07 (3,268.73-3,449.85); 3,488.48, 3,409.87 | 0 |
| fill sensitivity: five nearest, set B, with delivery % filled | 2021-04-23, 2024-08-19, 2023-06-13, 2026-03-17, 2020-09-15; 80-nearest medians 3,487 / 3,405 | same five; 3,486.7 / 3,405.1 | 0 |
| ridge out-of-sample R-squared (S3), range | -0.070 to +0.032 | **-0.023 to +0.008 in standardised units, -0.018 to +0.021 in raw units** | **does not match** (defect 1) |

## 3. Code review for look-ahead and arithmetic (`src/hl_analog.py`, all 1,186 lines read against `hl_model.py`, `common.py`, `metrics.py`)

No look-ahead found. Timestamps, for the forecast of session t (row t of the feature matrix):

* **Features.** Every bar-based and market feature of row t is read from row t-1 through `Lg()` (line 202: `np.r_[nan, a][:N]`); calendar items come from the target date itself. I re-typed all 43 from the pre-fixed rules and got the builder's matrix to 3.6e-15 (Section 1, C). Delivery % of day j is a post-close bhavcopy item (fine for the next pre-open).
* **Volatility.** `lnsig_rel`, `rng1`, `gap1`, `r5`, `r20`, `pk5`, `gk20`, `dhi`, `dlo` divide by or subtract `sig[t]`, the baseline's S6 sigma of session t, which the baseline itself knows at the pre-open (parameters fitted before the sigma block that contains t).
* **Index, VIX, breadth, peers files are aligned with the BSE dates, not shifted.** Correlation of the BSE daily return with the series of the previous / same / next session: Nifty 50 +0.06 / **+0.35** / -0.00; Bank Nifty +0.04 / **+0.32** / -0.01; India VIX change -0.05 / **-0.28** / -0.00; advance share +0.09 / **+0.43** / +0.07; CDSL +0.09 / **+0.48** / +0.10; MCX +0.07 / +0.39 / +0.05. A one-day shift of a file would have been a leak that the junk test cannot catch (junk replaces rows by date label only); this check rules it out. The row of date j is used only for target j+1.
* **US and slow macro.** Last observation dated on or before the target date minus 2 days (S&P 500, US VIX), 6 (US 10-year), 8 (Brent), 12 (dollar index, USDINR). The freshest US session is discarded on purpose, so a FRED posting lag of up to a day is covered. My leakage battery changes the observation dated D-1 (no effect on any variant, 10 of 10 sessions) and the observation dated D-2 (moves the C and L variants, 3 of 10 sessions; the other sessions have no observation dated D-2 because it is a weekend, or the file ends before it).
* **Neighbour search.** Line 279: `elig[POOL_FIRST:max(POOL_FIRST, t - EXCL)] = True` gives sessions 500 to t-6 inclusive: strictly earlier than the target and with the last five sessions excluded, as the text says. The features of neighbours and target still share trailing windows (r20, volz, dhi and dlo are 20 to 250 days long); that is overlap of past information, not a leak, but it makes neighbours cluster in time (Section 7.2).
* **Fitted quantities use only earlier data.** Standardisation, correlation matrix and ridge weights are fitted on sessions 500 to b0-1 where b0 is the start of the 20-session block that contains t (line 264: `okf[b0:] = False`). The kernel bandwidth uses distances only. Blend weights are the argmin over the trailing 500 scored sessions before the block (lines 325 to 330; weights 0.5 until 120 are scored). The sets, k grid and the display variant are in the text committed before any result (Section 6, item 10); none is chosen on the Final window.
* **Arithmetic.** DM (Newey-West lag 5 with Bartlett weights, Harvey-Leybourne-Newbold factor sqrt((n-1)/n), t with n-1 degrees of freedom), Holm, Kupiec and the atom-aware tail check agree with verA's independently typed versions to 1e-14. The family for Holm is the 172 pairs of one window (line 436). The sign convention (positive gain = variant better) is right. No off-by-one found (sessions 500..t-6; the block-start slice `lo:e` of the blend uses scored sessions strictly before the block).
* **Block offset (harmless, explains a live-versus-replay difference).** The analogue blocks start at 750 + 20m, the sigma blocks at 500 + 20m, so they are offset by 10 sessions. A live call at a block start therefore re-fits sigma 10 sessions fresher than the walk-forward row. For one-feature matching (set V, k40) this flips which 40 days are nearest: I re-ran seven block starts (`trunc_test.py`): median difference over the 86 arrays 1e-5 to 9e-3 log units, but up to 0.079 for `V_k40_a` at one session (2024-08-09), 0.066 for `B_k40_a` after the open at another (2020-03-25); blend weights identical. The builder's `hl5_live_checks.csv` figures (median Rs 0.11, 95th percentile Rs 3.0, largest Rs 47.7 over 200 values) reproduce. This is a property of one-feature nearest-neighbour matching, not a leak.
* **Fragility: the "never stale" guard in `lookup()` (lines 180 to 185).** A macro feature is set to missing when the derived series' last non-missing date plus the lag is before the target date. This makes forecasts depend on the end date of a file, not only on its content. Consequences, verified: (i) a leakage test whose junk contains negative or missing values makes the derived series end early and turns the S&P and US VIX features of C and L into missing; an earlier scratch verifier saw 3.4e-2 at session 1650 (a Monday) in exactly this way (`bisect_leak3.py` re-run on the current code: "only macro 3.36e-02", X row differs only in `sp_r1` finite -> NaN). With positive junk of the same date range, and with my "extreme" junk, session 1650 shows 0.0. It is an artifact of the guard, not information from the future. (ii) In live use on a Monday the S&P 500 and US VIX features are dropped even when the file is up to date (Friday + 2 days is Sunday, before Monday): I confirmed it for 1 Dec 2025 (dropped `sp_r1`, `usvix_ln`, `usvix_d1`), not for Tuesday 2 Dec or Thursday 4 Dec. The walk-forward used them on Mondays, so on Mondays the C and L sets differ between the tested and the live version. The display variant (B) and 16 Oct (a Friday, macro files end 12 Oct) are unaffected.
* **Secondary diagnostic S3 has a unit error** (`eval_tables`, `s3` block): `ridge_pred` is a prediction of the standardised outcome `U` (units of sigma), while `Y = names[ph][3]` is the raw log outcome. See defect 1.
* **`--selfcheck` is not independent** (same author, same specification, same file), but its 764 comparisons agree with my independent re-typing.

## 4. The pre-fixed adoption rule, applied by me (Final window n = 320; Validation n = 248; auction slice n = 52; family 172)

Rule: (i) pinball gain >= 2% in Final and Holm-adjusted DM p < 0.05 over all 172 pairs; (ii) Validation gain > 0; (iii) Final 50% and 90% coverage no further from nominal than the baseline's and Kupiec p > 0.05 (HO: tail share above q95 no further from 5% than the baseline's, binomial p > 0.05); (iv) auction-slice pinball <= 1.05 x baseline; (v) leakage test passed.

| target | pairs | best Final gain (variant) | its Holm p | pairs with gain > 0 | pairs with gain >= 2% | (i) | (ii) | (iii) | (iv) | (v) | met |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pre-open high | 43 | +0.018% (C_k40_b) | 1.000 | 1 | 0 | 0 | 22 | 6 | 30 | pass | **no** |
| pre-open low | 43 | +0.779% (A_k40_b) | 1.000 | 23 | 0 | 0 | 35 | 3 | 40 | pass | **no** |
| after-open high | 43 | +0.412% (C_k40_b) | 1.000 | 1 | 0 | 0 | 28 | 0 | 30 | pass | **no** |
| after-open low | 43 | +0.390% (V_ker_b) | 1.000 | 10 | 0 | 0 | 26 | 3 | 37 | pass | **no** |

Condition (i) alone excludes everything, so the verdict does not depend on how the family is counted: no pair reaches +1%, only 3 pairs reach +0.5%, and no positive-gain pair has an unadjusted p below 0.05 except three pre-open-low pairs (POOL_a +0.36%, p 0.041; B_ker_a and B_ker_b +0.39%, p 0.045), against 71 of 172 pairs that are significantly worse before any correction (172 x 0.05 = 8.6 expected by chance for both signs). Condition (iii) for the after-open high is an artifact of the rule: the baseline itself puts only 2.5% (8 of 320) of outcomes above its 95% quantile (binomial p 0.039), so no variant can pass; the builder says so. Condition (v): the builder's leakage test passed (8 sessions, all 43 variants and the baseline) and so did mine (Section 5).

**Adopted: none, for any of the four targets.** The baseline in `src/hl_model.py` stays the headline.

## 5. Leakage and isolation tests (mine)

### 5.1 My own battery (my junk, my sessions, my pipeline)
For each session k: build a copy of every data file in which everything dated on or after the session's date is replaced by junk (bars keep the target's own open and previous close; index, breadth, peers, and macro observations dated from the day before), recompute sigma, features and all 86 variant arrays, and compare row k (and every earlier row) with the clean run. Sessions: 800 (13 May 2020), 1303 (Mon 23 May 2022), 1650 (Mon 16 Oct 2023), 1990 (Mon 3 Mar 2025), 2054 (Mon 9 Jun 2025), 2200 (8 Jan 2026), 2300, 2349 (18 Aug 2026), 2380 (1 Oct 2026), 2389 (15 Oct 2026). None coincides with the builder's eight.

| test | sessions | variants changed (of 43 per phase) | max change in row k, log units | max change in any earlier row |
|---|---|---|---|---|
| junk, positive values (log-normal around the file median) | 10 | 0 | 0.0 | 0.0 |
| junk, extreme values (table values about 100 x the median or more; bar log-moves with standard deviation 0.5 to 0.8) | 10 | 0 | 0.0 | 0.0 |
| junk as missing values (only session 2389 can be run: later blocks cannot be fitted on missing returns) | 1 | 0 | 0.0 | 0.0 |
| positive control: session k-1 distorted (bar, volume, index, breadth and peer rows) | 10 | 43 and 43 | 0.045 to 0.156 | 0.0 |
| positive control: the macro observation dated D-1 changed | 10 | 0 | 0.0 | 0.0 |
| positive control: the macro observation dated D-2 changed | 10 | 10 to 16 on the 3 sessions where D-2 is a trading day with data (C and L spaces); 0 elsewhere | up to 0.048 | 0.0 |

### 5.2 The 3.4e-2 an earlier scratch verifier saw at session 1650
Explained in Section 3 (fragility of `lookup()`): junk containing negative values made the derived macro series end early, the guard then set `sp_r1` and the US VIX features to missing, so the C and L variants moved. My positive and extreme junk give 0.0 at session 1650.

### 5.3 The importable forecast for 16 Oct, with and without junk after the cutoff
`analog_forecast('2026-10-16', 3450.0)` and `hl_model.hl_forecast('2026-10-16', 3450.0)` run in four isolated copies, outputs compared as JSON:

| copy | what is different from the repo | result |
|---|---|---|
| A | nothing | the fresh JSON equals `results/hl5_2026-10-16.json` except the `adoption_status` text key; baseline equals `hl_forecast` to the cent (bars used sha256 53c6203c...) |
| B | bars from 16 Oct on replaced and extended by junk, index / breadth / peers rows from 16 Oct junk, macro observations from 15 Oct junk | display variant (space B), all `variants`, baseline: identical. Only the C and L sets differ (7 macro features come back with their old 12 Oct values instead of missing, because the file now "ends" later: the guard of Section 3) |
| B2 | same as B with different junk values | identical to B: the junk values are not used |
| C | as B but the macro rows dated from 15 Oct exist with empty values | identical to A in every key |

So the forecast uses nothing dated after the 15 Oct close except the opening price passed in. The data files it reads end 12 Oct (index, VIX, S&P 500, US VIX), 13 Oct (breadth, peers), 2 to 8 Oct (slow macro), 15 Oct (bars). Everything it reads was written before the 15 Oct 22:00 IST cutoff (the 15 Oct bar was the NSE bhavcopy of that evening). The fill files `results/hl2_fill_*.csv` are used only by `--live-filled` (sensitivity); they were retrieved on 16 Oct 08:12 UTC but contain observations dated up to 15 Oct, and the US values still go through the two-day lag rule.

### 5.4 Byte reproducibility
Builder commands re-run in the isolated copy `copyA`: `--eval` (40 s), `--adopt`, `--live`, `--leak` (340 s, PASSED), `--check` (about 2 min) and `--selfcheck` (49 s, 0 mismatches in checks A, B, C): every file they write, `hl5_leakage.csv`, `hl5_live_checks.csv` and `hl5_selfchecks.csv` included, is byte-identical (sha256 / `cmp`) to the file in the repo. Not re-run: `--tables` (it only reformats the files above) and `--live-filled` (its numbers I re-derived with my own code, Section 7.3).

## 6. Sentences checked: what overclaims, selection, small samples, contradictions

Sentences that are correct as written (numbers reproduce, strength of wording fits): the Final-window benchmark table; "0 of 172 meet the pre-fixed rule"; the counts of variants significantly worse; the median-of-5 comparison; the S1 result "0 of 32 after Holm" and the statement that set C against V is "suggestive, not established, and does not reach the baseline"; the noise-price and POOL control numbers; the by-year table (labelled post hoc); the fragility of the nearest-five list (reproduced independently); the removal of the unsupported JSON sentence; the disclosure of the 38 / 43 feature count correction and of the delivery-% gap.

Sentences that need correcting or softening:

1. **S3 / "numbers to quote" item 6 and the headline block: "ridge out-of-sample R-squared -0.07 to +0.03".** Wrong units (defect 1). Correct: Final n = 318, pre-open high / low -0.002 / -0.023, after-open high / low +0.008 / -0.010 (standardised outcome); Validation+Final n = 566: +0.002 / +0.008 and +0.004 / -0.004. Raw-outcome units: -0.018 to +0.021. Conclusion "essentially no linear information" holds.
2. **Section 3.6 and the headline block: "only a true gain of about 2.3% to 3.0% or more could have been confirmed".** 2.3% to 3.0% is the gain whose point estimate would just reach the Holm threshold, i.e. about 50% power. At 80% power the gains are about 2.8% / 3.7% / 3.7% / 2.9% (H / L / HO / LO). Reword: "a true gain below about 2.3% to 3.0% would usually have gone undetected; the point estimates are about zero or negative". The sentence that follows (a gain above 1.5% is excluded for the blended display variant) is right for that one variant, unadjusted 95% intervals.
3. **Section 5.1: "The five days are as spread out as the whole history".** No number supports "as spread out": the five days' highs range from -0.16% to +3.94% (width 4.1 points) against -0.18% to +6.80% (width 7.0) for the middle 90% of the 1,885 days. Five points cannot show a spread; the real evidence is Section 4.4 (their median misses by 8% to 16% more than the baseline's). The report removed a similar sentence from the JSON for the same reason; this one should go too.
4. **Headline "matching today to comparable past days does NOT make the day's high or low more precise".** Supported for the 43 pre-fixed variants and, with my extra probe, for similarity re-weighting inside the baseline's 500-day window; not shown for every possible matching scheme and for gains below about 2% to 3%. Reword: "none of the 43 pre-fixed variants made it more precise; a gain of 1% to 2% cannot be excluded".
5. **"Beyond volatility clustering: no detectable gain"** is fine; note that the volatility-only control V is itself a one-feature nearest-neighbour method with the same noise price, so "S1 against V" compares two noisy matchers.
6. **Selection among variants.** Nothing is adopted, so selection cannot create a false adoption. The "best of 43" numbers (+0.02% to +0.78%) are maxima over strongly correlated variants and are of the size expected by chance (the median standard error of a gain is 0.63 to 0.83 points). The three positive pairs with raw p below 0.05 (all pre-open low, +0.36% to +0.39%) are 3 of 172, with 71 pairs significantly worse.
7. **Effective sample.** n = 320 sessions with a lag-5 HAC variance is adequate for the DM test, but the 80 nearest days are on median 27 separate episodes (Section 7.2) and the nearest five are fewer; read nothing from single lists.
8. **Contradictions with `A_dayahead.md`, `verify_A_dayahead.md`, `B_liveintraday.md`, `docs/LIVE_TOOLS.md`.** None found. The baseline figures equal A's to the last digit; A explicitly did not test volume, delivery, the S&P cue or implied volatility, and G's null does not contradict A's remark that the model's gain is in the band shape; B's "context did not improve the live bands after Holm" is consistent. The report's own "Contradictions: none" is right.
9. **Feature menu coverage (the user asked for "whatever helps").** Tested: VIX level, change and VIX-versus-realised-volatility spread; Nifty and Bank Nifty return and range; advance share, tail balance, market turnover; four peers; S&P 500, US VIX, US 10-year, Brent, dollar index, USDINR (with lags); BSE own range, close location, gap, volume, turnover, delivery, Parkinson 5-day and Garman-Klass 20-day volatility, 5- and 20-day return, distance from the 250-day high and low, streak, weekday, month-end; after the open: gap in sigma, open beyond yesterday's range, open's place in yesterday's range. **Untested, said so in the report:** BSE implied volatility and skew (461 sessions), F&O expiry, the Capital Markets index, the NSE pre-open order book, GIFT Nifty, FII/DII flows; not built although on the menu: 10-day realised range and volatility, ANGELONE and the other peers beyond four, India VIX high and low. The reason given for the implied-volatility and expiry gap (a pool under 150 days, empty Validation window) is right for a nearest-neighbour method, but it leaves the user's "IV minus trailing realised volatility" idea untested by any method in this specialist's work.
10. **Pre-fixed claim.** Section 0 of the final report is byte-identical to Section 0 of `G_analogue.md` as committed in `2072844` (16 Oct 08:00:49 UTC). That commit also contains the whole of `src/hl_analog.py` (772 lines) but **no `hl5_*` result file**; the first result files are in `68032e4` (08:27:36 UTC); the builder's scratch shows the baseline log at 05:39:58, the pre-fixed record at 05:40:04 and the first analogue evaluation log at 08:02:48 UTC. The first full run's sha256 for `hl5_eval_summary.csv`, `hl5_dm_holm.csv`, `hl5_predictions.csv` (`hash_run1.txt`, 08:15) equals the repo files today, and the evaluation core (`run_space`, `blend`, `pipeline`) did not change after the pre-fixed commit (the diff adds only report tables, post-hoc diagnostics, `STUDY_END`, junk-builder fixes). It is the builder's own record plus a git commit time, not an independent timestamp; the builder says so.
11. **Hashes.** "Whole original file sha256 86315bda..." = `git show 2072844:research/hl/G_analogue.md` (reproduced). "Section 0 text sha256 5fe6dc76..." reproduces for the Section 0 text stripped of surrounding whitespace, including the separator line.
12. **The 16 Oct typical misses in the JSON** for the after-open side are converted at the open (Rs 3,450), so they read 35.0 / 37.7 (baseline) against 34.8 / 37.4 elsewhere; the report says so.

## 7. Extra probes I ran (post hoc, labelled; not part of the adoption decision)

### 7.1 Re-weight the baseline's own 500-day window by context similarity (my code `m_probe.py`; 32 tests, own Holm family; Final n = 320)
Idea: the analogue alone variants lose to the baseline partly because they use 40 to 160 old days instead of the baseline's last 500. Here the pool is exactly the baseline's trailing 500 sessions, and every session gets a Gaussian-kernel weight from the same shrunk-Mahalanobis distance (bandwidth = distance to the 250th or 125th nearest), weighted quantiles with Hazen positions. Spaces V, A, B, C; both phases; both targets.

| result | value |
|---|---|
| control: equal weights on the same 500 days (same quantile method) against the baseline | -0.07% / -0.06% / -0.07% / +0.03% (H / L / HO / LO); the estimator itself costs nothing |
| best gain against the baseline of the 32 | +0.71% (pre-open low, set V, bandwidth 125th nearest; raw p 0.31); next: +0.56% (after-open high, set A) and +0.46% (after-open high, set B, raw p 0.030) |
| gains >= 1% | none |
| smallest Holm p in the family of 32 | 0.35 (set C, after-open high: +0.24% / +0.29%, raw p 0.011) |
| typical miss of the median, Rs | pre-open high 42.5 to 42.7 (baseline 42.7), low 47.6 to 47.7 (47.7), after-open high 34.6 to 34.8 (34.8), low 37.3 to 37.4 (37.4) |

Result: the context carries at most a few tenths of a percent of pinball loss, not significant; the null does not hinge on the noise price of small samples.

### 7.2 How many independent episodes are in the 80 nearest days
For each Final-window session I took the 80 nearest days (set B, pre-open) and counted separate episodes (a neighbour more than 10 sessions from the previous one starts a new episode): median 27 (10th to 90th percentile 21 to 33). Sets V, A, C: 30, 34, 34. The headline "80 days" behaves like roughly 30 independent draws, which is another reason the analogue quantiles are noisy.

### 7.3 Fill sensitivity
With delivery % for 13 to 15 Oct filled from `results/hl2_fill_delivery.csv` (36.07, 34.09, 32.03; source `nsearchives sec_bhavdata_full` per the meta file; I could not verify the values against an independent source), set B has all 14 features, the pool shrinks to 1,693 days and the five nearest become 2021-04-23, 2024-08-19, 2023-06-13, 2026-03-17, 2020-09-15 (pre-open) and 2026-03-17, 2026-09-15, 2024-11-19, 2022-07-20, 2024-11-06 (after the open). The 80-nearest medians move by at most Rs 4. Reproduces the report.

### 7.4 Ridge penalty and the learned-metric set L
In `hl5_ridge_blocks.csv` the penalty chosen for the learned metric was one of the two strongest (1,000 or 10,000) in 74 of 77 pre-open blocks and 74 of 77 post-open blocks, i.e. the ridge shrinks almost everything away; its own selection-sample R-squared averages +0.02 (and is optimistic, being the best of five penalties on the fit's own validation part). For 16 Oct the ridge picked 10,000 in both phases; I re-derived the live L-set nearest days and 80-nearest medians (pre-open 3,479.3 / 3,401.9; after the open 3,489.9 / 3,410.9) and they equal the builder's JSON.

## 8. Defects found

1. **Ridge out-of-sample R-squared (secondary S3) is computed in mismatched units.** In `eval_tables` the prediction `ridge_pred` is `(Z @ beta) * sd_y + mu_y` where `y` is the standardised outcome `U = V / sigma`, but it is compared with `Y = names[ph][3]`, the raw log outcome. I reproduced the quoted figures exactly with that recipe (+0.0324, -0.0705, +0.0194, -0.0090 for Final; +0.0256, -0.0551, -0.0059, -0.0136 for Validation+Final), and obtained -0.002, -0.023, +0.008, -0.010 (Final) and +0.002, +0.008, +0.004, -0.004 (Validation+Final) in consistent units. Affected: `results/hl5_secondary_ridge_r2.csv`, Section 4.5, "numbers to quote" 6, and the headline block. Does not change any test, the adoption table or the conclusion.
2. **Wording items 2 to 4 of Section 6** (power, "as spread out", "does NOT").
3. **Staleness guard in `lookup()`** (Section 3): not a leak, but it makes a forecast depend on a file's end date; it can produce a false alarm in a leakage test and it changes the C and L feature sets on Mondays between test and live use. Suggested fix: when a source file ends before the target date minus the lag, drop the feature (as now) but decide it from the target date and a fixed calendar of the last allowed observation, not from the derived series' last non-missing date; or apply the same drop in the walk-forward.
4. **Stray file in the repo root:** `leak_junk_positive.csv` (commit `fd1cb40` says it was written by the analogue-day study). It was written by an earlier scratch verifier script (`verG/leak_indep2.py`), not by `hl_analog.py`; harmless, not used.
5. **Section 0.3 counts** (31 / 35 features, 35 / 40 candidate) are wrong in the pre-fixed text and corrected in Section 6 of the report; the correct counts are B 14, C 34, L 38 (43 with the five post-open features), as `hl5_features.csv` lists. Disclosed, no action.
6. **The pre-fixed reason for choosing set B as the display variant** ("complete on 16 Oct") turned out false (delivery % missing for the last three sessions). Disclosed in Section 6.2; the choice itself was made before results.

## 9. What the lead may quote, must correct, or must not quote

### 9.1 May be quoted as they stand (all reproduced; n beside them)
* 0 of 172 variant-target pairs meet the pre-fixed rule; family 172; 38 pre-open and 43 post-open candidate features; best Final gains +0.02% / +0.78% / +0.41% / +0.39% (pre-open high / low, after-open high / low; n = 320), the rule needs at least +2% and Holm p < 0.05. (My recomputation gives the same.)
* Typical miss of the median at Rs 3,428, Final n = 320: baseline pre-open high Rs 42.7, low Rs 47.7; after the open high Rs 34.8, low Rs 37.4; 'price stays' Rs 62.9 / 61.3; over all 43 variants the miss stays within Rs 41.8 to 44.0, 47.2 to 49.3, 34.2 to 35.7, 37.2 to 39.4. Display variant alone 43.4 / 47.6 / 34.4 / 37.5 and blended 42.8 / 47.4 / 34.5 / 37.2.
* Analogue-alone pinball against the baseline: -5.0% / -1.4% / -3.1% / -2.1%; blended -1.4% / -0.1% / -1.1% / -0.5%. Significantly worse after Holm: 16 / 0 / 15 / 1 of 43.
* The median of the 5 nearest days misses by Rs 46.2 / 51.9 / 40.5 / 41.9 against 42.7 / 47.7 / 34.8 / 37.4 (n = 320, s.e. Rs 2 to 3).
* 16 Oct: comparable-days and baseline medians differ by Rs 14 / 11 / 5 / 2; the dated nearest days (set B, 13 of 14 features, pool 1,885); the list changes from 2026-10-06, 2026-04-07, 2026-08-25, 2021-04-23, 2024-08-19 to 2021-04-23, 2024-08-19, 2023-06-13, 2026-03-17, 2020-09-15 when delivery % is filled.
* Leakage test passed (builder's 8 sessions; mine: 10 other sessions, two junk styles, positive controls move).
* Context sets against the volatility-only control: 0 of 32 comparisons significant after Holm.
* Add, from this verification: re-weighting the baseline's own 500 days by similarity gives at most +0.71% (n = 320; 32 tests; smallest Holm p 0.35); the 80 nearest days are about 27 episodes.

### 9.2 Must be corrected before quoting
1. "Ridge out-of-sample R-squared -0.07 to +0.03" -> "between -0.02 and +0.02 (verifier's recomputation in consistent units, -0.023 to +0.008 for the standardised outcome; n = 318 Final, 566 Validation+Final)".
2. "Only a true gain of about 2.3% to 3.0% or more could have been confirmed" -> "a true gain below roughly 2.3% to 3.0% would usually have gone undetected (about 50% power at that size, 80% power needs roughly 2.8% to 3.7%)".
3. "The five most similar days are as spread out as the whole history" -> "the five days' highs ranged from -0.16% to +3.94% against -0.18% to +6.80% for the middle 90% of all 1,885 compared days; five days are too few to read a forecast from (their median misses 8% to 16% more than the baseline's)".
4. "Matching ... does NOT make the high or low more precise" -> "none of the 43 pre-fixed variants did; a gain of 1% to 2% cannot be ruled out with 320 sessions".
5. For the after-open typical misses taken from the JSON (35.0 / 37.7 at Rs 3,450), say that the figures elsewhere (34.8 / 37.4) are at Rs 3,428.

### 9.3 Must not be quoted
* The nearest-five or nearest-ten days as a forecast or as "what usually happens"; the ridge feature weights as "what matters"; set C against the volatility-only control as a finding (raw p 0.0025, Holm 0.08, one of 32 secondary tests); the S4 table (matching against random draws) and the by-year table as evidence (post hoc); the 16 Oct session or anything about its outcome; "validated" for any of this (the Final window was also used to choose the baseline); the C and L variants' live output on a Monday.

## 10. What I could not check
* An independent source for the delivery-% and index / breadth / peer / US fill values (`hl2_fill_*.csv`); used only in the labelled sensitivity.
* The FRED publication lag beyond the conservative lag rule (the rule makes the question moot for the tested features).
* The user's untested menu items (implied volatility, expiry, GIFT Nifty, order book, FII/DII flows): no data or no history; nothing here says they would not help.
* That S6 itself is the right volatility model (a project decision; verified by earlier work).

## 11. Commands to reproduce every verification number

Scratch directory `S=/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/verG2`; run from `$S` (uses `$S/../verA/indep.py` for the S6 library; reads the repo files read-only; nothing writes into the repo):
```
cd $S
python3 m_base.py                   # S6 sigma from raw files -> sig_mine.pkl (9 s)
python3 m_run_base.py               # baseline vs project's stored predictions; Final metrics; price-stays
python3 m_run_feat.py               # my 43 features -> X_mine.pkl
python3 m_analog.py                 # my engine: all 86 variant arrays -> mine_Q.pkl (22 s)
python3 run_builder_pipeline.py     # builder's pipeline, read-only, cached for comparison (24 s)
python3 cmp_feat.py                 # my features vs builder's: 3.6e-15
python3 m_eval.py                   # my quantiles vs builder's: 1.1e-14
python3 m_adopt.py                  # the adoption rule, DM, Holm over 172, calibration -> mine_adoption.csv
python3 m_claims.py ; python3 m_claims2.py        # display variants, miss ranges, power, S1, S2, S4, by-year
python3 m_r2_units.py               # the ridge R-squared unit error (reproduces the builder's figures, then the correct ones)
python3 m_live.py ; python3 m_live_L.py ; python3 m_live_filled.py      # 16 Oct nearest days and quantiles (V, A, B, C; then the ridge set L); delivery-% fill
python3 text_vs_mine.py             # 688 + 24 report cells against my numbers
python3 align_check.py              # file alignment with the BSE dates
python3 m_probe.py ; python3 m_eff.py             # extra probes (7.1, 7.2)
for k in 800 1303 1650 1990 2054 2200 2300 2349 2380 2389; do for m in positive extreme ctrl_prev ctrl_macro1 ctrl_macro2; do python3 leak_mine.py $k $m; done; done   # about 40 s each
python3 junk_after_1015_v2.py ; python3 run_copy.py $S/copyB/ out_B.json   # isolation test, see Section 5.3
python3 trunc_test.py ; python3 monday_guard.py   # live row against walk-forward row at block starts; Monday guard
```
Builder commands re-run in `$S/copyA` (a copy of `src/`, `data/processed/`, `data/raw/macro/`, `results/`): `python3 src/hl_analog.py --eval | --adopt | --live | --leak | --check | --selfcheck`.
