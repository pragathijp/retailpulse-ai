# RetailPulse AI

A B2B retail analytics pipeline and decision-support platform, built as a consultancy-style deliverable on the public
**UCI Online Retail II** dataset (about 1.07 million transaction lines, December 2009 to December 2011).

It cleans the raw transactions, models them into tested analytical marts, segments customers (RFM), forecasts weekly
revenue, and presents the results in Power BI, a Streamlit app and a grounded AI assistant. Its guiding rule is
**one definition per metric, verified across layers** (SQL, Parquet, BI, app) to within 0.01 GBP.

**What it is not:** a store, a general upload-any-dataset tool, or internal management software. It is built for the
UCI Online Retail schema (versions I and II); other datasets need their own column mapping and business rules.

## Architecture

```text
data/raw (UCI xlsx/csv)
   -> src/ingestion.py        profile + load into DuckDB raw.retail_transactions
   -> dbt (dbt-duckdb)        staging -> intermediate -> marts, 48 data tests
   -> data/processed/*.parquet  (written by dbt external models)
        |-> Power BI Desktop  (powerbi/ build guide and DAX)
        |-> Streamlit app     (src/app)
        |-> forecasting.py, rfm_check.py, context_builder.py -> ai_assistant.py (Gemini)
        |-> pytest reconciliation suite (tests/)
```

Diagrams: [docs/architecture.md](docs/architecture.md).

## Quick start (Windows PowerShell)

```powershell
git clone https://github.com/pragathijp/retailpulse-ai.git
cd retailpulse-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python run.py setup                    # install pinned requirements + dbt packages
# put online_retail_II.xlsx (or the Online Retail csv/xlsx) into data\raw\
python run.py run_all                  # ingest, dbt build, analyses, RFM check, forecast, export, AI context, audit
streamlit run src/app/main.py          # optional app
```

`run.py` always re-launches itself inside the project `.venv`, so it works even if the venv is not activated.
`make` is optional (the Makefile only wraps `run.py`).

| Command | What it does |
|---|---|
| `python run.py setup` | install requirements and dbt packages |
| `python run.py ingest` | load the raw file into DuckDB and write `reports/data_profile.md` |
| `python run.py dbt_build` | `dbt build`: models, seeds and 48 data tests, Parquet export |
| `python run.py analyses` | compile dbt analyses and save `reports/analysis_*.csv` |
| `python run.py rfm_check` | independent pandas recomputation of the RFM mart |
| `python run.py forecast` | weekly forecast, metrics and `reports/forecast_report.md` |
| `python run.py export` | verify Parquet deliverables and write a manifest |
| `python run.py ai_context "question"` | build the JSON context for the assistant |
| `python run.py audit` | run the pytest reconciliation suite |
| `python run.py run_all` | everything above in order (`--skip-ingest` reuses the database) |
| `python run.py clean` | delete generated databases, Parquet files and dbt target |

## Metric definitions (single source: `metrics_contract.yml`)

- **Return line:** invoice starts with `C`, or quantity below 0.
- **Valid sale:** not a return, quantity above 0 and unit price above 0.
- **Gross revenue:** sum of quantity x unit price on valid sales.
- **Return amount:** sum of abs(quantity) x unit price on return lines with a positive price.
- **Net revenue:** gross revenue minus return amount, subtracted exactly once (a line is in one bucket only).
- **Orders:** distinct invoices containing a valid sale. **AOV:** gross revenue divided by orders.
- **Line key:** `md5` of invoice, stock code, timestamp and quantity, plus a deterministic sequence number for the
  few lines that share all four (269 on the real data). Only exact full-row duplicates (34,335) are removed.
- **Customers:** lines without a customer id stay in all revenue totals and are excluded from RFM. The gap is logged in
  `audit_revenue_variance` and fully explained: store revenue minus RFM revenue equals revenue of lines with no
  customer id plus revenue of identified customers with no valid sale (unexplained residual 0.0000).
- **Partial months:** the final month of data is partial; it counts in totals and is excluded from growth and forecasting.
- **Money:** exact decimals (18,4). No rounding inside the models.

## Results on the real data (last verified run, 11 October 2026)

| Item | Value |
|---|---|
| Raw rows / staged rows | 1,067,371 / 1,033,036 |
| Total net revenue | 19,013,462.70 GBP |
| Revenue on lines with no customer id | 2,723,471.41 GBP (235,151 lines) |
| Customers segmented (RFM) | 5,878 |
| Unexplained revenue variance | 0.0000 GBP |
| Products behind 80 percent of revenue | 1,049 of 4,881 ranked (21.49 percent) |
| dbt build | 59 of 59 pass (48 data tests) |
| pytest | all pass; 1 skipped until the Power BI KPI export exists |
| RFM cross-check | all 5,878 customers identical in pandas and SQL |

**Forecast (21-week holdout, mean absolute error):** seasonal naive (same week last year) 34,141 GBP is best;
naive 69,840; Holt-Winters 73,319; 4-week moving average 82,880. Holt-Winters does **not** beat the naive baseline here:
two years of history are too short for it to learn yearly seasonality. See `reports/forecast_report.md`.

## Testing layers

1. **dbt tests (48):** keys, accepted values and ranges, revenue identities, dedupe, variance, partial months.
2. **pytest reconciliation (`tests/`):** independent revenue recompute from staging, fact vs marts vs Parquet,
   RFM population and variance, row ledger, forecast leakage and reconciliation, contract execution,
   exact NTILE vs DuckDB, assistant grounding (mocked LLM), app KPIs vs the contract, DAX vs the contract.
3. **Power BI:** KPI export compared with the contract (`tests/test_contract.py`, skipped until the export exists).

Mutation checks were run during development (for example, making gross sales also count returns, or letting null
customers into RFM, or disabling the number check): each made the matching tests fail.

## AI assistant

`src/ai_assistant.py` sends pre-aggregated JSON (from the marts, using contract definitions) to Gemini and verifies
that every number in the reply exists in that JSON (or is a difference or percent change of two of its numbers).
A reply with an unverifiable figure is retried once, then withheld.

```powershell
copy .env.example .env                 # then put GEMINI_API_KEY in .env
python src/ai_assistant.py --list-models   # choose a model name, set GEMINI_MODEL in .env
python src/ai_assistant.py --golden        # five golden questions -> docs/ai_golden_answers.md
```

## Power BI

Follow [powerbi/BUILD_GUIDE.md](powerbi/BUILD_GUIDE.md). Measures live in `powerbi/measures.dax`; the six contract
measures are checked against `metrics_contract.yml` by a test. The `.pbix` is git-ignored (it embeds the data).

## Repository layout

```text
run.py, run_all.ps1, Makefile   runner (PowerShell first)
metrics_contract.yml            single definition of every KPI
src/                            ingestion, forecasting, rfm_check, context_builder, ai_assistant, kpis, app/
dbt_project/                    models, seeds, analyses, custom tests
tests/                          pytest suites
powerbi/                        measures.dax, kpi_export.dax, build guide
docs/                           baseline, architecture, verification matrix
reports/                        data profile, forecast report, analysis CSVs
```

## Known limitations

- Built for UCI Online Retail I and II only; not a general upload-any-dataset tool.
- Power BI is verified through an exported KPI file, not a live query (pytest cannot query Power BI).
- About two years of data: Holt-Winters cannot estimate yearly seasonality; boundary weeks are dropped from the forecast.
- Intervals are approximate (residual spread scaled by the square root of the horizon).
- The dataset has no product category field; "product" means stock code.
- The assistant answers only from the pre-aggregated context; questions outside it are refused.
- Airflow appears only as a conceptual diagram; nothing depends on it.
