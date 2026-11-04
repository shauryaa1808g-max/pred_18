# Specialist B: live running high / low estimate for NSE:BSE

*Status: PRE-FIXED SECTION WRITTEN BEFORE ANY MODEL RESULT WAS COMPUTED (clock at writing: Thu 15 Oct 2026 22:05 IST). What had been looked at before writing it: data facts only (session counts, the Yahoo-vs-NSE high/low differences over 39 + 479 sessions, the shape of the 1-minute bars around the close, and one Monte-Carlo check that the closed-form distribution below is arithmetically right). No coverage, pinball or calibration number of any variant had been computed. The results sections are appended below this one.*

## 0. Pre-fixed design

**What is predicted.** At a time T inside the session: the final official day high H and day low L, given the price now P, the running high M and running low N so far (from Yahoo bars, unofficial). By construction H >= M and L <= N. The model describes how far the extremes usually extend. It does not say which way the price goes (zero drift, symmetric).

**Model (fixed before results).** Log price from T to the end of the continuous session is a driftless random walk whose variance follows the time-of-day profile estimated in `src/live_nowcast.py` (15-minute slots 09:15 ... 15:15, mean squared 15-minute log return, reused by import). Continuous trading effectively ends at about 15:15; the official close since 2026-08-03 is a single closing-auction print (slot 24 = 15:15-15:30; the 1-minute bars show one print at 15:28-15:29). So the remaining path is: a continuous part with variance s_c^2 = sum of the remaining slot variances up to 15:15, then one discrete jump with variance s_J^2 = slot-24 variance. With sigma_W^2 = s_c^2 + s_J^2, the future maximum (relative to P, in logs) has the exact distribution F(b) = Phi(b/s_c) + Phi(b/sigma_W) - 1 for b >= 0 (reflection principle for the continuous part plus one discretely monitored final point; derivation in the report; checked against Monte-Carlo). The final high is max(M, P * exp(future max)), so: P(high already in) = F(ln(M/P)); every quantile of the final high is max(M, P * exp(quantile of the future max)). The low is the mirror image. All scales are multiplied by one volatility multiplier c (calibrated, below).

**Printed bands.** 50% band = [q25, q75], 90% band = [q05, q95] of the final-high (final-low) distribution, which has an atom at M (N). When P(high in) > 5% the lower end of the 90% band is M itself.

**Data and windows.**
* 15-minute sample: `data/processed/intraday_union_15m.csv` + `intraday_extra_15m.csv`, 39 sessions 2026-08-18 to 2026-10-15 (all after the closing auction began; all inside the project's Final window 2025-07-01 onward; there is no Development or Validation window in this sample). Truth for the primary score: the official NSE daily high/low (`bse_daily.csv` + `bse_daily_extra.csv`, read-only). Secondary truth: the Yahoo bars' own final extreme (structure test free of the Yahoo-NSE offset). Checkpoints: 09:45, 10:30, 11:30, 12:30, 13:15, 14:00, 14:30, 15:00.
* Hourly sample: the 2-year Yahoo hourly file (scratchpad), complete 7-bar sessions only. Walk-forward, expanding: the first 50 complete sessions are fit-only (never scored); the profile and the multiplier for session t use sessions before t only. Windows by session date: Validation = scored sessions before 2025-07-01, Final = 2025-07-01 onward, post-closing-auction = 2026-08-03 onward. There is no Development window (the file starts 2024-10-16). Truth: the hourly bars' own final extreme (the official-vs-Yahoo offset is measured separately). Checkpoints: 10:15, 11:15, 12:15, 13:15, 14:15, 15:15. Labelled "hourly" everywhere.
* 1-minute sample: the last 7 sessions Yahoo serves (7-15 Oct): used to measure the Yahoo-NSE offset and as a descriptive replay only.

**Calibration protocol.** 15-minute sample: leave-one-session-out and nested: for the scored session j, the multiplier is chosen on the other sessions i, each of which is itself forecast with a profile that excludes both i and j; the scored session's forecast uses the profile of the other sessions. Hourly sample: walk-forward as above (the multiplier for t is chosen on sessions before t, each forecast with the profile of the sessions before it). The multiplier is chosen on a grid 0.50 ... 2.00 (step 0.025) to minimise the mean pinball loss over the project's 9-level grid (2.5, 5, 10, 25, 50, 75, 90, 95, 97.5%), summed over both sides and all slot boundaries 09:30-15:00 (15-minute) or 10:15-15:15 (hourly).

**All variants that will be tried (listed now; any added later is marked "post-hoc").**

| id | what |
|---|---|
| B1 | price stays: final high = running high, final low = running low |
| B2 | unconditional empirical quantiles of the extension ln(H/M) (ln(N/L)) at that checkpoint, other sessions (15-minute: leave-one-out; hourly: past sessions), ignores where the price sits inside the range |
| B3 | constant variance rate: same model but no time-of-day profile (every slot gets the same variance, total unchanged), own multiplier |
| B4 | historical path replay: the actual remaining paths (future maximum / minimum relative to the price at that time) of the other / past sessions as the distribution |
| M0 | profile model, c = 1 (no calibration) |
| **M1** | profile model with a calibrated c (the base model the live tool uses unless something below is validated) |
| M2a, M2b | M1 with sigma scaled by sqrt((1-w) + w * (realised variance so far / its average at that time)), w = 0.5, 1 |
| M3a, M3b | same with realised range so far (Parkinson) instead of realised variance, w = 0.5, 1 |
| M4a, M4b | same with a day-ahead sigma stand-in: EWMA(lambda = 0.94) of the Garman-Klass intraday variance of earlier sessions (dated before the session), w = 0.5, 1 |
| M5 | M2 (w = 0.5) and M4 (w = 0.5) together |
| M6 | M1 with a separate multiplier for each quantile level |
| M7 | M1 with a separate multiplier for morning (09:30-11:00), midday (11:15-13:00), afternoon (13:15-15:00) |
| M1+off | M1 with the average Yahoo-to-NSE offset added to the quantiles (official truth only) |

Ratios in M2-M5 are clipped to [0.4, 4] as in `live_nowcast.py`.

**Tests.** Pinball loss, 50% and 90% coverage of the printed bands with Kupiec p, Diebold-Mariano (Harvey-Leybourne-Newbold, `src/metrics.py`, per-session mean loss over checkpoints; one-sided "variant better than M1"; lag 2 for the 39 unordered sessions, lag 5 for the hourly series). Holm correction within two families: (i) the nine tests M2a ... M7 against M1 (per sample), (ii) the four tests M1 against B1 ... B4. Coverage uncertainty from a session-cluster bootstrap (checkpoints of one session are strongly dependent; n sessions is the real sample size). Everything is reported, winners and losers.

**Honesty rules.** A variant is called an improvement only if it beats M1 on the hourly Final window AND on the 15-minute sample (or is stated as hourly-only / 15-minute-only) with Holm-adjusted p < 0.05. Otherwise "no improvement found" and the live tool keeps M1. The 15-minute sample is 39 sessions: a coverage figure from it can be off by +-8 points (50% band) or +-5 (90% band) from sampling alone.


---

# RESULTS (written after the runs; everything below is generated from files in `results/live_hl_*` by `src/live_highlow.py`, tables are copied by code)

## 1. Summary in plain words

**What I built.** `src/live_highlow.py`: at any time T in a session it prints the price now, the running high and low so far (Yahoo 1-minute bars, unofficial), the chance that the day's high (low) is already in, how far it usually extends if it is not, and "half the time / nine times in ten" values for the final NSE high and low, plus the typical miss in rupees at that time of day. It does not say which way the price goes.

**Terms.** Pinball loss = the average penalty of a set of quantile forecasts (lower is better; here in rupees). Kupiec test = does the hit rate equal the stated one. Diebold-Mariano (DM) = does one forecaster have lower loss than another. Holm = correction for trying many variants. CAS / post-closing-auction = the regime since 3 Aug 2026 in which the official close is the closing-auction price. "Yahoo" = Yahoo bars (unofficial), "NSE" = the official daily high/low.

**What the evidence says (every figure has its n next to it below).**
1. **The Yahoo high/low are not the NSE high/low.** In 39 sessions the NSE high was above the Yahoo high by Rs 0.2 typically (mean 0.9, 90% of sessions within Rs 2.6, max Rs 5.3) and the NSE low below the Yahoo low by Rs 0.7 typically (mean 1.05, 90th percentile 2.7, max 4.5); never the other way. This is larger than the "up to about Rs 4" in `docs/INPUT_AUDIT.md` (that figure came from 20 sessions). On Thu 15 Oct the Yahoo 1-minute bars gave exactly the NSE figures (H 3,445.0, L 3,315.2, difference Rs 0.0).
2. **Ignoring that offset breaks the bands.** With plain Yahoo extremes as the estimate of the NSE figure, the "nine times in ten" values held only 71% (high) and 75% (low) of the time (39 sessions, 8 checkpoints each) and at 15:00 only 46% / 56%, because late in the day the band collapses onto the running high and the NSE figure sits a few rupees beyond it. Adding the measured offset distribution (post-hoc fix, called M1c) brings it to **88% (high) and 88% (low)**, session-cluster bootstrap 95% interval 80-95%, and "half the time" to 54% / 57% (interval 41-65 / 46-68). One of 32 checkpoint cells fails a Kupiec test (low side, "half the time", 14:00: 27 of 39 = 69%, p = 0.015) and one sits at p = 0.051 (low side, "nine in ten", 12:30: 31 of 39 = 79%). Cells are 39 sessions each, so one cell can be off by +-8 (50% level) or +-5 (90% level) points from luck alone.
3. **Realised volatility so far and a day-ahead sigma do not help.** Scaling the remaining volatility by how wild the session has been so far (variants M2a/M2b, M3a/M3b) or by an EWMA of earlier sessions' volatility (M4a/M4b, M5) never beat the plain model after Holm correction in any window (15-minute sample n = 39, hourly Validation n = 123, hourly Final n = 306, post-closing-auction n = 43); using all of the session's realised variance (M2b, weight 1) was worse (+4.1% pinball in hourly Final, +6.3% in the 15-minute sample). Same conclusion `live_nowcast.py` reached for the close.
4. **The time-of-day variance profile earns its keep only in the large hourly sample.** In the 2-year hourly file (Final window n = 306) the profile model beats a constant-variance-rate model by 1.6% in pinball loss (Diebold-Mariano p < 0.001, Holm < 0.001); in the 39-session 15-minute sample the constant-rate model is nominally better (-1.1% official target, -0.8% Yahoo target). So with 39 sessions I cannot show that the profile matters; the difference is about Rs 0.03 of average pinball loss either way.
5. **"The high is probably in (X%)" is a conservative probability for the high.** When the model said 30-90% that the running high is already final, the high was in 81% of the time (15-minute sample, 167 checkpoint states from 39 sessions; stated 62%) and 72% (hourly Final, 918 states from 306 sessions; stated 61%). For the low the stated and observed values were close (64% vs 61% and 66% vs 61%). Read a stated "is in" probability for the high as a floor.
6. **Typical miss in rupees** (NSE final high / low vs the running high / low, 39 sessions): about Rs 20 / 22 at 09:45, 16 / 19 at 10:30, 9 / 15 at 12:30, 7 / 5 at 14:00, 3 / 2 at 15:00 on average, but half the time only Rs 4 / 7 at 09:45 and under Rs 1 by 15:00, because on many days the extreme is already in. The model's median cuts the average miss only a little (Rs 17.5 / 18.3 at 09:45).
7. **Replay of Thu 15 Oct** (one session, so an illustration, not evidence): the NSE high 3,445.0 was above the "nine times in ten" value at 4 of 8 checkpoints (09:45, 11:30, 12:30, 13:15) because of a jump of about +3% that began at about 13:33 (the high was made at 14:04); the low (3,315.2, made at 09:16) was inside the bands at all 8.
8. **Not tested:** any trading rule or profit. The tool describes extension of extremes, with zero drift.

## 2. What was built (the tool)

```
python3 src/live_highlow.py                  # live: fetch Yahoo 1-minute bars (7-day window), print, append to results/live_hl_log.jsonl
python3 src/live_highlow.py --asof 12:30     # replay the last session; only 1-minute bars that STARTED before 12:30 are used (as live_nowcast does)
python3 src/live_highlow.py --replay         # table for the last completed session -> results/live_hl_replay_latest.csv
python3 src/live_highlow.py --backtest       # all the evaluation below -> results/live_hl_*.csv/json
python3 src/live_highlow.py --selftest       # closed form vs Monte-Carlo, profile vs live_nowcast.profile, state check, no-leak test
```

Reused by import from `src/live_nowcast.py` (not edited): `yahoo_1m`, `rows_1m`, `to_15m`, `profile`, `load_history`. Official daily bars are read from `data/processed/bse_daily.csv` + `bse_daily_extra.csv` with a read-only merge (`common.load_bse()` alone ends on 13 Oct; the extra file carries 14 and 15 Oct; `official_bars.load_bse_ext()` would also try to download, so it is not used).

Handled: Yahoo 429 or bad JSON (query2, then query1, 3 rounds with back-off, then the cached bars in `results/live_hl_bars_1m.csv`; ad-hoc tests, not stored in the repo, simulated a 429 on query2 and a 429 on both hosts); weekends (message and exit; tested with the `--now` clock override); before 09:15 (message); a weekday with no bars today, e.g. a holiday (message); after the close (all bars used, "session complete", NSE value expected a little beyond the Yahoo extreme); the window 15:15-15:35 (continuous trading over, only the closing print left). The cache keeps every 1-minute bar ever fetched (Yahoo serves only about 7 sessions), so the 7-15 Oct minute bars are preserved.

Example (replay of 15 Oct as of 12:30, copied from the tool):

```
At 12:30 IST [replay as of 12:30, session 2026-10-15] BSE is Rs 3,344.0 (+0.18% vs the previous official close Rs 3,338.0); 180 min to the close. Running range so far (Yahoo 1-minute bars, unofficial): low Rs 3,315.2 - high Rs 3,378.9.
Yahoo vs NSE: over 39 sessions the NSE official high was above Yahoo's by Rs 0.2 typically (mean 0.9, 90th percentile 2.6, max 5.3) and the NSE official low below Yahoo's by Rs 0.7 typically (mean 1.1, 90th percentile 2.7, max 4.5); never the other way in this sample. The ranges below are on the NSE basis (Yahoo path plus that offset), so they sit a little outside the Yahoo figures.
Final HIGH: the high is probably in (64%); if it extends, another Rs 7-30 up is typical. It can not end below Rs 3,378.9 (the running high, the floor). Half the time it ends at or below Rs 3,380.3; nine times in ten at or below Rs 3,407.6; 19 times in 20 at or below Rs 3,419.7.
   Note: in past sessions this 'is in' probability for the HIGH ran low (the high was in more often than stated; see the calibration table in research/hl/B_liveintraday.md).
   Chance the high is pushed at least Rs 5 / 10 / 20 / 40 up from the running high: 29% / 24% / 15% / 5%.
Final LOW: toss-up whether the low is in (56% it is); if it extends, another Rs 8-31 down is typical. It can not end above Rs 3,315.2 (the running low, the ceiling). Half the time it ends at or above Rs 3,312.7; nine times in ten at or above Rs 3,281.4; 19 times in 20 at or above Rs 3,269.7.
   Chance the low is pushed at least Rs 5 / 10 / 20 / 40 down from the running low: 37% / 30% / 19% / 7%.
Typical miss at this time of day (39 past sessions, out of sample, vs the NSE figure): assuming the final high equals the running high is off by Rs 10 on average (half the time under Rs 1); for the low Rs 15 (half under Rs 4). The model's median is off by Rs 9 (high) / Rs 14 (low) on average.
This says how far the extremes usually extend, not which way the price goes (no drift assumed). Volatility multiplier c = 1.00 (leave-one-out value for this session, so the replay does not see itself). checked leave-one-session-out on 39 sessions (8 checkpoints each, strongly dependent): 'half the time at or below/above' held 54% (high) / 57% (low) of the time and 'nine times in ten' held 88% / 88% (effective sample about 39 sessions, so +-8 points on the first and +-5 on the second from sampling alone; per-checkpoint table in research/hl/B_liveintraday.md).
```

## 3. Method, exactly

**State at time T** (all known at T): P = close of the last 1-minute bar that started before T; M, N = highest high / lowest low of those bars; position in the day = m completed 15-minute slots plus a fraction.

**Remaining path.** Log price is a driftless random walk until about 15:15 with the time-of-day variance profile `ev[k]` (mean squared 15-minute log return of slot k over the training sessions; `live_nowcast.profile`). Continuous trading in the 1-minute data effectively stops at 15:14-15:15; the official close is then one auction print (timestamped 15:15 on 7 Oct, 15:14 on 8-9 Oct, 15:28-15:29 on 12-15 Oct). So: continuous variance s_c^2 = (1-f) ev[m] + sum of ev[m+1 .. 23]; one jump with variance s_J^2 = ev[24]; sigma_W^2 = s_c^2 + s_J^2; everything multiplied by c.

**Exact distribution of the future maximum** (log, relative to P): F(b) = Phi(b/s_c) + Phi(b/sigma_W) - 1 for b >= 0. Derivation: P(max <= b, final point <= b) = P(final point <= b) - P(max > b, final point <= b); the continuous part obeys the reflection principle and the final point (continuous end plus the jump, both symmetric) is below b with probability 1/2 given that the path touched b, so P(max > b, final <= b) = P(max > b)/2 where P(max > b) = 2(1 - Phi(b/s_c)). This is the "reflection form with discrete monitoring correction": the correction is exact because the one discretely monitored point is the auction print. Checked against 1,000,000 simulated paths (max difference 0.0004, `results/live_hl_selftest.json` holds a 200,000-path version, max difference 0.0023) and on a real state (12 Oct 12:30: model P(high in) 0.3970 vs simulation 0.3960; 90% extension quantile 0.01953 vs 0.01954).

**Final high (Yahoo bars) = max(M, P exp(future max)).** Hence P(high already in) = F(ln(M/P)) and every quantile of the final high is max(M, P exp(quantile of the future max)); the distribution has an atom at M. The low is the mirror image (same F with ln(P/N)).

**NSE official basis (M1c, post-hoc).** The NSE figure is the Yahoo extreme moved outwards by an offset (Section 4). M1c = Yahoo-basis model convolved with the empirical offsets of the other sessions (39 values for the live tool; leave-one-out in the backtest). The Yahoo-basis structure and c are fitted against the Yahoo-bars final extreme, so the offset is not counted twice.

**Calibration of c.** Grid 0.50-2.00 (step 0.025) minimising mean pinball loss over the project's 9 levels, both sides, all slot boundaries 09:30-15:00 (15-minute) or 10:15-15:15 (hourly). 15-minute sample: leave-one-session-out and nested (the scored session never enters its own profile or c; each calibration session is forecast with a profile excluding both itself and the scored session). Hourly sample: expanding walk-forward, first 50 sessions fit-only, c for session t from sessions 20..t-1 each forecast with the profile of the sessions before it. The live tool uses c = 1.025 (fitted on all 39 sessions, Yahoo-target fit) and the profile of all sessions except today.

**Feature timestamps relative to the forecast time T**

| input | dated |
|---|---|
| P, M, N, position in the day | bars that started before T (same session) |
| realised variance / range so far (M2, M3) | bars before T (same session) |
| day-ahead sigma stand-in (M4): EWMA(0.94) of the Garman-Klass intraday variance | official daily bars of sessions strictly before the session date |
| variance profile, c | other sessions. 15-minute sample: ALL other 38 sessions, including later ones (leave-one-out, not chronological; a strictly chronological check is in Section 4.8). Hourly: earlier sessions only |
| Yahoo-to-NSE offsets | other sessions' final extremes (15-minute: leave-one-out) |
| target | final extreme of the bars (Yahoo) or the NSE daily high/low (published about 16:34 IST) |

**No-leak test** (`--selftest`): wiping everything about the scored session that is not known at the checkpoint (final extremes, future paths, its own squared returns) changes none of its forecasts (max absolute change 0.0 for all 12 variants checked).

## 4. Results

### 4.1 Data and the Yahoo-vs-NSE offset

Samples: 15-minute: 39 sessions 2026-08-18 to 2026-10-15, all after the closing auction began (so all inside the project's Final window; there is no Development or Validation window in this sample); 8 of them lack a 15:15 bar (the 1-minute bars of 8 and 9 Oct show the auction print inside the 15:14 bar; the other six are presumably the same), 31 have it. Hourly: 479 complete 7-bar sessions 2024-10-16 to 2026-10-15; 429 scored (first 50 fit-only): Validation 123 sessions (before 2025-07-01), Final 306 (2025-07-01 on), of which post-closing-auction 43 (2026-08-03 on); there is no Development window. Hourly bars are bonus-adjusted by Yahoo (divided by 3 before 23 May 2025); `bse_daily.csv` holds OHLC as traded (Rs 7,385 on 20 May 2025) with the adjustment in `prev` / `ca_factor`, so the hourly comparison rescales 146 early sessions by 3; all model quantities are logs and unaffected. The 15-minute bars rebuilt from the cached 1-minute bars equal the 15-minute file exactly (T13: 173 bars of 7 sessions, maximum difference Rs 0.00).

**T2. Yahoo extremes vs the NSE official high / low (rupees)**

| sample | n | difference | mean | median | p90 | p95 | max | min | share > Rs 0.05 | share < -Rs 0.05 |
|---|---|---|---|---|---|---|---|---|---|---|
| 15-minute bars, 39 sessions (Aug-Oct 2026) | 39 | NSE high minus Yahoo high | 0.89 | 0.20 | 2.62 | 4.00 | 5.3 | -0.00 | 0.64 | 0.000 |
| 15-minute bars, 39 sessions (Aug-Oct 2026) | 39 | Yahoo low minus NSE low | 1.05 | 0.70 | 2.70 | 3.93 | 4.5 | -0.00 | 0.79 | 0.000 |
| 1-minute bars, last 7 sessions (7-15 Oct 2026) | 7 | NSE high minus Yahoo high | 0.66 | 0.10 | 1.76 | 2.03 | 2.3 | -0.00 | 0.57 | 0.000 |
| 1-minute bars, last 7 sessions (7-15 Oct 2026) | 7 | Yahoo low minus NSE low | 0.37 | 0.20 | 0.96 | 1.23 | 1.5 | -0.00 | 0.57 | 0.000 |
| hourly bars, 479 sessions (Oct 2024-Oct 2026), Rs as traded | 479 | NSE high minus Yahoo high | 1.21 | 0.30 | 3.46 | 4.95 | 46.4 | -8.70 | 0.64 | 0.004 |
| hourly bars, 479 sessions (Oct 2024-Oct 2026), Rs as traded | 479 | Yahoo low minus NSE low | 1.88 | 0.60 | 4.42 | 8.50 | 54.7 | -12.80 | 0.76 | 0.002 |
| hourly bars, post closing-auction sessions | 43 | NSE high minus Yahoo high | 2.04 | 0.40 | 4.00 | 5.26 | 30.4 | -0.00 | 0.77 | 0.000 |
| hourly bars, post closing-auction sessions | 43 | Yahoo low minus NSE low | 0.95 | 0.70 | 1.96 | 2.68 | 9.0 | -0.00 | 0.81 | 0.000 |

Reading: in the 39 sessions the NSE high was never below the Yahoo high and the NSE low never above the Yahoo low (beyond float noise), so the Yahoo running high is a true floor for the NSE high. The 479-session hourly sample has a much fatter tail (95th percentile Rs 5.0 / 8.5, a few outliers of Rs 46 / 55 and three sessions where Yahoo's hourly extreme was beyond the NSE one by up to Rs 12.8), which may be missed prints in the hourly aggregation; the 1-minute sessions (n = 7) show only Rs 0-2.3. The 39-session distribution is what the tool uses; its tail is the least certain part. This **contradicts** the "up to about Rs 4" in `docs/INPUT_AUDIT.md` mildly (max 5.3 / 4.5 in 39 sessions) and strongly for the hourly tail.

### 4.2 Which variant? (pre-fixed list; pinball loss, DM, Holm)

**T3a. Mean pinball loss in rupees over the 8 (15-minute) / 6 (hourly) checkpoints, both sides, 9 quantile levels (in brackets: % vs M1; M1c/B3c/B4c exist only for the official target)**

| variant | 15m Yahoo (n=39) | 15m official (n=39) | hourly Valid. (n=123) | hourly Final (n=306) | hourly post-CAS (n=43) |
|---|---|---|---|---|---|
| B1 | 5.28 (+79.7%) | 5.79 (+83.4%) | 6.05 (+125.0%) | 4.63 (+100.9%) | 5.17 (+87.3%) |
| B2 | 3.24 (+10.3%) | 3.29 (+4.4%) | 3.48 (+29.2%) | 2.72 (+18.1%) | 3.02 (+9.2%) |
| B3 | 2.92 (-0.8%) | 3.12 (-1.1%) | 2.72 (+1.1%) | 2.34 (+1.6%) | 2.83 (+2.4%) |
| B4 | 2.97 (+1.1%) | 3.22 (+2.0%) | 2.71 (+0.6%) | 2.36 (+2.5%) | 2.70 (-2.2%) |
| M0 | 2.93 (-0.2%) | 3.15 (-0.1%) | 2.65 (-1.5%) | 2.37 (+2.9%) | 2.72 (-1.4%) |
| M1 | 2.94 (+0.0%) | 3.15 (+0.0%) | 2.69 (+0.0%) | 2.30 (+0.0%) | 2.76 (+0.0%) |
| M2a | 3.03 (+3.0%) | 3.22 (+2.0%) | 2.72 (+0.9%) | 2.31 (+0.2%) | 2.70 (-2.3%) |
| M2b | 3.16 (+7.6%) | 3.35 (+6.3%) | 2.90 (+7.9%) | 2.40 (+4.1%) | 2.74 (-0.9%) |
| M3a | 2.93 (-0.3%) | 3.13 (-0.7%) | 2.66 (-1.0%) | 2.29 (-0.8%) | 2.74 (-0.8%) |
| M3b | 2.98 (+1.3%) | 3.17 (+0.6%) | 2.80 (+4.2%) | 2.35 (+2.2%) | 2.80 (+1.3%) |
| M4a | 2.96 (+0.6%) | 3.17 (+0.5%) | 2.67 (-0.8%) | 2.31 (+0.3%) | 2.78 (+0.7%) |
| M4b | 2.98 (+1.4%) | 3.18 (+0.9%) | 2.69 (-0.0%) | 2.35 (+1.8%) | 2.84 (+2.8%) |
| M5 | 3.02 (+2.8%) | 3.23 (+2.3%) | 2.71 (+0.7%) | 2.34 (+1.8%) | 2.74 (-0.7%) |
| M6 | 2.88 (-2.1%) | 3.12 (-1.0%) | 2.70 (+0.3%) | 2.29 (-0.6%) | 2.73 (-1.2%) |
| M7 | 2.92 (-0.7%) | 3.13 (-0.7%) | 2.71 (+0.6%) | 2.31 (+0.1%) | 2.76 (+0.1%) |
| M1+off |  | 3.20 (+1.3%) |  |  |  |
| M1c (post-hoc) |  | 3.05 (-3.4%) |  |  |  |
| B3c (post-hoc) |  | 3.03 (-4.1%) |  |  |  |
| B4c (post-hoc) |  | 3.11 (-1.5%) |  |  |  |

**T3b. Diebold-Mariano one-sided p (raw / Holm). Benchmarks: p that M1 is better than the benchmark. M2a-M7: p that the variant is better than M1 (Holm over the 9). M1c: p better than M1 (not in a family). B3c, B4c: p that M1c is better (Holm over B1, B2, B3c, B4c)**

| variant | 15m Yahoo (n=39) | 15m official (n=39) | hourly Valid. (n=123) | hourly Final (n=306) | hourly post-CAS (n=43) |
|---|---|---|---|---|---|
| B1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| B2 | 0.041 / 0.124 | 0.195 / 0.584 | 0.000 / 0.000 | 0.000 / 0.000 | 0.096 / 0.192 |
| B3 | 0.953 / 0.953 | 0.995 / 0.995 | 0.126 / 0.252 | 0.000 / 0.000 | 0.007 / 0.021 |
| B4 | 0.302 / 0.604 | 0.223 / 0.584 | 0.367 / 0.367 | 0.014 / 0.014 | 0.785 / 0.785 |
| M2a | 0.760 / 1.000 | 0.685 / 1.000 | 0.655 / 1.000 | 0.574 / 1.000 | 0.232 / 1.000 |
| M2b | 0.829 / 1.000 | 0.801 / 1.000 | 0.981 / 1.000 | 0.964 / 1.000 | 0.434 / 1.000 |
| M3a | 0.460 / 1.000 | 0.384 / 1.000 | 0.297 / 1.000 | 0.214 / 1.000 | 0.351 / 1.000 |
| M3b | 0.600 / 1.000 | 0.551 / 1.000 | 0.903 / 1.000 | 0.862 / 1.000 | 0.630 / 1.000 |
| M4a | 0.896 / 1.000 | 0.847 / 1.000 | 0.174 / 1.000 | 0.710 / 1.000 | 0.939 / 1.000 |
| M4b | 0.904 / 1.000 | 0.806 / 1.000 | 0.493 / 1.000 | 0.942 / 1.000 | 0.984 / 1.000 |
| M5 | 0.741 / 1.000 | 0.712 / 1.000 | 0.611 / 1.000 | 0.856 / 1.000 | 0.419 / 1.000 |
| M6 | 0.046 / 0.413 | 0.153 / 1.000 | 0.803 / 1.000 | 0.013 / 0.121 | 0.020 / 0.180 |
| M7 | 0.203 / 1.000 | 0.173 / 1.000 | 0.961 / 1.000 | 0.870 / 1.000 | 0.764 / 1.000 |
| M1c |  | 0.0001 / - |  |  |  |
| B3c |  | 0.946 / 0.946 |  |  |  |
| B4c |  | 0.130 / 0.259 |  |  |  |

Verdicts:
* **B1 price stays** is far worse everywhere (+80-125%): the model adds real information about how far extremes extend.
* **M0 vs M1** (c = 1 vs fitted c): no difference in the 15-minute sample (-0.1%); in hourly Final c = 1 is 2.9% worse than the fitted c (about 0.875), so calibration matters there. The fitted c is not stable across samples (T12: about 1.0 for the 15-minute sample, 0.85-0.875 for hourly), a +-15% uncertainty on the scale.
* **M2, M3 (realised vol / range so far), M4 (day-ahead EWMA), M5 (both), M7 (3 time buckets):** no improvement after Holm in any window. Best raw cases: M3a -0.7% (15-minute official, raw p 0.38) and -0.8% (hourly Final, raw p 0.21).
* **M6 (one c per quantile level):** consistently slightly better (-1.0% 15-minute official, -2.1% 15-minute Yahoo, -0.6% hourly Final, -1.2% hourly post-closing-auction), raw p 0.15 / 0.046 / 0.013 / 0.020 but Holm 1.0 / 0.41 / 0.12 / 0.18: **not an established improvement** and not adopted.
* **B2 (unconditional empirical extension):** M1 is better by 18% (hourly Final, p < 0.001), 10% (15-minute Yahoo, raw p 0.04, Holm 0.12) and 4% (15-minute official, p 0.19): knowing where the price sits inside the day's range matters.
* **B4 (replay of other sessions' actual remaining paths):** M1 is better by 2.5% in hourly Final (p 0.014); not distinguishable elsewhere (15-minute +1.1% / +2.0%; hourly post-closing-auction B4 is 2.2% better, p of M1 better 0.79).
* **B3 (constant variance rate):** discussed in Section 1, point 4.
* **M1+off (add the mean offset to every quantile)** is worse than M1 on the official target (+1.3%, n = 39); **M1c (add the offset DISTRIBUTION; post-hoc)** is better: -3.4% (DM p = 0.0001). B3c (constant-rate model plus the same offsets) is 0.7% better than M1c (p that M1c is better 0.95) and B4c is 1.9% worse (raw p 0.13, Holm 0.26), B2 is 8.0% worse (raw p 0.06, Holm 0.19). So the offset treatment is what matters on the official target; the profile model is not shown to be better than simpler structures in the 39-session sample.

### 4.3 Coverage of the printed bands, by checkpoint (the requested table)

What the tool prints are one-sided values: for the high "half the time it ends at or below X, nine times in ten at or below Y" (it can not end below the running high), for the low the mirror image. Reason for this choice (deviation from the pre-fixed central band, Section 6): the final high has an atom at the running high, so the central [q25, q75] / [q05, q95] band is mostly [running high, upper value] anyway, and its true probability is above the stated one whenever the atom exceeds 5% / 25%. The central-band versions are in the CSVs (`band == central`).

**T4a. 15-minute sample, nested leave-one-session-out, OFFICIAL NSE high/low, model M1c (printed bands: 'ends at or below the 50% / 90% value' for the high, 'at or above' for the low). hits/n = coverage (Kupiec p vs the stated level)**

| checkpoint | high 50% | low 50% | high 90% | low 90% |
|---|---|---|---|---|
| 09:45 | 23/39 = 0.59 (p 0.26) | 19/39 = 0.49 (p 0.87) | 34/39 = 0.87 (p 0.57) | 36/39 = 0.92 (p 0.62) |
| 10:30 | 22/39 = 0.56 (p 0.42) | 20/39 = 0.51 (p 0.87) | 36/39 = 0.92 (p 0.62) | 33/39 = 0.85 (p 0.29) |
| 11:30 | 19/39 = 0.49 (p 0.87) | 22/39 = 0.56 (p 0.42) | 35/39 = 0.90 (p 0.96) | 32/39 = 0.82 (p 0.13) |
| 12:30 | 22/39 = 0.56 (p 0.42) | 21/39 = 0.54 (p 0.63) | 34/39 = 0.87 (p 0.57) | 31/39 = 0.79 (p 0.05) |
| 13:15 | 20/39 = 0.51 (p 0.87) | 23/39 = 0.59 (p 0.26) | 34/39 = 0.87 (p 0.57) | 34/39 = 0.87 (p 0.57) |
| 14:00 | 21/39 = 0.54 (p 0.63) | 27/39 = 0.69 (p 0.01) | 33/39 = 0.85 (p 0.29) | 35/39 = 0.90 (p 0.96) |
| 14:30 | 21/39 = 0.54 (p 0.63) | 23/39 = 0.59 (p 0.26) | 34/39 = 0.87 (p 0.57) | 36/39 = 0.92 (p 0.62) |
| 15:00 | 19/39 = 0.49 (p 0.87) | 23/39 = 0.59 (p 0.26) | 34/39 = 0.87 (p 0.57) | 36/39 = 0.92 (p 0.62) |

Contrast: the same model without the offset (plain Yahoo extremes) against the NSE figures:

**T4b. Same sample and target but the bands taken from the plain Yahoo-basis model M1 (no Yahoo-to-NSE offset; its multiplier c is fitted against the NSE figures, the most favourable version of the plain model; with the Yahoo-fitted c the 90% values held 70% / 72% pooled)**

| checkpoint | high 50% | low 50% | high 90% | low 90% |
|---|---|---|---|---|
| 09:45 | 16/39 = 0.41 (p 0.26) | 17/39 = 0.44 (p 0.42) | 36/39 = 0.92 (p 0.62) | 36/39 = 0.92 (p 0.62) |
| 10:30 | 13/39 = 0.33 (p 0.04) | 16/39 = 0.41 (p 0.26) | 34/39 = 0.87 (p 0.57) | 32/39 = 0.82 (p 0.13) |
| 11:30 | 12/39 = 0.31 (p 0.01) | 17/39 = 0.44 (p 0.42) | 34/39 = 0.87 (p 0.57) | 31/39 = 0.79 (p 0.05) |
| 12:30 | 12/39 = 0.31 (p 0.01) | 15/39 = 0.38 (p 0.15) | 30/39 = 0.77 (p 0.02) | 26/39 = 0.67 (p 0.00) |
| 13:15 | 13/39 = 0.33 (p 0.04) | 16/39 = 0.41 (p 0.26) | 26/39 = 0.67 (p 0.00) | 29/39 = 0.74 (p 0.01) |
| 14:00 | 13/39 = 0.33 (p 0.04) | 17/39 = 0.44 (p 0.42) | 23/39 = 0.59 (p 0.00) | 30/39 = 0.77 (p 0.02) |
| 14:30 | 15/39 = 0.38 (p 0.15) | 14/39 = 0.36 (p 0.08) | 21/39 = 0.54 (p 0.00) | 27/39 = 0.69 (p 0.00) |
| 15:00 | 13/39 = 0.33 (p 0.04) | 12/39 = 0.31 (p 0.01) | 18/39 = 0.46 (p 0.00) | 22/39 = 0.56 (p 0.00) |

Structure test (target = the Yahoo bars' own final extreme, no data-source offset). The coverage here is judged against the model-implied probability (higher than the stated level wherever the value collapses onto the running extreme, T4f):

**T4c. Same sample, Yahoo-bars final extreme as the target (structure test, no data-source offset), model M1; observed coverage vs the model-implied nominal coverage (higher than the stated level wherever the band collapses on the running extreme, because the running extreme itself then has probability above the stated level), Kupiec p vs the model-implied nominal**

| checkpoint | high 50% | low 50% | high 90% | low 90% |
|---|---|---|---|---|
| 09:45 | 28/39 = 0.72 vs 0.58 (p 0.07) | 23/39 = 0.59 vs 0.56 (p 0.74) | 34/39 = 0.87 vs 0.90 (p 0.57) | 36/39 = 0.92 vs 0.90 (p 0.62) |
| 10:30 | 28/39 = 0.72 vs 0.60 (p 0.12) | 23/39 = 0.59 vs 0.60 (p 0.94) | 35/39 = 0.90 vs 0.90 (p 0.95) | 33/39 = 0.85 vs 0.90 (p 0.29) |
| 11:30 | 29/39 = 0.74 vs 0.64 (p 0.16) | 27/39 = 0.69 vs 0.62 (p 0.36) | 35/39 = 0.90 vs 0.90 (p 0.93) | 32/39 = 0.82 vs 0.90 (p 0.12) |
| 12:30 | 31/39 = 0.79 vs 0.70 (p 0.18) | 27/39 = 0.69 vs 0.64 (p 0.46) | 36/39 = 0.92 vs 0.91 (p 0.76) | 32/39 = 0.82 vs 0.91 (p 0.07) |
| 13:15 | 33/39 = 0.85 vs 0.75 (p 0.14) | 29/39 = 0.74 vs 0.64 (p 0.18) | 36/39 = 0.92 vs 0.92 (p 0.94) | 36/39 = 0.92 vs 0.91 (p 0.83) |
| 14:00 | 33/39 = 0.85 vs 0.79 (p 0.37) | 34/39 = 0.87 vs 0.68 (p 0.01) | 36/39 = 0.92 vs 0.94 (p 0.74) | 37/39 = 0.95 vs 0.92 (p 0.49) |
| 14:30 | 37/39 = 0.95 vs 0.82 (p 0.02) | 35/39 = 0.90 vs 0.76 (p 0.03) | 37/39 = 0.95 vs 0.95 (p 0.98) | 39/39 = 1.00 vs 0.93 (p 0.02) |
| 15:00 | 36/39 = 0.92 vs 0.88 (p 0.35) | 35/39 = 0.90 vs 0.81 (p 0.15) | 37/39 = 0.95 vs 0.96 (p 0.72) | 39/39 = 1.00 vs 0.95 (p 0.04) |

**T4f. Share of sessions where the printed band is collapsed onto the running extreme (M1, Yahoo basis, 15-minute sample), by checkpoint**

| checkpoint | high 50% | high 90% | low 50% | low 90% |
|---|---|---|---|---|
| 09:45 | 0.410 | 0.000 | 0.308 | 0.026 |
| 10:30 | 0.513 | 0.051 | 0.436 | 0.026 |
| 11:30 | 0.615 | 0.051 | 0.410 | 0.077 |
| 12:30 | 0.744 | 0.154 | 0.436 | 0.179 |
| 13:15 | 0.769 | 0.359 | 0.462 | 0.205 |
| 14:00 | 0.744 | 0.462 | 0.564 | 0.231 |
| 14:30 | 0.769 | 0.590 | 0.641 | 0.385 |
| 15:00 | 0.897 | 0.692 | 0.769 | 0.538 |

Hourly walk-forward, same structure test (n = 306 sessions in Final per cell; n = 43 post-closing-auction):

**T4d. Hourly walk-forward, Final window (n=306 sessions), Yahoo-hourly-bars final extreme, model M1**

| checkpoint | high 50% | low 50% | high 90% | low 90% |
|---|---|---|---|---|
| 10:15 | 204/306 = 0.67 vs 0.57 (p 0.00) | 201/306 = 0.66 vs 0.59 (p 0.01) | 284/306 = 0.93 vs 0.90 (p 0.11) | 275/306 = 0.90 vs 0.90 (p 0.81) |
| 11:15 | 218/306 = 0.71 vs 0.63 (p 0.00) | 213/306 = 0.70 vs 0.63 (p 0.01) | 279/306 = 0.91 vs 0.91 (p 0.71) | 281/306 = 0.92 vs 0.91 (p 0.48) |
| 12:15 | 224/306 = 0.73 vs 0.69 (p 0.10) | 221/306 = 0.72 vs 0.67 (p 0.07) | 282/306 = 0.92 vs 0.91 (p 0.66) | 279/306 = 0.91 vs 0.91 (p 0.87) |
| 13:15 | 239/306 = 0.78 vs 0.75 (p 0.15) | 230/306 = 0.75 vs 0.72 (p 0.22) | 286/306 = 0.93 vs 0.93 (p 0.54) | 288/306 = 0.94 vs 0.92 (p 0.22) |
| 14:15 | 253/306 = 0.83 vs 0.80 (p 0.17) | 250/306 = 0.82 vs 0.77 (p 0.03) | 290/306 = 0.95 vs 0.94 (p 0.45) | 293/306 = 0.96 vs 0.93 (p 0.07) |
| 15:15 | 281/306 = 0.92 vs 0.92 (p 0.83) | 281/306 = 0.92 vs 0.90 (p 0.38) | 293/306 = 0.96 vs 0.98 (p 0.06) | 299/306 = 0.98 vs 0.97 (p 0.49) |

**T4e. Hourly walk-forward, post closing-auction sessions (n=43), model M1**

| checkpoint | high 50% | low 50% | high 90% | low 90% |
|---|---|---|---|---|
| 10:15 | 31/43 = 0.72 vs 0.59 (p 0.07) | 24/43 = 0.56 vs 0.58 (p 0.82) | 40/43 = 0.93 vs 0.90 (p 0.51) | 35/43 = 0.81 vs 0.90 (p 0.09) |
| 11:15 | 32/43 = 0.74 vs 0.67 (p 0.26) | 26/43 = 0.60 vs 0.60 (p 0.99) | 37/43 = 0.86 vs 0.91 (p 0.32) | 36/43 = 0.84 vs 0.90 (p 0.16) |
| 12:15 | 33/43 = 0.77 vs 0.77 (p 0.98) | 30/43 = 0.70 vs 0.60 (p 0.17) | 39/43 = 0.91 vs 0.92 (p 0.76) | 36/43 = 0.84 vs 0.91 (p 0.12) |
| 13:15 | 36/43 = 0.84 vs 0.83 (p 0.91) | 29/43 = 0.67 vs 0.65 (p 0.75) | 40/43 = 0.93 vs 0.94 (p 0.82) | 38/43 = 0.88 vs 0.92 (p 0.45) |
| 14:15 | 38/43 = 0.88 vs 0.86 (p 0.69) | 34/43 = 0.79 vs 0.72 (p 0.29) | 41/43 = 0.95 vs 0.95 (p 0.98) | 41/43 = 0.95 vs 0.93 (p 0.45) |
| 15:15 | 43/43 = 1.00 vs 0.97 (p 0.11) | 43/43 = 1.00 vs 0.97 (p 0.10) | 43/43 = 1.00 vs 0.99 (p 0.28) | 43/43 = 1.00 vs 0.98 (p 0.19) |

Counts of cells with Kupiec p < 0.05 against the model-implied probability: 15-minute Yahoo target 5 of 32 cells; hourly Final 5 of 24 (all on the "half the time" value, the high being in more often than stated at 10:15-11:15 and the low at 10:15-11:15 and 14:15); hourly Validation 2 of 24; hourly post-closing-auction 0 of 24. Against the stated level, M1c on the official target: 1 of 32; plain M1 on the official target: 17 of 32.

### 4.4 Pooled coverage and dependence between checkpoints

Checkpoints of one session are strongly dependent: the average correlation between the hit indicators of different checkpoints in a session is about 0.3-0.6 (last column), so 8 checkpoints x 39 sessions is far fewer than 312 independent observations; the intervals are session-cluster bootstrap (resampling whole sessions), the effective n is about 39.

For the rows with the Yahoo-bars or hourly target the model-implied probability of the one-sided value is above the stated level wherever the value collapses onto the running extreme (T4f), so those rows are to be read against T4c-T4e, not against 50% / 90%.

**T5. Pooled coverage over all checkpoints (session-cluster bootstrap 95% interval in brackets) and the average correlation between the checkpoints' hit indicators inside a session**

| sample / window | target | variant | n sessions | high 50% | low 50% | high 90% | low 90% | mean within-session hit corr (90% high) |
|---|---|---|---|---|---|---|---|---|
| 15min LOO nested / All 39 sessions (all in Fina | official NSE | M1c | 39 | 0.54 [0.41, 0.65] | 0.57 [0.46, 0.68] | 0.88 [0.80, 0.95] | 0.88 [0.80, 0.94] | 0.50 |
| 15min LOO nested / All 39 sessions (all in Fina | official NSE | B3c | 39 | 0.54 [0.42, 0.65] | 0.57 [0.45, 0.68] | 0.88 [0.81, 0.95] | 0.87 [0.79, 0.94] | 0.47 |
| 15min LOO nested / All 39 sessions (all in Fina | official NSE | B4c | 39 | 0.47 [0.35, 0.60] | 0.50 [0.38, 0.62] | 0.89 [0.81, 0.95] | 0.87 [0.80, 0.94] | 0.44 |
| 15min LOO nested / All 39 sessions (all in Fina | official NSE | M1 | 39 | 0.34 [0.23, 0.46] | 0.40 [0.29, 0.50] | 0.71 [0.62, 0.80] | 0.75 [0.65, 0.84] | 0.38 |
| 15min LOO nested / All 39 sessions (all in Fina | official NSE | B2 | 39 | 0.50 [0.38, 0.62] | 0.50 [0.39, 0.62] | 0.88 [0.80, 0.96] | 0.88 [0.79, 0.95] | 0.60 |
| 15min LOO nested / 31 sessions that have a 15:1 | official NSE | M1c | 31 | 0.50 [0.37, 0.64] | 0.61 [0.48, 0.74] | 0.87 [0.77, 0.95] | 0.89 [0.81, 0.96] | 0.49 |
| 15min LOO nested / 31 sessions that have a 15:1 | official NSE | M1 | 31 | 0.28 [0.17, 0.41] | 0.43 [0.31, 0.54] | 0.68 [0.57, 0.79] | 0.74 [0.63, 0.85] | 0.37 |
| 15min LOO nested / All 39 sessions (all in Fina | Yahoo-bars | M1 | 39 | 0.82 [0.71, 0.91] | 0.75 [0.64, 0.84] | 0.92 [0.84, 0.97] | 0.91 [0.85, 0.97] | 0.58 |
| 15min chronological (past sessions only) / chronological, scored 2026-0 | official NSE | M1c | 19 | 0.54 [0.36, 0.71] | 0.56 [0.39, 0.72] | 0.85 [0.73, 0.95] | 0.88 [0.77, 0.97] | 0.36 |
| 15min chronological (past sessions only) / chronological, scored 2026-0 | official NSE | M1 | 19 | 0.30 [0.15, 0.47] | 0.39 [0.25, 0.53] | 0.68 [0.53, 0.81] | 0.72 [0.59, 0.85] | 0.33 |
| hourly walk-forward / Final (2025-07-01 on) | Yahoo hourly-bars | M1 | 306 | 0.77 [0.73, 0.81] | 0.76 [0.72, 0.80] | 0.93 [0.91, 0.95] | 0.93 [0.91, 0.95] | 0.43 |
| hourly walk-forward / Validation (scored, before 2 | Yahoo hourly-bars | M1 | 123 | 0.73 [0.66, 0.79] | 0.75 [0.68, 0.81] | 0.93 [0.89, 0.96] | 0.90 [0.85, 0.93] | 0.40 |
| hourly walk-forward / Post-closing-auction (2026-0 | Yahoo hourly-bars | M1 | 43 | 0.83 [0.73, 0.91] | 0.72 [0.62, 0.81] | 0.93 [0.87, 0.98] | 0.89 [0.81, 0.95] |  |

### 4.5 "Is the high already in?" reliability

Event: the price never exceeds the running high (low) again (Yahoo-bars basis). Predicted -> observed share in each probability bin; Brier score of the model vs a leave-one-out constant per-checkpoint base rate.

**T8a. P(running extreme is already the final one): predicted -> observed, 15-minute sample (39 sessions x 8 checkpoints = 312 states)**

| side | n sessions | n states | mean predicted | observed share | Brier model | Brier checkpoint base rate (LOO) | bin [0.0,0.1) | bin [0.1,0.3) | bin [0.3,0.5) | bin [0.5,0.7) | bin [0.7,0.9) | bin [0.9,1.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 39 | 312 | 0.648 | 0.744 | 0.157 | 0.183 | 0.05 -> 0.07 (n 15) | 0.20 -> 0.32 (n 38) | 0.41 -> 0.72 (n 46) | 0.62 -> 0.80 (n 65) | 0.81 -> 0.89 (n 56) | 0.98 -> 0.91 (n 92) |
| low | 39 | 312 | 0.526 | 0.548 | 0.129 | 0.225 | 0.06 -> 0.09 (n 34) | 0.19 -> 0.20 (n 75) | 0.40 -> 0.35 (n 46) | 0.61 -> 0.68 (n 38) | 0.80 -> 0.85 (n 54) | 0.98 -> 1.00 (n 65) |

**T8b. Same, 31 sessions with a 15:15 bar**

| side | n sessions | n states | mean predicted | observed share | Brier model | Brier checkpoint base rate (LOO) | bin [0.0,0.1) | bin [0.1,0.3) | bin [0.3,0.5) | bin [0.5,0.7) | bin [0.7,0.9) | bin [0.9,1.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 31 | 248 | 0.672 | 0.770 | 0.137 | 0.178 | 0.06 -> 0.00 (n 11) | 0.20 -> 0.24 (n 25) | 0.42 -> 0.76 (n 34) | 0.62 -> 0.83 (n 53) | 0.81 -> 0.90 (n 48) | 0.98 -> 0.94 (n 77) |
| low | 31 | 248 | 0.481 | 0.488 | 0.130 | 0.228 | 0.06 -> 0.09 (n 32) | 0.19 -> 0.18 (n 66) | 0.39 -> 0.32 (n 44) | 0.60 -> 0.65 (n 26) | 0.80 -> 0.86 (n 35) | 0.98 -> 1.00 (n 45) |

**T8c. Same, hourly Final window (306 sessions, 6 checkpoints)**

| side | n sessions | n states | mean predicted | observed share | Brier model | Brier checkpoint base rate (LOO) | bin [0.0,0.1) | bin [0.1,0.3) | bin [0.3,0.5) | bin [0.5,0.7) | bin [0.7,0.9) | bin [0.9,1.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 306 | 1836 | 0.650 | 0.708 | 0.131 | 0.194 | 0.05 -> 0.05 (n 88) | 0.20 -> 0.25 (n 236) | 0.40 -> 0.53 (n 298) | 0.60 -> 0.73 (n 288) | 0.80 -> 0.89 (n 332) | 0.98 -> 0.97 (n 594) |
| low | 306 | 1836 | 0.617 | 0.644 | 0.116 | 0.211 | 0.05 -> 0.04 (n 110) | 0.19 -> 0.19 (n 323) | 0.40 -> 0.43 (n 271) | 0.60 -> 0.66 (n 267) | 0.80 -> 0.88 (n 292) | 0.98 -> 0.99 (n 573) |

**T8d. Same, hourly post closing-auction (43 sessions)**

| side | n sessions | n states | mean predicted | observed share | Brier model | Brier checkpoint base rate (LOO) | bin [0.0,0.1) | bin [0.1,0.3) | bin [0.3,0.5) | bin [0.5,0.7) | bin [0.7,0.9) | bin [0.9,1.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 43 | 258 | 0.737 | 0.787 | 0.114 | 0.162 | 0.06 -> 0.00 (n 7) | 0.18 -> 0.17 (n 18) | 0.41 -> 0.55 (n 31) | 0.60 -> 0.83 (n 42) | 0.81 -> 0.84 (n 50) | 0.98 -> 0.96 (n 110) |
| low | 43 | 258 | 0.564 | 0.562 | 0.119 | 0.200 | 0.06 -> 0.10 (n 20) | 0.19 -> 0.15 (n 61) | 0.40 -> 0.36 (n 39) | 0.60 -> 0.65 (n 34) | 0.80 -> 0.80 (n 30) | 0.98 -> 1.00 (n 74) |

Reading: for the low the stated and observed shares differ by 0-8 points in the middle bins (15-minute: 0.40 -> 0.35, 0.61 -> 0.68, 0.80 -> 0.85; hourly Final: 0.60 -> 0.66, 0.80 -> 0.88); for the high the middle bins are too low by 8-31 points in the 15-minute sample (e.g. 0.41 -> 0.72, n = 46 states from 39 sessions) and by 9-13 points in hourly Final (0.40 -> 0.53, 0.60 -> 0.73, 0.80 -> 0.89; n = 298, 288, 332 states from 306 sessions). The model beats the base rate in Brier score for both sides in all four samples (e.g. hourly Final high 0.131 vs 0.194, 15-minute low 0.129 vs 0.225). The 15-minute high-side miscalibration also holds in the 31 sessions that have a 15:15 bar (0.42 -> 0.76), so it is not caused by the 8 sessions with the merged closing print.

### 4.6 Typical miss in rupees

**T9. Typical miss in rupees at each checkpoint vs the NSE official final high/low (15-minute sample, 39 sessions, nested leave-one-out, model M1c's median). 'stays' = assume the final high (low) equals the running high (low)**

| time | high: 'stays' mean / median miss Rs | high: model median mean / median miss Rs | low: 'stays' mean / median miss Rs | low: model median mean / median miss Rs |
|---|---|---|---|---|
| 09:45 | 19.7 / 4.0 | 17.5 / 6.2 | 22.2 / 7.2 | 18.3 / 12.3 |
| 10:30 | 15.8 / 2.5 | 15.0 / 7.0 | 18.7 / 5.5 | 17.5 / 8.8 |
| 11:30 | 13.3 / 1.4 | 11.4 / 2.1 | 17.0 / 4.3 | 17.2 / 8.6 |
| 12:30 | 9.4 / 1.4 | 8.6 / 2.0 | 14.9 / 4.1 | 13.4 / 3.3 |
| 13:15 | 8.7 / 0.8 | 8.5 / 1.8 | 12.1 / 2.6 | 10.8 / 3.3 |
| 14:00 | 6.7 / 0.7 | 6.2 / 1.3 | 5.3 / 1.8 | 4.9 / 2.0 |
| 14:30 | 4.2 / 0.4 | 5.3 / 1.0 | 4.3 / 1.5 | 3.7 / 1.3 |
| 15:00 | 2.7 / 0.3 | 3.2 / 0.6 | 2.4 / 0.8 | 2.1 / 0.8 |

The model's median does little better than "the high stays": the final-high distribution has an atom at the running high, so the median is the running high whenever P(in) > 50% (which is most of the day). The value of the tool is in the probabilities and in the 90% value, not in a point estimate. The hourly version (Final window, n = 306 sessions, `results/live_hl_miss_by_slot_hourly.csv`) shows the same pattern: mean miss of "the high stays" Rs 15.0 at 10:15 falling to Rs 1.0 at 15:15.

### 4.7 Replay of Thu 15 Oct 2026, and the 1-minute check

15 Oct: NSE open 3,342.0, high 3,445.0, low 3,315.2, close 3,428.0. Yahoo 1-minute bars (348 bars): high 3,445.0, low 3,315.2, difference Rs 0.00 / 0.00. The low was made at 09:16 (it was in at every checkpoint). The high was made at 14:04, after a jump that began about 13:33 (price Rs 3,340.9 at 13:31, volume 40-fold higher in the next minutes); the price at the 13:15 checkpoint was Rs 3,348.9.

**T10. Replay of Thu 15 Oct 2026 (bars that started before the time shown; c from the leave-one-out fit that excludes 15 Oct)**

| asof | price_then | run_high_yahoo | run_low_yahoo | p_high_in | p_low_in | high_at_or_below_50 | high_at_or_below_90 | official_high | high_le_q50 | high_le_q90 | low_at_or_above_50 | low_at_or_above_90 | official_low | low_ge_q50 | low_ge_q90 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 09:45 | 3355.1 | 3363.6 | 3315.2 | 0.13 | 0.56 | 3390.9 | 3441.7 | 3445.0 | False | False | 3312.7 | 3270.4 | 3315.2 | True | True |
| 10:30 | 3372.0 | 3377.1 | 3315.2 | 0.09 | 0.77 | 3405.1 | 3452.0 | 3445.0 | False | True | 3314.1 | 3293.7 | 3315.2 | True | True |
| 11:30 | 3364.6 | 3378.9 | 3315.2 | 0.26 | 0.75 | 3394.9 | 3437.6 | 3445.0 | False | False | 3313.9 | 3293.0 | 3315.2 | True | True |
| 12:30 | 3344.0 | 3378.9 | 3315.2 | 0.64 | 0.56 | 3380.3 | 3407.6 | 3445.0 | False | False | 3312.7 | 3281.4 | 3315.2 | True | True |
| 13:15 | 3348.9 | 3378.9 | 3315.2 | 0.60 | 0.66 | 3381.0 | 3408.4 | 3445.0 | False | False | 3313.7 | 3290.3 | 3315.2 | True | True |
| 14:00 | 3411.4 | 3423.4 | 3315.2 | 0.32 | 1.00 | 3432.1 | 3460.9 | 3445.0 | False | True | 3314.5 | 3312.5 | 3315.2 | True | True |
| 14:30 | 3432.7 | 3445.0 | 3315.2 | 0.39 | 1.00 | 3450.3 | 3473.9 | 3445.0 | True | True | 3314.5 | 3312.5 | 3315.2 | True | True |
| 15:00 | 3437.0 | 3445.0 | 3315.2 | 0.35 | 1.00 | 3450.0 | 3466.9 | 3445.0 | True | True | 3314.5 | 3312.5 | 3315.2 | True | True |

The high fell outside the "nine times in ten" value at 09:45 (by Rs 3.3), 11:30, 12:30, 13:15: a news-type jump is exactly what a Gaussian random walk with the average variance profile does not anticipate (one session, so no inference).

**T11. 1-minute bars, 7 sessions, state rebuilt every 5 minutes 09:20-15:15, Yahoo 1-minute final extreme as the target, Yahoo-basis M1 with the leave-one-out profile and c (descriptive; n = 7 sessions)**

| side | sessions | 5-minute marks per session | 50% value hit | 90% value hit | 90% bootstrap 95% | model-implied 90% nominal | mean predicted P(in) | observed share in |
|---|---|---|---|---|---|---|---|---|
| high | 7 | 72 | 0.65 | 0.80 | [0.62, 0.95] | 0.91 | 0.58 | 0.57 |
| low | 7 | 72 | 0.69 | 1.00 | [0.99, 1.00] | 0.92 | 0.54 | 0.55 |

**T13. 15-minute bars rebuilt from the cached 1-minute bars (live_nowcast.to_15m) vs the 15-minute file used for the profile**

| sessions | bars_compared | max_abs_high_diff | max_abs_low_diff | max_abs_close_diff | bars_with_any_difference_over_0.06 |
|---|---|---|---|---|---|
| 7 | 173 | 0.00 | 0.00 | 0.00 | 0 |

The 1-minute check (7 sessions, 72 marks each) is descriptive: the 90% value for the high held 80% (cluster bootstrap 62-95%) against a model-implied 91% (the 15 Oct jump is in this sample), for the low 100% against 92%; P(in) calibrated well on average (0.58 predicted vs 0.57 observed for the high, 0.54 vs 0.55 for the low).

### 4.8 Sensitivities

* **Strictly chronological 15-minute run** (only past sessions for the profile, c and offsets; the first 20 sessions fit-only, 19 scored sessions 2026-09-15 to 2026-10-15): pooled "half the time" 54% / 56%, "nine in ten" 85% / 88% (high / low) for M1c, 30% / 39% and 68% / 72% for plain M1 (row "15min chronological" of T5). Same picture as leave-one-out, n = 19 only; pinball: M1c 2.84 vs M1 2.91 Rs (-2.5%, raw p 0.02).
* **Sessions without a 15:15 bar excluded from scoring** (31 sessions): M1c 50% / 61% and 87% / 89%.
* **c** (T12): see above.

**T12. Fitted volatility multiplier c (model M1)**

| sample | min | median | max |
|---|---|---|---|
| 15-minute LOO, Yahoo-target fit (39 values) | 1.000 | 1.025 | 1.075 |
| 15-minute LOO, official-target fit | 1.050 | 1.075 | 1.125 |
| hourly walk-forward, all scored | 0.700 | 0.875 | 0.975 |
| hourly walk-forward, post-CAS | 0.850 | 0.850 | 0.875 |

## 5. What failed, plainly

1. Plain Yahoo extremes as the estimate of the NSE figure: bands too narrow (71% / 75% instead of 90%), worst late in the day.
2. Realised-vol-so-far scaling: no gain, worse at full weight. Day-ahead EWMA sigma: no gain. Both together: no gain.
3. One multiplier per quantile level (M6): small consistent gain, not significant after Holm; not adopted.
4. Profile vs constant variance rate: not separable with 39 sessions (nominally the wrong way), clearly helpful only in the 306-session hourly Final window.
5. "Is the high in" probability for the high is too low (conservative) by 8-31 points in the middle range (15-minute sample) and 9-13 points (hourly Final).
6. The scale multiplier is not stable between samples (1.0 vs 0.875).
7. A news jump (15 Oct, about 13:30) puts the final high far outside the bands set before it.
8. The mean-offset fix (M1+off) made things worse; only the offset distribution worked.

## 6. Deviations from the pre-fixed section (all of them)

* **Added after seeing results (post-hoc):** M1c, B3c, B4c (offset treatment, added when the plain-Yahoo bands on the official target were seen to collapse at 15:00: 46% / 56% coverage of the 90% value); the 31-session subset; the chronological 15-minute sensitivity; the 1-minute descriptive check; the 1-minute vs 15-minute consistency check; the P(in) reliability tables; the clustering correlation.
* **Printed bands:** pre-fixed as central [q25, q75] / [q05, q95]; the tool prints one-sided "at or below / at or above" values because the lower end of the central band is the running extreme itself in most states. Central-band coverage for M1 is in `results/live_hl_backtest_coverage_*.csv` (`band == central`): on the official target pooled 52% / 48% (50% band) and 76% / 82% (90% band) for high / low (n = 39); on the Yahoo target 82% / 74% and 94% / 94%; their model-implied probabilities are higher than the stated levels.
* **Official-target c** (pre-fixed M1 was fitted on the official target) vs **Yahoo-target c** (used for M1c and the tool): c = 1.075 vs 1.025; both reported (T12).
* The pre-fixed text said the closing print is "at 15:28-15:29"; the 1-minute bars show it between 15:14 and 15:29.
* The pre-fixed hourly bucket edges for M7 were not written down: used 10:15-11:15 / 12:15-13:15 / 14:15-15:15; the 15-minute buckets are as fixed (09:30-11:00 / 11:15-13:00 / 13:15-15:00).

## 7. Honest limits

* **39 sessions, 18 Aug to 15 Oct 2026**, one regime (post-closing-auction), 8 checkpoints each and strongly dependent (hit correlation about 0.3-0.6): coverage numbers carry +-8 (50% level) and +-5 (90% level) points of sampling noise per checkpoint cell and about +-12 (50% level) / +-7 (90% level) points pooled (session-cluster bootstrap). The calibration of the live tool rests on this sample.
* Leave-one-out uses later sessions to calibrate earlier ones; the chronological check has n = 19.
* The Yahoo-to-NSE offsets come from the same 39 sessions; the hourly sample suggests a fatter tail than 39 sessions show (Section 4.1). The sensitivity of the bands to using the hourly-sample offsets instead was not tested.
* The model is Gaussian with a fixed average variance profile; jumps (news, circulars, block deals) are not modelled. The Q2 board meeting (4 Nov) and the pending SEBI settlement-method decision (`FORECAST_REPORT_V2.md` Sections 6-7) can produce such a day.
* Zero drift. `live_nowcast.py` found price rising about 0.2% from 15:00 to the close in its sample; not used here.
* P(in) for the high is conservative (Section 4.5); the "chance of a further Rs 5 / 10 / 20 / 40" figures printed by the tool are not separately validated (they follow from the same distribution that was validated at the 50% / 90% / 95% values).
* The profile is the 15-minute profile of 39 sessions (as in `live_nowcast.py`); it is noisy slot by slot. Sessions with a merged closing print (8 of 39) contribute only to slots 0-22 of the profile (`live_nowcast.profile` rule).
* Yahoo's 1-minute window is about 7 sessions; the live tool depends on an unofficial endpoint (429s, outages, bar timestamps).
* Nothing here is investment advice, and no trading rule was tested.

## 8. Contradictions with earlier project statements

* `docs/INPUT_AUDIT.md` / `FORECAST_REPORT_V2.md` §1.1: "highs <= NSE high by up to Rs 4.0, lows >= NSE low by up to Rs 4.2". In 39 sessions: up to Rs 5.3 (high, 9 Sep) and Rs 4.5 (low, 3 Sep); hourly bars (479 sessions): 95th percentile Rs 5.0 / 8.5, maximum Rs 46 / 55. The direction (NSE high >= Yahoo high, NSE low <= Yahoo low) held in all 39 sessions.
* The task text says prices are "bonus-adjusted in the processed history"; the OHLC columns of `bse_daily.csv` are as traded (adjustment in `prev` / `ca_factor`).
* `docs/LIVE_TOOLS.md` says that using today's realised volatility did not improve the close nowcast; this work finds the same for the extension of the high and low (no contradiction, an extension to a second target).
* `live_nowcast.py` and `FORECAST_REPORT_V2.md` treat a 1-minute/15-minute high or low as the day's range; this work shows that doing so understates the NSE range by Rs 0.9 + 1.05 on average (up to Rs 6.7 in one session, 9 Sep), enough to break a band that has collapsed onto the running extreme late in the day.

## 9. How to use it (plain words)

* **Before the open:** nothing. The tool needs session bars; it prints a message and exits. (The next-session high/low numbers come from the day-ahead specialist, not from this tool.)
* **During the session:** run `python3 src/live_highlow.py` at any time. Read three things: (1) "the high is probably in (X%)": X% is a floor for the high (Section 4.5); (2) "chance the high is pushed at least Rs 10 / 20 / 40": use it to judge whether a stop or target sitting that far beyond the running high is likely to be touched; (3) "nine times in ten at or below Rs Y": a reference level for the day's extreme, not a limit.
* **Late in the day the room is small:** at 14:00 the NSE final high is on average only Rs 6.7 above the running high (low Rs 5.3), at 15:00 Rs 2.7 (2.4); half of days the high is within Rs 0.7 of the running high (the low within Rs 1.8).
* **Not a direction signal.** "Still has room" says the extreme may extend, not that price will go up or down. Whether any use of these numbers makes money was not tested.
* The tool logs every live call (time, price, running high/low, probabilities, quantiles) to `results/live_hl_log.jsonl` so the calls can be scored later against the NSE figures (published about 16:34 IST).

## 10. Numbers to quote

* Yahoo vs NSE (39 sessions, Aug-Oct 2026): NSE high above Yahoo high by Rs 0.2 median / 0.89 mean / 2.6 (90th pct) / 5.3 max; NSE low below Yahoo low by Rs 0.7 median / 1.05 mean / 2.7 / 4.5; never reversed. 1-minute bars (7 sessions): up to Rs 2.3 / 1.5. On 15 Oct: Rs 0.0 / 0.0.
* NSE-basis bands (M1c), 15-minute sample, leave-one-out, 39 sessions x 8 checkpoints: "half the time" held 54% (high) / 57% (low) [bootstrap 41-65 / 46-68]; "nine times in ten" held 88% / 88% [80-95 / 80-94]. Per checkpoint (n = 39 each): 50% level 19-23 of 39 (high) and 19-27 (low); 90% level 33-36 (high) and 31-36 (low). Plain Yahoo bands on the NSE figures: 71% / 75% at the 90% level (46% / 56% at 15:00).
* Chronological 15-minute check (n = 19 sessions): 85% / 88% at the 90% level.
* Hourly walk-forward (306 Final sessions, Yahoo-hourly truth): the model's own implied probabilities are matched within noise (5 of 24 cells below p = 0.05, all on the 50% value); post-closing-auction (43 sessions) 0 of 24.
* Typical miss (mean, NSE final vs running extreme, 39 sessions), high / low: Rs 19.7 / 22.2 at 09:45; 15.8 / 18.7 at 10:30; 13.3 / 17.0 at 11:30; 9.4 / 14.9 at 12:30; 8.7 / 12.1 at 13:15; 6.7 / 5.3 at 14:00; 4.2 / 4.3 at 14:30; 2.7 / 2.4 at 15:00. Medians: 4.0 / 7.2 at 09:45 down to 0.3 / 0.8 at 15:00.
* "High is in" probability: stated 62% -> observed 81% (15-minute, 167 states / 39 sessions); stated 61% -> 72% (hourly Final, 918 states / 306 sessions). Low: 61% -> 64% and 61% -> 66%.
* No variant beats the base model after Holm (realised vol so far, range so far, day-ahead EWMA, both, per-level c, time-bucket c): best Holm p 0.12 (M6, hourly Final, -0.6%).
* Fitted multiplier c: 1.025 (15-minute, live tool), 1.075 (official-target fit), 0.875 (hourly, 0.85 post-closing-auction).
* 15 Oct replay: NSE H 3,445.0 / L 3,315.2 = Yahoo 1-minute H 3,445.0 / L 3,315.2; the high exceeded the 90% value at 4 of 8 checkpoints.

## 11. Commands to reproduce each number

Run from the repo root (`/home/user/pred_18`). The hourly Yahoo file is the scratchpad copy; the first `--backtest` copied its 7-bar sessions to `results/live_hl_hourly_bars.csv`, so later runs do not need `--hourly`. Yahoo serves 1-minute bars for only about 7 sessions: the 7-15 Oct minute bars are in `results/live_hl_bars_1m.csv` and the 1-minute parts of `--backtest` read that cache.

```
python3 src/live_highlow.py --selftest                                # Section 3 checks: closed form vs Monte-Carlo, profile identical to live_nowcast, state check, no-leak test -> results/live_hl_selftest.json
python3 src/live_highlow.py --replay                                  # fetches Yahoo 1-minute bars, merges them into results/live_hl_bars_1m.csv, writes results/live_hl_replay_latest.csv (T10)
python3 src/live_highlow.py --backtest --hourly /tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/h60_BSE.NS.json
     # -> results/live_hl_backtest_variants.csv (T3a, T3b), live_hl_backtest_coverage_checkpoints.csv (T4), live_hl_backtest_coverage_pooled.csv (T5), live_hl_backtest_p_in_reliability.csv (T8),
     #    live_hl_miss_by_slot_15min.csv / _hourly.csv (T9), live_hl_offsets_yahoo_vs_nse.csv + live_hl_offsets_summary.json (T2, T11, T13), live_hl_check_1m.csv, live_hl_loo_c_15min.csv + live_hl_hourly_c_path.csv (T12),
     #    live_hl_loo_forecasts_15min.csv (every leave-one-out forecast), live_hl_params.json (what the live tool reads)
python3 src/live_highlow.py --asof 12:30 --nosave                     # the example in Section 2
python3 src/live_highlow.py                                           # live call (appends to results/live_hl_log.jsonl)
python3 src/live_highlow.py --now "2026-10-17 10:00" --nosave         # weekend message (also "2026-10-16 08:30" before open, "2026-10-16 10:00" no bars today, "2026-10-15 16:00" after close)
```

The tables in this report were generated from the CSV/JSON files above by a throw-away script (not part of the repo); each cell can be read directly from the files: T3 from `live_hl_backtest_variants.csv` (columns `pinball_Rs_mean`, `pinball_vs_M1_pct`, `dm_p_*`), T4 from `live_hl_backtest_coverage_checkpoints.csv` (`variant`, `band == upto`), T5 from `live_hl_backtest_coverage_pooled.csv`, T8 from `live_hl_backtest_p_in_reliability.csv`, T9 from `live_hl_miss_by_slot_15min.csv`, T2 from `live_hl_offsets_summary.json`.
