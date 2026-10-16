# Live close estimate and daily scoreboard (how to use)

Both tools are exploratory aids. They do not claim to predict direction or make money; the scoreboard exists to find out, on paper, over many sessions.

## Live close estimate (`src/live_nowcast.py`)
* `python3 src/live_nowcast.py` — fetches today's Yahoo 1-minute bars (unofficial, near-real-time), prints in plain words: price now, indicative close, 50% and 90% ranges, typical miss, and how the range will shrink if the price stays put. Logs the call to `results/nowcast_log.jsonl`.
* `--asof HH:MM` replays today as of that time; `--replay` prints the table used on the dashboard; `--backtest` runs the leave-one-session-out calibration; `--refresh` adds newly completed sessions to `data/processed/intraday_extra_15m.csv`.
* Method: centre = last traded price; spread = how much the stock usually moves from that time of day to the official (closing-auction) close, measured on ~39 sessions of 15-minute bars since the closing auction began. Today's volatility so far did not improve the leave-one-out test and is not used.
* Honest limits: small sample (39 sessions, overlapping checkpoints; 90% coverage could be 83-96%); the printed 50% range covers 50% overall but is too narrow in the morning; a late news spike breaks it (on 15 Oct the 12:30 and 13:15 calls ended outside the 90% range before the 13:30 jump); in this sample price rose about 0.2% from 15:00 to the close on average (not used). Independent review: research/live_verify_nowcast.md.

## Daily scoreboard (`src/scoreboard.py`)
* `issue` — run after the US close (~01:30 IST) and before 09:15 IST. Writes `results/scoreboard/entries/<date>.json` (never rewritten) with the open and close ranges, a direction lean (US S&P 500 last night + BSE's last two days), and two paper-trade rules: PT1 every day, PT2 only the strongest 20% of leans (open to close, 0.10% round-trip cost). **Commit the entry before 09:15 IST: the commit time is the proof.** Use `--dry` to preview.
* `score` — after the official NSE bhavcopy (~16:34 IST): outcomes, running totals, and comparison with "unchanged".
* `report` — running totals in plain words. 30 sessions cannot separate 55% from 50% (that takes several hundred): use it to catch gross failures and build evidence. `issue` refuses weekends, stale data (a missing weekday: pass `--force-gap` only for a known holiday) and anything after 09:00 IST on the target day (`--late` records a late entry). Independent review: research/live_verify_scoreboard.md.
* `src/official_bars.py` downloads missing official bars into `data/processed/bse_daily_extra.csv`. It assumes no corporate action: check `data/corp_actions_verified.csv` across any ex-date.

## Opening price from NSE's pre-open auction (`src/preopen.py`)
* `python3 src/preopen.py` reads NSE's pre-open call-auction data for BSE: the indicative opening price (IEP), orders waiting to buy and sell, and the book near the price. The IEP can still change from 09:00 to 09:08; from 09:08 it is final and NSE uses it as the official open. Snapshots are saved to `results/preopen/`.
* On 15 Oct the 09:09 pre-open price was Rs 3,342.0 and the official open was Rs 3,342.0 (miss Rs 0.0; one session, but the mechanism is that the auction sets the open). The endpoint is an unofficial public API and may change; it needs the cookie warm-up the script does.
* This gives the open to within a tick from about 09:08-09:09. It is not a forecast, and it says nothing by itself about the direction of the rest of the day.

## Intraday study at 10:15 (`src/intraday_study.py`, exploratory)
Two years of hourly bars (486 sessions; 336 walk-forward observations). Nothing known at 10:15 (first-hour return, gap, Nifty and peers' first hour, BSE minus Nifty, all together) improved the estimate of the close beyond 'price stays': out-of-sample R2 -0.2% to -4.8%, typical miss about Rs 40 either way. Trade rules at 10:15 that looked good in the first 60% of the sample (follow the first-hour move: +0.8% per trade, t 3.3) were about zero in the last 40%. Hourly volume is unavailable (zero on most sessions).


## Hour-by-hour table (`src/hourly_table.py`): the user's fixed format
One row per time frame: time | precise close | close range at the end of the day | precise high of the next hour | precise low of the next hour | this hour's high vs the previous prediction | this hour's low vs the previous prediction. At 08:30 and 09:00 (before the open) `--pre-open` gives the open range and the open pin-point.
* `python3 src/hourly_table.py` — the row for now (Yahoo 1-minute bars, unofficial). Logs the predictions to `results/hourly_table_log.jsonl`. The 'this hour' columns compare ONLY the previous table given to the user (the latest live row logged before this one) with what happened in that table's own window ('so far only' while that hour is not over); with no earlier table the cell says so (no replay, no recomputed prediction). Separately every logged live prediction is scored once its own window is over (`--score`, `results/hourly_table_scored.csv`: the learning dataset; `--report` prints running accuracy). `--asof HH:MM` replays today for testing; `--eval` runs the leave-one-session-out test of the next-hour model (`results/hourly_hl_eval.csv`).
* Close pin-point = the price now (no drift); range = the live close estimate (`src/live_nowcast.py`).
* Next-hour high/low pin-point = the median of: P x exp(z x sigma_window), P = price now, sigma_window = the profile variance of the next 60 minutes (cut at 15:30), z = pooled standardised past excursions (about 39 sessions of 15-minute bars since the closing auction). Leave-one-session-out typical miss (rupees, mean absolute, 39 sessions; 31 for windows reaching 15:15): high Rs 6-15, low Rs 6-14 depending on the time of day, against Rs 10-22 for 'the high is the price now'. The 50% range held 36-65% and the 90% range 80-97% by checkpoint (39 sessions: noisy). Not validated beyond this; not a direction call; the new predictions have no live track record before 16 Oct 2026.
* "This hour" actual high and low are Yahoo 1-minute figures; NSE's official figures can differ by a few rupees.
