# H. Peer-move column: pre-registered FORWARD test

Written Wed 21 Oct 2026 (evening), before any forward data exists.  Nothing in this file may be edited after the first forward reading (Thu 22 Oct 2026); later changes go into `docs/DEVIATIONS.md` with a date.

## 0. What is fixed here (read this section first)

**Question.**  At a reading during the day, BSE has moved some percentage since the previous close and its capital-market peers have moved some other percentage.  Does the *difference* tell us anything about how far BSE still moves from now to the official close, beyond what the pin-point (the price now) already gives?

**Why this is being asked.**  On Wed 21 Oct every close reading sat above the official close (BSE closed -2.63%).  Yahoo daily figures (unofficial) show the peers fell about as much as BSE and more than the market: Nifty -0.34%, Bank Nifty -0.92%, CDSL -2.58%, Angel One -3.20%, MCX -3.06%, 360 ONE -1.61%.  That is the only thing looked at before this registration; **no intraday peer-versus-BSE relationship was examined.**  21 Oct is excluded from the test sample.  The direction of the hypothesis below (catch-up) was chosen after seeing that one session, which is a weakness (section 9).

**Nothing about the forecasts changes.**  The column is context.  The pin-point stays the price now.  The test decides only whether the column is later promoted from "context" to "a documented lead" (and a lead would need its own registration before it touched a forecast).

### 0.1 Definitions (frozen)

* **Reading**: one live row logged by `src/hourly_table.py` into `results/hourly_table_log.jsonl` (field `peers` added from Thu 22 Oct).  Replays (`--asof`) are never readings.
* **Baskets** (symbols as on NSE; Yahoo symbol = NSE symbol + `.NS`):
  * **P (primary)**: CDSL, MCX, MOTILALOFS, IEX.  This is the `PEERS` tuple of `src/hl_analog.py` (study G), written before this registration.
  * **S (secondary)**: ANGELONE, CDSL, MCX: the peers named in the invalidation conditions of the 14 Oct forecast records (`src/finalize_record.py`).
  * Logged for context and never tested: Nifty 50 (`^NSEI`), Bank Nifty (`^NSEBANK`).
* **Peer move** m_i = ln(price_i / previous close_i): price_i = close of the last Yahoo 1-minute bar that started before the reading's minute (the same rule as BSE's own price); previous close_i = Yahoo `chartPreviousClose` of the same request.  A peer is dropped at a reading if it has no bar, its last bar is more than 10 minutes older than the reading, or |m_i| > 15% (a corporate action or a bad print: the same rule as study G).
* **Basket move** M = equal-weight mean of the available m_i; valid only if at least 3 of 4 (P) or 2 of 3 (S) peers are available.
* **BSE move** b = ln(price now / official previous close), price now = the table's own `price_now`.
* **Gap** G = M - b, in percentage points (x100).  G > 0 means the peers are doing better than BSE (or falling less).
* **Outcome** R = 100 x ln(official close / price now), the move still to come.  Official close = NSE bhavcopy close in `data/processed/bse_daily_extra.csv` (about 16:35 IST).
* **Primary reading of a session**: the first live reading with time at or after 11:00 and before 13:00 IST.
* **Eligible session**: a primary reading exists with a valid basket P, the official close is in the repository, and the session is a normal one (the Sun 8 Nov 2026 Muhurat evening session and any other special session are excluded).

### 0.2 Hypotheses (one-sided; Holm across the two)

* **H1 (primary)**: the slope of R on G is **positive** (catch-up: when the peers are doing worse than BSE, BSE tends to fall further; when better, to rise), basket P, primary readings.
* **H2 (secondary)**: the same with basket S.

A significantly **negative** slope would be recorded as a reverse-sign lead.  It would not count as adoption and would need a new registration.

### 0.3 Statistic and sample

* Statistic: OLS slope of R on G with an intercept, one primary reading per eligible session.
* p-value: one-sided permutation test (G permuted across sessions, 20,000 permutations, numpy seed 20261022); Holm adjustment over H1 and H2.
* Sample: sessions from Thu 22 Oct 2026 onward.  **First analysis when 60 eligible sessions exist** (about three months); if not adopted, **one more at 120**.  No other looks.
* **Locked reporting**: before the first analysis the report prints counts and data-quality facts only.  No slope, correlation, p-value or plot of R on G is computed on forward data.

### 0.4 Adoption rule (all three at an analysis point)

1. Slope > 0 for H1 and the Holm-adjusted p < 0.05.
2. **Out of sample**: fit the slope on the first 30 eligible sessions and then on an expanding window, each later session being predicted from the slope fitted on the sessions before it; the shifted pin-point is price now x exp(slope x G / 100).  Its mean absolute error to the official close must be at least **3% lower** than "price stays" over sessions 31..n.
3. The slope has the same sign in the first and the second half of the eligible sessions.

If adopted, the column is promoted to a "documented lead" in `docs/LIVE_TOOLS.md` and the dashboard evidence; shifting any pin-point would be a separate, separately registered step.

### 0.5 Descriptive items that are allowed (never tested, never used to adopt)

Counts of readings and eligible sessions; share of peers missing; how often a peer is dropped; the table of the logged peer and index moves by reading time.  After the first analysis, plain tables of G and R by reading time.

## 1. How much can this test show?  (rough power, simulated, assumptions not measured)

Remaining-move sd 1.35 pp (from the width of the model's own close ranges at 11:00-13:00); G sd 0.5 or 1.0 pp (not measured: there is no intraday peer history in the project); normal errors; one-sided t-test at 5% (the permutation test behaves alike; the Holm step makes it slightly weaker).

| true slope | G sd | power at 60 sessions | power at 120 sessions |
|---|---|---|---|
| 0.2 | 0.5 | 15% | 21% |
| 0.2 | 1.0 | 31% | 50% |
| 0.4 | 0.5 | 30% | 49% |
| 0.4 | 1.0 | 76% | 94% |
| 0.6 | 0.5 | 54% | 79% |
| 0.6 | 1.0 | 98% | 100% |

So with a small true slope or a quiet G the likely outcome is "not demonstrated", which must be read as "this test could not see it", never as "there is no relationship".

## 2. Data, code, hashes

* Data: `results/hourly_table_log.jsonl` (field `peers`: per symbol previous close, price used, bar time, move; basket moves; gap; index moves), `data/processed/bse_daily*.csv`.
* Code: `src/peers_live.py` (fetch and gap), `src/peer_forward.py` (dataset, locked report, analysis, self-test on synthetic data).  The analysis code is tested on synthetic data before it is allowed to run on forward data.
* The column in the table is the eighth and last column; the seven columns of the fixed format are unchanged.  Rows logged before 22 Oct and every replay print seven columns exactly as before.

## 3. Known weaknesses (stated now)

1. Yahoo is unofficial and the peers are thin: a stale last bar is possible (the 10-minute rule drops those).
2. The catch-up direction was chosen after one session.
3. One independent observation per day: about 60 sessions is a small sample, and regimes change (the closing auction began 3 Aug 2026).
4. A sector-wide news day moves BSE and peers together: G is then near zero and says nothing; the test cannot tell news from catch-up.
5. The pin-point already moves with the price, so any gain has to come on top of "price stays", the hardest benchmark.
6. Earlier daily-frequency studies (D, E, G) found no demonstrated gain from peers; this is a different horizon (intraday remaining move), not a re-run.
