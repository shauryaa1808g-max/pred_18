# Specialist A: day-ahead and post-open high / low for NSE:BSE

*Status: PRE-FIXED SECTION WRITTEN BEFORE ANY H/L MODEL RESULT WAS COMPUTED (clock at writing: Thu 15 Oct 2026 about 21:57 IST). The only things looked at before writing it were data facts (row counts, windows, share of days with open == previous close, the stored S6 sigma path being reproduced to 1e-14). The results sections are appended below this one.*

## 0. Pre-fixed variants (decided before looking at results)

**Targets.** Pre-open: Hp = ln(H/P0), Lp = ln(L/P0) with P0 = previous official close, information up to that close only. Post-open: HO = ln(H/O), LO = ln(L/O) with O = official open (NSE pre-open auction price, final at 09:08 IST) as one extra known number; constraints HO >= 0 and LO <= 0 (they hold in all 2,390 sessions by construction of the data check). "First value known pre-open" is read as the official open itself (equivalently the gap G = ln(O/P0)); the 09:00-09:07 indicative price has no history in the repo and is not used.

**Evaluation protocol.** Walk-forward, expanding, target day t evaluated for sessions 750 onward (2020-02-25, exactly as src/eval_hl.py so that all methods are scored on the same days); S6/S0/S1/S4 sigma paths are the project's own (src/models.py, refit every 20 sessions on data strictly before the block). Windows by target date: Development 2020-02-25 to 2024-06-30, Validation 2024-07-01 to 2025-06-30, Final 2025-07-01 onward (to 15 Oct 2026), and a post closing-auction slice from 2026-08-03 (CAS). Loss = mean pinball over the project's 9-level grid (2.5, 5, 10, 25, 50, 75, 90, 95, 97.5%) in log points, also shown in rupees at the current price (x 3,428). Also: central 50% and 90% coverage with Kupiec p, Diebold-Mariano (Harvey-Leybourne-Newbold, lag 5, src/metrics.py), and MAE / median absolute error of the 50% quantile (the "pin-point") in rupees.

**Pre-open variants (target: Hp and Lp; 8 candidates against one baseline).**

| id | what | information used (all dated <= close of t-1) |
|---|---|---|
| P_S6 (BASELINE) | project's OHLC bootstrap: sigma_t = S6 (GARCH(1,1)-t x HAR on gap^2+Garman-Klass) of the close-to-close return R, times the joint trailing-500 standardised residuals of (Hp, Lp) (src/eval_hl.py) | returns, G, GK to t-1 |
| P_EMP250, P_EMP500 | unconditional trailing-250 / 500 empirical quantiles of Hp, Lp (no scaling) | Hp, Lp to t-1 |
| P_S0 | expanding-RMS (constant scale) sigma x same bootstrap | R to t-1 |
| P_S1 | EWMA(0.94) sigma x same bootstrap | R to t-1 |
| P_S4 | HAR on gap^2+GK sigma x same bootstrap | G, GK to t-1 |
| P_RNG | range model: HAR on rho^2, rho = ln(H/L), as scale; bootstrap of (Hp, Lp)/sigma_rho | rho to t-1 |
| P_GK | Garman-Klass model: HAR on GK intraday variance as scale; same bootstrap | GK to t-1 |
| P_DOW | S6 bootstrap with a weekday multiplier; BUILT ONLY IF a screen on Development+Validation sessions (Kruskal-Wallis of ln(rho/sigma_S6), Hp/sigma, Lp/sigma by weekday, Holm over the 3 outcomes) gives Holm p < 0.05. No expiry-day variant: the exchange expiry weekdays changed during the sample and the repo has no verified expiry calendar. | weekday of t |
| (point only) PRICE_STAYS | H = L = P0 | P0 |

**Post-open variants (target: HO and LO; baseline W_I6).**

| id | what | extra information beyond the pre-open set |
|---|---|---|
| W_I6 (BASELINE) | sigma_t = S6 of the open-to-close return I (project's selected intraday model; v = GK) x joint trailing-500 residuals of (HO, LO) | the open is used only as the reference price |
| W_EMP250, W_EMP500 | unconditional trailing empirical quantiles of HO, LO | none |
| W_PRE | the pre-open P_S6 quantiles of Hp, Lp shifted by the known G and clipped at the constraints (H >= O, L <= O); "pre-open information plus the open as a floor/ceiling" | O (09:08) |
| W_I6w | W_I6 with a trailing-1000 window (control for the window used by the pooled variants) | none |
| W_HAR | HAR on GK alone as sigma (control for the next line) | none |
| W_HARz | the same HAR with the gap size z_t = min(\|G_t\| / sigma_t^{S1}, 4) as one extra regressor, sigma^{S1} = EWMA(0.94) scale of R known at t-1 (z_t is known at 09:08 of day t; all other regressors dated <= t-1; parameters refit every 20 sessions on earlier data) | O (09:08) |
| W_SIZE | W_I6w with the residual pool split by gap size z: flat (< 0.25), small (0.25 to 1), large (>= 1), where gap size is in units of sigma^{S1} | O |
| W_SIGN | W_I6w with the pool split by gap sign: down (G/sigma <= -0.25), flat (\|.\| < 0.25), up (>= 0.25) | O |
| W_SZSG | W_I6w with 5 pools: flat, up-small, up-large, down-small, down-large (same cut points) | O |

A pool with fewer than 30 draws falls back to the unsplit pool (the count of fallbacks is reported).

**Pre vs post (question 3).** Because Hp = G + HO exactly, a post-open quantile of HO maps to a quantile of Hp by adding G, so pre-open and post-open versions are scored on the same quantity (ln(H/P0)) with the same pinball loss; pre-open quantiles are also mapped to HO space (minus G, clipped at 0 / 0) as W_PRE.

**Multiple comparisons.** Each family is tested against its baseline on the pooled Validation+Final window with the DM test; family 1 = {P_EMP250, P_EMP500, P_S0, P_S1, P_S4, P_RNG, P_GK, [P_DOW]} x {H, L}; family 2 = {W_EMP250, W_EMP500, W_PRE, W_I6w, W_HAR, W_HARz, W_SIZE, W_SIGN, W_SZSG} x {HO, LO}; family 3 = pre vs post (best-of-W is NOT picked from the results: the comparison is the baseline W_I6 and W_HARz and W_SZSG, 3 x {H, L}); Holm on two-sided p within each family.

**Adoption rule for the live forecast (fixed now).** The baseline stays unless a variant has Holm-adjusted two-sided p < 0.05 in Validation+Final pooled AND a lower mean pinball in Validation and in Final separately (the project's own rule, DEVIATIONS #15). Anything else is reported as a tie or a null. The CAS slice (n about 52) is descriptive only.

**What counts as a null.** A variant that is not significantly better than its baseline after Holm. I will say "tie" when the point estimate favours it but Holm p >= 0.05, and "worse" when the baseline is significantly better.

**Yahoo vs NSE.** Measured separately on the repo's 15-minute sessions (and, if available, the hourly bars): per-session (Yahoo extreme minus NSE official extreme) in rupees. Evaluation targets are the NSE official high / low from the bhavcopy.

**Amendment A1 (made a few minutes after the first write, still before any H/L model result had been computed; no clock time recorded).** The gap size used by W_HARz / W_SIZE / W_SIGN / W_SZSG is normalised by the EWMA(0.94) scale of R (sigma^{S1}, available from session 30) instead of S6 (available only from session 500, which would have left the HAR with about 240 training rows at the first evaluation block). Nothing else changed.


---

## 1. The answer in plain words (Friday 16 Oct 2026; data through the official 15 Oct close Rs 3,428.0; volatility model fitted with sessions through 15 Oct only)

**Before the open** (what you can know tonight; typical daily move sigma = 2.43%):

| | best single guess (median) | typical miss, last 320 sessions | half the time between | nine times in ten between |
|---|---|---|---|---|
| **HIGH** | **Rs 3,475** | Rs 43 on average, Rs 34 half the time | Rs 3,449 to 3,513 (width Rs 63) | Rs 3,421 to 3,591 (width Rs 169) |
| **LOW** | **Rs 3,390** | Rs 48 on average, Rs 32 half the time | Rs 3,352 to 3,419 (width Rs 67) | Rs 3,269 to 3,450 (width Rs 181) |

* "Typical miss" = the out-of-sample mean absolute error of the median (Final window, 1 Jul 2025 to 15 Oct 2026, n = 320), converted to rupees at today's price (Rs 3,428). Its standard error is about Rs 2 (high) and Rs 3 (low).
* **That is the honest precision: about Rs 40 to 50 on either extreme, and no better.** Saying "the high will be yesterday's close" would have missed by Rs 63 (high) and Rs 61 (low) on the same sessions, so the model is better than that, but the simple median of the last 250 sessions misses by almost the same (Rs 44 and Rs 48; the model's advantage in the median is small and borderline for the high and absent for the low, Section 4.3). The model's real gain is in the *shape* of the bands, not in a sharper best guess.
* The 90% bands are wide (Rs 169 and Rs 181). They cannot be narrowed honestly from daily data: they measured 90% coverage 90.3% (high) and 88.8% (low) in the Final window, so narrowing them would simply make them wrong more often. The 50% band (about Rs 63 to 67 wide) was right about half the time (high 46.9%, low 50.3%); that is the tightest statement the data supported.

**Once the NSE pre-open auction fixes the official open at 09:08** (`python3 src/hl_model.py --date 2026-10-16 --open <price>`): knowing the open cuts the typical miss by about a fifth. If the open were flat at Rs 3,428: high median Rs 3,466 (half the time Rs 3,446 to 3,504), low median Rs 3,388 (half the time Rs 3,352 to 3,408); typical miss Rs 35 (high) and Rs 37 (low) instead of Rs 43 and Rs 48. In any case the median high is about **open +1.12%** and the median low about **open -1.16%**; the bands move one-for-one with the open (the gap size and direction add nothing beyond the level, tested in Section 4.2).

**What this is not:** a direction call (nothing here says whether the day closes up or down), a trading rule (no rule was tested here, and the project's own earlier test found that fading the predicted high/low lost money after costs, DEVIATIONS #30), or evidence that the 14 and 15 Oct sessions were well forecast (two days prove nothing, Section 4.7).


---

## 2. What I built

| file | what |
|---|---|
| `src/hl_model.py` | the forecaster (`hl_forecast(date, open_price=None, p0=None)` returns a dict), the CLI, the whole walk-forward evaluation (`--eval`), the same-row leakage tests (`--selftest`) and the check against the project's stored sigma (`--replicate`). No network access. |
| `results/hl_dayahead_2026-10-16.json` | the forecast for Friday 16 Oct: sigma used, pre-open quantiles of the high and low in rupees (5, 10, 25, 50, 75, 90, 95%, also 2.5/97.5), typical miss, band widths, touch probabilities, and post-open tables for opens of -2%, -1%, 0, +1%, +2% vs the previous close |
| `results/hl_eval_preopen.csv`, `hl_eval_postopen.csv` | every variant x target x window: pinball, 50/90% coverage, Kupiec p, tail frequencies and binomial p, miss of the median in rupees (at Rs 3,428, and in traded rupees for the Final and CAS windows), Wilson interval of 90% coverage |
| `results/hl_eval_dm_holm.csv`, `hl_eval_adoption.csv` | Diebold-Mariano (HLN, lag 5) with Holm within each family and window; the pre-fixed adoption rule applied to every variant |
| `results/hl_eval_reliability.csv`, `hl_eval_touchprob.csv`, `hl_eval_byyear.csv` | calibration at every quantile level; probability that the high/low reaches +-0.5/1/2/3% (model vs trailing frequency); pinball by calendar year |
| `results/hl_eval_cas_facts.csv`, `hl_eval_gap_bins.csv`, `hl_eval_dow_screen.csv` | closing-auction-era facts, descriptive high/low-vs-open tables by gap bin, the pre-declared weekday screen |
| `results/hl_eval_twodays.csv` | 14 and 15 Oct as the model would have said at the prior close |
| `results/hl_eval_yahoo_vs_nse*.csv` | Yahoo minus NSE official high/low, rupees |
| `results/hl_eval_predictions.csv`, `hl_eval_replication.csv`, `hl_eval_selftest.csv` | stored daily quantiles of the two live models; replication of the project's coverage; leakage tests |

### Method in one paragraph
Pre-open: the project's selected volatility model S6 (geometric mean of a GARCH(1,1)-t and a HAR on gap^2 + Garman-Klass, refit every 20 sessions on earlier data) gives sigma for the close-to-close return; the forecast distribution of (Hp, Lp) = (ln H/P0, ln L/P0) is sigma times the joint standardised residuals of the last 500 sessions (filtered historical simulation; the project's `eval_hl.py`). Post-open: the same engine with sigma = S6 of the open-to-close return (GARCH on it, HAR on Garman-Klass) and residuals of (HO, LO) = (ln H/O, ln L/O); because the residuals are non-negative / non-positive, the constraints H >= O and L <= O hold automatically and the probability that the open is the high (about 4.2% of sessions pooled Validation+Final) or the low (2.1%) is built in. The reported "pin-point" is the median of each distribution. The live forecast refits the models on all sessions through 15 Oct (a block starting exactly at the forecast session), so it is one step fresher than the walk-forward blocks it was evaluated with.

### What each input is, and when it is known (forecast made for session t)
| input | used by | known at |
|---|---|---|
| official daily bars to t-1 (open, high, low, close) | all | NSE bhavcopy, about 16:34 IST on t-1 (the 15 Oct bar was in `bse_daily_extra.csv` this evening) |
| P0 = official close of t-1 (the closing-auction price since 3 Aug 2026) | all price levels | 15:30 IST on t-1 |
| S6 sigma of R (filter state through t-1, parameters fitted on sessions before the block) | all pre-open variants | close of t-1 |
| trailing 500 standardised (Hp, Lp) or (HO, LO) outcomes of sessions t-500..t-1 | all | close of t-1 |
| official open O of session t (NSE pre-open call-auction price, final at 09:08 IST; the continuous session starts 09:15) | all `W_*` variants (level; gap size only in the gap-conditioned variants) | 09:08 IST on t |
| gap size z = min(abs(G_t) / EWMA-sigma, 4), EWMA sigma from returns to t-1 | W_HARz, W_SIZE, W_SIGN, W_SZSG | 09:08 IST on t |
| weekday of t | P_DOW | calendar |
| nothing from the session t itself (its high, low, close, volume, intraday prints) is used by any variant | | |

Not used, on purpose: the previous US session (S&P 500; the project's validated gap cue is worth about Rs 2 on a median, v2 report Section 4, and the 15 Oct US session has not closed at the 22:00 IST cutoff), implied volatility (only about 460 sessions of history), volume and delivery data.


---

## 3. Windows and sample sizes

Evaluation sessions: 1,640 (25 Feb 2020 to 15 Oct 2026; session 750 onward as in `eval_hl.py`). Development n = 1072 (to 30 Jun 2024), Validation n = 248 (1 Jul 2024 to 30 Jun 2025), pooled Validation+Final n = 568, **Final n = 320** (1 Jul 2025 to 15 Oct 2026; the project's earlier "n = 317" ends 12 Oct, the three later sessions 13, 14, 15 Oct are included here), post closing-auction slice **CAS n = 52** (3 Aug 2026 on; n = 51 if 3 Aug itself is dropped because its previous close was still the old VWAP-type close; the sensitivity rows are in the CSVs and change nothing below).

**Data note (found while converting to rupees).** In `data/processed/bse_daily.csv` only the previous close (`prev`) is bonus-adjusted (on the ex-date); the open / high / low / close levels are the raw traded prices (for example close 4,809.50 on 14 Oct 2024). All log targets are therefore right, but rupee errors in the Development and Validation windows are on a different price level from today. I therefore report rupee misses as "log miss x Rs 3,428" everywhere, and "traded rupees" (raw differences) only for the Final and CAS windows, where the raw levels are the real ones.


---

## 4. Results (all out of sample, expanding walk-forward; n beside every table)

### 4.1 Pre-open: high and low from the previous close (target ln(H/P0), ln(L/P0))

**Final window, n = 320.** Pinball is mean over the 9-level grid in log points x 1e4 (lower is better); "miss of median" is the mean absolute error of the 50% quantile in rupees at Rs 3,428; the last column is the median absolute miss ("half the time within"). `PRICE_STAYS` = predict H = L = P0.

| variant | H: pinball x1e4 | H: 50% cov % | H: 90% cov % (Kupiec p) | H: miss of median Rs (mean ± s.e.) | H: median abs miss Rs | L: pinball x1e4 | L: 50% cov % | L: 90% cov % (Kupiec p) | L: miss of median Rs (mean ± s.e.) | L: median abs miss Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| `P_S6` | 31.15 | 46.9 | 90.3 (0.851) | 42.7 ± 2.2 | 33.6 | 36.58 | 50.3 | 88.8 (0.464) | 47.7 ± 2.9 | 32.2 |
| `P_EMP250` | 32.74 | 50.6 | 91.2 (0.447) | 43.7 ± 2.2 | 35.4 | 36.59 | 51.9 | 91.9 (0.249) | 47.5 ± 2.9 | 33.7 |
| `P_EMP500` | 33.98 | 52.5 | 91.9 (0.249) | 44.0 ± 2.2 | 36.7 | 36.98 | 55.6 | 94.1 (0.0093) | 47.8 ± 2.8 | 34.6 |
| `P_S0` | 34.73 | 52.8 | 91.9 (0.249) | 44.5 ± 2.2 | 39.0 | 37.30 | 56.9 | 94.7 (0.0023) | 48.1 ± 2.8 | 37.4 |
| `P_S1` | 31.33 | 47.2 | 88.8 (0.464) | 42.8 ± 2.3 | 32.4 | 36.80 | 47.8 | 88.1 (0.276) | 47.8 ± 3.0 | 33.1 |
| `P_S4` | 31.08 | 48.8 | 90.0 (1.000) | 42.5 ± 2.3 | 32.2 | 36.66 | 50.6 | 88.4 (0.362) | 47.8 ± 2.9 | 32.4 |
| `P_RNG` | 31.08 | 47.8 | 89.4 (0.712) | 42.3 ± 2.3 | 32.9 | 36.49 | 50.6 | 87.8 (0.206) | 47.4 ± 2.9 | 32.6 |
| `P_GK` | 30.97 | 47.2 | 89.7 (0.853) | 42.3 ± 2.2 | 32.9 | 36.45 | 50.9 | 88.4 (0.362) | 47.6 ± 2.9 | 32.9 |
| `P_DOW` | 31.34 | 46.9 | 89.1 (0.581) | 43.0 ± 2.3 | 31.7 | 36.78 | 49.7 | 89.1 (0.581) | 47.9 ± 2.9 | 32.1 |
| `PRICE_STAYS` | - | - | - | 62.9 ± 3.0 | 51.6 | - | - | - | 61.3 ± 3.4 | 42.6 |

How the project's S6 baseline compares across all windows (pinball x1e4 / 90% coverage / miss of the median in Rs at 3,428):

| variant | target | dev (n=1072): pinball x1e4 / 90% cov / miss | val (n=248): pinball x1e4 / 90% cov / miss | final (n=320): pinball x1e4 / 90% cov / miss | cas (n=52): pinball x1e4 / 90% cov / miss |
|---|---|---|---|---|---|
| `P_S6` | H | 43.5 / 90% / Rs 54 | 52.1 / 89% / Rs 66 | 31.2 / 90% / Rs 43 | 31.2 / 85% / Rs 44 |
| `P_S6` | L | 36.2 / 89% / Rs 48 | 47.0 / 88% / Rs 64 | 36.6 / 89% / Rs 48 | 34.0 / 88% / Rs 48 |
| `P_EMP250` | H | 45.8 / 87% / Rs 58 | 53.3 / 88% / Rs 69 | 32.7 / 91% / Rs 44 | 31.6 / 85% / Rs 44 |
| `P_EMP250` | L | 38.9 / 87% / Rs 50 | 47.4 / 88% / Rs 63 | 36.6 / 92% / Rs 48 | 32.9 / 88% / Rs 48 |
| `P_S0` | H | 45.0 / 90% / Rs 57 | 53.7 / 87% / Rs 69 | 34.7 / 92% / Rs 45 | 34.4 / 87% / Rs 45 |
| `P_S0` | L | 38.4 / 90% / Rs 49 | 47.7 / 86% / Rs 63 | 37.3 / 95% / Rs 48 | 33.0 / 94% / Rs 48 |

**Diebold-Mariano against the baseline `P_S6`** (family 1; positive gain = variant better; two-sided p; Holm within window over the 16 tests of the family; CAS is descriptive, no Holm):

| variant | target | valfinal n=568: pinball gain vs baseline | final n=320: pinball gain vs baseline | cas n=52: pinball gain vs baseline |
|---|---|---|---|---|
| `P_EMP250` | H | -3.6% (p 0.015, Holm 0.191) | -5.1% (p 0.0009, Holm 0.013) | -1.2% (p 0.196) |
| `P_EMP250` | L | -0.5% (p 0.672, Holm 1.000) | -0.0% (p 0.989, Holm 1.000) | +3.2% (p 0.047) |
| `P_EMP500` | H | -6.2% (p 0.0015, Holm 0.022) | -9.1% (p <0.0001, Holm <0.0001) | -9.7% (p 0.0002) |
| `P_EMP500` | L | -1.9% (p 0.193, Holm 1.000) | -1.1% (p 0.466, Holm 1.000) | +3.0% (p 0.354) |
| `P_S0` | H | -6.8% (p 0.0001, Holm 0.0018) | -11.5% (p <0.0001, Holm <0.0001) | -10.3% (p 0.0001) |
| `P_S0` | L | -1.8% (p 0.184, Holm 1.000) | -2.0% (p 0.268, Holm 1.000) | +3.0% (p 0.356) |
| `P_S1` | H | -1.6% (p 0.0099, Holm 0.138) | -0.6% (p 0.429, Holm 1.000) | -0.6% (p 0.762) |
| `P_S1` | L | -0.3% (p 0.504, Holm 1.000) | -0.6% (p 0.371, Holm 1.000) | -2.1% (p 0.107) |
| `P_S4` | H | +0.6% (p 0.311, Holm 1.000) | +0.2% (p 0.710, Holm 1.000) | +0.1% (p 0.910) |
| `P_S4` | L | -0.5% (p 0.328, Holm 1.000) | -0.2% (p 0.530, Holm 1.000) | -1.3% (p 0.093) |
| `P_RNG` | H | +0.2% (p 0.750, Holm 1.000) | +0.2% (p 0.821, Holm 1.000) | +0.4% (p 0.750) |
| `P_RNG` | L | +0.4% (p 0.479, Holm 1.000) | +0.2% (p 0.603, Holm 1.000) | -0.1% (p 0.957) |
| `P_GK` | H | +0.7% (p 0.315, Holm 1.000) | +0.6% (p 0.540, Holm 1.000) | +0.6% (p 0.542) |
| `P_GK` | L | +0.2% (p 0.730, Holm 1.000) | +0.4% (p 0.449, Holm 1.000) | -0.7% (p 0.257) |
| `P_DOW` | H | -1.2% (p 0.110, Holm 1.000) | -0.6% (p 0.498, Holm 1.000) | -1.0% (p 0.494) |
| `P_DOW` | L | -1.4% (p 0.027, Holm 0.318) | -0.5% (p 0.407, Holm 1.000) | -2.5% (p 0.127) |

Reading it:
* **Nothing beats the baseline.** No variant meets the pre-fixed adoption rule (`results/hl_eval_adoption.csv`: adopted = none). The S4, range-model (RNG) and Garman-Klass (GK) scales are statistical ties with S6 (gains of -0.5% to +0.7% in pooled Validation+Final and in Final, every Holm p = 1.0). The live pre-open model therefore stays `P_S6`.
* **For the high, the volatility timing helps against unscaled history; for the low it does not.** Against S0 (constant scale) and the 500-day empirical quantiles the baseline is better for the high (Final Holm <0.0001 and <0.0001; pooled Validation+Final Holm 0.0018 and 0.022); against the 250-day empirical quantiles it is better for the high in Final (Holm 0.013) but not in pooled Validation+Final (Holm 0.191, a tie). For the low every comparison is a tie (|gain| below 2%, all Holm p = 1.0). By year, S6 has the lower high-pinball than EMP250 in every calendar year 2020 to 2026 (`hl_eval_byyear.csv`), and for the low it wins clearly in 2020 to 2023 and is level or marginally better after (2026: EMP250 slightly better).
* **Day of week.** The pre-declared weekday screen (Development+Validation, n = 1318) found that Monday lows are deeper (mean Lp/sigma -0.70 on Mondays vs -0.56 on Fridays and -0.47 to -0.55 on Tue to Thu; Kruskal-Wallis p = 0.0053, Holm over the 3 outcomes 0.016), so by the pre-fixed rule the `P_DOW` variant was built. It did **not** improve the forecasts out of sample (low: -1.4% pooled, p 0.027 unadjusted against it, Holm 0.318; high -1.2%). Friday, the target day, is average on all three statistics anyway. Expiry-day effects were not tested (no verified expiry calendar in the repo; the expiry weekdays changed during the sample).

### 4.2 Post-open: high and low from the official open (target ln(H/O), ln(L/O))

**Final window, n = 320.** `OPEN_STAYS` = predict H = L = O. Note on the 90% coverage column for HO: HO is never negative and equals zero on 4.1% of Final sessions (the open is the day's high), so the model's 5% quantile of HO is about zero and the interval [q5, q95] is effectively one-sided. Its correct coverage target is then about 95%, not 90%, and the Kupiec test against 90% is the wrong test for HO. The meaningful tail check is the upper-tail exceedance (below).

| variant | HO: pinball x1e4 | HO: 50% cov % | HO: 90% cov % (Kupiec p) | HO: miss of median Rs (mean ± s.e.) | HO: median abs miss Rs | LO: pinball x1e4 | LO: 50% cov % | LO: 90% cov % (Kupiec p) | LO: miss of median Rs (mean ± s.e.) | LO: median abs miss Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| `W_I6` | 23.85 | 49.4 | 95.0 (0.0011) | 34.8 ± 1.8 | 29.1 | 28.03 | 50.3 | 89.4 (0.712) | 37.4 ± 2.6 | 26.6 |
| `W_EMP250` | 25.01 | 50.0 | 92.2 (0.177) | 35.4 ± 1.7 | 31.2 | 28.05 | 49.1 | 90.3 (0.851) | 37.6 ± 2.5 | 28.3 |
| `W_EMP500` | 26.24 | 55.0 | 96.9 (<0.0001) | 35.7 ± 1.6 | 31.9 | 28.60 | 53.1 | 92.2 (0.177) | 38.2 ± 2.4 | 30.4 |
| `W_PRE` | 29.35 | 46.9 | 90.3 (0.851) | 40.5 ± 2.0 | 33.4 | 34.44 | 50.3 | 88.8 (0.464) | 45.8 ± 2.8 | 31.4 |
| `W_I6w` | 24.18 | 48.4 | 92.2 (0.177) | 34.6 ± 1.7 | 29.7 | 28.03 | 50.0 | 89.7 (0.853) | 37.4 ± 2.6 | 26.8 |
| `W_HAR` | 23.73 | 49.7 | 94.1 (0.0093) | 34.4 ± 1.7 | 28.3 | 28.22 | 51.6 | 89.7 (0.853) | 37.7 ± 2.6 | 26.2 |
| `W_HARz` | 23.57 | 49.4 | 94.1 (0.0093) | 34.1 ± 1.7 | 28.1 | 28.41 | 50.9 | 89.4 (0.712) | 37.9 ± 2.6 | 27.6 |
| `W_SIZE` | 23.99 | 47.2 | 95.0 (0.0011) | 34.2 ± 1.8 | 29.0 | 27.97 | 50.0 | 89.4 (0.712) | 37.3 ± 2.6 | 24.6 |
| `W_SIGN` | 24.09 | 47.2 | 94.1 (0.0093) | 34.2 ± 1.7 | 29.0 | 28.07 | 50.6 | 89.4 (0.712) | 37.5 ± 2.6 | 24.9 |
| `W_SZSG` | 23.97 | 46.9 | 94.4 (0.0048) | 34.2 ± 1.8 | 29.0 | 28.12 | 50.6 | 89.1 (0.581) | 37.5 ± 2.6 | 24.8 |
| `OPEN_STAYS` | - | - | - | 51.3 ± 2.6 | 40.7 | - | - | - | 59.0 ± 3.2 | 45.2 |

Windows (pinball x1e4 / 90% coverage / miss of the median in Rs at 3,428):

| variant | target | dev (n=1072): pinball x1e4 / 90% cov / miss | val (n=248): pinball x1e4 / 90% cov / miss | final (n=320): pinball x1e4 / 90% cov / miss | cas (n=52): pinball x1e4 / 90% cov / miss |
|---|---|---|---|---|---|
| `W_I6` | HO | 36.9 / 91% / Rs 48 | 43.2 / 91% / Rs 57 | 23.9 / 95% / Rs 35 | 22.3 / 88% / Rs 35 |
| `W_I6` | LO | 30.1 / 93% / Rs 42 | 34.7 / 90% / Rs 49 | 28.0 / 89% / Rs 37 | 25.9 / 87% / Rs 38 |
| `W_EMP250` | HO | 38.9 / 89% / Rs 51 | 44.6 / 93% / Rs 59 | 25.0 / 92% / Rs 35 | 22.4 / 87% / Rs 35 |
| `W_EMP250` | LO | 32.7 / 90% / Rs 43 | 35.5 / 90% / Rs 49 | 28.1 / 90% / Rs 38 | 25.2 / 88% / Rs 38 |

**Diebold-Mariano against the baseline `W_I6`** (family 2; Holm within window over the 18 tests):

| variant | target | valfinal n=568: pinball gain vs baseline | final n=320: pinball gain vs baseline | cas n=52: pinball gain vs baseline |
|---|---|---|---|---|
| `W_EMP250` | HO | -4.0% (p 0.018, Holm 0.269) | -4.8% (p 0.0030, Holm 0.042) | -0.5% (p 0.672) |
| `W_EMP250` | LO | -1.2% (p 0.353, Holm 1.000) | -0.1% (p 0.962, Holm 1.000) | +2.6% (p 0.183) |
| `W_EMP500` | HO | -6.6% (p 0.0014, Holm 0.023) | -10.0% (p <0.0001, Holm <0.0001) | -10.0% (p 0.0011) |
| `W_EMP500` | LO | -3.1% (p 0.085, Holm 1.000) | -2.0% (p 0.322, Holm 1.000) | +0.8% (p 0.865) |
| `W_PRE` | HO | -18.3% (p <0.0001, Holm <0.0001) | -23.0% (p 0.0009, Holm 0.013) | -34.9% (p 0.023) |
| `W_PRE` | LO | -24.4% (p <0.0001, Holm <0.0001) | -22.9% (p <0.0001, Holm 0.0002) | -22.7% (p 0.046) |
| `W_I6w` | HO | -0.6% (p 0.037, Holm 0.516) | -1.4% (p 0.0005, Holm 0.0080) | -1.9% (p 0.0067) |
| `W_I6w` | LO | +0.1% (p 0.335, Holm 1.000) | -0.0% (p 0.960, Holm 1.000) | -0.0% (p 0.990) |
| `W_HAR` | HO | +0.3% (p 0.615, Holm 1.000) | +0.5% (p 0.319, Holm 1.000) | -0.8% (p 0.520) |
| `W_HAR` | LO | -0.8% (p 0.190, Holm 1.000) | -0.7% (p 0.213, Holm 1.000) | -1.5% (p 0.039) |
| `W_HARz` | HO | +1.1% (p 0.139, Holm 1.000) | +1.2% (p 0.090, Holm 1.000) | -1.3% (p 0.262) |
| `W_HARz` | LO | -1.4% (p 0.046, Holm 0.601) | -1.4% (p 0.037, Holm 0.482) | -1.4% (p 0.261) |
| `W_SIZE` | HO | +0.4% (p 0.512, Holm 1.000) | -0.6% (p 0.473, Holm 1.000) | -3.8% (p 0.046) |
| `W_SIZE` | LO | +0.3% (p 0.269, Holm 1.000) | +0.2% (p 0.684, Holm 1.000) | -1.0% (p 0.534) |
| `W_SIGN` | HO | +0.3% (p 0.690, Holm 1.000) | -1.0% (p 0.291, Holm 1.000) | -3.6% (p 0.205) |
| `W_SIGN` | LO | +0.1% (p 0.805, Holm 1.000) | -0.1% (p 0.816, Holm 1.000) | -1.0% (p 0.547) |
| `W_SZSG` | HO | +0.4% (p 0.549, Holm 1.000) | -0.5% (p 0.549, Holm 1.000) | -2.0% (p 0.414) |
| `W_SZSG` | LO | +0.0% (p 0.963, Holm 1.000) | -0.3% (p 0.573, Holm 1.000) | -1.3% (p 0.417) |

Reading it:
* **No gap-conditioned variant beats the baseline** (size bins, sign, size x sign, or the gap size as a HAR regressor: gains between -1.4% and +1.2% in pooled Validation+Final and in Final, every Holm p = 1.0 or at best 0.48; in CAS, n = 52, they are 0.5% to 4% worse, unadjusted). Knowing *how big* the gap is, or its direction, did not change the shape of the high/low distribution beyond what the open price already does (it moves the level one-for-one). The descriptive medians by gap bin (Section 4.8) point the same way: after a small gap-up the median high is a little farther above the open (1.75% vs 1.14% on flat opens), but the forecast built on that did not win out of sample. The large-gap bins have 7 to 12 sessions in Validation+Final and 1 each in CAS: nothing can be said about them.
* **Using the open only as a floor/ceiling on the pre-open distribution (`W_PRE`) is much worse** than modelling the open-to-extreme move (pinball -18% and -24% pooled, Holm <0.0001 and <0.0001).
* The unscaled 500-day history is worse for HO (Holm 0.023 pooled); the 1,000-day window for the baseline (`W_I6w`) is worse for HO in Final (Holm 0.0080), which is why the 500-day window is kept. The volatility model's advantage over the plain trailing 250-day quantiles is significant for HO in Final (Holm 0.042) but a tie for LO (p 0.962). The live post-open model stays `W_I6`.

### 4.3 The pin-point (median) and its honest miss

Difference in the absolute error of the median (positive gain = first model better; family 4/5/6):

| comparison | target | pooled Val+Final (n = 568) | Final (n = 320) | CAS (n = 52) |
|---|---|---|---|---|
| `P_S6` median vs 'price stays' (H = L = P0) | H | +33.2% (p <0.0001) | +32.1% (p <0.0001) | +23.5% (p 0.0071) |
| `P_S6` median vs 'price stays' (H = L = P0) | L | +19.8% (p <0.0001) | +22.2% (p <0.0001) | +24.2% (p 0.0001) |
| `P_EMP250` median vs 'price stays' | H | +30.9% (p <0.0001) | +30.5% (p <0.0001) | +22.7% (p 0.017) |
| `P_EMP250` median vs 'price stays' | L | +20.4% (p <0.0001) | +22.4% (p <0.0001) | +24.6% (p 0.0001) |
| `P_S6` median vs `P_EMP250` median | H | +3.4% (p 0.019) | +2.3% (p 0.086) | +1.1% (p 0.502) |
| `P_S6` median vs `P_EMP250` median | L | -0.8% (p 0.262) | -0.3% (p 0.759) | -0.4% (p 0.705) |
| `W_I6` median vs 'open stays' | HO | +32.1% (p <0.0001) | +32.1% (p <0.0001) | +25.7% (p 0.0073) |
| `W_I6` median vs 'open stays' | LO | +35.6% (p <0.0001) | +36.5% (p <0.0001) | +33.5% (p <0.0001) |
| `W_I6` median vs `P_S6` median (open known vs not) | H | +16.0% (p <0.0001) | +18.5% (p 0.0004) | +19.4% (p 0.053) |
| `W_I6` median vs `P_S6` median (open known vs not) | L | +22.3% (p <0.0001) | +21.5% (p <0.0001) | +21.5% (p 0.016) |

* The median beats "the extreme stays at the reference price" by about 20% to 37% in absolute miss, in every window (p < 0.001 in Final and pooled Validation+Final; p between 0.0001 and 0.007 in CAS).
* The model's pre-open median is **only marginally better than the plain trailing-250-day median for the high and no better for the low** (high: +3.4% pooled, p 0.019, Holm 0.039, but +2.3% and p 0.086 in Final, so borderline; low: a tie). So the single "best guess" number is about as good as a trailing median; what the volatility model adds is bands that widen and narrow with the market (Section 4.5).
* Knowing the open improves the median clearly: absolute miss +18.5% (high) and +21.5% (low) in Final, both Holm p below 0.001, and in CAS +19.4% / +21.5% (n = 52, p 0.053 / 0.016).

### 4.4 Does knowing the open improve the high/low distributions? (question 3, family 3)

Both models are scored on the same quantity ln(H/P0) (the post-open quantile of HO plus the known gap G is a quantile of ln(H/P0); pinball is translation-invariant, so the two losses are directly comparable). Pinball gain of the post-open model over the pre-open `P_S6` (family 3, Holm over the 6 tests of each window):

| variant | target | valfinal n=568: pinball gain vs baseline | final n=320: pinball gain vs baseline | cas n=52: pinball gain vs baseline |
|---|---|---|---|---|
| `W_I6` | H | +19.8% (p <0.0001, Holm <0.0001) | +23.4% (p <0.0001, Holm <0.0001) | +28.4% (p 0.014) |
| `W_I6` | L | +24.8% (p <0.0001, Holm <0.0001) | +23.4% (p <0.0001, Holm <0.0001) | +24.0% (p 0.013) |
| `W_HARz` | H | +20.7% (p <0.0001, Holm <0.0001) | +24.3% (p <0.0001, Holm <0.0001) | +27.5% (p 0.018) |
| `W_HARz` | L | +23.7% (p <0.0001, Holm <0.0001) | +22.3% (p <0.0001, Holm <0.0001) | +23.0% (p 0.011) |
| `W_SZSG` | H | +20.1% (p <0.0001, Holm <0.0001) | +23.1% (p <0.0001, Holm <0.0001) | +27.0% (p 0.015) |
| `W_SZSG` | L | +24.8% (p <0.0001, Holm <0.0001) | +23.1% (p <0.0001, Holm <0.0001) | +23.0% (p 0.025) |

| Final (n = 320) | pre-open `P_S6` | post-open `W_I6` | change |
|---|---|---|---|
| high: pinball x1e4 / miss of median (Rs) / half the time within | 31.15 / 42.7 / 33.6 | 23.85 / 34.8 / 29.1 | -23% / Rs -7.9 / Rs -4.4 |
| low: pinball x1e4 / miss of median (Rs) / half the time within | 36.58 / 47.7 / 32.2 | 28.03 / 37.4 / 26.6 | -23% / Rs -10.3 / Rs -5.6 |

**Yes, clearly.** The gain is 20% (high) and 25% (low) in pinball pooled over Validation+Final, 23% and 23% in Final, and 28% and 24% in CAS (p 0.014 and 0.013, n = 52), all Holm p below 0.001 outside CAS. In rupees: the typical miss of the median falls by about Rs 8 (high) and Rs 10 (low). Almost all of the improvement comes from the open price itself, i.e. from having the opening gap out of the way; the gap-conditioned variants add nothing on top (Section 4.2). The comparison is mechanical in one respect: the pre-open forecast must also guess the gap, which is the part the open removes.

### 4.5 Calibration: are the bands what they claim?

Share of outcomes at or below each model quantile (nominal 2.5, 5, 10, 25, 50, 75, 90, 95, 97.5%), pre-open `P_S6` and post-open `W_I6`; 90% and 50% central coverage with the Kupiec p are in the tables above.

| model | target | window | n | 2.5 | 5 | 10 | 25 | 50 | 75 | 90 | 95 | 97.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `P_S6` | H | final | 320 | 3.1 | 7.2 | 15.0 | 29.1 | 53.4 | 75.9 | 92.2 | 97.5 | 99.4 |
| `P_S6` | H | valfinal | 568 | 3.7 | 7.0 | 13.6 | 29.2 | 53.5 | 76.4 | 91.7 | 96.7 | 99.1 |
| `P_S6` | L | final | 320 | 2.8 | 5.0 | 10.6 | 26.9 | 50.0 | 77.2 | 90.0 | 93.8 | 97.8 |
| `P_S6` | L | valfinal | 568 | 2.3 | 5.6 | 11.3 | 26.8 | 49.1 | 76.2 | 89.6 | 93.8 | 97.4 |
| `P_S6` | H | cas | 52 | 7.7 | 15.4 | 23.1 | 32.7 | 50.0 | 73.1 | 92.3 | 100.0 | 100.0 |
| `P_S6` | L | cas | 52 | 5.8 | 5.8 | 17.3 | 40.4 | 55.8 | 80.8 | 94.2 | 94.2 | 98.1 |
| `W_I6` | HO | final | 320 | 4.1 | 5.0 | 10.3 | 26.2 | 50.3 | 75.6 | 91.9 | 97.5 | 99.1 |
| `W_I6` | LO | final | 320 | 4.4 | 5.9 | 10.3 | 26.6 | 48.1 | 76.9 | 90.9 | 95.3 | 98.1 |
| `W_I6` | HO | cas | 52 | 5.8 | 9.6 | 19.2 | 30.8 | 51.9 | 69.2 | 88.5 | 98.1 | 100.0 |
| `W_I6` | LO | cas | 52 | 5.8 | 5.8 | 9.6 | 32.7 | 50.0 | 73.1 | 92.3 | 92.3 | 96.2 |

* **Low (pre-open) is well calibrated** in Final (median 50.0%, 5% / 95% quantiles 5.0% / 93.8%, 90% coverage 88.8%, Wilson 95% interval 85% to 92%).
* **High (pre-open) runs a little high and too wide at the top**: 53.4% of Final highs were below the model's median (53.5% pooled Validation+Final), only 2.5% were above its 95% quantile (nominal 5%; binomial p 0.039) and 7.2% below its 5% quantile. Roughly, the high's median is about Rs 4 too high and its top tail too long. This is small next to the typical miss and I did not correct it (a recalibration was not in the pre-fixed list).
* **50% bands:** coverage in Final was 46.9% (high) and 50.3% (low); in CAS only 40.4% and 40.4% (n = 52; Kupiec p 0.164 and 0.164). The project already noted that 50% intervals ran narrow (v2 report, Section 3.2).
* **Post-open `W_I6`:** 50% coverage 49.4% / 50.3% in Final; the upper tail of HO is too long in Final (only 2.5% above the 95% quantile, binomial p 0.039; Development 5.2%, Validation 4.8%, so a Final-window feature); LO is fine (5.9% below q5, 4.7% above q95).

**Probabilities that the high / low reaches a level** (the numbers behind "chance the high gets +1% / +2%"): mean predicted vs observed frequency, Brier score of the model vs the trailing 500-day frequency, Final window n = 320 (`hl_eval_touchprob.csv`):

| model | event | mean predicted | observed | Brier model | Brier trailing-500 freq | DM p (two-sided) |
|---|---|---|---|---|---|---|
| `P_S6` | H reaches +0.5% | 80.9% | 78.4% | 0.170 | 0.172 | 0.189 |
| `P_S6` | L reaches -0.5% | 67.8% | 71.6% | 0.206 | 0.204 | 0.185 |
| `W_I6` | HO reaches +0.5% | 74.7% | 73.8% | 0.194 | 0.197 | 0.161 |
| `W_I6` | LO reaches -0.5% | 78.6% | 80.9% | 0.156 | 0.155 | 0.577 |
| `P_S6` | H reaches +1% | 64.1% | 59.7% | 0.242 | 0.250 | 0.040 |
| `P_S6` | L reaches -1% | 53.8% | 55.0% | 0.252 | 0.250 | 0.455 |
| `W_I6` | HO reaches +1% | 55.6% | 55.0% | 0.249 | 0.255 | 0.187 |
| `W_I6` | LO reaches -1% | 58.7% | 59.7% | 0.237 | 0.244 | 0.164 |
| `P_S6` | H reaches +2% | 37.8% | 36.2% | 0.230 | 0.240 | 0.045 |
| `P_S6` | L reaches -2% | 29.1% | 29.7% | 0.212 | 0.214 | 0.608 |
| `W_I6` | HO reaches +2% | 29.6% | 31.9% | 0.218 | 0.224 | 0.269 |
| `W_I6` | LO reaches -2% | 29.7% | 31.9% | 0.220 | 0.223 | 0.577 |
| `P_S6` | H reaches +3% | 20.6% | 18.8% | 0.150 | 0.167 | 0.0015 |
| `P_S6` | L reaches -3% | 16.3% | 16.6% | 0.141 | 0.140 | 0.649 |
| `W_I6` | HO reaches +3% | 15.9% | 13.8% | 0.119 | 0.130 | 0.0029 |
| `W_I6` | LO reaches -3% | 15.7% | 14.1% | 0.124 | 0.128 | 0.224 |

The predicted frequencies are within about 4.5 points of the observed ones everywhere; the model beats the plain trailing frequency clearly only for the high reaching +3% (pre-open p 0.0015, post-open p 0.0029; Holm over the 16 Final tests 0.024 and 0.044) and is otherwise a tie (the pre-open high at +1% and +2% has unadjusted p 0.04 and does not survive Holm). These probabilities inherit the 4.5 findings (the high is a little over-predicted); they are the one place where "probability of a big move up" has real, if modest, support.

### 4.6 Post closing-auction slice (since 3 Aug 2026, n = 52)

* Facts (`hl_eval_cas_facts.csv`): the open equals the previous close on 17.3% of CAS sessions vs 6.4% in the 250 sessions before (median gap 0.00% vs 0.22%); the high never reaches the previous close on 17.3% of days vs 7.6%; mean daily return -0.12% vs +0.14% (a drawdown period); median high/low vs P0 +1.20% / -1.50% (before: +1.49% / -1.14%); median daily range 2.92% vs 2.93% (unchanged). The official close equals the official high in 3.8% of CAS sessions (2 of 52) and never the low; before the auction it could not (the old close was a 30-minute VWAP).
* Performance of the baselines (table in 4.1/4.2): `P_S6` pre-open miss of the median Rs 44 (high) / Rs 48 (low) with s.e. about Rs 4 / Rs 5: no different from Final. The post-open model `W_I6` missed by Rs 35 / Rs 38.
* **Suggestive only (n = 52, one drawdown episode):** the 50% bands covered 40.4% (pre-open, both sides) and the pre-open high fell below its own 5% quantile on 15.4% of days (8 of 52; expected 2.6; binomial p 0.0041). In this regime the lower tail of the high is fatter than modelled (more days when the stock never rallies far above the previous close). The high's median itself was not biased (50% below it). I did not adjust the live forecast for this, because it is 52 sessions overlapping a drawdown, not pre-fixed, and the sign of the effect could reverse. It is a reason to treat the lower end of the pre-open HIGH band (Rs 3,421 to 3,449) as more likely than the table says.

### 4.7 14 and 15 Oct as the model would have said at the prior close (not evidence of skill)

Production function `hl_forecast(day)` with only sessions before `day`; "open known" uses the official open (14 Oct: Rs 3,375.4 = previous close; 15 Oct: Rs 3,342.0). `hl_eval_twodays.csv`.

| session | side | phase | realised | q5 | q25 | median | q75 | q95 | miss of median Rs | inside 50% / 90% |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-14 | high | pre_open | 3,408.3 | 3,369 | 3,397 | 3,423 | 3,460 | 3,538 | -14.3 | yes / yes |
| 2026-10-14 | high | post_open | 3,408.3 | 3,376 | 3,393 | 3,413 | 3,451 | 3,515 | -5.1 | yes / yes |
| 2026-10-14 | low | pre_open | 3,320.0 | 3,216 | 3,298 | 3,337 | 3,366 | 3,397 | -17.1 | yes / yes |
| 2026-10-14 | low | post_open | 3,320.0 | 3,221 | 3,300 | 3,335 | 3,355 | 3,373 | -15.2 | yes / yes |
| 2026-10-15 | high | pre_open | 3,445.0 | 3,332 | 3,358 | 3,382 | 3,417 | 3,491 | +62.8 | no / yes |
| 2026-10-15 | high | post_open | 3,445.0 | 3,343 | 3,359 | 3,378 | 3,413 | 3,475 | +67.0 | no / yes |
| 2026-10-15 | low | pre_open | 3,315.2 | 3,188 | 3,266 | 3,302 | 3,329 | 3,359 | +13.1 | yes / yes |
| 2026-10-15 | low | post_open | 3,315.2 | 3,195 | 3,270 | 3,304 | 3,323 | 3,339 | +11.4 | yes / yes |

Eight forecast-vs-actual comparisons: all inside the 90% band, six inside the 50% band; the two misses were the 15 Oct high (3,445.0 against a pre-open median of 3,382: Rs +63; between the 75% and 90% quantiles, a rally from a near-flat open, +0.12% gap, to a Rs 3,428 close, +2.7% on the day) and its post-open version (Rs +67). Two sessions cannot show skill or its absence; the evidence is the 320-session walk-forward above.

### 4.8 Descriptive: where the extremes sit relative to the open, by gap bin (not a forecast; Validation+Final, `hl_eval_gap_bins.csv`)

| gap bin (in EWMA sigmas) | n | median high above open % | p25 / p75 | median low below open % | p25 / p75 | open is the high | open is the low |
|---|---|---|---|---|---|---|---|
| flat (|gap| < 0.25 sigma) | 385 | 1.14 | 0.48 / 2.36 | -1.49 | -2.70 / -0.76 | 5% | 2% |
| gap up, small (0.25-1 sigma) | 108 | 1.75 | 0.75 / 2.53 | -1.16 | -2.34 / -0.58 | 2% | 3% |
| gap up, large (>= 1 sigma) | 12 | 2.35 | 1.56 / 2.88 | -1.39 | -2.10 / -0.50 | 8% | 8% |
| gap down, small | 56 | 1.70 | 0.95 / 3.54 | -1.37 | -2.63 / -0.67 | 2% | 2% |
| gap down, large | 7 | 4.41 | 1.37 / 4.85 | -0.99 | -1.99 / -0.22 | 0% | 14% |

Small gaps are the norm (flat or small bins hold 549 of 568 sessions). The open is the day's high on about 4% of sessions and the day's low on about 2%, so the open is the day's high or low on only about 1 session in 16 (6%).

### 4.9 Yahoo / chart extremes versus the NSE official high and low

The forecasts and all scores are for the **NSE official** high and low (bhavcopy). A chart built on Yahoo data differs by a few rupees (`hl_eval_yahoo_vs_nse_summary.csv`; Yahoo minus NSE):

| source | extreme | sessions | identical to the paisa | mean Rs | median Rs | mean abs Rs | 90th pct abs Rs | 99th pct abs Rs | max abs Rs | > Rs 5 / > Rs 10 | Yahoo inside NSE range |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15-minute bars (18 Aug to 15 Oct 2026) | high | 39 | 36% | -0.89 | -0.20 | 0.89 | 2.6 | 4.8 | 5.3 | 1 / 0 | 100.0% |
| 15-minute bars (18 Aug to 15 Oct 2026) | low | 39 | 21% | +1.05 | +0.70 | 1.05 | 2.7 | 4.4 | 4.5 | 0 / 0 | 100.0% |
| hourly bars (23 May 2025 to 15 Oct 2026) | high | 333 | 35% | -1.12 | -0.20 | 1.19 | 2.3 | 15.2 | 46.4 | 15 / 6 | 99.4% |
| hourly bars (23 May 2025 to 15 Oct 2026) | low | 333 | 25% | +1.31 | +0.50 | 1.39 | 3.1 | 12.3 | 54.7 | 20 / 5 | 99.7% |

So the Yahoo high is typically Rs 0.9 to 1.1 *lower* than the NSE high on average (median Rs 0.2) and the Yahoo low about Rs 1.1 to 1.3 *higher* than the NSE low; Yahoo is almost always inside the NSE range (missed extreme ticks). The "up to about Rs 4" in `docs/INPUT_AUDIT.md` holds for the 15-minute sessions at the 99th percentile (Rs 4.8 / 4.4, single maxima Rs 5.3 / 4.5); the hourly feed has rare outliers (maximum Rs 46 high, Rs 55 low; 6 and 5 sessions over Rs 10 of 333). Practical reading: if you compare my numbers with a Yahoo-based chart, expect the chart's high to read a rupee or two lower and its low a rupee or two higher; compared with the typical model miss (Rs 35 to 50) this is small but it is not zero. The hourly comparison uses only sessions from the bonus ex-date 23 May 2025 on, because Yahoo back-adjusts earlier prices while the repo's OHLC levels are raw.

### 4.10 Checks that the pipeline is clean

* **Same-row leakage tests** (`python3 src/hl_model.py --selftest`, output `results/hl_eval_selftest.csv`): changing one session's high, low and close (and the next session's `prev`) leaves every pre-open and post-open walk-forward forecast for that session and all earlier ones bit-identical (tolerance 1e-12) for all 18 variants (`P_DOW`, which only filters the residual pool by weekday, is built inside `--eval` and is not in the test), and changes the later ones (positive control); changing only that session's open leaves every pre-open forecast identical and moves exactly the post-open variants that use the gap (`W_HARz`, `W_SIZE`, `W_SIGN`, `W_SZSG`, `W_PRE`). Result: PASSED.
* **Replication of the project** (`python3 src/hl_model.py --replicate`, `hl_eval_replication.csv`): my S6 sigma path equals the stored `results/forecasts_R.csv` (max relative difference 8.2e-15, n = 1,887) and the OHLC bootstrap on the stored sigma gives Final (to 12 Oct, n = 317) coverage **90.2% (high) and 88.6% (low)**: exactly the project's published "90.2% / 88.6%". A separate scratch script that re-implements `eval_hl.py`'s loop (not stored in the repo) gave the same pinball, 31.240 and 36.767 x1e4, which `hl_eval_replication.csv` also holds.
* With the 3 sessions added after the project's stored forecasts (13, 14, 15 Oct), the walk-forward Final window (n = 320) gives 90.3% and 88.8%.


---

## 5. What failed, or came out null (everything I tried is above)

* **No variant beat the project's baseline, pre-open or post-open** (adoption rule: none of the 34 variant-target pairs). Specifically null: S4 / range-model / Garman-Klass scales (ties), EWMA scale (slightly worse for the high), weekday multiplier (built because the screen passed, no out-of-sample gain), gap-size bins, gap sign, gap size x sign, gap size as a HAR regressor (ties).
* The volatility model gives at most a marginally better *median* than the plain trailing 250-day median (high: borderline; low: none; Section 4.3); its value is in the band shape and the tail probabilities.
* For the **low**, the volatility model is a tie with every unscaled benchmark; the gain is concentrated in the high.
* Using the open merely as a floor/ceiling on the pre-open distribution (`W_PRE`) loses 18% to 24% of pinball against modelling the move from the open.
* Closing-auction slice: the 50% bands are too narrow and the pre-open high band too high at the bottom (Section 4.6); only 52 sessions, flagged as suggestive.

### Departures from, and additions to, the pre-fixed list (all disclosed)
* Amendment A1 (gap size normalised by the EWMA scale), made before any result existed (Section 0).
* The point-accuracy tests on the absolute error of the median against 'price stays' and the trailing-250 median (families 4 to 6) are not in the pre-fixed text: family 4 was coded before the first run but not listed; **families 5 and 6, the by-year table, the touch-probability calibration, the closing-auction facts, the gap-bin table, the Yahoo comparison, the replication and the leakage tests were added after the first results had been seen**; they are descriptive or are checks and carry no adoption decision.
* The first Yahoo-hourly comparison had a basis error (the repo's OHLC levels are raw; Yahoo's earlier hourly prices are bonus-adjusted), visible as a mean difference of Rs -1,108; I restricted that comparison to sessions from the bonus ex-date on.
* The first-written pre-fixed file hash was `e757b838...` and the amended one `e46eaf28...`; these are my own working records, not an independent timestamp (I may not commit).

---

## 6. Honest limits

* Final n = 320 sessions: the standard error of a typical miss is about Rs 2 to 3, Kupiec tests on 90% coverage have low power (the 95% Wilson interval of the Final 90% coverage is 87% to 93% for the high and 85% to 92% for the low). Daily sessions overlap in volatility regimes, so the effective sample is smaller than n.
* The ranges are wide because the thing being forecast (the day's extremes, from a daily-data model) is genuinely uncertain: even with the official open, the typical miss is Rs 35 to 37. I cannot make it sharper without information I do not have (intraday volume, order book, news).
* Probabilities beyond the 2.5% and 97.5% quantiles are extrapolations of a 500-session empirical distribution.
* The reported "typical miss" is an average over past conditions; on a day like today (after a 2.7% rally on 5.2 million shares) the realised miss could be larger. The model's sigma for 16 Oct is 2.43% against the project's 2.48% on 13 Oct, so it already reflects today.
* The live forecast is fitted through the 15 Oct close; if the bonus / split calendar or a data revision changes the history, the file must be regenerated (the JSON stores the data hashes).
* Quantiles are in rupees to Rs 0.1 but only meaningful to about +-Rs 2 (grid noise of a 500-point empirical distribution).
* Not tested here: trading rules built on these levels; the S&P overnight cue (about Rs 2 on the median per the v2 report); implied volatility as a scale; recalibration of the high's median; intraday timing of the high and low.

---

## 7. What range of rupees would a trader rely on? (16 Oct 2026, reference Rs 3,428)

Band widths from `results/hl_dayahead_2026-10-16.json`; typical miss = out-of-sample mean absolute error of the median, Final window n = 320 (CAS n = 52 in brackets); half-the-time = median absolute miss.

| | pre-open HIGH | pre-open LOW | after the open HIGH (flat open Rs 3,428) | after the open LOW (flat open) |
|---|---|---|---|---|
| median (the pin-point) | Rs 3,475 | Rs 3,390 | Rs 3,466 (open +1.12%) | Rs 3,388 (open -1.16%) |
| typical miss of the median (mean, Rs) | 43 [44] | 48 [48] | 35 [35] | 37 [38] |
| half the time within (Rs) | 34 [39] | 32 [38] | 29 [34] | 27 [29] |
| 50% band (Rs, width) | 3,449 to 3,513 (63) | 3,352 to 3,419 (67) | 3,446 to 3,504 (58) | 3,352 to 3,408 (56) |
| 90% band (Rs, width) | 3,421 to 3,591 (169) | 3,269 to 3,450 (181) | 3,429 to 3,569 (140) | 3,273 to 3,425 (152) |
| comparator miss ('price stays' / 'open stays'), Rs | 63 | 61 | 51 | 59 |
| measured coverage of the 90% band (Final) | 90.3% | 88.8% | 95.0% (one-sided, see 4.2) | 89.4% |

What a trader can rely on: **the 50% band (Rs 56 to 67 wide) is right about half the time and no tighter statement was supported; the median is good to roughly Rs 27 to 34 either way half the time and to Rs 35 to 48 on average; the 90% band is a wide safety fence, not a target.** After the open, the bands for any other open are the same shape moved to that open (median high about open +1.12%, median low about open -1.16%; open +2.21% / -2.21% for the 25% / 75% edges, open +4.10% / -4.51% for the 95% / 5% edges).

### How the bands can be read when placing orders (descriptive, not a rule)
Because the quantiles are reasonably calibrated (Section 4.5; the high runs slightly high) they translate into how often a level is touched. For the pre-open model in the Final window: the day's low went to or below the model's 25% quantile on 27% of sessions, below the median on 50%, below the 75% quantile on 77%; the day's high reached or exceeded the model's 75% / 50% / 25% quantile on 24% / 47% / 71% of sessions (n = 320). For 16 Oct, pre-open: a resting buy at Rs 3,352 would be reached about 1 day in 4, at Rs 3,390 about 1 in 2; a resting sell at Rs 3,513 about 1 in 4, at Rs 3,475 about 1 in 2 (high side: a little less than 1 in 2 because the high band runs slightly high). **Being reachable is not being profitable.** This study did not test any trading rule; the project's earlier exploratory test (DEVIATIONS #30) found that buying at the predicted low and shorting at the predicted high lost money after a 0.10% cost, and nothing here contradicts that. Use the bands for sizing stops and judging whether a move is unusual (in Final the low went below the model's 5% quantile on 5% of days, about 1 in 20, and the high above its 95% quantile on 2.5%, about 1 in 40: for 16 Oct, a low under Rs 3,269 or a high over Rs 3,591), not as entry signals.

---

## 8. Contradictions with, and notes on, earlier project statements
* **Confirmed:** the Final 90% coverage of the OHLC-bootstrap high / low, 90.2% / 88.6% (n = 317), reproduces exactly.
* **Note (code behaviour, not edited by me):** `src/eval_hl.py` as it stands now loads the 13 Oct row, whose stored sigma does not exist (`results/forecasts_R.csv` ends 12 Oct). It prints `nan` pinball for every row and counts 13 Oct as a miss (it now prints Final n = 318, 89.9% / 88.4%). The published 90.2% / 88.6% is correct for n = 317.
* **Correction of a stated convention:** the task brief says prices in the processed history are bonus-adjusted; only `prev` is adjusted (on the ex-date), the OHLC levels are raw traded prices (Section 3). Log targets are unaffected; rupee errors computed straight from the file before 23 May 2025 are on a different price level.
* **New nuance to the S6-vs-trailing result (v2 report 3.2: "vs a trailing-250-day benchmark the Final gain is weak, p 0.084" for the close):** for the day's high the volatility model beats the 250-day empirical quantiles in Final (Holm 0.013) but not pooled over Validation+Final, and for the low it never does.
* **Consistent with:** "50% intervals ran narrow" (the 50% bands covered 46.9% / 50.3% in Final and about 40% in CAS); "the gap interval is the least reliable" (not re-tested).
* The "NSE vs Yahoo up to about Rs 4" statement holds at the 99th percentile for 15-minute sessions and fails for rare outliers in the hourly feed (Section 4.9).

---

## 9. Numbers to quote
* Forecast for Fri 16 Oct 2026 (P0 = Rs 3,428.0, S6 sigma 2.43%, fitted through 15 Oct): **pre-open HIGH median Rs 3,475 (50%: 3,449 to 3,513; 90%: 3,421 to 3,591); LOW median Rs 3,390 (50%: 3,352 to 3,419; 90%: 3,269 to 3,450).** Full 5/10/25/50/75/90/95% in `results/hl_dayahead_2026-10-16.json`.
* Typical miss of the median, out of sample (Final, n = 320, at Rs 3,428): pre-open high Rs 42.7 (half the time within Rs 33.6), low Rs 47.7 (Rs 32.2); after the open: high Rs 34.8 (Rs 29.1), low Rs 37.4 (Rs 26.6). 'Price stays' / 'open stays' miss: Rs 63 / 61 and Rs 51 / 59.
* Knowing the open improves the high/low pinball by 23% / 23% in Final (Holm p < 0.001), and cuts the typical miss by about Rs 8 (high) and Rs 10 (low).
* Gap size and direction add nothing beyond the open's level (all gap-conditioned variants are ties, Holm p >= 0.48).
* 90% coverage, Final n = 320: pre-open high 90.3%, low 88.8% (Wilson 95%: 87-93% / 85-92%); 50% coverage 46.9% / 50.3%. CAS (n = 52): 90% 84.6% / 88.5%, 50% 40.4% / 40.4%.
* The open is the day's high on about 4% of sessions and the low on about 2% (Validation+Final, n = 568).
* Yahoo vs NSE official extremes: Yahoo high lower by Rs 1.1 on average (median Rs 0.2), Yahoo low higher by Rs 1.3 (hourly, n = 333); 15-minute sessions (n = 39): Rs 0.9 / 1.1, 99th percentile Rs 4.8 / 4.4.
* 14 Oct and 15 Oct (pre-open, as of the prior close): highs 3,408.3 and 3,445.0 vs medians 3,423 and 3,382; lows 3,320.0 and 3,315.2 vs medians 3,337 and 3,302; n = 2, not evidence of skill.

---

## 10. Reproduce every number (repo root `/home/user/pred_18`; python3, no network)

```
python3 src/hl_model.py --eval --hourly /tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/h60_BSE.NS.json
        # -> results/hl_eval_preopen.csv, hl_eval_postopen.csv, hl_eval_dm_holm.csv, hl_eval_adoption.csv, hl_eval_reliability.csv, hl_eval_touchprob.csv, hl_eval_byyear.csv,
        #    hl_eval_cas_facts.csv, hl_eval_gap_bins.csv, hl_eval_dow_screen.csv, hl_eval_twodays.csv, hl_eval_predictions.csv, hl_eval_yahoo_vs_nse*.csv   (about 30 s; the hourly JSON is a Yahoo 1h chart pull
        #    saved in the scratchpad, interval=1h range=2y for BSE.NS, last bar 15 Oct 15:15; without --hourly only the 15-minute Yahoo comparison is produced)
python3 src/hl_model.py --date 2026-10-16 --save            # -> results/hl_dayahead_2026-10-16.json  (needs hl_eval_*open.csv for the typical-miss fields)
python3 src/hl_model.py --date 2026-10-16 [--open 3440] [--json]
python3 src/hl_model.py --selftest            # -> results/hl_eval_selftest.csv
python3 src/hl_model.py --replicate           # -> results/hl_eval_replication.csv
python3 src/eval_hl.py                                      # the project's own script (prints nan for 13 Oct, see Section 8)
```

| number | file and column |
|---|---|
| typical miss, half-the-time miss, s.e. (Rs at 3,428) | `hl_eval_preopen.csv` / `hl_eval_postopen.csv`: `mae_med_rs_at_now`, `medae_med_rs_at_now`, `mae_med_se_rs_at_now` (rows window = final, cas) ; traded-rupee versions: `mae_med_rs_traded` |
| pinball, 50/90% coverage, Kupiec p, tail shares, Wilson interval | same files: `pinball_x1e4`, `cov50`, `cov90`, `kupiec90`, `below_q5`, `above_q95`, `p_below_q5`, `p_above_q95`, `cov90_wilson_lo/hi` |
| DM gains, p, Holm | `hl_eval_dm_holm.csv`: `gain_pct`, `p_two_sided`, `holm_two_sided` (family, window) |
| adoption verdicts | `hl_eval_adoption.csv` |
| calibration by quantile; touch probabilities | `hl_eval_reliability.csv`; `hl_eval_touchprob.csv` |
| weekday screen; closing-auction facts; gap bins; by-year | `hl_eval_dow_screen.csv`; `hl_eval_cas_facts.csv`; `hl_eval_gap_bins.csv`; `hl_eval_byyear.csv` |
| 14 / 15 Oct | `hl_eval_twodays.csv` |
| Yahoo vs NSE | `hl_eval_yahoo_vs_nse_summary.csv`, per-session `hl_eval_yahoo_vs_nse.csv` |
| 16 Oct forecast, sigma, band widths, touch probabilities, open examples | `hl_dayahead_2026-10-16.json` |
| replication and leakage tests | `hl_eval_replication.csv`; `hl_eval_selftest.csv` |
