# Deviations, clarifications and additions to the pre-registration

Each entry states when it was made relative to seeing results of the affected model. Entries 1–7 were written **before any
model output on real BSE data had been produced** (only synthetic-data self-tests had been run).

| # | Date/time (IST) | Type | Change | Results seen before? |
|---|---|---|---|---|
| 1 | 2026-10-13 ~16:00 | clarification | Quantile grid also includes 0.025 and 0.975 (needed to evaluate the pre-registered 95% interval). | No |
| 2 | 2026-10-13 ~16:00 | clarification | L0 “location fixed at 0” is implemented by subtracting the trailing median of the standardised residuals, so the predictive *median* is exactly P0. L1 keeps the un-centred residuals (carries historical drift). | No |
| 3 | 2026-10-13 ~16:00 | factual fix | BSE Ltd shares are listed on NSE only (an exchange cannot list on itself); there is one trading venue. Pre-registration did not claim otherwise. | n/a |
| 4 | 2026-10-13 ~16:00 | addition (exploratory, non-gating) | Options-implied volatility (ATM Black-76 IV from NSE F&O bhavcopy settlement prices, available from the F&O listing of BSE Ltd, ≈ Dec 2024) is tested as an extra scale input `S7_iv` on its own short sample. It cannot enter the model-selection gate. | No |
| 5 | 2026-10-13 ~16:00 | addition (exploratory, non-gating) | Joint OHLC bootstrap (G, H′, L′, R scaled by σ_R) gives mutually-consistent forecasts of the high and low; H′/L′ coverage is reported descriptively. | No |
| 6 | 2026-10-13 ~16:00 | clarification | S5/S6 are also run for the G and I targets; the HAR proxy for G is G² (floored), for I it is the Garman–Klass variance. | No |
| 7 | 2026-10-13 ~16:00 | clarification | Location-model features are scaled by the S1 (EWMA) σ forecast; standardised ridge target is clipped to ±5 for fitting only. | No |
| 8 | 2026-10-13 ~16:15 | **data-error fix** | NSE's `PREV_CLOSE` in the archive files is **not** re-based on bonus/split ex-dates (found because the two largest "returns" were −110% and −105%). Returns now use our own previous kept close ÷ verified factor (`data/corp_actions_verified.csv`: 2:1 bonuses ex 2022-03-21 and 2025-05-23, factor 3). | No (found in data QA) |
| 9 | 2026-10-13 ~16:15 | data rule | Short special sessions (Muhurat, Saturday DR-drill) are dropped when Nifty-50 volume < 0.35 × trailing-20-session median (12 sessions). Their price moves roll into the next regular session's gap. The rule uses volume only, never returns. | No |
| 10 | 2026-10-13 ~16:15 | data completeness | Weekend sessions (Budget Saturdays/Sunday 2020-02-01, 2025-02-01, 2026-02-01 and the full special session 2024-01-20) were missing from the weekday-only download and were added. | No |
| 11 | 2026-10-13 ~16:15 | known limitation | Prices are *price* returns; cash dividends are not re-based. Cross-sectional breadth statistics are not cleaned for other stocks' corporate actions (affects only rare extreme-count columns, not the median/advance-share used). | n/a |
| 12 | 2026-10-13 ~16:45 | process | **Freeze point.** Scale-model code, location-model code, evaluator and Development-only hyperparameter selection (ridge α=1000, logit C=0.01; both at the strongest-regularisation edge of their pre-registered grids) are committed before any Validation/Final-window output exists. A shuffled-returns null test (tests/test_location_null.py) gave OOS R² ≈ −0.002 (max +0.003, 8 seeds), so the pipeline itself does not generate spurious predictability. | No (Dev window only seen) |
