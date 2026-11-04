# Independent audit of the NSE:BSE next-session forecast pipeline

Auditor stance: sceptical, adversarial, no edits to `src/`, `docs/`, `results/`, `data/`, `tests/`. All scratch code is in `/tmp/audit/` (listed at the end). Repo state audited: branch `claude/dreamy-albattani-k94wba`, HEAD `b636691` plus untracked `src/scenarios.py` / `results/scenarios.json` that appeared during the audit (not reviewed). Data end: 2026-10-12 (2,387 sessions); the 2026-10-13 row is not in the processed data (live forecast uses a provisional bar).

Note on a moving target: at about 11:14 UTC, while this audit was being finished, someone other than the auditor began editing the working tree (`src/location.py` now adjusts the close for RSI/MA and gates sparse features, and a `results/v1_before_audit_fixes/` folder appeared; `results/location_selection.json` and `eval_location_stdout.txt` show as modified). All findings and all numbers below refer to the committed code at `b636691`, which is what I executed. I did not audit the edited `location.py` or the regenerated location results. Because the F4/F5 fixes change the location predictions and the frozen-hyperparameter/Val+Final evaluation, that regeneration should be logged in `docs/DEVIATIONS.md` (it is a post-result code change; my own re-runs show it does not alter the gate outcome).

## 0. Verdicts

| # | Task | Verdict | One-line reason |
|---|---|---|---|
| 1 | Look-ahead / leakage | **PASS** | No leakage in any scale, range, ridge or logit model. Verified by 5 independent test types on real data, with positive controls. The repo's own tests are too weak to show this (see F1). |
| 2 | Independent re-derivation | **PASS** | S0, S1, S4, S2, S6 and the evaluation table reproduce to machine precision (>= 12 significant figures). |
| 3 | Data checks | **PASS WITH ISSUES** | Bonus adjustment, jump screen, session counts and the last 64 closes check out. Minor: two unverifiable special-session classifications. |
| 4 | Protocol compliance | **PASS WITH ISSUES** | Both gates applied correctly and reproduced. Several small unrecorded departures (F8), none outcome-changing. |
| 5 | Statistical soundness | **PASS WITH ISSUES** | The tests are implemented correctly. The headline "timed beats untimed" is supported only against the weak pre-registered S0 (F2). Model choice among S1-S6 is statistically a tie (F3). |
| 6 | Bugs | **PASS WITH ISSUES** | No critical or outcome-changing bug. Two real feature defects (F4, F5) that I quantified as harmless to the gate result. |

No critical findings. Two major findings (F1 test weakness, F2 over-strong claim). Everything else is minor.

---

## 1. Findings (ordered by importance)

### F1 [major] The repo's anti-leakage tests cannot detect the most common leakage types
**Evidence.** I copied `src/` and injected two look-ahead bugs, then ran the repo's own `tests/test_pipeline.py::test_no_lookahead` against each:
* bug1: `models.fhs_quantiles` uses `x[lo:t+1]/sigma[lo:t+1]` (the realised target enters the quantile window). Repo test: **PASS**.
* bug2: `models.sigma_har_block` trains on `< t_b + 3` (3 future rows inside the refit block). Repo test: **PASS**.

Reason: the truncation test and the "scramble the future" test only reach leaks that extend beyond the cutoff. A leak of the same session, or of a few sessions inside a 20-session block, is present identically in the truncated and the full run. It also runs only on synthetic data with `exog=None`, so S5 and `exog_matrix` are never tested.

`tests/test_location_null.py` shuffles BSE returns, which destroys any link to exogenous series. I injected an unshifted same-day Nifty return (`F["nifty1"]` without `.shift(1)`) into a copy of `location.py`:
* the null test still reports OOS R² -0.0021 (mean) / +0.0032 (max), identical to the clean code, so it is **blind** to this leak;
* on real data that leak lifts Dev OOS R² from about 0.016 to 0.097.

The claim in DEVIATIONS #12 that the null test shows "the pipeline itself does not generate spurious predictability" is true for the shuffle null (I reproduced -0.0021 / +0.0032). It is not evidence of absence of look-ahead.

**Fix.** Add a same-row perturbation test that runs on the real data. Truncate at t-1, append a garbage row t (twice, with different garbage), and assert identical forecasts and feature row at t. Do this for S0-S6 including S5, the range model, the location features and `walk`. My harness is `/tmp/audit/same_day.py`. It flags bug1 in 14 of 23 series and bug2 in 6 of 23, and passes the real pipeline.

### F2 [major, claim] "Timed volatility models beat the untimed benchmark out of sample" is supported only against S0, and in the Final window the gain is mostly level recalibration
**What is supported (reproduced).** DM one-sided vs S0, Newey-West 5 lags with the HLN factor. Mean pinball is x1e4, gain is S0 minus model.

| Window | n | S1 gain (p) | S6 gain (p) | S6 Holm p |
|---|---|---|---|---|
| Dev | 1322 | 1.09 (0.004) | 1.36 (0.0002) | 0.0012 |
| Val | 248 | 0.85 (0.20) | 1.18 (0.11) | 0.60 (not significant) |
| Final | 317 | 1.67 (0.006) | 1.95 (0.0006) | 0.0037 |
| Dev+Val | 1570 | 1.06 (0.003) | 1.33 (0.0001) | 0.0006 |

The Final-window result is a genuine unseen-data result for the pre-registered gate. It passes (p well below 0.10).

**What is not supported.**
1. In Final, S0 is badly mis-calibrated, not just unskilled. Its 90% coverage is 96.85% (Kupiec p = 2.8e-6) because the expanding RMS still carries the high-volatility 2020-2024 history. Multiplying S0 by a single ex-post constant (c = 0.75, fitted on the Final window itself, so optimistic for S0) gives pinball 47.311, against S6 47.271 and S1 47.557. DM S6 vs S0·c has p = 0.44 and S1 vs S0·c has the wrong sign. So the Final-window gain is indistinguishable from a one-parameter level correction. The data cannot separate day-to-day volatility timing from level adaptation.
2. Against a more natural untimed benchmark, the trailing-250-day median-centred empirical return quantiles, the advantage is weak:

| Window | S6 vs EMP250 gain (p) | S1 vs EMP250 gain (p) |
|---|---|---|
| Final | 0.74 (0.084) | 0.46 (0.22) |
| Val | 0.70 (0.19) | 0.37 (0.33) |
| Dev+Val | 1.41 (0.0001) | 1.14 (0.003) |

Only the pooled Dev+Val window is clearly significant. A 500-day untimed window is beaten by S6 in Final (p = 0.002), but that window is itself a poor comparator: it is worse than S0 in Dev+Val (one-sided p that it is better than S0 = 0.98), so S0 is not a pathological benchmark pooled, only in Final.
3. The Validation window alone shows no significant gain for any model (Holm p about 0.6). The DM t-statistics are insensitive to the NW lag (S6 vs S0 Final: 3.49, 3.50, 3.39, 3.26, 3.15, 3.50 for lags 0, 1, 3, 5, 10, 20).

**Suggested wording.** "Volatility-adaptive scale models (EWMA, GARCH, HAR and blends) beat the pre-registered expanding-RMS benchmark on pinball loss on Dev+Val and Final. The Final-window gain is no larger than a one-parameter rescaling of that benchmark, and not significant against a trailing-250-day untimed benchmark."

**Fix.** Add an adaptive untimed benchmark (trailing-250 empirical quantiles) as a reported comparator. Report coverage of the benchmark next to its pinball.

### F3 [minor] Selection among S1-S6 is statistically a tie; "ties -> simpler" was never operationalised
Gate result reproduced: R -> S6 (Dev+Val pinball 52.798 vs S4 52.889, S1 53.076), G -> S4 (20.517 vs S5 20.556), I -> S6 (49.178 vs S4 49.234), rho -> HAR. Code applies a strict minimum, which is literal compliance.

DM on Dev+Val: S6 vs S4 gain 0.09 (p = 0.22); S6 vs S1 gain 0.28 (p = 0.029, unadjusted for choosing the best of 6). Final (unseen): S6 vs S4 0.017 (p = 0.45); S6 vs S1 0.29 (p = 0.106). If "tie" meant "not significantly different", the clause would select S1 (or S4) for R. The choice of S6 is unjustified by data, though harmless: live R sigma spans 0.0229 (S1) to 0.0261 (S0, S2) and the selected S6 is 0.0248.

**Fix.** Define "tie" (e.g. DM p > 0.10 -> simpler) before the next protocol. State in the record that S6 was chosen by the strict minimum and is not distinguishable from S1/S4.

### F4 [minor, outcome-neutral] RSI and distance-to-MA features use the unadjusted close
`location.py:66-69`: `rsi(d["close"])`, `d["close"].rolling(20/50).mean()`. `d["close"]` is the raw NSE close, which falls by factor 3 on 2022-03-21 and 2025-05-23. Right after the 2022 ex-date, `dist20` is about -3.6, `dist50` about -2.2, `rsi14` about -22 (feature scale). `dist20` is distorted on 38 rows (2022-03-22 to 2025-06-19) and `dist50` on 98 rows (to 2025-07-31). The 2025 episode lies in Validation/Final. `snapshot.py` and `episodes.py` do use an adjusted close, so this is an inconsistency of the kind already fixed once (DEVIATIONS #13).

**Impact (re-run).** With adjusted close, Val+Final ridge OOS R² vs hist mean goes -0.0280 -> -0.0272, CW p 0.559 -> 0.543, direction accuracy 0.5009 -> 0.5062. Gate unchanged.

**Fix.** Build the technical features on the bonus-adjusted close (the `ca_factor` suffix product used in `snapshot.py`).

### F5 [minor, latent hazard] `capmkts1` is a degenerate feature and its standardiser blows up
`index_daily.csv` has Nifty Capital Markets only from 2024-09-13 (plus one stray point on 2023-04-12). `location.py:54` zero-fills the feature, so it is exactly 0 for 76% of evaluation rows. `walk()` standardises with `sd = std + 1e-12`. In the first block where the feature is non-zero, the training sd is 0, and the standardised test value reaches |Z| = 4.8e11. This is harmless only because the ridge/logit weight on an all-zero training column is exactly 0. In later blocks the sd is tiny (a few non-zero rows among about 1,700 zeros), so test |Z| is inflated for a feature the model has barely seen.

**Impact.** Dropping `capmkts1`: Val+Final R² -0.0280 -> -0.0272, CW p 0.559 -> 0.424, logit AUC 0.499 -> 0.516, ridge direction accuracy 0.5009 -> 0.5186 and logit 0.508 -> 0.520 (both still below the 0.529 best-constant base rate; binomial p 0.71). Gate unchanged. With both F4 and F5 fixed: R² -0.0264, CW p 0.408, ridge direction accuracy 0.515.

**Fix.** Exclude features with fewer than N non-missing training rows, or use `fillna` only after standardising on the available subsample, and guard `sd < eps`.

### F6 [minor] Comment/code mismatch on the beta residual
`location.py:55` says "rolling beta on data dated <= t-2". The code `R.rolling(120).cov(nifty).shift(1)` ends at t-1, so the beta includes day t-1, the day whose residual it then removes. This is not look-ahead (all information is <= t-1). It makes the residual slightly in-sample.

### F7 [minor] "Validated" is too strong for the coverage statements
`forecast_live.py:133` says 90% coverage "was validated (Final-window Kupiec p=0.27)". Facts:
* Kupiec power at n = 317 to reject true coverage 0.88 is only 22% (0.86: 62%, 0.85: 79%).
* Selected S6 on Dev+Val has 90% coverage 88.15% with Kupiec p = 0.017.
* For G, every model under-covers 90% in Dev+Val (selected S4: 86.1%, Kupiec p about 0); Final is fine (91.2%, p = 0.48).
* S6 50% interval coverage in Final is 46.4% and S1's is 43.9%.

This is a wording issue only. The pre-registered calibration rule (scalar rescale if Final Kupiec p < 0.05) is not triggered by any selected model (R p = 0.27, G p = 0.48, I p = 0.61).

### F8 [minor] Departures from the protocol not recorded in DEVIATIONS.md
1. QLIKE secondary metric (PREREGISTRATION s4): `metrics.qlike` exists but is never called; no QLIKE output exists.
2. Christoffersen test reported only for the 90% interval (`christ90`), not 50/80/95%.
3. S0 is a zero-mean expanding RMS, not an expanding std (`models.py:27-34`). Immaterial.
4. High/low-vol halves use an expanding-median split of trailing-60d vol (`evaluate.py:90-91`), not a "rank" split.
5. Location features are divided by the S1 forecast sigma for day t, not sigma_{t-1} (DEVIATIONS #7 covers the S1 choice, not the t vs t-1 indexing).
6. `capmkts1` is zero-filled where unavailable (the protocol says "when available").
7. Weekend sessions get all-zero day-of-week dummies, so they are treated as Mondays.
8. Delivery-% secondary analysis (`src/delivery_secondary.py`) prints to stdout only, with no stored results file.
9. Live record schema vs PREREGISTRATION s6: `forecast_live.py` writes no cutoff timestamp (only `generated_utc`), no scenario probabilities or invalidation conditions (not written by `forecast_live.py`; `src/scenarios.py` is new and unreviewed), and data hashes are truncated to 16 hex characters for 3 files. `code_commit` is `git rev-parse HEAD`, which does not capture a dirty working tree (the preview's commit `9bfedcb` pre-dates `forecast_live.py` itself).
10. DEVIATIONS.md timestamps are inconsistent with git commit times (UTC+5:30). Entry #12 "freeze ~16:45 IST" vs commit `2df7073` at 16:07 IST. Entry #13 "~17:30 IST" vs commit `b636691` at 16:30 IST. Entry #14 (16:30) is listed after #13 (17:30). Entries #13-#18 are timestamped 16:30-17:45 IST but are contained in the 16:30 IST commit, so the log times cannot be literal. The ordering of work is still consistent with the claims: the freeze commit precedes `forecasts_*.csv` (10:37:43 UTC) and `eval_scale_all.csv` (10:37:47 UTC) by 35-39 s; the frozen model/eval files are byte-identical in HEAD; and `eval_scale_dev.csv` equals the Dev rows of `eval_scale_all.csv` exactly. Entries 8-12 were committed only at 10:37 UTC, after the Dev outputs existed at 10:35-10:36, so "results seen: No" for #8-#11 rests on the log's word, not on git.

### F9 [minor] Stated power is somewhat off
PREREGISTRATION s4: "≈320 sessions, a true 53% hit-rate is detectable with ≈15% power". Exact binomial, alpha 0.05: one-sided vs 50% power = 26-27%; two-sided = 16%; one-sided vs the hindsight best-constant 0.514 (what the gate actually tests) = 12%. For Val+Final (n = 565, base 0.529) the gate needs accuracy >= 0.5646: power 26% if true accuracy is 55%, 43% at 56%, 78% at 58%. "Not detected" must not be read as "no effect", as the protocol itself says.

### F10 [info] The location gate is nearly impossible to pass by design; Clark-West is well sized
Under a null that preserves volatility clustering (shuffle R/s_t, keep s_t, 60 seeds), ridge OOS R² vs hist-mean averages -0.0275 (all) / -0.0634 (Val+Final), the directional binomial test rejects 0-1.7% of the time, and Clark-West rejects 5.0% (all) / 8.3% (Val+Final; se about 3.5%). So the R² > 0 and the "beat the hindsight best constant" legs are conservative; CW is the informative leg and it is not significant (p = 0.56). The real Val+Final R² (-0.028) is not worse than the noise-only average. The conclusion "no demonstrated directional predictability" stands, but with low power (F9). CW is applied to approximately, not strictly, nested models: ridge forecast = (mean clipped standardised return) × s_t + features, vs raw expanding mean. Empirical size above says this does not matter.

### F11 [info] Deviation #16 (gap-location override) is data-supported but confounded
Verified from `bse_daily.csv`:
* LAST == CLOSE in 49/49 sessions since 2026-08-03 vs 1.5% before.
* Positive-gap share 22/49 = 0.449 vs 0.707 before (binomial p = 0.0002).
* Median gap 0.000% vs +0.279%.

Cautions: the post-break window is a drawdown (mean R -0.185%/day vs +0.146% before); the positive-gap share was already 0.615 in Jan-Jul 2026 (n = 143); the "Welch p = 0.11" is not reproduced (I get 0.042 vs all pre-break sessions, 0.055 vs Val+Final, 0.125 vs the last 250, 0.279 vs 2026 pre-break). The override is disclosed and reasonable, but the post-hoc L1 rule (#15) had validated a real gap premium on Val+Final (DM p = 0.0007), and the live record should say the zero-median gap is a judgement call.

### F12 [info] Numerical: EPS floor on G²
`common.EPS = 1e-8` floors G² for 125 exact-zero gaps (5.2% of sessions) in the HAR for G, which feeds log(1e-8) = -18.4 in both the response and the lagged regressor. Floors of 2.5e-7, 1e-6 and 4e-6 change selected-S4 G pinball by at most +0.3% (floors up to 1e-6) and +0.6% (4e-6): devval 20.517 -> 20.512/20.540/20.572; final 18.702 -> 18.721/18.758/18.819. Not outcome-relevant; a tick-based floor would still be cleaner.

### F13 [info] Checked and immaterial
* In-sample z-history for parametric models (z uses the current-block parameters for the 500 prior rows, so rows before the block are in-sample): replacing it with the stored out-of-sample sigma path changes pinball by <= 0.1% and 90% coverage by <= +0.8 points (S2/S4/S6, Dev+Val from eval row 500, and Final).
* GARCH fit failures: 0 of 95 blocks (R target).

---

## 2. Task 1 detail: look-ahead / leakage

### 2.1 Code read, per model (could the forecast for session t use information dated >= t?)

| Component | Verdict | Why (file:line) |
|---|---|---|
| S0 `sigma_hist` | No | `s[t] = sqrt(cumsum(x²)[t-1]/t)` (`models.py:27-34`) |
| S1 `sigma_ewma` | No | `s[t]` stored before the update with `x[t]` (`models.py:37-45`) |
| S2/S3 GARCH | No | Params fit on `x[t_b-1500:t_b]`, t_b <= t (`models.py:60-77`). `_garch_filter` stores `h[t]` before the update with `x[t]` (`models.py:49-57`). Filter run over the full series, but `h[t]` depends on `x[<t]` only |
| S4 HAR | No | Design is `shift(1)` then `rolling` (`models.py:98-100`). Training rows `< t_b` (`models.py:112`). Smear from the training residuals only |
| S5 HAR-X | No | As S4; `exog_matrix` shifts every column by one (`models.py:190`) |
| S6 | No | `sqrt(S2·S4)` of the above |
| FHS z-history | No | `z = x[t-500:t]/sigma[t-500:t]` (`models.py:126`). `sigma` is the current block's path: parameters from rows < b0 <= t, so rows before b0 are in-sample fits and rows in [b0, t) are out-of-sample. No information >= t. Only `x[<t]` enters |
| Range HAR / EMP250 | No | `run_range` (`walkforward.py:38-51`): same HAR machinery on rho²; `EMP250` uses `rho[t-250:t]` |
| Ridge / logit | No | Features see <= t-1 (table below). Standardiser `mu, sd` and weights are fit on `tr = arange(0, b0)` (`location.py:84-87`). Block refit every 20 sessions. alpha/C chosen on Dev only (recomputed: dev MSE/logloss equal the stored JSON to 6 d.p.; full-run and dev-stage predictions agree to 2e-18) |
| Live forecast | No | `live_sigma`/`quantiles` append a placeholder at index n that is never read by `sigma[n]` (`forecast_live.py:30-52`). Parameters are refit on all n known rows |

### 2.2 Feature alignment in `location.py` (all verified by the perturbation tests too)

| Feature | Construction | Latest data used |
|---|---|---|
| r1, r2 | `R.shift(k)/s` | t-1, t-2 |
| cum5/20/60 | `R.rolling(k).sum().shift(1)` | t-1 |
| i1, g1 | `.shift(1)` | t-1 |
| nifty1, capmkts1 | `.shift(1)` over `rolling(60).std().shift(1)` | t-1 |
| resid1 | beta `rolling(120).shift(1)` | t-1 (includes the lagged day, F6) |
| dvix1 | `diff().shift(1)` / 60d std shifted | t-1 |
| vixpct | `lv.shift(1).rolling(500,min_periods=120).rank(pct)` | t-1 |
| turn_z | `rolling(60)` z then `.shift(1)` | t-1 |
| adv1 | `br.adv_share.shift(1)` | t-1 |
| rsi14, dist20, dist50 | computed on close, then `.shift(1)` | t-1 (but unadjusted close, F4) |
| dow | calendar of t | known ahead |
| s | S1 EWMA forecast of R_t | t-1 |

### 2.3 My own tests on the REAL data (`/tmp/audit/trunc_scale.py`, `loc_run.py`, `same_day.py`)
1. **Truncation, cutoff 2024-12-31** (1,447 forecast dates, 23 series: R/G/I × S0-S6 + rho HAR/EMP250): forecasts from a run on the truncated CSVs equal the full run. Max abs diff 4.9e-17. Cutoff 2025-09-30 (1,634 dates): 4.9e-17.
2. **Future-garbage, cutoff 2024-12-31**: after the cutoff, BSE OHLC ratios permuted/re-based, turnover/volume scrambled, index and breadth rows permuted and noised. Max diff 0.0 over the same 23 series (S5 included).
3. **Location**: the full feature frame (21 features + sigma) is identical row-by-row between full, truncated and garbage-future runs (diff 0). Ridge (alpha = 1000 and 10) and logit predictions are identical (max diff 1e-16, NaN patterns equal, 1,447 dates).
4. **Same-row perturbation** (the test that catches same-session leakage): at rows 2022-03-22, 2025-05-26, 2025-08-14 and 2026-10-12, data up to t-1 is real and row t is replaced by two different garbage versions. All 23 scale forecasts, the 21 features, ridge and logit at t are identical (diff 0.0). They also equal the stored `forecasts_*.csv` / `location_predictions.csv` values at those dates (<= 1e-16), so the stored forecasts used nothing from t onwards.
5. **Positive controls**: the same-row test flags injected bug1 in 14/23 series (max change 0.0046) and bug2 in 6/23. The truncation test flags neither (F1).
6. The stored outputs reproduce exactly: re-running the pipeline from the CSVs matches `forecasts_{R,G,I,rho}.csv` to 1e-16, and re-running `evaluate.py --periods all` on the stored forecasts matches `eval_scale_all.csv` (194 rows) to <1e-9.

(e) Period slicing: `slice_dates` / `window_mask` are inclusive and non-overlapping; dev 1322 + val 248 + final 317 = 1,887 forecast dates = `all`. Dev/Val/Final boundaries are the pre-registered dates. The volatility-regime split (`evaluate.py:90-91`) uses `shift(1)` and an expanding median.

Limit: I verified code from the CSVs onwards. `build_dataset.py` I read and re-ran (it reproduces the four processed CSVs bit-for-bit from `data/raw`). Its only same-session element is the short-session flag, which uses the session's own Nifty volume to decide inclusion. That selects which sessions exist, not a forecast input, and special sessions are scheduled in advance.

---

## 3. Task 2 detail: independent re-derivation (from `bse_daily.csv` only; no `src` imports)

Targets: G = ln(open/prev), I = ln(close/open), R = ln(close/prev); |R - (G+I)| <= 2.8e-16; n = 2,387.
Final window = 2025-07-01 onward (n = 317), R target. Grid {0.025,0.05,0.10,0.25,0.5,0.75,0.9,0.95,0.975}.

| Quantity | Mine | `eval_scale_all.csv` |
|---|---|---|
| S0 mean pinball ×1e4 | 49.22368 | 49.22368 |
| S0 90% coverage / Kupiec p | 0.968454 / 2.8196e-6 | 0.96845426 / 2.82e-6 |
| S1 mean pinball ×1e4 | 47.55743 | 47.55743 |
| S1 90% coverage / Kupiec p | 0.883281 / 0.33239 | 0.88328076 / 0.33238991 |
| DM S1 vs S0: mean gain ×1e4 | 1.66625 | 1.66625 |
| DM t (NW 5 lags, plain / HLN-adjusted) | 2.5215 / 2.5176 | 2.5176 (HLN) |
| DM one-sided p (t, n-1 df) | 0.0061557 | 0.0061557 |

Match to 3 significant figures and far beyond. Further independent re-implementations:
* S0 and S1 quantiles for **all** dates and all three targets (R, G, I): max abs diff vs stored forecasts about 1e-16.
* S4 (HAR + Duan smearing; own design matrix and OLS): max |dq| 7e-16, final pinball 47.2875 (stored 47.2875).
* S2 (own GARCH(1,1)-t recursion using only `arch` to fit; zero-mean, 1,500-session window, 20-session refit) and S6 = sqrt(S2·S4): S2 sigma rel diff 1e-14, S6 quantiles abs diff 4e-16. S6 Final pinball **47.2707**, 90% coverage 0.91798, Kupiec p 0.27219. All equal the stored values.
* S6 plausibility from the stored file alone: recomputing from the stored S6 quantiles and realised returns gives 47.2707; stored y equals R to 1e-16; quantiles are monotone and NaN-free for all 7 models.

---

## 4. Task 3 detail: data checks

* **Bonus adjustment.** Verified list: 2:1 bonus ex 2022-03-21 and ex 2025-05-23, factor 3. NSE `PREV_CLOSE` is not re-based in the archive (nse_prev 2826.60 / 6996.50 on the ex-dates), so the raw log(open/prev_kept_close) is -1.144 and -1.088. Adjusted: 2022-03-21 prev 942.20, open 900.00, close 938.05 -> G -4.6%, I +4.1%, R -0.4%; 2025-05-23 prev 2332.17, open 2358.00, close 2448.00 -> G +1.1%, I +3.8%, R +4.85%. Both sane, and the surrounding days continue smoothly.
* **Other jumps.** Under the raw definition |ln(open/prev_kept)| > 0.25 occurs only on those two dates. After adjustment the largest |G| are 0.182 (2020-06-23, an isolated event day I could not cross-check offline), -0.163 (2024-04-29, SEBI turnover-fee order; R -0.147 = -13.7% simple, matching dossier A1), 0.102 (2024-08-08); largest |R| 0.171 (2022-03-10), 0.167 (2024-09-16), 0.157 (2025-03-28, = +16.98% simple, matching dossier A4 exactly). Nothing looks like an unadjusted corporate action.
* **Short-session drop rule** (`SHORT_RATIO = 0.35` of the trailing-20 median Nifty volume). 12 dropped: 9 Diwali Muhurat dates, 2 Saturday DR-drill dates (2024-03-02, 2024-05-18), and **2017-07-10 (Monday)**. The last is not a known special session, but the whole market was abnormal that day: median trades per stock 242 vs 1,267 the day before, market turnover 0.27× its median, only 411 liquid names vs about 820. The rule is volume-only and the exclusion is justified; the day is in the burn-in period. The lowest ratios among kept sessions are 0.48-0.61 (New-Year's-Day and year-end low-activity days such as 2019-01-01, 2021-01-01, 2018-12-31, plus 2024-01-20), so no ordinary session is dropped by mistake. Returns on the first regular session after a dropped one (e.g. +14.4% on 2023-11-13) span two sessions by design (DEVIATIONS #9).
* **Weekend sessions kept.** 2020-02-01 (Sat, Budget), 2025-02-01 (Sat, Budget), 2026-02-01 (Sun, Budget; R -8.1% log = -7.8% simple, intraday low -15%, matching dossier A11) have Nifty volume ratio about 1.0 and look like full sessions. **2024-01-20 (Sat)** has ratio 0.56, market turnover 0.76× and BSE turnover half normal; DEVIATIONS #10 calls it "full". I cannot verify the session format offline; if it was a two-part DR session it should have been dropped. It is 1 observation of 2,387 (Dev window) and immaterial.
* **Sessions per year (kept):** 2017: 222 (from Feb), 2018: 245, 2019: 244, 2020: 251, 2021: 247, 2022: 247, 2023: 245, 2024: 246, 2025: 248, 2026: 192 (to 12 Oct). Plausible (245-251 for full years). No gaps longer than 5 calendar days other than normal holiday clusters (2017-10-23, 2018-04-02, 2021-11-08, 2022-04-18). No zero-range, zero-volume or duplicated-OHLC sessions apart from one benign repeat.
* **Cross-check against `research/02_regulatory_macro_catalysts.md` "Compact BSE close series".** 65 table rows (13-Jul to 13-Oct-2026). 64 are in the data (13-Oct is not in the processed file): all 64 closes match with **0.00 difference**, and the printed % changes match to <= 0.005 pp. The dossier's descriptive stats (mean -0.16%, sigma 2.11%, 29 up days of 65) are reproduced from the data plus the +1.36% 13-Oct line.
* **Reproducibility.** `build_dataset.py` run on `data/raw` in a scratch directory reproduces `bse_daily.csv`, `index_daily.csv`, `breadth_daily.csv` and `bse_all_sessions_with_flags.csv` with zero difference.
* **Feature-side data issues:** F4 (unadjusted close in technical features), F5 (Capital Markets index only from 2024-09-13). Known limitations already logged: price returns without dividend re-basing, breadth not corrected for other stocks' corporate actions (DEVIATIONS #11).

---

## 5. Task 4 detail: protocol compliance

**Scale gate (PREREGISTRATION s4), reproduced from `eval_scale_all.csv` period `devval`.**

| Target | Lowest Dev+Val pinball among S1-S6 | Live selection in `forecast_live.py` |
|---|---|---|
| R | S6 52.798 | S6 ✓ |
| G | S4 20.517 | S4 ✓ |
| I | S6 49.178 | S6 ✓ |
| rho | HAR 35.746 vs EMP250 41.585 | HAR ✓ |

Final-window DM (one-sided) vs S0 passes the "p < 0.10" requirement for the selected models (R p = 0.0006, G p = 0.0064, I p = 0.0001), so the "no demonstrated advantage" label is correctly not triggered. Final-window 90% Kupiec for the selected models is p = 0.27 / 0.48 / 0.61, so no calibration scalar is required and none is applied ✓.

**Location gate (Val+Final pooled, `eval_location.csv`, row `valfinal`, n = 565).** All four legs fail, so L0 is correctly used:
* OOS R² vs hist-mean -0.0280 (needs > 0; vs zero -0.0239);
* Clark-West t = -0.148, one-sided p = 0.559 (needs < 0.05);
* direction accuracy ridge 0.5009 / logit 0.5080 vs best-constant 0.5292 (binomial p 0.918 / 0.854);
* the top-5-days leg is moot (R² -0.0385, CW p 0.656).

AUC of the logit is 0.499, Brier skill -0.028. I re-ran the gate with the F4/F5 fixes (§1): same conclusion. Hyperparameters (alpha 1000, C 0.01) are the pre-registered grid edges chosen on Dev only; I recomputed the Dev MSE/log-loss grid and it matches the JSON. The Dev window itself looks "significant" (CW p = 0.0001, direction p = 0.0001) but the effect vanishes in Val and Final, which is why the gate is on Val+Final.

**Departures not recorded in DEVIATIONS.md:** see F8 (items 1-10). The recorded post-hoc steps (#15 L1-vs-L0 on Val+Final, #16 override) are disclosed. Note that #15 reuses the Val+Final window that the protocol reserved as test data, which #15 itself labels as weaker evidence.

---

## 6. Task 5 detail: statistical soundness

* **Metrics code.** Kupiec, Christoffersen (independence), Holm (step-down with running max), pinball, coverage, AUC, Clark-West (`adj = (y-f_nest)² - ((y-f_alt)² - (f_nest-f_alt)²)`, one-sided p), exact binomial all check out against my own implementations (Kupiec/DM/pinball matched to 8 digits; DM also matched `statsmodels` HAC OLS with `maxlags=5, use_correction=False`).
* **DM / HLN.** `metrics.py:73` gives `sqrt((n-1)/n)`, the correct HLN factor for h = 1. Pairing it with a 5-lag Bartlett NW variance is a mild hybrid but harmless (n = 317: factor 0.9984), and the t(n-1) reference is conservative. The DM framework is acceptable here because the evaluation sample is much larger than the estimation noise in sigma for S0/S1 and the models are not nested. A Giacomini-White conditional test would be the textbook choice for expanding-window parametric models.
* **Multiple testing.** Holm is applied only within each (target, period) cell over the 6 non-benchmark models. There is no correction across targets (R, G, I, rho), windows, or the many descriptive tables (14 regime rows, location ablations, episode tables, `conditional_day.py`). That is acceptable for the gate (one pre-selected model, three targets: all still significant at Bonferroni ×3), but regime and ablation p-values should be read as exploratory. The location gate is a conjunction of four conditions, so no multiplicity inflation. See F3 for the winner's-curse issue within S1-S6.
* **Directional power.** See F9, F10. With 565 Val+Final observations and a hindsight best-constant null, the directional test is weak and the R² > 0 leg is deliberately hard. "No reliable directional forecast" is the right wording; "no predictability" would not be.
* **Claims the evidence does NOT support (or only partly):**
  1. "Timed volatility models beat the untimed benchmark out of sample" (F2): supported against S0 on pooled Dev+Val and on Final, **not** on Validation alone, and not distinguishable from a one-parameter rescale of S0 or from a trailing-250-day untimed benchmark in Final.
  2. "90% interval coverage was validated" (F7).
  3. A specific advantage of S6 over S1/S4 (F3).
  4. "The shuffled-returns null test shows the pipeline does not generate spurious predictability" is true only for that null (F1).

---

## 7. Task 6: bug list (file:line, what, impact)

| # | File:line | What | Impact |
|---|---|---|---|
| B1 | `location.py:66-69` | RSI, MA20, MA50 on unadjusted close (F4) | 38-98 contaminated rows (some in Val/Final); gate unchanged |
| B2 | `location.py:54`, `location.py:87` | Zero-filled `capmkts1` with `sd+1e-12` standardiser; test |Z| up to 4.8e11 (F5) | Harmless only because weight is exactly 0; gate unchanged |
| B3 | `location.py:55-58` | Comment says beta window <= t-2, code includes t-1 (F6) | None (no leakage) |
| B4 | `common.py:12`, `models.py:98-106` (HAR) | EPS = 1e-8 floor on G² for 125 exact-zero gaps (F12) | <= 0.6% pinball change |
| B5 | `metrics.py:73` | `hln` expression carries a dead `h(h-1)/n` term; fine for h = 1 | None |
| B6 | `location.py:90` | `nan_to_num(nan=0)` silently imputes missing test features; 0 rows affected for t >= 500 on current data | None now; latent |
| B7 | `run_location.py:74-75`, `evaluate.py:53` | `eval_loc` / `eval_target` silently return nothing when n < 30 | None now; latent |
| B8 | `run_location.py:82` | `up = (y > 0)`: an exactly-zero return counts as "down" | negligible |
| B9 | `episodes.py:127` | `share_next_up` counts a missing `next_R` as not-up | negligible (last row only) |
| B10 | `forecast_live.py:133` | Hard-coded "Kupiec p=0.27" in the note (value is correct, but is not computed) | wording (F7) |

No off-by-one found in the walk-forward blocks (`range(MIN_HIST, n, REFIT)`, last partial block handled), the FHS windows, the expanding mean (`cs[idx-1]/idx`), the S0 denominator, or the live-forecast placeholder row. Choice of `np.quantile` default (linear) is used consistently.

**Would the tests catch the leakage types identified?**
* `test_pipeline.py::test_metrics`: validates the metric code; fine.
* `test_models_recover_vol`: checks calibration on synthetic GARCH-t; fine.
* `test_no_lookahead`: catches only look-ahead that reaches beyond the truncation point, on synthetic data without exogenous inputs. It passes with the target leaking into the FHS window (bug1) and with 3 future rows in the HAR training set (bug2). Does not cover S5, `exog_matrix`, the range model or any location code.
* `test_location_null.py`: a Dev-window shuffle null. It would catch an unshifted BSE-own-return feature, but not an unshifted exogenous feature (Nifty, VIX, breadth, volume), not a rolling-window mistake involving exogenous series, and not bonus-adjustment defects (it overwrites `close` with a synthetic path, which also hides F4).
* Recommended replacements: the same-row perturbation harness (F1) plus a bit-for-bit reproduction test of `eval_scale_all.csv` from `forecasts_*.csv`.

---

## 8. What I did not do / limits
* I did not attempt to obtain external price data beyond the dossier's table, so the 2017-2026 history is validated only by internal consistency, the bit-for-bit rebuild from the exchange archive in `data/raw`, and the 64-row dossier match.
* I did not review `src/scenarios.py`, `src/intraday_profile.py`, `src/fetch_*.py`, `src/options_iv.py` beyond a skim (all exploratory/non-gating by the protocol), nor the research dossiers' factual claims.
* The Yahoo 15-minute bars (DEVIATIONS #14, #17, #18) were not re-validated.
* "Run once" for the Final window cannot be proved from git; the sequence is consistent with it (freeze commit before the all-window forecasts).

## 9. Audit scripts (all in `/tmp/audit/`)
`rederive.py`, `rederive2.py` (S0/S1 re-derivation and comparison), `har_indep.py` (S4), `garch_indep.py` (S2/S6), `trunc_scale.py` / `loc_run.py` (truncation and future-garbage tests), `same_day.py` (same-row perturbation; also used with injected bugs via `SRCDIR`/`TAG`, copies in `src_bug1..3`), `loc_adj.py` / `loc_clean.py` / `feat_diag.py` (feature defects), `stats_checks.py` (DM sensitivity, alternative benchmarks, rescaled S0), `size_study.py` (null size of CW and directional tests), `oos_z.py`, `g_floor.py`, `sel_check.py`, and `tests_copy/` (repo tests run against injected bugs).
