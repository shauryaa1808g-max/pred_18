# Hour-by-hour paper trade: rules fixed BEFORE the backtest (written Fri 16 Oct 2026, about 14:22 IST)

Purpose: the user asked for a paper-trade algorithm built on the hour-by-hour method (next-hour high/low pin-points), "if that would be better" than the open-to-close lean (PT1/PT2 of the scoreboard). These rules and the verdict test below were written before any rule was run. Nothing here claims an edge: the pin-points are medians of price excursions, symmetric around the price, so they carry no direction information by construction; the test is whether trading around them survives costs.

Checkpoints: 10:00, 11:00, 12:00, 13:00, 14:00 (15-minute bar index k = 3, 7, 11, 15, 19 completed bars). Window = the next 4 bars (60 minutes). P = close of the last completed bar. Pin-points H* and L* = the leave-one-session-out MEDIAN of the next-hour high and low from `src/hourly_table.py`. Cost: 0.10% round trip on every filled trade (the project's convention); no extra slippage (stated, generous to the rules). One trade per rule per window, exit at the close of the window's last bar. Orders fill only if the bar trades STRICTLY through the level (low < limit for a buy, high > limit for a short); fills are at the limit price; if stop and target are both inside the same bar the stop is assumed first.

Rules:
* R-A buy the dip: limit buy at L*; exit at window end.
* R-B sell the pop: limit short at H*; exit at window end.
* R-C long with bracket: buy at P; target H*, stop L*; exit at window end otherwise.
* R-D short with bracket: sell at P; target L*, stop H*; exit at window end otherwise.
* R-E control: buy at P, sell at window end (no use of the predictions).

Data: the 39 post-closing-auction sessions of 15-minute bars (data/processed/intraday_union_15m.csv + intraday_extra_15m.csv), predictions leave-one-session-out (no look-ahead). Placebo: 400 random-walk paths per checkpoint with the same time-of-day variance profile, same prediction method, same rules (what a no-edge world pays).

Verdict rule (fixed now): a rule is called "better than nothing" only if its mean net return per trade is > 0 with a session-clustered t-statistic > 2 AND it is positive in both halves of the sample AND it beats the placebo's mean by more than 2 standard errors. Otherwise it is "not found" (and the live paper ledger still records it, labelled, because paper trading is how the question gets answered with more data). The scoreboard's PT1/PT2 stay as they are.
