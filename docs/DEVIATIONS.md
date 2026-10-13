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
