# pred_18 — NSE:BSE (BSE Ltd) next-session forecast, 14 Oct 2026

* **Read first:** [`FORECAST_REPORT.md`](FORECAST_REPORT.md) — the forecast, evidence and honest assessment.
* **Dated record:** `results/forecast_record_2026-10-14.json` (score it after the session with `python3 src/score_forecast.py results/forecast_record_2026-10-14.json`).
* **Protocol committed before results:** `docs/PREREGISTRATION.md`; every departure: `docs/DEVIATIONS.md` (git commit times are authoritative).
* **Research dossiers:** `research/01_company_dossier.md`, `02_regulatory_macro_catalysts.md`, and the independent audit `03_independent_audit.md`.
* **Code:** `src/` (data fetch/build, models, walk-forward, evaluation, live forecast); **tests:** `tests/` (`test_same_row_real.py` is the leakage guard, with a positive control).
* Raw exchange archives are git-ignored (`data/raw`, re-creatable with `src/fetch_nse.py`, `src/fetch_fo.py`, `src/fetch_udiff.py`); processed data and all results are committed.

Nothing here is investment advice. The central finding is negative for direction: no model beat "unchanged" out of sample; the supported output is a risk range.
