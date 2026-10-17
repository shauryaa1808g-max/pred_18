# v2 workstream "events": event reactions and structural change (NSE:BSE, session 2026-10-14)

Code: `src/behaviour/events.py` (the module docstring is the pre-registration: event inclusion rule, first-tradable-session rule, sign rule, every statistic, window and null, written before any event or break statistic was computed). Numbers: `results/behaviour/events.json` (every figure below is read from it). Reference price P0 = Rs 3,375.40 (NSE close 2026-10-13); v2 information cutoff 2026-10-13 22:00 IST. Nothing here is investment advice.

## 0. Provenance, order of work, cutoff exposure

| item | value |
|---|---|
| script as run | SHA-256 `41001d332421185f...` (full hash in JSON), seed 20261014, deterministic (second run byte-identical except run time) |
| tests | 22 Part A + 54 Part B primary + 12 Part B post-hoc sensitivity = 88 registered; 9 robustness-variant runs counted separately |
| order of work | (1) read brief, both dossiers, results_dates, DEVIATIONS, research/v2/01-02; (2) coverage-only data queries; (3) wrote the pre-registration and the event table in `events.py`; (4) simulated-data self-test; (5) first real run; (6) post-first-run changes, all listed in the docstring changelog and in section 9 below; (7) second run |
| NOT blind | I had read the printed reactions of most events (dossier A1-A15, B4 timeline, P-9, research/v2/01 s3) before writing the sign column. Signs and first-session choices could have been nudged by that knowledge; `judgement` and `timing_evidence` flags exist to expose it, and section 4.3 shows it matters. |
| cutoff exposure | **none.** The script has no network code and asserts every input row is dated <= 2026-10-13 (`max_date_in_inputs` = 2026-10-13). I ran no `fetch_*.py`, did not refresh `data/raw/macro`, did not open any price, quote or news page for BSE/NSE dated after the cutoff. Web access used: NSE archive `HEAD` requests on five pre-cutoff BSE filings; one WebFetch of the Investing.com earnings-history table (rows to 2026-08-04 plus an aggregator 'upcoming' row); one WebSearch for a pre-results consensus (returned only post-results articles dated Aug 2026). The sandbox clock (14 Oct) was used for nothing. The 14-Oct session was never seen. |
| independent check | Plain pandas/numpy re-computation (not the script's functions) reproduced R0, z0, AR0, beta, D5 and the volume multiple for R01, E10, T01, R15 and X05 to the printed precision, the B2 turnover effect (1.7227) and volatility effect (0.0353), the mean abs(z0) of the 27 gated events (1.7752) and the 14/20 hits with mean sign*R0 = +4.157%. |
| files written | `src/behaviour/events.py`, `results/behaviour/events.json`, this report. Nothing else; no git commands. |

## 1. Bottom line (numbers, not adjectives)

| # | Result | Status |
|---|---|---|
| 1 | **Event sessions are larger than ordinary sessions.** 27 gated non-earnings events: mean abs(z0) = 1.78 (95% CI [1.39, 2.18]) vs 0.75 for ordinary sessions (2019-2026, n = 1702); Holm over 22 tests 0.0011, over all 88 0.0044. Unscheduled (n=18): 2.03 (selection-exposed); scheduled (n=9): 1.27, raw p 0.0386, Holm 0.6184 (not established). Earnings (n=7): 1.30, raw p 0.0471, Holm 0.7072. | `descriptive_only` for NE; scheduled/earnings `not_found` after Holm |
| 2 | **Volume multiple.** Day-0 turnover / trailing-20 mean: non-earnings events 1.78x (median 1.69x) vs 0.83x ordinary (the ordinary figure is below 1 because the trailing mean contains spikes); earnings (n=7) 2.48x, Holm 0.0038. | `descriptive_only` |
| 3 | **Content-based sign rule.** Hit rate 14/20 = 70% (95% CI [0.50, 0.90]) vs chance 48.6%, raw p 0.0590; mean(sign*R0) = +4.16% (CI [1.76, 6.55]), Holm over 22 tests 0.0279, over 88 0.1302. **Not robust:** hit rate 12/14 for events whose reaction session was inferred from the dossier, 2/6 for events with a documented release time (Fisher p 0.0374, post hoc); mean(sign*R0) +5.85% vs +0.21%. The three scheduled hawkish macro prints all coincided with BSE gains. | `descriptive_only` at best; **do not use signs to forecast direction** |
| 4 | **Asymmetry.** Positive events do not move less or more than negative ones: mean abs(z0) negative 1.89 (n=13) vs positive 2.32 (n=7), diff -0.43 (CI [-1.39, 0.48]), p 0.4335. Direction-adjusted reaction: +5.54% mean R0 for positive vs -3.41% for negative events, difference of means of sign*R0 +2.13 pp (CI [-2.50, 6.99]), p 0.0578. | `not_found` |
| 5 | **Follow-through vs reversal.** F = sign(R0)*(5-day return after day 0)/sigma: signed events +0.16 (n=18; continuation share 50%) vs +0.80 (continuation 60%, n=214) after ordinary large-move days, p 0.4649; positive vs negative events +0.39 vs +0.01, p 0.7651. No evidence of systematic reversal; none of drift either. | `not_found` |
| 6 | **Formal documents vs verbal/reported news (unscheduled regulatory).** mean abs(z0) formal (order/circular/consultation, n=6) 2.23 vs verbal/media (n=8) 2.06; diff +0.17 (CI [-1.07, 1.43]), p 0.8093. Reports and remarks moved the stock as much as documents. | `not_found` (power: n 6 vs 8) |
| 7 | **Earnings (n=7, 10 extended).** Sign of revenue surprise matched sign of R0 in 6/7 (exact p 0.1429); Spearman(rev surprise, R0) +0.18 (p 0.7131); EPS surprise vs R0 +0.10 (n=5, p 0.9500); PAT QoQ +0.00; PAT YoY +0.16. PAT grew YoY and QoQ in all 7 and EPS beat in 5/5 vendor-comparable quarters, yet R0 was positive in only 3/7 and 2/5. Power at n=7: 51% for rho=0.8, 74% for rho=0.9. | `not_found (n<=7: ~no power)` |
| 8 | **Structural breaks (Part B).** 0 of 54 pre-specified cells survive Holm or BH over the Part B family (smallest claim p 0.0022: turnover at 2024-10-01, x5.6, 95% CI of the ratio 3.5-8.5x, Holm-54 0.1214). Block permutation alone would have flagged 8 of 54 at 5% (2.7 expected) but the self-test shows it has 39% size for a persistent-volatility null; the placebo-date rank flags 4; both together 2. | `not_found` family-wise; B2 turnover is the one large effect |
| 9 | **Gap distribution around the closing-auction date.** 250 sessions before 2026-08-03 vs the 50 since (post-hoc cell B8L): share G>0 -20.4 pp (CI -32.4 to -9.6), share G==0 +9.6 pp, median G -0.22 pp; claim p 0.0491 / 0.0626 / 0.1669; Holm over the 12 sensitivity cells 0.4906. BSE's positive-gap share **minus the Nifty's** was +15.2 pp in the 250 sessions before and -2.0 pp since; it was already 0.0 pp in July 2026 (n=23), so 2026-07-01 and 2026-08-03 cannot be told apart. | `not_found` after correction; point estimates large |
| 10 | **No directional or scale change for 14 Oct from this workstream.** The centre of the distribution is unchanged (no signed rule validated; gap median stays 0). Widening applies only conditional on a regulatory catalyst landing inside the session: see section 7. | |

## 2. The pre-registered event table (45 events)

Day 0 = first tradable session (rule in the docstring). `timing_evidence`: timestamp = primary file/filing stamp; press = dated press item; dossier = day taken from the dossier's reaction date (release time not independently verified); unknown. sign_V from the content rule; `J` = judgement-coded. `gated` events enter the tests; the two unknown-timing governance rows do not (G03 has a filing stamp but its information had been public since the SEBI approval letter).

| ID | Event | info date -> day 0 | timing (evidence) | type / form | sched. | sign_V | J | gated | set |
|---|---|---|---|---|---|---|---|---|---|
| E01 | Q4 FY24 results | 2024-05-08 -> 2024-05-09 | post_close (press) | earnings / results | Y | n/a |  | Y | EARN |
| E02 | Q1 FY25 results | 2024-08-07 -> 2024-08-08 | post_close (press) | earnings / results | Y | n/a |  | Y | EARN |
| E03 | Q2 FY25 results | 2024-11-12 -> 2024-11-13 | post_close (timestamp) | earnings / results | Y | n/a |  | Y | EARN |
| E04 | Q3 FY25 results | 2025-02-06 -> 2025-02-07 | post_close (press) | earnings / results | Y | n/a |  | Y | EARN |
| E05 | Q4 FY25 results | 2025-05-06 -> 2025-05-07 | post_close (timestamp) | earnings / results | Y | n/a |  | Y | EARN |
| E06 | Q1 FY26 results | 2025-08-07 -> 2025-08-08 | post_close (press) | earnings / results | Y | n/a |  | Y | EARN |
| E07 | Q2 FY26 results | 2025-11-11 -> 2025-11-12 | post_close (press) | earnings / results | Y | n/a |  | Y | EARN |
| E08 | Q3 FY26 results | 2026-02-09 -> 2026-02-10 | post_close (press) | earnings / results | Y | n/a |  | Y | EARN |
| E09 | Q4 FY26 results | 2026-05-07 -> 2026-05-08 | post_close (press) | earnings / results | Y | n/a |  | Y | EARN |
| E10 | Q1 FY27 results | 2026-08-04 -> 2026-08-05 | post_close (timestamp) | earnings / results | Y | n/a |  | Y | EARN |
| R01 | SEBI order on regulatory fee base for options (turnover charges) | 2024-04-29 -> 2024-04-29 | intraday (dossier_reaction_date) | regulatory / formal_order | N | -1 |  | Y | NE |
| R02 | SEBI F&O consultation paper (weekly expiry, lot size, upfront premium) | 2024-07-30 -> 2024-07-31 | post_close (dossier_reaction_date) | regulatory / consultation_paper | N | -1 |  | Y | NE |
| R03 | SEBI six-measure F&O circular | 2024-10-01 -> 2024-10-03 | post_close (dossier_reaction_date) | regulatory / formal_circular | N | -1 |  | Y | NE |
| R04 | Report: SEBI works out expiry-day solution (Tue/Thu) | 2025-03-28 -> 2025-03-28 | intraday (dossier_reaction_date) | regulatory / media_report | N | +1 |  | Y | NE |
| R05 | SEBI clears NSE Tuesday / BSE Thursday expiry swap | 2025-06-18 -> 2025-06-18 | intraday (dossier_reaction_date) | regulatory / media_report | N | +0 |  | Y | NE |
| R06 | SEBI interim order vs Jane Street (3 Jul) | 2025-07-03 -> 2025-07-04 | post_close (dossier_reaction_date) | regulatory / formal_order | N | -1 |  | Y | NE |
| R07 | SEBI chair on longer-tenor derivatives (verbal) | 2025-08-21 -> 2025-08-21 | intraday (dossier_reaction_date) | regulatory / verbal | N | -1 |  | Y | NE |
| R08 | Report: SEBI weighing end of weekly F&O | 2025-09-11 -> 2025-09-11 | intraday (dossier_reaction_date) | regulatory / media_report | N | -1 |  | Y | NE |
| R09 | Report: no change in weekly options expiry | 2025-11-07 -> 2025-11-07 | intraday (dossier_reaction_date) | regulatory / media_report | N | +1 |  | Y | NE |
| R10 | SEBI NOC to NSE IPO | 2026-01-30 -> 2026-01-30 | intraday (dossier_reaction_date) | market_structure / corporate_filing | N | -1 | Y | Y | NE |
| R11 | RBI circular on bank credit to capital-market intermediaries (13 Feb) | 2026-02-13 -> 2026-02-16 | post_close (dossier_reaction_date) | regulatory / formal_circular | N | -1 |  | Y | NE |
| R12 | NSE files DRHP | 2026-06-17 -> 2026-06-17 | intraday (dossier_reaction_date) | market_structure / corporate_filing | N | -1 | Y | Y | NE |
| R13 | SEBI says it will review expiry-settlement method (reported 3-4 Sep) | 2026-09-04 -> 2026-09-04 | pre_open (press) | regulatory / verbal | N | +1 |  | Y | NE |
| R14 | SEBI consultation paper on CAS / settlement (Sat 12 Sep; 14 Sep holiday) | 2026-09-12 -> 2026-09-15 | nontrading (timestamp) | regulatory / consultation_paper | N | +1 | Y | Y | NE |
| R15 | Reuters-sourced report: SEBI to revert derivatives settlement to 30-min VWAP | 2026-10-05 -> 2026-10-06 | post_close (timestamp) | regulatory / media_report | N | +1 |  | Y | NE |
| R16 | SEBI chair: CAS guidelines 'in about a week' (Sat 10 Oct 18:20 IST) | 2026-10-10 -> 2026-10-12 | nontrading (timestamp) | regulatory / verbal | N | +0 |  | Y | NE |
| R17 | NSE Indices announces BSE to replace Wipro in Nifty 50 | 2026-08-07 -> 2026-08-10 | post_close (dossier_reaction_date) | market_structure / index_review | N | +1 | Y | Y | NE |
| X01 | Expiry-day swap effective (NSE Tue / BSE Thu) | 2025-09-01 -> 2025-09-01 | intraday (timestamp) | regulatory / scheduled_impl | Y | +0 |  | Y | NE |
| X02 | RBI prop-funding curbs effective | 2026-07-01 -> 2026-07-01 | intraday (timestamp) | regulatory / scheduled_impl | Y | +0 |  | Y | NE |
| X03 | CAS goes live | 2026-08-03 -> 2026-08-03 | intraday (timestamp) | regulatory / scheduled_impl | Y | +0 |  | Y | NE |
| X04 | NSE lists (Rs 1,800) | 2026-09-24 -> 2026-09-24 | intraday (timestamp) | market_structure / scheduled_impl | Y | +0 |  | Y | NE |
| X05 | Nifty-50 inclusion effective after close (passive buying at close) | 2026-09-29 -> 2026-09-29 | intraday (timestamp) | market_structure / scheduled_impl | Y | +0 | Y | Y | NE |
| T01 | Union Budget (Sunday session): F&O STT hike | 2026-02-01 -> 2026-02-01 | intraday (dossier_reaction_date) | tax_budget / budget | Y | -1 |  | Y | NE |
| M01 | US-India trade deal announced (2 Feb, US hours) | 2026-02-02 -> 2026-02-03 | post_close (dossier_reaction_date) | macro / macro_release | N | +1 |  | Y | NE |
| M02 | Fed 25bp hike (16 Sep, ~23:30 IST) | 2026-09-16 -> 2026-09-17 | post_close (press) | macro / macro_release | Y | -1 |  | Y | NE |
| M03 | RBI MPC hikes repo to 5.50% | 2026-10-07 -> 2026-10-07 | intraday (press) | macro / macro_release | Y | -1 |  | Y | NE |
| M04 | India Sept CPI 5.54% (12 Oct ~16:00) | 2026-10-12 -> 2026-10-13 | post_close (press) | macro / macro_release | Y | -1 | Y | Y | NE |
| A01 | Jefferies Hold -> Underperform | 2026-08-17 -> 2026-08-17 | intraday (press) | analyst / rating_action | N | -1 |  | Y | ANALYST |
| A02 | Nuvama Buy -> Hold | 2026-08-18 -> 2026-08-18 | intraday (press) | analyst / rating_action | N | -1 |  | Y | ANALYST |
| A03 | Bernstein initiates Underperform | 2026-09-09 -> 2026-09-09 | intraday (press) | analyst / rating_action | N | -1 |  | Y | ANALYST |
| A04 | JPMorgan upgrade to Overweight (date approx.) | 2026-09-15 -> 2026-09-15 | intraday (press) | analyst / rating_action | N | +1 |  | Y | ANALYST |
| A05 | Macquarie initiates Outperform | 2026-09-24 -> 2026-09-24 | intraday (press) | analyst / rating_action | N | +1 |  | Y | ANALYST |
| G01 | MD&CEO Chauhan resignation | 2022-07-25 -> 2022-07-25 | unknown (unknown) | governance / corporate_filing | N | -1 |  | N | GOV |
| G02 | SEBI approval letter for new MD&CEO (28 Nov) | 2022-11-28 -> 2022-11-28 | unknown (unknown) | governance / corporate_filing | N | +1 |  | N | GOV |
| G03 | Board appoints Ramamurthy MD&CEO (filing 13:29 IST) | 2022-12-08 -> 2022-12-08 | intraday (timestamp) | governance / corporate_filing | N | +1 |  | N | GOV |

Timing corrections taken from the workstreams: the Reuters CAS story (R15) first appeared 5 Oct 20:32 IST, so its reaction session is 6 Oct, **not** 5 Oct (+4.39% on 5 Oct has no identified cause; research/v2/01 row 12). The Q2 FY27 board meeting is Wed 4 Nov 2026 (NSE filing 13 Oct 16:02:54 IST), outside every window. Earnings releases were all after 15:30 (17:19 to 20:45 IST); two re-checked by `HEAD` on the NSE archive (Q4 FY25 filing Last-Modified 19:03 IST; Q1 FY27 18:46 IST).

### 2.1 Per-event metrics (log returns in %; z = R / RMS of the 60 sessions before day 0; AR = market-model excess vs Nifty 50, beta from sessions [-260,-11])

| ID | R0 | G0 | I0 | z0 | AR0 | R1 | abs(R1)/sigma | D5 (days 1-5) | volume x | recovery (sessions to fully give back day-0 move) | beta | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E01 | -3.95 | -1.01 | -2.94 | -1.05 | -3.17 | -2.24 | 0.59 | +3.91 | 0.65 | 4 | 0.94 |  |
| E02 | +8.06 | +10.23 | -2.18 | +2.86 | +8.23 | +1.93 | 0.69 | +1.76 | 3.34 | >20 | 0.77 |  |
| E03 | -4.07 | +1.26 | -5.33 | -0.90 | -3.22 | +1.24 | 0.28 | +4.95 | 1.25 | 2 | 0.85 |  |
| E04 | +2.81 | -1.22 | +4.03 | +0.86 | +2.65 | -1.70 | 0.52 | -11.18 | 1.51 | 2 | 1.03 |  |
| E05 | +6.32 | +1.98 | +4.34 | +1.42 | +5.86 | +0.56 | 0.13 | +9.93 | 3.78 | >20 | 1.23 |  |
| E06 | -2.04 | +2.34 | -4.38 | -0.75 | -1.09 | +0.14 | 0.05 | +4.17 | 1.50 | 3 | 1.50 |  |
| E07 | +4.84 | +4.65 | +0.19 | +1.82 | +3.52 | -0.55 | 0.21 | +4.33 | 3.09 | 20 | 1.61 |  |
| E08 | +6.14 | +4.10 | +2.04 | +2.53 | +5.59 | +0.09 | 0.04 | -14.63 | 3.96 | 4 | 1.82 | 5d window overlaps R11 |
| E09 | -1.43 | +0.00 | -1.43 | -0.50 | -0.64 | +0.27 | 0.10 | +2.36 | 2.44 | 4 | 1.60 |  |
| E10 | -2.33 | +1.27 | -3.60 | -1.21 | -2.57 | -2.86 | 1.48 | -0.22 | 2.73 | >20 | 1.53 | 5d window overlaps R17 |
| R01 | -14.71 | -16.26 | +1.56 | -4.15 | -16.24 | +0.68 | 0.19 | +1.30 | 7.63 | >20 | 0.89 |  |
| R02 | +5.80 | -1.55 | +7.36 | +2.33 | +5.10 | +3.34 | 1.34 | -6.38 | 3.82 | 3 | 0.77 |  |
| R03 | +2.42 | -1.54 | +3.96 | +0.58 | +3.86 | +3.83 | 0.92 | +6.43 | 3.71 | 2 | 0.80 |  |
| R04 | +15.68 | +6.52 | +9.16 | +3.86 | +15.84 | -0.25 | 0.06 | -5.58 | 4.27 | >20 | 1.22 |  |
| R05 | -1.18 | -5.37 | +4.20 | -0.30 | -1.38 | -1.45 | 0.37 | +5.75 | 1.05 | 2 | 1.29 |  |
| R06 | -6.78 | -1.50 | -5.28 | -2.21 | -7.49 | +0.04 | 0.01 | -10.56 | 2.04 | >20 | 1.48 |  |
| R07 | -7.86 | +0.04 | -7.90 | -2.96 | -8.48 | +0.03 | 0.01 | -10.67 | 3.09 | >20 | 1.56 |  |
| R08 | -4.68 | +0.24 | -4.93 | -1.76 | -5.24 | +1.76 | 0.66 | +1.63 | 1.85 | 19 | 1.53 |  |
| R09 | +8.69 | -0.22 | +8.91 | +3.58 | +8.62 | -2.00 | 0.82 | +5.42 | 4.30 | >20 | 1.63 | 5d window overlaps E07 |
| R10 | -2.28 | -0.09 | -2.19 | -0.97 | -1.72 | -8.15 | 3.44 | +3.35 | 1.07 | 4 | 1.79 | 5d window overlaps T01,M01 |
| R11 | -7.57 | -7.38 | -0.19 | -2.95 | -9.19 | -2.25 | 0.87 | -2.87 | 2.22 | >20 | 1.86 |  |
| R12 | -4.00 | +0.42 | -4.42 | -1.54 | -4.89 | +0.38 | 0.15 | -2.86 | 1.71 | >20 | 1.63 |  |
| R13 | +3.09 | +2.80 | +0.29 | +1.59 | +2.82 | +1.06 | 0.55 | -0.76 | 1.69 | 3 | 1.42 | 5d window overlaps A03 |
| R14 | -2.21 | +0.97 | -3.18 | -1.16 | -0.66 | -2.14 | 1.12 | -2.29 | 0.82 | not within window | 1.43 | co-dated A04; 5d window overlaps M02 |
| R15 | +3.87 | +0.92 | +2.95 | +1.83 | +2.28 | +1.53 | 0.72 | +2.11 | 1.23 | not within window | 1.43 | 5d window overlaps R16,M03,M04 |
| R16 | +1.30 | +0.72 | +0.58 | +0.59 | +2.10 | +1.35 | 0.62 | n/a | 0.60 | not within window | 1.44 | 5d window overlaps M04 |
| R17 | +3.94 | +0.00 | +3.94 | +2.00 | +3.68 | +0.25 | 0.13 | -7.63 | 2.29 | 4 | 1.52 | 5d window overlaps A01 |
| X01 | +3.94 | +1.60 | +2.34 | +1.46 | +2.27 | +0.63 | 0.23 | +7.33 | 1.10 | 17 | 1.54 |  |
| X02 | +2.01 | +0.11 | +1.90 | +0.85 | +0.88 | -2.81 | 1.20 | -5.34 | 0.59 | 1 | 1.66 |  |
| X03 | -1.97 | +0.38 | -2.35 | -1.01 | -4.60 | +1.20 | 0.61 | +0.59 | 1.43 | >20 | 1.54 | 5d window overlaps E10,R17 |
| X04 | -2.69 | -1.10 | -1.60 | -1.36 | -0.55 | +0.24 | 0.12 | -4.42 | 1.33 | 7 | 1.42 | co-dated A05; 5d window overlaps X05 |
| X05 | +3.26 | +0.08 | +3.17 | +1.63 | +3.48 | -3.43 | 1.72 | +4.76 | 6.81 | 1 | 1.42 | 5d window overlaps R15,M03 |
| T01 | -8.15 | +0.11 | -8.26 | -3.46 | -4.76 | +4.68 | 1.99 | +11.66 | 4.10 | 2 | 1.79 | 5d window overlaps M01 |
| M01 | +5.73 | +5.35 | +0.38 | +2.18 | +1.06 | +1.23 | 0.47 | +10.40 | 1.46 | 19 | 1.82 | 5d window overlaps E08 |
| M02 | +0.58 | +0.46 | +0.12 | +0.30 | +0.09 | +0.23 | 0.12 | -2.33 | 0.61 | 2 | 1.43 | 5d window overlaps X04,A05 |
| M03 | +1.53 | -1.22 | +2.75 | +0.71 | +2.44 | -0.63 | 0.29 | n/a | 1.21 | 2 | 1.42 | 5d window overlaps R16,M04 |
| M04 | +1.35 | +0.05 | +1.29 | +0.62 | n/a | n/a | n/a | n/a | 0.73 | not within window | 1.44 |  |
| A01 | -3.39 | -1.67 | -1.73 | -1.73 | -3.07 | -0.72 | 0.37 | -0.58 | 2.27 | >20 | 1.51 | 5d window overlaps A02 |
| A02 | -0.72 | -1.00 | +0.28 | -0.36 | -0.07 | +1.32 | 0.66 | -0.15 | 1.57 | 1 | 1.46 |  |
| A03 | -3.12 | -2.78 | -0.34 | -1.64 | -2.01 | +0.49 | 0.26 | -0.94 | 0.90 | >20 | 1.42 | 5d window overlaps R14,M02,A04 |
| A04 | -2.21 | +0.97 | -3.18 | -1.16 | -0.66 | -2.14 | 1.12 | -2.29 | 0.82 | not within window | 1.43 | co-dated R14; 5d window overlaps M02 |
| A05 | -2.69 | -1.10 | -1.60 | -1.36 | -0.55 | +0.24 | 0.12 | -4.42 | 1.33 | 7 | 1.42 | co-dated X04; 5d window overlaps X05 |
| G01 | -1.45 | -0.09 | -1.36 | -0.44 | -0.95 | -0.87 | 0.26 | +2.40 | 0.45 | 4 | 1.44 |  |
| G02 | -0.20 | +0.00 | -0.20 | -0.13 | -0.64 | +1.65 | 1.07 | -0.12 | 0.96 | 1 | 1.36 |  |
| G03 | -1.10 | -0.29 | -0.80 | -0.77 | -1.46 | -0.40 | 0.28 | +0.92 | 0.66 | 3 | 1.38 |  |

Reading notes. (i) For `intraday` events G0 is pre-news and R0 is diluted by pre-release trading; for `post_close`/`nontrading` events G0 + I0 is the reaction. (ii) Beta from a 30-minute-VWAP close against a 15:30 index close is non-synchronous before 2026-08-03 (biased down, noisier); the AR column inherits that. (iii) M04 (13 Oct) has no Nifty row and no forward window. (iv) Largest day-0 moves: R01 -14.7%, R04 +15.7%, R09 +8.7%, T01 -8.1%, E02 +8.1%, R07 -7.9%, R11 -7.6%, R06 -6.8%, E05 +6.3%, E08 +6.1%.

### 2.2 Group descriptives

| group | n | mean R0 % | mean abs(R0) % | mean abs(z0) | median abs(z0) | max abs(z0) | mean abs(AR0) % | mean abs(zG0) | mean abs(zI0) | mean abs(R1)/sigma | mean D5 % | geo volume x | n down |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EARN7 | 7 | +1.06 | 3.88 | 1.30 | 1.21 | 2.53 | 3.21 | 0.81 | 1.01 | 0.33 | +1.56 | 2.48 | 4 |
| EARN10 | 10 | +1.44 | 4.20 | 1.39 | 1.13 | 2.86 | 3.65 | 0.99 | 0.98 | 0.41 | +0.54 | 2.12 | 5 |
| NE | 27 | -0.03 | 4.71 | 1.77 | 1.59 | 4.15 | 4.60 | 0.72 | 1.37 | 0.72 | -0.04 | 1.78 | 12 |
| NE_sched | 9 | -0.02 | 2.83 | 1.27 | 1.01 | 3.46 | 2.38 | 0.26 | 1.19 | 0.78 | +1.75 | 1.38 | 3 |
| NE_unsched | 18 | -0.04 | 5.66 | 2.03 | 1.92 | 4.15 | 5.59 | 0.95 | 1.46 | 0.69 | -0.78 | 2.03 | 9 |
| NE_pos | 7 | +5.54 | 6.17 | 2.31 | 2.00 | 3.86 | 4.99 | 0.88 | 1.61 | 0.55 | +0.24 | 1.94 | 1 |
| NE_neg | 13 | -3.41 | 5.21 | 1.89 | 1.76 | 4.15 | 5.79 | 0.78 | 1.46 | 0.83 | -1.03 | 2.05 | 8 |
| ANALYST | 5 | -2.43 | 2.43 | 1.25 | 1.36 | 1.74 | 1.27 | 0.78 | 0.74 | 0.51 | -1.68 | 1.28 | 5 |

Ordinary-session baseline (2019-01-01 to 2026-09-02, outside [day-1, day+5] of every listed event, n = 1702): mean abs(z0) 0.751, RMS z0 1.070, median abs(z0) 0.527, share with abs(z0) >= 1.5 12.6%.

By type (gated non-earnings): macro n=4 mean abs(z0)=0.95; market_structure n=5 mean abs(z0)=1.50; regulatory n=17 mean abs(z0)=1.95; tax_budget n=1 mean abs(z0)=3.46. By release timing: intraday n=15 mean abs(z0)=1.97; nontrading n=2 mean abs(z0)=0.88; post_close n=9 mean abs(z0)=1.67; pre_open n=1 mean abs(z0)=1.59. Macro prints (n=4, all scheduled or US-hours) produced the smallest reactions (0.95), tax_budget n=1 (Budget day) the largest per event (3.46).

## 3. Part A tests (22 hypotheses; Holm and BH within the family and across the whole 88-test registry)

| ID | hypothesis | n | estimate | 95% CI | raw p | Holm (22) | BH (22) | Holm (88) | status |
|---|---|---|---|---|---|---|---|---|---|
| A1_EARN7 | mean abs(z0) of EARN7 exceeds the pool of ordinary sessions | 7 | +1.304 | [0.862, 1.820] | 0.0471 | 0.7072 | 0.1297 | 1.0000 | not_found |
| A1_NE | mean abs(z0) of NE exceeds the pool of ordinary sessions | 27 | +1.775 | [1.387, 2.185] | <0.0001 | 0.0011 | 0.0004 | 0.0044 | descriptive_only |
| A1_NE_sched | mean abs(z0) of NE_sched exceeds the pool of ordinary sessions | 9 | +1.266 | [0.798, 1.934] | 0.0386 | 0.6184 | 0.1215 | 1.0000 | not_found |
| A1_NE_unsched | mean abs(z0) of NE_unsched exceeds the pool of ordinary sessions | 18 | +2.030 | [1.523, 2.530] | <0.0001 | 0.0011 | 0.0004 | 0.0044 | descriptive_only |
| A1_ANALYST | mean abs(z0) of ANALYST exceeds the pool of ordinary sessions | 5 | +1.250 | [0.777, 1.620] | 0.0875 | 1.0000 | 0.1745 | 1.0000 | not_found |
| A2a | mean(sign_V*R0) > 0 on NE_signed | 20 | +4.16% | [1.76, 6.55] | 0.0015 | 0.0279 | 0.0068 | 0.1302 | descriptive_only |
| A2b | mean(sign_V*AR0) > 0 on NE_signed | 19 | +4.22% | [1.79, 6.77] | 0.0041 | 0.0705 | 0.0152 | 0.3403 | not_found |
| A2c | hit rate P(sign(R0)=sign_V) > chance | 20 | 0.70 | [0.50, 0.90] | 0.0590 | 0.8099 | 0.1298 | 1.0000 | not_found |
| A3 | mean abs(z0)(negative) - mean abs(z0)(positive) != 0 | 20 | -0.429 | [-1.387, 0.482] | 0.4335 | 1.0000 | 0.6813 | 1.0000 | not_found |
| A4 | mean(s*R0 given s=+1) - mean(s*R0 given s=-1) != 0 (direction-adjusted reaction differs by sign) | 20 | +2.13% | [-2.50, 6.99] | 0.0578 | 0.8099 | 0.1298 | 1.0000 | not_found |
| A5a | mean F=sign(R0)*D5/sig of NE_signed differs from large-move ordinary days (abs(z0)>=1.5) | 18 | +0.159 | [-0.944, 1.250] | 0.4649 | 1.0000 | 0.6818 | 1.0000 | not_found |
| A5b | F(positive events) - F(negative events) != 0 | 18 | +0.385 | [-1.910, 2.608] | 0.7651 | 1.0000 | 0.8859 | 1.0000 | not_found |
| A6 | mean abs(z0) formal documents - verbal/reported news != 0 (unscheduled regulatory) | 14 | +0.170 | [-1.073, 1.432] | 0.8093 | 1.0000 | 0.8902 | 1.0000 | not_found |
| A7 | mean abs(z0) unscheduled - scheduled != 0 (selection diagnostic) | 27 | +0.764 | [-0.035, 1.500] | 0.0952 | 1.0000 | 0.1745 | 1.0000 | not_found |
| A8_NE | mean ln V0 of NE exceeds ordinary sessions | 27 | +0.580 (ln) | [0.315, 0.860] | <0.0001 | 0.0011 | 0.0004 | 0.0044 | descriptive_only |
| A8_EARN7 | mean ln V0 of EARN7 exceeds ordinary sessions | 7 | +0.908 (ln) | [0.587, 1.193] | 0.0002 | 0.0038 | 0.0011 | 0.0170 | descriptive_only |
| A9 | share of negative signed events fully retracing the day-0 loss within 5 sessions differs from ordinary large-loss days | 9 | 0.22 | [0.00, 0.56] | 0.7359 | 1.0000 | 0.8859 | 1.0000 | not_found |
| E1 | mean(sign(revenue surprise)*R0) > 0 (EARN7, exact permutation, two-sided) | 7 | +0.027 | n/a | 0.1429 | 1.0000 | 0.2418 | 1.0000 | not_found (n<=7: ~no power) |
| E2 | Spearman(revenue surprise %, R0), EARN7 exact permutation, two-sided | 7 | +0.179 | n/a | 0.7131 | 1.0000 | 0.8859 | 1.0000 | not_found (n<=7: ~no power) |
| E3 | Spearman(EPS surprise % (vendor basis), R0), EARN7 exact permutation, two-sided | 5 | +0.100 | n/a | 0.9500 | 1.0000 | 0.9952 | 1.0000 | not_found (n<=7: ~no power) |
| E4 | Spearman(PAT QoQ %, R0), EARN7 exact permutation, two-sided | 7 | +0.000 | n/a | 1.0000 | 1.0000 | 1.0000 | 1.0000 | not_found (n<=7: ~no power) |
| E5 | Spearman(PAT YoY %, R0), EARN7 exact permutation, two-sided | 7 | +0.162 | n/a | 0.7286 | 1.0000 | 0.8859 | 1.0000 | not_found (n<=7: ~no power) |

Null models: A1/A8 draw n sessions with replacement from the ordinary-session pool; A2/A4 shuffle R0 across events (signs fixed); A3/A6/A7 permute group labels; A5a/A9 compare with ordinary large-move days (abs(z0) >= 1.5 for A5a; z0 <= -1.5 for A9); E1-E5 enumerate all n! pairings. B = 20,000 (+1 correction). CIs: percentile bootstrap over events (5,000). **Effective n = number of events**; events overlapping in time are flagged in 2.1 (A5a restricted to the 9 events with uncontaminated 5-day windows: mean F +0.70).

### 3.1 Robustness variants (counted runs, not family members)

| variant | result |
|---|---|
| A1_W2_NE | {"n": 26, "mean": 1.393751, "p": 0.0002, "note": "pool is the day-0 abs(z0) pool (not 2-session); W2 scaled by sqrt2 so null mean is comparable only approximately"} |
| A1_EARN10 | {"n": 10, "mean": 1.389515, "p": 0.015149} |
| A8_EARN10 | {"n": 10, "geo": 2.125, "p": 0.00015} |
| A3_rawR0 | {"diff": -0.009616, "p": 0.62069} |
| A3_AR0 | {"diff": 0.007977, "p": 0.729635} |
| A5a_uncontaminated | {"n": 9, "mean_F": 0.699319} |
| A2a_timestamped_only | {"n": 6, "mean": 0.002136} |
| A2a_chrono_halves | {"first_half_n": 10, "first_half_mean": 0.06061, "second_half_n": 10, "second_half_mean": 0.022524} |
| A2c_by_timing_evidence_POSTHOC | {"table_rows_dossier_inferred_vs_documented": [[12, 2], [2, 4]], "odds_ratio": 12.0, "p_two_sided": 0.03741, "mean_sR0_dossier_inferred": 0.058466, "n_dossier_inferred": 14, "mean_sR0_documented": 0.002136, "n_documented": 6} |

Chronological halves of the signed set (descriptive, not a validation): mean sign*R0 +6.06% in the first 10 events, +2.25% in the last 10. The event study has no out-of-sample component; no Part A pattern is labelled `validated_out_of_sample`.

## 4. Findings in detail

### 4.1 Earnings (Part A, n = 7; extended n = 10)

| quarter | day 0 | R0 % | G0 % | I0 % | z0 | AR0 % | next-day abs(R)/sigma | D5 % | volume x | recovery | PAT QoQ % | PAT YoY % | revenue surprise % | EPS surprise % (vendor) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q4 FY24 (extended) | 2024-05-09 | -3.95 | -1.01 | -2.94 | -1.05 | -3.17 | 0.59 | +3.91 | 0.65 | 4 | n/a | n/a | n/a | n/a |
| Q1 FY25 (extended) | 2024-08-08 | +8.06 | +10.23 | -2.18 | +2.86 | +8.23 | 0.69 | +1.76 | 3.34 | >20 | +147.2 | n/a | -0.16 | n/a |
| Q2 FY25 | 2024-11-13 | -4.07 | +1.26 | -5.33 | -0.90 | -3.22 | 0.28 | +4.95 | 1.25 | 2 | +30.8 | +188.0 | +1.50 | n/a |
| Q3 FY25 (extended) | 2025-02-07 | +2.81 | -1.22 | +4.03 | +0.86 | +2.65 | 0.52 | -11.18 | 1.51 | 2 | -36.8 | +100.0 | +6.03 | n/a |
| Q4 FY25 | 2025-05-07 | +6.32 | +1.98 | +4.34 | +1.42 | +5.86 | 0.13 | +9.93 | 3.78 | >20 | +125.8 | +362.0 | +0.83 | n/a |
| Q1 FY26 | 2025-08-08 | -2.04 | +2.34 | -4.38 | -0.75 | -1.09 | 0.05 | +4.17 | 1.50 | 3 | +9.0 | +103.6 | -0.93 | +14.22 |
| Q2 FY26 | 2025-11-12 | +4.84 | +4.65 | +0.19 | +1.82 | +3.52 | 0.21 | +4.33 | 3.09 | 20 | +3.5 | +61.1 | +1.71 | +9.36 |
| Q3 FY26 | 2026-02-10 | +6.14 | +4.10 | +2.04 | +2.53 | +5.59 | 0.04 | -14.63 | 3.96 | 4 | +7.1 | +172.9 | +0.48 | +9.14 |
| Q4 FY26 | 2026-05-08 | -1.43 | +0.00 | -1.43 | -0.50 | -0.64 | 0.10 | +2.36 | 2.44 | 4 | +33.3 | +61.1 | -2.55 | +19.05 |
| Q1 FY27 | 2026-08-05 | -2.33 | +1.27 | -3.60 | -1.21 | -2.57 | 1.48 | -0.22 | 2.73 | >20 | +9.7 | +62.2 | -1.94 | +4.34 |

What the 7 results days show: abs(R0) averaged 3.9% (mean abs(z0) 1.30, CI 0.86-1.82); the gap carries 0.81 of the abs(z) and the intraday leg 1.01 (mean abs(zG0), abs(zI0)), i.e. the market kept repricing after the open; volume 2.5x the trailing 20-day mean (1.8x-3.3x). The *next* day is ordinary (mean abs(R1)/sigma 0.33). R0 was positive in 3/7 although PAT grew QoQ and YoY in 7/7 and the EPS beat in 5/5 vendor-comparable quarters: headline profit growth and EPS surprise do not identify direction.

**What cannot be concluded with n = 7.** (a) Any dependence of direction on PAT growth: the explanatory variable has no sign variation (all growth > 0) and its rank correlation with R0 is +0.16 (YoY) / 0.00 (QoQ), exact p 0.73 / 1.00; (b) any link between EPS surprise and R0 (n = 5, all surprises positive; exact two-sided p cannot go below 0.017 and is 0.95); (c) the 6/7 revenue-surprise sign agreement is p = 0.14 by exact permutation and 7/8 in the extended set (research/v2/01 reports Fisher p 0.14 on n = 8); a true 85% hit rate reaches p < 0.05 (which needs 7/7 hits) in only 32% of samples of 7; (d) magnitudes versus surprise size; (e) whether the Q1 FY27 -2.33%, -2.86% next day pattern generalises. Simulated power of the exact Spearman test: n=7 0.16/0.34/0.51/0.74/0.87 at rho 0.5/0.7/0.8/0.9/0.95 (80% power needs rho of about 0.92); n=5 0.04/0.08/0.14/0.23/0.38 (even rho 0.95 reaches only 38%).

**Consensus and the TradingView claim (verification).** TradingView's public page reports Q1 FY27 EPS 21.40 vs 20.31 estimate (+5.38%) and revenue 15.66B vs 15.97B. I did not fetch TradingView (terms of service). Checks: (i) 21.40 = PAT Rs 872.66 cr / 407.88 mn listed shares = 21.39: a vendor share-count basis, **not** the company-reported EPS of 21.22 (denominator 411.9 mn incl. shares held in abeyance) -> `verified_source` as a vendor figure, `unverifiable` as a company figure; (ii) 20.31 is **not reproduced** by any source I could read: Investing.com shows 20.51 (re-read today: EPS 21.40 vs 20.51, +4.34%; revenue 15.66B vs 15.97B, -1.94%), TradersUnion 20.45 (via research/v2/01, page 403), PL Capital 20.7 -> `unverifiable` as an exact consensus; (iii) the SIGN of the EPS surprise (beat) is vendor-robust and the revenue shortfall (-1.1% to -1.9%) is vendor-robust. I searched for a pre-results consensus (previews before 4 Aug) and found none. Consequence: only surprise signs and rank order are used (E1-E3); no magnitude-based claim. The Investing.com re-read is the same vendor page used by research/v2/01, so it reproduces rather than independently confirms their table.

### 4.2 Regulatory events: formal documents vs verbal/reported news

| form | events (day-0 R %) |
|---|---|
| formal_order | R01 -14.7; R06 -6.8 |
| formal_circular | R03 +2.4; R11 -7.6 |
| consultation_paper | R02 +5.8; R14 -2.2 |
| verbal | R07 -7.9; R13 +3.1; R16 +1.3 |
| media_report | R04 +15.7; R05 -1.2; R08 -4.7; R09 +8.7; R15 +3.9 |

Formal documents (n=6): mean abs(R0) 6.58%, mean abs(z0) 2.23. Verbal remarks and media reports (n=8): 5.79%, 2.06. Difference +0.17 z (CI [-1.07, 1.43]), permutation p 0.8093. The two largest moves in the whole table are a formal order (R01 SEBI fee order -14.7%) and a media report (R04 SEBI 'solution' +15.7%). Direction vs content: formal documents with a curb content (R01, R06, R11) all fell (-14.7, -6.8, -7.6); formal/consultation items with a 'less bad / relief' reading (R02 +5.8, R03 +2.4, R14 -2.2) went both ways; media/verbal items: curb stories fell (R07 -7.9, R08 -4.7), relief stories rose (R04 +15.7, R09 +8.7, R13 +3.1, R15 +3.9). The pattern is consistent with the market reacting to the *change relative to expectations*, which the content rule ignores by design; it is not a tested claim.

### 4.3 Selection and timing contamination (why the sign result is not trusted)

* The unscheduled set was assembled from dossiers whose authors searched for causes of large moves: mean abs(z0) 2.03 (n=18) vs 1.27 (n=9, date known in advance), difference +0.76 (CI [-0.04, 1.50], p 0.0952). Taking the scheduled subset and earnings as the selection-light estimates, the event premium over an ordinary session is about 1.3 / 0.75 = 1.7x, not 2.4x.
* For 14 of 20 signed events the first session was inferred from the dossier's reaction date; for 6 it comes from a timestamp or dated press item. Hit rates 12/14 vs 2/6 (Fisher exact p 0.0374; odds ratio 12). This diagnostic was added after seeing the first-run variant `A2a_timestamped_only` (mean sign*R0 +0.21%, n=6) and is post hoc. It does not prove contamination (the six documented events are mostly 2026 macro prints and CAS items in a falling market) but it removes any basis for using the sign rule as a directional predictor.
* Sign misses (6): R02 (+5.8% vs -1), R03 (+2.4% vs -1; 'milder than feared'), R14 (-2.2% vs +1), and the three hawkish macro prints M02/M03/M04 (+0.6%, +1.5%, +1.4% vs -1).

### 4.4 Follow-through, reversal and recovery

After signed events the next five sessions continued the day-0 direction by F = +0.16 sigma on average (CI [-0.94, 1.25], n=18); 50% continued. After *ordinary* large days (abs(z0) >= 1.5, n=214) the same quantity is +0.80 sigma (continuation 60%): ordinary big days show momentum in this sample (in-sample; the patterns workstream, research/v2/04, owns that question), event days do not, and the difference is not significant (p 0.4649). Mean 5-day return after positive events +0.24% (n=7), after negative events -1.03% (n=13), with standard deviations of several percent. Recovery: of 23 gated events with a defined window, 8 had not fully given back the day-0 move within the available window (up to 20 sessions); among negative signed events with complete windows 2 of 9 (22%) fully retraced within 5 sessions vs 30% of ordinary large-loss days (n=84), p 0.7359. Not given back within 20 sessions: R01 (-14.7%), R04 (+15.7%), R06 (-6.8%), R07 (-7.9%), R09 (+8.7%), R11 (-7.6%), R12 (-4.0%), X03 (-2.0%). Fully given back within 5 sessions: R02 (+5.8%, 3d), R03 (+2.4%, 2d), R05 (-1.2%, 2d), R10 (-2.3%, 4d), R13 (+3.1%, 3d), R17 (+3.9%, 4d), X02 (+2.0%, 1d), X05 (+3.3%, 1d), T01 (-8.1%, 2d), M02 (+0.6%, 2d), M03 (+1.5%, 2d).

## 5. Part B: structural change at the nine pre-specified dates

Design (docstring): adjacent 'clean' segments between neighbouring candidate dates (cap 120 sessions per side), six metrics per date, two independent permutation-type p-values per cell (5-session block permutation of the pooled windows; rank of the effect among the same-length windows at every other date of 2017-2026), claim p = max of the two, Holm/BH across the 54 claim p-values. Effects: post minus pre (vol and turnover as log ratios).

### 5.1 Segments (descriptive levels)

| date id | break session | pre window (n) | post window (n) | RMS R % pre -> post | beta pre -> post | corr Nifty pre -> post | median G % pre -> post | share G>0 pre -> post (Nifty post) | share G==0 pre -> post | geo-mean turnover Rs cr pre -> post |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 SEBI fee order | 2024-04-29 | 2023-10-31..2024-04-26 (120) | 2024-04-29..2024-09-30 (106) | 3.42 -> 3.77 | 1.00 -> 0.72 | 0.20 -> 0.19 | +0.45 -> +0.31 | 0.79 -> 0.73 (0.71) | 0.042 -> 0.028 | 223 -> 271 |
| B2 SEBI F&O measures | 2024-10-01 | 2024-04-29..2024-09-30 (106) | 2024-10-01..2024-11-28 (39) | 3.77 -> 3.90 | 0.72 -> 1.37 | 0.19 -> 0.30 | +0.31 -> +0.65 | 0.73 -> 0.82 (0.59) | 0.028 -> 0.000 | 271 -> 1515 |
| B3 first BSE-stock F&O row in data/raw/fo_bse | 2024-11-29 | 2024-10-01..2024-11-28 (39) | 2024-11-29..2025-05-22 (118) | 3.90 -> 3.97 | 1.37 -> 1.74 | 0.30 -> 0.42 | +0.65 -> +0.32 | 0.82 -> 0.69 (0.60) | 0.000 -> 0.034 | 1515 -> 1426 |
| B4 2:1 bonus ex-date | 2025-05-23 | 2024-11-29..2025-05-22 (118) | 2025-05-23..2025-08-29 (69) | 3.97 -> 2.81 | 1.74 -> 1.64 | 0.42 -> 0.34 | +0.32 -> +0.28 | 0.69 -> 0.80 (0.55) | 0.034 -> 0.043 | 1426 -> 1364 |
| B5 expiry-day swap | 2025-09-01 | 2025-05-23..2025-08-29 (69) | 2025-09-01..2026-01-30 (103) | 2.81 -> 2.30 | 1.64 -> 2.18 | 0.34 -> 0.48 | +0.28 -> +0.26 | 0.80 -> 0.69 (0.58) | 0.043 -> 0.078 | 1364 -> 1051 |
| B6 Budget STT (Sunday session) | 2026-02-01 | 2025-09-01..2026-01-30 (103) | 2026-02-01..2026-06-30 (100) | 2.30 -> 2.75 | 2.18 -> 1.51 | 0.48 -> 0.63 | +0.26 -> +0.25 | 0.69 -> 0.63 (0.47) | 0.078 -> 0.050 | 1051 -> 1417 |
| B7 RBI prop-funding curbs | 2026-07-01 | 2026-02-01..2026-06-30 (100) | 2026-07-01..2026-07-31 (23) | 2.75 -> 1.73 | 1.51 -> -0.12 | 0.63 -> -0.05 | +0.25 -> +0.11 | 0.63 -> 0.57 (0.57) | 0.050 -> 0.130 | 1417 -> 919 |
| B8 closing-auction regime | 2026-08-03 | 2026-07-01..2026-07-31 (23) | 2026-08-03..2026-09-29 (41) | 1.73 -> 2.17 | -0.12 -> 0.58 | -0.05 -> 0.15 | +0.11 -> +0.00 | 0.57 -> 0.46 (0.46) | 0.130 -> 0.195 | 919 -> 1466 |
| B9 first session as Nifty-50 member | 2026-09-30 | 2026-08-03..2026-09-29 (41) | 2026-09-30..2026-10-13 (9) | 2.17 -> 2.49 | 0.58 -> 0.94 | 0.15 -> 0.36 | +0.00 -> -0.03 | 0.46 -> 0.44 (0.50) | 0.195 -> 0.000 | 1466 -> 1658 |
| B7L RBI curbs, long windows: 120 sessions before vs 07-01..end | 2026-07-01 | 2026-01-01..2026-06-30 (120) | 2026-07-01..2026-10-13 (73) | 2.64 -> 2.09 | 1.57 -> 0.38 | 0.63 -> 0.12 | +0.25 -> +0.00 | 0.62 -> 0.49 (0.50) | 0.050 -> 0.151 | 1331 -> 1284 |
| B8L closing-auction regime, long windows: 250 sessions before vs 08-03..end | 2026-08-03 | 2025-07-25..2026-07-31 (250) | 2026-08-03..2026-10-13 (50) | 2.50 -> 2.23 | 1.51 -> 0.70 | 0.51 -> 0.20 | +0.22 -> +0.00 | 0.66 -> 0.46 (0.47) | 0.064 -> 0.160 | 1164 -> 1499 |

F&O listing: the first file in `data/raw/fo_bse` with a BSE-stock row is 2024-11-29 (469 files; the 8 files 2024-11-18..2024-11-28 are header-only). B7L/B8L rows are the post-hoc long-window cells (windows listed in the JSON).

### 5.2 The 54 primary tests (+12 post-hoc sensitivity cells)

| cell | n pre / post | effect (post - pre) | 95% bootstrap CI | p block | p placebo | claim p | Holm (54) | BH (54) | status |
|---|---|---|---|---|---|---|---|---|---|
| B1_vol | 120 / 106 | +0.098 ln ratio | [-0.367, +0.502] | 0.7527 | 0.7457 | 0.7527 | 1.0000 | 0.9770 | not_found |
| B1_beta | 120 / 106 | -0.277 beta | [-1.500, +0.547] | 0.5000 | 0.5035 | 0.5035 | 1.0000 | 0.9770 | not_found |
| B1_med_gap | 120 / 106 | -0.134 pp | [-0.27, +0.04] | 0.1434 | 0.3691 | 0.3691 | 1.0000 | 0.9770 | not_found |
| B1_pos_gap | 120 / 106 | -6.525 pp | [-18.52, +4.47] | 0.2730 | 0.5161 | 0.5161 | 1.0000 | 0.9770 | not_found |
| B1_zero_gap | 120 / 106 | -1.336 pp | [-7.39, +3.99] | 0.7683 | 0.6925 | 0.7683 | 1.0000 | 0.9770 | not_found |
| B1_turnover | 120 / 106 | +0.196 ln ratio | [-0.244, +0.671] | 0.2999 | 0.7732 | 0.7732 | 1.0000 | 0.9770 | not_found |
| B2_vol | 106 / 39 | +0.035 ln ratio | [-0.365, +0.504] | 0.8859 | 0.9388 | 0.9388 | 1.0000 | 0.9770 | not_found |
| B2_beta | 106 / 39 | +0.643 beta | [-0.661, +3.620] | 0.3230 | 0.2797 | 0.3230 | 1.0000 | 0.9770 | not_found |
| B2_med_gap | 106 / 39 | +0.339 pp | [+0.18, +0.64] | 0.0191 | 0.0423 | 0.0423 | 1.0000 | 0.8054 | not_found |
| B2_pos_gap | 106 / 39 | +9.410 pp | [-1.11, +19.94] | 0.2760 | 0.4744 | 0.4744 | 1.0000 | 0.9770 | not_found |
| B2_zero_gap | 106 / 39 | -2.830 pp | [-6.60, +0.00] | 0.6499 | 0.5567 | 0.6499 | 1.0000 | 0.9770 | not_found |
| B2_turnover | 106 / 39 | +1.723 ln ratio | [+1.243, +2.145] | <0.0001 | 0.0022 | 0.0022 | 0.1214 | 0.1214 | not_found |
| B3_vol | 39 / 118 | +0.016 ln ratio | [-0.266, +0.347] | 0.9235 | 0.9589 | 0.9589 | 1.0000 | 0.9770 | not_found |
| B3_beta | 39 / 118 | +0.376 beta | [-2.472, +1.720] | 0.6669 | 0.4507 | 0.6669 | 1.0000 | 0.9770 | not_found |
| B3_med_gap | 39 / 118 | -0.335 pp | [-0.71, -0.15] | 0.0542 | 0.0393 | 0.0542 | 1.0000 | 0.8054 | not_found |
| B3_pos_gap | 39 / 118 | -12.560 pp | [-23.60, -2.35] | 0.1553 | 0.2731 | 0.2731 | 1.0000 | 0.9770 | not_found |
| B3_zero_gap | 39 / 118 | +3.390 pp | [+0.85, +5.93] | 0.4705 | 0.3847 | 0.4705 | 1.0000 | 0.9770 | not_found |
| B3_turnover | 39 / 118 | -0.061 ln ratio | [-0.477, +0.325] | 0.7579 | 0.9159 | 0.9159 | 1.0000 | 0.9770 | not_found |
| B4_vol | 118 / 69 | -0.344 ln ratio | [-0.575, -0.106] | 0.0216 | 0.2814 | 0.2814 | 1.0000 | 0.9770 | not_found |
| B4_beta | 118 / 69 | -0.097 beta | [-1.052, +0.755] | 0.8841 | 0.8579 | 0.8841 | 1.0000 | 0.9770 | not_found |
| B4_med_gap | 118 / 69 | -0.034 pp | [-0.21, +0.26] | 0.8682 | 0.8341 | 0.8682 | 1.0000 | 0.9770 | not_found |
| B4_pos_gap | 118 / 69 | +10.219 pp | [-1.40, +22.69] | 0.1463 | 0.3483 | 0.3483 | 1.0000 | 0.9770 | not_found |
| B4_zero_gap | 118 / 69 | +0.958 pp | [-3.40, +5.55] | 0.8786 | 0.7961 | 0.8786 | 1.0000 | 0.9770 | not_found |
| B4_turnover | 118 / 69 | -0.045 ln ratio | [-0.417, +0.372] | 0.7952 | 0.9436 | 0.9436 | 1.0000 | 0.9770 | not_found |
| B5_vol | 69 / 103 | -0.200 ln ratio | [-0.395, +0.022] | 0.1511 | 0.5589 | 0.5589 | 1.0000 | 0.9770 | not_found |
| B5_beta | 69 / 103 | +0.531 beta | [-0.311, +1.454] | 0.3054 | 0.2640 | 0.3054 | 1.0000 | 0.9770 | not_found |
| B5_med_gap | 69 / 103 | -0.026 pp | [-0.28, +0.14] | 0.8629 | 0.8921 | 0.8921 | 1.0000 | 0.9770 | not_found |
| B5_pos_gap | 69 / 103 | -10.778 pp | [-22.91, +1.82] | 0.2255 | 0.3027 | 0.3027 | 1.0000 | 0.9770 | not_found |
| B5_zero_gap | 69 / 103 | +3.419 pp | [-2.90, +10.20] | 0.4444 | 0.3528 | 0.4444 | 1.0000 | 0.9770 | not_found |
| B5_turnover | 69 / 103 | -0.261 ln ratio | [-0.549, +0.018] | 0.0442 | 0.7228 | 0.7228 | 1.0000 | 0.9770 | not_found |
| B6_vol | 103 / 100 | +0.179 ln ratio | [-0.045, +0.378] | 0.2110 | 0.5822 | 0.5822 | 1.0000 | 0.9770 | not_found |
| B6_beta | 103 / 100 | -0.664 beta | [-1.264, -0.002] | 0.0752 | 0.1533 | 0.1533 | 1.0000 | 0.9770 | not_found |
| B6_med_gap | 103 / 100 | -0.013 pp | [-0.20, +0.19] | 0.9277 | 0.9321 | 0.9321 | 1.0000 | 0.9770 | not_found |
| B6_pos_gap | 103 / 100 | -5.932 pp | [-19.73, +6.95] | 0.3789 | 0.5499 | 0.5499 | 1.0000 | 0.9770 | not_found |
| B6_zero_gap | 103 / 100 | -2.767 pp | [-9.62, +3.17] | 0.4653 | 0.4377 | 0.4653 | 1.0000 | 0.9770 | not_found |
| B6_turnover | 103 / 100 | +0.299 ln ratio | [+0.138, +0.441] | 0.0008 | 0.7124 | 0.7124 | 1.0000 | 0.9770 | not_found |
| B7_vol | 100 / 23 | -0.462 ln ratio | [-0.699, -0.205] | 0.0609 | 0.2663 | 0.2663 | 1.0000 | 0.9770 | not_found |
| B7_beta | 100 / 23 | -1.635 beta | [-2.398, -0.581] | 0.0093 | 0.0597 | 0.0597 | 1.0000 | 0.8054 | not_found |
| B7_med_gap | 100 / 23 | -0.132 pp | [-0.31, +0.11] | 0.4560 | 0.5031 | 0.5031 | 1.0000 | 0.9770 | not_found |
| B7_pos_gap | 100 / 23 | -6.478 pp | [-25.87, +13.57] | 0.6361 | 0.6371 | 0.6371 | 1.0000 | 0.9770 | not_found |
| B7_zero_gap | 100 / 23 | +8.043 pp | [-3.65, +20.09] | 0.1929 | 0.0850 | 0.1929 | 1.0000 | 0.9770 | not_found |
| B7_turnover | 100 / 23 | -0.433 ln ratio | [-0.644, -0.208] | 0.0019 | 0.4728 | 0.4728 | 1.0000 | 0.9770 | not_found |
| B8_vol | 23 / 41 | +0.226 ln ratio | [+0.049, +0.444] | 0.0995 | 0.5755 | 0.5755 | 1.0000 | 0.9770 | not_found |
| B8_beta | 23 / 41 | +0.701 beta | [-0.626, +2.051] | 0.5192 | 0.3968 | 0.5192 | 1.0000 | 0.9770 | not_found |
| B8_med_gap | 23 / 41 | -0.114 pp | [-0.32, +0.08] | 0.4891 | 0.5815 | 0.5815 | 1.0000 | 0.9770 | not_found |
| B8_pos_gap | 23 / 41 | -10.180 pp | [-30.54, +9.65] | 0.4998 | 0.4380 | 0.4998 | 1.0000 | 0.9770 | not_found |
| B8_zero_gap | 23 / 41 | +6.469 pp | [-9.54, +22.48] | 0.6172 | 0.2021 | 0.6172 | 1.0000 | 0.9770 | not_found |
| B8_turnover | 23 / 41 | +0.467 ln ratio | [+0.247, +0.685] | 0.0144 | 0.3313 | 0.3313 | 1.0000 | 0.9770 | not_found |
| B9_vol | 41 / 9 (underpowered) | +0.135 ln ratio | [-0.248, +0.384] | 0.5074 | 0.7832 | 0.7832 | 1.0000 | 0.9770 | not_found (underpowered) |
| B9_beta | 41 / 9 (underpowered) | +0.362 beta | [-1.335, +2.697] | 0.8692 | 0.7072 | 0.8692 | 1.0000 | 0.9770 | not_found (underpowered) |
| B9_med_gap | 41 / 9 (underpowered) | -0.030 pp | [-0.30, +0.05] | 0.7101 | 0.9171 | 0.9171 | 1.0000 | 0.9770 | not_found (underpowered) |
| B9_pos_gap | 41 / 9 (underpowered) | -1.897 pp | [-22.76, +20.33] | 1.0000 | 0.9154 | 1.0000 | 1.0000 | 1.0000 | not_found (underpowered) |
| B9_zero_gap | 41 / 9 (underpowered) | -19.512 pp | [-34.15, -7.32] | 0.4677 | 0.0378 | 0.4677 | 1.0000 | 0.9770 | not_found (underpowered) |
| B9_turnover | 41 / 9 (underpowered) | +0.123 ln ratio | [-0.073, +0.328] | 0.5615 | 0.7716 | 0.7716 | 1.0000 | 0.9770 | not_found (underpowered) |
| B7L_vol (post-hoc) | 120 / 73 | -0.234 ln ratio | [-0.456, -0.002] | 0.1261 | 0.4872 | 0.4872 | 1.0000 | 0.6496 | not_found |
| B7L_beta (post-hoc) | 120 / 73 | -1.189 beta | [-2.042, -0.288] | 0.0037 | 0.0224 | 0.0224 | 0.2466 | 0.1345 | not_found |
| B7L_med_gap (post-hoc) | 120 / 73 | -0.246 pp | [-0.33, -0.02] | 0.0437 | 0.0801 | 0.0801 | 0.6404 | 0.1921 | not_found |
| B7L_pos_gap (post-hoc) | 120 / 73 | -13.185 pp | [-25.33, -0.80] | 0.0780 | 0.1995 | 0.1995 | 1.0000 | 0.2992 | not_found |
| B7L_zero_gap (post-hoc) | 120 / 73 | +10.068 pp | [-0.35, +21.56] | 0.0157 | 0.0037 | 0.0157 | 0.1884 | 0.1345 | not_found |
| B7L_turnover (post-hoc) | 120 / 73 | -0.036 ln ratio | [-0.265, +0.163] | 0.7230 | 0.9529 | 0.9529 | 1.0000 | 0.9529 | not_found |
| B8L_vol (post-hoc) | 250 / 50 | -0.112 ln ratio | [-0.286, +0.062] | 0.4305 | 0.7667 | 0.7667 | 1.0000 | 0.8364 | not_found |
| B8L_beta (post-hoc) | 250 / 50 | -0.814 beta | [-1.945, +0.373] | 0.1097 | 0.1510 | 0.1510 | 1.0000 | 0.2861 | not_found |
| B8L_med_gap (post-hoc) | 250 / 50 | -0.224 pp | [-0.30, -0.10] | 0.0389 | 0.1669 | 0.1669 | 1.0000 | 0.2861 | not_found |
| B8L_pos_gap (post-hoc) | 250 / 50 | -20.400 pp | [-32.41, -9.59] | 0.0139 | 0.0491 | 0.0491 | 0.4906 | 0.1878 | not_found |
| B8L_zero_gap (post-hoc) | 250 / 50 | +9.600 pp | [-0.40, +22.80] | 0.0626 | 0.0188 | 0.0626 | 0.5634 | 0.1878 | not_found |
| B8L_turnover (post-hoc) | 250 / 50 | +0.253 ln ratio | [+0.090, +0.411] | 0.0233 | 0.6898 | 0.6898 | 1.0000 | 0.8277 | not_found |

Holm/BH for the sensitivity cells are taken within the 12; across the full 88-test registry no Part B cell reaches Holm < 0.05 (smallest 0.19). The whole-registry BH value of B2_turnover is 0.033 because the registry also contains the tiny Part A p-values; that figure borrows strength from a different family and is not used as the Part B claim (family BH-54 = 0.121). Within the nine turnover tests alone Holm = 0.020.

### 5.3 Calibration of the test procedure (simulated data, `--selftest`)

GARCH(1,1) null (alpha 0.08, beta 0.90), N = 1,500, 100/100 windows, 120 replications: size of the 5% test for a volatility break: block permutation alone **0.39**, placebo-date rank **0.05**, max rule **0.05**. Power against a x1.6 volatility step: block 0.79, placebo 0.35, max rule 0.35. So the pre-specified max rule controls size but has modest power against moderate shifts with 100-session windows; for 20-40 session windows the power is lower still. 'Not found' below means 'not detectable with these windows', not 'no change'.

### 5.4 What the tests say, date by date (effects with 95% CIs; every cell failed family control)

* **Volatility level.** ln(RMS ratio): B1 +0.10 [-0.37, +0.50], B2 +0.04 [-0.37, +0.50], B3 +0.02 [-0.27, +0.35], B4 -0.34 [-0.58, -0.11] (3.97% -> 2.81%; block p 0.0216 but placebo p 0.2814), B5 -0.20 [-0.40, +0.02], B6 +0.18 [-0.04, +0.38], B7 -0.46 [-0.70, -0.21] (2.75% -> 1.73% over 23 sessions; block p 0.0609, placebo p 0.2663), B8 +0.23 [+0.05, +0.44]. The daily RMS of R fell from 3.4-4.0% (Oct 2023-May 2025) to 2.3-2.8% (May 2025-Jun 2026) and 1.7-2.5% since July 2026, but no single candidate date carries the step: the decline is gradual and the placebo ranks (0.27-0.96) say shifts of this size occur at other dates too.
* **Beta to Nifty 50.** Segment betas in date order: B1 1.00 -> 0.72, B2 0.72 -> 1.37, B3 1.37 -> 1.74, B4 1.74 -> 1.64, B5 1.64 -> 2.18, B6 2.18 -> 1.51, B7 1.51 -> -0.12, B8 -0.12 -> 0.58, B9 0.58 -> 0.94; segment correlations range from -0.05 to 0.63. B7 -1.64 [-2.40, -0.58] (claim p 0.0597) and long-window B7L -1.19 (claim p 0.0224, Holm-12 0.2466) are the nearest to a detectable change: the stock's co-movement with the index fell after 1 July (post-window corr 0.12 from 1 Jul, 0.20 from 3 Aug, vs 0.63 in H1 2026). Part of the pre-2026-08-03 relationship is timing mismatch (VWAP close vs index close), so the change at B8 is confounded by a measurement change.
* **Gap distribution.** Median G: B2 +0.34 [+0.18, +0.64] pp (claim p 0.0423), B3 -0.34 [-0.71, -0.15] pp; share G>0: B8 -10.2 [-30.5, +9.7] pp, B8L -20.4 pp; share G==0: B8 +6.5 [-9.5, +22.5] pp, B8L +9.6 pp. See 5.5.
* **Turnover.** B2 +1.72 [+1.24, +2.15] ln units (x5.6; geo-mean Rs 271 cr -> Rs 1,515 cr/day between Apr-Sep 2024 and Oct-Nov 2024; claim p 0.0022, Holm-54 0.1214). B6 +0.30 [+0.14, +0.44] (block p 0.0008, placebo p 0.7124); B7 -0.43 [-0.64, -0.21]; B8 +0.47 [+0.25, +0.69]. Rupee turnover is free of the bonus mechanics (B4: -0.04 [-0.42, +0.37]) but moves with price level and market cap, so the 2024 step cannot be attributed to the SEBI measures.
* **B9 (Nifty 50 membership, 9-10 sessions)** is underpowered for every metric (post n = 9): vol +0.14 ln, beta +0.36, zero-gap share -19.5 pp (placebo p 0.038, block p 0.47, claim p 0.47). Nothing can be said about membership effects yet.

### 5.5 The gap regime (the 'closing-auction break')

| month | n | BSE median G % | BSE share G>0 | Nifty share G>0 | BSE share G==0 | mean R % |
|---|---|---|---|---|---|---|
| 2025-07 | 23 | +0.206 | 0.78 | 0.56 | 0.043 | -0.57 |
| 2025-08 | 19 | +0.144 | 0.84 | 0.37 | 0.000 | -0.77 |
| 2025-09 | 22 | +0.433 | 0.82 | 0.73 | 0.045 | -0.12 |
| 2025-10 | 20 | +0.216 | 0.80 | 0.60 | 0.050 | +0.97 |
| 2025-11 | 19 | +0.263 | 0.58 | 0.63 | 0.053 | +0.83 |
| 2025-12 | 22 | +0.067 | 0.64 | 0.46 | 0.182 | -0.44 |
| 2026-01 | 20 | +0.226 | 0.60 | 0.50 | 0.050 | +0.30 |
| 2026-02 | 21 | +0.213 | 0.62 | 0.48 | 0.000 | -0.16 |
| 2026-03 | 19 | +0.000 | 0.47 | 0.37 | 0.053 | -0.05 |
| 2026-04 | 20 | +0.246 | 0.60 | 0.50 | 0.100 | +1.52 |
| 2026-05 | 19 | +0.312 | 0.74 | 0.47 | 0.105 | +0.68 |
| 2026-06 | 21 | +0.392 | 0.71 | 0.52 | 0.000 | -0.33 |
| 2026-07 | 23 | +0.114 | 0.56 | 0.56 | 0.130 | -0.25 |
| 2026-08 | 21 | +0.000 | 0.43 | 0.52 | 0.286 | -0.50 |
| 2026-09 | 21 | +0.000 | 0.48 | 0.38 | 0.095 | -0.28 |
| 2026-10 | 8 | +0.012 | 0.50 | 0.57 | 0.000 | +1.10 |

Facts: (i) from 2025-07 to 2026-06 BSE's share of positive gaps exceeded the Nifty's in 11 of 12 months (mean excess about +15 pp over the 250 sessions to 31 Jul 2026; monthly median G between 0.00% and +0.43%, at least +0.2% in 9 of 12 months); (ii) the excess was 0 pp in July 2026 (23 sessions: BSE 0.565, Nifty 0.565) and -2.0 pp over 3 Aug-13 Oct (0.46 vs 0.47); (iii) the BSE median gap is exactly 0.000 in August and September and +0.012% in October; (iv) exact-zero gaps: 8 of 50 sessions since 3 Aug (16%) vs 5.0% over 2017-2026-08-02, but 13% in July 2026 (3/23), 18% in Dec 2025 and 10% in April-May 2026, so a 16% share is inside the range seen before the auction regime; (v) the three zero-gap sessions with intraday data (31 Aug, 16 Sep, 18 Sep) have an official open equal to the previous close while the first continuous trade was Rs -7.6, -8.5, +4.5 away; I cannot tell whether the zero-gap pre-open price is a thin-book default or a data convention (`not_found`). **Interpretation limits:** the sign of the change is clear in the point estimates (B8L: -20.4 pp, CI -32.4 to -9.6 on the bootstrap) but it does not survive correction (claim p 0.049 raw, Holm-12 0.49), the window since 3 Aug is also a drawdown (mean R -0.15%/day vs +0.14%), and July 2026 already looked like the post-regime. v1's attribution of the change to the closing-auction price (DEVIATIONS #16) is therefore *consistent* with the data but not *identified* by it; the RBI curbs (1 Jul) and the market drawdown are equally compatible. For 14 Oct the practical conclusion is the same as v1's: do not assume a positive median gap.

## 6. Business, ownership, leverage and market-structure changes (association, not cause)

From research/01 (dossier) with its confidence tags; none of this was tested as a cause.

| change | dated facts | what the data show around it (association only) |
|---|---|---|
| Leverage | No borrowings (lease liability Rs 2 lakh); core settlement guarantee funds Rs 1,232.64 cr (B-1, B-3, CONFIRMED primary) | No leverage channel exists to explain volatility or beta shifts; operating leverage to F&O volume is the relevant one (transaction charges 84.8% of Q1 FY27 operating revenue) |
| Foreign ownership | FPI 16.3% (Sep-25) -> 17.5% (Dec-25) -> 19.42% (Mar-26) -> 21.32% (Jun-26); institutions 29.41% (Jun-25) -> 45.55% (Jun-26); MF 12.52% -> 11.69% (G-1, CONFIRMED via aggregators) | Calendar-quarter table (n=4): RMS R 2.66, 2.43, 2.90, 2.35%; beta 1.63, 2.39, 1.69, 1.39; corr with Nifty 0.31, 0.48, 0.66, 0.57; geo turnover Rs 1,020, 1,141, 1,203, 1,472 cr. Pearson with FPI share: RMS -0.23, beta -0.52, corr(Nifty) +0.79, turnover +0.97. Four points: no inference; turnover and FPI share both trend upward with price/market cap |
| Nifty 50 membership | Replaced Wipro after the close of 29 Sep 2026; announced ~10 Aug (single-source); six-month free-float cap Rs 1,40,879 cr; passive-flow estimates US$639-741 mn; Goldman/BNP sold 68.33 lakh shares (1.67%) on 29 Sep | 29 Sep +3.26% on 6.8x volume, 30 Sep -3.4%, 1 Oct -1.5% (a reversal that fits 'sell the news' but is n=1); post-membership beta 0.94 / corr 0.36 on 8 pairs: not interpretable |
| Market structure | 29 Nov 2024 BSE-stock F&O listing; 23 May 2025 2:1 bonus (share count x3, face value unchanged); 1 Sep 2025 expiry swap; Budget STT 1 Feb 2026 (effective 1 Apr); RBI curbs 1 Jul 2026; CAS 3 Aug 2026; NSE listing 24 Sep 2026 | Part B: no break detectable family-wise; the only large effect is the turnover step at 2024-10-01 |
| Fee/regulatory regime | SEBI fee order 29 Apr 2024 (-14.7%); SEBI measures 1 Oct 2024; true-to-label charges 1 Oct 2024 | B1: RMS R 3.42% -> 3.77%, CI of the log ratio -0.37 to +0.50: not distinguishable |

## 7. Effect on the 14 Oct forecast

* **Centre: no change.** No signed rule is usable (4.3); the gap median is not assumed positive (5.5); earnings are not in play (Q2 board meeting 4 Nov; trading window closed 1 Oct to 6 Nov).
* **Scale: conditional widening only.** A regulatory catalyst is the one unscheduled event with a live date (SEBI chairman on 10 Oct: guidelines 'in about a week'; Reuters: by end-October). The listed unscheduled events had mean z0^2 = 5.32 (RMS abs(z) 2.31; selection-biased upward) vs 1.15 for ordinary sessions. A mixture with event probability p multiplies the daily sigma by m(p) = sqrt(1 + p*(Zev^2/Zpool^2 - 1)): p = 0.030 (historical frequency of listed unscheduled events: 18 in 608 sessions): m = 1.053; p = 0.15: m = 1.244; p = 0.30: m = 1.447. v1's sigma (2.478%) rests on standardised residuals from a history that already contains these event days at roughly the base rate (about 3% of sessions), so only the excess over that base rate is new information; it therefore needs a widening factor of about 1.18 at p = 0.15 and 1.37 at p = 0.30 *if* one believes the probability of a catalyst inside the session is that high. History cannot supply p for a specific date; p = 0.15-0.30 is an assumption, not an estimate.
* **If the catalyst lands:** unscheduled regulatory events (n=14) had abs(z0) quartiles 1.27 / 2.02 / 2.96; at the current 60-session RMS of 2.153% that is about 2.7% / 4.3% / 6.4% (Rs 92 / 147 / 215 from P0), with no reliable sign: the one formal-consultation 'relief' item before 14 Oct (R14, 15 Sep) fell 2.2% and the leak-type item (R15) rose 3.9%. The 5-6 Oct rise (+4.39%, +3.94%) is only partly in these statistics (6 Oct is R15; 5 Oct has no identified cause and is not an event), so the market has already traded part of a favourable outcome; the table cannot say how much.

## 8. Relationships likely invalid on 14 Oct (and why)

| relationship | why it likely does not carry over | evidence |
|---|---|---|
| Positive gap premium (median G +0.2% to +0.4%, ~66% positive) | Closing price is an auction price since 3 Aug (before: 30-minute VWAP); BSE's excess over the Nifty's positive-gap share disappeared by July 2026; median gap 0.000% Aug-Sep | monthly table 5.5; B8L -20.4 pp (CI -32 to -10), uncorrected p 0.049 |
| Beta to Nifty 1.4-1.6 (250-day) and corr 0.5-0.65 | Pre-2026-08-03 co-movement is measured with a VWAP close against a 15:30 index close; segment betas range from -0.12 to 2.18 with bootstrap CIs of the changes up to 4 units wide; post-3-Aug corr 0.20 (0.12 since 1 Jul) | segment table 5.1; B7L beta -1.19 (CI -2.04 to -0.29) |
| Volatility level from before mid-2025 (3.4-4.0% daily) and the 2024-25 regime | RMS R is 2.15% over the last 60 sessions, 2.23% since 3 Aug; the level re-scaled across 2025 | 5.1 and B4/B5 CIs (the change is gradual, not dated) |
| Absolute rupee turnover before Oct 2024 (Rs ~270 cr/day geo-mean) | A x5.6 step at 2024-10-01 (price level, F&O listing 29 Nov 2024 and the stock's re-rating); relative-volume measures against a trailing 20-day mean remain usable | B2_turnover |
| Event reaction sizes from the dossier set (abs(z) 2.0 unscheduled) | Selection towards large moves; the selection-light estimate is about 1.3; sign rule fails on expectations and is not robust to timing evidence | 4.3 |
| Results-day reactions and post-results drift | No earnings release before 4 Nov; trading window closed 1 Oct-6 Nov; n=7 | 4.1 |
| Index-inclusion demand | Completed on 29 Sep (6.8x volume, then -3.4%/-1.5%); the 2026-10-06/07 recovery is not an inclusion effect | X05 |
| 'Weekly expiry' seasonality | 14 Oct is a non-expiry Wednesday (Nifty expired 13 Oct; Sensex expires Thu 15 Oct) | dossier 02 s(c) |

## 9. Post-first-run changes (full disclosure)

1. **Bug fix A4.** The pre-registered A4 statistic is mean(s*R0 given s=+1) - mean(s*R0 given s=-1); the first run coded the sum of the two means (0.0895, raw p 0.0030, Holm 0.051), visible because the estimate lay outside its own bootstrap CI. Corrected value: +0.0213, raw p 0.058, Holm 0.81. The first-run number is a wrong statistic and is not a finding.
2. **Post-hoc sensitivity cells B7L and B8L** (12 tests): added because the clean windows of B7/B8 have 23 sessions on one side. Counted in the 88-test registry. B7L's post window contains B8 and B9.
3. **Post-hoc diagnostic** A2c by timing evidence (Fisher exact), counted as a variant run.
4. **Post-hoc descriptive additions**: Nifty gap columns, monthly gap table, zero-gap/first-bar comparison.
5. First-run facts that were seen before 1-4: A1 and A8 highly significant; A2a Holm 0.028 with a null timestamped subsample; no Part B cell below Holm 0.12.

## 10. Contrary evidence and what would reverse each conclusion

| conclusion | contrary evidence | would reverse if |
|---|---|---|
| Events are larger than ordinary sessions | Scheduled-event excess is only p 0.039 raw and not significant after Holm; mean abs(z) is 1.3 not 1.8 once selection is removed | A systematic list of ALL SEBI/RBI/exchange dated items (including those with small moves) gives mean abs(z0) near 0.75 |
| Sign rule not usable | 14 of 20 hits overall; 12 of 14 for dossier-dated events | More documented-time events show hit rate > 70% (power: 6 events cannot tell) |
| No asymmetry | positive events averaged +5.5% vs -3.4% for negative (n=7 vs 13); p 0.058 raw for the direction-adjusted difference | The 7 positive events are 3 media reports (R04 +15.7%, R09 +8.7%, R15 +3.9%), 1 verbal remark, 1 consultation paper, 1 index announcement and 1 macro item: more positives with formal content would settle it |
| No follow-through/reversal difference | ordinary large days show +0.80 sigma continuation (p ~ 0), events +0.16 | an event sample free of overlap (only 9 uncontaminated) |
| No break detectable | B2 turnover x5.6; B7L beta -1.2; B8L positive-gap share -20 pp | A longer post-regime sample (>100 sessions after 3 Aug) with the same estimates would clear Holm; power for 1.6x vol steps with 100-session windows is only 35% |
| Gap premium no longer valid | July-2026 evidence is 23 sessions; Oct 8 sessions show 0.5 positive share | Positive-gap share back above the Nifty's by > 10 pp over the next 60 sessions |

## 11. Gaps and failed attempts

* Primary sources for the regulatory events (SEBI orders/circular texts, RBI directions beyond the press release, NSE Indices announcement) were not opened by me; event existence and dates rest on dossiers 01/02 and research/v2/01-02 (many `SINGLE-SOURCE` or snippet-only). 14 of 20 signed events have dossier-inferred day-0.
* Release times: R01 (29 Apr 2024), R05, R07, R08, R09, R10, R12, T01 are 'intraday' by inference; the pre-release part of day 0 cannot be separated, so G0/I0 for these rows are not a clean news response.
* Consensus: only vendor tables (Investing.com; TradersUnion 403 per research/v2/01); TradingView's 20.31 estimate unreproduced; no pre-results consensus found by WebSearch. Surprise *magnitudes* unusable.
* Governance: only 3 dated management events (2022 CEO transition), two with unknown release time; nothing in 2024-2026. No claim possible.
* Macro: only 4 named-date items from the dossier; no systematic RBI/Fed/CPI calendar was available in the repo, so no dates were added. Budget days other than 2026-02-01 are not in the dossiers and were not added (n=1 for tax_budget).
* September-quarter shareholding pattern (due 21 Oct) not yet available; FPI share series is aggregator-sourced.
* Index data end 2026-10-12 (no Nifty row for 13 Oct): M04 has no AR and the last Part B session has no beta pair.
* The 14-Oct session is unseen; nothing after the cutoff was used.

## 12. Registry summary

Part A 22 tests; Part B 54 primary + 12 post-hoc; total 88. Raw p < 0.05: Part A 8; Part B primary claim p 2 (block-only 8, placebo-only 4). Whole-registry Holm < 0.05: A1_NE, A1_NE_unsched, A8_NE, A8_EARN7. Whole-registry BH < 0.05: A1_NE, A1_NE_unsched, A2a, A8_NE, A8_EARN7, B2_turnover.

