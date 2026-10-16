# Specialist C: can the high / low estimates be traded? (NSE:BSE)

*Status: PRE-FIXED SECTION 0 WRITTEN BEFORE ANY EXCURSION, HIT-PROBABILITY, TRADE RESULT, FILL RATE OR PLACEBO WAS COMPUTED (clock at writing: Thu 15 Oct 2026 22:32 IST, sandbox clock 17:01 UTC). What had been looked at before writing it: the project documents and the reports of specialists A and B (their published tables), data facts only (hourly-bar counts per session and which bars are missing, the tick size of the official prices, which dates are in the hourly file but not the daily file, the stored `hl_eval_predictions.csv` column list and its first two rows), and the project's published first-hour finding. No rule's profit and loss, no fill rate, no stop or target hit probability, no excursion quantile and no placebo has been computed. The results sections are appended below this one and nothing above the line "END OF PRE-FIXED SECTION" is edited afterwards.*

## 0. Pre-fixed design

### 0.1 Questions
1. **Part 1 (descriptive, for risk management).** Where do stops and targets of a given size get hit? (maximum favourable and adverse excursion from the open and from 10:15; probability a stop at -x% is touched before a target at +y%, split by volatility regime; how often the open or the first hour holds the day's high or low).
2. **Part 2 (inferential).** Do rules that trade the estimated high / low levels, or simple intraday rules, make money after costs, out of sample? Expected prior: **no edge after costs**.

### 0.2 Data, windows, timestamps
* **Daily bars**: `data/processed/bse_daily.csv` (through 13 Oct 2026) plus `data/processed/bse_daily_extra.csv` (14 and 15 Oct, official NSE bhavcopy). `common.load_bse()` alone ends on 13 Oct; I read both files directly without any network call (the equivalent of `official_bars.load_bse_ext()` minus its download step). 2,390 sessions, 6 Feb 2017 to 15 Oct 2026, last official bar open 3,342.0, high 3,445.0, low 3,315.2, close 3,428.0. Only `prev` is bonus-adjusted (specialist A's finding, confirmed in the file: 7,305 -> 2,358 on the 23 May 2025 ex-date); open / high / low / close are raw traded prices, so every within-day ratio is exact and **rupee amounts are always "percentage x Rs 3,428", never raw differences from before the ex-dates**.
* **Hourly bars**: `h60_BSE.NS.json` (Yahoo, 1-hour, range 2y, 16 Oct 2024 to 15 Oct 2026). Bar k starts at 09:15, 10:15, ..., 15:15 (the last bar is 15 minutes long and holds the closing auction since 3 Aug 2026). Yahoo back-adjusts the hourly prices for the 2:1 bonus of 23 May 2025 (prices before that date are raw / 3): I multiply all hourly prices of sessions before 23 May 2025 by 3 (the project's `ca_factor`), so hourly prices are in official raw units. Only **complete 7-bar sessions that are also in the daily file** are used (the hourly file has 9 six-bar sessions, all after 14 Aug 2026, where the feed omits the 15:15 bar, 3 short or stale dates, and misses the 1 Feb 2026 Budget session).
* **Windows** (by session date, as in the project): Development 2019-01-01 to 2024-06-30 (the project's own Development starts 2019-02; I start at 1 Jan 2019, which adds 33 sessions, because the task asks for 2019-2026), Validation 2024-07-01 to 2025-06-30, **Final 2025-07-01 onward**, **post closing-auction slice (CAS) 2026-08-04 onward** (the first session whose previous close is itself an auction close; 3 Aug is excluded, giving the task's "51 post-CAS sessions"; n is printed beside every CAS number). Hourly-bar rules have no Development window (the file starts in Oct 2024): Validation = hourly sample before 2025-07-01, Final and CAS as above. Rules using the project's model quantiles start on 2020-02-25 (session 750, where the stored model forecasts start), so their Development window is 2020-02-25 to 2024-06-30.
* **Timestamps of every input relative to the decision time**:

| input | used by | known at |
|---|---|---|
| daily open / high / low / close of sessions up to t-1, hence every sigma below | all rules | official bhavcopy ~16:34 IST on t-1 |
| previous official close P0 | gap rule | 15:30 IST on t-1 |
| official open O of session t (NSE pre-open call-auction price) | all open-based rules (entry price, level origin, gap) | 09:08 IST on t (final); the pre-open order window closes 09:08, so an order that depends on the *final* open can only go in as a continuous-session order from 09:15 |
| first hourly bar of session t (open, high, low, close) | fade first hour, opening-range breakout | 10:15 IST on t |
| later hourly bars | breakout trigger; ordering of stop and target hits; outcome | at the bar's end (bar k ends at 09:15 + 60 k minutes) |
| official high, low, close of session t | outcome only (never an input) | 15:30 / 16:34 IST on t |
| stored model quantiles `P_S6_*` (pre-open) | model-level limit orders | close of t-1 (they use only sessions before t) |
| stored model quantiles `W_I6_*` (post-open) | model-level limit orders | 09:08 IST on t (open + sessions before t) |

### 0.3 Past-only estimators (every one is computed from sessions strictly before t)
* All scale estimators are EWMA with lambda = 0.94 of squared values, initialised with the mean square of the first 30 sessions, value used at t computed through t-1 (the project's `S1`, re-implemented here so no fitted model is needed): `sigR` for the close-to-close log return R = ln(C_t/P0_t); `sigG` for the gap G = ln(O/P0); `sigL` for LO = ln(L/O) (<= 0) and `sigH` for HO = ln(H/O) (>= 0), both as root-mean-square. Volatility regime for Part 1 = terciles of `sigR` using **expanding** cut points from the previous sessions only (from session 100; sessions before that are unclassified).
* `sig1h` = EWMA(0.94) root-mean-square of the past first-hour log returns r1 = ln(c1/o1) of the *hourly sample*, needing at least 40 earlier hourly sessions (first traded session about 12 Dec 2024). Because of this burn-in the Validation window of the two first-hour rules is about 6 months long.
* `EMP250` = the trailing 250-session empirical quantile of LO (or HO) of sessions before t.

### 0.4 The eight rules (fixed now; 31 variants in total; the **primary** variant of each rule is the one used for the verdict, the others are neighbours that are all counted in the Holm family)
All trades are intraday (entered and closed the same session), one unit, no pyramiding; at most one trade per session per variant; return = simple return on entry value; shorts earn (entry - exit) / entry. Exit is the **official close** unless stopped out or targeted.

| rule | text | variants (primary in bold) |
|---|---|---|
| **R1** (a) buy limit below the open | resting limit buy at O x (1 - k x sigL); filled only if the day's low trades through the level; exit at the close | **k = 1.0**, 0.5, 1.5 |
| **R2** (b) sell limit above the open | resting limit sell (short) at O x (1 + k x sigH); filled only if the high trades through; exit at the close | **k = 1.0**, 0.5, 1.5 |
| **R3** (c) fade a large first-hour move | z1 = r1 / sig1h; if z1 >= z0 sell short, if z1 <= -z0 buy, at the close of the first hourly bar (10:15 price); exit at the close | **z0 = 1.5**, 1.0, 2.0; plus **R3t**: z0 = 1.5 with a limit target at the open price (fills if the high / low trades through the open price), otherwise close |
| **R4** (d) follow the opening-range breakout | opening range = high and low of the first hourly bar; **R4a** (primary): stop-entry at the range high (long) or low (short) at the first bar from 10:15 to 14:15 that breaks it (ambiguous bar breaking both sides is scored as the losing side), fill at the level; **R4b**: market entry at the close of the first hourly bar (ending 11:15 .. 14:15) that closes beyond the range; exit at the close | **R4a**, R4b |
| **R5** (e) gap reversion | zG = G / sigG; if zG <= -z0 buy, if zG >= z0 sell short, at the official open; exit at the close | **z0 = 1.0**, 0.5, 1.5 |
| **R6** (f) fixed bracket from the open | enter at the official open every session; stop at s%, target at t% (limit); if neither is hit exit at the close. If a session touches both, the **conservative** reading (stop first) is the verdict, the optimistic reading (target first) and the hourly-bar ordering (where available) are sensitivities | long s = 1%, t = 2% (**primary**); long s = 2%, t = 1%; short s = 1%, t = 2%; short s = 2%, t = 1% |
| **R7** buy limit at the *project's estimated low* | buy limit at the stored model quantile of the day's low: post-open `W_I6_L_q25` (nominal fill 25%) = primary; `W_I6_L_q10`; pre-open `P_S6_L_q25`, `P_S6_L_q10` (resting order placed the night before: filled at the open if the open is at or below the level, otherwise at the level when the low trades through); benchmark levels `EMP250` quantile 25% and 10% of LO. Exit at the close | **post q25**, post q10, pre q25, pre q10, EMP250 q25, EMP250 q10 |
| **R8** sell limit at the *project's estimated high* | mirror image with `W_I6_H_q75` (nominal fill 25%) primary, `W_I6_H_q90`, `P_S6_H_q75`, `P_S6_H_q90`, EMP250 quantile 75% and 90% of HO | **post q75**, post q90, pre q75, pre q90, EMP250 q75, EMP250 q90 |

(R7 and R8 use the stored out-of-sample quantiles of `results/hl_eval_predictions.csv` as written by specialist A; I record the file's SHA-256. R7 and R8 are the literal answer to "can the next session's high and low be traded"; R1 and R2 are the same idea with a transparent past-only scale. The 8th slot is not used for anything else.)

### 0.5 Fill and cost conventions
* **Limit orders fill only if the extreme trades through the level.** F0 (primary): low < level (high > level) strictly. F1 (conservative, "1 tick through"): low <= level - tick (high >= level + tick), tick = Rs 0.10 at today's price = 0.00292% of price (the official prices in the file are all multiples of Rs 0.10). F2 (queue-priority stress, extra): the extreme must trade through by 0.10% of price. A filled limit order fills at the limit price (no price improvement, except a pre-open buy whose level is at or above the open, which fills at the open). A target limit in R3t / R6 follows the same fill rule. A stop in R6 is a stop-market order filled at the stop level (no gap-through is possible because entry is at the open); a stop-entry in R4a fills at the level.
* **Costs.** Primary: **0.10% round trip** (as assigned) deducted from every filled trade, no extra slippage on limit orders. Stress S1: an additional 0.05% per *marketable* leg (market or stop entries, market / stop exits, the exit at the close; not limit fills). Gross returns are always shown so the reader can see how much cost an edge could absorb (realistic all-in intraday cost for a retail account is lower than 0.10%; the assigned figure is conservative).
* **Entry at the official open** is possible only through the pre-open call auction (orders by 09:08) or at the first continuous price; the project's own check (`results/behaviour/intraday.json`) found the first printed bar open differs from the official open by 0.115% (mean absolute, Rs 4) and the maximum by Rs 22. I therefore also run the open-based rules R1, R2, R5, R6 on the hourly sample with Yahoo's first printed open and Yahoo's own extremes and report the difference (Section 3.6).
* **Closing price.** The official close is a 30-minute VWAP before 3 Aug 2026 and the auction price after; a trader cannot always transact at it. The sensitivity "exit at Yahoo's last printed price" is reported for the hourly sample.

### 0.6 Tests and the verdict rule (fixed now)
* Statistic: mean **net** return per filled trade (percent), one-sided test of "> 0". Standard error: Newey-West (Bartlett, lag 5, in trade order) with t reference distribution, df = n - 1; also the plain i.i.d. t. A variant with fewer than 10 trades in a window gets no p-value (treated as p = 1 inside Holm).
* **Holm** across all 31 variants, separately for each window and each fill convention, applied to the HAC p-values and, separately, to the placebo p-values.
* **Placebo** (Section 0.7). A variant's placebo p = share of 2,000 simulated histories (plus one) whose statistic (same window, same rule, same estimators, same fills, same costs) is at least the observed one.
* **Diebold-Mariano** (Harvey-Leybourne-Newbold, lag 5, `src/metrics.py`): model-level rules against the EMP250 benchmark level (R7 / R8 pairs) on calendar-day net profit and loss (0 on no-fill days), one-sided "model better", Holm over the pairs. Pinball loss and 50% / 90% coverage of the high / low quantiles themselves are specialist A's tables (not repeated); here I report Kupiec tests of the fill frequency of the model-quantile limit orders against their nominal 25% / 10%, and Kupiec and coverage for stop placement at the trailing EMP250 quantile of the adverse excursion (Section 0.8 item 5).
* **Verdict for a primary variant** (all of these, fixed now):
  * **validated**: net mean > 0 with Holm-adjusted HAC p < 0.05 **and** Holm-adjusted placebo p < 0.05 under **both** placebos (zero drift and drift matched to the window) in the **Final** window; net mean > 0 also in the Validation window (and in the Development window where one exists); still positive under F1; and the CAS slice is not significantly negative.
  * **descriptive**: gross mean > 0 with unadjusted p < 0.05 in at least one window, or net > 0 in Final without meeting every validated condition. Descriptive means "something happened in this sample", not "tradable".
  * **not found**: anything else, including net mean <= 0 in Final.
* A positive result is *not* believed on the strength of one window. Minimum detectable effect (80% power, one-sided 5%) = 2.49 x standard error is printed for each primary variant so that "not found" is read as "no edge larger than X% per trade can be ruled out", not as "no edge".

### 0.7 Placebo design (fixed now)
2,000 simulated histories for each of two drift settings. Each history has the same 2,390 session dates as the real file. Per session: scale of the intraday move = the real past-only `sigI_t` (EWMA of squared open-to-close log returns of the *real* history through t-1) times exp(eta_t), eta_t ~ N(-v^2/2, v^2) (so the placebo has volatility that moves around, with v^2 = ln of the mean of (I_t / sigI_t)^2 in the real sample); the gap scale likewise from the real `sigG_t`. The intraday path is a driftless Gaussian random walk on a 5-minute grid (75 steps, 09:15 to 15:30) whose step variance follows the **empirical hourly variance clock** (session-normalised squared hourly returns of the 479 complete hourly sessions; uniform inside each hour), the day's high and low taken from the path with Brownian-bridge extremes inside every step (so they are continuous-time extremes, not 5-minute-grid extremes), prices rounded to the tick. Hourly bars (12 steps per bar, 3 for the last) are built from the same path for the last 479 sessions' calendar positions. The same functions that score the real data score the simulated data, including re-estimating every sigma from the simulated history. **Drift setting A**: zero drift. **Drift setting B**: drift equal to the real sample mean of the gap and of the open-to-close log return in the same window (Development / Validation / Final-before-CAS / CAS), spread evenly over the gap and over the intraday steps, i.e. "the same drift but no timing". Rules for the project's stored model quantiles (R7 / R8 model variants) cannot be re-fitted inside a simulation; they get no placebo p and therefore **cannot be called validated** (at most "descriptive"); their EMP250 siblings do get one.

### 0.8 Part 1 definitions (fixed now)
1. **Excursions.** Entry at the official open (daily bars, 2019-01-01 onward) and at 10:15 (price = close of the first hourly bar; hourly sample). Long: favourable = high of the rest of the day / entry - 1, adverse = 1 - low of the rest of the day / entry; short: swapped. For 10:15 the rest of the day = bars 2 to 7. Tables: mean and quantiles 10 / 25 / 50 / 75 / 90 / 95 in percent and in rupees (percent x Rs 3,428), windows all / Development / Validation / Final / CAS. Additional entry hours 11:15 .. 15:15 (hourly sample) to show how much room is left late in the day.
2. **Stop and target touch.** Stop at -x% and target at +y% from the open, x, y in {0.5, 1, 1.5, 2}%. A level is "touched" when the extreme reaches it (>=); this descriptive convention differs from the strict fill rule of Part 2. Daily bars give exact shares of {stop only, target only, both, neither}, hence bounds for P(stop before target) and P(target before stop); the hourly sample resolves the order when the two levels fall in different bars and reports "same bar, order unknown" otherwise. Split into low / mid / high regime by the expanding terciles of `sigR`. Today's regime is classified from `sigR` after the 15 Oct close.
3. **Open and first hour.** P(open = high), P(open = low), P(either) (daily bars, equality within Rs 0.001); P(high in first hour), P(low in first hour), P(either), P(both), P(high in last hour) (hourly sample, bar 1 / bar 7; ties go to the first bar and are counted); the same quantities in the placebo; compared with the project's 31/37 = 83.8% against 84.9%.
4. **Range already formed.** For each entry hour, share of sessions in which the final high (low) was already set, and the median share of the final range already formed.
5. **Stop calibration (walk-forward).** Stop distance = trailing-250-session empirical quantile q of the adverse excursion from the open, q in {0.50, 0.75, 0.90}; realised frequency of the stop being touched against the nominal 1 - q, with Kupiec p, for long and short, by window.

### 0.9 What is reported whatever the outcome
Every variant, every window, both fill conventions, the cost stress, trade counts, the placebo distribution summaries, the by-year table, the cases where a rule's sample is too small. Nothing is dropped because it lost.

*END OF PRE-FIXED SECTION*

---

## 1. Short answer, in plain words

**Can the estimated high and low of the next session be turned into a profitable intraday trade? On this evidence, no.** I fixed eight rules in advance (section 0; 31 variants counting the neighbours of each rule), tested them in time order with a 0.10% round-trip cost, and compared them with a random-walk placebo of 2,000 simulated histories. **No rule meets the bar for the word 'validated'.** In the Final window (sessions from 1 Jul 2025: 320 daily sessions, 306 with usable hourly bars) 7 of the 8 primary rules had a negative mean return after costs. The eighth, 'follow a breakout of the first-hour range' (R4), is labelled **descriptive**: that word only means its Final-window mean was above zero, at +0.04% (Rs 1.3) per trade net, n = 246 trades, p = 0.34, which is nothing. It earned +0.47% per trade net in the Validation half-year (n = 105 trades, Holm-adjusted p = 0.031), then +0.04% in Final and -0.14% in the 35 trades since the closing auction began. That is the pattern of something that was there for a while and went away, not of something to build on.

Final window, primary variant of each rule, strict fill convention (the extreme must trade through the level), 0.10% round-trip cost. All variants are in section 4.

| rule | what it does | sessions | trades | gross % per trade | net % per trade | net Rs per trade | p (net mean > 0) | Holm p | verdict |
|---|---|---|---|---|---|---|---|---|---|
| R1 | (a) limit buy 1 sigma below the open, exit at the close | 320 | 86 | -0.30 | -0.40 | -13.9 | 0.986 | 1.00 | **not found** |
| R2 | (b) limit sell (short) 1 sigma above the open, exit at the close | 320 | 95 | -0.22 | -0.32 | -11.0 | 0.994 | 1.00 | **not found** |
| R3 | (c) fade a first-hour move beyond 1.5 sigma, exit at the close | 306 | 45 | -0.19 | -0.29 | -9.8 | 0.879 | 1.00 | **not found** |
| R4 | (d) follow a breakout of the first-hour range, exit at the close | 306 | 246 | +0.14 | +0.04 | +1.3 | 0.338 | 1.00 | **descriptive** |
| R5 | (e) trade against a gap larger than 1 sigma, open to close | 320 | 56 | +0.08 | -0.02 | -0.6 | 0.524 | 1.00 | **not found** |
| R6 | (f) long from the open, stop 1%, target 2%, else close | 320 | 320 | -0.06 | -0.16 | -5.4 | 0.990 | 1.00 | **not found** |
| R7 | limit buy at the project's estimated low (25% level, known after the open) | 320 | 85 | -0.31 | -0.41 | -14.0 | 0.987 | 1.00 | **not found** |
| R8 | limit sell at the project's estimated high (75% level, known after the open) | 320 | 78 | -0.19 | -0.29 | -9.9 | 0.986 | 1.00 | **not found** |

'Net Rs per trade' is net % times Rs 3,428 (the 15 Oct close). p is one-sided with a Newey-West (autocorrelation-robust) standard error. Holm corrects for trying 31 variants in the same window. R7 and R8 are the project's own estimated-low and estimated-high levels (specialist A's stored out-of-sample quantiles); R1 and R2 are the same idea with a plain past-only scale. R7 and R8 cannot be re-fitted inside a simulation, so they have no placebo and could never be called validated (pre-fixed in 0.7).

**The estimated levels themselves are not the problem.** The post-open 25% low level was traded through on 26.6% of the 320 Final sessions (promised 25%, Kupiec p = 0.52) and the 75% high level on 24.4% (promised 25%, p = 0.80). A level that is touched as often as promised is still not a bargain: a buyer at the estimated low lost Rs 14 per share on average per fill (-0.41% net, -0.31% before cost, n = 85), and a seller at the estimated high lost Rs 9.9 (-0.29% net, n = 78). Once the price reached those levels it showed no tendency to turn back (gross mean per fill -0.31% for the low level and -0.19% for the high level in Final; -0.07% and -0.41% over 2020-2026, where a turn would show as a positive number). The same was true of the transparent versions (R1, R2). The opposite-direction look (trade with the breach instead of against it) is post hoc and is in section 5.

**What the estimates are good for** is risk management, not entries: how far a stop has to be to survive an ordinary day, how large a position that implies, and how little room is left late in the day (sections 3 and 7). **What they cannot do** is tell you where to buy or sell for a profit.

**Words used.** *Net* = after the 0.10% round-trip cost (Rs 3.4 a share at today's price). *Fill* = a resting limit order counts as executed only if the day's price trades strictly through its level. *p-value* = the chance of a result at least this good if there were no edge at all; small (under 0.05) means unlikely to be luck, and *Holm* tightens that after correcting for the number of variants tried. *Placebo* = the same rule run on 2,000 invented random-walk histories with the same volatility pattern, to show what luck alone produces. *Final window* = sessions from 1 Jul 2025; the rules were fixed in section 0, so this window was not used to choose a rule (section 2 says what can and cannot be checked about that; the one exception is the project's own model behind R7 and R8, which the project chose using it). *Descriptive* = something happened in this sample; it does not mean tradable.

**In three lines for a trader.** (1) Do not place orders at the estimated high or low expecting a turn: in the 320 Final sessions that lost Rs 14 (buying at the low) and Rs 9.9 (selling at the high) a share per fill after costs. (2) Do use them, and the swing tables in 3.1, to decide how far a stop must sit and how many shares that allows: from the open the low has been at least Rs 45 below on half the days and Rs 115 below on one day in ten. (3) After about 13:15 there is little left to gain (median Rs 16-17 of room against a Rs 3.4 round trip), so late entries rarely pay their costs.

**How much would have been visible.** With 45-320 trades per rule in the Final window, a true edge smaller than about 0.17-0.68% net per trade could not have been detected with 80% power (column 'MDE' in 4.1). So 'not found' means 'no edge large enough to see', not 'proven absent'. An edge of 0.1-0.2% per trade, the size that would matter after costs, would need on the order of a thousand trades per rule to confirm or to rule out.

## 2. What was built, where it came from, and what changed after the first look

* **Code**: `src/hl_trade_study.py` (commands `selftest`, `part1`, `part2`, `placebo`, `finish`, `posthoc`, `today`, `indepcheck`, `diag`, `report`; `all` runs them in that order; no network). **Outputs**: `results/hl_trade_*.csv` and `.json` (section 10). **This report** is written by `report` from those files only.
* **Inputs** (nothing dated after 15 Oct 2026; the code drops later bars if they ever appear): `data/processed/bse_daily.csv` + `bse_daily_extra.csv` (2,390 sessions, last official bar 15 Oct 2026: open 3,342.0, high 3,445.0, low 3,315.2, close 3,428.0; `common.load_bse()` alone ends on 13 Oct, so the extra file is needed); the Yahoo 1-hour file for BSE.NS (range 2y, fetched 15 Oct, SHA-256 `ef5d3b6be31bcf7f...`, last bar the 15:15 bar of 15 Oct, 479 complete 7-bar sessions used; not stored in the repo); specialist A's stored out-of-sample quantiles `results/hl_eval_predictions.csv` (SHA-256 `6b97a92d6fc4cf4d...`).
* **When, and what was not used.** The study was re-run and this report written on the morning of Fri 16 Oct 2026; the last full run finished at about 09:23 IST, after the 09:15 open, so the wording 'before the open' used in the brief no longer applies to the run time. That does not matter for the data: the data cut-off is the 15 Oct 2026 close, the code drops any later bar (the hourly file's last bar is the 15:15 bar of 15 Oct), and no 16 Oct price enters any number. I did see, in a git commit message of the repository history, that a pre-open snapshot of 16 Oct exists and what opening price it records; I did not open that file or use the figure, and nothing in this report depends on it.
* **Provenance, stated plainly.** An earlier attempt at this task stopped part-way (usage limit) and left code, 28 result files and section 0. I trusted none of its numbers. I re-ran its unchanged code from scratch (self-test, Part 1, Part 2, the 2,000-history placebo in four settings, the finishing step, the post-hoc step) and compared every result file by SHA-256 with the file on disk: all 28 were byte-for-byte identical (same seeds give the same placebo). That comparison was done in the session scratchpad and is not reproducible from the repository alone. I then made the additions listed below, re-ran everything, and rebuilt this report from the files.
* **Is section 0 really pre-fixed?** Its text is unchanged: its SHA-256 (`4f8bd8aa1a07ffd0...`, checked by `report` every time it runs) is the value that was written to a file five seconds after the report file was last modified, at 17:03:06 UTC on 15 Oct 2026, and the first commit containing any result file is dated 17:13 UTC. Section 0 itself states that no result had been computed when it was written. I cannot audit that statement from the repository (the same limit the independent verifier of specialist A noted for A's report); what can be checked is that no variant, window, cost or verdict rule has changed since, and that everything added later is listed here.
* **Changes and additions after the first look** (none changes a pre-fixed rule, window, cost, fill convention or the verdict rule; items 1-6 come from the earlier attempt's own notes and code comments, items 7-10 are mine):
  1. The two-sided placebo p-value for the first-hour share is capped at 1, because ties can push it above 1 (`hl_trade_open_hl.csv`).
  2. A Holm-adjusted two-sided column was added to the Diebold-Mariano table (`hl_trade_dm.csv`).
  3. The hourly rules R3/R4 were added to the no-look-ahead self-test.
  4. Volatility regime for Part 1: the pre-fixed expanding terciles leave almost no 'low' sessions in the Final window (3 of 320), so two **post-hoc** definitions were added and labelled: terciles of the trailing 500 sessions (from the earlier attempt), and terciles of all sessions (mine; descriptive only: the cut points use the whole sample, so it is not a classification a trader could have used in real time).
  5. A placebo sensitivity with a different variance clock (settings P0 and P1, section 5.3), after I found that the pre-fixed clock under-weights the first hour (`hl_trade_clock.csv`).
  6. 16 post-hoc variants (section 5) and the numbers for 16 Oct (section 8).
  7. **Section 0.7 says simulated prices are 'rounded to the tick'. The placebo code does not round.** I found this while re-reading; it is a mismatch between the pre-fixed text and the code, and the main placebo results stand as run. To see whether it matters I re-ran the first 400 placebo histories (same seeds) with prices rounded to Rs 0.10 at today's price and compared them one by one: the null mean net return per trade moved by at most 0.0017 percentage points and no placebo p-value for the variants listed moved by more than 0.005 (`hl_trade_sensitivity_tick.csv`). The omission has no visible effect.
  8. The closing-price sensitivity that section 0.5 promised ('exit at Yahoo's last printed price') was run for R1, R2, R5, R6 at first; I extended it to the hourly rules R3 and R4 (`hl_trade_crosscheck.csv`).
  9. A table of the typical miss of the stored median forecasts (`hl_trade_model_miss.csv`), the placebo-versus-reality diagnostics (`hl_trade_placebo_diag.csv`), the plain-loop re-computation (`hl_trade_indepcheck.csv`) and a data cut-off guard were added.
  10. Section 3.7 (which stop-distance estimator works best, with Diebold-Mariano and Holm over 12 comparisons) and the stop distances for 16 Oct were added after the pre-fixed section; they are descriptive and not among the 31 variants (`hl_trade_stop_forecast.csv`, `hl_trade_today_stops_2026-10-16.csv`).
* **Checks that passed.** Self-test (`hl_trade_selftest.csv`, 12 of 12 rows true, 10 real checks and 2 informational rows that are always true): the exponentially weighted scale equals the project's `sigma_ewma`; changing one session's high, low, close or hourly bars leaves every earlier trade bit-identical (daily and hourly rules); the scale and level used on session t do not change when session t's own high, low or close change; later sessions do change (positive control); the stored model levels use the same previous close as the daily file; under zero drift the placebo's mean log return per fill is within 4 standard errors of zero for R1, R2, R3, R4a, R4b, R5 and the trailing-quantile siblings of R7/R8. **Independent re-computation** (`hl_trade_indepcheck.csv`, command `indepcheck`): the headline numbers re-typed with plain loops that call none of the study's functions: 145 of 145 comparisons agree (trade counts and mean returns of R1, R2, R3, R4a, R5, R6, R7 and R8 in every window, three Newey-West t and p values, open-equals-high/low counts, Final excursion quantiles, the 10:15 excursions, one Kupiec test). It checks the coding and the arithmetic, not the design, because it is my own second typing of the same rules.
* **Costs, fills, windows** are as pre-fixed in sections 0.2 and 0.5: Development (to 30 Jun 2024), Validation (to 30 Jun 2025), Final (from 1 Jul 2025), post-closing-auction slice (from 4 Aug 2026; 51 daily and 42 hourly sessions); fill F0 = the extreme must trade strictly through the level, F1 = one tick (Rs 0.10) through, F2 = 0.10% through; cost 0.10% round trip, stress S1 adds 0.05% per marketable leg (market orders, stop entries, the exit at the close).
* **Closing-auction regime check**: since 4 Aug 2026 the official open equals the previous close on 9 of 51 sessions (17.6%), against 6.3% (17 of 269) in the rest of the Final window and 5.4% in Development (`hl_trade_open_equals_prev.csv`). That is a real change in how the day starts, but 51 sessions are too few to say what it does to any rule.

## 3. Part 1 (descriptive, for risk management)

Everything here describes what happened; none of it is a forecast or a trading signal. Rupee figures are percent times Rs 3,428 (the 15 Oct close), so they are 'what it would be at today's price'. Daily figures use the official NSE open, high, low and close; hourly figures use Yahoo's hourly bars (section 4.9 measures how far the two sources differ).

### 3.1 How far the price travels from the official open (daily bars)

'Up' is the day's high above the open; 'down' is the day's low below the open. For a long entered at the open, 'down' is the worst drawdown you would have sat through (the maximum adverse excursion) and 'up' the best moment to take profit (the maximum favourable excursion); for a short, swap them. Cells are percent (rupees).

| window | side | mean | 25th pct | median | 75th pct | 90th pct | 95th pct |
|---|---|---|---|---|---|---|---|
| all 2019-2026 (n=1923) | up | 1.91% (65) | 0.51% (18) | 1.27% (44) | 2.52% (86) | 4.37% (150) | 5.71% (196) |
| all 2019-2026 (n=1923) | down | 1.77% (61) | 0.64% (22) | 1.31% (45) | 2.36% (81) | 3.92% (134) | 5.27% (181) |
| Development (n=1355) | up | 1.89% (65) | 0.50% (17) | 1.23% (42) | 2.48% (85) | 4.40% (151) | 6.06% (208) |
| Development (n=1355) | down | 1.72% (59) | 0.61% (21) | 1.28% (44) | 2.28% (78) | 3.85% (132) | 5.15% (177) |
| Validation (n=248) | up | 2.51% (86) | 0.74% (25) | 1.69% (58) | 3.46% (119) | 5.38% (184) | 7.85% (269) |
| Validation (n=248) | down | 2.15% (74) | 0.79% (27) | 1.61% (55) | 3.02% (104) | 5.05% (173) | 5.91% (202) |
| Final (n=320) | up | 1.52% (52) | 0.48% (16) | 1.20% (41) | 2.22% (76) | 3.26% (112) | 3.99% (137) |
| Final (n=320) | down | 1.69% (58) | 0.63% (22) | 1.31% (45) | 2.34% (80) | 3.37% (115) | 4.71% (161) |
| post-closing-auction (n=51) | up | 1.42% (49) | 0.25% (8.4) | 1.04% (36) | 2.30% (79) | 3.23% (111) | 3.57% (122) |
| post-closing-auction (n=51) | down | 1.62% (55) | 0.56% (19) | 1.07% (37) | 2.49% (85) | 3.16% (108) | 4.16% (143) |

Plain reading (Final, n = 320): on half of the sessions the high is at least Rs 41 above the open and the low at least Rs 45 below it; on one session in ten the high is Rs 112 or more above the open, and on one in ten the low is Rs 115 or more below it. The distributions are skewed, so the mean is above the median. The Validation year (2024-25) was far more violent (median low Rs 55 below the open) than Final.

### 3.2 Entering at 10:15 or later (hourly bars): how much room is left

Entry price = the close of the hourly bar shown (so '10:15' is the close of the 09:15-10:15 bar). Favourable and adverse excursions are measured on the remaining bars to 15:30, from Yahoo's hourly extremes. Hourly sample: 479 sessions in all, 306 in Final, 42 since the closing auction. Cells are percent (rupees).

**Entry at 10:15, full distribution:**

| window | side | mean | 25th pct | median | 75th pct | 90th pct | 95th pct |
|---|---|---|---|---|---|---|---|
| whole hourly sample (Oct 2024 - Oct 2026) (n=479) | up | 1.27% (43) | 0.39% (13) | 0.95% (33) | 1.83% (63) | 2.65% (91) | 3.51% (120) |
| whole hourly sample (Oct 2024 - Oct 2026) (n=479) | down | 1.31% (45) | 0.42% (14) | 0.96% (33) | 1.84% (63) | 2.98% (102) | 3.87% (133) |
| Validation (Oct 2024 - Jun 2025) (n=173) | up | 1.55% (53) | 0.59% (20) | 1.30% (45) | 2.09% (72) | 3.19% (109) | 3.97% (136) |
| Validation (Oct 2024 - Jun 2025) (n=173) | down | 1.53% (52) | 0.44% (15) | 1.19% (41) | 2.32% (79) | 3.53% (121) | 4.20% (144) |
| Final (n=306) | up | 1.10% (38) | 0.35% (12) | 0.81% (28) | 1.61% (55) | 2.34% (80) | 3.03% (104) |
| Final (n=306) | down | 1.19% (41) | 0.42% (14) | 0.88% (30) | 1.57% (54) | 2.54% (87) | 3.37% (115) |
| post-closing-auction (n=42) | up | 1.03% (35) | 0.36% (12) | 0.62% (21) | 1.50% (51) | 2.23% (76) | 3.08% (106) |
| post-closing-auction (n=42) | down | 1.25% (43) | 0.50% (17) | 0.93% (32) | 1.69% (58) | 2.79% (96) | 3.29% (113) |

**Later entry hours, Final window** (median and 90th percentile of the remaining room):

| entry at | room above: median | room above: 90th pct | room below: median | room below: 90th pct |
|---|---|---|---|---|
| 10:15 | 0.81% (28) | 2.34% (80) | 0.88% (30) | 2.54% (87) |
| 11:15 | 0.68% (23) | 2.12% (73) | 0.76% (26) | 2.07% (71) |
| 12:15 | 0.59% (20) | 1.69% (58) | 0.62% (21) | 1.89% (65) |
| 13:15 | 0.47% (16) | 1.38% (47) | 0.50% (17) | 1.39% (48) |
| 14:15 | 0.33% (11) | 1.09% (37) | 0.40% (14) | 1.05% (36) |
| 15:15 | 0.16% (5.3) | 0.52% (18) | 0.15% (5.2) | 0.40% (14) |

Plain reading: after 13:15 the median remaining swing is only about Rs 16-17 either way, after 14:15 about Rs 11-14, against a round-trip cost of about Rs 3.4 (0.10%). Late in the day there is little left to gain or lose.

### 3.3 Where a stop and a target of a given size get hit (entry at the official open)

Cells show **S** = share of sessions in which the stop was touched first, **T** = the target was touched first, **N** = neither was touched. 'Touched' means the day's extreme reached the level. A daily bar cannot tell which came first when both levels were reached on the same day, so S and T are shown as ranges (the lower end gives the ambiguous days to the other side); N is exact. The long side has the stop below the open and the target above; the short side the reverse.

**Long side, all 2019-2026, n = 1923 sessions** (rows: stop size; columns: target size; in % of the open)

|  | target 0.5% | target 1% | target 1.5% | target 2% |
|---|---|---|---|---|
| stop 0.5% (Rs 17) | S 24-80 / T 19-76 / N 1 | S 40-80 / T 18-58 / N 2 | S 52-80 / T 16-44 / N 4 | S 60-80 / T 13-33 / N 7 |
| stop 1% (Rs 34) | S 21-60 / T 36-76 / N 3 | S 35-60 / T 33-58 / N 7 | S 43-60 / T 27-44 / N 12 | S 49-60 / T 22-33 / N 18 |
| stop 1.5% (Rs 51) | S 17-43 / T 50-76 / N 7 | S 28-43 / T 42-58 / N 15 | S 33-43 / T 34-44 / N 22 | S 37-43 / T 26-33 / N 30 |
| stop 2% (Rs 69) | S 14-32 / T 58-76 / N 10 | S 21-32 / T 47-58 / N 21 | S 25-32 / T 38-44 / N 31 | S 27-32 / T 28-33 / N 40 |

**Long side, Final window, n = 320 sessions** (rows: stop size; columns: target size; in % of the open)

|  | target 0.5% | target 1% | target 1.5% | target 2% |
|---|---|---|---|---|
| stop 0.5% (Rs 17) | S 26-81 / T 19-74 / N 0 | S 45-81 / T 19-55 / N 0 | S 56-81 / T 17-42 / N 2 | S 63-81 / T 14-32 / N 5 |
| stop 1% (Rs 34) | S 25-60 / T 39-74 / N 1 | S 41-60 / T 36-55 / N 4 | S 48-60 / T 30-42 / N 11 | S 52-60 / T 24-32 / N 17 |
| stop 1.5% (Rs 51) | S 22-42 / T 54-74 / N 4 | S 33-42 / T 46-55 / N 12 | S 36-42 / T 35-42 / N 22 | S 39-42 / T 28-32 / N 29 |
| stop 2% (Rs 69) | S 20-32 / T 62-74 / N 6 | S 27-32 / T 50-55 / N 18 | S 28-32 / T 38-42 / N 30 | S 30-32 / T 30-32 / N 38 |

**Short side, Final window, n = 320 sessions** (rows: stop size; columns: target size; in % of the open)

|  | target 0.5% | target 1% | target 1.5% | target 2% |
|---|---|---|---|---|
| stop 0.5% (Rs 17) | S 19-74 / T 26-81 / N 0 | S 39-74 / T 25-60 / N 1 | S 54-74 / T 22-42 / N 4 | S 62-74 / T 20-32 / N 6 |
| stop 1% (Rs 34) | S 19-55 / T 45-81 / N 0 | S 36-55 / T 41-60 / N 4 | S 46-55 / T 33-42 / N 12 | S 50-55 / T 27-32 / N 18 |
| stop 1.5% (Rs 51) | S 17-42 / T 56-81 / N 2 | S 30-42 / T 48-60 / N 11 | S 35-42 / T 36-42 / N 22 | S 38-42 / T 28-32 / N 30 |
| stop 2% (Rs 69) | S 14-32 / T 63-81 / N 5 | S 24-32 / T 52-60 / N 17 | S 28-32 / T 39-42 / N 29 | S 30-32 / T 30-32 / N 38 |

Plain reading (Final, long): a 1% stop with a 2% target from the open was stopped first in 52-60% of sessions, reached its target first in 24-32%, and ended without either in 17%. A 0.5% stop (Rs 17) was touched on 81% of days: ordinary noise takes out a stop that tight on most days.

**Order resolved with the hourly bars** (Final, long side, hourly sample n = 306; 'same hour' = both levels were reached inside one hourly bar, so the order is unknown). Cells: stop first / target first / same hour / neither, in %:

|  | target 0.5% | target 1% | target 1.5% | target 2% |
|---|---|---|---|---|
| stop 0.5% | 34 / 29 / 36 / 0 | 58 / 24 / 18 / 0 | 69 / 20 / 9 / 2 | 75 / 14 / 5 / 6 |
| stop 1% | 30 / 54 / 14 / 2 | 48 / 43 / 5 / 5 | 53 / 34 / 2 / 11 | 55 / 25 / 2 / 18 |
| stop 1.5% | 25 / 64 / 6 / 4 | 36 / 49 / 2 / 13 | 39 / 37 / 1 / 23 | 41 / 27 / 1 / 31 |
| stop 2% | 22 / 68 / 3 / 7 | 28 / 52 / 1 / 19 | 29 / 40 / 0 / 30 | 31 / 29 / 0 / 40 |

**By volatility regime.** Regime = tercile (lowest, middle, highest third) of the exponentially weighted close-to-close volatility known the evening before. Three definitions are shown because they disagree (the first is the pre-fixed one; the other two are post hoc):

* `expanding`: cut points from all earlier sessions (no look-ahead). Because volatility rose a lot in 2024-25, most recent sessions count as 'high' or 'mid'.
* `trailing500_posthoc`: cut points from the previous 500 sessions only.
* `fullsample_posthoc`: cut points from all sessions 2019-2026 (descriptive; uses the future to set the cut points, so it is not a rule a trader could have followed in real time, but it gives usable counts in every cell).

Sessions in the Final window by regime (low / mid / high): expanding 3 / 261 / 56; trailing-500 263 / 57 / 0; full-sample 76 / 212 / 32 (cut points of the full-sample definition: 2.15% and 3.05% a day). Over all years the expanding definition gives 5% low, 32% mid, 63% high.

| sample (long side) | n | stop 1% / target 2% | stop 1% / target 1% | stop 2% / target 1% | stop 0.5% / target 1% |
|---|---|---|---|---|---|
| Final, fullsample_posthoc, low | 76 | S 51-55 / T 28-32 / N 17 | S 43-55 / T 41-53 / N 4 | S 32-36 / T 49-53 / N 16 | S 47-79 / T 21-53 / N 0 |
| Final, fullsample_posthoc, mid | 212 | S 51-60 / T 24-32 / N 17 | S 40-60 / T 35-55 / N 5 | S 25-30 / T 50-55 / N 20 | S 44-81 / T 19-55 / N 0 |
| Final, fullsample_posthoc, high | 32 | S 53-69 / T 16-31 / N 16 | S 38-69 / T 28-59 / N 3 | S 31-34 / T 56-59 / N 9 | S 41-88 / T 12-59 / N 0 |
| all 2019-2026, fullsample_posthoc, low | 641 | S 47-50 / T 16-19 / N 34 | S 39-50 / T 33-44 / N 17 | S 17-21 / T 40-44 / N 39 | S 51-76 / T 19-44 / N 5 |
| all 2019-2026, fullsample_posthoc, mid | 641 | S 50-60 / T 25-35 / N 15 | S 37-60 / T 36-60 / N 3 | S 21-30 / T 52-60 / N 19 | S 39-80 / T 20-60 / N 1 |
| all 2019-2026, fullsample_posthoc, high | 641 | S 49-71 / T 24-45 / N 6 | S 30-71 / T 28-69 / N 1 | S 25-45 / T 49-69 / N 6 | S 31-84 / T 15-69 / N 0 |
| all 2019-2026, expanding, low | 100 | S 33-35 / T 8-10 / N 57 | S 32-35 / T 24-27 / N 41 | S 8-10 / T 25-27 / N 65 | S 58-71 / T 14-27 / N 15 |
| all 2019-2026, expanding, mid | 621 | S 50-54 / T 21-25 / N 25 | S 41-54 / T 36-49 / N 10 | S 21-25 / T 45-49 / N 30 | S 49-77 / T 20-49 / N 3 |
| all 2019-2026, expanding, high | 1202 | S 50-66 / T 23-39 / N 11 | S 33-66 / T 32-65 / N 3 | S 22-37 / T 50-65 / N 13 | S 35-82 / T 17-65 / N 1 |
| Final, expanding, low | 3 | S 33-33 / T 67-67 / N 0 | S 33-33 / T 67-67 / N 0 | S 33-33 / T 67-67 / N 0 | S 33-67 / T 33-67 / N 0 |
| Final, expanding, mid | 261 | S 51-58 / T 25-31 / N 17 | S 41-58 / T 38-54 / N 5 | S 27-32 / T 49-54 / N 19 | S 46-80 / T 19-54 / N 0 |
| Final, expanding, high | 56 | S 54-70 / T 16-32 / N 14 | S 38-70 / T 27-59 / N 4 | S 27-30 / T 55-59 / N 14 | S 41-84 / T 16-59 / N 0 |
| all 2019-2026, trailing500_posthoc, low | 581 | S 48-52 / T 20-23 / N 28 | S 40-52 / T 35-46 / N 13 | S 20-23 / T 43-46 / N 34 | S 50-77 / T 20-46 / N 3 |
| all 2019-2026, trailing500_posthoc, mid | 510 | S 51-59 / T 23-31 / N 18 | S 36-59 / T 33-55 / N 8 | S 21-29 / T 48-55 / N 23 | S 41-80 / T 17-55 / N 3 |
| all 2019-2026, trailing500_posthoc, high | 832 | S 48-67 / T 22-41 / N 11 | S 31-67 / T 31-67 / N 2 | S 22-40 / T 49-67 / N 11 | S 33-82 / T 17-67 / N 0 |
| Final, trailing500_posthoc, low | 263 | S 52-58 / T 25-31 / N 17 | S 42-58 / T 38-53 / N 5 | S 27-32 / T 48-53 / N 20 | S 46-80 / T 19-53 / N 0 |
| Final, trailing500_posthoc, mid | 57 | S 51-68 / T 19-37 / N 12 | S 33-68 / T 28-63 / N 4 | S 26-30 / T 60-63 / N 11 | S 37-84 / T 16-63 / N 0 |
| Final, trailing500_posthoc, high | 0 | no sessions | no sessions | no sessions | no sessions |

Where n is under about 30 the cell is an anecdote (for example the 'low' regime of the expanding definition in Final). The robust, non-controversial pattern is that busier regimes have wider swings (next table), so the same stop is touched more often.

**Size of the swing by regime** (full-sample terciles; median and 90th percentile of the day's high above / low below the open; percent (rupees at Rs 3,428)):

| window | regime | n | high above open: median | high: 90th pct | low below open: median | low: 90th pct |
|---|---|---|---|---|---|---|
| all 2019-2026 | low | 641 | 0.80% (27) | 2.95% (101) | 1.00% (34) | 2.94% (101) |
| all 2019-2026 | mid | 641 | 1.34% (46) | 4.31% (148) | 1.30% (44) | 3.42% (117) |
| all 2019-2026 | high | 641 | 1.81% (62) | 5.37% (184) | 1.70% (58) | 5.21% (179) |
| Final | low | 76 | 1.17% (40) | 3.10% (106) | 1.29% (44) | 3.37% (116) |
| Final | mid | 212 | 1.16% (40) | 3.29% (113) | 1.31% (45) | 3.52% (121) |
| Final | high | 32 | 1.41% (48) | 4.18% (143) | 1.38% (47) | 2.98% (102) |

**Which regime is Friday 16 Oct?** The scale going into 16 Oct is 2.26% a day: **mid** by the pre-fixed expanding definition, **mid** by the full-sample one, **low** by the trailing-500 one (cut points 2.44% and 3.22%, because 2024-25 was so volatile). Two of three definitions say 'mid'; the disagreement is a warning that the regime label is a matter of definition. The Final-window rows are the fair guide for the 16 Oct session.

### 3.4 Is the open, or the first hour, the high or the low of the day?

The project's earlier finding (research/v2/05_intraday_structure.md) was that 83.8% (31 of 37) of post-closing-auction sessions had their high or low in the first hour, and that a random walk with the same U-shaped variance profile gives 84.9%, so it is not a pattern. Here is the larger-sample check, with the placebo (histories with the real variance profile; setting A = the pre-fixed clock, P0 = a pooled clock, section 5.3). 'High or low in first hour' counts a session if either extreme falls in the 09:15-10:15 bar.

| window | hourly sessions | observed: high or low in first hour (count) | placebo A: mean (5-95%) | p (two-sided) | placebo P0: mean (5-95%) | p (two-sided) | observed: BOTH in first hour | placebo P0: both |
|---|---|---|---|---|---|---|---|---|
| whole hourly sample (Oct 2024 - Oct 2026) | 479 | 86.4% (414) | 82.3% (80%-85%) | 0.020 | 87.5% (85%-90%) | 0.516 | 13.6% | 7.9% |
| Validation (Oct 2024 - Jun 2025) | 173 | 90.2% (156) | 82.3% (78%-87%) | 0.008 | 87.5% (83%-91%) | 0.327 | 13.3% | 7.9% |
| Final | 306 | 84.3% (258) | 82.3% (79%-86%) | 0.397 | 87.5% (84%-91%) | 0.117 | 13.7% | 7.9% |
| post-closing-auction | 42 | 83.3% (35) | 82.5% (74%-93%) | 1.000 | 87.6% (79%-95%) | 0.518 | 9.5% | 7.7% |

Plain reading: 83.3% (35 of 42) of post-auction sessions had the high or the low in the first hour (the project's 31 of 37 is 83.8%), 84.3% in Final and 86.4% in all 479 hourly sessions. A random walk with the same variance profile gives 82.3% (pre-fixed clock) to 87.5% (pooled clock). The observed share sits between the two, so this is **not a pattern you can trade**: the first hour simply carries a large part of the day's variance. The exact verdict depends on how the profile is estimated (section 5.3). One honest wrinkle: days on which BOTH extremes fall in the first hour are more frequent in the data (13.6%) than in the placebo (4.8% to 7.9%); real days are lumpier than the simulation, which is a limit of the placebo (section 6).

**The open itself** (the official NSE open, which is the pre-open call-auction price): it is the day's high in 6.2% and the day's low in 4.4% of all 1923 sessions (10.6% either; 119 and 85 sessions), 5.6% in Final (n = 320) and 9.8% since the closing auction (n = 51). The placebo cannot say anything about this (it gives 0.06%), because its paths are continuous and the real open is an auction print, not the first trade of a path; so I report it as a fact and not as a pattern or a non-pattern: on about one session in 9 over all years, and one in 18 in Final, no price after the open ever improves on the open on one side.

**Hour by hour (Final, hourly sample n = 306):** the share of sessions whose high falls in each hourly bar is 09:15 53%, 10:15 8%, 11:15 6%, 12:15 4%, 13:15 7%, 14:15 11%, 15:15 9%; for the low 09:15 45%, 10:15 9%, 11:15 7%, 12:15 6%, 13:15 7%, 14:15 16%, 15:15 11%. The extremes cluster at the start and at the end (the 14:15 and 15:15 bars), the usual U-shape.

### 3.5 How much of the day's range is already in place

Share of sessions in which the day's final high (low) has already been printed by the time shown, Final window (hourly sample, n = 306), and the median share of the final range already formed.

| by | final high already set | final low already set | both already set | median share of range formed |
|---|---|---|---|---|
| 10:15 | 53% | 45% | 14% | 68% |
| 11:15 | 62% | 54% | 19% | 79% |
| 12:15 | 68% | 60% | 30% | 86% |
| 13:15 | 72% | 66% | 39% | 94% |
| 14:15 | 79% | 73% | 52% | 100% |
| 15:15 | 91% | 89% | 79% | 100% |

Plain reading: by 14:15 the day's high is already in for 79% of sessions and the low for 73%, both extremes for 52%; by 15:15 for 91%, 89% and 79%. A fresh high or low late in the day is a minority event.

### 3.6 Placing a stop from the trailing history (walk-forward)

Stop distance = the trailing 250-session empirical quantile q of the adverse excursion from the open (sessions before the day only). If the history were a perfect guide, the stop would be touched on a share 1 - q of days. Kupiec tests whether the observed share equals the nominal one (a small p means it does not).

| window | side | stop at trailing | n | average stop distance | nominal touch | observed touch | Kupiec p |
|---|---|---|---|---|---|---|---|
| all 2019-2026 | long | 50th pct | 1923 | 1.33% (Rs 46) | 50% | 49.9% | 0.909 |
| all 2019-2026 | long | 75th pct | 1923 | 2.36% (Rs 81) | 25% | 26.5% | 0.126 |
| all 2019-2026 | long | 90th pct | 1923 | 3.78% (Rs 130) | 10% | 11.5% | 0.033 |
| all 2019-2026 | short | 50th pct | 1923 | 1.26% (Rs 43) | 50% | 52.1% | 0.065 |
| all 2019-2026 | short | 75th pct | 1923 | 2.50% (Rs 86) | 25% | 27.4% | 0.018 |
| all 2019-2026 | short | 90th pct | 1923 | 4.20% (Rs 144) | 10% | 11.2% | 0.077 |
| Development | long | 50th pct | 1355 | 1.24% (Rs 43) | 50% | 51.8% | 0.183 |
| Development | long | 75th pct | 1355 | 2.16% (Rs 74) | 25% | 27.5% | 0.039 |
| Development | long | 90th pct | 1355 | 3.51% (Rs 120) | 10% | 12.8% | 0.001 |
| Development | short | 50th pct | 1355 | 1.17% (Rs 40) | 50% | 53.1% | 0.021 |
| Development | short | 75th pct | 1355 | 2.34% (Rs 80) | 25% | 29.1% | <0.001 |
| Development | short | 90th pct | 1355 | 4.01% (Rs 137) | 10% | 12.5% | 0.003 |
| Validation | long | 50th pct | 248 | 1.72% (Rs 59) | 50% | 46.0% | 0.204 |
| Validation | long | 75th pct | 248 | 3.12% (Rs 107) | 25% | 25.8% | 0.770 |
| Validation | long | 90th pct | 248 | 4.73% (Rs 162) | 10% | 10.9% | 0.646 |
| Validation | short | 50th pct | 248 | 1.56% (Rs 54) | 50% | 54.4% | 0.162 |
| Validation | short | 75th pct | 248 | 3.32% (Rs 114) | 25% | 25.8% | 0.770 |
| Validation | short | 90th pct | 248 | 5.27% (Rs 181) | 10% | 11.3% | 0.506 |
| Final | long | 50th pct | 320 | 1.43% (Rs 49) | 50% | 44.7% | 0.057 |
| Final | long | 75th pct | 320 | 2.59% (Rs 89) | 25% | 23.1% | 0.435 |
| Final | long | 90th pct | 320 | 4.20% (Rs 144) | 10% | 6.6% | 0.030 |
| Final | short | 50th pct | 320 | 1.39% (Rs 48) | 50% | 45.9% | 0.146 |
| Final | short | 75th pct | 320 | 2.55% (Rs 87) | 25% | 21.2% | 0.115 |
| Final | short | 90th pct | 320 | 4.18% (Rs 143) | 10% | 5.9% | 0.009 |
| post-closing-auction | long | 50th pct | 51 | 1.24% (Rs 43) | 50% | 49.0% | 0.889 |
| post-closing-auction | long | 75th pct | 51 | 2.34% (Rs 80) | 25% | 29.4% | 0.475 |
| post-closing-auction | long | 90th pct | 51 | 3.22% (Rs 111) | 10% | 9.8% | 0.963 |
| post-closing-auction | short | 50th pct | 51 | 1.23% (Rs 42) | 50% | 47.1% | 0.674 |
| post-closing-auction | short | 75th pct | 51 | 2.23% (Rs 76) | 25% | 27.5% | 0.689 |
| post-closing-auction | short | 90th pct | 51 | 3.35% (Rs 115) | 10% | 7.8% | 0.595 |

Plain reading: the trailing history is a decent guide but not a precise one. In Final the stops at the 90th percentile were touched less often than nominal (6.6% long and 5.9% short against 10%; Kupiec p 0.030 and 0.009) probably because the Final window is calmer than the earlier years that dominate a 250-session history; in the Development window they were touched more often (12.8% and 12.5%; p 0.001 and 0.003). Expect the realised touch frequency to be within about five percentage points of the nominal one (the largest gap in Final was 5.3 points), not exactly equal.

### 3.7 Which estimate of the stop distance works best? (added after the pre-fixed section; descriptive)

Same question as 3.6 with two more candidates, forecast from earlier sessions only. **T250** = the trailing-250-session quantile of 3.6. **EXPANDING** = the quantile of all earlier sessions (a constant scale: it ignores whether the market is calm or wild). **EWMA_SCALED** = the recent volatility of the day's swing (exponentially weighted, lambda 0.94, known the evening before) times the all-history quantile of the swing measured in units of that volatility. Scored by pinball loss (the standard loss for a quantile forecast; lower is better, in percent of price), by how often the stop was touched against the promised share (Kupiec), and by Diebold-Mariano against T250 (Holm over the 12 comparisons of each window). This is a small side study with a family of 12 tests, not one of the 31 variants.

| side | stop at | method | all years (n=1923): touched (Kupiec p) | pinball | DM vs T250 | Final (n=320): touched (Kupiec p) | pinball  | DM vs T250  |
|---|---|---|---|---|---|---|---|---|
| long | 50th pct | T250 | 49.9% (p 0.909) | 0.574 | - | 44.7% (p 0.057) | 0.536 | - |
| long | 50th pct | EXPANDING | 57.6% (p <0.001) | 0.583 | t -2.6 (Holm 1.00) | 53.4% (p 0.219) | 0.536 | t 0.1 (Holm 1.00) |
| long | 50th pct | EWMA_SCALED | 45.9% (p <0.001) | 0.572 | t 0.2 (Holm 1.00) | 44.4% (p 0.044) | 0.543 | t -0.9 (Holm 1.00) |
| long | 75th pct | T250 | 26.5% (p 0.126) | 0.575 | - | 23.1% (p 0.435) | 0.525 | - |
| long | 75th pct | EXPANDING | 33.7% (p <0.001) | 0.594 | t -2.8 (Holm 1.00) | 29.7% (p 0.057) | 0.521 | t 0.3 (Holm 1.00) |
| long | 75th pct | EWMA_SCALED | 26.1% (p 0.265) | 0.554 | t 2.6 (Holm 0.05) | 25.3% (p 0.897) | 0.538 | t -1.0 (Holm 1.00) |
| long | 90th pct | T250 | 11.5% (p 0.033) | 0.394 | - | 6.6% (p 0.030) | 0.362 | - |
| long | 90th pct | EXPANDING | 16.5% (p <0.001) | 0.412 | t -2.3 (Holm 1.00) | 9.1% (p 0.571) | 0.348 | t 1.0 (Holm 1.00) |
| long | 90th pct | EWMA_SCALED | 10.5% (p 0.511) | 0.369 | t 2.5 (Holm 0.05) | 9.4% (p 0.707) | 0.378 | t -1.0 (Holm 1.00) |
| short | 50th pct | T250 | 52.1% (p 0.065) | 0.688 | - | 45.9% (p 0.146) | 0.525 | - |
| short | 50th pct | EXPANDING | 63.2% (p <0.001) | 0.711 | t -3.7 (Holm 1.00) | 52.2% (p 0.434) | 0.516 | t 0.8 (Holm 1.00) |
| short | 50th pct | EWMA_SCALED | 53.1% (p 0.007) | 0.664 | t 4.6 (Holm 0.00) | 55.3% (p 0.057) | 0.521 | t 0.3 (Holm 1.00) |
| short | 75th pct | T250 | 27.4% (p 0.018) | 0.708 | - | 21.2% (p 0.115) | 0.494 | - |
| short | 75th pct | EXPANDING | 37.2% (p <0.001) | 0.746 | t -3.7 (Holm 1.00) | 24.7% (p 0.897) | 0.469 | t 2.2 (Holm 0.16) |
| short | 75th pct | EWMA_SCALED | 26.2% (p 0.223) | 0.679 | t 3.0 (Holm 0.02) | 32.2% (p 0.004) | 0.495 | t -0.1 (Holm 1.00) |
| short | 90th pct | T250 | 11.2% (p 0.077) | 0.501 | - | 5.9% (p 0.009) | 0.325 | - |
| short | 90th pct | EXPANDING | 17.2% (p <0.001) | 0.535 | t -3.4 (Holm 1.00) | 5.0% (p 0.001) | 0.312 | t 1.5 (Holm 0.81) |
| short | 90th pct | EWMA_SCALED | 9.9% (p 0.861) | 0.477 | t 2.2 (Holm 0.13) | 10.3% (p 0.853) | 0.307 | t 1.3 (Holm 1.00) |

Plain reading: (1) the constant-scale stop (EXPANDING) is too tight in every case over 2019-2026, because it ignores that the market has been far busier at times: its stops were touched on 16%-63% of days against promised 10%-50% (Kupiec p < 0.001 each). (2) Scaling by recent volatility (EWMA_SCALED) had a lower pinball loss than T250 in all six side-and-level combinations over 2019-2026, significantly so (Holm-adjusted p < 0.05) in 4 of them (two of those only just: 0.050), all of it coming from the Development years (to mid-2024; in Validation and Final no gain is significant), and its 75% and 90% stops were touched about as often as promised (Kupiec p above 0.2 in all four). (3) In the Final window nothing beat T250 (smallest Holm p 0.16). T250's 90% stops were touched on 6.6% (long) and 5.9% (short) of Final days against 10%, EWMA_SCALED's on 9.4% and 10.3%; but EWMA_SCALED's 75% short stops were touched on 32.2% of Final days against 25% (p 0.004). In words: after a wild year the trailing-year history sets stops too wide, and a volatility-scaled stop corrects most of that; no method was clearly best in the last fifteen months, so treat any single stop distance as good to within roughly five to seven percentage points of the promised touch rate (the largest deviation in Final was {f(mx_dev, 1)} points), and do not read the difference between T250 and EWMA_SCALED as proven.

## 4. Part 2 (inferential): do rules that trade the levels make money after costs?

Method exactly as in section 0 (31 variants, walk-forward past-only scales, F0/F1/F2 fills, 0.10% cost, Newey-West p, Holm over the 31 variants per window and fill convention, a placebo in two drift settings, Diebold-Mariano and Kupiec for the model-level rules). Net = gross minus 0.10%. **Hourly rules (R3, R4) have no Development window** (the hourly file starts in Oct 2024) and their Validation window is Dec 2024 - Jun 2025 (the first-hour scale needs 40 sessions to start).

### 4.1 Primary variants: Final window in detail, and which verdict conditions failed

| rule | variant | sessions | trades | fill rate | gross % | net % | net Rs | win rate | p HAC | Holm p | placebo p (A) | placebo p (B) | MDE % (80% power) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | R1_k1.0 | 320 | 86 | 27% | -0.30 | -0.40 | -14 | 35% | 0.986 | 1.00 | 0.915 | 0.837 | 0.45 |
| R2 | R2_k1.0 | 320 | 95 | 30% | -0.22 | -0.32 | -11 | 41% | 0.994 | 1.00 | 0.789 | 0.871 | 0.31 |
| R3 | R3_z1.5 | 306 | 45 | 15% | -0.19 | -0.29 | -9.8 | 36% | 0.879 | 1.00 | 0.670 | 0.668 | 0.60 |
| R4 | R4a | 306 | 246 | 80% | +0.14 | +0.04 | +1.3 | 56% | 0.338 | 1.00 | 0.069 | 0.075 | 0.23 |
| R5 | R5_z1.0 | 320 | 56 | 18% | +0.08 | -0.02 | -0.6 | 45% | 0.524 | 1.00 | 0.413 | 0.452 | 0.68 |
| R6 | R6_long_s1_t2 | 320 | 320 | 100% | -0.06 | -0.16 | -5.4 | 34% | 0.990 | 1.00 | 0.268 | 0.080 | 0.17 |
| R7 | R7_post_q25 | 320 | 85 | 27% | -0.31 | -0.41 | -14 | 38% | 0.987 | 1.00 | none | none | 0.45 |
| R8 | R8_post_q75 | 320 | 78 | 24% | -0.19 | -0.29 | -9.9 | 41% | 0.986 | 1.00 | none | none | 0.32 |

MDE = the smallest true mean net return per trade that would be detected with 80% power at one-sided 5% (2.49 times the Newey-West standard error). Placebo p = share of simulated no-edge histories whose net mean is at least the observed one; A = zero drift, B = drift matched to the window.

The verdict is **validated** only if every condition below holds (fixed in 0.6):

| rule | variant | Final net > 0 and Holm p < 0.05 | Holm placebo p < 0.05 (A and B) | net > 0 in Validation (and Development) | net > 0 with 1-tick fill | post-auction slice not significantly negative | placebo available | verdict |
|---|---|---|---|---|---|---|---|---|
| R1 | R1_k1.0 | NO | NO | NO | NO | yes | possible | **not found** |
| R2 | R2_k1.0 | NO | NO | NO | NO | NO | possible | **not found** |
| R3 | R3_z1.5 | NO | NO | NO | NO | yes | possible | **not found** |
| R4 | R4a | NO | NO | yes | yes | yes | possible | **descriptive** |
| R5 | R5_z1.0 | NO | NO | NO | NO | yes | possible | **not found** |
| R6 | R6_long_s1_t2 | NO | NO | NO | NO | yes | possible | **not found** |
| R7 | R7_post_q25 | NO | NO | NO | NO | yes | not possible (no placebo) | **not found** |
| R8 | R8_post_q75 | NO | NO | NO | NO | yes | not possible (no placebo) | **not found** |

**descriptive** = gross mean above zero with unadjusted p < 0.05 in some window, or net above zero in Final without meeting every condition; it means 'something happened in this sample', not 'tradable'. **not found** = anything else.

### 4.2 Primary variants across the four windows (net % per trade; number of trades in brackets)

| rule | variant | Development | Validation | Final | post-closing-auction |
|---|---|---|---|---|---|
| R1 | R1_k1.0 | +0.02 (377) | -0.56 (67) p=0.989 | -0.40 (86) p=0.986 | +0.09 (16) |
| R2 | R2_k1.0 | -0.35 (314) | -1.30 (57) p=0.999 | -0.32 (95) p=0.994 | -0.38 (18) |
| R3 | R3_z1.5 | no hourly data | -1.54 (15) p=1.000 | -0.29 (45) p=0.879 | +0.31 (5) |
| R4 | R4a | no hourly data | +0.47 (105) p=0.001 | +0.04 (246) p=0.338 | -0.14 (35) |
| R5 | R5_z1.0 | -0.08 (301) | +0.20 (54) p=0.321 | -0.02 (56) p=0.524 | -0.28 (13) |
| R6 | R6_long_s1_t2 | -0.26 (1355) | -0.23 (248) p=0.998 | -0.16 (320) p=0.990 | -0.04 (51) |
| R7 | R7_post_q25 | +0.02 (259) | -0.65 (60) p=0.989 | -0.41 (85) p=0.987 | +0.07 (16) |
| R8 | R8_post_q75 | -0.47 (267) | -0.97 (63) p=0.990 | -0.29 (78) p=0.986 | -0.16 (16) |

The post-closing-auction slice has 51 daily and 42 hourly sessions; most cells there have 5-35 trades, and no p-value is shown below the 10-trade floor. It is a check for gross failure, not a test.

### 4.3 All 31 variants, Final window, strict fill (F0)

| variant | trades | fill rate | gross % | net % | net % with 0.05% extra per marketable leg | p HAC | Holm p | placebo p A | placebo p B |
|---|---|---|---|---|---|---|---|---|---|
| R1_k1.0 | 86 | 27% | -0.30 | -0.40 | -0.45 | 0.986 | 1.00 | 0.915 | 0.837 |
| R2_k1.0 | 95 | 30% | -0.22 | -0.32 | -0.37 | 0.994 | 1.00 | 0.789 | 0.871 |
| R1_k0.5 | 170 | 53% | -0.32 | -0.42 | -0.47 | 1.000 | 1.00 | 0.978 | 0.926 |
| R2_k0.5 | 174 | 54% | -0.23 | -0.33 | -0.38 | 0.999 | 1.00 | 0.888 | 0.962 |
| R1_k1.5 | 32 | 10% | -0.55 | -0.65 | -0.70 | 0.991 | 1.00 | 0.943 | 0.915 |
| R2_k1.5 | 47 | 15% | -0.18 | -0.28 | -0.33 | 0.995 | 1.00 | 0.674 | 0.748 |
| R5_z1.0 | 56 | 18% | +0.08 | -0.02 | -0.12 | 0.524 | 1.00 | 0.413 | 0.452 |
| R5_z0.5 | 142 | 44% | -0.02 | -0.12 | -0.22 | 0.744 | 1.00 | 0.543 | 0.612 |
| R5_z1.5 | 29 | 9% | -0.37 | -0.47 | -0.57 | 0.947 | 1.00 | 0.810 | 0.844 |
| R6_long_s1_t2 | 320 | 100% | -0.06 | -0.16 | -0.25 | 0.990 | 1.00 | 0.268 | 0.080 |
| R6_long_s2_t1 | 320 | 100% | -0.24 | -0.34 | -0.41 | 1.000 | 1.00 | 0.448 | 0.170 |
| R6_short_s1_t2 | 320 | 100% | +0.09 | -0.01 | -0.10 | 0.572 | 1.00 | 0.002 | 0.016 |
| R6_short_s2_t1 | 320 | 100% | -0.19 | -0.29 | -0.36 | 1.000 | 1.00 | 0.143 | 0.412 |
| R7_emp_q25 | 74 | 23% | -0.05 | -0.15 | -0.20 | 0.811 | 1.00 | 0.599 | 0.492 |
| R7_emp_q10 | 21 | 7% | -0.26 | -0.36 | -0.41 | 0.992 | 1.00 | 0.707 | 0.659 |
| R8_emp_q75 | 68 | 21% | -0.19 | -0.29 | -0.34 | 0.985 | 1.00 | 0.719 | 0.799 |
| R8_emp_q90 | 19 | 6% | -0.07 | -0.17 | -0.22 | 0.749 | 1.00 | 0.542 | 0.591 |
| R7_post_q25 | 85 | 27% | -0.31 | -0.41 | -0.46 | 0.987 | 1.00 | none | none |
| R7_pre_q25 | 86 | 27% | -0.39 | -0.49 | -0.54 | 0.993 | 1.00 | none | none |
| R7_post_q10 | 33 | 10% | -0.21 | -0.31 | -0.36 | 0.866 | 1.00 | none | none |
| R7_pre_q10 | 34 | 11% | +0.02 | -0.08 | -0.13 | 0.590 | 1.00 | none | none |
| R8_post_q75 | 78 | 24% | -0.19 | -0.29 | -0.34 | 0.986 | 1.00 | none | none |
| R8_pre_q75 | 77 | 24% | -0.28 | -0.38 | -0.43 | 0.998 | 1.00 | none | none |
| R8_post_q90 | 26 | 8% | -0.06 | -0.16 | -0.21 | 0.757 | 1.00 | none | none |
| R8_pre_q90 | 25 | 8% | -0.30 | -0.40 | -0.45 | 0.988 | 1.00 | none | none |
| R3_z1.5 | 45 | 15% | -0.19 | -0.29 | -0.39 | 0.879 | 1.00 | 0.670 | 0.668 |
| R3_z1.0 | 88 | 29% | -0.23 | -0.33 | -0.43 | 0.975 | 1.00 | 0.837 | 0.839 |
| R3_z2.0 | 15 | 5% | +0.48 | +0.38 | +0.28 | 0.213 | 1.00 | 0.222 | 0.223 |
| R3t_z1.5 | 45 | 15% | -0.18 | -0.28 | -0.38 | 0.897 | 1.00 | 0.686 | 0.692 |
| R4a | 246 | 80% | +0.14 | +0.04 | -0.06 | 0.338 | 1.00 | 0.069 | 0.075 |
| R4b | 189 | 62% | +0.18 | +0.08 | -0.02 | 0.158 | 1.00 | 0.033 | 0.033 |

No variant has a Holm-adjusted p below 1.0 in the Final window. 3 of the 31 variants have a positive net mean (R4b, R3_z2.0, R4a); the smallest unadjusted p among them is 0.158. Windows other than Final, fill conventions F1 and F2, and every statistic are in `hl_trade_holm.csv` and `hl_trade_rules.csv`; the table in Appendix A gives net % and trades for every variant in every window.

### 4.4 By calendar year (primary variants, net % per trade, trades in brackets, F0)

| rule | variant | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 15 Oct) |
|---|---|---|---|---|---|---|---|---|---|
| R1 | R1_k1.0 | -0.29 (63) | +0.30 (75) | -0.12 (66) | -0.61 (58) | +0.49 (82) | -0.02 (68) | -0.73 (65) | -0.28 (53) |
| R2 | R2_k1.0 | +0.23 (57) | -0.29 (54) | -0.85 (60) | -0.42 (47) | -0.19 (67) | -1.04 (54) | -0.88 (63) | -0.28 (64) |
| R3 | R3_z1.5 | - | - | - | - | - | -1.97 (1) | -0.90 (35) | -0.11 (24) |
| R4 | R4a | - | - | - | - | - | +0.31 (8) | +0.32 (195) | -0.04 (148) |
| R5 | R5_z1.0 | +0.18 (52) | -0.25 (55) | -0.12 (68) | +0.17 (49) | -0.37 (59) | +0.42 (44) | -0.16 (43) | -0.01 (41) |
| R6 | R6_long_s1_t2 | -0.33 (244) | -0.29 (251) | -0.25 (247) | -0.26 (247) | -0.15 (245) | -0.30 (246) | -0.23 (248) | -0.08 (195) |
| R7 | R7_post_q25 | - | +0.22 (49) | +0.07 (54) | -0.53 (60) | +0.31 (59) | -0.05 (68) | -0.86 (61) | -0.25 (53) |
| R8 | R8_post_q75 | - | -0.28 (47) | -0.83 (68) | -0.20 (53) | -0.42 (71) | -0.70 (60) | -0.79 (58) | -0.24 (51) |

Years in which the net mean was positive: R1 2 of 8, R2 1 of 8, R3 0 of 3, R4 2 of 3, R5 3 of 8, R6 0 of 8, R7 3 of 7, R8 0 of 7. R4 has data only for late 2024 to 2026 and fades in 2026. Years with 45-70 trades have a standard error of 0.15-0.3% per year, so single-year differences are mostly noise.

### 4.5 Fill conventions and cost stress (Final, net % per trade, trades in brackets)

| rule | variant | F0: strictly through | F1: one tick through | F2: 0.10% through | F0 with extra 0.05% per marketable leg | F0 gross (no cost) |
|---|---|---|---|---|---|---|
| R1 | R1_k1.0 | -0.40 (86) | -0.40 (86) | -0.49 (81) | -0.45 | -0.30 |
| R2 | R2_k1.0 | -0.32 (95) | -0.32 (95) | -0.39 (89) | -0.37 | -0.22 |
| R3 | R3_z1.5 | -0.29 (45) | -0.29 (45) | -0.29 (45) | -0.39 | -0.19 |
| R4 | R4a | +0.04 (246) | +0.05 (245) | +0.16 (232) | -0.06 | +0.14 |
| R5 | R5_z1.0 | -0.02 (56) | -0.02 (56) | -0.02 (56) | -0.12 | +0.08 |
| R6 | R6_long_s1_t2 | -0.16 (320) | -0.16 (320) | -0.18 (320) | -0.25 | -0.06 |
| R7 | R7_post_q25 | -0.41 (85) | -0.41 (85) | -0.46 (82) | -0.46 | -0.31 |
| R8 | R8_post_q75 | -0.29 (78) | -0.29 (78) | -0.38 (72) | -0.34 | -0.19 |

**Do not read F2 for the stop-entry rule R4a as a conservative case.** F2 keeps only breakouts that went at least 0.10% beyond the range, yet assumes the fill at the range edge; that selects trades by what the price did after entry, which flatters a breakout rule (R4a net rises from +0.04% to +0.16%, p = 0.035 unadjusted). A real stop order would have been filled on the marginal breakouts too, and those are the ones that fail. F2 is a fair stress only for resting limit orders (R1, R2, R7, R8), where it makes results worse, as the table shows. The pre-fixed verdict uses F0 for the test and F1 for the robustness condition, so this does not touch any verdict.

### 4.6 What a rule with no edge looks like (placebo)

2,000 simulated random-walk histories per setting (same dates, same past-only scale estimators, same variance profile across the day, same fill rules, same 0.10% cost). Final window, F0. 'Null' = the distribution, over the simulated histories, of the net mean per trade. The per-trade standard deviations are shown so that the simulated and the real trades can be compared.

| rule | variant | observed net % | null mean net % (A) | null sd of the mean (A) | null 95th pct (A) | null 95th pct (B) | mean simulated trades vs real trades | per-trade sd %: simulated vs real |
|---|---|---|---|---|---|---|---|---|
| R1 | R1_k1.0 | -0.40 | -0.08 | 0.24 | +0.30 | +0.21 | 85 vs 86 | 2.21 vs 1.66 |
| R2 | R2_k1.0 | -0.32 | -0.13 | 0.24 | +0.25 | +0.36 | 85 vs 95 | 2.20 vs 1.51 |
| R3 | R3_z1.5 | -0.29 | -0.11 | 0.40 | +0.54 | +0.52 | 38 vs 45 | 2.49 vs 1.95 |
| R4 | R4a | +0.04 | -0.11 | 0.10 | +0.06 | +0.06 | 281 vs 246 | 1.71 vs 1.51 |
| R5 | R5_z1.0 | -0.02 | -0.09 | 0.30 | +0.42 | +0.46 | 66 vs 56 | 2.42 vs 1.98 |
| R6 | R6_long_s1_t2 | -0.16 | -0.20 | 0.07 | -0.09 | -0.14 | 320 vs 320 | 1.25 vs 1.28 |
| R7 | R7_post_q25 | -0.41 | none (model quantiles cannot be re-fitted inside a simulation) |  |  |  |  |  |
| R8 | R8_post_q75 | -0.29 | none (model quantiles cannot be re-fitted inside a simulation) |  |  |  |  |  |

Plain reading: a rule with no edge earns roughly minus the cost (-0.13% to -0.08% net for the single-fill limit and entry rules; the fixed bracket R6 sits near -0.20% because the conservative 'stop first when both levels are touched' reading is pessimistic by construction). **Fill-conditional selection did not manufacture an edge here**: the simulated gross mean per fill is within 0.031 percentage points of zero for R1, R2 and R5 (`hl_trade_holm.csv`, column `null_mean_gross_pct_A`). The luck range matters more than any bias: with 38-85 trades a pure-noise rule has a 95th percentile of +0.25% to +0.54% net per trade, so a single window showing +0.2% means nothing. The R6 placebo p-values must not be read as evidence: the placebo's days are more two-sided than real days (section 6), which makes the conservative reading look worse in the simulation than in the data; the short 1%/2% bracket has a placebo p of 0.002 in Final while its observed net mean is -0.01% (Newey-West p 0.57); it lost money.

### 4.7 The project's estimated levels against a plain trailing-quantile level (R7/R8 versus the 250-session empirical quantile)

Diebold-Mariano (Harvey-Leybourne-Newbold, lag 5) on the daily net profit and loss of the limit order at the model's post-open quantile versus the same order at the trailing-250-session empirical quantile of the same variable; no-fill days count as zero. Positive DM t means the model level did better. Kupiec tests whether the fill frequency matches the promised quantile. The profit-and-loss differences are sparse and heavy-tailed, so treat the t values as indicative.

| model variant | benchmark | window | days | model: mean daily net P&L % | benchmark: mean daily net P&L % | DM t | p (two-sided) | Holm p (all 16 rows) | model fill rate (Kupiec p) | benchmark fill rate (Kupiec p) | promised |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R7_post_q25 | R7_emp_q25 | Final | 320 | -0.108 | -0.035 | -4.31 | <0.001 | <0.001 | 26.6% (p 0.52) | 23.1% (p 0.43) | 25% |
| R7_post_q25 | R7_emp_q25 | post-closing-auction | 51 | +0.022 | +0.082 | -3.03 | 0.004 | 0.057 | 31.4% (p 0.31) | 29.4% (p 0.47) | 25% |
| R7_post_q10 | R7_emp_q10 | Final | 320 | -0.032 | -0.024 | -0.41 | 0.684 | 1.000 | 10.3% (p 0.85) | 6.6% (p 0.03) | 10% |
| R7_post_q10 | R7_emp_q10 | post-closing-auction | 51 | +0.015 | -0.008 | 0.89 | 0.377 | 1.000 | 9.8% (p 0.96) | 9.8% (p 0.96) | 10% |
| R8_post_q75 | R8_emp_q75 | Final | 320 | -0.070 | -0.061 | -0.58 | 0.563 | 1.000 | 24.4% (p 0.80) | 21.2% (p 0.11) | 25% |
| R8_post_q75 | R8_emp_q75 | post-closing-auction | 51 | -0.049 | -0.065 | 0.52 | 0.608 | 1.000 | 31.4% (p 0.31) | 27.5% (p 0.69) | 25% |
| R8_post_q90 | R8_emp_q90 | Final | 320 | -0.013 | -0.010 | -0.23 | 0.822 | 1.000 | 8.1% (p 0.25) | 5.9% (p 0.01) | 10% |
| R8_post_q90 | R8_emp_q90 | post-closing-auction | 51 | -0.039 | -0.035 | -0.35 | 0.726 | 1.000 | 11.8% (p 0.68) | 7.8% (p 0.60) | 10% |

Plain reading: (1) the model's post-open levels are touched about as often as promised in every window (smallest Kupiec p 0.20); among the pre-open model levels only R7_pre_q25 in the post-closing-auction slice (39.2% against 25%, n = 51, p = 0.026) departs. The trailing-quantile benchmark is off more often (6 of 20 variant-window cells have p < 0.05: 4 in the Development window and 2 in Final; its 10% and 90% levels were touched on only 6-7% of Final days against 10%). (2) In Final neither the model's nor the benchmark's resting orders made money (every mean daily net P&L in the Final rows above is negative); the positive means in the 51-day slice rest on 5-16 fills each. (3) For the 25% low order the model level did **worse** than the plain trailing quantile in Final (DM t = -4.3, Holm p < 0.001, 320 days) and in the post-auction slice (t = -3.0, Holm p = 0.057, 51 days); for the other three pairs there is no difference. This is about the profit and loss of an order, not about the accuracy of the quantile (pinball loss and coverage of the levels themselves are specialist A's tables).

### 4.8 Fixed brackets from the open (R6): does the order of events matter?

On the hourly sample (n = 479; 306 in Final) the order of the stop and the target can be resolved whenever they fall in different hours. Net % per session, stop and target as shown (same-hour conflicts scored stop-first in the resolved column).

| bracket | window | sessions | both levels touched | both in the same hour | net % conservative (stop first) | net % hourly-resolved | net % optimistic (target first) |
|---|---|---|---|---|---|---|---|
| R6_long_s1_t2 | Final | 306 | 7.5% | 2.0% | -0.15 | -0.10 | +0.08 |
| R6_long_s1_t2 | post-closing-auction | 42 | 7.1% | 0.0% | -0.17 | -0.10 | +0.04 |
| R6_long_s2_t1 | Final | 306 | 5.2% | 1.0% | -0.34 | -0.28 | -0.19 |
| R6_long_s2_t1 | post-closing-auction | 42 | 9.5% | 2.4% | -0.52 | -0.37 | -0.23 |
| R6_short_s1_t2 | Final | 306 | 5.2% | 1.0% | -0.01 | +0.05 | +0.14 |
| R6_short_s1_t2 | post-closing-auction | 42 | 9.5% | 2.4% | +0.03 | +0.10 | +0.32 |
| R6_short_s2_t1 | Final | 306 | 7.5% | 2.0% | -0.28 | -0.16 | -0.05 |
| R6_short_s2_t1 | post-closing-auction | 42 | 7.1% | 0.0% | -0.24 | -0.10 | -0.03 |

The hourly-resolved result lies between the two bounds and is negative for 3 of the 4 brackets in Final (the exception is R6_short_s1_t2 at +0.05%, n = 306, which is not distinguishable from zero). A trader who 'always uses a bracket from the open' paid the cost and got nothing in return. The result depends on the ordering convention by more than the whole cost: in Final the conservative and optimistic readings differ by 0.16-0.23 percentage points against a cost of 0.10.

### 4.9 Does the choice of price source matter? (Yahoo against the official NSE bars)

The hourly file is Yahoo's; the daily file is NSE's official bar. Differences in rupees, Yahoo minus NSE, same sessions:

| quantity | n | mean Rs | mean absolute Rs | 90th pct of absolute | 99th pct of absolute | max absolute | share above Rs 5 |
|---|---|---|---|---|---|---|---|
| Yahoo hourly high minus NSE official high, all hourly sessions | 479 | -1.2 | 1.3 | 3.5 | 11.5 | 46.4 | 5% |
| Yahoo hourly low minus NSE official low, all hourly sessions | 479 | 1.9 | 1.9 | 4.5 | 17.1 | 54.7 | 9% |
| Yahoo first printed open minus NSE official open, all hourly sessions | 479 | -0.9 | 6.0 | 14.0 | 43.0 | 60.2 | 36% |
| Yahoo last-bar close minus NSE official close, all hourly sessions | 479 | 0.2 | 5.7 | 15.9 | 36.2 | 86.8 | 35% |
| Yahoo hourly high minus NSE official high, from 2025-07-01 | 306 | -1.0 | 1.1 | 2.3 | 10.8 | 46.4 | 4% |
| Yahoo hourly low minus NSE official low, from 2025-07-01 | 306 | 1.1 | 1.2 | 2.9 | 9.0 | 16.1 | 5% |
| Yahoo first printed open minus NSE official open, from 2025-07-01 | 306 | -1.8 | 4.2 | 10.0 | 30.8 | 60.2 | 25% |
| Yahoo last-bar close minus NSE official close, from 2025-07-01 | 306 | 0.6 | 2.9 | 7.5 | 18.8 | 31.0 | 20% |
| Yahoo hourly high minus NSE official high, closing-auction slice | 42 | -2.1 | 2.1 | 4.0 | 22.4 | 30.4 | 7% |
| Yahoo hourly low minus NSE official low, closing-auction slice | 42 | 0.9 | 0.9 | 1.8 | 6.4 | 9.0 | 2% |
| Yahoo first printed open minus NSE official open, closing-auction slice | 42 | -3.1 | 5.2 | 10.6 | 42.3 | 57.9 | 29% |
| Yahoo last-bar close minus NSE official close, closing-auction slice | 42 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0% |

Plain reading: Yahoo's hourly high is on average Rs 1.2 below NSE's official high and Yahoo's low Rs 1.9 above NSE's official low (Yahoo's range is about Rs 3 narrower). On nine sessions in ten the gap is within Rs 3.5 (high) and Rs 4.5 (low), which is close to the 'up to about Rs 4' in the project's input audit (docs/INPUT_AUDIT.md); but 5% (high) and 9% (low) of sessions differ by more than Rs 5, and the largest gaps are Rs 46 and Rs 55. Yahoo's first printed open differs from the official open by Rs 6.0 on average (up to Rs 60; 36% of sessions by more than Rs 5), and its last bar from the official close by Rs 5.7 on average before the closing auction and by Rs 0.0 since (the close is then the auction price). So a rule that depends on 'the open', 'the high' or 'the close' needs a precise definition: I use the official NSE open, high, low and close wherever the rule allows it, and the official open can be traded only through the pre-open call auction (orders by 09:08).

Re-running R1, R2, R5 and R6 on the hourly sample with Yahoo's own open, extremes and last price instead of the official ones changed the Final-window net means by 0.01 to 0.08 percentage points (R1 -0.33 vs -0.35; R2 -0.25 vs -0.23; R5 +0.04 vs -0.03; R6 long 1%/2% -0.16 vs -0.12). For the hourly rules, exiting at Yahoo's last printed price instead of the official close changed the Final net means by 0.00 to 0.12 percentage points (R4a +0.04 vs +0.03). `hl_trade_crosscheck.csv`. No verdict depends on the price source; R5 flips from slightly positive to slightly negative, which is noise around zero.

### 4.10 A reference point: where the stock's average return comes from

Buying at every official open and selling at every official close (gross, no cost) averaged -0.035% per day over all 1923 sessions (Newey-West t = -0.55) and -0.119% in Final (n = 320, t = -1.00), while the average gap (previous close to open) was +0.274% per day (all) and +0.211% (Final). In this sample the stock's gain came overnight; the trading day itself was flat on average. Buying and holding from 1 Jan 2019 multiplied the (bonus-adjusted) price 51.6 times, 3.2 times in the Validation year and 1.24 times in Final. That is a description of the past, not an overnight trading rule (it was not one of the eight rules). A stock that rose about fifty-fold has a large drift in any sample, which is a likely reason the sell-the-spike rules R2 and R8 lost money before costs (gross -0.22% and -0.19% per trade in Final) even though their levels were reached as often as promised; I did not test that explanation.

## 5. Post-hoc looks (exploratory; found after seeing the results; cannot change a verdict)

Every number in this section comes from rules written down only after seeing that R2 and R8 lost money in a consistent direction. They are the mirror image of the failed rules (trade WITH the move through the level instead of against it) plus R4a split into long and short. I counted all 16 post-hoc variants, so the Holm family below is 31 + 16 = 47. The stop-entry is assumed filled at the level (generous for a stop order). Two marketable legs, so the 'extra slippage' column charges 0.10% in all.

### 5.1 The mirror of the failed rules (buy when the high trades through the upper level; sell short when the low trades through the lower level)

| variant | id | Development net % (n) | Validation net % (n) | Final net % (n) | post-auction net % (n) | Final p HAC | Final Holm p (47) | Final placebo p (A) | Final placebo p (P0) | Final net % with 0.10% extra slippage |
|---|---|---|---|---|---|---|---|---|---|---|
| M2: buy-stop at open + 1 sigma_H | M2_k1.0 | +0.15 (314) | +1.10 (57) | +0.12 (95) | +0.18 (18) | 0.170 | 1.00 | 0.211 | 0.216 | +0.02 |
| M2: buy-stop at open + 0.5 sigma_H | M2_k0.5 | -0.01 (672) | +0.52 (126) | +0.13 (174) | +0.02 (29) | 0.119 | 1.00 | 0.112 | 0.111 | +0.03 |
| M2: buy-stop at open + 1.5 sigma_H | M2_k1.5 | +0.17 (175) | +0.88 (32) | +0.08 (47) | +0.13 (12) | 0.217 | 1.00 | 0.327 | 0.338 | -0.02 |
| M1: sell-stop at open - 1 sigma_L | M1_k1.0 | -0.22 (377) | +0.36 (67) | +0.20 (86) | -0.29 (16) | 0.131 | 1.00 | 0.086 | 0.088 | +0.10 |
| M1: sell-stop at open - 0.5 sigma_L | M1_k0.5 | +0.01 (787) | +0.25 (136) | +0.22 (170) | +0.33 (25) | 0.031 | 1.00 | 0.022 | 0.025 | +0.12 |
| M1: sell-stop at open - 1.5 sigma_L | M1_k1.5 | -0.38 (171) | +0.51 (30) | +0.45 (32) | -0.10 (5) | 0.047 | 1.00 | 0.057 | 0.064 | +0.35 |
| M8: buy-stop at trailing 75% high level | M8_emp_q75 | +0.06 (394) | +0.87 (64) | +0.09 (68) | +0.04 (14) | 0.256 | 1.00 | 0.282 | 0.294 | -0.01 |
| M8: buy-stop at trailing 90% high level | M8_emp_q90 | +0.24 (169) | +1.21 (28) | -0.03 (19) | +0.24 (4) | 0.551 | 1.00 | 0.458 | 0.472 | -0.13 |
| M7: sell-stop at trailing 25% low level | M7_emp_q25 | -0.17 (372) | +0.24 (64) | -0.05 (74) | -0.48 (15) | 0.606 | 1.00 | 0.402 | 0.401 | -0.15 |
| M7: sell-stop at trailing 10% low level | M7_emp_q10 | -0.41 (173) | +0.17 (27) | +0.16 (21) | -0.12 (5) | 0.125 | 1.00 | 0.294 | 0.291 | +0.06 |
| M8: buy-stop at the model's 75% high | M8_post_q75 | +0.27 (267) | +0.77 (63) | +0.09 (78) | -0.04 (16) | 0.248 | 1.00 | none | none | -0.01 |
| M8: buy-stop at the model's 90% high | M8_post_q90 | +0.40 (107) | +1.24 (23) | -0.04 (26) | +0.13 (6) | 0.579 | 1.00 | none | none | -0.14 |
| M7: sell-stop at the model's 25% low | M7_post_q25 | -0.22 (259) | +0.45 (60) | +0.21 (85) | -0.27 (16) | 0.124 | 1.00 | none | none | +0.11 |
| M7: sell-stop at the model's 10% low | M7_post_q10 | -0.46 (98) | -0.12 (31) | +0.11 (33) | -0.35 (5) | 0.345 | 1.00 | none | none | +0.01 |
| R4a long breakouts only | R4a_long | - | +0.44 (50) | +0.03 (102) | +0.09 (9) | 0.423 | 1.00 | 0.192 | 0.180 | -0.07 |
| R4a short breakouts only | R4a_short | - | +0.49 (55) | +0.05 (144) | -0.22 (26) | 0.367 | 1.00 | 0.122 | 0.120 | -0.05 |

Plain reading: the mirror of R2 (buy when the high trades 1 sigma above the open) shows +0.26% net per trade over all years (n = 466, unadjusted p 0.011, Holm over the 47 variants 0.48; the same idea at the model's post-open 75% high level, M8: +0.31%, n = 408, p 0.005, Holm 0.22) and +0.12% in Final (n = 95, p 0.170; M8 +0.09%, p 0.248). With the 0.10% extra slippage that a stop order realistically pays, the Final result of M2 is +0.02%. The gains are bunched in 2021, 2024, 2025 (below); in 2026 M2 earned +0.08%. The pattern fits 'a strongly trending stock keeps going once it breaks out of its usual daily range', which is a statement about a bull market, not about the quality of the high/low estimates. **Suggestive only.** It cannot be validated on the data in hand: it was found after looking, the smallest Holm-adjusted p over the 47 variants is 0.22 for all years and 1.00 in Final, and no pre-fixed momentum rule (R4) held up in Final either.

By calendar year (net % per trade, F0; trades in brackets):

| variant | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| M2_k1.0 | -0.43 (57) | +0.09 (54) | +0.65 (60) | +0.22 (47) | -0.01 (67) | +0.84 (54) | +0.68 (63) | +0.08 (64) |
| M2_k0.5 | -0.37 (111) | -0.30 (135) | +0.54 (111) | -0.11 (120) | +0.02 (141) | +0.31 (118) | +0.52 (123) | +0.10 (113) |
| M1_k0.5 | +0.07 (152) | -0.02 (147) | -0.10 (148) | +0.44 (130) | -0.36 (144) | +0.05 (135) | +0.46 (135) | +0.09 (102) |
| M8_post_q75 | - | +0.08 (47) | +0.63 (68) | +0.00 (53) | +0.22 (71) | +0.50 (60) | +0.59 (58) | +0.04 (51) |
| R4a_long | - | - | - | - | - | -0.03 (4) | +0.23 (90) | +0.08 (58) |
| R4a_short | - | - | - | - | - | +0.64 (4) | +0.40 (105) | -0.12 (90) |

### 5.2 R4 (the one descriptive rule) split by direction, and pooled

R4a long and R4a short each look like the whole: in Validation +0.44% (n = 50) and +0.49% (n = 55), in Final +0.03% (n = 102) and +0.05% (n = 144), so the Validation result was not just a bull-market long bias, and the Final-window fade affects both sides. Pooled over every eligible hourly session (439 sessions), R4a earned +0.17% net per trade (n = 351; Newey-West p 0.023, Holm over 31 variants 0.69; placebo p 0.004) and its neighbour R4b +0.20% (n = 271; p 0.004, Holm 0.12, Holm-adjusted placebo p 0.043). So, pooled, the rule looks significant; split in time, it was concentrated in the Validation half-year and is gone in Final. The pre-fixed test is the Final window, and I follow it: a pooled number dominated by one half-year is not validation. The project's own earlier note (docs/LIVE_TOOLS.md: 'follow the first-hour move: +0.8% per trade, t 3.3 in the first 60% of the sample, about zero in the last 40%') describes the same fade independently.

### 5.3 Does the placebo's variance clock change the conclusions? (settings P0 and P1)

The pre-fixed placebo (A, B) builds the intraday variance clock as the mean of session-normalised squared hourly returns. That estimator is biased toward an equal split because of ratio noise. A pooled ratio-of-sums clock gives the first hourly bar a larger share (0.46 against 0.40 of the day's variance; the whole clock is in `hl_trade_clock.csv`). I re-ran the whole placebo with it (P0 = zero drift, P1 = matched drift; same seeds). Result for the rules that matter:

| variant | window | trades | net % | placebo p: A | B | P0 (pooled clock) | P1 |
|---|---|---|---|---|---|---|---|
| R4a | val | 105 | +0.47 | 0.010 | 0.009 | 0.009 | 0.009 |
| R4a | final | 246 | +0.04 | 0.069 | 0.075 | 0.067 | 0.077 |
| R4b | val | 82 | +0.48 | 0.006 | 0.007 | 0.005 | 0.006 |
| R4b | final | 189 | +0.08 | 0.033 | 0.033 | 0.028 | 0.030 |
| R1_k1.0 | val | 67 | -0.56 | 0.874 | 0.895 | 0.870 | 0.904 |
| R1_k1.0 | final | 86 | -0.40 | 0.915 | 0.837 | 0.913 | 0.826 |
| R2_k1.0 | val | 57 | -1.30 | 0.992 | 0.988 | 0.992 | 0.987 |
| R2_k1.0 | final | 95 | -0.32 | 0.789 | 0.871 | 0.785 | 0.878 |
| R3_z1.5 | val | 15 | -1.54 | 0.928 | 0.928 | 0.942 | 0.939 |
| R3_z1.5 | final | 45 | -0.29 | 0.670 | 0.668 | 0.680 | 0.682 |
| R5_z1.0 | val | 54 | +0.20 | 0.287 | 0.231 | 0.288 | 0.234 |
| R5_z1.0 | final | 56 | -0.02 | 0.413 | 0.452 | 0.415 | 0.450 |
| R6_long_s1_t2 | val | 248 | -0.23 | 0.051 | 0.111 | 0.056 | 0.109 |
| R6_long_s1_t2 | final | 320 | -0.16 | 0.268 | 0.080 | 0.272 | 0.090 |

The placebo p-values barely move with the clock, and the conclusion for every rule is unchanged. What does depend on the clock is the first-hour comparison in section 3.4: with the pre-fixed clock the observed share of sessions with the high or low in the first hour looks slightly high (p 0.020 for all years, 0.397 in Final), with the pooled clock it looks about equal (p 0.516 all years, 0.117 in Final). The honest summary is 'consistent with a random walk with a U-shaped variance profile; the exact verdict depends on how that profile is estimated'.

## 6. What failed, and honest limits

* **Nothing was validated.** R1, R2, R3, R5, R6, R7 and R8 are 'not found'; R4 is 'descriptive' because its Final-window net mean is above zero, but it is not distinguishable from zero there and turns negative with a further 0.05% per leg (-0.06%).
* **Power is low.** Final-window MDEs for the primary variants range from 0.17% (R6, 320 trades) to 0.68% (R5, 56 trades) per trade. Effects of the size that survive costs (0.1-0.2% per trade) are below the detection limit of every rule. The daily sample has 1,923 sessions, but only 24%-28% of them produce a fill for the 1-sigma limit rules; the hourly sample has 479 sessions.
* **Two years of hourly data are one market episode** (the price multiplied 3.2 times in the Validation year and 1.24 times in Final, section 4.10). Any rule that needs a trend, or the lack of one, is confounded with that episode.
* **The placebo is a random walk with a fitted variance clock, not reality** (`hl_trade_placebo_diag.csv`). In the all-years, Development, Validation and Final windows its days are wider than the real ones (in the 51-session auction slice the two agree) (median high-to-low range 3.06% real against 3.29% simulated, 5-95% band of the simulation 3.21-3.37%) and more two-sided: the share of sessions that reach both -1% and +2% from the open is 8.1% in Final against 12.1% simulated (short side 5.0% against 11.9%). Real trades are also less noisy than simulated ones for the limit-order and first-hour rules (per-trade sd in Final: R1 1.66% real against 2.21% simulated; R4a 1.51% against 1.71%). Placebo p-values are therefore somewhat conservative for the limit-order rules and not meaningful for the fixed brackets (4.6). The real days are also lumpier: both extremes in the first hour on 13.6% of sessions against 4.8%-7.9%. The real open is an auction print and is the day's high or low on 10.6% of sessions, which a continuous-path placebo cannot reproduce. For rules whose observed means are negative none of this matters; the verdicts rest on the Newey-West tests, with the placebo as a second, necessary condition.
* **Execution is idealised.** Limit and stop orders fill at the level when the extreme trades through it; no queue position, no partial fills, no market impact (not measured), no slippage except the S1 stress. Entering 'at the official open' needs the pre-open call auction (orders by 09:08) or a first-print market order; the first printed open differs from the official one by Rs 6.0 on average. The close is a 30-minute VWAP before 3 Aug 2026 and an auction price after it; a trader cannot always exit at it.
* **The 0.10% round-trip cost is the assigned conservative figure**, not a measured cost for any particular account. Gross numbers are shown beside every net number so the reader can substitute their own. With a cost of 0.05% instead of 0.10% the best primary variant in Final would be R4a at +0.09% per trade, unadjusted p = 0.17; no primary variant would reach p < 0.05 (R5 would turn slightly positive, +0.03%, p = 0.45).
* **R7 and R8 use specialist A's model, which was chosen by the project using the Validation and Final windows** (A's independent verifier, item 9), so Final is not completely untouched for them. If that matters at all it flatters R7/R8, and they lost money anyway.
* **Not tested**: any use of news, index, peers, options or volume; positions held overnight; sizing rules as strategies (section 7 is descriptive); intraday exits other than the close, the stop and the target listed; model quantiles at levels other than the four stored ones. The pinball loss, coverage and Kupiec tests of the high and low quantiles themselves are specialist A's tables, not repeated here.
* **Contradictions with earlier project claims**: none found. This work agrees with the project's statement that the first-hour concentration of highs and lows is a random-walk feature, with its note that the 10:15 follow-the-first-hour rule faded, with DEVIATIONS item 30 (buying the predicted low and selling the predicted high lost money after a 0.10% cost; breakout entries roughly broke even) and with items 31 and 33 (rules that looked good early in a sample reversed later). It adds that the first-hour share depends on the placebo clock (5.3) and that the opening print is the day's extreme about one session in ten (not a random-walk feature).

## 7. What a trader can honestly do with a good high/low estimate

These are uses that the data support as description (Part 1), not as a source of profit.

1. **Know how far an ordinary day travels and size accordingly.** From the open, the day's low was a median Rs 45 and a 90th percentile Rs 115 below it; the high a median Rs 41 and Rs 112 above (Final, n = 320). Swings differ with the regime: the median low-below-open is Rs 34 in the calmest third of sessions and Rs 58 in the busiest (all years, full-sample terciles). If you risk a fixed rupee amount per trade, the share count should shrink as the swing grows: shares = rupee risk / stop distance in rupees. Example with a Rs 10,000 risk budget on a long: a stop at the median adverse swing (Rs 45, hit on about half the days) allows 222 shares; a stop at the 75th percentile (Rs 80, hit on about one day in four) allows 124; at the 90th percentile (Rs 115) 86. This is arithmetic on the table in 3.1, not a recommended risk size.
2. **Place the stop outside ordinary noise, or accept being stopped.** Entering at the open, a stop 0.5% below (Rs 17) was touched on 81% of Final sessions, 1% (Rs 34) on 60%, 1.5% on 42%, 2% (Rs 69) on 32%. A stop at the trailing-250-session 75th percentile of the adverse swing (about Rs 89, 2.6%) was touched on 23.1% of Final days against 25% nominal (Kupiec p = 0.43); at the median distance (Rs 49) on 44.7% (p = 0.06). A stop is the price of insurance, not a profit centre: a wider stop lowers the chance of being stopped but raises the loss when it is hit, and the fixed brackets (R6) did not pay.
3. **Do not enter late hoping for a fresh extreme.** After 13:15 the median remaining swing is about Rs 16-17 either way (Final), after 14:15 about Rs 11-14, and by 14:15 the day's high is already in on 79% of sessions (3.5). The round trip costs about Rs 3.4 at 0.10%.
4. **Use the estimate to set expectations, not to enter against the move.** How good is the estimate? Recomputed here from specialist A's stored file (`hl_trade_model_miss.csv`, Final, n = 320): the pre-open median forecast of the high is off by Rs 43 on average (Rs 34 typical, i.e. half the time within that), the low by Rs 48 (Rs 32); after the open is known the misses are Rs 35 (high) and Rs 37 (low), against Rs 51 / Rs 59 for 'the open is the high / low'. That is smaller than the naive guesses (specialist A's tests, not mine, say the improvement is statistically solid) and the levels are calibrated (reached as often as promised), but the miss is of the same order as the swing it is trying to locate: the median swing from the open is Rs 41-45, the typical (median) miss of the estimate Rs 27-34, and the cost only Rs 3.4. A target at the estimated high is a reasonable place to think about taking profit on a long you already hold; selling short at the estimated high is a rule that lost money (R2, R8: Final -0.32% and -0.29% net per trade, n = 95 and 78), and so is buying at the estimated low (R1, R7: -0.40% and -0.41%).
5. **Count costs at your own number.** At 0.10% a round trip costs about Rs 3.4 a share at today's price; a single 1% stop-out is Rs 34, ten times that. The costs are small next to the swing; what is missing is a direction edge, not a cheaper broker.
6. **Beware of the one result that looks like an edge.** Following a breakout of the first-hour range made money in the Dec 2024 - Jun 2025 sample and then stopped; if you try it, treat it as an experiment with a known fade, paper-trade it, and expect about zero until proven otherwise (section 5.2).

**What it cannot do**: it cannot tell you the direction; it cannot say whether the stock will touch the estimated high or low before the close with more certainty than the quantile says (it is calibrated to be touched 25% of the time at the 25% level, and is); it cannot turn that touch into a reversal entry (R1, R2, R7, R8 and R3 failed); it cannot time the day (the first-hour concentration is a variance-profile feature); it cannot be improved by a bracket (R6); and with the data available it cannot support a claim of an edge smaller than about 0.2-0.7% per trade.

## 8. Applying Part 1 to the Friday 16 Oct 2026 session (descriptive; uses nothing dated after the 15 Oct close)

Reference price: Rs 3,428 (15 Oct official close; open 3,342.0, high 3,445.0, low 3,315.2). Scales going into 16 Oct (exponentially weighted, lambda 0.94, through the 15 Oct session): close-to-close 2.26% (Rs 77), gap 0.78% (Rs 27), open-to-close 2.03% (Rs 69), open-to-low 1.90% (Rs 65), open-to-high 2.01% (Rs 69). Volatility regime: mid (pre-fixed expanding terciles), mid (full-sample, post hoc), low (trailing-500, post hoc).

How far the day's low (high) has been from the open, in percent and rupees at Rs 3,428 (`hl_trade_today_2026-10-16.csv`):

| sample | sessions | extreme | 25th pct | median | 75th pct | 90th pct |
|---|---|---|---|---|---|---|
| trailing 250 sessions to 15 Oct 2026 | 250 | price falls below the open | 0.59% (20) | 1.22% (42) | 2.33% (80) | 3.12% (107) |
| trailing 250 sessions to 15 Oct 2026 | 250 | price rises above the open | 0.53% (18) | 1.26% (43) | 2.25% (77) | 3.30% (113) |
| Final window (2025-07-01 to 15 Oct 2026) | 320 | price falls below the open | 0.63% (22) | 1.31% (45) | 2.34% (80) | 3.37% (115) |
| Final window (2025-07-01 to 15 Oct 2026) | 320 | price rises above the open | 0.48% (16) | 1.20% (41) | 2.22% (76) | 3.26% (112) |
| since closing auction (2026-08-04 on) | 51 | price falls below the open | 0.56% (19) | 1.07% (37) | 2.49% (85) | 3.16% (108) |
| since closing auction (2026-08-04 on) | 51 | price rises above the open | 0.25% (8.4) | 1.04% (36) | 2.30% (79) | 3.23% (111) |

**Stop distance from the 16 Oct open** under the three estimators of 3.7 (distance in percent of the open and in rupees at Rs 3,428; the share is how often a stop at that distance has been touched, by promise). `hl_trade_today_stops_2026-10-16.csv`:

| side | touched on about | T250 | EXPANDING | EWMA_SCALED |
|---|---|---|---|---|
| long (stop below the open) | 50% | Rs 42 (1.22%) | Rs 41 (1.21%) | Rs 40 (1.17%) |
| long (stop below the open) | 25% | Rs 80 (2.33%) | Rs 74 (2.16%) | Rs 68 (2.00%) |
| long (stop below the open) | 10% | Rs 107 (3.12%) | Rs 123 (3.59%) | Rs 106 (3.10%) |
| short (stop above the open) | 50% | Rs 43 (1.26%) | Rs 36 (1.06%) | Rs 34 (1.00%) |
| short (stop above the open) | 25% | Rs 77 (2.25%) | Rs 77 (2.24%) | Rs 68 (1.97%) |
| short (stop above the open) | 10% | Rs 113 (3.30%) | Rs 137 (4.01%) | Rs 119 (3.48%) |

How to read it for the 16 Oct session: whatever the open is, a long entered there has had its low at least Rs 22 below it on three days in four, at least Rs 45 below on one day in two and Rs 115 or more on one day in ten (Final window); for a short, the high was at least Rs 16, Rs 41 and Rs 112 above the open on three days in four, one in two and one in ten. Rule R1 would place a buy limit 1 sigma below the open, i.e. about Rs 65 (1.88%) below, and R2 a sell limit about Rs 70 (2.03%) above; this report does not recommend either (both lost money in Final). For the estimated high and low of 16 Oct itself, see specialist A's report and `results/hl_dayahead_2026-10-16.json` (not mine); the relevant fact from this study is that touching those levels has not been a profitable place to trade against the move.

## 9. Numbers to quote

* No rule validated: 0 of 8 pre-fixed rules (31 variants) passed (`hl_trade_verdicts.csv`); 7 'not found', 1 ('follow the first-hour breakout', R4) 'descriptive' (net +0.04% in Final, p = 0.34).
* Estimated-low limit buy (R7, post-open 25% level), Final window: 85 fills in 320 sessions, -0.31% gross, -0.41% net = -Rs 14 per share per trade (`hl_trade_rules.csv`).
* Estimated-high limit sell (R8, post-open 75% level), Final window: 78 fills, -0.29% net = -Rs 9.9 per share per trade.
* Fill frequency of the model's levels in Final matched the promise: 26.6% against 25% (low, n = 320, Kupiec p = 0.52) and 24.4% against 25% (high, Kupiec p = 0.80) (`hl_trade_kupiec_fill.csv`).
* The model's 25% low level did worse than a plain trailing-quantile level in Final (DM t = -4.3, Holm p < 0.001, 320 days); no difference for the other three pairs (`hl_trade_dm.csv`).
* Follow-the-breakout (R4a): Validation +0.47% net per trade (n = 105, Holm p = 0.031), Final +0.04% (n = 246, p = 0.34), since the closing auction -0.14% (n = 35); with a further 0.05% per marketable leg the Final figure is -0.06%.
* Typical swing from the official open, Final (n = 320): median high Rs 41 above, median low Rs 45 below; 90th percentile Rs 112 / Rs 115 (`hl_trade_excursions.csv`).
* Entering at 10:15: median room left Rs 28 up / Rs 30 down (Final, n = 306); entering at 13:15: Rs 16 / Rs 17.
* A 1% stop with a 2% target from the open (long): stopped first 52-60%, target first 24-32%, neither 17% (Final, n = 320; daily bars give ranges because the order within a day is unknown).
* A 0.5% stop (Rs 17) is touched on 81% of Final sessions; a 1% stop (Rs 34) on 60%; a 2% stop (Rs 69) on 32%.
* High or low set in the first hour: 83.3% post-auction (35 of 42), 84.3% in Final (n = 306), 86.4% in all hourly sessions (n = 479); random-walk placebo 82.3% (A) to 87.5% (P0). Not a pattern.
* Official open equals the day's high or low in 10.6% of 1923 sessions (9.8% of 51 since the closing auction); open equals the previous close on 9 of 51 post-auction sessions.
* Yahoo hourly extremes against NSE official: mean absolute difference Rs 1.3 (high) and Rs 1.9 (low), 90th percentile Rs 3.5 / Rs 4.5, maximum Rs 46 / Rs 55; Yahoo's first printed open differs from the official open by Rs 6.0 on average (n = 479).
* Typical miss of A's median forecasts, Final (n = 320): pre-open high Rs 43 / low Rs 48; post-open Rs 35 / Rs 37 (recomputed in `hl_trade_model_miss.csv`; specialist A's own tables are the primary source).
* Power: Final-window MDE (80% power) 0.17% to 0.68% net per trade across the primary variants; 'not found' does not rule out smaller edges.
* Stock return split (all 1923 sessions): average gap +0.27% per day, average open-to-close -0.03% (Newey-West t -0.55); the price multiplied 51.6 times.
* Checks: self-test 12 of 12 passed; independent plain-loop re-computation 145 of 145 comparisons agree.

## 10. Files and exact commands to reproduce every number

All commands from the repository root; the hourly file is `h60_BSE.NS.json` (Yahoo chart API, `BSE.NS`, range 2y, interval 60m, fetched 15 Oct 2026, SHA-256 in `results/hl_trade_summary.json`; Yahoo's rolling window means a later download will not be identical, and a later download would also contain bars after the 15 Oct cut-off, which the code drops). `HL_TRADE_TMP` is where the placebo draws are kept between steps (default `/tmp/hl_trade`).

```
export HL_TRADE_TMP=/tmp/hl_trade
H=<path>/h60_BSE.NS.json
python3 src/hl_trade_study.py all --hourly $H --reps 2000 --procs 4        # everything below plus this report; about 4 minutes on 4 cores
```

| numbers | command (all run by `all`, in this order) | files |
|---|---|---|
| no-look-ahead and arithmetic checks (section 2) | `python3 src/hl_trade_study.py selftest --hourly $H` | hl_trade_selftest.csv |
| Part 1: excursions, stop/target, open and first hour, range formed, stop calibration and stop-distance estimators, Yahoo vs NSE, variance clock, open = previous close, regime for 16 Oct (sections 3, 4.9) | `python3 src/hl_trade_study.py part1 --hourly $H` | hl_trade_excursions.csv, hl_trade_stop_target_daily.csv, hl_trade_stop_target_hourly.csv, hl_trade_open_hl_real.csv, hl_trade_extreme_bar.csv, hl_trade_range_formed.csv, hl_trade_stop_calibration.csv, hl_trade_data_checks.csv, hl_trade_bracket_order.csv, hl_trade_open_equals_prev.csv, hl_trade_clock.csv, hl_trade_stop_forecast.csv, hl_trade_summary.json |
| Part 2 real-data results: 31 variants x 5 windows x 3 fill conventions, trades, by year, DM, Kupiec, Yahoo cross-check, typical miss of the stored forecasts, reference drift (sections 1, 4, 7) | `python3 src/hl_trade_study.py part2 --hourly $H` | hl_trade_rules.csv, hl_trade_trades.csv, hl_trade_byyear.csv, hl_trade_dm.csv, hl_trade_kupiec_fill.csv, hl_trade_crosscheck.csv, hl_trade_model_miss.csv, hl_trade_reference_drift.csv |
| placebo draws (4 settings x 2,000 histories; seed 20261015) | `python3 src/hl_trade_study.py placebo --hourly $H --reps 2000 --procs 4` | $HL_TRADE_TMP/placebo.npz (not kept in results/) |
| Holm, placebo p-values, verdicts, first-hour comparison with the placebo (sections 1, 3.4, 4.1-4.6) | `python3 src/hl_trade_study.py finish --hourly $H` | hl_trade_holm.csv, hl_trade_verdicts.csv, hl_trade_open_hl.csv |
| post-hoc variants, joint Holm, clock sensitivity P0/P1 (section 5) | `python3 src/hl_trade_study.py posthoc --hourly $H` | hl_trade_posthoc.csv, hl_trade_posthoc_byyear.csv, hl_trade_sensitivity_clock.csv, hl_trade_open_hl_clock.csv |
| numbers for 16 Oct (section 8) | `python3 src/hl_trade_study.py today --hourly $H` | hl_trade_today_2026-10-16.csv, hl_trade_today_stops_2026-10-16.csv, hl_trade_today_2026-10-16.json |
| independent plain-loop re-computation (section 2) | `python3 src/hl_trade_study.py indepcheck --hourly $H` | hl_trade_indepcheck.csv |
| placebo versus reality, tick-rounding sensitivity (sections 2, 6) | `python3 src/hl_trade_study.py diag --hourly $H` | hl_trade_placebo_diag.csv, hl_trade_sensitivity_tick.csv |
| this report's tables and text (every number is read from the files above; qualitative sentences are guarded by checks that stop the build if the files disagree) | `python3 src/hl_trade_study.py report` | research/hl/C_tradeability.md |

*Research on past data for a risk-management question; not investment advice.*

## Appendix A. Every variant in every window (F0, net % per trade after 0.10%; trades in brackets)

Development has no hourly rules (R3, R4); for R3/R4 the first column is the hourly sample after its 40-session burn-in (Dec 2024 - Oct 2026). Post-hoc variants are in section 5.

| variant | all 2019-2026 | Development | Validation | Final | post-closing-auction |
|---|---|---|---|---|---|
| R1_k1.0 | -0.12 (530) | +0.02 (377) | -0.56 (67) | -0.40 (86) | +0.09 (16) |
| R2_k1.0 | -0.46 (466) | -0.35 (314) | -1.30 (57) | -0.32 (95) | -0.38 (18) |
| R1_k0.5 | -0.27 (1093) | -0.21 (787) | -0.45 (136) | -0.42 (170) | -0.53 (25) |
| R2_k0.5 | -0.28 (972) | -0.19 (672) | -0.72 (126) | -0.33 (174) | -0.22 (29) |
| R1_k1.5 | -0.05 (233) | +0.18 (171) | -0.71 (30) | -0.65 (32) | -0.10 (5) |
| R2_k1.5 | -0.44 (254) | -0.37 (175) | -1.08 (32) | -0.28 (47) | -0.33 (12) |
| R5_z1.0 | -0.03 (411) | -0.08 (301) | +0.20 (54) | -0.02 (56) | -0.28 (13) |
| R5_z0.5 | -0.05 (945) | +0.04 (695) | -0.48 (108) | -0.12 (142) | +0.19 (23) |
| R5_z1.5 | -0.13 (200) | -0.10 (144) | +0.04 (27) | -0.47 (29) | -0.56 (8) |
| R6_long_s1_t2 | -0.24 (1923) | -0.26 (1355) | -0.23 (248) | -0.16 (320) | -0.04 (51) |
| R6_long_s2_t1 | -0.40 (1923) | -0.40 (1355) | -0.46 (248) | -0.34 (320) | -0.39 (51) |
| R6_short_s1_t2 | -0.12 (1923) | -0.12 (1355) | -0.22 (248) | -0.01 (320) | -0.05 (51) |
| R6_short_s2_t1 | -0.31 (1923) | -0.28 (1355) | -0.50 (248) | -0.29 (320) | -0.34 (51) |
| R7_emp_q25 | -0.10 (510) | -0.03 (372) | -0.44 (64) | -0.15 (74) | +0.28 (15) |
| R7_emp_q10 | +0.08 (221) | +0.21 (173) | -0.37 (27) | -0.36 (21) | -0.08 (5) |
| R8_emp_q75 | -0.36 (526) | -0.26 (394) | -1.07 (64) | -0.29 (68) | -0.24 (14) |
| R8_emp_q90 | -0.54 (216) | -0.44 (169) | -1.41 (28) | -0.17 (19) | -0.44 (4) |
| R7_post_q25 | -0.17 (404) | +0.02 (259) | -0.65 (60) | -0.41 (85) | +0.07 (16) |
| R7_pre_q25 | -0.23 (412) | -0.10 (260) | -0.39 (66) | -0.49 (86) | -0.16 (20) |
| R7_post_q10 | +0.08 (162) | +0.26 (98) | -0.08 (31) | -0.31 (33) | +0.15 (5) |
| R7_pre_q10 | +0.11 (166) | +0.20 (102) | -0.00 (30) | -0.08 (34) | +0.77 (9) |
| R8_post_q75 | -0.51 (408) | -0.47 (267) | -0.97 (63) | -0.29 (78) | -0.16 (16) |
| R8_pre_q75 | -0.54 (408) | -0.45 (274) | -1.18 (57) | -0.38 (77) | -0.35 (14) |
| R8_post_q90 | -0.65 (156) | -0.60 (107) | -1.44 (23) | -0.16 (26) | -0.33 (6) |
| R8_pre_q90 | -0.78 (157) | -0.67 (110) | -1.74 (22) | -0.40 (25) | -0.22 (4) |
| R3_z1.5 | -0.60 (60) | - | -1.54 (15) | -0.29 (45) | +0.31 (5) |
| R3_z1.0 | -0.65 (126) | - | -1.38 (38) | -0.33 (88) | +0.06 (13) |
| R3_z2.0 | -0.48 (24) | - | -1.92 (9) | +0.38 (15) | +2.49 (2) |
| R3t_z1.5 | -0.60 (60) | - | -1.54 (15) | -0.28 (45) | -0.35 (5) |
| R4a | +0.17 (351) | - | +0.47 (105) | +0.04 (246) | -0.14 (35) |
| R4b | +0.20 (271) | - | +0.48 (82) | +0.08 (189) | +0.07 (27) |

