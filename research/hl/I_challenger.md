# I. Challenger ("v2 clone") against the champion: pre-registered FORWARD comparison

Written Wed 28 Oct 2026, 21:26 IST (machine clock), before the challenger has made any forward forecast.  The first forward session is Thu 29 Oct 2026.  **Section 0 below is frozen at that moment (its SHA-256 is in `results/challenger/prefixed_sha256.txt` and in the commit message); nothing in Section 0 may be edited afterwards.**  Section 1 (the one fitted number) is written after Section 0, still before the first forward forecast, and is frozen the same way.  Later changes go into `docs/DEVIATIONS.md` with a date.

## 0. What is fixed here (read this section first)

### 0.1 The two sides

* **Champion** = every model exactly as it ran up to the 28 Oct 2026 close (repository commit `717001f`).  Everything the user sees (the hour-by-hour table, the 08:34 / 09:10 forecasts, the scoreboard, the dashboard) stays on the champion for the whole trial.
* **Challenger** = a clone that runs silently next to the champion, on the same bars, the same history and the same clock, and logs its own predictions to `results/challenger/`.  It is never printed in the user's table.  Nothing is switched over automatically: a switch needs the adoption rule of 0.5 and the user's go-ahead.

### 0.2 What the challenger changes (only these two things; every other line of code and data is the champion's)

* **C1 (applied).  Next-hour high and low** (the two "precise high / low of the next hour" columns).  The window sigma of the champion (`hourly_table.next_hour`) is multiplied by `sqrt(scale2)`, with `scale2 = clip((1 - w) + w * ratio, 0.5, 2.0)` and `ratio = (realised variance of the 15-minute bars completed before the reading) / (the profile's expected variance for the same bars)`; with no completed bar `scale2 = 1`.  Everything else (the pooled standardised excursions, the median pin-point, the 15:30 cut) is unchanged.  **`w` is the only fitted number and is chosen once by the rule in 0.3.**  If the rule picks `w = 0`, C1 is identical to the champion and the report says "identical" (that is a result, not a failure).
* **C2 (recorded only, not applied).  Pre-open order book.**  For every session from 29 Oct the challenger stores, from the last NSE pre-open snapshot of BSE that is FINAL (the page stamp is on the session's own date and at or after 09:08:00, `finalPrice > 0` and `finalQuantity > 0`): total buy quantity, total sell quantity, the imbalance `I = (buy - sell) / (buy + sell)`, the IEP, the previous close and the gap `100 * ln(IEP / previous close)`.  It changes no forecast.  It feeds the forward test of 0.6.

Not changed (identical in both, so nothing to compare): the day-ahead and after-open high/low forecasts, the 08:30 open range, the close range and pin-point, the peers column (forward test H keeps running as registered).

### 0.3 How `w` is chosen (history only)

* Grid `w` in {0, 0.25, 0.5, 0.75, 1.0} (five values; this is the family).
* Method: leave-one-session-out on every session in the 15-minute history (`hourly_table.load_sessions`, through 28 Oct 2026), every checkpoint k = 2..22 (so some of today's bars are already completed), the champion's pooled standardised excursions refitted without the held-out session, exactly as `hourly_table.loo_eval` does.
* Criterion: pooled mean pinball loss over the five quantiles (0.05, 0.25, 0.5, 0.75, 0.95), high and low together.  `w > 0` is taken only if it beats `w = 0` by **at least 1%** in that loss; among values that do, the lowest loss wins.  Otherwise `w = 0`.
* This choice is **in-sample and is not evidence**; the forward comparison is the only test.  The earlier close-nowcast test found no gain from "today's volatility so far" (`live_nowcast.W_SCALE = 0`: w = 0 covered 90.0%, w = 0.5 88.9%, w = 1 86.0%), so `w = 0` is a likely outcome.

### 0.4 Forward comparison of C1 (the only comparison)

* Data: every LIVE row that `src/hourly_table.py` logs from Thu 29 Oct 2026, with both predictions computed in the same run from the same price now, scored against the same Yahoo 1-minute high / low of the window (the existing scorer; windows cut at 15:30).  Replays are never readings.
* Eligible session: a normal session (the Sun 8 Nov 2026 Muhurat evening session and any special session are excluded) with at least 4 complete scored readings and no Yahoo gap in a scored window.
* Statistic: for each eligible session, the mean over its readings of the absolute error of the median pin-point (rupees), for the high and for the low, champion and challenger.  `d_s = AE_champion - AE_challenger` per session (positive = the challenger is better).
* Test: one-sided sign-flip permutation test on the mean of `d_s` over sessions (20,000 permutations, numpy seed 20261029), separately for the high and the low, **Holm over the two**.
* Looks: **10 eligible sessions: no-harm check only** (the two mean absolute errors for each side and a warning flag if the challenger is 10% or more worse on either side; no p-value, no adoption possible).  **40 eligible sessions: decision.**  **60: decision if none was reached.**  No other looks.
* Locked reporting: before the 10-session look only counts and data-quality facts are printed; no error comparison.

### 0.5 Decision rules (at 40 and at 60 sessions)

* **Adopt** only if all hold: (i) Holm-adjusted p < 0.05 on at least one side; (ii) on every side that passes, the challenger's mean absolute error is at least **3% lower** than the champion's; (iii) the other side is not worse by 3% or more; (iv) the sign of the mean difference is the same in the first and the second half of the eligible sessions.  Adoption then still waits for the user's go-ahead.
* **Drop** if on either side the challenger is worse by 3% or more with a one-sided p < 0.05 in that direction.
* Otherwise: not demonstrated; the champion stays; read as "this test could not see a difference", not "there is none".

### 0.6 Forward lead test for C2 (a lead test like H, never an adoption by itself)

* Question: does the pre-open imbalance `I` say anything about the move from the official open to the official close?  `R = 100 * ln(official close / official open)`.
* H_B (one-sided, positive: more buying than selling at the open goes with a higher open-to-close move): OLS slope of `R` on `I`, one observation per eligible session (a normal session with a FINAL snapshot), permutation p-value (20,000 permutations, seed 20261029).
* Sample: sessions from Thu 29 Oct 2026.  First analysis at 60 eligible sessions, one more at 120; locked (counts only) before.
* Significance (p < 0.05) would only make C2 a documented lead; applying it to any forecast would need its own registration.
* **Power (simulated, not measured effects):** `I` has been strongly negative on every one of the 7 logged sessions (mean -0.48, sd 0.10; its marginal spread only: no outcome was looked at), and the model's own open-to-close sigma is about 2.3 percentage points.  A one-sided 5% test then has about 17% / 24% power at 60 / 120 sessions for a true slope of 2 points per unit of `I`, about 50% / 74% for a slope of 5, and about 94% / 100% for a slope of 10.  So unless the effect is large the likely outcome is "not demonstrated".

### 0.7 Known weaknesses (stated now)

1. About 45 sessions of 15-minute history and ~7 live readings a day: the C1 comparison is low-powered; a 3% gain is hard to see in 40-60 sessions (the measured spread of `d_s` and the resulting power are added in Section 1).
2. Five values of `w` are tried on the same history the profile comes from.
3. The two sides share data and profile, so they are far from independent; the paired test accounts for that, but the comparison cannot show that C1 is "right", only that it is not worse or is better on these sessions.
4. Readings within a session overlap and are correlated; sessions are the unit, hence the session-level statistic.
5. Yahoo 1-minute data is unofficial.
6. C2 has no history to fit or backtest (the NSE pre-open book was logged from 16 Oct only), so it is recorded, not applied.

### 0.8 Files and code

`src/challenger.py` (C1 prediction, side-by-side logging, C2 book features, forward dataset, locked report, comparison, synthetic self-test), `results/challenger/` (`hourly_log.jsonl`, `book_features.csv`, `compare_dataset.csv`, `prefixed_sha256.txt`).  The analysis code is tested on synthetic data before it may run on forward data.
