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
