# Architecture

## Data flow (as built)

```mermaid
flowchart TD
  A[UCI Online Retail II xlsx/csv] --> B[src/ingestion.py: normalise, profile]
  B --> C[(DuckDB raw.retail_transactions)]
  C --> D[dbt staging: stg_retail_transactions]
  D --> E[dbt intermediate: int_transactions_cleaned]
  E --> F[fact_sales]
  E --> G[mart_monthly_sales]
  E --> H[mart_product_performance]
  E --> I[mart_customer_rfm]
  E --> J[audit_revenue_variance]
  E --> K[audit_data_quality]
  F --> P[(data/processed Parquet)]
  G --> P
  H --> P
  I --> P
  J --> P
  P --> Q[Power BI Desktop]
  P --> R[Streamlit app]
  P --> S[forecasting.py]
  P --> T[rfm_check.py]
  P --> U[context_builder.py]
  U --> V[ai_assistant.py: Gemini + number check]
  P --> W[pytest reconciliation suite]
  C --> W
  X[metrics_contract.yml] --> W
  X --> Q
  X --> R
  X --> U
```

## Conceptual production orchestration (Airflow)

This is a documentation-only target-state diagram. Nothing in the project depends on Airflow;
locally the same order is run by `python run.py run_all`.

```mermaid
flowchart LR
  A[ingest] --> B[dbt build + tests]
  B --> C[analyses]
  C --> D[rfm_check]
  D --> E[forecast]
  E --> F[export verify]
  F --> G[ai_context]
  G --> H[audit pytest]
  H --> I[publish: Power BI refresh]
```

In Airflow each box would be a task; a failing dbt test or audit would stop the DAG before the BI refresh.
