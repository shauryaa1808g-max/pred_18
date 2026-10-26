# Readings CSV

`readings.csv` holds every reading given to the user, all days, one row per reading; `by_day/<date>.csv` holds the same rows for one day. Both are rebuilt from the logs by `python3 src/readings_csv.py` (it runs after every table, every pre-open reading and every saved high/low forecast, and at the 16:45 scoring), so a row can never differ from what was shown. Nothing is ever filled in from a recomputed prediction. Blank = not applicable or not known yet.

| `kind` | what the row is | source |
|---|---|---|
| `open_range` | the 08:30 reading: open range and open pin-point (= previous close) and the close range for the day | `results/scoreboard/entries/<date>.json` |
| `nse_preopen` | one NSE pre-open snapshot: `nse_status` INDICATIVE or FINAL, `nse_price`, orders waiting | `results/preopen/BSE_<date>.jsonl` |
| `day_high_low_pre_open` | day-ahead high / low pin-points (median) and bands for the whole day | `results/hl_dayahead_<date>.json` |
| `day_high_low_after_open` | the same once the official open is known (`open_pin` = that open) | `results/hl_dayahead_<date>_open<price>.json` |
| `table` | one row of the hour-by-hour table; `printed_row` is the row as printed | `results/hourly_table_log.jsonl` |

Columns: `*_pin` = pin-point (median); `*_50_lo/hi` = "half the time" range; `*_90_lo/hi` = "9 in 10" range (for the after-open high the 90% columns are a 19-in-20 band); `window_start/end` = the window the high/low columns refer to (the next hour for a table, the whole session for the day rows); `compared_with` and `this_hour_*` = the comparison with the previous table given to the user (n/a when there was none; "REPLAYED" marks the 16 Oct tables whose previous prediction was recomputed afterwards, which is no longer done).

Scoring columns fill in later: `window_actual_*`, `window_*_error_rs`, `window_*_in50/in90` once the row's own window is over (tables: Yahoo 1-minute high / low from `results/hourly_table_scored.csv`; whole-day rows: the OFFICIAL high / low), and `official_*`, `open_error_rs`, `close_error_rs`, `*_in50/in90` once NSE's official bar is in the repo (about 16:35 IST). Errors are actual minus predicted.

History: the file starts with the 15 and 16 Oct 2026 readings that exist in the logs (the 16 Oct tables before 14:22 were not logged). From Mon 19 Oct every reading is stored when it is given.

## summary.csv
One row per hour-by-hour table (45 rows so far), only five columns: `date`, `time`, `precise close` (with its typical miss), `this hour's high vs previous prediction`, `this hour's low vs previous prediction`. The cells are cut out of `printed_row` of readings.csv, so they read exactly as printed. Rebuilt with readings.csv after every reading.
