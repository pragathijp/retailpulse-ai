# Verification Matrix

Evidence from real-data runs on 11 October 2026 unless stated otherwise.

| Check | Enforced by | Evidence | Status |
|---|---|---|---|
| Surrogate line key unique | dbt `unique` on staging, intermediate, fact | 59/59 dbt pass; 269 key collisions resolved by sequence | Verified |
| Dedupe removes exact duplicates only | `assert_dedupe_removed_only_exact_duplicates`, ledger | 34,335 removed; raw = staged + removed + invalid | Verified |
| Returns never double-subtracted | dbt custom test, pytest, mutation check | mutation made 984 test rows fail (sandbox) | Verified |
| Net = gross minus returns | dbt and pytest | difference within 0.01 | Verified |
| Independent recompute equals model and Parquet | `test_independent_recompute_*` | pass on 1,033,036 rows | Verified |
| Marts equal fact; Parquet equals DuckDB | pytest (sums and row counts) | pass | Verified |
| RFM variance fully explained | dbt and pytest | unexplained 0.0000 | Verified |
| SQL RFM equals pandas RFM | `python run.py rfm_check`, `tests/test_rfm.py` | all 5,878 identical; NTILE equals DuckDB with ties | Verified |
| Forecast has no leakage; reconciles to fact | `tests/test_forecasting.py` | pass | Verified |
| Forecast verdict vs naive | `forecast_metrics.parquet` | Holt-Winters worse than naive; seasonal naive best | Reported as measured |
| Assistant numbers grounded | `tests/test_ai_assistant.py` (mocked LLM) | pass; disabling the check fails 4 tests | Verified (mock) |
| Assistant live with Gemini | `python src/ai_assistant.py --golden` | pending | PENDING |
| App KPIs equal the contract | `tests/test_app_pages.py` | pass on real data | Verified |
| DAX measures equal the contract | `tests/test_powerbi_assets.py` | pass | Verified |
| Power BI report equals the contract | `test_powerbi_kpis_match_contract` | KPI export not yet produced | PENDING |
| Clean-clone run | fresh clone, new venv, `python run.py run_all` | not yet rehearsed | PENDING |
