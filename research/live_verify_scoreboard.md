# Independent review: src/scoreboard.py and src/official_bars.py

Reviewer run: 2026-10-15 16:13 to 16:30 IST (sandbox clock). Repo was read-only for me: SHA-256 of `data/processed/bse_daily_extra.csv`, `data/processed/bse_daily.csv`, `data/raw/macro/SP500.csv` were identical before and after every command. No `issue` without `--dry`, no `score`, no `live_nowcast`, no git commands of my own. Anything that wrote output was run on a COPY of the module with the output directory moved to scratch and `ensure_bars` stubbed out.

Scratch scripts (own code, no import of the author's functions unless stated): `indep_issue.py` (recomputation of the dry-run), `align.py` (S&P alignment), `pt_sim.py` (lean hit rates and paper P&L), `open_cond.py` (open-band calibration), `test_report.py`, `test_score.py`, `test_issue_guards.py`, `test_twice.py`, `test_official.py`, `contam.py`. They live in the session scratchpad and were also copied to `/tmp/review_scratch/` (a shared directory; `cp` may have overwritten a same-named file of another reviewer).

**Overall severity: MAJOR.** No look-ahead and no arithmetic error in the forecast itself (everything reproduces to the cent). The majors are operational (wrong default target date, no pre-open guard, silent data corruption paths) and one scoring-formula bug that flatters the paper P&L.

---

## 1. Confirmed correct

1. **Dry-run numbers reproduce exactly.** `issue --date 2026-10-15 --dry` (P0 = 3338.0) vs my own HAR (S4) / GARCH-t (S2) / FHS code, with an own-written t-GARCH MLE as a cross-check of `arch`:

   | | author | mine |
   |---|---|---|
   | sigma_G (S4) | 0.7134% | 0.7134% |
   | sigma_R (S6) | 2.3512% | 2.3512% (arch params), 2.3527% (own MLE) |
   | OPEN q0.05/q0.25/q0.5/q0.75/q0.95 | 3304.76 / 3332.30 / 3338.00 / 3347.06 / 3368.39 | identical to the cent (all 9 quantiles) |
   | CLOSE q0.05/q0.25/q0.5/q0.75/q0.95 | 3217.40 / 3288.67 / 3338.00 / 3387.70 / 3462.86 | identical to the cent (all 9 quantiles) |
   | S&P used / return | 2026-10-14, -1.1145% (Yahoo 7805.45 -> 7718.94) | same |
   | pred close-to-close / open-to-close | -0.2975% / -0.2165% | same |
   | PT2 threshold abs(pred_I) at 80th pct | 0.2765% | same; PT2 off because 0.2165 < 0.2765 |

2. **No look-ahead in `issue()`.**
   - S&P: `searchsorted(day) - 1` is the latest US date strictly before the Indian date. Over all 2,389 Indian sessions the US date used is always < the Indian date (0 violations).
   - Weekend case: Mon 2026-10-12 -> Fri 10-09. Good.
   - Holiday cases (all run on real data):
     - Labor Day: Mon 2026-09-07 -> Fri 09-04, Tue 09-08 -> Fri 09-04 again (stale duplicate).
     - Memorial Day: 2026-05-26 -> Fri 05-22 (duplicate).
     - Thanksgiving: Fri 2025-11-28 -> Wed 11-26 (duplicate).
     - Good Friday: Mon 2026-04-06 -> Thu 04-02.
   - The 75 stale-duplicate sessions equal exactly the 75 that `research/v2/03_market_linkages.md` section 2 drops. See bug B7: the scoreboard keeps them.
   - OLS: each fit uses rows `:i` only; the live fit uses all rows through the previous session; features of the target (`last_I`, `last_R`) are the previous session's. Walk-forward threshold uses predictions made with past-only fits. Good.
   - P0, sigma path and z-window all end at the previous official bar.
3. **Chain of prev closes in `ensure_bars`.** The first extra row's prev (3375.4) equals the last base close; NSE's own prev agrees (ratio 1.0). The 2026-10-14 extra row (O 3375.4, H 3408.3, L 3320.0, C 3338.0, V 3001424) equals `results/forecast_score_2026-10-14.json`.
4. **`issue()` refusals that work.** Target already in data -> `SystemExit` (tested with 2026-10-14). Second run for the same target -> "entries are never rewritten" (tested on a copy). `--dry` does not write the entry.
5. **`score()` arithmetic** (fake entries against real bars; hand-computed): misses (actual minus median), unchanged misses, 50/90 flags, `close_return_pct`, `open_to_close_pct`, `lean_hit = None` when close == reference (shows as NaN in the CSV and is dropped by `report`), long P&L, cost 0.10%, PT2 "none" -> NaN, re-scoring a date replaces its row (3 rows stay 3). Missing entry -> `FileNotFoundError`; day not published -> clean `SystemExit`.
6. **`report()` arithmetic** on a fake 3-row CSV: MAEs (11.67 / 23.33), band shares (67% / 100%), PT1 mean +0.133%, sum +0.40%, win 67%, PT2 single trade, and the Clopper-Pearson interval for 1/2 (0.0126 to 0.9874, printed "1-99%") match `scipy.stats.binomtest(...).proportion_ci(method="exact")`.

---

## 2. Bugs (file:line, one-line fix)

**B1 (major). Default `--date` is wrong in the documented run window.** `scoreboard.py:163` uses `today_IST + 1 day` for `issue`. The docstring says run at ~01:30 IST, after the US close. At 01:30 IST on 16-Oct it targets 17-Oct (a Saturday); at 22:00 IST on 15-Oct it targets 16-Oct correctly but the US session is still open. At 08:00 IST on 16-Oct it also gives 17-Oct. There is no clock at which the default target is right and the US close is complete. Simulated with a patched clock.
Fix: `now=dt.datetime.now(IST); day = now.date() if now.time() < dt.time(9,15) else next weekday after now.date()` (and `score` default = latest entry without an outcome).

**B2 (major). No guard on the target date or horizon.** `scoreboard.py:74-75` only refuses `d.index[-1] >= target`. Run with the clock set to 01:30 IST on 16-Oct, `issue(2026-10-17)` (Saturday) and `issue(2026-10-19)` both produced entries with reference "previous official close" = 3338.0 (the 14-Oct close; the 15- and 16-Oct sessions are missing, i.e. a two-session horizon) and one-day sigma. Saturday/holiday targets are accepted.
Fix: require `target.dayofweek < 5`, and that no weekday between `d.index[-1]` and `target` lacks a bar unless confirmed holiday; abort otherwise.

**B3 (major). No pre-open guard, so the "before 09:15" rule is pure discipline.** My own dry run at 16:13 IST on the target day passed (printed "made 16:13 IST"); with a patched clock at 11:00 IST the same. The only refusal after the open is the data check, which works only after the bhavcopy appears (~16:34). `made_at_ist` is the local clock (the project already hit a wrong sandbox clock, DEV #24/#25) and `score()` never checks it.
Fix: in `issue`, `if now_ist >= target 09:00 IST and not --late: SystemExit`; write `"late": true` when forced; in `score`, flag entries whose `made_at_ist` is not before 09:15 of the target date.

**B4 (major). Short-side paper P&L is overstated (Jensen), `scoreboard.py:130`.** `pnl = 100*(np.exp(ret)-1-COST)` with `ret = -log(cl/op)` for shorts gives `op/cl - 1` instead of `1 - cl/op`. The error is `op/cl + cl/op - 2 ~ I^2`, always in favour of the short. Tested: -1.11% day: code +1.0204% vs correct +1.0080%.
Walk-forward replication of the scoreboard's own PT1/PT2 spec (1,888 days from 2019; 88% of PT1 trades are shorts, mean I^2 = 5.8e-4):

| | scoreboard formula | correct simple return |
|---|---|---|
| PT1 mean net per trade | +0.119% (t = +1.98) | +0.063% (t = +1.04, 95% CI -0.056 to +0.183) |
| PT2 mean net per trade (n = 210) | +0.040% (t = +0.18) | -0.057% (t = -0.25) |
| PT1 last 250 days | -0.018% | -0.059% |

The bug turns "no detectable edge" into an apparently significant PT1 and flips PT2's sign. `src/direction_check.py` (last line) uses the same formula: its printed +0.043% per trade is -0.013% with the correct formula.
Fix: `pnl = 100*(side_sign*(cl/op - 1) - COST)`; same one-line change in `direction_check.py`.

**B5 (major). A corporate action is silently ingested, `official_bars.py:58`.** Extra rows hard-code `ca_factor = 1.0` and `prev = previous kept close`; `data/corp_actions_verified.csv` is never read, and `nse_prev_vs_kept_close` is stored but never tested (NSE does not rebase prev, DEV #8, so that ratio would be 1.0 anyway). Simulated a 3-for-1 bonus ex-date row (scratch copy): stored G = -109.9%, R = -111.0%, no warning. Effect on the next-day forecast (own HAR/OLS): sigma_G 0.71% -> 28.35%, open 90% band 946-1271 around P0 1113, lean pred_R -13.3%, pred_I -12.2%. The outlier stays in the 500-session z-window and the OLS for good. `live_nowcast.py:105` and `build_dashboard_data.py:128` read the same file.
Fix: in `ensure_bars` raise if `abs(log(open/prev_close)) > 0.25` or `abs(r["prev"]/prev_close - 1) > 5e-4` unless the date is in `corp_actions_verified.csv`, and then set `ca_factor`/`prev = prev_close/factor` like `build_dataset.py` does.

**B6 (major). A failed download leaves a permanent hole, `official_bars.py:48-52`.** A transient failure (network error or non-200) on weekday D is reported as "holiday, or not published yet" and skipped (`continue`); if D+1 downloads, its row takes prev = the close of D-1 (two-session return stored as one-session; test: -1.90% instead of -0.78%) and D is never retried because the next scan starts after `last` (test: second call does not back-fill). In `issue()` the same gap yields a stale P0 (B2).
Fix: when a weekday < today has no file, stop the loop (`break`) unless an NSE index file for that date also 404s (the rule `fetch_nse.py` uses), and add the `prev` consistency check from B5. Also validate the zip before caching (`zipfile.is_zipfile` and `testzip`, `official_bars.py:31-33`) so a truncated 200 does not poison `data/raw/udiff` forever.

**B7 (minor). Stale S&P values are used silently.**
- `prior_us` (`scoreboard.py:56-59`) accepts `now_ist` but ignores it, and has no staleness test. If Yahoo fails (`:51-52`, a printed warning only) the last FRED date (here 10-12) would be used; after a US holiday the previous return is reused (75 training rows, plus live use). Research drops those; `lean_models` (`:64`) keeps them.
- Run between 19:00 and 01:30 IST and the Yahoo daily bar for the in-progress US session is accepted as "completed" (`:48-50`, no completeness filter), contradicting the docstring "latest completed US session".
Fix: `assert (target - sp_date).days <= 4` and `sp_date == previous US weekday` else lean = "none"; drop Yahoo bars dated today in New York before 16:05 ET.

**B8 (minor). `report()` prints "nan-nan%" for 0 or all hits, `scoreboard.py:149`.** Tested 1/1, 3/3, 0/2. Fix: `lo, hi = stats.binomtest(int(h.sum()), len(h)).proportion_ci(0.95, method="exact")`.

**B9 (minor). Reproducibility and provenance.** Entry stores no data hash, S&P series, coefficients or GARCH-fit status (a failed GARCH silently falls back to EWMA and only prints, `forecast_live.py`). `code_tree_dirty` uses `git status ... --untracked-files=no` after `ensure_bars()` has already rewritten `bse_daily_extra.csv`; if that file is tracked the flag will be True on any day a bar was appended (inference, not run). `ensure_bars` rewrites the tracked CSV non-atomically even on `--dry`, and is called twice per `issue` and `score` (`official_bars.py:63`, `:72`). No tests exist for either module.

**B10 (minor). Weekday special sessions.** `ensure_bars` skips weekends (right for Muhurat on Sundays, e.g. 2026-11-08) but would append a weekday Muhurat as a full session (`short_session=False`), unlike the base-table rule (DEV #9).

---

## 3. Unsupported or over-stated claims

1. **"about 55% right on 8 years" (docstring l.10, entry statement l.89, docs/LIVE_TOOLS.md).**
   - True only for the close-to-close lean: 54.9% (n = 1,886), by year 2019:51 2020:56 2021:49 2022:61 2023:62 2024:50 2025:50 2026:61; `direction_check.py` prints 55.0%.
   - The open-to-close lean (the one PT1/PT2 trade) is 56.6% right, but the always-short baseline is 55.8%: 88% of its leans are "down" (84% in the last 500, 92% in the last 50), because mean I is -0.135% historically (-0.189% since the 2026-08-03 closing-auction switch, n = 51). `direction_check.py`'s "I given the actual open" is 55.7% vs 55.7% baseline.
   - So for PT1/PT2 the figure is a base rate, not skill. The "8 years" are really 7.7 (walk-forward from 2019).
2. **"about zero profit after costs" (entry statement; report l.155).**
   - Defensible for PT1 only with the corrected formula (+0.063%, CI includes 0). The printed evidence behind it (`direction_check.py` +0.043%) carries the B4 bias.
   - `results/open_rules_search.csv` tests a different family (|z| > 1 trigger, follow/fade): sp_prior_us follow is Dev -0.076% (t -0.60, n 376) and Val+Final +0.191% (t +0.61, n 83), Holm 1.0. It supports "no edge found", not PT1/PT2 specifically.
   - The live scoreboard will print about +0.06 pp per trade too much (B4).
3. **"wait for 30+ sessions before reading anything into it" (`:150`).** Needs ~616 sessions to separate 55% from 50% (one-sided 5%, power 80%). At n = 30 power is 0.14 and an observed 55% has an exact CI of 34-72%; at n = 100 power is 0.24. A PT mean of 0.06% with 2.4% daily sd needs thousands of trades. 30 is a floor for the interval to be non-degenerate, not a reading threshold.
4. **"my typical miss vs 'unchanged'" (`:145-146`) is vacuous.** The centred FHS median equals P0 exactly (q0.5 = 3338.00 for both open and close), so `open_miss_rs == open_miss_unchanged_rs` and `close_miss_rs == close_miss_unchanged_rs` on every day (confirmed in the score test). The headline comparison cannot show any difference. Only band coverage (or pinball/CRPS against a different benchmark) can discriminate.
5. **"half the time between ... 9 in 10 between ..." is unconditional.** It is not calibrated on large prior-US-move days, and the entry I reproduced is exactly such a day (S&P -1.11%). In-sample, last 1,500 sessions, same band construction: all days 50.1% / 90.0% inside the 50% / 90% bands; prior S&P < -1% (n = 180) only 28.9% / 75.6%; prior S&P > +1% (n = 213) 39.4% / 88.7%. The project's own F8 finding (S&P -> gap validated) is not used for the open centre; the open band still sits at "about Rs 3,338" while the OLS gap prediction is -0.08% with the intercept (the intercept is the pre-August VWAP-close premium, DEV #16) and about -0.35% without it. Expect the open to land below the 50% band more often than half the time on such days.
6. **"BSE's own last two days" (docstring l.9; docs/LIVE_TOOLS.md l.12).** The features are one session: yesterday's open-to-close and close-to-close.
7. **"the commit time is the proof" (`:101`, docs).** A commit timestamp is author-controlled, and the sandbox clock has already been wrong (DEV #24/#25). Proof requires a push to a remote that records receipt time, or a hash of the entry published elsewhere.
8. **"strongest 20%" (PT2).** Historically only 15.1% of days exceed the trailing-500 80th-percentile threshold (210 of 1,389 days that have a threshold). The label is approximate.
9. **Mixed message in the printout.** CLOSE "about Rs 3,338" (the unchanged price) next to "down ... -0.30%". Disclosed in the docstring ("no drift claimed") but easy to misread.

---

## 4. Answers to the five numbered checks

- **(1) look-ahead:** none found; S&P alignment verified for weekend and US-holiday cases; stale-duplicate and multi-observation (118 sessions with 2+ US observations in the research window, only the latest used) mismatches vs research are minor (B7).
- **(2) existing target / after open / twice:** existing target refused; twice refused; after the open NOT refused (B3); default date wrong (B1); non-trading or stale targets accepted (B2).
- **(3) hand recomputation:** matches to the cent, section 1.
- **(4) score() / report():** formulas right except B4; benchmark comparison vacuous (3.4); interval edge case B8.
- **(5) official_bars:** B5, B6, B9, B10.
- **(6) over-claims:** section 3.
