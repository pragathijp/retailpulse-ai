# Baseline (before gap-closure work)

- Commit: 617475d
- Python 3.13.2 (Windows); dbt-core 1.12.5; dbt-duckdb 1.11.0; duckdb 1.5.6; pandas 3.0.6; numpy 2.5.3;
  pyarrow 25.0.1; statsmodels 0.15.0; scikit-learn 1.9.1; pytest 9.1.1; dbt_utils 1.4.1
- Dataset: online_retail_II.xlsx (Online Retail II)

| Metric | Value |
|---|---|
| Raw rows | 1,067,371 |
| Staged rows | 1,033,036 |
| Exact duplicates removed | 34,335 |
| Total net revenue (GBP) | 19,013,462.6980 |
| RFM customers | 5,878 |
| Unexplained revenue (GBP) | 0.0000 |
| dbt build | 18/18 PASS (8 data tests: 5 not_null + 3 custom) |
| pytest | 3 passed |

Known issue at baseline: external-model views stored the relative path ../data/processed/,
so querying them from outside dbt_project failed (fixed in Task 1.3).
